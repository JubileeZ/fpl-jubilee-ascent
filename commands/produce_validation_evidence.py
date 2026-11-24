"""Portable checkpoint evidence producer CLI (`collect`, `freeze`, `replay`, `bootstrap-s1-baseline`)."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, replace
from datetime import UTC, datetime
import csv
import hashlib
import io
import json
import lzma
from pathlib import Path
import re
import sys
import time
from typing import Any, Literal, Mapping, cast

import httpx
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backtesting.adoption_transaction import SharedReservationCoordinator
from backtesting.confirmation_registry import ConfirmationRegistry
from backtesting.data_admission import require_admitted, require_input
from backtesting.empirical_admission import (
    _compute_outcome_component_sum,
    assess_empirical_origins,
    build_empirical_seed_mapping,
)
from backtesting.empirical_mirrors import (
    canonical_bootstrap_table,
    canonical_json_sha256,
    parse_fixtures_csv_window,
    sha256_bytes,
)
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
    DEFAULT_CERTIFIED_TIME_LIMIT_SECONDS,
    QualityPolicy,
    ReplayDeadlineRecord,
    record_to_dict,
    run_rolling_replay,
    validate_quality_policy_gate,
)
from backtesting.season_rules import Chip, load_season_lifecycle
from backtesting.sparse_certification import build_certified_protocol_config, verify_certification_artifacts
from backtesting.walkforward import _build_actual_components, history_before_target
from clients.env_loader import configure_utf8_stdio
from features.builder import build_features
from models import get_model
from models.selection import ModelSelection, load_model_selection, save_model_selection
from models.scoring_matrix import event_points

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CERTIFICATION_RESULT_PATH = (
    PROJECT_ROOT / "docs" / "research" / "sparse-confirmation-certification" / "certification_result.json"
)
DEFAULT_FPL_API_BASE = "https://fantasy.premierleague.com/api"

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
    from backtesting.promotion_evidence import _resolve_context_catalog

    return _resolve_context_catalog(root, context)


def _load_existing_season_state(
    root: Path,
    season: str,
) -> tuple[dict[int, dict[str, Any]], dict[str, dict[str, str]], dict[str, Any]]:
    adm_dir = root / "admissions" / season
    if not adm_dir.is_dir():
        return {}, {}, {}
    files = sorted(p for p in adm_dir.glob("gw*.json") if p.is_file())
    if not files:
        return {}, {}, {}
    latest_ctx = json.loads(files[-1].read_bytes())
    req = dict(latest_ctx.get("request", {}))
    ext_cat: dict[str, dict[str, str]] = {
        str(k): dict(v) for k, v in dict(latest_ctx.get("catalog", {})).items() if isinstance(v, Mapping)
    }
    by_gw: dict[int, dict[str, Any]] = {}
    for origin in req.get("origins", ()):
        if isinstance(origin, Mapping) and type(origin.get("gw")) is int:
            by_gw[int(origin["gw"])] = dict(origin)
    return by_gw, ext_cat, req


def _persist_cumulative_admissions(
    root: Path,
    season: str,
    *,
    track: str,
    purpose: str,
    checkpoint_gw: Any,
    shared_chip_calendar: list[Any],
    anchor: dict[str, Any],
    origins_by_gw: Mapping[int, dict[str, Any]],
    ext_catalog: Mapping[str, dict[str, str]],
) -> None:
    adm_dir = root / "admissions" / season
    adm_dir.mkdir(parents=True, exist_ok=True)
    acc_origins: list[dict[str, Any]] = []
    acc_catalog: dict[str, dict[str, str]] = {}
    for gw in sorted(origins_by_gw):
        origin = dict(origins_by_gw[gw])
        acc_origins.append(origin)
        for spec in dict(origin.get("sources", {})).values():
            sid = str(spec.get("source_id", ""))
            if sid and sid in ext_catalog:
                acc_catalog[sid] = dict(ext_catalog[sid])
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
            "shared_chip_calendar": shared_chip_calendar,
            "anchor": anchor,
            "origins": list(acc_origins),
        }
        ctx_path = adm_dir / f"gw{gw:02d}.json"
        new_bytes = canonical_bytes({"request": req_prefix, "catalog": dict(acc_catalog)}) + b"\n"
        # Preserve byte-identical or already-committed prefix files unless this exact GW's origin changed
        if ctx_path.is_file() and ctx_path.read_bytes() == new_bytes:
            continue
        if ctx_path.is_file():
            existing_ctx = json.loads(ctx_path.read_bytes())
            existing_orig = next(
                (o for o in existing_ctx.get("request", {}).get("origins", ()) if o.get("gw") == gw),
                None,
            )
            if existing_orig == origin:
                continue
        ctx_path.write_bytes(new_bytes)


def _http_get_with_retry(
    client: httpx.Client,
    url: str,
    *,
    max_attempts: int = 3,
) -> httpx.Response:
    for attempt in range(max_attempts):
        resp = client.get(url)
        if resp.status_code == 429 and attempt + 1 < max_attempts:
            retry_raw = resp.headers.get("Retry-After", "0").strip()
            delay = float(retry_raw) if retry_raw.replace(".", "", 1).isdigit() else 0.5
            time.sleep(min(max(delay, 0.0), 5.0))
            continue
        resp.raise_for_status()
        return resp
    raise RuntimeError(f"Exhausted retries fetching {url}")


def _fixtures_to_csv_bytes(fixtures: list[dict[str, Any]]) -> bytes:
    buf = io.StringIO()
    fieldnames = [
        "id",
        "event",
        "team_h",
        "team_a",
        "kickoff_time",
        "team_h_difficulty",
        "team_a_difficulty",
        "finished",
        "finished_provisional",
        "minutes",
    ]
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    for fx in fixtures:
        ev = fx.get("event")
        ko = (fx.get("kickoff_time") or "")
        if ev is None or not str(ko).strip():
            continue
        writer.writerow(
            {
                "id": int(fx["id"]),
                "event": int(ev),
                "team_h": int(fx["team_h"]),
                "team_a": int(fx["team_a"]),
                "kickoff_time": str(ko),
                "team_h_difficulty": int(fx.get("team_h_difficulty") or 3),
                "team_a_difficulty": int(fx.get("team_a_difficulty") or 3),
                "finished": bool(fx.get("finished", False)),
                "finished_provisional": bool(fx.get("finished_provisional", fx.get("finished", False))),
                "minutes": int(fx.get("minutes") or 0),
            }
        )
    return buf.getvalue().encode("utf-8")


def _build_outcome_row_from_stats(
    *,
    pid: int,
    fid: int,
    pos_id: int,
    stats: Mapping[str, Any],
    rules_version: str,
) -> dict[str, Any]:
    mins = int(stats.get("minutes", 0) or 0)
    yc = int(stats.get("yellow_cards", 0) or 0)
    rc = int(stats.get("red_cards", 0) or 0)
    pts = int(stats.get("total_points", 0) or 0)
    row: dict[str, Any] = {
        "player_id": int(pid),
        "fixture_id": int(fid),
        "position_id": int(pos_id),
        "minutes": mins,
        "total_points": pts,
        "appeared": mins > 0,
        "goals_scored": int(stats.get("goals_scored", 0) or 0),
        "assists": int(stats.get("assists", 0) or 0),
        "clean_sheets": int(stats.get("clean_sheets", 0) or 0),
        "goals_conceded": int(stats.get("goals_conceded", 0) or 0),
        "own_goals": int(stats.get("own_goals", 0) or 0),
        "penalties_saved": int(stats.get("penalties_saved", 0) or 0),
        "penalties_missed": int(stats.get("penalties_missed", 0) or 0),
        "yellow_cards": yc,
        "red_cards": rc,
        "saves": int(stats.get("saves", 0) or 0),
        "bonus": int(stats.get("bonus", 0) or 0),
        "defensive_contribution": int(stats.get("defensive_contribution", 0) or 0),
    }
    row["component_points_sum"] = _compute_outcome_component_sum(row, rules_version)
    return row


def _build_history_row(
    *,
    pid: int,
    fid: int,
    pgw: int,
    ko_str: str,
    was_home: bool,
    opp_id: int,
    stats: Mapping[str, Any],
) -> dict[str, Any]:
    mins = int(stats.get("minutes", 0) or 0)
    return {
        "player_id": int(pid),
        "fixture_id": int(fid),
        "gameweek_id": int(pgw),
        "kickoff_time": ko_str,
        "was_home": bool(was_home),
        "opponent_club_id": int(opp_id),
        "minutes": mins,
        "total_points": int(stats.get("total_points", 0) or 0),
        "starts": 1 if mins > 0 else 0,
        "goals_scored": int(stats.get("goals_scored", 0) or 0),
        "assists": int(stats.get("assists", 0) or 0),
        "clean_sheets": int(stats.get("clean_sheets", 0) or 0),
        "goals_conceded": int(stats.get("goals_conceded", 0) or 0),
        "own_goals": int(stats.get("own_goals", 0) or 0),
        "penalties_saved": int(stats.get("penalties_saved", 0) or 0),
        "penalties_missed": int(stats.get("penalties_missed", 0) or 0),
        "yellow_cards": int(stats.get("yellow_cards", 0) or 0),
        "red_cards": int(stats.get("red_cards", 0) or 0),
        "saves": int(stats.get("saves", 0) or 0),
        "bonus": int(stats.get("bonus", 0) or 0),
        "bps": int(stats.get("bps", 0) or 0),
        "influence": float(stats.get("influence", 0.0) or 0.0),
        "creativity": float(stats.get("creativity", 0.0) or 0.0),
        "threat": float(stats.get("threat", 0.0) or 0.0),
        "ict_index": float(stats.get("ict_index", 0.0) or 0.0),
        "expected_goals": float(stats.get("expected_goals", 0.0) or 0.0),
        "expected_assists": float(stats.get("expected_assists", 0.0) or 0.0),
        "expected_goal_involvements": float(stats.get("expected_goal_involvements", 0.0) or 0.0),
        "expected_goals_conceded": float(stats.get("expected_goals_conceded", 0.0) or 0.0),
        "defensive_contribution": int(stats.get("defensive_contribution", 0) or 0),
    }


def _load_origin_team_map(
    *,
    store: BlobStore,
    prior_origin: Mapping[str, Any] | None,
    ext_catalog: Mapping[str, dict[str, str]],
    default_teams: Mapping[int, int] | None,
) -> dict[int, int]:
    teams = dict(default_teams or {})
    bs_spec = dict(prior_origin.get("sources", {})).get("bootstrap") if prior_origin else None
    if isinstance(bs_spec, Mapping) and str(bs_spec.get("source_id", "")) in ext_catalog:
        bs_raw = (store.root / ext_catalog[str(bs_spec["source_id"])]["relpath"]).read_bytes()
        bs_dec = lzma.decompress(bs_raw) if bs_raw.startswith(b"\xfd7zXZ\x00") else bs_raw
        for el in json.loads(bs_dec).get("elements", ()):
            if isinstance(el, Mapping) and "id" in el and "team" in el:
                teams[int(el["id"])] = int(el["team"])
    return teams


def _compose_pre_deadline_history(
    *,
    store: BlobStore,
    season: str,
    target_gw: int,
    deadline_dt: datetime,
    origins_by_gw: Mapping[int, dict[str, Any]],
    ext_catalog: Mapping[str, dict[str, str]],
    client: httpx.Client,
    events_by_id: Mapping[int, Mapping[str, Any]],
    fixtures_by_gw: Mapping[int, list[dict[str, Any]]],
    pos_by_id: Mapping[int, int],
    team_by_id: Mapping[int, int] | None = None,
) -> list[dict[str, Any]]:
    """Compose causal history strictly settled < target deadline (admitted slices or <24h event/live fallback)."""
    rows: list[dict[str, Any]] = []
    if target_gw <= 1:
        return rows
    for pgw in range(1, target_gw):
        prior_origin = origins_by_gw.get(pgw)
        out_spec = dict(prior_origin.get("sources", {})).get("outcomes") if prior_origin else None
        if isinstance(out_spec, Mapping) and str(out_spec.get("source_id", "")) in ext_catalog:
            fin_raw = out_spec.get("finalized_at")
            if isinstance(fin_raw, str) and _utc(fin_raw) < deadline_dt:
                meta = ext_catalog[str(out_spec["source_id"])]
                out_list = json.loads((store.root / meta["relpath"]).read_bytes().decode("utf-8"))
                fx_rows = fixtures_by_gw.get(pgw, [])
                fx_by_id = {int(f["id"]): f for f in fx_rows}
                bs_teams = _load_origin_team_map(
                    store=store,
                    prior_origin=prior_origin,
                    ext_catalog=ext_catalog,
                    default_teams=team_by_id,
                )
                for r in out_list:
                    fid = int(r["fixture_id"])
                    pid = int(r["player_id"])
                    fx = fx_by_id.get(fid, {})
                    ko_str = str(fx.get("kickoff_time") or deadline_dt.isoformat())
                    if _utc(ko_str) >= deadline_dt:
                        continue
                    team_id = bs_teams.get(pid, int(fx.get("team_h", 1) or 1))
                    was_home = int(fx.get("team_h", 0) or 0) == team_id
                    opp_id = int(fx.get("team_a", 2) if was_home else fx.get("team_h", 1))
                    rows.append(
                        _build_history_row(
                            pid=pid,
                            fid=fid,
                            pgw=pgw,
                            ko_str=ko_str,
                            was_home=was_home,
                            opp_id=opp_id,
                            stats=r,
                        )
                    )
                continue

        # Fallback on tight <24h turnaround: fetch single /event/{pgw}/live/ if fixtures finished < deadline
        ev_meta = events_by_id.get(pgw, {})
        if ev_meta.get("finished") is True:
            gw_fxs = [f for f in fixtures_by_gw.get(pgw, []) if f.get("finished") is True and f.get("kickoff_time") and _utc(f["kickoff_time"]) < deadline_dt]
            if not gw_fxs:
                continue
            live_resp = _http_get_with_retry(client, f"/event/{pgw}/live/").json()
            live_elems = {int(el["id"]): el for el in live_resp.get("elements", ()) if isinstance(el, Mapping) and "id" in el}
            fb_teams = _load_origin_team_map(
                store=store,
                prior_origin=prior_origin,
                ext_catalog=ext_catalog,
                default_teams=team_by_id,
            )
            for fx in gw_fxs:
                fid = int(fx["id"])
                ko_str = str(fx["kickoff_time"])
                for pid, el in live_elems.items():
                    if pid not in pos_by_id:
                        continue
                    stats = el.get("stats") or {}
                    explain = [e for e in el.get("explain", ()) if isinstance(e, Mapping) and int(e.get("fixture", -1)) == fid]
                    if not explain:
                        continue
                    team_id = fb_teams.get(pid, int(fx.get("team_h", 1) or 1))
                    was_home = int(fx.get("team_h", 0) or 0) == team_id
                    opp_id = int(fx.get("team_a", 2) if was_home else fx.get("team_h", 1))
                    rows.append(
                        _build_history_row(
                            pid=pid,
                            fid=fid,
                            pgw=pgw,
                            ko_str=ko_str,
                            was_home=was_home,
                            opp_id=opp_id,
                            stats=stats,
                        )
                    )
    return rows


def collect_live_validation_evidence(
    *,
    evidence_root: Path,
    season: str,
    slate_id: str = "default-slate",
    mode: str = "auto",
    fpl_api_base: str = DEFAULT_FPL_API_BASE,
    now_utc: str | None = None,
    max_concurrency: int = 3,
    seed_file: Path | None = None,
    transport: httpx.BaseTransport | None = None,
) -> dict[str, Any]:
    """Collect live pre-deadline (2-call) and post-settlement (3-call + bounded disambiguation) v2 receipts."""
    root = Path(evidence_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    store = BlobStore(root)
    concurrency = max(1, min(3, int(max_concurrency)))
    now_dt = _utc(now_utc) if now_utc else datetime.now(UTC)
    now_iso = now_dt.isoformat()
    lifecycle = load_season_lifecycle()
    dev_season = lifecycle.seasons[season].prior_seed if season in lifecycle.seasons and lifecycle.seasons[season].prior_seed else lifecycle.season_for_role("development")

    origins_by_gw, ext_catalog, existing_req = _load_existing_season_state(root, season)
    shared_chip_calendar = list(
        existing_req.get(
            "shared_chip_calendar",
            [{"gameweek": 3, "chip": "triple_captain"}, {"gameweek": 25, "chip": "wildcard"}],
        )
    )
    anchor = dict(existing_req.get("anchor", {}))
    checkpoint_gw_meta = existing_req.get("checkpoint_gw")

    with httpx.Client(base_url=fpl_api_base.rstrip("/"), timeout=30.0, transport=transport) as client:
        bootstrap = _http_get_with_retry(client, "/bootstrap-static/").json()
        raw_fixtures = _http_get_with_retry(client, "/fixtures/").json()

        events = [ev for ev in bootstrap.get("events", ()) if isinstance(ev, Mapping) and "id" in ev]
        events_by_id = {int(ev["id"]): ev for ev in events}
        fixtures_by_gw: dict[int, list[dict[str, Any]]] = {}
        for fx in raw_fixtures:
            if isinstance(fx, Mapping) and fx.get("event") is not None:
                fixtures_by_gw.setdefault(int(fx["event"]), []).append(dict(fx))

        elements = [el for el in bootstrap.get("elements", ()) if isinstance(el, Mapping) and "id" in el]
        pos_by_id = {
            int(el["id"]): int(el["element_type"])
            for el in elements
            if int(el.get("element_type", 0) or 0) in (1, 2, 3, 4)
        }
        team_by_id = {int(el["id"]): int(el["team"]) for el in elements if "team" in el}
        fx_csv_bytes = _fixtures_to_csv_bytes([dict(f) for f in raw_fixtures if isinstance(f, Mapping)])

        # 1. Pre-deadline capture (2 primary HTTP calls + conditional <24h history)
        if mode in ("auto", "pre_deadline"):
            future_evs = [
                ev
                for ev in events
                if ev.get("deadline_time") and _utc(ev["deadline_time"]) > now_dt
            ]
            target_ev = next(
                (ev for ev in future_evs if ev.get("is_next") is True),
                min(future_evs, key=lambda e: _utc(e["deadline_time"])) if future_evs else None,
            )
            if target_ev is not None:
                tgw = int(target_ev["id"])
                dl_dt = _utc(target_ev["deadline_time"])
                secs_to_dl = (dl_dt - now_dt).total_seconds()
                if 0 < secs_to_dl <= 48 * 3600 or mode == "pre_deadline":
                    prev_ev = events_by_id.get(tgw - 1) if tgw > 1 else None
                    prev_dl_str = str(prev_ev["deadline_time"]) if (prev_ev and prev_ev.get("deadline_time")) else None

                    bs_raw_json = canonical_bytes(bootstrap)
                    bs_xz = lzma.compress(bs_raw_json)
                    bs_sha = store.write_bytes(bs_xz)
                    bs_sid = f"{season}_gw{tgw:02d}_bootstrap_{bs_sha[:12]}"
                    ext_catalog[bs_sid] = {"blob_sha256": bs_sha, "relpath": store.relpath(bs_sha)}
                    sanitized_bs, bs_clubs, _ = _sanitize_bootstrap(bootstrap, capture_upper=now_dt)
                    bs_table = canonical_bootstrap_table(bootstrap, sanitized_bs, bs_clubs, tgw)
                    bs_spec = {
                        "source_id": bs_sid,
                        "blob_sha256": bs_sha,
                        "decompressed_sha256": sha256_bytes(bs_raw_json),
                        "table_sha256": canonical_json_sha256(bs_table),
                        "timing_basis": "receipt",
                        "url": f"receipt://official/bootstrap-static/gw{tgw:02d}",
                        "capture_lower": now_iso,
                        "capture_upper": now_iso,
                    }

                    fx_sha = store.write_bytes(fx_csv_bytes)
                    fx_sid = f"{season}_gw{tgw:02d}_fixtures_{fx_sha[:12]}"
                    ext_catalog[fx_sid] = {"blob_sha256": fx_sha, "relpath": store.relpath(fx_sha)}
                    fx_table = parse_fixtures_csv_window(fx_csv_bytes, tgw)
                    fx_spec = {
                        "source_id": fx_sid,
                        "blob_sha256": fx_sha,
                        "table_sha256": canonical_json_sha256(fx_table),
                        "timing_basis": "receipt",
                        "url": f"receipt://official/fixtures/gw{tgw:02d}",
                        "capture_lower": now_iso,
                        "capture_upper": now_iso,
                    }

                    hist_rows = _compose_pre_deadline_history(
                        store=store,
                        season=season,
                        target_gw=tgw,
                        deadline_dt=dl_dt,
                        origins_by_gw=origins_by_gw,
                        ext_catalog=ext_catalog,
                        client=client,
                        events_by_id=events_by_id,
                        fixtures_by_gw=fixtures_by_gw,
                        pos_by_id=pos_by_id,
                        team_by_id=team_by_id,
                    )
                    hist_bytes = canonical_bytes(hist_rows)
                    hist_sha = store.write_bytes(hist_bytes)
                    hist_sid = f"{season}_gw{tgw:02d}_history_{hist_sha[:12]}"
                    ext_catalog[hist_sid] = {"blob_sha256": hist_sha, "relpath": store.relpath(hist_sha)}
                    hist_spec = {
                        "source_id": hist_sid,
                        "blob_sha256": hist_sha,
                        "table_sha256": canonical_json_sha256(hist_rows),
                        "timing_basis": "receipt",
                        "url": f"receipt://official/history/gw{tgw:02d}",
                        "capture_lower": now_iso,
                        "capture_upper": now_iso,
                    }

                    sources_map: dict[str, Any] = {
                        "bootstrap": bs_spec,
                        "fixtures": fx_spec,
                        "history": hist_spec,
                    }
                    seed_candidate = seed_file or (root / "seeds" / f"{dev_season}.json")
                    if seed_candidate.is_file():
                        seed_base = json.loads(seed_candidate.read_bytes())
                        non_mgr_bs = [e for e in sanitized_bs if int(e.get("element_type", 0) or 0) != 5]
                        seed_obj = {
                            "season": dev_season,
                            "defensive_contribution_status": seed_base.get("defensive_contribution_status", "native"),
                            **seed_base,
                            "seed_mapping": build_empirical_seed_mapping(non_mgr_bs, seed_base.get("players", [])),
                        }
                        seed_bytes = canonical_bytes(seed_obj)
                        seed_sha = store.write_bytes(seed_bytes)
                        seed_sid = f"{season}_gw{tgw:02d}_seed_{seed_sha[:12]}"
                        ext_catalog[seed_sid] = {"blob_sha256": seed_sha, "relpath": store.relpath(seed_sha)}
                        sources_map["seed"] = {
                            "source_id": seed_sid,
                            "blob_sha256": seed_sha,
                            "table_sha256": canonical_json_sha256(seed_obj),
                            "timing_basis": "receipt",
                            "url": f"receipt://seed/{dev_season}/gw{tgw:02d}",
                            "capture_lower": now_iso,
                            "capture_upper": now_iso,
                        }

                    gw_fxs = fixtures_by_gw.get(tgw, [])
                    gw_kickoffs = [str(f["kickoff_time"]) for f in gw_fxs if f.get("kickoff_time")]
                    max_ko_str = max(gw_kickoffs, key=_utc) if gw_kickoffs else str(target_ev["deadline_time"])
                    origins_by_gw[tgw] = {
                        "season": season,
                        "gw": tgw,
                        "deadline": str(target_ev["deadline_time"]),
                        "prev_deadline": prev_dl_str,
                        "max_kickoff_utc": max_ko_str,
                        "disclosed_limitations": [],
                        "sources": sources_map,
                    }

        # 2. Post-settlement capture (3rd primary HTTP call /event/{gw}/live/ + bounded <=3 element-summary disambiguation)
        if mode in ("auto", "post_settlement"):
            for gw in sorted(origins_by_gw):
                origin = origins_by_gw[gw]
                existing_out = dict(origin.get("sources", {})).get("outcomes")
                if isinstance(existing_out, Mapping) and existing_out.get("data_checked") is True and existing_out.get("finished") is True:
                    continue
                ev = events_by_id.get(gw)
                if not ev or ev.get("finished") is not True or ev.get("data_checked") is not True:
                    continue
                gw_fxs = fixtures_by_gw.get(gw, [])
                if any(f.get("finished") is not True for f in gw_fxs):
                    continue
                gw_ko_dts = [_utc(f["kickoff_time"]) for f in gw_fxs if f.get("kickoff_time")]
                if not gw_ko_dts:
                    continue
                max_ko_dt = max(gw_ko_dts)
                if (now_dt - max_ko_dt).total_seconds() < 24 * 3600:
                    continue

                live_resp = _http_get_with_retry(client, f"/event/{gw}/live/").json()
                live_elems = {
                    int(el["id"]): el
                    for el in live_resp.get("elements", ())
                    if isinstance(el, Mapping) and "id" in el
                }

                # Use pre-deadline bootstrap/fixtures when available to keep player-fixture universe immutable
                pre_bs_spec = dict(origin.get("sources", {})).get("bootstrap")
                if isinstance(pre_bs_spec, Mapping) and str(pre_bs_spec.get("source_id", "")) in ext_catalog:
                    pre_bs_raw = (store.root / ext_catalog[str(pre_bs_spec["source_id"])]["relpath"]).read_bytes()
                    pre_bs_dec = json.loads(lzma.decompress(pre_bs_raw).decode("utf-8"))
                    pre_sanitized, _, _ = _sanitize_bootstrap(pre_bs_dec, capture_upper=_utc(pre_bs_spec["capture_upper"]))
                    origin_elems = pre_sanitized
                else:
                    origin_elems = [
                        {"id": int(el["id"]), "team": int(el["team"]), "element_type": int(el["element_type"])}
                        for el in elements
                        if int(el.get("element_type", 0) or 0) in (1, 2, 3, 4)
                    ]

                pre_fx_spec = dict(origin.get("sources", {})).get("fixtures")
                if isinstance(pre_fx_spec, Mapping) and str(pre_fx_spec.get("source_id", "")) in ext_catalog:
                    pre_fx_bytes = (store.root / ext_catalog[str(pre_fx_spec["source_id"])]["relpath"]).read_bytes()
                    admitted_gw_fxs = [r for r in parse_fixtures_csv_window(pre_fx_bytes, gw) if int(r["event"]) == gw]
                else:
                    admitted_gw_fxs = gw_fxs

                club_fxs: dict[int, list[int]] = {}
                for fx in admitted_gw_fxs:
                    fid = int(fx["id"])
                    club_fxs.setdefault(int(fx["team_h"]), []).append(fid)
                    club_fxs.setdefault(int(fx["team_a"]), []).append(fid)

                disambig_pids: list[int] = []
                for el in origin_elems:
                    pid = int(el["id"])
                    pre_team = int(el["team"])
                    cur_team = team_by_id.get(pid, pre_team)
                    fids = club_fxs.get(pre_team, [])
                    if len(fids) >= 2 or cur_team != pre_team:
                        disambig_pids.append(pid)

                summaries_by_pid: dict[int, list[Mapping[str, Any]]] = {}
                if disambig_pids:
                    with ThreadPoolExecutor(max_workers=concurrency) as pool:
                        futures = {
                            pool.submit(_http_get_with_retry, client, f"/element-summary/{pid}/"): pid
                            for pid in sorted(disambig_pids)
                        }
                        for fut in as_completed(futures):
                            pid = futures[fut]
                            payload = fut.result().json()
                            summaries_by_pid[pid] = [
                                h
                                for h in payload.get("history", ())
                                if isinstance(h, Mapping) and int(h.get("round", -1)) == gw
                            ]

                rules_ver = season
                out_rows: list[dict[str, Any]] = []
                for el in sorted(origin_elems, key=lambda r: int(r["id"])):
                    pid = int(el["id"])
                    pre_team = int(el["team"])
                    pos_id = int(el["element_type"])
                    fids = club_fxs.get(pre_team, [])
                    if not fids:
                        continue  # Blank Gameweek: zero outcome rows for non-playing club
                    if pid in summaries_by_pid:
                        by_fid = {int(h["fixture"]): h for h in summaries_by_pid[pid] if "fixture" in h}
                        for fid in fids:
                            stats_src = by_fid.get(fid, {})
                            out_rows.append(
                                _build_outcome_row_from_stats(
                                    pid=pid,
                                    fid=fid,
                                    pos_id=pos_id,
                                    stats=stats_src,
                                    rules_version=rules_ver,
                                )
                            )
                    else:
                        live_stats = (live_elems.get(pid) or {}).get("stats") or {}
                        out_rows.append(
                            _build_outcome_row_from_stats(
                                pid=pid,
                                fid=fids[0],
                                pos_id=pos_id,
                                stats=live_stats,
                                rules_version=rules_ver,
                            )
                        )

                out_bytes = canonical_bytes(out_rows)
                out_sha = store.write_bytes(out_bytes)
                out_sid = f"{season}_gw{gw:02d}_outcomes_{out_sha[:12]}"
                ext_catalog[out_sid] = {"blob_sha256": out_sha, "relpath": store.relpath(out_sha)}
                updated_origin = dict(origin)
                updated_origin["max_kickoff_utc"] = max_ko_dt.isoformat()
                updated_sources = dict(updated_origin.get("sources", {}))
                updated_sources["outcomes"] = {
                    "source_id": out_sid,
                    "blob_sha256": out_sha,
                    "table_sha256": canonical_json_sha256(out_rows),
                    "timing_basis": "receipt",
                    "url": f"receipt://official/outcomes/gw{gw:02d}",
                    "finalized_at": now_iso,
                    "finished": True,
                    "data_checked": True,
                }
                updated_origin["sources"] = updated_sources
                origins_by_gw[gw] = updated_origin

    if origins_by_gw:
        _persist_cumulative_admissions(
            root,
            season,
            track="validation_fplcache",
            purpose="validation",
            checkpoint_gw=checkpoint_gw_meta,
            shared_chip_calendar=shared_chip_calendar,
            anchor=anchor,
            origins_by_gw=origins_by_gw,
            ext_catalog=ext_catalog,
        )

    _, prefix_end, first_blocked, gap_status, gap_reasons = _assess_season_admissions(root, season)
    max_gw = max(origins_by_gw, default=0)
    scorecard = _build_scorecard(
        root,
        slate_id=slate_id,
        season=season,
        checkpoint_gw=max_gw,
        settled_through_gw=prefix_end,
        gap_status=gap_status,
        first_blocked_gw=first_blocked,
        reason_codes=tuple(gap_reasons),
    )
    write_scorecard(root, scorecard)
    return {
        "command": "collect",
        "mode": mode,
        "season": season,
        "settled_through_gw": prefix_end,
        "gap_status": gap_status,
        "first_blocked_gw": first_blocked,
        "reason_codes": gap_reasons,
    }


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
    if args.batch_json is None:
        lifecycle = load_season_lifecycle()
        season = str(args.season or lifecycle.season_for_role("active_validation"))
        summary = collect_live_validation_evidence(
            evidence_root=root,
            season=season,
            slate_id=str(args.slate_id),
            mode=str(args.mode),
            fpl_api_base=str(args.fpl_api_base),
            now_utc=args.now_utc,
            max_concurrency=int(args.max_concurrency),
            seed_file=Path(args.seed_file).resolve() if args.seed_file else None,
        )
        print(json.dumps(summary, sort_keys=True))
        return 0

    store = BlobStore(root)
    batch_path = Path(args.batch_json).resolve()
    batch = json.loads(batch_path.read_text(encoding="utf-8"))

    season = str(batch["season"])
    track = str(batch["track"])
    purpose = str(batch.get("purpose", "validation"))
    checkpoint_gw = batch.get("checkpoint_gw")
    origins_in = sorted(batch["origins"], key=lambda o: int(o["gw"]))

    origins_by_gw, ext_catalog, existing_req = _load_existing_season_state(root, season)
    shared_chip_calendar = list(batch.get("shared_chip_calendar", existing_req.get("shared_chip_calendar", [])))
    anchor = dict(batch.get("anchor", existing_req.get("anchor", {})))
    if checkpoint_gw is None:
        checkpoint_gw = existing_req.get("checkpoint_gw")

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
            sources_out[role] = {
                **{k: v for k, v in spec.items() if k not in ("file", "path")},
                "source_id": sid,
            }
        origins_by_gw[gw] = {
            "season": season,
            "gw": gw,
            "deadline": origin["deadline"],
            "prev_deadline": origin.get("prev_deadline"),
            "max_kickoff_utc": origin["max_kickoff_utc"],
            "disclosed_limitations": origin.get("disclosed_limitations", []),
            "sources": sources_out,
        }

    _persist_cumulative_admissions(
        root,
        season,
        track=track,
        purpose=purpose,
        checkpoint_gw=checkpoint_gw,
        shared_chip_calendar=shared_chip_calendar,
        anchor=anchor,
        origins_by_gw=origins_by_gw,
        ext_catalog=ext_catalog,
    )

    _, prefix_end, first_blocked, gap_status, gap_reasons = _assess_season_admissions(root, season)
    max_gw = max(origins_by_gw, default=0)
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


def _load_certified_sparse_v2_params(
    cert_path: Path | None = None,
    *,
    expected_digest: str | None = None,
) -> dict[str, Any]:
    from commands.manage_champion_adoption import CERTIFICATION_DIGEST_EXPECTED

    path = cert_path or DEFAULT_CERTIFICATION_RESULT_PATH
    if not path.is_file():
        raise FileNotFoundError(f"Certified sparse v2 artifact not found: {path}")
    exp = expected_digest if expected_digest is not None else CERTIFICATION_DIGEST_EXPECTED
    ver = verify_certification_artifacts(
        path.parent,
        expected_digest=exp,
        project_root=PROJECT_ROOT,
        check_evaluator_revisions=True,
    )
    if not ver["passed"]:
        raise ValueError(f"Sparse confirmation verification failed for {path}: {'; '.join(ver['errors'])}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("certified") is not True:
        raise ValueError(f"Sparse confirmation artifact is not certified: {path}")
    if data.get("certification_digest") != exp:
        raise ValueError(f"Sparse confirmation certification_digest mismatch for {path}")
    return data


def _build_default_protocol(
    *,
    development_season: str,
    validation_season: str,
    approval_reference: str,
    dev_windows: list[int],
    time_limit_seconds: float,
    max_family_attempts: int,
    s1_guard_baseline_mode: str | None = None,
    protocol_version: str = "v2.0",
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
    review_gws = [15, 30, 38]
    cert_v2: dict[str, Any] | None = None
    if protocol_version == "v2.0":
        cert_v2 = _load_certified_sparse_v2_params()
        c_cfg = cert_v2["certified_protocol_config"]
        review_gws = [int(g) for g in c_cfg.get("confirmation_checkpoints", [15, 30, 38])]

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
            "applicability": {
                s: {
                    name: (
                        "inapplicable_native"
                        if name == "defcon_points_mse" and s in ("2023-24", "2024-25")
                        else "required"
                    )
                    for name in guards
                }
                for s in windows
            },
        },
        "live_review": {
            "mode": "fplcache",
            "review_gameweeks": review_gws,
            "settlement_delay_hours": 24,
            "early_harm_min_gw": 6,
            "early_harm_p_threshold": EARLY_HARM_P_THRESHOLD,
        },
    }
    if s1_guard_baseline_mode is not None:
        protocol["s1_guard_baseline_mode"] = s1_guard_baseline_mode
    proto_decl_hash = content_hash(protocol)
    if protocol_version == "v2.0":
        assert cert_v2 is not None
        c_cfg = cert_v2["certified_protocol_config"]
        base_cfg = build_certified_protocol_config(
            calibrated_superiority_alphas=c_cfg["calibrated_superiority_alphas"],
            gw1_4_material_loss_limit=float(c_cfg["gw1_4_material_loss_limit"]),
            statistical_early_harm_mode=c_cfg["statistical_early_harm_mode"],
            certification_digest=str(cert_v2["certification_digest"]),
            development_season=development_season,
            confirmation_season=validation_season,
        )
        stat_cfg = replace(
            base_cfg,
            approved_by_human=True,
            approval_reference=approval_reference,
            max_family_attempts=max_family_attempts,
            evidence_protocol_hash=proto_decl_hash,
        )
    elif protocol_version == "v1.0":
        stat_cfg = StatisticalProtocolConfig(
            development_season=development_season,
            confirmation_season=validation_season,
            approved_by_human=True,
            approval_reference=approval_reference,
            max_family_attempts=max_family_attempts,
            required_projection_guards=tuple(guards),
            evidence_protocol_hash=proto_decl_hash,
        )
    else:
        raise ValueError(f"Unsupported protocol_version '{protocol_version}'")
    protocol["statistics"] = stat_cfg.to_dict()
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


def _write_staged_checkpoint_admission(
    root: Path,
    *,
    season: str,
    end_gw: int,
    training_blob_refs: Mapping[str, Mapping[str, str]],
    tag: str = "",
) -> dict[str, str]:
    """Assemble an immutable staged admission context for a checkpoint without mutating `admissions/`."""
    adm_dir = root / "admissions" / season
    exact_file = adm_dir / f"gw{end_gw:02d}.json"
    if not exact_file.is_file():
        files = sorted(adm_dir.glob("gw*.json"))
        if not files:
            raise ValueError(f"No admission files found for {season}")
        exact_file = files[-1]
    base_ctx = json.loads(exact_file.read_bytes())
    merged_cat: dict[str, Any] = {}
    for gw in range(1, end_gw + 1):
        gw_file = adm_dir / f"gw{gw:02d}.json"
        if gw_file.is_file():
            merged_cat.update(json.loads(gw_file.read_bytes()).get("catalog", {}))
    merged_cat.update({k: dict(v) for k, v in training_blob_refs.items()})
    req = dict(base_ctx["request"])
    req["origins"] = [o for o in req.get("origins", ()) if int(o["gw"]) <= end_gw]
    if req.get("track") == "validation_fplcache":
        req["checkpoint_gw"] = end_gw
    suffix = f"_{tag}" if tag else ""
    rel = f"checkpoints/{season}/gw{end_gw:02d}{suffix}_admission.json"
    return _write_rel_json(root, rel, {"request": req, "catalog": merged_cat})


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
) -> tuple[
    dict[str, str],
    list[ReplayDeadlineRecord],
    list[dict[str, Any]],
    dict[str, str],
    dict[str, Any],
    dict[str, dict[str, str]],
]:
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
    training_blob_refs: dict[str, dict[str, str]] = {}
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
        # Use explicit seed fixtures when provided; else reconstruct from seed_history
        raw_seed_fx = seed_obj.get("fixtures")
        if isinstance(raw_seed_fx, list) and raw_seed_fx:
            seed_fx = [
                {
                    "id": int(fx["id"]),
                    "gameweek_id": int(fx.get("gameweek_id", fx.get("event", 1))),
                    "home_club_id": int(fx.get("home_club_id", fx.get("team_h", 1))),
                    "away_club_id": int(fx.get("away_club_id", fx.get("team_a", 2))),
                    "finished": True,
                    "kickoff_time": str(fx.get("kickoff_time", origin["deadline"])),
                    "team_h_difficulty": int(fx.get("team_h_difficulty", 3)),
                    "team_a_difficulty": int(fx.get("team_a_difficulty", 3)),
                }
                for fx in raw_seed_fx
            ]
        else:
            seed_fx_seen: set[int] = set()
            seed_fx = []
            for srow in seed_obj.get("history", []):
                sfid = int(srow.get("fixture_id", 0))
                if sfid > 0 and sfid not in seed_fx_seen:
                    seed_fx_seen.add(sfid)
                    was_home = bool(srow.get("was_home", True))
                    club_id = int(srow.get("club_id", 1))
                    opp_id = int(srow.get("opponent_club_id", 2 if club_id == 1 else 1))
                    seed_fx.append(
                        {
                            "id": sfid,
                            "gameweek_id": int(srow.get("gameweek_id", 1)),
                            "home_club_id": club_id if was_home else opp_id,
                            "away_club_id": opp_id if was_home else club_id,
                            "finished": True,
                            "kickoff_time": str(srow.get("kickoff_time", origin["deadline"])),
                            "team_h_difficulty": int(srow.get("team_h_difficulty", 3)),
                            "team_a_difficulty": int(srow.get("team_a_difficulty", 3)),
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

        training_blob_refs[src_digest] = {"blob_sha256": src_blob_sha, "relpath": store.relpath(src_blob_sha)}
        training_blob_refs[auth_digest] = {"blob_sha256": auth_blob_sha, "relpath": store.relpath(auth_blob_sha)}

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
    return anchor_ref, records, issues, trace_ref, entry, training_blob_refs


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
    s1_mode: str | None = None
    if args.s1_guard_baseline is not None or (season == "2027-28" and (root / "s1_guard_baseline.json").is_file()):
        if season != "2027-28":
            raise ValueError("s1_guard_baseline_season_archive_transition permitted only on 2027-28")
        s1_mode = "s1_guard_baseline_season_archive_transition"

    dev_gws, dev_prefix_end, _, _, _ = _assess_season_admissions(root, dev_season)
    dev_windows = list(range(1, dev_prefix_end + 1)) if dev_prefix_end >= 2 else [1, 2]
    if (root / "protocol.json").is_file():
        protocol = json.loads((root / "protocol.json").read_bytes())
        if str(args.protocol_version) == "v2.0":
            from commands.manage_champion_adoption import CERTIFICATION_DIGEST_EXPECTED

            proto_stats = protocol.get("statistics", {}) if isinstance(protocol, dict) else {}
            if proto_stats.get("protocol_version") != "v2.0":
                raise ValueError("Existing protocol.json is not protocol_version='v2.0'")
            if proto_stats.get("certification_digest") != CERTIFICATION_DIGEST_EXPECTED:
                raise ValueError(
                    "Existing protocol.json certification_digest does not match CERTIFICATION_DIGEST_EXPECTED"
                )
        protocol_hash = content_hash(protocol)
    else:
        protocol = _build_default_protocol(
            development_season=dev_season,
            validation_season=season,
            approval_reference=str(args.approval_reference),
            dev_windows=dev_windows,
            time_limit_seconds=float(args.time_limit_seconds),
            max_family_attempts=int(args.max_family_attempts),
            s1_guard_baseline_mode=s1_mode,
            protocol_version=str(args.protocol_version),
        )
        _write_rel_json(root, "protocol.json", protocol)
        _write_rel_json(root, "parameters.json", {})
        protocol_hash = content_hash(protocol)

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

    cert_digest_val = protocol.get("statistics", {}).get("certification_digest")
    selection = ModelSelection(
        champion=champion,
        candidates=candidates,
        provisional_active=candidates[0],
        podium_frozen_season=season,
        podium_sealed=True,
        frozen_protocol_hash=protocol_hash,
        frozen_certification_digest=str(cert_digest_val) if isinstance(cert_digest_val, str) else None,
    )
    sel_file = root / "selection.json"
    if sel_file.is_file():
        if load_model_selection(sel_file) != selection:
            raise ValueError("Selection already sealed with different configuration")
    else:
        save_model_selection(selection, sel_file)

    source_hash = current_model_source_hash()
    parameters_hash = content_hash({})

    # Prepare S-1 development selection trace if S-1 admissions exist
    s1_trace_ref: dict[str, str] | None = None
    if dev_prefix_end >= len(dev_windows):
        _, _, _, trace_meta, _, _s1_blobs = _replay_season_prefix(
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

    slate = json.loads((root / "slate.json").read_bytes())
    selection = load_model_selection(root / "selection.json")
    protocol = json.loads((root / "protocol.json").read_bytes())
    expected_checkpoints = tuple(
        int(gw) for gw in protocol.get("statistics", {}).get("confirmation_checkpoints", [15, 30, 38])
    )
    if checkpoint_gw not in expected_checkpoints:
        raise ValueError(f"Replay checkpoint_gw must be in {expected_checkpoints}; got {checkpoint_gw}")
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
        c
        for c in selection.candidates
        if not exclusions.is_candidate_excluded(c, slate_id=str(slate["slate_id"]), season=season)
    ]
    prior_excluded = [c for c in selection.candidates if c not in active_candidates]
    if not active_candidates:
        raise ValueError("All frozen finalists have been excluded in ExclusionLedger")

    dev_season = str(slate["development_season"])
    dev_windows = list(protocol["windows"][dev_season])
    admitted_s1, _prefix_end_s1, first_blocked_s1, _gap_s1, gap_reasons_s1 = _assess_season_admissions(root, dev_season)
    s1_baseline_ref: dict[str, str] | None = None
    if protocol.get("s1_guard_baseline_mode") == "s1_guard_baseline_season_archive_transition" and (
        root / "s1_guard_baseline.json"
    ).is_file():
        s1_file = root / "s1_guard_baseline.json"
        s1_baseline_ref = {"path": "s1_guard_baseline.json", "sha256": hashlib.sha256(s1_file.read_bytes()).hexdigest()}
    elif _prefix_end_s1 < max(dev_windows):
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
        _, _, _, _s1_trace, s1_entry, s1_blobs = _replay_season_prefix(
            root,
            season=dev_season,
            model_name=selection.champion,
            admitted_gws=admitted_s1,
            end_gw=max(dev_windows),
            source_hash=source_hash,
            protocol_hash=protocol_hash,
            policy=policy,
        )
        adm_s1_ref = _write_staged_checkpoint_admission(
            root,
            season=dev_season,
            end_gw=max(dev_windows),
            training_blob_refs=s1_blobs,
            tag="s1",
        )
        for iss in s1_entry["issues"]:
            iss["admission"] = adm_s1_ref
        replays.append(s1_entry)
        for gw in dev_windows:
            guard_outcome_sources.append(
                {
                    "season": dev_season,
                    "gameweek": gw,
                    "admission": adm_s1_ref,
                }
            )

    # Active season shared guard outcome sources & replays
    all_s_training_blobs: dict[str, dict[str, str]] = {}
    _, champ_records, _, _champ_trace, champ_entry, champ_blobs = _replay_season_prefix(
        root,
        season=season,
        model_name=selection.champion,
        admitted_gws=admitted_s,
        end_gw=checkpoint_gw,
        source_hash=source_hash,
        protocol_hash=protocol_hash,
        policy=policy,
    )
    all_s_training_blobs.update(champ_blobs)
    cum_net: dict[str, float] = {selection.champion: float(sum(r.net_points for r in champ_records))}
    cand_entries: list[dict[str, Any]] = []

    for cand in selection.candidates:
        attempt = [r for r in all_records_reg if r.candidate_name == cand and r.protocol_hash == protocol_hash][-1]
        attempt_ids[cand] = attempt.attempt_id
        dev_sel_rel = f"development_selections/{cand}.json"
        dev_selections[cand] = {"path": dev_sel_rel, "sha256": hashlib.sha256((root / dev_sel_rel).read_bytes()).hexdigest()}

    for cand in active_candidates:
        attempt_id = attempt_ids[cand]

        _, cand_records, _, _cand_trace, cand_entry, cand_blobs = _replay_season_prefix(
            root,
            season=season,
            model_name=cand,
            admitted_gws=admitted_s,
            end_gw=checkpoint_gw,
            source_hash=source_hash,
            protocol_hash=protocol_hash,
            policy=policy,
        )
        all_s_training_blobs.update(cand_blobs)
        cand_entries.append(cand_entry)
        cum_net[cand] = float(sum(r.net_points for r in cand_records))

        scores = [pair_replay_score(season, c_rec, ch_rec) for c_rec, ch_rec in zip(cand_records, champ_records, strict=True)]
        trace_hash = compute_score_trace_hash(scores)
        latest = registry.get_attempt(attempt_id)
        if latest is None or latest.completed_gameweeks != tuple(range(1, checkpoint_gw + 1)):
            registry.record_checkpoint(
                attempt_id,
                checkpoint_gw=checkpoint_gw,
                completed_gameweeks=tuple(range(1, checkpoint_gw + 1)),
                score_trace_hash=trace_hash,
            )

    adm_s_ref = _write_staged_checkpoint_admission(
        root,
        season=season,
        end_gw=checkpoint_gw,
        training_blob_refs=all_s_training_blobs,
    )
    for gw in range(1, checkpoint_gw + 1):
        guard_outcome_sources.append({"season": season, "gameweek": gw, "admission": adm_s_ref})
    for replay_entry in (champ_entry, *cand_entries):
        for iss in replay_entry["issues"]:
            iss["admission"] = adm_s_ref
        replays.append(replay_entry)

    gw38_final_ko: str | None = args.gw38_final_kickoff_utc
    if gw38_final_ko is None and checkpoint_gw == expected_checkpoints[-1]:
        req_cp, cat_cp, _ = admitted_s[checkpoint_gw]
        gw_origin = next(o for o in req_cp["origins"] if o["season"] == season and int(o["gw"]) == checkpoint_gw)
        kickoff_candidates = [_utc(str(gw_origin["max_kickoff_utc"]))]
        fx_bytes = cat_cp.get(str(gw_origin["sources"]["fixtures"].get("source_id")))
        if fx_bytes is not None:
            for fx_row in parse_fixtures_csv_window(fx_bytes, checkpoint_gw):
                if int(fx_row["event"]) == checkpoint_gw and fx_row.get("kickoff_time"):
                    kickoff_candidates.append(_utc(str(fx_row["kickoff_time"])))
        gw38_final_ko = max(kickoff_candidates).isoformat()

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
        "excluded_finalists": prior_excluded,
        "evaluated_at_utc": args.evaluated_at_utc or datetime.now(UTC).isoformat(),
        "confirmation_attempt_ids": attempt_ids,
        "development_selections": dev_selections,
        "replays": replays,
        "guard_outcome_sources": guard_outcome_sources,
    }
    if gw38_final_ko is not None:
        payload["gw38_final_kickoff_utc"] = gw38_final_ko
    if s1_baseline_ref is not None:
        payload["s1_guard_baseline"] = s1_baseline_ref
    req_path.write_bytes(canonical_bytes(payload) + b"\n")

    expected_cert: str | None = None
    if protocol.get("statistics", {}).get("protocol_version") == "v2.0":
        from commands.manage_champion_adoption import CERTIFICATION_DIGEST_EXPECTED

        expected_cert = CERTIFICATION_DIGEST_EXPECTED
    bundle = write_checkpoint_recommendation_bundle(
        req_path,
        bundle_path,
        expected_certification_digest=expected_cert,
    )
    coordinator = SharedReservationCoordinator(root)
    if "newly_excluded_finalists" in bundle:
        excl_details = dict(bundle.get("exclusion_details", {}))
        for cand in bundle.get("newly_excluded_finalists", ()):
            if not exclusions.is_candidate_excluded(str(cand), slate_id=str(slate["slate_id"]), season=season):
                detail_obj = excl_details.get(str(cand), {})
                reason_code = str(detail_obj.get("reason_code", "early_harm"))
                reasons_list = detail_obj.get("reasons") or bundle.get("reasons", [])
                coordinator.record_exclusion_under_reservation(
                    holder="validation-collector",
                    slate_id=str(slate["slate_id"]),
                    season=season,
                    candidate_name=str(cand),
                    checkpoint_gw=checkpoint_gw,
                    reason_code=reason_code,
                    details="; ".join(str(r) for r in reasons_list) or reason_code,
                    evidence_hash=str(bundle.get("bundle_hash")) if bundle.get("bundle_hash") else None,
                )
    elif bundle.get("action") in ("rotate_to_backup", "fallback_to_champion"):
        for reason in bundle.get("reasons", []):
            reason_str = str(reason)
            if "Early-Harm" in reason_str:
                match_cand = re.search(r"Provisional Active '([^']+)'", reason_str)
                harmed = match_cand.group(1) if match_cand else (selection.provisional_active or active_candidates[0])
                if not exclusions.is_candidate_excluded(harmed, slate_id=str(slate["slate_id"]), season=season):
                    coordinator.record_exclusion_under_reservation(
                        holder="validation-collector",
                        slate_id=str(slate["slate_id"]),
                        season=season,
                        candidate_name=harmed,
                        checkpoint_gw=checkpoint_gw,
                        reason_code="early_harm",
                        details=reason_str,
                        evidence_hash=str(bundle.get("bundle_hash")) if bundle.get("bundle_hash") else None,
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

    active_candidates_post = [
        c
        for c in selection.candidates
        if not exclusions.is_candidate_excluded(c, slate_id=str(slate["slate_id"]), season=season)
    ]
    eligible_scores = {m: v for m, v in cum_net.items() if m == selection.champion or m in active_candidates_post}
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


def _compute_observed_components_for_row(row: Mapping[str, Any], pos_id: int, season: str) -> dict[str, float]:
    mins = int(row.get("minutes", 0) or 0)
    pos_map: dict[int, Literal["GK", "D", "M", "F"]] = {1: "GK", 2: "D", 3: "M", 4: "F"}
    pos_code: Literal["GK", "D", "M", "F"] = pos_map.get(pos_id, "M")
    min_pts = 2.0 if mins >= 60 else (1.0 if mins > 0 else 0.0)
    goals = int(row.get("goals_scored", 0) or 0)
    assists = int(row.get("assists", 0) or 0)
    cs = int(row.get("clean_sheets", 0) or 0)
    gc = int(row.get("goals_conceded", 0) or 0)
    saves = int(row.get("saves", 0) or 0)
    ps = int(row.get("penalties_saved", 0) or 0)
    pm = int(row.get("penalties_missed", 0) or 0)
    og = int(row.get("own_goals", 0) or 0)
    yc = int(row.get("yellow_cards", 0) or 0)
    rc = int(row.get("red_cards", 0) or 0)
    bonus = int(row.get("bonus", 0) or 0)
    dc = int(row.get("defensive_contribution", 0) or 0)
    cs_pts = float(cs) * {"GK": 4.0, "D": 4.0, "M": 1.0, "F": 0.0}[pos_code]
    gc_pts = float(-(gc // 2)) if pos_code in ("GK", "D") else 0.0
    saves_pts = float(saves // 3) if pos_code == "GK" else 0.0
    dc_units = 1.0 if ((pos_code == "D" and dc >= 10) or (pos_code in ("M", "F") and dc >= 12)) else 0.0
    defaults: dict[str, float] = {
        "actual_points": float(row.get("total_points", 0) or 0),
        "actual_minutes": float(mins),
        "actual_minutes_points": min_pts,
        "actual_goals_points": float(event_points("goals", pos_code, float(goals), rules_version=season)),
        "actual_assists_points": float(assists * 3.0),
        "actual_clean_sheet_points": cs_pts,
        "actual_conceded_points": gc_pts,
        "actual_saves_points": saves_pts,
        "actual_penalties_saved_points": float(ps * 5.0),
        "actual_penalties_missed_points": float(pm * -2.0),
        "actual_own_goals_points": float(og * -2.0),
        "actual_yellow_cards_points": float(yc * -1.0),
        "actual_red_cards_points": float(rc * -3.0),
        "actual_bonus_points": float(bonus),
        "actual_defcon_points": (
            0.0
            if season in ("2023-24", "2024-25")
            else float(event_points("defensive_contributions", pos_code, dc_units, rules_version=season))
        ),
    }
    return {
        acol: float(row[acol]) if acol in row and row[acol] is not None else defaults[acol]
        for _gname, (_fcol, acol, _loss, _units) in GUARD_SEMANTICS.items()
    }


def _scorecard_command(args: argparse.Namespace) -> int:
    """Compute verified common-prefix weekly scorecard without touching registry or checkpoint bundles."""
    root = Path(args.evidence_root).resolve()
    season = str(args.season)
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
    through_gw = int(args.through_gw) if args.through_gw is not None else int(prefix_end_s)
    if through_gw < 1:
        raise ValueError(f"No settled empirical gameweeks available for weekly scorecard in '{season}'")
    if prefix_end_s < through_gw:
        sc_gap = _build_scorecard(
            root,
            slate_id=str(slate["slate_id"]),
            season=season,
            checkpoint_gw=through_gw,
            settled_through_gw=prefix_end_s,
            gap_status=gap_status_s if gap_status_s != "complete" else "transient_gap",
            first_blocked_gw=first_blocked_s or (prefix_end_s + 1),
            reason_codes=tuple(gap_reasons_s or [f"incomplete_prefix_gw_{prefix_end_s}_of_{through_gw}"]),
        )
        write_scorecard(root, sc_gap)
        raise ValueError(
            f"Weekly scorecard through GW{through_gw} blocked at GW{sc_gap.first_blocked_gw} ({sc_gap.gap_status})"
        )

    exclusions = ExclusionLedger(root / "exclusions.jsonl")
    active_candidates = [
        c
        for c in selection.candidates
        if not exclusions.is_candidate_excluded(c, slate_id=str(slate["slate_id"]), season=season)
    ]
    _, champ_records, _, _champ_trace, _champ_entry, _champ_blobs = _replay_season_prefix(
        root,
        season=season,
        model_name=selection.champion,
        admitted_gws=admitted_s,
        end_gw=through_gw,
        source_hash=source_hash,
        protocol_hash=protocol_hash,
        policy=policy,
    )
    cum_net: dict[str, float] = {selection.champion: float(sum(r.net_points for r in champ_records))}
    for cand in active_candidates:
        _, cand_records, _, _cand_trace, _cand_entry, _cand_blobs = _replay_season_prefix(
            root,
            season=season,
            model_name=cand,
            admitted_gws=admitted_s,
            end_gw=through_gw,
            source_hash=source_hash,
            protocol_hash=protocol_hash,
            policy=policy,
        )
        cum_net[cand] = float(sum(r.net_points for r in cand_records))

    podium_rank = {c: idx for idx, c in enumerate(selection.candidates)}
    weekly_leader = max(
        cum_net,
        key=lambda m: (cum_net[m], m == selection.champion, -podium_rank.get(m, len(selection.candidates))),
    )
    sc = _build_scorecard(
        root,
        slate_id=str(slate["slate_id"]),
        season=season,
        checkpoint_gw=through_gw,
        settled_through_gw=through_gw,
        gap_status="complete" if (prefix_end_s == through_gw and first_blocked_s is None) else gap_status_s,
        first_blocked_gw=None if (prefix_end_s >= through_gw and first_blocked_s is None) else first_blocked_s,
        reason_codes=(),
        cumulative_net_points=cum_net,
        weekly_leader=weekly_leader,
        checkpoint_action="weekly_scorecard",
        bundle_hash=None,
    )
    write_scorecard(root, sc)
    print(
        json.dumps(
            {
                "command": "scorecard",
                "season": season,
                "through_gw": through_gw,
                "weekly_leader": weekly_leader,
                "cumulative_net_points": cum_net,
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
    players_df = pd.read_parquet(archive_dir / "players.parquet") if (archive_dir / "players.parquet").is_file() else pd.DataFrame()
    pos_by_player: dict[int, int] = (
        {
            int(r["id"]): int(r["position_id"])
            for r in cast(pd.DataFrame, players_df[["id", "position_id"]]).to_dict(orient="records")
        }
        if not players_df.empty and {"id", "position_id"}.issubset(players_df.columns)
        else {}
    )

    h = hashlib.sha256()
    for fname in sorted(p.name for p in archive_dir.glob("*.parquet")):
        h.update(fname.encode("utf-8"))
        h.update(hashlib.sha256((archive_dir / fname).read_bytes()).digest())
    archive_manifest_sha = h.hexdigest()

    champion_name = str(args.champion)
    rows: list[dict[str, Any]] = []
    gw_ids = sorted(int(g) for g in gw_df["id"].unique())
    has_full_tables = (
        (archive_dir / "clubs.parquet").is_file()
        and (archive_dir / "fixtures.parquet").is_file()
        and len(gw_ids) >= 2
        and {"expected_goals", "assists", "goals_scored"}.issubset(perf_df.columns)
    )
    if has_full_tables:
        model = get_model(champion_name)
        deadlines = (
            gw_df.set_index("id")["deadline_time"].to_dict()
            if {"id", "deadline_time"}.issubset(gw_df.columns)
            else {}
        )
        max_gw = max(gw_ids)
        forecast_cols = [fcol for _gname, (fcol, _acol, _loss, _units) in GUARD_SEMANTICS.items()]
        comp_rename = {
            "actual_xp_minutes": "actual_minutes_points",
            "actual_xp_goals": "actual_goals_points",
            "actual_xp_assists": "actual_assists_points",
            "actual_xp_clean_sheet": "actual_clean_sheet_points",
            "actual_xp_conceded": "actual_conceded_points",
            "actual_xp_saves": "actual_saves_points",
            "actual_xp_penalties_saved": "actual_penalties_saved_points",
            "actual_xp_penalties_missed": "actual_penalties_missed_points",
            "actual_xp_own_goals": "actual_own_goals_points",
            "actual_xp_yellow_cards": "actual_yellow_cards_points",
            "actual_xp_red_cards": "actual_red_cards_points",
            "actual_xp_bonus": "actual_bonus_points",
            "actual_xp_defcon": "actual_defcon_points",
        }
        for issue_gw in gw_ids:
            df_feat = build_features(
                archive_dir,
                target_gw=issue_gw,
                horizon=6,
                as_of_gw=issue_gw,
                target_deadline=deadlines.get(issue_gw),
                season=dev_season,
            )
            if df_feat.empty:
                continue
            fit_fn = getattr(model, "fit", None)
            if callable(fit_fn):
                fit_fn(history_before_target(perf_df, issue_gw, deadlines.get(issue_gw), False))
            df_proj = model.predict(df_feat, horizon=6)
            avail_fcols = [c for c in forecast_cols if c in df_proj.columns]
            grouped_proj = cast(
                pd.DataFrame,
                df_proj.groupby(["player_id", "gameweek_id"], as_index=False)[avail_fcols].sum(),
            )
            for target_gw in range(issue_gw, min(max_gw, issue_gw + 5) + 1):
                gw_perf_raw = cast(pd.DataFrame, perf_df[perf_df["gameweek_id"] == target_gw])
                if gw_perf_raw.empty:
                    continue
                gw_comp = _build_actual_components(gw_perf_raw.copy(), df_feat).rename(columns=comp_rename)
                gw_comp["actual_points"] = gw_comp["total_points"]
                gw_comp["actual_minutes"] = gw_comp["minutes"]
                obs_by_pid: dict[int, dict[str, float]] = {}
                for orow in gw_comp.to_dict(orient="records"):
                    pid_o = int(orow["player_id"])
                    obs_by_pid.setdefault(
                        pid_o,
                        {acol: 0.0 for _gname, (_fcol, acol, _loss, _units) in GUARD_SEMANTICS.items()},
                    )
                    for _gname, (_fcol, acol, _loss, _units) in GUARD_SEMANTICS.items():
                        obs_by_pid[pid_o][acol] += float(orow.get(acol, 0.0) or 0.0)
                sub_proj = cast(pd.DataFrame, grouped_proj[grouped_proj["gameweek_id"] == target_gw])
                for prow in sub_proj.to_dict(orient="records"):
                    pid_p = int(prow["player_id"])
                    if pid_p not in obs_by_pid:
                        continue
                    entry_full: dict[str, Any] = {
                        "season": dev_season,
                        "issue_gw": int(issue_gw),
                        "gameweek_id": int(target_gw),
                        "player_id": pid_p,
                    }
                    for fcol in forecast_cols:
                        entry_full[fcol] = float(prow.get(fcol, 0.0) or 0.0)
                    entry_full["_observed"] = obs_by_pid[pid_p]
                    rows.append(entry_full)

    if not rows:
        for row in perf_df.to_dict(orient="records"):
            pid = int(row["player_id"])
            gw_val = int(row["gameweek_id"])
            pos_id = int(row.get("position_id") or pos_by_player.get(pid, 3))
            entry: dict[str, Any] = {
                "season": dev_season,
                "issue_gw": gw_val,
                "gameweek_id": gw_val,
                "player_id": pid,
            }
            for _gname, (fcol, _acol, _loss, _units) in GUARD_SEMANTICS.items():
                entry[fcol] = float(row.get(fcol, 0.0) or 0.0)
            entry["_observed"] = _compute_observed_components_for_row(row, pos_id, dev_season)
            rows.append(entry)

    baseline = {
        "schema_version": 1,
        "season": dev_season,
        "target_validation_season": season,
        "champion_name": champion_name,
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


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Produce portable ADR 0069/0070 validation evidence.")
    sub = parser.add_subparsers(dest="subcommand", required=True)

    p_collect = sub.add_parser("collect", help="Collect empirical origin blobs into evidence root")
    p_collect.add_argument("--evidence-root", required=True)
    p_collect.add_argument("--batch-json", default=None)
    p_collect.add_argument("--season", default=None)
    p_collect.add_argument("--slate-id", default="default-slate")
    p_collect.add_argument("--mode", choices=("auto", "pre_deadline", "post_settlement"), default="auto")
    p_collect.add_argument("--fpl-api-base", default=DEFAULT_FPL_API_BASE)
    p_collect.add_argument("--now-utc", default=None)
    p_collect.add_argument("--max-concurrency", type=int, default=3)
    p_collect.add_argument("--seed-file", default=None)

    p_freeze = sub.add_parser("freeze", help="Seal slate, protocol, runtime bindings, and finalist registrations")
    p_freeze.add_argument("--evidence-root", required=True)
    p_freeze.add_argument("--season", required=True)
    p_freeze.add_argument("--development-season", required=True)
    p_freeze.add_argument("--champion", required=True)
    p_freeze.add_argument("--candidates", action="append", required=True)
    p_freeze.add_argument("--slate-id", required=True)
    p_freeze.add_argument("--approval-reference", required=True)
    p_freeze.add_argument("--time-limit-seconds", type=float, default=DEFAULT_CERTIFIED_TIME_LIMIT_SECONDS)
    p_freeze.add_argument("--max-family-attempts", type=int, default=1)
    p_freeze.add_argument("--s1-guard-baseline", default=None)
    p_freeze.add_argument("--protocol-version", choices=("v1.0", "v2.0"), default="v2.0")

    p_replay = sub.add_parser("replay", help="Run/resume prefix-reusable replay and evaluate checkpoint")
    p_replay.add_argument("--evidence-root", required=True)
    p_replay.add_argument("--season", required=True)
    p_replay.add_argument("--checkpoint-gw", type=int, required=True)
    p_replay.add_argument("--output-bundle", default=None)
    p_replay.add_argument("--snapshots-dir", default=None)
    p_replay.add_argument("--time-limit-seconds", type=float, default=None)
    p_replay.add_argument("--evaluated-at-utc", default=None)
    p_replay.add_argument("--gw38-final-kickoff-utc", default=None)

    p_boot = sub.add_parser("bootstrap-s1-baseline", help="Generate preregistered 2027-28 S-1 Season Archive transition baseline")
    p_boot.add_argument("--evidence-root", required=True)
    p_boot.add_argument("--season", required=True)
    p_boot.add_argument("--development-season", required=True)
    p_boot.add_argument("--archive-processed-dir", required=True)
    p_boot.add_argument("--champion", required=True)

    p_scorecard = sub.add_parser("scorecard", help="Publish intermediate weekly scorecard without touching registry")
    p_scorecard.add_argument("--evidence-root", required=True)
    p_scorecard.add_argument("--season", required=True)
    p_scorecard.add_argument("--through-gw", type=int, default=None)
    p_scorecard.add_argument("--time-limit-seconds", type=float, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    from backtesting.verification_cache import verification_call_scope

    configure_utf8_stdio()
    parser = _build_parser()

    args = parser.parse_args(argv)
    with verification_call_scope():
        if args.subcommand == "collect":
            return _collect_command(args)
        if args.subcommand == "freeze":
            return _freeze_command(args)
        if args.subcommand == "replay":
            return _replay_command(args)
        if args.subcommand == "scorecard":
            return _scorecard_command(args)
        if args.subcommand == "bootstrap-s1-baseline":
            return _bootstrap_s1_baseline_command(args)
        raise ValueError(f"Unknown subcommand: {args.subcommand}")


if __name__ == "__main__":
    raise SystemExit(main())
