"""Reconstruct candidate recommendations from retained, verified replay evidence."""

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, replace
from datetime import datetime
from hashlib import sha256
import json
import math
from pathlib import Path
from typing import Any, Literal, cast

import pandas as pd

from backtesting.confirmation_registry import ConfirmationRegistry
from backtesting.data_admission import AdmittedOrigin, assess_origins, require_admitted, require_input
from backtesting.portable_evidence import BlobStore, compute_serving_model_closure, validate_relative_posix_path
from backtesting.evidence_statistics import (
    EARLY_HARM_P_THRESHOLD,
    EarlyHarmAssessment,
    KendallPwHacResult,
    PairedGameweekScore,
    StatisticalProtocolConfig,
    assign_gameweek_segment,
    compute_score_trace_hash,
    evaluate_early_harm_fallback,
    evaluate_evidence_against_protocol,
    obrien_fleming_alpha,
    run_kendall_pw_hac_test,
)
from backtesting.promotion import segment_regression_tolerance
from models.selection import ModelSelection, load_model_selection, save_model_selection
from backtesting.forecast_export import strict_solver_table
from backtesting.forecast_store import load_forecast_verified
from backtesting.ownership_anchor import OwnershipAnchor, compute_universe_digest
from backtesting.projection_guards import (
    GuardOutput,
    MetricDirection,
    evaluate_gw_clustered_non_inferiority_guard,
    evaluate_non_inferiority_guard,
)
from backtesting.rolling_replay import (
    QualityPolicy,
    ReplayDeadlineRecord,
    UncertifiedSolveError,
    forecast_content_hash,
    record_from_dict,
    refresh_replay_market,
    replay_evaluation_identity,
    replay_solver_identity,
    get_strategic_replay_options,
    validate_quality_policy_gate,
    verify_replay_record,
    validate_solver_certificate_consistency,
)
from backtesting.season_rules import load_season_lifecycle

EVIDENCE_VERSION = "rolling-promotion-v1"
CHECKPOINT_EVIDENCE_VERSION = "adr0069-checkpoint-v1"
CHECKPOINT_EVIDENCE_V2 = "adr0069-checkpoint-v2"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
GUARD_SEMANTICS = {
    "points_mse": ("projected_points", "actual_points", "squared_error", "points^2"),
    "minutes_mae": ("projected_minutes", "actual_minutes", "absolute_error", "minutes"),
    "goals_points_mse": ("xp_goals", "actual_goals_points", "squared_error", "points^2"),
    "assists_points_mse": ("xp_assists", "actual_assists_points", "squared_error", "points^2"),
    "clean_sheet_points_mse": ("xp_clean_sheet", "actual_clean_sheet_points", "squared_error", "points^2"),
    "saves_points_mse": ("xp_saves", "actual_saves_points", "squared_error", "points^2"),
    "bonus_points_mse": ("xp_bonus", "actual_bonus_points", "squared_error", "points^2"),
    "minutes_points_mse": ("xp_minutes", "actual_minutes_points", "squared_error", "points^2"),
    "conceded_points_mse": ("xp_conceded", "actual_conceded_points", "squared_error", "points^2"),
    "defcon_points_mse": ("xp_defcon", "actual_defcon_points", "squared_error", "points^2"),
    "yellow_cards_points_mse": ("xp_yellow_cards", "actual_yellow_cards_points", "squared_error", "points^2"),
    "red_cards_points_mse": ("xp_red_cards", "actual_red_cards_points", "squared_error", "points^2"),
    "penalties_saved_points_mse": ("xp_penalties_saved", "actual_penalties_saved_points", "squared_error", "points^2"),
    "penalties_missed_points_mse": ("xp_penalties_missed", "actual_penalties_missed_points", "squared_error", "points^2"),
    "own_goals_points_mse": ("xp_own_goals", "actual_own_goals_points", "squared_error", "points^2"),
}
MANDATORY_GUARDS = frozenset(GUARD_SEMANTICS)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def content_hash(value: Any) -> str:
    return sha256(canonical_bytes(value)).hexdigest()


def current_model_source_hash(model_names: Sequence[str] = ()) -> str:
    """Return the portable transitive serving model closure SHA-256."""
    return compute_serving_model_closure(tuple(model_names)).serving_model_closure_hash


def _local_path(root: Path, relative: Any) -> Path:
    rel = validate_relative_posix_path(str(relative)) if isinstance(relative, str) else ""
    if not rel:
        raise ValueError("Missing retained evidence path")
    path = Path(rel)
    result = (root / path).resolve()
    if path.is_absolute() or ".." in path.parts or not result.is_relative_to(root.resolve()):
        raise ValueError("Evidence path must remain within request directory")
    return load_season_lifecycle().assert_unsealed_storage_path(result, error_message="Protected evidence path")


def _relative_bundle_path(registry: ConfirmationRegistry, bundle_path: Path) -> str:
    reg_dir = registry.registry_file.parent.resolve()
    try:
        rel = bundle_path.resolve().relative_to(reg_dir).as_posix()
    except ValueError as exc:
        raise ValueError("Bundle path must remain within confirmation registry directory") from exc
    return validate_relative_posix_path(rel)


def _read_material(root: Path, reference: Mapping[str, Any]) -> dict[str, Any]:
    if set(reference) != {"path", "sha256"}:
        raise ValueError("Expected path and SHA256 evidence reference")
    raw = _local_path(root, reference["path"]).read_bytes()
    if sha256(raw).hexdigest() != reference["sha256"]:
        raise ValueError("Retained evidence checksum mismatch")
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("Retained evidence must be an object")
    return value


def _restore_bytes(value: Any) -> Any:
    if isinstance(value, dict):
        if set(value) == {"bytes_hex"}:
            return bytes.fromhex(value["bytes_hex"])
        return {key: _restore_bytes(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_restore_bytes(item) for item in value]
    return value


def _resolve_context_catalog(root: Path | None, context: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, bytes]]:
    request = _restore_bytes(context["request"])
    raw_catalog = context["catalog"]
    if not isinstance(raw_catalog, Mapping):
        raise ValueError("Admission context catalog must be a mapping")
    blob_store = BlobStore(root) if root is not None else None
    catalog: dict[str, bytes] = {}
    for digest, raw in raw_catalog.items():
        if isinstance(raw, str):
            catalog[str(digest)] = bytes.fromhex(raw)
        elif isinstance(raw, Mapping):
            if blob_store is None:
                raise ValueError("Externalized blob catalog requires request root")
            expected_sha = str(raw.get("blob_sha256", ""))
            relpath = str(raw.get("relpath") or raw.get("path") or f"blobs/{expected_sha}")
            catalog[str(digest)] = blob_store.read_bytes(relpath, expected_sha256=expected_sha)
        else:
            raise ValueError(f"Unsupported catalog entry type for {digest!r}")
    return request, catalog


def _admit_context(
    context: dict[str, Any],
    season: str,
    gw: int,
    *,
    root: Path | None = None,
) -> tuple[AdmittedOrigin, dict[str, Any], dict[str, bytes]]:
    request, catalog = _resolve_context_catalog(root, context)
    return require_admitted(request, catalog, season, gw, allow_disk_path_fallback=False), request, catalog


def protocol_from_payload(payload: dict[str, Any]) -> StatisticalProtocolConfig:
    settings = dict(payload["statistics"])
    settings["required_projection_guards"] = tuple(settings.get("required_projection_guards", ()))
    config = StatisticalProtocolConfig(**settings)
    declaration = {key: value for key, value in payload.items() if key != "statistics"}
    if config.evidence_protocol_hash != content_hash(declaration):
        raise ValueError("Registered evidence protocol declaration mismatch")
    if payload.get("horizon") != 6 or set(payload["windows"]) != {config.development_season, config.confirmation_season}:
        raise ValueError("Final evaluation requires declared development and confirmation schedules")
    for gameweeks in payload["windows"].values():
        if not gameweeks or gameweeks != list(range(1, max(gameweeks) + 1)):
            raise ValueError("Continuous replay schedule must begin at locked GW1")
    if set(payload["guard_specs"]) != set(config.required_projection_guards):
        raise ValueError("Guard specifications differ from frozen protocol inventory")
    if not MANDATORY_GUARDS <= set(config.required_projection_guards):
        raise ValueError("Required total-points, minutes or measurable component guards omitted")
    for name, spec in payload["guard_specs"].items():
        if type(spec["margin"]) not in (int, float) or not math.isfinite(spec["margin"]) or spec["margin"] < 0 or not 0 < spec["alpha"] < 1:
            raise ValueError("Invalid approved guard uncertainty or margin")
        if name in GUARD_SEMANTICS and ((spec["forecast_field"], spec["outcome_field"], spec["loss"], spec.get("units")) != GUARD_SEMANTICS[name] or spec["direction"] != "lower_is_better"):
            raise ValueError("Mandatory guard semantics differ from protected forecast metric")
    projection = payload.get("projection_evaluation", {})
    if projection.get("leads") != list(range(6)) or projection.get("population") != "all_admitted_players" or projection.get("missingness") != "fail_closed" or projection.get("aggregation") != "weighted_paired_player_gameweek":
        raise ValueError("Explicit projection population, horizon leads, aggregation and missingness required")
    weights = projection.get("weights")
    if not isinstance(weights, list) or len(weights) != 6 or any(type(weight) not in (int, float) or not math.isfinite(weight) or weight <= 0 for weight in weights):
        raise ValueError("Six explicit positive projection horizon weights required")
    expected_applicability = {season: {name: ("inapplicable_native" if name == "defcon_points_mse" and season in ("2023-24", "2024-25") else "required") for name in config.required_projection_guards} for season in payload["windows"]}
    if projection.get("applicability") != expected_applicability:
        raise ValueError("Predeclared season/component guard applicability required")
    return config


def native_solver_identity() -> str:
    from backtesting.native_transfer_solver import native_strategic_solve

    return replay_solver_identity(native_strategic_solve)


_ACTUAL_XP_TO_GUARD_OUTCOME = {
    "actual_xp_goals": "actual_goals_points",
    "actual_xp_assists": "actual_assists_points",
    "actual_xp_clean_sheet": "actual_clean_sheet_points",
    "actual_xp_saves": "actual_saves_points",
    "actual_xp_bonus": "actual_bonus_points",
    "actual_xp_minutes": "actual_minutes_points",
    "actual_xp_conceded": "actual_conceded_points",
    "actual_xp_defcon": "actual_defcon_points",
    "actual_xp_yellow_cards": "actual_yellow_cards_points",
    "actual_xp_red_cards": "actual_red_cards_points",
    "actual_xp_penalties_saved": "actual_penalties_saved_points",
    "actual_xp_penalties_missed": "actual_penalties_missed_points",
    "actual_xp_own_goals": "actual_own_goals_points",
}


def _extract_origin_players_and_outcomes(
    origin: Mapping[str, Any],
    catalog: Mapping[str, bytes] | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Normalize synthetic v1 or empirical v2 origin into canonical (players, outcomes) lists."""
    if "sources" not in origin or not isinstance(origin.get("sources"), Mapping):
        return list(origin["players"]), list(origin["outcomes"])

    from backtesting.empirical_admission import resolve_and_verify_source_bytes
    from backtesting.fplcache_ingest import _sanitize_bootstrap, _utc
    from backtesting.walkforward import _build_actual_components

    sources = origin["sources"]
    bs_spec = sources["bootstrap"]
    out_spec = sources["outcomes"]
    bs_dec = resolve_and_verify_source_bytes(
        bs_spec, catalog, role_label="bootstrap", allow_disk_path_fallback=catalog is None
    )
    out_dec = resolve_and_verify_source_bytes(
        out_spec, catalog, role_label="outcomes", allow_disk_path_fallback=catalog is None
    )

    sanitized, _, bs_issues = _sanitize_bootstrap(
        json.loads(bs_dec.decode("utf-8")),
        capture_upper=_utc(bs_spec["capture_upper"]),
    )
    if bs_issues:
        raise ValueError("Malformed empirical bootstrap in promotion evidence")

    players = [
        {
            "id": int(el["id"]),
            "club": int(el["team"]),
            "position": int(el["element_type"]),
            "price": int(el["now_cost"]),
            "ownership": float(el.get("selected_by_percent") or 0.0),
            "eligible": bool(el["purchase_eligible"]),
        }
        for el in sanitized
    ]
    season = str(origin["season"])
    gw = int(origin["gw"])
    out_rows = json.loads(out_dec.decode("utf-8"))
    out_df = pd.DataFrame(out_rows)
    if out_df.empty:
        raise ValueError("Empty empirical outcomes in promotion evidence")
    if "gameweek_id" not in out_df.columns:
        out_df["gameweek_id"] = gw
    players_df = pd.DataFrame(
        {
            "player_id": [p["id"] for p in players],
            "position_id": [p["position"] for p in players],
            "native_rules_version": season,
        }
    )
    actual_df = _build_actual_components(out_df.drop(columns=["position_id"], errors="ignore"), players_df)
    normalized_outcomes: list[dict[str, Any]] = []
    for row in actual_df.to_dict(orient="records"):
        norm: dict[str, Any] = {
            "gw": int(row["gameweek_id"]),
            "player": int(row["player_id"]),
            "points": float(row["total_points"]),
            "minutes": int(row["minutes"]),
        }
        for src_col, dst_col in _ACTUAL_XP_TO_GUARD_OUTCOME.items():
            norm[dst_col] = float(row[src_col])
        normalized_outcomes.append(norm)
    return players, normalized_outcomes


def _verify_live_readiness(root: Path, payload: dict[str, Any], candidate: str, champion: str, protocol_hash: str, source_hash: str, frozen_review: dict[str, Any]) -> None:
    from backtesting.live_capture import LiveDeadlineCapture, PlayerForecastSnapshot

    if payload.get("version") == 2 and payload.get("mode") == "fplcache":
        if (payload.get("candidate_name"), payload.get("former_champion"), payload.get("protocol_hash")) != (candidate, champion, protocol_hash):
            raise ValueError("Live readiness identity mismatch")
        if not payload.get("fplcache_manifest_path"):
            raise ValueError("ADR 0069 live readiness requires fplcache_manifest_path")
        max_lag = payload.get("max_snapshot_lag_hours")
        if not isinstance(max_lag, (int, float)) or isinstance(max_lag, bool) or not 0 < float(max_lag) <= 24.0:
            raise ValueError("ADR 0069 fplcache readiness requires <= 24h snapshot lag ceiling")
        reviews = payload.get("review_gameweeks")
        if reviews != [15, 30, 38]:
            raise ValueError("ADR 0069 pre-declared checkpoints must be [15, 30, 38]")
        delay = payload.get("settlement_delay_hours")
        if not isinstance(delay, (int, float)) or isinstance(delay, bool) or float(delay) < 24.0:
            raise ValueError("ADR 0069 requires >= 24h settlement delay")
        if payload.get("early_harm_min_gw") != 6 or payload.get("early_harm_p_threshold") != 0.025:
            raise ValueError("ADR 0069 requires calibrated Early-Harm parameters (min_gw=6, p_threshold=0.025)")
        if {key: payload.get(key) for key in ("mode", "review_gameweeks", "settlement_delay_hours", "early_harm_min_gw", "early_harm_p_threshold")} != frozen_review:
            raise ValueError("Live review configuration differs from frozen protocol")
        return

    if (payload.get("version"), payload.get("candidate_name"), payload.get("former_champion"), payload.get("protocol_hash")) != (1, candidate, champion, protocol_hash):
        raise ValueError("Live readiness identity mismatch")
    if payload.get("capture_before_deadline") is not True or payload.get("native_shadow_replay") is not True:
        raise ValueError("Live capture and native shadow replay must be configured")
    if payload.get("capture_job") != {"module": "commands.capture_live_evidence", "before_deadline_minutes": 30, "clock": "execution_utc"}:
        raise ValueError("Missing prospective capture job configuration")
    if payload.get("prospective_evidence_status") != "pending" or payload.get("readiness") != "configured":
        raise ValueError("Configured capture readiness must distinguish prospective evidence pending")
    if set(payload.get("dry_run_captures", {})) != {candidate, champion}:
        raise ValueError("Both capture job dry-run outputs required")
    for model, reference in payload["dry_run_captures"].items():
        proof = _read_material(root, reference)
        capture = LiveDeadlineCapture(**{**proof, "forecasts": [PlayerForecastSnapshot(**row) for row in proof["forecasts"]]})
        if capture.compute_hash() != capture.capture_hash or capture.model_name != model or capture.model_version_hash != source_hash or capture.policy_settings_hash != protocol_hash or capture.is_late or not capture.forecasts:
            raise ValueError("Capture job dry-run proof failed identity/integrity verification")
        if datetime.fromisoformat(capture.capture_time_utc) > datetime.fromisoformat(capture.deadline_time_utc):
            raise ValueError("Capture job dry-run missed deadline")
    reviews = payload.get("review_gameweeks")
    if not isinstance(reviews, list) or not reviews or any(type(gw) is not int or gw < 4 for gw in reviews) or reviews != sorted(set(reviews)):
        raise ValueError("Missing predefined sufficient-evidence live review points")
    if type(payload.get("settlement_delay_hours")) not in (int, float) or payload["settlement_delay_hours"] <= 0:
        raise ValueError("Missing outcome settlement delay")
    if type(payload.get("material_loss_limit")) not in (int, float) or not math.isfinite(payload["material_loss_limit"]) or payload["material_loss_limit"] < 0:
        raise ValueError("Missing approved live material-harm limit")
    if {key: payload[key] for key in ("capture_job", "review_gameweeks", "settlement_delay_hours", "material_loss_limit")} != frozen_review:
        raise ValueError("Live review configuration differs from frozen protocol")


def _verify_replay(
    root: Path,
    entry: dict[str, Any],
    protocol: dict[str, Any],
    config: StatisticalProtocolConfig,
    model_source_hash: str,
    guard_outcomes: dict[tuple[str, int, int], dict[str, Any]],
    registered_at: str,
    *,
    max_target_gw: int | None = None,
    frozen_protocol_hash: str | None = None,
) -> tuple[list[ReplayDeadlineRecord], list[dict[str, Any]], bool]:
    season, model = entry["season"], entry["model_name"]
    if season not in protocol["windows"]:
        raise ValueError("Replay season outside frozen protocol")
    anchor = OwnershipAnchor.from_dict(_read_material(root, entry["anchor"]))
    if anchor.season != season or anchor.anchor_type != "opening" or anchor.gameweek != 1 or anchor.total_budget != 1000 or anchor.certificate.status != "OPTIMAL":
        raise ValueError("Missing certified neutral opening anchor")
    state = anchor.to_replay_state(season)
    raw_trace = _read_material(root, entry["trace"])
    records = [record_from_dict(row) for row in raw_trace["records"]]
    from backtesting.rolling_replay import record_to_dict

    if any(canonical_bytes(raw) != canonical_bytes(record_to_dict(record)) for raw, record in zip(raw_trace["records"], records, strict=True)):
        raise ValueError("Replay trace contains malformed or lossy typed values")
    if [record.deadline for record in records] != protocol["windows"][season] or len(entry["issues"]) != len(records):
        raise ValueError("Replay trace does not cover the complete frozen schedule")
    quality = QualityPolicy(**protocol["quality_policy"])
    try:
        validate_quality_policy_gate(quality, require_certified=True)
    except UncertifiedSolveError as exc:
        raise ValueError(str(exc)) from exc
    protocol_hash = frozen_protocol_hash or config.compute_hash()
    identity = replay_evaluation_identity(
        model_name=model, model_version_hash=model_source_hash, protocol_hash=protocol_hash,
        season=season, anchor_id=anchor.anchor_id, horizon=6, last_gw=38, scored_end_gw=max(protocol["windows"][season]),
        policy=quality, chip_calendar=tuple(tuple(item) for item in protocol["chip_calendar"]),
        solver_identity=protocol["solver_identity"],
    )
    evidence_rows: list[dict[str, Any]] = []
    empirical = True
    parent_id: str | None = None
    for record, issue in zip(records, entry["issues"], strict=True):
        context = _read_material(root, issue["admission"])
        admitted, request, catalog = _admit_context(context, season, record.deadline, root=root)
        empirical = empirical and (admitted.mode == "empirical" and admitted.promotable and not admitted.partial_prefix)
        capability = require_input(request, catalog, season, record.deadline, allow_disk_path_fallback=False)
        origin = next(origin for origin in request["origins"] if origin["season"] == season and origin["gw"] == record.deadline)
        origin_players, origin_outcomes = _extract_origin_players_and_outcomes(origin, catalog)
        origin_universe = [player["id"] for player in origin_players]
        if record.deadline == 1:
            universe = pd.DataFrame(origin_players).rename(columns={"id": "player_id", "club": "club_id", "position": "position_id", "price": "now_cost", "ownership": "selected_by_percent", "eligible": "is_eligible"})
            if anchor.source_digest != compute_universe_digest(universe):
                raise ValueError("Neutral anchor differs from admitted opening universe")
            selected = {player["id"]: player for player in origin_players if player["id"] in anchor.player_ids}
            position_codes = {1: "GK", 2: "D", 3: "M", 4: "F"}
            if len(selected) != 15 or any(anchor.acquisition_prices[pid] != player["price"] or anchor.player_clubs[pid] != player["club"] or anchor.player_positions[pid] != position_codes[player["position"]] or anchor.player_eligible.get(pid) != player["eligible"] or not player["eligible"] for pid, player in selected.items()):
                raise ValueError("Neutral anchor acquisition state differs from admitted opening metadata")
            if not math.isclose(anchor.objective_value, sum(float(player["ownership"]) for player in selected.values()), abs_tol=1e-6) or anchor.certificate.total_cost != sum(anchor.acquisition_prices.values()) or anchor.certificate.bank != anchor.bank or anchor.certificate.objective_value != anchor.objective_value:
                raise ValueError("Neutral anchor certificate differs from independently reconstructed objective/finances")
        cache = _local_path(root, issue["forecast_store"])
        predictions, material = load_forecast_verified(cache, issue["forecast_id"], capability, request, catalog, issue["training_authority"], model)
        generated = json.loads((cache / "forecasts" / issue["forecast_id"] / "generator_log.json").read_bytes())
        generation_time = datetime.fromisoformat(generated["completed_at"])
        registration_time = datetime.fromisoformat(registered_at)
        start = generated.get("started_at") if frozen_protocol_hash else generated["completed_at"]
        generation_start = datetime.fromisoformat(start) if isinstance(start, str) else None
        if (generation_time.utcoffset() is None or generation_start is None or generation_start.utcoffset() is None
                or generation_start > generation_time):
            raise ValueError("Verified forecast generation timing required")
        if season == config.confirmation_season and generation_start < registration_time:
            raise ValueError("Confirmation forecast predates frozen finalist registration")
        if season == config.development_season and generation_time >= registration_time:
            raise ValueError("Development selection evidence must precede finalist registration")
        wide = strict_solver_table(predictions, capability, request, catalog)
        wide = wide.rename(columns={"club": "club_id", "position": "position_id", "price": "now_cost"})
        eligibility = {player["id"]: player["eligible"] for player in origin_players}
        wide["purchase_eligible"] = wide["player_id"].map(lambda pid: eligibility[pid])
        if record.forecast_hash != forecast_content_hash(wide) or record.evaluation_identity != identity:
            raise ValueError("Replay does not bind verified forecasts and frozen policy")
        if record.model_version_hash != model_source_hash or record.protocol_hash != protocol_hash:
            raise ValueError("Replay model or protocol identity mismatch")
        if material["model"] != model or material["input_digest"] != capability.input_digest:
            raise ValueError("Forecast model or admitted input mismatch")
        if "serving_model_closure_hash" in material:
            model_closure = compute_serving_model_closure((model,))
            if (
                material.get("serving_model_closure_hash") != model_closure.serving_model_closure_hash
                or material.get("model_runtime_bindings") != model_closure.model_runtime_bindings
            ):
                raise ValueError("Forecast serving closure or runtime binding mismatch")
        if material["model_parameters"] != {}:
            raise ValueError("Unsupported forecast generator parameterization")
        if record.outcomes.source_identity != admitted.evidence_digest:
            raise ValueError("Scored outcomes do not bind admitted source closure")
        source_points: dict[int, float] = {pid: 0.0 for pid in origin_universe}
        source_minutes: dict[int, float] = {pid: 0.0 for pid in origin_universe}
        for outcome in origin_outcomes:
            if outcome["gw"] == record.deadline:
                source_points[outcome["player"]] += outcome["points"]
                if type(outcome.get("minutes")) is not int:
                    raise ValueError("Admitted native appearance/minutes evidence required")
                source_minutes[outcome["player"]] += outcome["minutes"]
        if {pid: value.points for pid, value in record.outcomes.outcomes} != source_points:
            raise ValueError("Replay scores differ from admitted native outcomes")
        if any(value.minutes != source_minutes[pid] or value.appeared != (source_minutes[pid] > 0) for pid, value in record.outcomes.outcomes):
            raise ValueError("Replay appearance or minutes differ from admitted native outcomes")
        certificate = record.certificate
        validate_solver_certificate_consistency(certificate)
        if (record.execution_status != "SUCCESS" or not certificate.feasible or certificate.quality_mode != "certified"
                or certificate.termination_status != "OPTIMAL" or certificate.relative_gap > quality.target_gap + 1e-8
                or certificate.threads != 1 or certificate.seed != 42 or certificate.runtime_seconds > quality.time_limit_seconds):
            raise ValueError("Replay lacks required certified solver-quality certificate")
        lowered_solver = record.certificate.solver_version.lower()
        if any(bad in lowered_solver for bad in ("lineup", "dry_run", "diagnostic", "mock", "heuristic")):
            raise ValueError("Diagnostic/mock solver cannot produce final promotion evidence")
        expected_options = get_strategic_replay_options(min(6, 39 - record.deadline), rules_version=season)
        if any(record.certificate.strategic_audit.get(key) != value for key, value in expected_options.items()):
            raise ValueError("Effective solver policy differs from frozen Strategic baseline")
        if record.decision.chip != dict(protocol["chip_calendar"]).get(record.deadline):
            raise ValueError("Replay chip differs from registered shared calendar")
        state = refresh_replay_market(state, wide)
        state = verify_replay_record(record, state, model_name=model, parent_checkpoint_id=parent_id)
        parent_id = record.checkpoint_id
        evidence_rows.extend(
            group_projection_gameweeks(
                predictions, season, record.deadline, guard_outcomes, max_target_gw=max_target_gw
            )
        )
    return records, evidence_rows, empirical


def group_projection_gameweeks(
    predictions: pd.DataFrame,
    season: str,
    issue_gw: int,
    outcomes: dict[tuple[str, int, int], dict[str, Any]],
    *,
    max_target_gw: int | None = None,
) -> list[dict[str, Any]]:
    """Score issue-known fixture sums against complete finalized player/GW outcomes."""
    columns = ["projected_points", "projected_minutes", *{semantics[0] for semantics in GUARD_SEMANTICS.values() if semantics[0].startswith("xp_")}]
    grouped = cast(pd.DataFrame, predictions.groupby(["player_id", "gameweek_id"], as_index=False)[columns].sum())
    if max_target_gw is not None:
        grouped = cast(pd.DataFrame, grouped[grouped["gameweek_id"] <= max_target_gw])
    result: list[dict[str, Any]] = []
    for row in grouped.to_dict(orient="records"):
        native = outcomes.get((season, row["gameweek_id"], row["player_id"]))
        if native is None:
            raise ValueError("Missing complete finalized player/gameweek component outcomes")
        result.append({**row, "season": season, "issue_gw": issue_gw, "_observed": native})
    return result


def finalized_gameweek_outcomes(
    origin: dict[str, Any],
    protocol: dict[str, Any],
    *,
    catalog: Mapping[str, bytes] | None = None,
) -> dict[tuple[str, int, int], dict[str, Any]]:
    """Only call after independent native outcome admission proves complete coverage."""
    season, gw = origin["season"], origin["gw"]
    origin_players, origin_outcomes = _extract_origin_players_and_outcomes(origin, catalog)
    fields = {spec["outcome_field"] for spec in protocol["guard_specs"].values()}
    totals = {(season, gw, player["id"]): {field: 0.0 for field in fields} for player in origin_players}
    for row in origin_outcomes:
        if row["gw"] != gw:
            raise ValueError("Incorrectly scoped guard outcome source")
        measured = {**row, "actual_points": row["points"], "actual_minutes": row.get("minutes")}
        target = totals[season, gw, row["player"]]
        for field in fields:
            if field == "actual_defcon_points" and season in ("2023-24", "2024-25"):
                value = 0.0
            else:
                value = measured.get(field)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError("Missing measured native component outcome")
            target[field] += float(value)
    component_fields = {semantics[1] for name, semantics in GUARD_SEMANTICS.items() if name not in {"points_mse", "minutes_mae"}}
    for native in totals.values():
        if not math.isclose(sum(native[field] for field in component_fields), native["actual_points"], abs_tol=1e-6):
            raise ValueError("Finalized native component ledger does not reconcile to total points")
    return totals


def _compute_guard_loss(predicted: Any, realized: Any, loss: str) -> float:
    if (
        isinstance(predicted, bool)
        or isinstance(realized, bool)
        or not isinstance(predicted, (int, float))
        or not isinstance(realized, (int, float))
        or not math.isfinite(predicted)
        or not math.isfinite(realized)
    ):
        raise ValueError("Missing or nonfinite required projection evidence")
    delta = float(predicted) - float(realized)
    if loss == "squared_error":
        return delta * delta
    if loss == "absolute_error":
        return abs(delta)
    if loss == "signed_error":
        return delta
    raise ValueError(f"Unknown predefined guard loss '{loss}'")


def derive_s1_guard_margins(
    champion_rows: Sequence[Mapping[str, Any]],
    *,
    leads: Sequence[int] = (0, 1, 2, 3, 4, 5),
    weights: Sequence[float] = (1.0, 1.0, 1.0, 1.0, 1.0, 1.0),
    guard_specs: Mapping[str, Mapping[str, Any]] | None = None,
    inapplicable_metrics: Sequence[str] = (),
) -> dict[str, float]:
    """Derive 15 mandatory non-inferiority margins from Confirmed Champion S-1 paired errors.

    Formula (#186): margin_i = max(0.05 * S1_mean_i, 1.0 * S1_GW_SE_i) across all admitted
    players and registered leads 0..5.
    """
    if not champion_rows:
        raise ValueError("Cannot derive S-1 guard margins from empty Champion rows")
    if len(leads) != len(weights) or not leads or any(
        type(w) not in (int, float) or not math.isfinite(w) or w <= 0 for w in weights
    ):
        raise ValueError("Positive horizon weights matching declared leads required")

    lead_weights = dict(zip(leads, weights, strict=True))
    inapplicable = set(inapplicable_metrics)
    specs: Mapping[str, Mapping[str, Any]] = guard_specs or {
        name: {"forecast_field": s[0], "outcome_field": s[1], "loss": s[2]}
        for name, s in GUARD_SEMANTICS.items()
    }
    margins: dict[str, float] = {}
    for name, spec in specs.items():
        if name in inapplicable:
            continue
        raw_errors: list[float] = []
        row_weights: list[float] = []
        row_gws: list[int] = []
        f_field = str(spec["forecast_field"])
        o_field = str(spec["outcome_field"])
        loss = str(spec["loss"])
        for row in champion_rows:
            lead = int(row["gameweek_id"]) - int(row["issue_gw"])
            if lead not in lead_weights:
                continue
            obs = row["_observed"]
            raw_errors.append(_compute_guard_loss(row[f_field], obs[o_field], loss))
            row_weights.append(float(lead_weights[lead]))
            row_gws.append(int(row["gameweek_id"]))

        if not raw_errors:
            raise ValueError(f"No matching lead observations for S-1 guard margin '{name}'")
        scaling = float(len(row_weights)) / float(sum(row_weights))
        weighted = [e * w * scaling for e, w in zip(raw_errors, row_weights, strict=True)]
        s1_mean = sum(weighted) / float(len(weighted))
        by_gw: dict[int, list[float]] = {}
        for gw, val in zip(row_gws, weighted, strict=True):
            by_gw.setdefault(gw, []).append(val)
        if len(by_gw) < 2:
            raise ValueError(f"At least two gameweeks required to estimate S-1 GW SE for '{name}'")
        gw_means = [sum(vals) / float(len(vals)) for vals in by_gw.values()]
        gw_mean_avg = sum(gw_means) / float(len(gw_means))
        gw_var = sum((m - gw_mean_avg) ** 2 for m in gw_means) / float(len(gw_means) - 1)
        s1_gw_se = math.sqrt(gw_var / float(len(gw_means)))
        margins[name] = max(0.05 * s1_mean, 1.0 * s1_gw_se)
    return margins


def _guards_from_rows(
    request: dict[str, Any],
    protocol: dict[str, Any],
    rows: dict[tuple[str, str], list[dict[str, Any]]],
    *,
    cluster_by_gw: bool = False,
) -> list[GuardOutput]:
    keys = ("season", "issue_gw", "gameweek_id", "player_id")
    candidate = {tuple(row[key] for key in keys): row for (season, model), values in rows.items() if model == request["candidate_name"] for row in values}
    champion = {tuple(row[key] for key in keys): row for (season, model), values in rows.items() if model == request["former_champion"] for row in values}
    if not candidate or set(candidate) != set(champion) or any(row["_observed"] != champion[key]["_observed"] for key, row in candidate.items()):
        raise ValueError("Projection guards require invariant complete paired forecast/outcome population")
    use_clustering = cluster_by_gw or protocol.get("guard_clustering") == "gameweek"
    guards: list[GuardOutput] = []
    for name, spec in protocol["guard_specs"].items():
        cand_errors: list[float] = []
        champ_errors: list[float] = []
        weights: list[float] = []
        gw_keys: list[tuple[str, int]] = []
        for key, candidate_row in candidate.items():
            outcome = candidate_row["_observed"]
            if protocol["projection_evaluation"]["applicability"][candidate_row["season"]][name] == "inapplicable_native":
                continue
            lead = candidate_row["gameweek_id"] - candidate_row["issue_gw"]
            if lead not in protocol["projection_evaluation"]["leads"]:
                raise ValueError("Projection forecast outside registered horizon leads")
            weights.append(protocol["projection_evaluation"]["weights"][lead])
            gw_keys.append((str(candidate_row["season"]), int(candidate_row["gameweek_id"])))
            for source, errors in ((candidate, cand_errors), (champion, champ_errors)):
                errors.append(_compute_guard_loss(source[key][spec["forecast_field"]], outcome[spec["outcome_field"]], str(spec["loss"])))
        scaling = len(weights) / sum(weights)
        cand_errors = [error * weight * scaling for error, weight in zip(cand_errors, weights, strict=True)]
        champ_errors = [error * weight * scaling for error, weight in zip(champ_errors, weights, strict=True)]
        if use_clustering:
            cand_by_gw: dict[tuple[str, int], list[float]] = {}
            champ_by_gw: dict[tuple[str, int], list[float]] = {}
            for gk, ce, he in zip(gw_keys, cand_errors, champ_errors, strict=True):
                cand_by_gw.setdefault(gk, []).append(ce)
                champ_by_gw.setdefault(gk, []).append(he)
            guards.append(
                evaluate_gw_clustered_non_inferiority_guard(
                    cand_by_gw,
                    champ_by_gw,
                    metric_name=name,
                    meaningful_margin=spec["margin"],
                    alpha=spec["alpha"],
                    direction=cast(MetricDirection, spec["direction"]),
                )
            )
        else:
            guards.append(evaluate_non_inferiority_guard(cand_errors, champ_errors, metric_name=name, meaningful_margin=spec["margin"], alpha=spec["alpha"], direction=cast(MetricDirection, spec["direction"])))
    return guards


def _projection_diagnostics(rows: dict[tuple[str, str], list[dict[str, Any]]]) -> list[dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    for (season, model), forecasts in sorted(rows.items()):
        for lead in sorted({row["gameweek_id"] - row["issue_gw"] for row in forecasts}):
            selected = [row for row in forecasts if row["gameweek_id"] - row["issue_gw"] == lead]
            differences = [row["projected_points"] - row["_observed"]["actual_points"] for row in selected]
            observed_mean = sum(row["_observed"]["actual_points"] for row in selected) / len(selected)
            projected_mean = sum(row["projected_points"] for row in selected) / len(selected)
            mse = sum(error * error for error in differences) / len(differences)
            diagnostics.append({"season": season, "model": model, "horizon_lead": lead, "sample_size": len(selected), "points_mse": mse, "points_rmse": math.sqrt(mse), "points_mae": sum(abs(error) for error in differences) / len(differences), "points_bias": sum(differences) / len(differences), "calibration_ratio": projected_mean / observed_mean if observed_mean != 0 else None})
    return diagnostics


def pair_replay_score(season: str, candidate: ReplayDeadlineRecord, champion: ReplayDeadlineRecord) -> PairedGameweekScore:
    if candidate.deadline != champion.deadline or candidate.outcomes != champion.outcomes or candidate.decision.chip != champion.decision.chip:
        raise ValueError("Compared policies require common deadlines, outcomes and shared chip calendar")
    return PairedGameweekScore(season=season, gameweek=candidate.deadline, candidate_net_points=candidate.net_points, champion_net_points=champion.net_points, candidate_gross_points=candidate.total_gross_points, champion_gross_points=champion.total_gross_points, candidate_hits_deducted=candidate.hit_penalty // 4, champion_hits_deducted=champion.hit_penalty // 4, segment=assign_gameweek_segment(candidate.deadline), is_chip_gameweek=candidate.decision.chip is not None)


def evaluate_replay_evidence(request_path: Path | str) -> dict[str, Any]:
    """Evaluate existing retained outputs; no model fitting, solver or source acquisition."""
    path = Path(request_path).resolve()
    root = path.parent
    request = json.loads(path.read_bytes())
    if request.get("version") != EVIDENCE_VERSION:
        raise ValueError("Unsupported recommendation evidence request")
    candidate, champion = request["candidate_name"], request["former_champion"]
    if not candidate or not champion or candidate == champion:
        raise ValueError("Recommendation must name distinct candidate and Champion")
    source_hash = current_model_source_hash()
    if request["model_source_hash"] != source_hash:
        raise ValueError("Frozen model source changed")
    protocol = _read_material(root, request["protocol"])
    config = protocol_from_payload(protocol)
    if protocol["solver_identity"] != native_solver_identity():
        raise ValueError("Final replay evidence requires the native Strategic transfer solver")
    parameters = _read_material(root, request["parameters"])
    if parameters:
        raise ValueError("Retained forecast generator supports only empty model parameters")
    registry = ConfirmationRegistry(_local_path(root, request["registry_path"]))
    registration = registry.get_attempt(request["confirmation_attempt_id"])
    if registration is None or (registration.candidate_name, registration.champion_name, registration.model_source_hash, registration.parameters_hash, registration.protocol_hash) != (candidate, champion, source_hash, content_hash(parameters), config.compute_hash()):
        raise ValueError("Frozen finalist registration identity mismatch")
    development = _read_material(root, request["development_selection"])
    if registration.dev_selection_record_ref != request["development_selection"]["sha256"] or development.get("candidate_name") != candidate or development.get("former_champion") != champion or development.get("model_source_hash") != source_hash or development.get("protocol_hash") != config.compute_hash():
        raise ValueError("Development finalist-selection reference mismatch")
    _verify_live_readiness(root, _read_material(root, request["live_readiness"]), candidate, champion, config.compute_hash(), source_hash, protocol["live_review"])
    all_records: dict[tuple[str, str], list[ReplayDeadlineRecord]] = {}
    all_rows: dict[tuple[str, str], list[dict[str, Any]]] = {}
    empirical = True
    partial_prefix_seen = False
    disclosed: list[str] = []
    guard_outcomes: dict[tuple[str, int, int], dict[str, Any]] = {}
    guard_windows: set[tuple[str, int]] = set()
    for reference in request["guard_outcome_sources"]:
        season, gw = reference["season"], reference["gameweek"]
        admitted, source_request, source_catalog = _admit_context(_read_material(root, reference["admission"]), season, gw, root=root)
        empirical = empirical and (admitted.mode == "empirical" and admitted.promotable and not admitted.partial_prefix)
        partial_prefix_seen = partial_prefix_seen or (admitted.mode == "empirical" and admitted.partial_prefix)
        for lim in admitted.disclosed_limitations:
            if lim not in disclosed:
                disclosed.append(str(lim))
        if (season, gw) in guard_windows:
            raise ValueError("Duplicate guard outcome source window")
        guard_windows.add((season, gw))
        origin = next(origin for origin in source_request["origins"] if origin["season"] == season and origin["gw"] == gw)
        guard_outcomes.update(finalized_gameweek_outcomes(origin, protocol, catalog=source_catalog))
    expected_guard_windows = {(season, gw) for season, weeks in protocol["windows"].items() for issue in weeks for gw in range(issue, min(39, issue + 6))}
    if guard_windows != expected_guard_windows:
        raise ValueError("Required six-lead guard outcome source coverage missing")
    anchors: dict[str, dict[str, Any]] = {}
    for entry in request["replays"]:
        key = entry["season"], entry["model_name"]
        if key in all_records or key[1] not in (candidate, champion):
            raise ValueError("Duplicate or foreign replay comparison")
        anchor = _read_material(root, entry["anchor"])
        if key[0] == config.development_season and development["traces"].get(key[1]) != entry["trace"]:
            raise ValueError("Final replay differs from frozen development selection evidence")
        if key[0] in anchors and anchors[key[0]] != anchor:
            raise ValueError("Candidate and Champion must share exact neutral anchor")
        anchors[key[0]] = anchor
        records, rows, admitted_empirical = _verify_replay(root, entry, protocol, config, source_hash, guard_outcomes, registration.registered_at)
        all_records[key], all_rows[key] = records, rows
        empirical = empirical and admitted_empirical
    expected = {(season, model) for season in protocol["windows"] for model in (candidate, champion)}
    if set(all_records) != expected:
        raise ValueError("Missing development or confirmation comparator replay")
    scores: list[PairedGameweekScore] = []
    for season in protocol["windows"]:
        for cand, champ in zip(all_records[season, candidate], all_records[season, champion], strict=True):
            scores.append(pair_replay_score(season, cand, champ))
    guards = _guards_from_rows(request, protocol, all_rows)
    result = evaluate_evidence_against_protocol(scores, guards, config, attempt_number=registration.attempt_number_in_family, confirmation_registry=registry, confirmation_attempt_id=registration.attempt_id)
    if not empirical:
        note = (
            "Partial-prefix empirical slice non-promotable for full-season readiness"
            if partial_prefix_seen
            else "Synthetic evidence verifies infrastructure only; empirical admission pending"
        )
        result = replace(result, verdict="inconclusive" if result.verdict == "pass" else result.verdict, reasons=[*result.reasons, note], admitted_limitations=[*result.admitted_limitations, *disclosed, "No production recommendation or adoption authority"])
    elif disclosed:
        result = replace(result, admitted_limitations=[*result.admitted_limitations, *disclosed])
    if registration.status == "completed" and registration.scientific_verdict != result.verdict:
        raise ValueError("Registered terminal verdict differs from reconstructed evidence")
    body = {
        "version": EVIDENCE_VERSION, "candidate_name": candidate, "former_champion": champion,
        "model_source_hash": source_hash, "protocol_hash": config.compute_hash(),
        "scientific_verdict": result.verdict, "execution_status": "complete",
        "empirical_admission": empirical, "request_sha256": sha256(path.read_bytes()).hexdigest(),
        "request_path": path.name, "confirmation_attempt_id": registration.attempt_id,
        "assessment": result.to_dict(), "guards": [asdict(guard) for guard in guards],
        "projection_diagnostics": _projection_diagnostics(all_rows),
    }
    return {**body, "bundle_hash": content_hash(body)}


def write_recommendation_bundle(request_path: Path | str, output_path: Path | str) -> dict[str, Any]:
    path = Path(output_path).resolve()
    request = Path(request_path).resolve()
    if path.parent != request.parent:
        raise ValueError("Recommendation bundle must accompany its retained request")
    bundle = evaluate_replay_evidence(request)
    raw = canonical_bytes(bundle) + b"\n"
    if path.exists() and path.read_bytes() != raw:
        raise ValueError("Refusing to replace frozen recommendation bundle")
    if not path.exists():
        with path.open("xb") as output:
            output.write(raw)
    payload = json.loads(request.read_bytes())
    registry = ConfirmationRegistry(_local_path(request.parent, payload["registry_path"]))
    registration = registry.get_attempt(bundle["confirmation_attempt_id"])
    if registration is not None and registration.status == "in_progress" and registration.execution_status == "complete":
        registry.transition_attempt_status(
            registration.attempt_id,
            "completed",
            scientific_verdict=bundle["scientific_verdict"],
            bundle_path=_relative_bundle_path(registry, path),
        )
    return bundle


def verify_recommendation_bundle(bundle_path: Path | str, *, require_finalized: bool = False) -> dict[str, Any]:
    path = Path(bundle_path).resolve()
    bundle = json.loads(path.read_bytes())
    if not isinstance(bundle, dict) or bundle.get("version") != EVIDENCE_VERSION:
        raise ValueError("Unsupported verified recommendation bundle")
    body = {key: value for key, value in bundle.items() if key != "bundle_hash"}
    if bundle.get("bundle_hash") != content_hash(body):
        raise ValueError("Recommendation bundle hash mismatch")
    request_path = _local_path(path.parent, bundle["request_path"])
    if sha256(request_path.read_bytes()).hexdigest() != bundle["request_sha256"]:
        raise ValueError("Frozen evidence request changed")
    if evaluate_replay_evidence(request_path) != bundle:
        raise ValueError("Recommendation differs from reconstructed evidence")
    if require_finalized:
        request = json.loads(request_path.read_bytes())
        registry = ConfirmationRegistry(_local_path(path.parent, request["registry_path"]))
        registration = registry.get_attempt(bundle["confirmation_attempt_id"])
        if registration is None or registration.status != "completed" or registration.scientific_verdict != bundle["scientific_verdict"]:
            raise ValueError("Confirmation attempt must be finalized with reconstructed verdict before adoption")
    return bundle


@dataclass(frozen=True)
class PodiumCandidateRecord:
    """Two-season qualification record for ADR 0069 Max-2 Podium selection."""

    candidate_name: str
    champion_name: str
    delta_s1: float
    delta_s2: float
    s1_segment_deltas: Mapping[str, float]
    s2_segment_deltas: Mapping[str, float]
    s1_guards_ok: bool
    s2_guards_ok: bool
    s1_segment_tolerances: Mapping[str, float] | None = None
    s2_segment_tolerances: Mapping[str, float] | None = None

    @property
    def mean_two_season_delta(self) -> float:
        return 0.5 * (float(self.delta_s1) + float(self.delta_s2))


@dataclass(frozen=True)
class PodiumFreezeResult:
    podium: tuple[str, ...]
    provisional_active: str | None
    backup_finalist: str | None
    displaced_candidates: tuple[str, ...]
    rejected_candidates: tuple[str, ...]
    updated_selection: ModelSelection


CheckpointAction = Literal[
    "eligible_for_manual_adopt",
    "retain_dual_tier",
    "rotate_to_backup",
    "fallback_to_champion",
]


@dataclass(frozen=True)
class FinalistCheckpointOutcome:
    candidate_name: str
    net_delta: float
    mean_delta: float
    hac_result: KendallPwHacResult
    early_harm: EarlyHarmAssessment
    guards_passed: bool
    superior: bool


@dataclass(frozen=True)
class DualTierCheckpointResult:
    checkpoint_gw: int
    num_finalists: int
    alpha_spent: float | None
    action: CheckpointAction
    recommended_champion: str | None
    next_provisional_active: str | None
    requires_manual_adopt: bool
    outcomes: Mapping[str, FinalistCheckpointOutcome]
    reasons: tuple[str, ...]


def _passes_segment_floors(
    segment_deltas: Mapping[str, float],
    tolerances: Mapping[str, float] | None = None,
) -> bool:
    for seg in ("cold_start", "early_mid", "late"):
        if seg in segment_deltas:
            tol = segment_regression_tolerance(seg, tolerances=tolerances)
            if float(segment_deltas[seg]) < -tol:
                return False
    return True


def rank_and_freeze_podium(
    candidates: Sequence[PodiumCandidateRecord],
    *,
    current_selection: ModelSelection,
    active_season: str,
    seal_slate: bool = False,
) -> PodiumFreezeResult:
    """Rank S-1+S-2 qualified finalists by 0.5*(delta_S1+delta_S2), enforce M<=2 cap & seal."""
    if current_selection.podium_sealed and current_selection.podium_frozen_season == active_season:
        raise ValueError(
            f"Podium slate is sealed for active validation season {active_season}; "
            "M<=2 cap prohibits mid-season finalist additions or displacement"
        )

    qualified: list[PodiumCandidateRecord] = []
    rejected: list[str] = []
    for cand in candidates:
        if cand.champion_name != current_selection.champion or cand.candidate_name == current_selection.champion:
            rejected.append(cand.candidate_name)
            continue
        ok = (
            cand.delta_s1 > 0.0
            and cand.delta_s2 > 0.0
            and cand.s1_guards_ok
            and cand.s2_guards_ok
            and _passes_segment_floors(cand.s1_segment_deltas, cand.s1_segment_tolerances)
            and _passes_segment_floors(cand.s2_segment_deltas, cand.s2_segment_tolerances)
        )
        if ok:
            qualified.append(cand)
        else:
            rejected.append(cand.candidate_name)

    ranked = sorted(
        qualified,
        key=lambda c: (-c.mean_two_season_delta, -float(c.delta_s2), c.candidate_name),
    )
    selected = ranked[:2]
    displaced = tuple(c.candidate_name for c in ranked[2:])
    podium = tuple(c.candidate_name for c in selected)
    provisional_active = podium[0] if podium else None
    backup = podium[1] if len(podium) > 1 else None
    updated = ModelSelection(
        champion=current_selection.champion,
        candidates=podium,
        promotion_status=current_selection.promotion_status,
        schema_version=current_selection.schema_version,
        provisional_active=provisional_active,
        podium_frozen_season=active_season if (seal_slate and podium) else None,
        podium_sealed=bool(seal_slate and podium),
    )
    return PodiumFreezeResult(
        podium=podium,
        provisional_active=provisional_active,
        backup_finalist=backup,
        displaced_candidates=displaced,
        rejected_candidates=tuple(rejected),
        updated_selection=updated,
    )


def evaluate_dual_tier_checkpoint(
    *,
    checkpoint_gw: int,
    finalist_traces: Mapping[str, Sequence[PairedGameweekScore]],
    finalist_guards: Mapping[str, Sequence[GuardOutput]],
    selection: ModelSelection,
    podium_order: Sequence[str],
    protocol_approved: bool = True,
    inapplicable_guards: Sequence[str] = (),
    s1_champion_rows: Sequence[Mapping[str, Any]] | None = None,
) -> DualTierCheckpointResult:
    """Evaluate frozen M<=2 finalists symmetrically at GW15/GW30/GW38 (or intermediate Early-Harm GW>=6)."""
    if type(checkpoint_gw) is not int or not 6 <= checkpoint_gw <= 38:
        raise ValueError(f"Dual-Tier evaluation requires integer GW in [6, 38], got {checkpoint_gw}")
    order = tuple(dict.fromkeys(podium_order))
    m_count = len(order)
    if not 1 <= m_count <= 2:
        raise ValueError(f"Dual-Tier checkpoint requires 1 or 2 frozen finalists, got {m_count}")
    is_obf_checkpoint = checkpoint_gw in (15, 30, 38)
    alpha_spent = obrien_fleming_alpha(checkpoint_gw, num_finalists=m_count) if is_obf_checkpoint else None
    hac_alpha = alpha_spent if alpha_spent is not None else EARLY_HARM_P_THRESHOLD
    required_guards = MANDATORY_GUARDS - set(inapplicable_guards)
    derived_margins = (
        derive_s1_guard_margins(s1_champion_rows, inapplicable_metrics=inapplicable_guards)
        if s1_champion_rows is not None
        else None
    )

    outcomes: dict[str, FinalistCheckpointOutcome] = {}
    for cand in order:
        if cand not in finalist_traces or cand not in finalist_guards:
            raise ValueError(f"Missing active-season scores or guards for finalist '{cand}'")
        scores = sorted(
            [s for s in finalist_traces[cand] if s.gameweek <= checkpoint_gw],
            key=lambda s: s.gameweek,
        )
        gws = [s.gameweek for s in scores]
        if gws != list(range(1, checkpoint_gw + 1)):
            raise ValueError(f"Finalist '{cand}' trace at GW{checkpoint_gw} must cover GW1..{checkpoint_gw}")
        guards = [g for g in finalist_guards[cand] if g.metric_name in required_guards]
        supplied_names = {g.metric_name for g in guards}
        if not required_guards <= supplied_names:
            raise ValueError(f"Finalist '{cand}' missing mandatory projection guards")
        if derived_margins is not None:
            for g in guards:
                if g.metric_name in derived_margins and not math.isclose(g.margin, derived_margins[g.metric_name], rel_tol=1e-6, abs_tol=1e-9):
                    raise ValueError(f"Guard '{g.metric_name}' margin {g.margin} differs from derived S-1 margin {derived_margins[g.metric_name]}")

        harm = evaluate_early_harm_fallback(scores, guards)
        hac = run_kendall_pw_hac_test([s.delta_net for s in scores], alpha=hac_alpha)
        net_delta = float(sum(s.delta_net for s in scores))
        mean_delta = net_delta / float(len(scores))
        guards_pass = all(g.status == "PASS" for g in guards)
        superior = bool(
            protocol_approved
            and alpha_spent is not None
            and hac.point_estimate > 0.0
            and hac.one_sided_lower > 0.0
            and hac.p_value_superiority <= alpha_spent
            and not harm.triggered
            and guards_pass
        )
        outcomes[cand] = FinalistCheckpointOutcome(
            candidate_name=cand,
            net_delta=net_delta,
            mean_delta=mean_delta,
            hac_result=hac,
            early_harm=harm,
            guards_passed=guards_pass,
            superior=superior,
        )

    reasons: list[str] = []
    if selection.provisional_active is None:
        reasons.append("No active Provisional Active finalist (already reverted to Confirmed Champion)")
        return DualTierCheckpointResult(
            checkpoint_gw=checkpoint_gw,
            num_finalists=m_count,
            alpha_spent=alpha_spent,
            action="fallback_to_champion",
            recommended_champion=None,
            next_provisional_active=None,
            requires_manual_adopt=False,
            outcomes=outcomes,
            reasons=tuple(reasons),
        )
    if selection.provisional_active not in order:
        raise ValueError(f"Active provisional model '{selection.provisional_active}' absent from podium {order}")

    active = selection.provisional_active
    active_idx = order.index(active)

    # Only active/downstream finalists remain eligible (a dropped #1 cannot resurrect after #1 -> #2 rotation)
    passing = [cand for cand in order[active_idx:] if outcomes[cand].superior]
    if passing and alpha_spent is not None:
        winner = max(passing, key=lambda c: (outcomes[c].net_delta, -order.index(c)))
        if len(passing) > 1:
            reasons.append(
                f"Simultaneous pass at GW{checkpoint_gw}: '{winner}' won higher S net delta "
                f"({outcomes[winner].net_delta:+.2f} pts)"
            )
        else:
            reasons.append(
                f"'{winner}' cleared OBF alpha={alpha_spent:.5f} at GW{checkpoint_gw} "
                f"(p={outcomes[winner].hac_result.p_value_superiority:.5f}); manual adopt_champion required"
            )
        return DualTierCheckpointResult(
            checkpoint_gw=checkpoint_gw,
            num_finalists=m_count,
            alpha_spent=alpha_spent,
            action="eligible_for_manual_adopt",
            recommended_champion=winner,
            next_provisional_active=winner,
            requires_manual_adopt=True,
            outcomes=outcomes,
            reasons=tuple(reasons),
        )

    active_out = outcomes[active]
    # Strictly one-way rotation: only downstream podium backups (#1 -> #2) eligible; never bounce back to dropped #1
    # At GW15, a trailing backup (#2 net_delta < 0.0) cannot replace #1 in Provisional Active.
    backups = [
        cand
        for cand in order[active_idx + 1 :]
        if not outcomes[cand].early_harm.triggered
        and (checkpoint_gw != 15 or outcomes[cand].net_delta >= 0.0)
    ]

    trail_at_gw15 = checkpoint_gw == 15 and active_out.net_delta < 0.0
    if active_out.early_harm.triggered or trail_at_gw15:
        if backups and checkpoint_gw < 38:
            backup = backups[0]
            why = "Early-Harm Fallback" if active_out.early_harm.triggered else "GW15 trail vs Confirmed Champion"
            reasons.append(f"Rotating Provisional Active '{active}' -> backup '{backup}' ({why})")
            return DualTierCheckpointResult(
                checkpoint_gw=checkpoint_gw,
                num_finalists=m_count,
                alpha_spent=alpha_spent,
                action="rotate_to_backup",
                recommended_champion=None,
                next_provisional_active=backup,
                requires_manual_adopt=False,
                outcomes=outcomes,
                reasons=tuple(reasons),
            )
        reasons.append(f"Reverting Provisional Active '{active}' -> Confirmed Champion '{selection.champion}'")
        return DualTierCheckpointResult(
            checkpoint_gw=checkpoint_gw,
            num_finalists=m_count,
            alpha_spent=alpha_spent,
            action="fallback_to_champion",
            recommended_champion=None,
            next_provisional_active=None,
            requires_manual_adopt=False,
            outcomes=outcomes,
            reasons=tuple(reasons),
        )

    if checkpoint_gw == 38:
        reasons.append("GW38 final checkpoint did not clear <= 5% FWER; resetting Provisional Active cleanly")
        return DualTierCheckpointResult(
            checkpoint_gw=checkpoint_gw,
            num_finalists=m_count,
            alpha_spent=alpha_spent,
            action="fallback_to_champion",
            recommended_champion=None,
            next_provisional_active=None,
            requires_manual_adopt=False,
            outcomes=outcomes,
            reasons=tuple(reasons),
        )

    reasons.append(
        f"'{active}' non-harmful at GW{checkpoint_gw}; retaining Dual-Tier"
    )
    return DualTierCheckpointResult(
        checkpoint_gw=checkpoint_gw,
        num_finalists=m_count,
        alpha_spent=alpha_spent,
        action="retain_dual_tier",
        recommended_champion=None,
        next_provisional_active=active,
        requires_manual_adopt=False,
        outcomes=outcomes,
        reasons=tuple(reasons),
    )


def evaluate_checkpoint_payload(
    payload: Mapping[str, Any], selection: ModelSelection
) -> tuple[DualTierCheckpointResult, dict[str, list[PairedGameweekScore]]]:
    """Use the same score and guard interpretation for checkpoint reports and bundles."""
    checkpoint_gw = int(payload["checkpoint_gw"])
    podium_order = tuple(payload["podium_order"])
    traces: dict[str, list[PairedGameweekScore]] = {}
    for cand, rows in payload["finalist_traces"].items():
        traces[cand] = [
            PairedGameweekScore(
                season=str(row["season"]),
                gameweek=int(row["gameweek"]),
                candidate_net_points=float(row["candidate_net_points"]),
                champion_net_points=float(row["champion_net_points"]),
                candidate_gross_points=float(row.get("candidate_gross_points", row["candidate_net_points"])),
                champion_gross_points=float(row.get("champion_gross_points", row["champion_net_points"])),
                candidate_hits_deducted=int(row.get("candidate_hits_deducted", 0)),
                champion_hits_deducted=int(row.get("champion_hits_deducted", 0)),
                is_chip_gameweek=bool(row.get("is_chip_gameweek", False)),
                segment=assign_gameweek_segment(int(row["gameweek"])),
            )
            for row in rows
        ]
    inapplicable = tuple(payload.get("inapplicable_guards", ()))
    s1_rows = payload.get("s1_champion_rows")
    margins = derive_s1_guard_margins(s1_rows, inapplicable_metrics=inapplicable) if s1_rows is not None else None
    guards: dict[str, list[GuardOutput]] = {}
    if "finalist_guard_errors" in payload:
        for cand, by_metric in payload["finalist_guard_errors"].items():
            guards[cand] = []
            for m_name, gw_pairs in by_metric.items():
                if m_name in inapplicable:
                    continue
                margin = float(margins[m_name]) if margins is not None else float(gw_pairs["margin"])
                guards[cand].append(
                    evaluate_gw_clustered_non_inferiority_guard(
                        gw_pairs["candidate_by_gw"],
                        gw_pairs["champion_by_gw"],
                        metric_name=m_name,
                        meaningful_margin=margin,
                        alpha=float(gw_pairs.get("alpha", 0.05)),
                    )
                )
    else:
        for cand, g_list in payload["finalist_guards"].items():
            guards[cand] = [GuardOutput(**g) for g in g_list]

    result = evaluate_dual_tier_checkpoint(
        checkpoint_gw=checkpoint_gw,
        finalist_traces=traces,
        finalist_guards=guards,
        selection=selection,
        podium_order=podium_order,
        protocol_approved=bool(payload.get("protocol_approved", True)),
        inapplicable_guards=inapplicable,
        s1_champion_rows=s1_rows,
    )
    return result, traces


def evaluate_verified_checkpoint_payload(
    root: Path, payload: Mapping[str, Any], *, finalized_bundle_path: Path | None = None
) -> tuple[DualTierCheckpointResult, dict[str, Any]]:
    """Rebuild the checkpoint from registered, admitted native replay material."""
    lifecycle = load_season_lifecycle()
    season = lifecycle.season_for_role("active_validation")
    development_season = lifecycle.season_for_role("development")
    checkpoint = payload["checkpoint_gw"]
    if type(checkpoint) is not int or checkpoint not in (15, 30, 38):
        raise ValueError("Verified checkpoint must be GW15, GW30 or GW38")
    selection = load_model_selection(_local_path(root, payload["selection_path"]))
    if not selection.podium_sealed or selection.podium_frozen_season != season or not selection.candidates:
        raise ValueError("Verified checkpoint requires the frozen active-season podium")
    champion = selection.champion
    podium = selection.candidates
    attempts = payload["confirmation_attempt_ids"]
    development_refs = payload["development_selections"]
    if set(attempts) != set(podium) or set(development_refs) != set(podium):
        raise ValueError("Verified checkpoint requires registration and development selection for each frozen finalist")

    source_hash = current_model_source_hash()
    if payload["model_source_hash"] != source_hash:
        raise ValueError("Frozen model source changed")
    closure = compute_serving_model_closure((champion, *podium))
    if (
        payload.get("serving_model_closure_hash") is not None
        and payload["serving_model_closure_hash"] != closure.serving_model_closure_hash
    ):
        raise ValueError("Serving model closure changed")
    if (
        payload.get("model_runtime_bindings") is not None
        and payload["model_runtime_bindings"] != closure.model_runtime_bindings
    ):
        raise ValueError("Model runtime bindings mismatch")
    protocol = _read_material(root, payload["protocol"])
    config = protocol_from_payload(protocol)
    protocol_hash = content_hash(protocol)
    if (config.development_season, config.confirmation_season) != (development_season, season):
        raise ValueError("Checkpoint protocol differs from the active season lifecycle")
    s1_mode = protocol.get("s1_guard_baseline_mode")
    disclosed_transition: list[str] = []
    if s1_mode is not None:
        if s1_mode != "s1_guard_baseline_season_archive_transition":
            raise ValueError(f"Unsupported s1_guard_baseline_mode: {s1_mode!r}")
        if season != "2027-28":
            raise ValueError("s1_guard_baseline_season_archive_transition is permitted only for 2027-28")
        disclosed_transition.append("s1_guard_baseline_season_archive_transition")
    if (config.approved_by_human is not True or not isinstance(config.approval_reference, str) or not config.approval_reference.strip()
            or config.approval_reference == "UNAPPROVED" or config.nominal_alpha != 0.05):
        raise ValueError("Approved ADR 0069 checkpoint protocol required")
    review = {"mode": "fplcache", "review_gameweeks": [15, 30, 38], "settlement_delay_hours": 24,
              "early_harm_min_gw": 6, "early_harm_p_threshold": EARLY_HARM_P_THRESHOLD}
    if (protocol["windows"][season] != list(range(1, 39)) or protocol.get("live_review") != review
            or len(protocol["windows"][development_season]) < 2 or set(protocol["guard_specs"]) != MANDATORY_GUARDS
            or any(spec["alpha"] != 0.05 for spec in protocol["guard_specs"].values())):
        raise ValueError("Frozen schedule or guard policy differs from ADR 0069")
    if protocol["solver_identity"] != native_solver_identity():
        raise ValueError("Checkpoint evidence requires the native Strategic transfer solver")

    registry = ConfirmationRegistry(_local_path(root, payload["registry_path"]))
    registrations = {}
    baseline_refs = {}
    for candidate in podium:
        registration = registry.get_attempt(attempts[candidate])
        development_ref = development_refs[candidate]
        development = _read_material(root, development_ref)
        identity = (candidate, champion, source_hash, protocol_hash)
        if (registration is None or registration.dev_selection_record_ref != development_ref["sha256"]
                or (registration.candidate_name, registration.champion_name,
                    registration.model_source_hash, registration.protocol_hash) != identity
                or tuple(development.get(field) for field in ("candidate_name", "former_champion", "model_source_hash", "protocol_hash")) != identity):
            raise ValueError("Frozen checkpoint finalist or development selection mismatch")
        registrations[candidate] = registration
        baseline_refs[candidate] = development.get("traces", {}).get(champion)
    registered_times = [datetime.fromisoformat(registration.registered_at) for registration in registrations.values()]
    if any(value.utcoffset() is None for value in registered_times):
        raise ValueError("Timezone-aware frozen finalist registration required")

    s1_baseline: dict[str, Any] | None = None
    if s1_mode == "s1_guard_baseline_season_archive_transition" and payload.get("s1_guard_baseline") is not None:
        s1_baseline = _read_material(root, payload["s1_guard_baseline"])
        archive_sha = str(s1_baseline.get("archive_manifest_sha256", ""))
        if (
            s1_baseline.get("season") != development_season
            or s1_baseline.get("champion_name") != champion
            or len(archive_sha) != 64
            or any(c not in "0123456789abcdef" for c in archive_sha)
            or not isinstance(s1_baseline.get("rows"), list)
            or not s1_baseline["rows"]
        ):
            raise ValueError("Invalid 2027-28 S-1 Season Archive transition baseline")
        windows = {season: list(range(1, checkpoint + 1))}
    else:
        windows = {**protocol["windows"], season: list(range(1, checkpoint + 1))}
    expected_admissions = {(year, gw) for year, weeks in windows.items() for gw in weeks}
    admission_refs: dict[tuple[str, int], dict[str, Any]] = {}
    guard_outcomes: dict[tuple[str, int, int], dict[str, Any]] = {}
    validation_ref = next((item["admission"] for item in payload["guard_outcome_sources"] if item["season"] == season), None)
    if validation_ref is None:
        raise ValueError("Missing active-season fplcache admission")
    context = _read_material(root, validation_ref)
    request, catalog = _resolve_context_catalog(root, context)
    if request.get("track") != "validation_fplcache" or request.get("checkpoint_gw") != checkpoint:
        raise ValueError("Verified checkpoint requires a matching validation_fplcache request")
    reports = assess_origins(request, catalog, allow_disk_path_fallback=False)
    if ([(row["season"], row["gw"]) for row in reports] != [(season, gw) for gw in windows[season]]
            or not all(row.get("checkpoint_complete") is True and row["status"] == "admitted_empirical" for row in reports)):
        raise ValueError("Incomplete admitted fplcache checkpoint")
    for item in payload["guard_outcome_sources"]:
        year, gw, reference = item["season"], item["gameweek"], item["admission"]
        if (year, gw) not in expected_admissions or (year, gw) in admission_refs:
            raise ValueError("Duplicate or foreign checkpoint admission")
        admission_refs[year, gw] = reference
        if year == season and reference != validation_ref:
            raise ValueError("Active-season policies and outcomes require one shared admitted checkpoint")
        if year == season:
            source_request, source_catalog = request, catalog
        else:
            admitted, source_request, source_catalog = _admit_context(_read_material(root, reference), year, gw, root=root)
            if admitted.mode != "empirical":
                raise ValueError("S-1 guard baseline requires admitted empirical observations")
        origin = next(origin for origin in source_request["origins"] if (origin["season"], origin["gw"]) == (year, gw))
        guard_outcomes.update(finalized_gameweek_outcomes(origin, protocol, catalog=source_catalog))
    if set(admission_refs) != expected_admissions:
        raise ValueError("Incomplete checkpoint or S-1 guard outcome coverage")

    records = {}
    rows = {}
    anchors = {}
    expected_replays = (
        {(season, model) for model in (champion, *podium)}
        if s1_baseline is not None
        else {(development_season, champion), *((season, model) for model in (champion, *podium))}
    )
    replay_protocol = {**protocol, "windows": {**protocol["windows"], season: list(range(1, checkpoint + 1))}}
    for entry in payload["replays"]:
        year, model = entry["season"], entry["model_name"]
        key = year, model
        if key not in expected_replays or key in records:
            raise ValueError("Duplicate or foreign checkpoint replay")
        if [issue["admission"] for issue in entry["issues"]] != [admission_refs[year, gw] for gw in windows[year]]:
            raise ValueError("Replay and guard outcomes must use the same admitted sources")
        if anchors.setdefault(year, entry["anchor"]) != entry["anchor"]:
            raise ValueError("Active-season policies must share the certified neutral opening anchor")
        if year == development_season and any(reference != entry["trace"] for reference in baseline_refs.values()):
            raise ValueError("S-1 Champion baseline differs from frozen finalist selection evidence")
        registered_at = max(registered_times) if year == season else min(registered_times)
        records[key], rows[key], _ = _verify_replay(
            root, entry, replay_protocol, config, source_hash, guard_outcomes, registered_at.isoformat(),
            max_target_gw=windows[year][-1], frozen_protocol_hash=protocol_hash,
        )
    if set(records) != expected_replays:
        raise ValueError("Missing frozen finalist, Champion or S-1 baseline replay")

    traces = {
        candidate: [pair_replay_score(season, cand, champ) for cand, champ in
                    zip(records[season, candidate], records[season, champion], strict=True)]
        for candidate in podium
    }
    margins = derive_s1_guard_margins(
        s1_baseline["rows"] if s1_baseline is not None else rows[development_season, champion],
        weights=protocol["projection_evaluation"]["weights"],
        guard_specs=protocol["guard_specs"],
    )
    guard_protocol = {**protocol, "guard_specs": {
        name: {**spec, "margin": margins[name]} for name, spec in protocol["guard_specs"].items()
    }}
    guards = {
        candidate: _guards_from_rows(
            {"candidate_name": candidate, "former_champion": champion}, guard_protocol,
            {(season, model): rows[season, model] for model in (candidate, champion)}, cluster_by_gw=True,
        )
        for candidate in podium
    }
    result = evaluate_dual_tier_checkpoint(
        checkpoint_gw=checkpoint, finalist_traces=traces, finalist_guards=guards, selection=selection, podium_order=podium,
    )
    winner = result.recommended_champion
    trace_hashes = {candidate: compute_score_trace_hash(scores) for candidate, scores in traces.items()}
    for candidate in podium:
        registry.verify_checkpoint_attempt(
            attempts[candidate], candidate_name=candidate, champion_name=champion, active_season=season,
            checkpoint_gw=checkpoint, model_source_hash=source_hash, parameters_hash=content_hash({}),
            protocol_hash=protocol_hash, score_trace_hash=trace_hashes[candidate], max_family_attempts=config.max_family_attempts,
            finalized_bundle_path=finalized_bundle_path if candidate == winner else None,
        )
    return result, {
        "candidate_name": winner or selection.provisional_active or podium[0], "former_champion": champion,
        "model_source_hash": source_hash,
        "serving_model_closure_hash": closure.serving_model_closure_hash,
        "model_runtime_bindings": closure.model_runtime_bindings,
        "protocol_hash": protocol_hash, "empirical_admission": True,
        "selection_sha256": content_hash(asdict(selection)),
        "admitted_limitations": sorted({*disclosed_transition, *(limitation for row in reports for limitation in row["disclosed_limitations"])}),
        "confirmation_attempt_id": attempts[winner] if winner else None,
        "score_trace_hash": trace_hashes[winner] if winner else None,
    }


def evaluate_checkpoint_bundle_evidence(
    request_path: Path | str, *, finalized_bundle_path: Path | None = None
) -> dict[str, Any]:
    """Reconstruct an ADR 0069 checkpoint recommendation from retained evidence."""
    path = Path(request_path).resolve()
    root = path.parent
    raw_request = path.read_bytes()
    payload = json.loads(raw_request)
    if payload.get("version") == CHECKPOINT_EVIDENCE_V2:
        result, identity = evaluate_verified_checkpoint_payload(root, payload, finalized_bundle_path=finalized_bundle_path)
    elif payload.get("version") == CHECKPOINT_EVIDENCE_VERSION:
        result, identity = _diagnostic_checkpoint_evidence(root, payload)
    else:
        raise ValueError("Unsupported checkpoint recommendation evidence request")
    body = {
        "version": payload["version"],
        "checkpoint_gw": result.checkpoint_gw,
        **identity,
        "scientific_verdict": "pass" if result.action == "eligible_for_manual_adopt" else "inconclusive",
        "execution_status": "complete" if result.action == "eligible_for_manual_adopt" else "partial",
        "action": result.action,
        "recommended_champion": result.recommended_champion,
        "next_provisional_active": result.next_provisional_active,
        "requires_manual_adopt": result.requires_manual_adopt,
        "request_sha256": sha256(raw_request).hexdigest(),
        "request_path": path.name,
        "reasons": list(result.reasons),
    }
    return {**body, "bundle_hash": content_hash(body)}


def _diagnostic_checkpoint_evidence(
    root: Path, payload: Mapping[str, Any]
) -> tuple[DualTierCheckpointResult, dict[str, Any]]:
    selection = (
        load_model_selection(_local_path(root, payload["selection_path"]))
        if payload.get("selection_path")
        else load_model_selection()
    )
    result, traces = evaluate_checkpoint_payload(payload, selection)
    podium_order = payload["podium_order"]
    registry_path = _local_path(root, payload["registry_path"]) if payload.get("registry_path") else None
    attempt_ids: Mapping[str, str] = payload.get("confirmation_attempt_ids") or {}
    winner = result.recommended_champion
    attempt_id = attempt_ids.get(winner) if winner else None
    if registry_path is not None and winner is not None and attempt_id is not None:
        registry = ConfirmationRegistry(registry_path)
        reg = registry.get_attempt(attempt_id)
        expected_hash = compute_score_trace_hash(traces[winner])
        if reg is None or reg.candidate_name != winner or reg.score_trace_hash != expected_hash:
            raise ValueError("Checkpoint registry attempt or score_trace_hash mismatch")

    return result, {
        "candidate_name": winner or (selection.provisional_active or podium_order[0]),
        "former_champion": selection.champion,
        "protocol_hash": str(payload.get("protocol_hash", "")),
        # V1 retains submitted scores and guards, without replay material that can prove admission.
        "empirical_admission": False,
        "confirmation_attempt_id": attempt_id,
    }


def write_checkpoint_recommendation_bundle(request_path: Path | str, output_path: Path | str) -> dict[str, Any]:
    path = Path(output_path).resolve()
    request = Path(request_path).resolve()
    if path.parent != request.parent:
        raise ValueError("Recommendation bundle must accompany its retained request")
    bundle = evaluate_checkpoint_bundle_evidence(request)
    raw = canonical_bytes(bundle) + b"\n"
    if path.exists() and path.read_bytes() != raw:
        raise ValueError("Refusing to replace frozen recommendation bundle")
    if not path.exists():
        with path.open("xb") as output:
            output.write(raw)
    if bundle["version"] == CHECKPOINT_EVIDENCE_V2 and bundle["scientific_verdict"] == "pass":
        payload = json.loads(request.read_bytes())
        registry = ConfirmationRegistry(_local_path(request.parent, payload["registry_path"]))
        attempt = registry.get_attempt(bundle["confirmation_attempt_id"])
        if (attempt is None or attempt.score_trace_hash != bundle["score_trace_hash"]
                or attempt.completed_gameweeks != tuple(range(1, bundle["checkpoint_gw"] + 1))
                or (attempt.model_source_hash, attempt.protocol_hash) != (bundle["model_source_hash"], bundle["protocol_hash"])):
            raise ValueError("Checkpoint registration changed before finalization")
        if attempt.status == "completed":
            if (attempt.execution_status != "complete" or attempt.scientific_verdict != "pass"
                    or not attempt.bundle_path or (registry.registry_file.parent / attempt.bundle_path).resolve() != path):
                raise ValueError("Checkpoint registry was finalized for a different evidence bundle")
        elif bundle["checkpoint_gw"] in (15, 30):
            registry.finalize_early_checkpoint_pass(
                attempt.attempt_id,
                checkpoint_gw=bundle["checkpoint_gw"],
                completed_gameweeks=attempt.completed_gameweeks,
                score_trace_hash=bundle["score_trace_hash"],
                bundle_path=_relative_bundle_path(registry, path),
            )
        else:
            registry.transition_attempt_status(
                attempt.attempt_id,
                "completed",
                scientific_verdict="pass",
                bundle_path=_relative_bundle_path(registry, path),
            )
    return bundle


def verify_checkpoint_recommendation_bundle(bundle_path: Path | str, *, require_finalized: bool = False) -> dict[str, Any]:
    path = Path(bundle_path).resolve()
    bundle = json.loads(path.read_bytes())
    if not isinstance(bundle, dict) or bundle.get("version") not in (CHECKPOINT_EVIDENCE_VERSION, CHECKPOINT_EVIDENCE_V2):
        raise ValueError("Unsupported verified checkpoint recommendation bundle")
    body = {key: value for key, value in bundle.items() if key != "bundle_hash"}
    if bundle.get("bundle_hash") != content_hash(body):
        raise ValueError("Recommendation bundle hash mismatch")
    request_path = _local_path(path.parent, bundle["request_path"])
    if sha256(request_path.read_bytes()).hexdigest() != bundle["request_sha256"]:
        raise ValueError("Frozen evidence request changed")
    finalized_path = path if require_finalized and bundle["version"] == CHECKPOINT_EVIDENCE_V2 else None
    if evaluate_checkpoint_bundle_evidence(request_path, finalized_bundle_path=finalized_path) != bundle:
        raise ValueError("Recommendation differs from reconstructed evidence")
    if require_finalized and bundle["version"] == CHECKPOINT_EVIDENCE_VERSION:
        request = json.loads(request_path.read_bytes())
        registry = ConfirmationRegistry(_local_path(path.parent, request["registry_path"]))
        attempt_id = bundle.get("confirmation_attempt_id")
        if not attempt_id:
            raise ValueError("Confirmation attempt ID required for adoption")
        registration = registry.get_attempt(attempt_id)
        if registration is None or registration.status != "completed" or registration.scientific_verdict != bundle["scientific_verdict"]:
            raise ValueError("Confirmation attempt must be finalized with reconstructed verdict before adoption")
    return bundle


def apply_provisional_action(
    selection: ModelSelection,
    checkpoint: DualTierCheckpointResult,
    *,
    config_path: Path | None = None,
) -> ModelSelection:
    """Apply non-champion Provisional Active rotation/fallback without ever altering Confirmed Champion or mid-season seal."""
    seal = selection.podium_sealed
    updated = ModelSelection(
        champion=selection.champion,
        candidates=selection.candidates,
        promotion_status=selection.promotion_status,
        schema_version=selection.schema_version,
        provisional_active=checkpoint.next_provisional_active,
        podium_frozen_season=selection.podium_frozen_season if seal else None,
        podium_sealed=seal,
    )
    if config_path is not None:
        save_model_selection(updated, config_path)
    return updated
