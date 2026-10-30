"""Retained toy source closure, real model forecasts and native solver outputs."""

from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import patch
import json

import pandas as pd

from backtesting.confirmation_registry import ConfirmationRegistry
from backtesting.data_admission import assess_origins, require_admitted, require_input
from backtesting.evidence_statistics import StatisticalProtocolConfig, compute_score_trace_hash
from backtesting.forecast_export import strict_solver_table
from backtesting.forecast_store import generate_forecast
from backtesting.ownership_anchor import solve_ownership_anchor
from backtesting.promotion_evidence import GUARD_SEMANTICS, canonical_bytes, content_hash, current_model_source_hash, native_solver_identity, pair_replay_score
from backtesting.replay_state import Outcome, OutcomeBatch, ReplayState
from backtesting.rolling_replay import QualityPolicy, record_to_dict, run_rolling_replay
from backtesting.season_rules import get_rules
from features.builder import EVENT_RATE_MAP
from test_data_admission import RETAINED, authorize, catalog, rehash, request
from test_forecast_inputs import retain

CANDIDATE = "metrics_component_hybrid"
CHAMPION = "calibrated_matchup_hybrid"


def save_material(root: Path, name: str, value: Any) -> dict[str, str]:
    raw = canonical_bytes(value)
    (root / name).write_bytes(raw)
    from hashlib import sha256

    return {"path": name, "sha256": sha256(raw).hexdigest()}


def encode_bytes(value: Any) -> Any:
    if isinstance(value, bytes):
        return {"bytes_hex": value.hex()}
    if isinstance(value, dict):
        return {key: encode_bytes(item) for key, item in value.items()}
    if isinstance(value, list):
        return [encode_bytes(item) for item in value]
    return value


def _context(season: str, gw: int) -> tuple[dict[str, Any], dict[str, bytes], str]:
    value = request()
    origin = value["origins"][0]
    cutoff = datetime(2025, 1, 1, 12, tzinfo=UTC) + timedelta(days=7 * (gw - 1))
    positions = [1] * 2 + [2] * 5 + [3] * 5 + [4] * 3
    players = [{"id": pid, "club": (pid - 1) % 5 + 1, "position": pos, "price": 50, "eligible": True, "ownership": 10.0 + pid, "availability": "available"} for pid, pos in enumerate(positions, 1)]
    targets = list(range(gw, gw + 6))
    fixtures = [{"id": target * 10 + club, "gw": target, "home_club": club, "away_club": club + 1} for target in targets for club in (1, 3, 5)]
    schedule = [{"player": player["id"], "gw": target, "status": "fixture", "fixture": next(fixture["id"] for fixture in fixtures if fixture["gw"] == target and player["club"] in (fixture["home_club"], fixture["away_club"])), "price": player["price"], "ownership": player["ownership"]} for player in players for target in targets]
    outcome_rows = [{**row, "status": "played", "points": 2, "minutes": 90, **{semantics[1]: (2.0 if semantics[1] in {"actual_points", "actual_minutes_points"} else 90.0 if semantics[1] == "actual_minutes" else 0.0) for semantics in GUARD_SEMANTICS.values()}} for row in schedule if row["gw"] == gw]
    origin.update(season=season, gw=gw, deadline=cutoff.isoformat(), universe=list(range(1, 16)), players=players, fixtures=fixtures, target_gws=targets, schedule=schedule, outcomes=outcome_rows, native_rules=get_rules(season).rules_id)
    origin["fixture_events"] = [{"fixture": fixture["id"], "gw": fixture["gw"], "status": "final", "home_club": fixture["home_club"], "away_club": fixture["away_club"], "changed_at": None, "finalized_at": (cutoff + timedelta(days=50)).isoformat()} for fixture in fixtures]
    for source in origin["sources"]:
        source.update(published_at=(cutoff - timedelta(hours=2)).isoformat(), captured_at=(cutoff - timedelta(hours=1)).isoformat(), retrieved_at=(cutoff + timedelta(hours=1)).isoformat())
        if source["role"] == "outcome":
            source.update(published_at=(cutoff + timedelta(days=51)).isoformat(), captured_at=(cutoff + timedelta(days=52)).isoformat(), retrieved_at=(cutoff + timedelta(days=53)).isoformat())
    rehash(value)
    authority = json.loads(RETAINED[value["authority_digest"]])
    authority.update(version=2, season=season, first_gw=gw, last_gw=gw, native_rules=origin["native_rules"], universe=list(range(1, 16)), seed_mapping={str(pid): f"s{pid}" for pid in range(1, 16)}, components={str(pid): ["points", "minutes", *GUARD_SEMANTICS] for pid in range(1, 16)}, eligible_since={str(pid): 1 for pid in range(1, 16)})
    value["authority_digest"] = retain(RETAINED, authority)
    authorize(value)
    entries = catalog(value)
    authority = json.loads(entries[value["authority_digest"]])
    prior_year = int(season[:4]) - 1
    seed_season = f"{prior_year}-{str(prior_year + 1)[-2:]}"
    events = {name: 0.0 for name, _ in EVENT_RATE_MAP}
    seed_rows = [{**events, "player_id": p["id"], "fixture_id": 99, "gameweek_id": 38, "kickoff_time": "2023-05-19T00:00:00Z", "minutes": 60 + p["id"] % 4 * 10, "total_points": 2 + p["id"] % 4, "starts": 1, "was_home": True, "opponent_club_id": 6, "goals_scored": 0.2 * (p["id"] % 3), "expected_goals": 0.25 * (p["id"] % 5), "assists": 0.1 * (p["id"] % 4), "expected_assists": 0.2 * (p["id"] % 3)} for p in players]
    training = {"version": 2, "url": "synthetic://" + "a" * 40, "revision": "a" * 40, "parser_version": "1", "seed_season": seed_season, "seed_registry_complete": True, "published_at": (cutoff - timedelta(hours=2)).isoformat(), "captured_at": (cutoff - timedelta(hours=1)).isoformat(), "timestamp_uncertainty_seconds": 0, "seed_mapping": authority["seed_mapping"], "tables": {"clubs": [{"id": club, "strength": 1000 + club * 30, "short_name": f"C{club}"} for club in range(1, 7)], "player_metadata": [{"id": p["id"], "web_name": f"Player {p['id']}"} for p in players], "target_fixtures": [{"id": f["id"], "gameweek_id": f["gw"], "home_club_id": f["home_club"], "away_club_id": f["away_club"], "team_h_difficulty": 3, "team_a_difficulty": 3} for f in fixtures], "history": [], "history_fixtures": [], "seed_players": [{"seed_key": f"s{p['id']}", "id": p["id"], "club_id": p["club"], "position_id": p["position"], "now_cost": 50} for p in players], "seed_history": seed_rows, "seed_fixtures": [{"id": 99, "gameweek_id": 38, "home_club_id": 1, "away_club_id": 6, "finished": True, "finalized_at": "2023-05-20T00:00:00Z"}]}}
    training_digest = retain(entries, training)
    authority["training_source_digests"] = [training_digest]
    value["authority_digest"] = retain(entries, authority)
    for source in origin["sources"]:
        source["parent_manifest"] = value["authority_digest"]
    report = assess_origins(value, entries)
    assert report[0]["input_ready"], report
    cap = require_input(value, entries, season, gw)
    training_authority = retain(entries, {"version": 2, "mode": "synthetic", "input_digest": cap.input_digest, "season": season, "gw": gw, "seed_identity": origin["seed_identity"], "source_digest": training_digest})
    assert report[0]["status"] == "admitted_synthetic", report
    require_admitted(value, entries, season, gw)
    return value, entries, training_authority


def build_evidence_fixture(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    guards = {name: {"forecast_field": semantics[0], "outcome_field": semantics[1], "loss": semantics[2], "units": semantics[3], "margin": 20.0 if name == "points_mse" else 10.0 if name == "minutes_mae" else 5.0, "alpha": 0.05, "direction": "lower_is_better"} for name, semantics in GUARD_SEMANTICS.items()}
    policy = QualityPolicy()
    declaration = {"horizon": 6, "windows": {season: [1, 2, 3] for season in ("2024-25", "2025-26")}, "guard_specs": guards, "quality_policy": asdict(policy), "chip_calendar": [], "solver_identity": native_solver_identity(), "projection_evaluation": {"leads": list(range(6)), "weights": [1.0] * 6, "population": "all_admitted_players", "missingness": "fail_closed", "aggregation": "weighted_paired_player_gameweek", "applicability": {season: {name: "inapplicable_native" if name == "defcon_points_mse" and season == "2024-25" else "required" for name in guards} for season in ("2024-25", "2025-26")}}}
    declaration["live_review"] = {"capture_job": {"module": "commands.capture_live_evidence", "before_deadline_minutes": 30, "clock": "execution_utc"}, "review_gameweeks": [4, 8], "settlement_delay_hours": 24, "material_loss_limit": 8.0}
    config = StatisticalProtocolConfig(bootstrap_draws=100, max_family_attempts=1, approved_by_human=True, approval_reference="fixture-protocol-approval", required_projection_guards=tuple(guards), evidence_protocol_hash=content_hash(declaration))
    protocol = {**declaration, "statistics": config.to_dict()}
    source_hash = current_model_source_hash()
    registry = ConfirmationRegistry(root / "registry.jsonl")
    request_payload: dict[str, Any] = {"version": "rolling-promotion-v1", "candidate_name": CANDIDATE, "former_champion": CHAMPION, "model_source_hash": source_hash, "protocol": save_material(root, "protocol.json", protocol), "parameters": save_material(root, "parameters.json", {}), "registry_path": "registry.jsonl", "confirmation_attempt_id": "fixture-attempt", "replays": [], "guard_outcome_sources": []}
    readiness: dict[str, Any] = {"version": 1, "candidate_name": CANDIDATE, "former_champion": CHAMPION, "protocol_hash": config.compute_hash(), "capture_before_deadline": True, "native_shadow_replay": True, "capture_job": {"module": "commands.capture_live_evidence", "before_deadline_minutes": 30, "clock": "execution_utc"}, "review_gameweeks": [4, 8], "settlement_delay_hours": 24, "material_loss_limit": 8.0, "readiness": "configured", "prospective_evidence_status": "pending", "dry_run_captures": {}}
    trajectories: dict[tuple[str, str], Any] = {}
    for season in ("2025-26", "2024-25"):
        contexts = {gw: _context(season, gw) for gw in range(1, 9)}
        for gw, (value, entries, _) in contexts.items():
            source_ref = save_material(root, f"context-{season}-{gw}.json", {"request": encode_bytes(value), "catalog": {digest: raw.hex() for digest, raw in entries.items()}})
            request_payload["guard_outcome_sources"].append({"season": season, "gameweek": gw, "admission": source_ref})
        first = contexts[1][0]["origins"][0]
        universe = pd.DataFrame(first["players"]).rename(columns={"id": "player_id", "club": "club_id", "position": "position_id", "price": "now_cost", "ownership": "selected_by_percent", "eligible": "is_eligible"})
        anchor = solve_ownership_anchor(universe, season)
        anchor_ref = save_material(root, f"anchor-{season}.json", anchor.to_dict())
        for model in (CANDIDATE, CHAMPION):
            forecasts: dict[int, pd.DataFrame] = {}
            batches: dict[int, OutcomeBatch] = {}
            issues: list[dict[str, Any]] = []
            for gw, (value, entries, training_authority) in contexts.items():
                if gw > 3:
                    continue
                cap = require_input(value, entries, season, gw)
                admitted = require_admitted(value, entries, season, gw)
                forecast_id, _, _ = generate_forecast(root / "forecast_cache", cap, value, entries, training_authority, model)
                from backtesting.forecast_store import load_forecast_verified

                frame, _ = load_forecast_verified(root / "forecast_cache", forecast_id, cap, value, entries, training_authority, model)
                wide = strict_solver_table(frame, cap, value, entries).rename(columns={"club": "club_id", "position": "position_id", "price": "now_cost"})
                wide["purchase_eligible"] = True
                forecasts[gw] = wide
                origin = value["origins"][0]
                immediate = [row for row in origin["outcomes"] if row["gw"] == gw]
                batches[gw] = OutcomeBatch(season, gw, admitted.evidence_digest, tuple((row["player"], Outcome(row["points"], row["minutes"], True)) for row in immediate))
                context_ref = save_material(root, f"context-{season}-{gw}.json", {"request": encode_bytes(value), "catalog": {digest: raw.hex() for digest, raw in entries.items()}})
                issues.append({"admission": context_ref, "forecast_store": "forecast_cache", "forecast_id": forecast_id, "training_authority": training_authority})
                if season == "2025-26" and gw == 1:
                    from commands.capture_live_evidence import capture_verified_issue

                    capture_request = {"version": 1, "season": season, "gameweek": gw, "model_name": model, "model_source_hash": source_hash, "protocol_hash": config.compute_hash(), **issues[-1]}
                    capture_ref = save_material(root, f"capture-request-{model}.json", capture_request)
                    with patch("commands.capture_live_evidence._utc_now", return_value=datetime(2025, 1, 1, 11, 30, tzinfo=UTC)):
                        capture = capture_verified_issue(root / capture_ref["path"], root / "live-captures")
                    readiness["dry_run_captures"][model] = save_material(root, f"capture-proof-{model}.json", capture.to_dict())
            def forecast_provider(gw: int, state: ReplayState) -> pd.DataFrame:
                return forecasts[gw]
            def outcome_provider(gw: int) -> OutcomeBatch:
                return batches[gw]
            trajectory = run_rolling_replay(model, season, anchor, forecast_provider, outcome_provider, end_gw=3, model_version_hash=source_hash, protocol_hash=config.compute_hash())
            trajectories[season, model] = trajectory
            trace_ref = save_material(root, f"trace-{season}-{model}.json", {"records": [record_to_dict(record) for record in trajectory.records]})
            request_payload["replays"].append({"season": season, "model_name": model, "anchor": anchor_ref, "trace": trace_ref, "issues": issues})
        if season == "2025-26":
            development = {"version": 1, "candidate_name": CANDIDATE, "former_champion": CHAMPION, "model_source_hash": source_hash, "protocol_hash": config.compute_hash(), "traces": {entry["model_name"]: entry["trace"] for entry in request_payload["replays"] if entry["season"] == season}}
            development_ref = save_material(root, "development-selection.json", development)
            request_payload["development_selection"] = development_ref
            registry.register_finalist(CANDIDATE, CHAMPION, "fixture-family", source_hash, content_hash({}), development_ref["sha256"], config.compute_hash(), attempt_id="fixture-attempt", registered_gameweeks=[1, 2, 3], max_family_attempts=1)
    confirmation_scores = [pair_replay_score("2024-25", candidate, champion) for candidate, champion in zip(trajectories["2024-25", CANDIDATE].records, trajectories["2024-25", CHAMPION].records, strict=True)]
    registry.transition_attempt_status("fixture-attempt", "in_progress", execution_status="complete", completed_gameweeks=[1, 2, 3], score_trace_hash=compute_score_trace_hash(confirmation_scores))
    request_payload["live_readiness"] = save_material(root, "live.json", readiness)
    save_material(root, "request.json", request_payload)
    return root / "request.json"
