"""Portable checkpoint evidence producer CLI (`collect`, `freeze`, `replay`, `bootstrap-s1-baseline`)."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import UTC, datetime
import csv
import hashlib
import io
import json
import lzma
from pathlib import Path
import re
import sys
from typing import Any, cast

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backtesting.confirmation_registry import ConfirmationRegistry
from backtesting.data_admission import require_admitted, require_input
from backtesting.empirical_admission import assess_empirical_origins
from backtesting.empirical_mirrors import parse_fixtures_csv_window
from backtesting.evidence_statistics import (
    EARLY_HARM_P_THRESHOLD,
    StatisticalProtocolConfig,
    compute_score_trace_hash,
)
from backtesting.forecast_export import strict_solver_table
from backtesting.forecast_store import generate_forecast
from backtesting.fplcache_ingest import _sanitize_bootstrap, _utc
from backtesting.ownership_anchor import OwnershipAnchor, solve_ownership_anchor
from backtesting.portable_evidence import (
    BlobStore,
    ExclusionLedger,
    GapStatus,
    VerificationScorecard,
    compute_evaluator_code_hash,
    compute_serving_model_closure,
    get_producer_git_sha,
    pack_checkpoint_snapshot,
    validate_relative_posix_path,
    write_scorecard,
)
from backtesting.promotion_evidence import (
    GUARD_SEMANTICS,
    CHECKPOINT_EVIDENCE_V2,
    _extract_origin_players_and_outcomes,
    canonical_bytes,
    content_hash,
    current_model_source_hash,
    native_solver_identity,
    pair_replay_score,
    write_checkpoint_recommendation_bundle,
)
from backtesting.replay_state import Outcome, OutcomeBatch
from backtesting.rolling_replay import (
    QualityPolicy,
    ReplayDeadlineRecord,
    record_to_dict,
    run_rolling_replay,
    validate_quality_policy_gate,
)
from backtesting.season_rules import Chip, load_season_lifecycle
from models.selection import ModelSelection, load_model_selection, save_model_selection

_TRANSIENT_REASONS = frozenset(
    {
        "bootstrap_bytes_missing",
        "fixtures_bytes_missing",
        "history_bytes_missing",
        "seed_bytes_missing",
        "outcomes_bytes_missing",
        "bootstrap_missing",
        "fixtures_missing",
        "history_missing",
        "seed_missing",
        "outcomes_missing",
        "outcomes:premature_settlement_lt_24h",
        "outcomes:fixture_unfinished",
        "outcomes:prospective_data_unchecked",
        "outcomes:awaiting_bootstrap",
    }
)


def _write_rel_json(root: Path, relpath: str, payload: Any) -> dict[str, str]:
    rel = validate_relative_posix_path(relpath)
    dest = (root / rel).resolve()
    if not dest.is_relative_to(root.resolve()):
        raise ValueError(f"Path escapes evidence root: {relpath!r}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    raw = canonical_bytes(payload) + b"\n"
    dest.write_bytes(raw)
    return {"path": rel, "sha256": hashlib.sha256(raw).hexdigest()}


def _build_scorecard(
    root: Path,
    *,
    slate_id: str,
    season: str,
    checkpoint_gw: int,
    settled_through_gw: int,
    gap_status: GapStatus,
    first_blocked_gw: int | None,
    reason_codes: tuple[str, ...],
    cumulative_net_points: dict[str, float] | None = None,
    weekly_leader: str | None = None,
    checkpoint_action: str | None = None,
    bundle_hash: str | None = None,
) -> VerificationScorecard:
    slate_file = root / "slate.json"
    slate_obj = json.loads(slate_file.read_bytes()) if slate_file.is_file() else {}
    sel_file = root / "selection.json"
    sel_obj = load_model_selection(sel_file) if sel_file.is_file() else None
    excl_file = root / "exclusions.jsonl"
    exclusions = ExclusionLedger(excl_file).excluded_candidates(season=season) if excl_file.is_file() else frozenset()
    return VerificationScorecard(
        season=season,
        checkpoint_gw=checkpoint_gw,
        slate_id=str(slate_obj.get("slate_id", slate_id)),
        slate_sealed=slate_file.is_file(),
        confirmed_champion=str(slate_obj.get("champion") or (sel_obj.champion if sel_obj else "")),
        podium_order=tuple(str(x) for x in slate_obj.get("candidates", sel_obj.candidates if sel_obj else ())),
        provisional_active=sel_obj.provisional_active if sel_obj else None,
        serving_model_closure_hash=str(slate_obj.get("serving_model_closure_hash", "")),
        model_runtime_bindings=dict(slate_obj.get("model_runtime_bindings", {})),
        evaluator_code_hash=str(slate_obj.get("evaluator_code_hash") or compute_evaluator_code_hash()),
        producer_git_sha=str(slate_obj.get("producer_git_sha") or get_producer_git_sha()),
        settled_through_gw=settled_through_gw,
        gap_status=gap_status,
        first_blocked_gw=first_blocked_gw,
        reason_codes=reason_codes,
        cumulative_net_points=cumulative_net_points or {},
        weekly_leader=weekly_leader,
        active_exclusions=tuple(sorted(exclusions)),
        generated_at=datetime.now(UTC).isoformat(),
        checkpoint_action=checkpoint_action,
        bundle_hash=bundle_hash,
    )


def _classify_gap_status(reasons: list[str], *, missing_gw: bool = False) -> GapStatus:
    if missing_gw:
        return "transient_gap"
    if not reasons:
        return "permanent_gap"
    return "transient_gap" if all(reason in _TRANSIENT_REASONS for reason in reasons) else "permanent_gap"


def _resolve_context_bytes(root: Path, context: dict[str, Any]) -> tuple[dict[str, Any], dict[str, bytes]]:
    store = BlobStore(root)
    catalog: dict[str, bytes] = {}
    for key, val in context["catalog"].items():
        if isinstance(val, str):
            catalog[str(key)] = bytes.fromhex(val)
        elif isinstance(val, dict):
            sha = str(val["blob_sha256"])
            rel = str(val.get("relpath") or val.get("path") or f"blobs/{sha}")
            catalog[str(key)] = store.read_bytes(rel, expected_sha256=sha)
        else:
            raise ValueError(f"Unsupported catalog entry type for {key!r}")
    return context["request"], catalog


def _assess_season_admissions(
    root: Path,
    season: str,
) -> tuple[dict[int, tuple[dict[str, Any], dict[str, bytes], dict[str, Any]]], int, int | None, GapStatus, list[str]]:
    adm_dir = root / "admissions" / season
    if not adm_dir.is_dir():
        return {}, 0, 1, "transient_gap", [f"missing_season_admissions:{season}"]
    files = sorted(p for p in adm_dir.glob("gw*.json") if p.is_file())
    if not files:
        return {}, 0, 1, "transient_gap", [f"empty_season_admissions:{season}"]

    # Load latest cumulative prefix context and per-gw records
    latest_ctx = json.loads(files[-1].read_text(encoding="utf-8"))
    request, catalog = _resolve_context_bytes(root, latest_ctx)
    reports = assess_empirical_origins(request, catalog, allow_disk_path_fallback=False)
    by_gw: dict[int, dict[str, Any]] = {int(rep["gw"]): rep for rep in reports}
    admitted_gws: dict[int, tuple[dict[str, Any], dict[str, bytes], dict[str, Any]]] = {}
    max_gw = max(by_gw) if by_gw else 0
    prefix_end = 0
    first_blocked: int | None = None
    gap_status: GapStatus = "complete"
    gap_reasons: list[str] = []

    for gw in range(1, max_gw + 1):
        rep = by_gw.get(gw)
        if rep is None:
            first_blocked = gw
            gap_status = "transient_gap"
            gap_reasons = [f"missing_gw:{gw}"]
            break
        if rep.get("status") != "admitted_empirical":
            first_blocked = gw
            gap_reasons = [str(r) for r in rep.get("reasons", [])]
            gap_status = _classify_gap_status(gap_reasons)
            break
        prefix_end = gw
        admitted_gws[gw] = (request, catalog, rep)
    return admitted_gws, prefix_end, first_blocked, gap_status, gap_reasons


def _collect_command(args: argparse.Namespace) -> int:
    root = Path(args.evidence_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    store = BlobStore(root)
    batch_path = Path(args.batch_json).resolve()
    batch = json.loads(batch_path.read_text(encoding="utf-8"))

    season = str(batch["season"])
    track = str(batch["track"])
    purpose = str(batch.get("purpose", "validation"))
    checkpoint_gw = batch.get("checkpoint_gw")
    origins_in = sorted(batch["origins"], key=lambda o: int(o["gw"]))

    ext_catalog: dict[str, dict[str, str]] = {}
    raw_catalog: dict[str, bytes] = {}
    req_origins: list[dict[str, Any]] = []

    adm_dir = root / "admissions" / season
    adm_dir.mkdir(parents=True, exist_ok=True)

    for origin in origins_in:
        gw = int(origin["gw"])
        sources_out: dict[str, dict[str, Any]] = {}
        for role, spec in origin["sources"].items():
            file_rel = spec.get("file")
            if isinstance(file_rel, str) and file_rel:
                raw = (batch_path.parent / file_rel).read_bytes()
            elif "source_id" in spec and isinstance(spec.get("path"), str):
                raw = Path(spec["path"]).read_bytes()
            else:
                raise ValueError(f"Collector origin GW{gw} role '{role}' lacks source bytes path")
            blob_sha = store.write_bytes(raw)
            sid = f"{season}_gw{gw:02d}_{role}_{blob_sha[:12]}"
            ext_catalog[sid] = {"blob_sha256": blob_sha, "relpath": store.relpath(blob_sha)}
            raw_catalog[sid] = raw
            sources_out[role] = {
                **{k: v for k, v in spec.items() if k not in ("file", "path")},
                "source_id": sid,
            }
        req_origins.append(
            {
                "season": season,
                "gw": gw,
                "deadline": origin["deadline"],
                "prev_deadline": origin.get("prev_deadline"),
                "max_kickoff_utc": origin["max_kickoff_utc"],
                "disclosed_limitations": origin.get("disclosed_limitations", []),
                "sources": sources_out,
            }
        )
        req_prefix = {
            "version": 2,
            "mode": "empirical",
            "track": track,
            "season": season,
            "purpose": purpose,
            "checkpoint_gw": checkpoint_gw,
            "eligibility_policy": "empirical-v2",
            "partial_prefix": False,
            "full_season_required": False,
            "shared_chip_calendar": batch.get("shared_chip_calendar", []),
            "anchor": batch.get("anchor", {}),
            "origins": list(req_origins),
        }
        ctx_path = adm_dir / f"gw{gw:02d}.json"
        ctx_payload = {"request": req_prefix, "catalog": dict(ext_catalog)}
        ctx_path.write_bytes(canonical_bytes(ctx_payload) + b"\n")

    _, prefix_end, first_blocked, gap_status, gap_reasons = _assess_season_admissions(root, season)
    max_gw = max((int(o["gw"]) for o in req_origins), default=0)
    scorecard = _build_scorecard(
        root,
        slate_id=str(args.slate_id),
        season=season,
        checkpoint_gw=max_gw,
        settled_through_gw=prefix_end,
        gap_status=gap_status,
        first_blocked_gw=first_blocked,
        reason_codes=tuple(gap_reasons),
    )
    write_scorecard(root, scorecard)
    print(
        json.dumps(
            {
                "command": "collect",
                "season": season,
                "settled_through_gw": prefix_end,
                "gap_status": gap_status,
                "first_blocked_gw": first_blocked,
                "reason_codes": gap_reasons,
            },
            sort_keys=True,
        )
    )
    return 0


def _build_default_protocol(
    *,
    development_season: str,
    validation_season: str,
    approval_reference: str,
    dev_windows: list[int],
    time_limit_seconds: float,
    max_family_attempts: int,
    s1_guard_baseline_mode: str | None = None,
) -> dict[str, Any]:
    guards = {
        name: {
            "forecast_field": spec[0],
            "outcome_field": spec[1],
            "loss": spec[2],
            "units": spec[3],
            "margin": 0.0,
            "alpha": 0.05,
            "direction": "lower_is_better",
        }
        for name, spec in GUARD_SEMANTICS.items()
    }
    windows = {
        development_season: list(dev_windows),
        validation_season: list(range(1, 39)),
    }
    protocol: dict[str, Any] = {
        "horizon": 6,
        "windows": windows,
        "guard_specs": guards,
        "quality_policy": asdict(QualityPolicy(mode="certified", target_gap=0.0, time_limit_seconds=time_limit_seconds)),
        "chip_calendar": [[3, "triple_captain"], [25, "wildcard"]],
        "solver_identity": native_solver_identity(),
        "projection_evaluation": {
            "leads": list(range(6)),
            "weights": [1.0] * 6,
            "population": "all_admitted_players",
            "missingness": "fail_closed",
            "aggregation": "weighted_paired_player_gameweek",
            "applicability": {s: dict.fromkeys(guards, "required") for s in windows},
        },
        "live_review": {
            "mode": "fplcache",
            "review_gameweeks": [15, 30, 38],
            "settlement_delay_hours": 24,
            "early_harm_min_gw": 6,
            "early_harm_p_threshold": EARLY_HARM_P_THRESHOLD,
        },
    }
    if s1_guard_baseline_mode is not None:
        protocol["s1_guard_baseline_mode"] = s1_guard_baseline_mode
    protocol["statistics"] = StatisticalProtocolConfig(
        development_season=development_season,
        confirmation_season=validation_season,
        approved_by_human=True,
        approval_reference=approval_reference,
        max_family_attempts=max_family_attempts,
        required_projection_guards=tuple(guards),
        evidence_protocol_hash=content_hash(protocol),
    ).to_dict()
    return protocol


def _parse_fixtures_with_difficulty(raw_bytes: bytes, gw: int, *, horizon: int = 6) -> list[dict[str, Any]]:
    rows = parse_fixtures_csv_window(raw_bytes, gw, horizon=horizon)
    diff_by_id: dict[int, tuple[int, int]] = {}
    for raw_row in csv.DictReader(io.StringIO(raw_bytes.decode("utf-8-sig"))):
        if raw_row.get("id"):
            diff_by_id[int(raw_row["id"])] = (
                int(raw_row.get("team_h_difficulty") or 3),
                int(raw_row.get("team_a_difficulty") or 3),
            )
    return [
        {
            **row,
            "team_h_difficulty": diff_by_id.get(int(row["id"]), (3, 3))[0],
            "team_a_difficulty": diff_by_id.get(int(row["id"]), (3, 3))[1],
        }
        for row in rows
    ]


def _replay_season_prefix(
    root: Path,
    *,
    season: str,
    model_name: str,
    admitted_gws: dict[int, tuple[dict[str, Any], dict[str, bytes], dict[str, Any]]],
    end_gw: int,
    source_hash: str,
    protocol_hash: str,
    policy: QualityPolicy,
) -> tuple[dict[str, str], list[ReplayDeadlineRecord], list[dict[str, Any]], dict[str, str]]:
    req_gws = sorted(gw for gw in admitted_gws if gw <= end_gw)
    if req_gws != list(range(1, end_gw + 1)):
        raise ValueError(f"Incomplete admitted origins for {season} GW1..{end_gw}")

    req1, cat1, _ = admitted_gws[1]
    require_admitted(req1, cat1, season, 1, allow_disk_path_fallback=False)
    origin1 = next(o for o in req1["origins"] if o["season"] == season and o["gw"] == 1)
    players1, _ = _extract_origin_players_and_outcomes(origin1, cat1)
    universe_df = pd.DataFrame(players1).rename(
        columns={
            "id": "player_id",
            "club": "club_id",
            "position": "position_id",
            "price": "now_cost",
            "ownership": "selected_by_percent",
            "eligible": "is_eligible",
        }
    )
    anchor_rel = f"anchors/{season}.json"
    anchor_file = root / anchor_rel
    if anchor_file.is_file():
        anchor = OwnershipAnchor.from_dict(json.loads(anchor_file.read_bytes()))
        anchor_ref = {"path": anchor_rel, "sha256": hashlib.sha256(anchor_file.read_bytes()).hexdigest()}
    else:
        anchor = solve_ownership_anchor(universe_df, season=season)
        anchor_ref = _write_rel_json(root, anchor_rel, anchor.to_dict())

    forecast_cache_rel = f"forecast_cache/{season}-{model_name}"
    forecast_cache = root / forecast_cache_rel
    forecast_cache.mkdir(parents=True, exist_ok=True)
    chip_calendar = cast(
        tuple[tuple[int, Chip], ...],
        tuple(
            (int(item["gameweek"]), str(item["chip"]))
            if isinstance(item, dict)
            else (int(item[0]), str(item[1]))
            for item in req1.get("shared_chip_calendar", [])
        ),
    )

    issues: list[dict[str, Any]] = []
    frames_by_gw: dict[int, pd.DataFrame] = {}
    outcomes_by_gw: dict[int, OutcomeBatch] = {}

    for gw in req_gws:
        request, catalog, _ = admitted_gws[gw]
        adm_rel = f"admissions/{season}/gw{gw:02d}.json"
        if not (root / adm_rel).is_file():
            adm_files = sorted((root / "admissions" / season).glob("gw*.json"))
            adm_rel = f"admissions/{season}/{adm_files[-1].name}"
        adm_ref = {"path": adm_rel, "sha256": hashlib.sha256((root / adm_rel).read_bytes()).hexdigest()}
        cap = require_input(request, catalog, season, gw, allow_disk_path_fallback=False)
        origin = next(o for o in request["origins"] if o["season"] == season and o["gw"] == gw)
        auth_obj = {
            "version": 2,
            "mode": "empirical",
            "track": cap.track,
            "input_digest": cap.input_digest,
            "season": season,
            "gw": gw,
            "seed_identity": origin["sources"]["seed"].get("url", f"seed:{season}"),
            "source_digest": origin["sources"]["seed"]["blob_sha256"],
        }
        bs_raw = catalog[origin["sources"]["bootstrap"]["source_id"]]
        bs_payload = json.loads(lzma.decompress(bs_raw).decode("utf-8"))

        cap_up = _utc(origin["sources"]["bootstrap"]["capture_upper"])
        sanitized_bs, _, _ = _sanitize_bootstrap(bs_payload, capture_upper=cap_up)
        fx_dec = catalog[origin["sources"]["fixtures"]["source_id"]]
        fx_rows = _parse_fixtures_with_difficulty(fx_dec, gw)
        hist_rows = json.loads(catalog[origin["sources"]["history"]["source_id"]].decode("utf-8"))
        seed_obj = json.loads(catalog[origin["sources"]["seed"]["source_id"]].decode("utf-8"))
        # Build history_fixtures strictly pre-deadline from prior origins or synthetic completion
        hist_fx: list[dict[str, Any]] = []
        for prev_gw in range(1, gw):
            prev_req, prev_cat, _ = admitted_gws[prev_gw]
            prev_or = next(o for o in prev_req["origins"] if o["season"] == season and o["gw"] == prev_gw)
            for fx in _parse_fixtures_with_difficulty(prev_cat[prev_or["sources"]["fixtures"]["source_id"]], prev_gw):
                if int(fx["event"]) == prev_gw:
                    hist_fx.append(
                        {
                            "id": int(fx["id"]),
                            "gameweek_id": int(fx["event"]),
                            "home_club_id": int(fx["team_h"]),
                            "away_club_id": int(fx["team_a"]),
                            "finished": True,
                            "kickoff_time": fx["kickoff_time"],
                            "team_h_difficulty": int(fx["team_h_difficulty"]),
                            "team_a_difficulty": int(fx["team_a_difficulty"]),
                        }
                    )
        # Reconstruct seed_fixtures from seed_history fixture IDs
        seed_fx_seen: set[int] = set()
        seed_fx: list[dict[str, Any]] = []
        for srow in seed_obj.get("history", []):
            sfid = int(srow.get("fixture_id", 0))
            if sfid > 0 and sfid not in seed_fx_seen:
                seed_fx_seen.add(sfid)
                seed_fx.append(
                    {
                        "id": sfid,
                        "gameweek_id": int(srow.get("gameweek_id", 1)),
                        "home_club_id": 1,
                        "away_club_id": 2,
                        "finished": True,
                        "kickoff_time": str(srow.get("kickoff_time", origin["deadline"])),
                        "team_h_difficulty": 3,
                        "team_a_difficulty": 3,
                    }
                )
        src_bundle = {
            "mode": "empirical",
            "track": cap.track,
            "url": origin["sources"]["seed"]["url"],
            "revision": str(origin["sources"]["seed"].get("commit_sha", "a" * 40)),
            "parser_version": "empirical-v2",
            "captured_at": origin["sources"]["bootstrap"]["capture_upper"],
            "defensive_contribution_status": seed_obj.get("defensive_contribution_status", "native"),
            "disclosed_limitations": list(cap.disclosed_limitations),
            "seed_mapping": seed_obj["seed_mapping"],
            "tables": {
                "clubs": [
                    {"id": int(t["id"]), "strength": int(t.get("strength", 1000) or 1000), "short_name": str(t["short_name"])}
                    for t in bs_payload["teams"]
                ],
                "player_metadata": [
                    {
                        "id": int(e["id"]),
                        "code": e.get("code"),
                        "club_id": int(e["team"]),
                        "position_id": int(e["element_type"]),
                        "now_cost": int(e["now_cost"]),
                        "first_name": e.get("first_name", ""),
                        "second_name": e.get("second_name", ""),
                        "web_name": e.get("web_name", ""),
                        "status": e.get("status", "a"),
                        "chance_of_playing_next_round": e.get("chance_of_playing_next_round"),
                    }
                    for e in sanitized_bs
                ],
                "target_fixtures": [
                    {
                        "id": int(fx["id"]),
                        "gameweek_id": int(fx["event"]),
                        "home_club_id": int(fx["team_h"]),
                        "away_club_id": int(fx["team_a"]),
                        "kickoff_time": fx["kickoff_time"],
                        "team_h_difficulty": int(fx["team_h_difficulty"]),
                        "team_a_difficulty": int(fx["team_a_difficulty"]),
                    }
                    for fx in fx_rows
                ],
                "history": hist_rows,
                "history_fixtures": hist_fx,
                "seed_players": seed_obj["players"],
                "seed_history": seed_obj["history"],
                "seed_fixtures": seed_fx,
            },
        }
        store = BlobStore(root)
        local_cat = dict(catalog)
        src_bytes = canonical_bytes(src_bundle)
        src_digest = hashlib.sha256(src_bytes).hexdigest()
        src_blob_sha = store.write_bytes(src_bytes)
        local_cat[src_digest] = src_bytes
        auth_obj["source_digest"] = src_digest
        auth_bytes = canonical_bytes(auth_obj)
        auth_digest = hashlib.sha256(auth_bytes).hexdigest()
        auth_blob_sha = store.write_bytes(auth_bytes)
        local_cat[auth_digest] = auth_bytes

        # Persist externalized training blobs into the referenced admission context for offline snapshot verification.
        adm_file = root / adm_rel
        adm_ctx = json.loads(adm_file.read_bytes())
        src_ref = {"blob_sha256": src_blob_sha, "relpath": store.relpath(src_blob_sha)}
        auth_ref = {"blob_sha256": auth_blob_sha, "relpath": store.relpath(auth_blob_sha)}
        if adm_ctx["catalog"].get(src_digest) != src_ref or adm_ctx["catalog"].get(auth_digest) != auth_ref:
            adm_ctx["catalog"][src_digest] = src_ref
            adm_ctx["catalog"][auth_digest] = auth_ref
            adm_file.write_bytes(canonical_bytes(adm_ctx) + b"\n")
        adm_ref = {"path": adm_rel, "sha256": hashlib.sha256(adm_file.read_bytes()).hexdigest()}

        forecast_id, predictions, _ = generate_forecast(
            forecast_cache,
            cap,
            request,
            local_cat,
            auth_digest,
            model_name=model_name,
        )
        wide = strict_solver_table(predictions, cap, request, local_cat).rename(
            columns={"club": "club_id", "position": "position_id", "price": "now_cost"}
        )
        players, outcomes = _extract_origin_players_and_outcomes(origin, local_cat)
        elig = {player["id"]: player["eligible"] for player in players}
        wide["purchase_eligible"] = wide["player_id"].map(lambda pid: elig[pid])
        frames_by_gw[gw] = wide

        pts_by_player: dict[int, int] = {}
        mins_by_player: dict[int, int] = {}
        for out_row in outcomes:
            pid = int(out_row["player"])
            pts_by_player[pid] = pts_by_player.get(pid, 0) + int(out_row["points"])
            mins_by_player[pid] = mins_by_player.get(pid, 0) + int(out_row["minutes"])
        adm_origin = require_admitted(request, local_cat, season, gw, allow_disk_path_fallback=False)
        outcomes_by_gw[gw] = OutcomeBatch(
            season,
            gw,
            adm_origin.evidence_digest,
            tuple(
                (
                    player["id"],
                    Outcome(
                        points=pts_by_player.get(int(player["id"]), 0),
                        minutes=mins_by_player.get(int(player["id"]), 0),
                        appeared=mins_by_player.get(int(player["id"]), 0) > 0,
                    ),
                )
                for player in players
            ),
        )
        issues.append(
            {
                "gameweek": gw,
                "admission": adm_ref,
                "forecast_store": forecast_cache_rel,
                "forecast_id": forecast_id,
                "training_authority": auth_digest,
            }
        )

    checkpoint_dir = root / "replay_checkpoints" / f"{season}-{model_name}"
    trajectory = run_rolling_replay(
        model_name,
        season,
        anchor,
        lambda gw, _state: frames_by_gw[gw],
        lambda gw: outcomes_by_gw[gw],
        end_gw=end_gw,
        horizon=6,
        policy=policy,
        checkpoint_dir=checkpoint_dir,
        model_version_hash=source_hash,
        protocol_hash=protocol_hash,
        chip_calendar=chip_calendar,
    )
    records = list(trajectory.records)
    trace_ref = _write_rel_json(
        root,
        f"traces/{season}-{model_name}-gw{end_gw:02d}.json",
        {"records": [record_to_dict(r) for r in records]},
    )
    entry = {
        "season": season,
        "model_name": model_name,
        "anchor": anchor_ref,
        "trace": trace_ref,
        "issues": issues,
    }
    return anchor_ref, records, issues, trace_ref | {"entry": json.dumps(entry)}  # type: ignore[return-value]


def _freeze_command(args: argparse.Namespace) -> int:
    root = Path(args.evidence_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    season = str(args.season)
    dev_season = str(args.development_season)
    champion = str(args.champion)
    candidates = tuple(
        c.strip()
        for raw in (args.candidates or [])
        for c in raw.split(",")
        if c.strip()
    )
    if not candidates or champion in candidates or len(set(candidates)) != len(candidates):
        raise ValueError("Freeze requires 1..2 distinct candidates distinct from Champion")

    policy = QualityPolicy(mode="certified", target_gap=0.0, time_limit_seconds=float(args.time_limit_seconds))
    validate_quality_policy_gate(policy, require_certified=True)

    closure = compute_serving_model_closure((champion, *candidates))
    slate_file = root / "slate.json"
    slate_payload = {
        "slate_id": str(args.slate_id),
        "season": season,
        "development_season": dev_season,
        "champion": champion,
        "candidates": list(candidates),
        "serving_model_closure_hash": closure.serving_model_closure_hash,
        "model_runtime_bindings": closure.model_runtime_bindings,
        "evaluator_code_hash": closure.evaluator_code_hash,
        "producer_git_sha": closure.producer_git_sha,
    }
    if slate_file.is_file():
        existing = json.loads(slate_file.read_bytes())
        if existing != slate_payload:
            raise ValueError(f"Slate '{existing.get('slate_id')}' already sealed with different parameters or closure")
    else:
        _write_rel_json(root, "slate.json", slate_payload)

    selection = ModelSelection(
        champion=champion,
        candidates=candidates,
        provisional_active=candidates[0],
        podium_frozen_season=season,
        podium_sealed=True,
    )
    sel_file = root / "selection.json"
    if sel_file.is_file():
        if load_model_selection(sel_file) != selection:
            raise ValueError("Selection already sealed with different configuration")
    else:
        save_model_selection(selection, sel_file)

    s1_mode: str | None = None
    if args.s1_guard_baseline is not None or (season == "2027-28" and (root / "s1_guard_baseline.json").is_file()):
        if season != "2027-28":
            raise ValueError("s1_guard_baseline_season_archive_transition permitted only on 2027-28")
        s1_mode = "s1_guard_baseline_season_archive_transition"

    dev_gws, dev_prefix_end, _, _, _ = _assess_season_admissions(root, dev_season)
    dev_windows = list(range(1, dev_prefix_end + 1)) if dev_prefix_end >= 2 else [1, 2]
    if (root / "protocol.json").is_file():
        protocol = json.loads((root / "protocol.json").read_bytes())
        protocol_hash = content_hash(protocol)
        params_ref = {"path": "parameters.json", "sha256": content_hash({})}
    else:
        protocol = _build_default_protocol(
            development_season=dev_season,
            validation_season=season,
            approval_reference=str(args.approval_reference),
            dev_windows=dev_windows,
            time_limit_seconds=float(args.time_limit_seconds),
            max_family_attempts=int(args.max_family_attempts),
            s1_guard_baseline_mode=s1_mode,
        )
        _write_rel_json(root, "protocol.json", protocol)
        params_ref = _write_rel_json(root, "parameters.json", {})
        del params_ref
        protocol_hash = content_hash(protocol)

    source_hash = current_model_source_hash()
    parameters_hash = content_hash({})

    # Prepare S-1 development selection trace if S-1 admissions exist
    s1_trace_ref: dict[str, str] | None = None
    if dev_prefix_end >= len(dev_windows):
        _, _, _, trace_meta = _replay_season_prefix(
            root,
            season=dev_season,
            model_name=champion,
            admitted_gws=dev_gws,
            end_gw=dev_windows[-1],
            source_hash=source_hash,
            protocol_hash=protocol_hash,
            policy=policy,
        )
        s1_trace_ref = {"path": trace_meta["path"], "sha256": trace_meta["sha256"]}

    if not (root / "exclusions.jsonl").exists():
        (root / "exclusions.jsonl").write_bytes(b"")
    registry = ConfirmationRegistry(root / "registry.jsonl")
    existing_records = registry.load_all_records()
    for candidate in candidates:
        dev_sel_payload: dict[str, Any] = {
            "version": 1,
            "candidate_name": candidate,
            "former_champion": champion,
            "model_source_hash": source_hash,
            "protocol_hash": protocol_hash,
            "traces": {champion: s1_trace_ref} if s1_trace_ref is not None else {},
        }
        dev_ref = _write_rel_json(root, f"development_selections/{candidate}.json", dev_sel_payload)
        if not any(r.candidate_name == candidate and r.protocol_hash == protocol_hash for r in existing_records):
            registry.register_finalist(
                candidate,
                champion,
                f"family-{candidate}",
                source_hash,
                parameters_hash,
                dev_ref["sha256"],
                protocol_hash,
                requested_seasons=(season,),
                max_family_attempts=int(args.max_family_attempts),
            )

    print(
        json.dumps(
            {
                "command": "freeze",
                "slate_id": str(args.slate_id),
                "season": season,
                "champion": champion,
                "candidates": list(candidates),
                "serving_model_closure_hash": closure.serving_model_closure_hash,
                "protocol_hash": protocol_hash,
            },
            sort_keys=True,
        )
    )
    return 0


def _replay_command(args: argparse.Namespace) -> int:
    root = Path(args.evidence_root).resolve()
    season = str(args.season)
    checkpoint_gw = int(args.checkpoint_gw)
    if checkpoint_gw not in (15, 30, 38):
        raise ValueError(f"Replay checkpoint_gw must be 15, 30, or 38; got {checkpoint_gw}")

    slate = json.loads((root / "slate.json").read_bytes())
    selection = load_model_selection(root / "selection.json")
    protocol = json.loads((root / "protocol.json").read_bytes())
    protocol_hash = content_hash(protocol)
    source_hash = current_model_source_hash()
    closure = compute_serving_model_closure((selection.champion, *selection.candidates))
    if slate.get("serving_model_closure_hash") != closure.serving_model_closure_hash:
        raise ValueError("Serving model closure differs from sealed slate")

    policy_dict = dict(protocol["quality_policy"])
    if args.time_limit_seconds is not None:
        policy_dict["time_limit_seconds"] = float(args.time_limit_seconds)
    policy = QualityPolicy(**policy_dict)
    validate_quality_policy_gate(policy, require_certified=True)

    admitted_s, prefix_end_s, first_blocked_s, gap_status_s, gap_reasons_s = _assess_season_admissions(root, season)
    if prefix_end_s < checkpoint_gw:
        sc = _build_scorecard(
            root,
            slate_id=str(slate["slate_id"]),
            season=season,
            checkpoint_gw=checkpoint_gw,
            settled_through_gw=prefix_end_s,
            gap_status=gap_status_s if gap_status_s != "complete" else "transient_gap",
            first_blocked_gw=first_blocked_s or (prefix_end_s + 1),
            reason_codes=tuple(gap_reasons_s or [f"incomplete_prefix_gw_{prefix_end_s}_of_{checkpoint_gw}"]),
        )
        write_scorecard(root, sc)
        raise ValueError(
            f"Replay at GW{checkpoint_gw} blocked by incomplete empirical prefix: "
            f"admitted GW1..{prefix_end_s}, first blocked GW{sc.first_blocked_gw} ({sc.gap_status})"
        )

    exclusions = ExclusionLedger(root / "exclusions.jsonl")
    active_candidates = [
        c for c in selection.candidates if not exclusions.is_excluded(c, slate_id=str(slate["slate_id"]), season=season)
    ]
    if not active_candidates:
        raise ValueError("All frozen finalists have been excluded in ExclusionLedger")

    dev_season = str(slate["development_season"])
    dev_windows = list(protocol["windows"][dev_season])
    admitted_s1, prefix_end_s1, first_blocked_s1, _gap_s1, gap_reasons_s1 = _assess_season_admissions(root, dev_season)
    s1_baseline_ref: dict[str, str] | None = None
    if protocol.get("s1_guard_baseline_mode") == "s1_guard_baseline_season_archive_transition" and (
        root / "s1_guard_baseline.json"
    ).is_file():
        s1_file = root / "s1_guard_baseline.json"
        s1_baseline_ref = {"path": "s1_guard_baseline.json", "sha256": hashlib.sha256(s1_file.read_bytes()).hexdigest()}
    elif prefix_end_s1 < max(dev_windows):
        raise ValueError(
            f"S-1 development baseline '{dev_season}' incomplete at GW{first_blocked_s1}: {gap_reasons_s1}"
        )

    if not (root / "exclusions.jsonl").exists():
        (root / "exclusions.jsonl").write_bytes(b"")
    registry = ConfirmationRegistry(root / "registry.jsonl")
    all_records_reg = registry.load_all_records()
    attempt_ids: dict[str, str] = {}
    dev_selections: dict[str, dict[str, str]] = {}
    replays: list[dict[str, Any]] = []
    guard_outcome_sources: list[dict[str, Any]] = []

    if s1_baseline_ref is None:
        _, _, _, s1_meta = _replay_season_prefix(
            root,
            season=dev_season,
            model_name=selection.champion,
            admitted_gws=admitted_s1,
            end_gw=max(dev_windows),
            source_hash=source_hash,
            protocol_hash=protocol_hash,
            policy=policy,
        )
        replays.append(json.loads(s1_meta["entry"]))
        for gw in dev_windows:
            adm_rel = f"admissions/{dev_season}/gw{gw:02d}.json"
            guard_outcome_sources.append(
                {
                    "season": dev_season,
                    "gameweek": gw,
                    "admission": {"path": adm_rel, "sha256": hashlib.sha256((root / adm_rel).read_bytes()).hexdigest()},
                }
            )

    # Active season shared guard outcome sources & replays
    _, champ_records, _, champ_meta = _replay_season_prefix(
        root,
        season=season,
        model_name=selection.champion,
        admitted_gws=admitted_s,
        end_gw=checkpoint_gw,
        source_hash=source_hash,
        protocol_hash=protocol_hash,
        policy=policy,
    )
    champ_entry = json.loads(champ_meta["entry"])
    cum_net: dict[str, float] = {selection.champion: float(sum(r.net_points for r in champ_records))}
    cand_entries: list[dict[str, Any]] = []

    for cand in selection.candidates:
        attempt = [r for r in all_records_reg if r.candidate_name == cand and r.protocol_hash == protocol_hash][-1]
        attempt_ids[cand] = attempt.attempt_id
        dev_sel_rel = f"development_selections/{cand}.json"
        dev_selections[cand] = {"path": dev_sel_rel, "sha256": hashlib.sha256((root / dev_sel_rel).read_bytes()).hexdigest()}

        _, cand_records, _, cand_meta = _replay_season_prefix(
            root,
            season=season,
            model_name=cand,
            admitted_gws=admitted_s,
            end_gw=checkpoint_gw,
            source_hash=source_hash,
            protocol_hash=protocol_hash,
            policy=policy,
        )
        cand_entry = json.loads(cand_meta["entry"])
        cand_entries.append(cand_entry)
        cum_net[cand] = float(sum(r.net_points for r in cand_records))

        scores = [pair_replay_score(season, c_rec, ch_rec) for c_rec, ch_rec in zip(cand_records, champ_records, strict=True)]
        trace_hash = compute_score_trace_hash(scores)
        latest = registry.get_attempt(attempt.attempt_id)
        if latest is None or latest.completed_gameweeks != tuple(range(1, checkpoint_gw + 1)):
            registry.record_checkpoint(
                attempt.attempt_id,
                checkpoint_gw=checkpoint_gw,
                completed_gameweeks=tuple(range(1, checkpoint_gw + 1)),
                score_trace_hash=trace_hash,
            )

    # Merge all per-GW active-season training blobs into shared checkpoint admission gw<NN>.json
    adm_s_rel = f"admissions/{season}/gw{checkpoint_gw:02d}.json"
    adm_s_file = root / adm_s_rel
    shared_raw = adm_s_file.read_bytes()
    shared_ctx = json.loads(shared_raw)
    shared_changed = False
    for gw in range(1, checkpoint_gw + 1):
        gw_adm_file = root / f"admissions/{season}/gw{gw:02d}.json"
        if gw_adm_file.is_file():
            gw_ctx = json.loads(gw_adm_file.read_bytes())
            for c_key, c_val in gw_ctx.get("catalog", {}).items():
                if shared_ctx["catalog"].get(c_key) != c_val:
                    shared_ctx["catalog"][c_key] = c_val
                    shared_changed = True
    if shared_changed:
        adm_s_file.write_bytes(canonical_bytes(shared_ctx) + b"\n")
    adm_s_ref = {"path": adm_s_rel, "sha256": hashlib.sha256(adm_s_file.read_bytes()).hexdigest()}
    for gw in range(1, checkpoint_gw + 1):
        guard_outcome_sources.append({"season": season, "gameweek": gw, "admission": adm_s_ref})
    for replay_entry in (champ_entry, *cand_entries):
        for iss in replay_entry["issues"]:
            iss["admission"] = adm_s_ref
        replays.append(replay_entry)

    bundle_path = Path(args.output_bundle).resolve() if args.output_bundle else (root / f"bundle_gw{checkpoint_gw:02d}.json")
    if bundle_path.parent != root:
        raise ValueError("output-bundle must reside directly inside evidence-root alongside selection.json and registry.jsonl")
    req_path = bundle_path.with_name(f"request_{bundle_path.stem}.json")
    payload: dict[str, Any] = {
        "version": CHECKPOINT_EVIDENCE_V2,
        "checkpoint_gw": checkpoint_gw,
        "selection_path": "selection.json",
        "registry_path": "registry.jsonl",
        "model_source_hash": source_hash,
        "serving_model_closure_hash": closure.serving_model_closure_hash,
        "model_runtime_bindings": closure.model_runtime_bindings,
        "protocol": {"path": "protocol.json", "sha256": hashlib.sha256((root / "protocol.json").read_bytes()).hexdigest()},
        "parameters": {"path": "parameters.json", "sha256": hashlib.sha256((root / "parameters.json").read_bytes()).hexdigest()},
        "podium_order": list(selection.candidates),
        "confirmation_attempt_ids": attempt_ids,
        "development_selections": dev_selections,
        "replays": replays,
        "guard_outcome_sources": guard_outcome_sources,
    }
    if s1_baseline_ref is not None:
        payload["s1_guard_baseline"] = s1_baseline_ref
    req_path.write_bytes(canonical_bytes(payload) + b"\n")

    bundle = write_checkpoint_recommendation_bundle(req_path, bundle_path)
    if bundle.get("action") in ("rotate_to_backup", "fallback_to_champion"):
        for reason in bundle.get("reasons", []):
            reason_str = str(reason)
            if "Early-Harm" in reason_str:
                match_cand = re.search(r"Provisional Active '([^']+)'", reason_str)
                harmed = match_cand.group(1) if match_cand else (selection.provisional_active or active_candidates[0])
                if not exclusions.is_excluded(harmed, slate_id=str(slate["slate_id"]), season=season):
                    exclusions.record_exclusion(
                        slate_id=str(slate["slate_id"]),
                        season=season,
                        candidate_name=harmed,
                        checkpoint_gw=checkpoint_gw,
                        reason_code="early_harm",
                        details=reason_str,
                    )
    snapshot_meta: dict[str, Any] | None = None
    has_passing_snapshot = False
    if bundle["scientific_verdict"] == "pass" and bundle.get("empirical_admission") is True:
        snapshots_dir = Path(args.snapshots_dir).resolve() if args.snapshots_dir else (root / "snapshots")
        snapshot_meta = pack_checkpoint_snapshot(
            bundle_path,
            output_dir=snapshots_dir,
            exclusions_path=root / "exclusions.jsonl",
        )
        has_passing_snapshot = True

    eligible_scores = {m: v for m, v in cum_net.items() if m == selection.champion or m in active_candidates}
    weekly_leader = max(eligible_scores, key=lambda m: (eligible_scores[m], m == selection.champion)) if eligible_scores else None
    sc = _build_scorecard(
        root,
        slate_id=str(slate["slate_id"]),
        season=season,
        checkpoint_gw=checkpoint_gw,
        settled_through_gw=prefix_end_s,
        gap_status="complete",
        first_blocked_gw=None,
        reason_codes=tuple(bundle.get("reasons", [])),
        cumulative_net_points=cum_net,
        weekly_leader=weekly_leader,
        checkpoint_action=str(bundle.get("action")),
        bundle_hash=str(bundle.get("bundle_hash")),
    )
    write_scorecard(root, sc)

    print(
        json.dumps(
            {
                "command": "replay",
                "season": season,
                "checkpoint_gw": checkpoint_gw,
                "scientific_verdict": bundle["scientific_verdict"],
                "action": bundle["action"],
                "bundle_path": bundle_path.name,
                "bundle_hash": bundle["bundle_hash"],
                "has_passing_snapshot": has_passing_snapshot,
                "snapshot": snapshot_meta,
            },
            sort_keys=True,
        )
    )
    return 0


def _bootstrap_s1_baseline_command(args: argparse.Namespace) -> int:
    root = Path(args.evidence_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    season = str(args.season)
    dev_season = str(args.development_season)
    lifecycle = load_season_lifecycle()
    if (
        season != "2027-28"
        or dev_season in lifecycle.sealed_seasons()
        or season in lifecycle.sealed_seasons()
        or lifecycle.role_of(dev_season) == "active_validation"
    ):
        raise ValueError(
            "bootstrap-s1-baseline is permitted only for rolled-over 2027-28 transition and never on active_validation/sealed seasons"
        )

    archive_dir = Path(args.archive_processed_dir).resolve()
    gw_df = pd.read_parquet(archive_dir / "gameweeks.parquet")
    if gw_df.empty or not bool(gw_df["finished"].all()):
        raise ValueError(f"Development archive '{archive_dir}' lacks finalized gameweeks")
    perf_df = pd.read_parquet(archive_dir / "player_performances.parquet")
    if perf_df.empty:
        raise ValueError(f"Development archive '{archive_dir}' has no player_performances")

    h = hashlib.sha256()
    for fname in sorted(p.name for p in archive_dir.glob("*.parquet")):
        h.update(fname.encode("utf-8"))
        h.update(hashlib.sha256((archive_dir / fname).read_bytes()).digest())
    archive_manifest_sha = h.hexdigest()

    rows: list[dict[str, Any]] = []
    for row in perf_df.to_dict(orient="records"):
        entry: dict[str, Any] = {
            "season": dev_season,
            "gameweek": int(row["gameweek_id"]),
            "player_id": int(row["player_id"]),
        }
        for _gname, (fcol, acol, _loss, _units) in GUARD_SEMANTICS.items():
            entry[fcol] = float(row.get(fcol, 0.0) or 0.0)
            entry[acol] = float(row.get(acol, 0.0) or 0.0)
        rows.append(entry)

    baseline = {
        "schema_version": 1,
        "season": dev_season,
        "target_validation_season": season,
        "champion_name": str(args.champion),
        "archive_manifest_sha256": archive_manifest_sha,
        "disclosure": "s1_guard_baseline_season_archive_transition",
        "rows": rows,
    }
    _write_rel_json(root, "s1_guard_baseline.json", baseline)
    BlobStore(root).write_canonical_json(baseline)
    print(
        json.dumps(
            {
                "command": "bootstrap-s1-baseline",
                "season": season,
                "development_season": dev_season,
                "archive_manifest_sha256": archive_manifest_sha,
                "row_count": len(rows),
            },
            sort_keys=True,
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Produce portable ADR 0069/0070 validation evidence.")
    sub = parser.add_subparsers(dest="subcommand", required=True)

    p_collect = sub.add_parser("collect", help="Collect empirical origin blobs into evidence root")
    p_collect.add_argument("--evidence-root", required=True)
    p_collect.add_argument("--batch-json", required=True)
    p_collect.add_argument("--slate-id", default="default-slate")

    p_freeze = sub.add_parser("freeze", help="Seal slate, protocol, runtime bindings, and finalist registrations")
    p_freeze.add_argument("--evidence-root", required=True)
    p_freeze.add_argument("--season", required=True)
    p_freeze.add_argument("--development-season", required=True)
    p_freeze.add_argument("--champion", required=True)
    p_freeze.add_argument("--candidates", action="append", required=True)
    p_freeze.add_argument("--slate-id", required=True)
    p_freeze.add_argument("--approval-reference", required=True)
    p_freeze.add_argument("--time-limit-seconds", type=float, default=60.0)
    p_freeze.add_argument("--max-family-attempts", type=int, default=1)
    p_freeze.add_argument("--s1-guard-baseline", default=None)

    p_replay = sub.add_parser("replay", help="Run/resume prefix-reusable replay and evaluate checkpoint")
    p_replay.add_argument("--evidence-root", required=True)
    p_replay.add_argument("--season", required=True)
    p_replay.add_argument("--checkpoint-gw", type=int, required=True)
    p_replay.add_argument("--output-bundle", default=None)
    p_replay.add_argument("--snapshots-dir", default=None)
    p_replay.add_argument("--time-limit-seconds", type=float, default=None)

    p_boot = sub.add_parser("bootstrap-s1-baseline", help="Generate preregistered 2027-28 S-1 Season Archive transition baseline")
    p_boot.add_argument("--evidence-root", required=True)
    p_boot.add_argument("--season", required=True)
    p_boot.add_argument("--development-season", required=True)
    p_boot.add_argument("--archive-processed-dir", required=True)
    p_boot.add_argument("--champion", required=True)

    args = parser.parse_args(argv)
    if args.subcommand == "collect":
        return _collect_command(args)
    if args.subcommand == "freeze":
        return _freeze_command(args)
    if args.subcommand == "replay":
        return _replay_command(args)
    if args.subcommand == "bootstrap-s1-baseline":
        return _bootstrap_s1_baseline_command(args)
    raise ValueError(f"Unknown subcommand: {args.subcommand}")


if __name__ == "__main__":
    raise SystemExit(main())
