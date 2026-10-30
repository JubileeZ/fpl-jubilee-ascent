"""Reconstruct candidate recommendations from retained, verified replay evidence."""

from collections.abc import Mapping
from dataclasses import asdict, replace
from datetime import datetime
from hashlib import sha256
import json
import math
from pathlib import Path
from typing import Any, cast

import pandas as pd

from backtesting.confirmation_registry import ConfirmationRegistry
from backtesting.data_admission import AdmittedOrigin, require_admitted, require_input
from backtesting.evaluation_protocol import material_digest
from backtesting.evidence_statistics import (
    PairedGameweekScore,
    StatisticalProtocolConfig,
    assign_gameweek_segment,
    evaluate_evidence_against_protocol,
)
from backtesting.forecast_export import strict_solver_table
from backtesting.forecast_store import load_forecast_verified
from backtesting.ownership_anchor import OwnershipAnchor, compute_universe_digest
from backtesting.projection_guards import GuardOutput, MetricDirection, evaluate_non_inferiority_guard
from backtesting.rolling_replay import (
    QualityPolicy,
    ReplayDeadlineRecord,
    forecast_content_hash,
    record_from_dict,
    refresh_replay_market,
    replay_evaluation_identity,
    replay_solver_identity,
    get_strategic_replay_options,
    verify_replay_record,
    validate_solver_certificate_consistency,
)

EVIDENCE_VERSION = "rolling-promotion-v1"
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


def current_model_source_hash() -> str:
    """Use the retained forecast generator's conservative modeling dependency closure."""
    material: dict[str, bytes] = {}
    for name in ("backtesting", "features", "models", "projections", "solver", "config"):
        directory = PROJECT_ROOT / name
        for path in sorted(directory.rglob("*.py")):
            if not path.resolve().is_relative_to(directory.resolve()):
                raise ValueError("Model source escapes dependency closure")
            material[path.relative_to(PROJECT_ROOT).as_posix()] = path.read_bytes()
    for name in ("pyproject.toml", "uv.lock"):
        material[name] = (PROJECT_ROOT / name).read_bytes()
    return material_digest(material)


def _local_path(root: Path, relative: Any) -> Path:
    if not isinstance(relative, str) or not relative:
        raise ValueError("Missing retained evidence path")
    path = Path(relative)
    result = (root / path).resolve()
    if path.is_absolute() or ".." in path.parts or not result.is_relative_to(root.resolve()):
        raise ValueError("Evidence path must remain within request directory")
    if any(part in {"archive", "2026-27", ".git", ".agents"} for part in result.parts):
        raise ValueError("Protected evidence path")
    return result


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


def _admit_context(context: dict[str, Any], season: str, gw: int) -> tuple[AdmittedOrigin, dict[str, Any], dict[str, bytes]]:
    request = _restore_bytes(context["request"])
    catalog = {digest: bytes.fromhex(raw) for digest, raw in context["catalog"].items()}
    return require_admitted(request, catalog, season, gw), request, catalog


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


def _verify_live_readiness(root: Path, payload: dict[str, Any], candidate: str, champion: str, protocol_hash: str, source_hash: str, frozen_review: dict[str, Any]) -> None:
    from backtesting.live_capture import LiveDeadlineCapture, PlayerForecastSnapshot

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
    identity = replay_evaluation_identity(
        model_name=model, model_version_hash=model_source_hash, protocol_hash=config.compute_hash(),
        season=season, anchor_id=anchor.anchor_id, horizon=6, last_gw=38, scored_end_gw=max(protocol["windows"][season]),
        policy=quality, chip_calendar=tuple(tuple(item) for item in protocol["chip_calendar"]),
        solver_identity=protocol["solver_identity"],
    )
    evidence_rows: list[dict[str, Any]] = []
    empirical = True
    parent_id: str | None = None
    for record, issue in zip(records, entry["issues"], strict=True):
        context = _read_material(root, issue["admission"])
        admitted, request, catalog = _admit_context(context, season, record.deadline)
        empirical = empirical and admitted.mode == "empirical"
        capability = require_input(request, catalog, season, record.deadline)
        origin = next(origin for origin in request["origins"] if origin["season"] == season and origin["gw"] == record.deadline)
        if record.deadline == 1:
            universe = pd.DataFrame(origin["players"]).rename(columns={"id": "player_id", "club": "club_id", "position": "position_id", "price": "now_cost", "ownership": "selected_by_percent", "eligible": "is_eligible"})
            if anchor.source_digest != compute_universe_digest(universe):
                raise ValueError("Neutral anchor differs from admitted opening universe")
            selected = {player["id"]: player for player in origin["players"] if player["id"] in anchor.player_ids}
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
        if generation_time.utcoffset() is None or (season == config.confirmation_season and generation_time < registration_time):
            raise ValueError("Confirmation forecast predates frozen finalist registration")
        if season == config.development_season and generation_time >= registration_time:
            raise ValueError("Development selection evidence must precede finalist registration")
        wide = strict_solver_table(predictions, capability, request, catalog)
        wide = wide.rename(columns={"club": "club_id", "position": "position_id", "price": "now_cost"})
        eligibility = {player["id"]: player["eligible"] for player in origin["players"]}
        wide["purchase_eligible"] = wide["player_id"].map(lambda pid: eligibility[pid])
        if record.forecast_hash != forecast_content_hash(wide) or record.evaluation_identity != identity:
            raise ValueError("Replay does not bind verified forecasts and frozen policy")
        if record.model_version_hash != model_source_hash or record.protocol_hash != config.compute_hash():
            raise ValueError("Replay model or protocol identity mismatch")
        if material["model"] != model or material["input_digest"] != capability.input_digest:
            raise ValueError("Forecast model or admitted input mismatch")
        if material["model_parameters"] != {}:
            raise ValueError("Unsupported forecast generator parameterization")
        if record.outcomes.source_identity != admitted.evidence_digest:
            raise ValueError("Scored outcomes do not bind admitted source closure")
        source_points: dict[int, float] = {pid: 0.0 for pid in origin["universe"]}
        source_minutes: dict[int, float] = {pid: 0.0 for pid in origin["universe"]}
        for outcome in origin["outcomes"]:
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
        if (record.execution_status != "SUCCESS" or not certificate.feasible or certificate.quality_mode != quality.mode
                or certificate.termination_status != "OPTIMAL" or certificate.relative_gap > quality.target_gap
                or certificate.threads != 1 or certificate.seed != 42 or certificate.runtime_seconds > quality.time_limit_seconds):
            raise ValueError("Replay lacks required solver-quality certificate")
        if "lineup" in record.certificate.solver_version or "dry_run" in record.certificate.solver_version:
            raise ValueError("Diagnostic solver cannot produce final promotion evidence")
        expected_options = get_strategic_replay_options(min(6, 39 - record.deadline), rules_version=season)
        if any(record.certificate.strategic_audit.get(key) != value for key, value in expected_options.items()):
            raise ValueError("Effective solver policy differs from frozen Strategic baseline")
        if record.decision.chip != dict(protocol["chip_calendar"]).get(record.deadline):
            raise ValueError("Replay chip differs from registered shared calendar")
        state = refresh_replay_market(state, wide)
        state = verify_replay_record(record, state, model_name=model, parent_checkpoint_id=parent_id)
        parent_id = record.checkpoint_id
        evidence_rows.extend(group_projection_gameweeks(predictions, season, record.deadline, guard_outcomes))
    return records, evidence_rows, empirical


def group_projection_gameweeks(predictions: pd.DataFrame, season: str, issue_gw: int, outcomes: dict[tuple[str, int, int], dict[str, Any]]) -> list[dict[str, Any]]:
    """Score issue-known fixture sums against complete finalized player/GW outcomes."""
    columns = ["projected_points", "projected_minutes", *{semantics[0] for semantics in GUARD_SEMANTICS.values() if semantics[0].startswith("xp_")}]
    grouped = cast(pd.DataFrame, predictions.groupby(["player_id", "gameweek_id"], as_index=False)[columns].sum())
    result: list[dict[str, Any]] = []
    for row in grouped.to_dict(orient="records"):
        native = outcomes.get((season, row["gameweek_id"], row["player_id"]))
        if native is None:
            raise ValueError("Missing complete finalized player/gameweek component outcomes")
        result.append({**row, "season": season, "issue_gw": issue_gw, "_observed": native})
    return result


def finalized_gameweek_outcomes(origin: dict[str, Any], protocol: dict[str, Any]) -> dict[tuple[str, int, int], dict[str, Any]]:
    """Only call after independent native outcome admission proves complete coverage."""
    season, gw = origin["season"], origin["gw"]
    fields = {spec["outcome_field"] for spec in protocol["guard_specs"].values()}
    totals = {(season, gw, pid): {field: 0.0 for field in fields} for pid in origin["universe"]}
    for row in origin["outcomes"]:
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


def _guards_from_rows(request: dict[str, Any], protocol: dict[str, Any], rows: dict[tuple[str, str], list[dict[str, Any]]]) -> list[GuardOutput]:
    keys = ("season", "issue_gw", "gameweek_id", "player_id")
    candidate = {tuple(row[key] for key in keys): row for (season, model), values in rows.items() if model == request["candidate_name"] for row in values}
    champion = {tuple(row[key] for key in keys): row for (season, model), values in rows.items() if model == request["former_champion"] for row in values}
    if not candidate or set(candidate) != set(champion) or any(row["_observed"] != champion[key]["_observed"] for key, row in candidate.items()):
        raise ValueError("Projection guards require invariant complete paired forecast/outcome population")
    guards: list[GuardOutput] = []
    for name, spec in protocol["guard_specs"].items():
        cand_errors: list[float] = []
        champ_errors: list[float] = []
        weights: list[float] = []
        for key, candidate_row in candidate.items():
            outcome = candidate_row["_observed"]
            if protocol["projection_evaluation"]["applicability"][candidate_row["season"]][name] == "inapplicable_native":
                continue
            lead = candidate_row["gameweek_id"] - candidate_row["issue_gw"]
            if lead not in protocol["projection_evaluation"]["leads"]:
                raise ValueError("Projection forecast outside registered horizon leads")
            weights.append(protocol["projection_evaluation"]["weights"][lead])
            for source, errors in ((candidate, cand_errors), (champion, champ_errors)):
                predicted, realized = source[key][spec["forecast_field"]], outcome[spec["outcome_field"]]
                if type(predicted) not in (int, float) or type(realized) not in (int, float) or not math.isfinite(predicted) or not math.isfinite(realized):
                    raise ValueError("Missing or nonfinite required projection evidence")
                delta = predicted - realized
                if spec["loss"] == "squared_error":
                    errors.append(delta * delta)
                elif spec["loss"] == "absolute_error":
                    errors.append(abs(delta))
                elif spec["loss"] == "signed_error":
                    errors.append(delta)
                else:
                    raise ValueError("Unknown predefined guard loss")
        scaling = len(weights) / sum(weights)
        cand_errors = [error * weight * scaling for error, weight in zip(cand_errors, weights, strict=True)]
        champ_errors = [error * weight * scaling for error, weight in zip(champ_errors, weights, strict=True)]
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
    guard_outcomes: dict[tuple[str, int, int], dict[str, Any]] = {}
    guard_windows: set[tuple[str, int]] = set()
    for reference in request["guard_outcome_sources"]:
        season, gw = reference["season"], reference["gameweek"]
        admitted, source_request, _ = _admit_context(_read_material(root, reference["admission"]), season, gw)
        empirical = empirical and admitted.mode == "empirical"
        if (season, gw) in guard_windows:
            raise ValueError("Duplicate guard outcome source window")
        guard_windows.add((season, gw))
        origin = next(origin for origin in source_request["origins"] if origin["season"] == season and origin["gw"] == gw)
        guard_outcomes.update(finalized_gameweek_outcomes(origin, protocol))
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
        result = replace(result, verdict="inconclusive" if result.verdict == "pass" else result.verdict, reasons=[*result.reasons, "Synthetic evidence verifies infrastructure only; empirical admission pending"], admitted_limitations=[*result.admitted_limitations, "No production recommendation or adoption authority"])
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
        registry.transition_attempt_status(registration.attempt_id, "completed", scientific_verdict=bundle["scientific_verdict"], bundle_path=str(path))
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
