"""Verified checkpoint evidence reconstructed from retained empirical replay material."""

from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from backtesting.confirmation_registry import ConfirmationRegistry
from backtesting.data_admission import require_admitted, require_input
from backtesting.evidence_statistics import StatisticalProtocolConfig, compute_score_trace_hash
from backtesting.forecast_export import strict_solver_table
from backtesting.forecast_store import generate_forecast, load_forecast_verified
from backtesting.ownership_anchor import OwnershipAnchor, solve_ownership_anchor
from backtesting.promotion_evidence import (
    GUARD_SEMANTICS,
    _extract_origin_players_and_outcomes,
    content_hash,
    current_model_source_hash,
    native_solver_identity,
    pair_replay_score,
)
from backtesting.replay_state import Outcome, OutcomeBatch, ReplayState
from backtesting.rolling_replay import QualityPolicy, ReplayDeadlineRecord, record_to_dict, run_rolling_replay
from models.selection import ModelSelection, load_model_selection, save_model_selection
from promotion_evidence_fixture import CANDIDATE, CHAMPION, save_material
from test_empirical_admission import _build_empirical_bundle


def _retain_checkpoint_replay(
    root: Path,
    request: dict[str, Any],
    catalog: dict[str, bytes],
    training: dict[int, str],
    admissions: list[dict[str, Any]],
    model: str,
    source_hash: str,
    protocol_hash: str,
) -> tuple[dict[str, Any], list[ReplayDeadlineRecord]]:
    season = request["season"]
    anchor_name = f"anchor-{season}.json"
    anchor_path = root / anchor_name
    if anchor_path.exists():
        anchor = OwnershipAnchor.from_dict(json.loads(anchor_path.read_bytes()))
    else:
        players, _ = _extract_origin_players_and_outcomes(request["origins"][0], catalog)
        universe = pd.DataFrame(players).rename(
            columns={"id": "player_id", "club": "club_id", "position": "position_id", "price": "now_cost",
                     "ownership": "selected_by_percent", "eligible": "is_eligible"}
        )
        anchor = solve_ownership_anchor(universe, season)
    anchor_ref = save_material(root, anchor_name, anchor.to_dict())
    forecasts: dict[int, pd.DataFrame] = {}
    batches: dict[int, OutcomeBatch] = {}
    issues: list[dict[str, Any]] = []
    for origin, admission in zip(request["origins"], admissions, strict=True):
        gw = origin["gw"]
        capability = require_input(request, catalog, season, gw)
        admitted = require_admitted(request, catalog, season, gw)
        forecast_id, _, _ = generate_forecast(
            root / "forecast_cache", capability, request, catalog, training[gw], model
        )
        predictions, _ = load_forecast_verified(
            root / "forecast_cache", forecast_id, capability, request, catalog, training[gw], model
        )
        forecasts[gw] = strict_solver_table(predictions, capability, request, catalog).rename(
            columns={"club": "club_id", "position": "position_id", "price": "now_cost"}
        )
        players, outcomes = _extract_origin_players_and_outcomes(origin, catalog)
        eligibility = {player["id"]: player["eligible"] for player in players}
        forecasts[gw]["purchase_eligible"] = forecasts[gw]["player_id"].map(eligibility)
        points = pd.DataFrame(outcomes).groupby("player")[["points", "minutes"]].sum()
        batches[gw] = OutcomeBatch(
            season, gw, admitted.evidence_digest,
            tuple(
                (pid, Outcome(int(points.at[pid, "points"]), int(points.at[pid, "minutes"]),
                              bool(points.at[pid, "minutes"] > 0)))
                if pid in points.index else (pid, Outcome(0, 0, False))
                for pid in sorted(eligibility)
            ),
        )
        issues.append(
            {"admission": admission["admission"], "forecast_store": "forecast_cache",
             "forecast_id": forecast_id, "training_authority": training[gw]}
        )

    def forecasts_at(gw: int, state: ReplayState) -> pd.DataFrame:
        return forecasts[gw]

    def outcomes_at(gw: int) -> OutcomeBatch:
        return batches[gw]

    trajectory = run_rolling_replay(
        model, season, anchor, forecasts_at, outcomes_at, end_gw=len(issues),
        model_version_hash=source_hash, protocol_hash=protocol_hash,
        chip_calendar=((3, "triple_captain"), (25, "wildcard")),
    )
    records = list(trajectory.records)
    assert len(records) == len(issues)
    trace = save_material(root, f"trace-{season}-{model}.json", {"records": [record_to_dict(record) for record in records]})
    return {"season": season, "model_name": model, "anchor": anchor_ref, "trace": trace, "issues": issues}, records


@pytest.fixture(scope="module")
def retained_verified_checkpoint(tmp_path_factory: pytest.TempPathFactory) -> Path:
    from backtesting.promotion_evidence import CHECKPOINT_EVIDENCE_V2

    root = tmp_path_factory.mktemp("verified-checkpoint")
    development, validation = "2025-26", "2026-27"
    windows = {development: [1, 2], validation: list(range(1, 39))}
    guards = {
        name: {"forecast_field": spec[0], "outcome_field": spec[1], "loss": spec[2], "units": spec[3],
               "margin": 0.0, "alpha": 0.05, "direction": "lower_is_better"}
        for name, spec in GUARD_SEMANTICS.items()
    }
    protocol = {
        "horizon": 6,
        "windows": windows,
        "guard_specs": guards,
        "quality_policy": asdict(QualityPolicy()),
        "chip_calendar": [[3, "triple_captain"], [25, "wildcard"]],
        "solver_identity": native_solver_identity(),
        "projection_evaluation": {
            "leads": list(range(6)), "weights": [1.0] * 6, "population": "all_admitted_players",
            "missingness": "fail_closed", "aggregation": "weighted_paired_player_gameweek",
            "applicability": {season: dict.fromkeys(guards, "required") for season in windows},
        },
        "live_review": {
            "mode": "fplcache", "review_gameweeks": [15, 30, 38], "settlement_delay_hours": 24,
            "early_harm_min_gw": 6, "early_harm_p_threshold": 0.025,
        },
    }
    protocol["statistics"] = StatisticalProtocolConfig(
        development_season=development, confirmation_season=validation, approved_by_human=True,
        approval_reference="test-checkpoint-protocol", max_family_attempts=1,
        required_projection_guards=tuple(guards), evidence_protocol_hash=content_hash(protocol),
    ).to_dict()
    protocol_hash = content_hash(protocol)
    source_hash = current_model_source_hash()
    payload: dict[str, Any] = {
        "version": CHECKPOINT_EVIDENCE_V2, "checkpoint_gw": 15, "selection_path": "selection.json",
        "registry_path": "registry.jsonl", "model_source_hash": source_hash,
        "protocol": save_material(root, "protocol.json", protocol),
        "parameters": save_material(root, "parameters.json", {}),
        "podium_order": [CANDIDATE], "replays": [], "guard_outcome_sources": [],
    }
    save_model_selection(
        ModelSelection(CHAMPION, (CANDIDATE,), provisional_active=CANDIDATE, podium_frozen_season=validation,
                       podium_sealed=True),
        root / payload["selection_path"],
    )
    registry = ConfirmationRegistry(root / payload["registry_path"])
    for season in windows:
        active_validation = season == validation
        request, catalog, training = (
            _build_empirical_bundle(
                gws=tuple(range(1, 16)), track="validation_fplcache", season=validation,
                seed_season=development, checkpoint_gw=15, partial_prefix=False, fixtures_age_hours=1.5,
                with_manager=False,
            )
            if active_validation else _build_empirical_bundle(gws=(1, 2), with_manager=False)
        )
        context = save_material(
            root, f"admission-{season}.json",
            {"request": request, "catalog": {digest: raw.hex() for digest, raw in catalog.items()}},
        )
        admissions = [{"season": season, "gameweek": origin["gw"], "admission": context}
                      for origin in request["origins"]]
        payload["guard_outcome_sources"].extend(admissions)
        champion, champion_records = _retain_checkpoint_replay(
            root, request, catalog, training, admissions, CHAMPION, source_hash, protocol_hash
        )
        payload["replays"].append(champion)
        if not active_validation:
            development_selection = save_material(
                root, "development-selection.json",
                {"version": 1, "candidate_name": CANDIDATE, "former_champion": CHAMPION,
                 "model_source_hash": source_hash, "protocol_hash": protocol_hash,
                 "traces": {CHAMPION: champion["trace"]}},
            )
            payload["development_selections"] = {CANDIDATE: development_selection}
            registration = registry.register_finalist(
                CANDIDATE, CHAMPION, "fixture-checkpoint", source_hash, content_hash({}),
                development_selection["sha256"], protocol_hash, requested_seasons=(validation,), max_family_attempts=1,
            )
            payload["confirmation_attempt_ids"] = {CANDIDATE: registration.attempt_id}
            continue
        candidate, candidate_records = _retain_checkpoint_replay(
            root, request, catalog, training, admissions, CANDIDATE, source_hash, protocol_hash
        )
        payload["replays"].append(candidate)
        scores = [pair_replay_score(validation, candidate_gw, champion_gw)
                  for candidate_gw, champion_gw in zip(candidate_records, champion_records, strict=True)]
        registry.record_checkpoint(
            registration.attempt_id, checkpoint_gw=15, completed_gameweeks=tuple(range(1, 16)),
            score_trace_hash=compute_score_trace_hash(scores),
        )
    return root / save_material(root, "request.json", payload)["path"]


def test_checkpoint_reconstructs_real_empirical_replay(retained_verified_checkpoint: Path) -> None:
    from backtesting.promotion_evidence import (
        verify_checkpoint_recommendation_bundle,
        write_checkpoint_recommendation_bundle,
    )

    request_path = retained_verified_checkpoint
    bundle_path = request_path.with_name("bundle.json")
    bundle = write_checkpoint_recommendation_bundle(request_path, bundle_path)
    assert bundle["empirical_admission"] is True
    assert bundle["checkpoint_gw"] == 15
    assert verify_checkpoint_recommendation_bundle(bundle_path) == bundle


def test_checkpoint_rejects_replay_with_unbound_admission(retained_verified_checkpoint: Path) -> None:
    from backtesting.promotion_evidence import evaluate_checkpoint_bundle_evidence

    request_path = retained_verified_checkpoint
    payload = json.loads(request_path.read_bytes())
    replay = next(entry for entry in payload["replays"] if entry["season"] == "2026-27")
    replay["issues"][0]["admission"] = payload["guard_outcome_sources"][0]["admission"]
    bad_request = request_path.with_name(save_material(request_path.parent, "wrong-active-admission.json", payload)["path"])
    with pytest.raises(ValueError, match="Replay and guard outcomes must use the same admitted sources"):
        evaluate_checkpoint_bundle_evidence(bad_request)


def test_verified_checkpoint_pass_finalizes_then_requires_manual_adoption(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Isolate the scientific pass boundary while exercising real registry and adoption writes."""
    from backtesting import promotion_evidence
    from commands.evaluate_model_promotion import adopt_champion

    checkpoint = 15
    season = "2026-27"
    weeks = tuple(range(1, checkpoint + 1))
    selection = ModelSelection(CHAMPION, (CANDIDATE,), provisional_active=CANDIDATE,
                               podium_frozen_season=season, podium_sealed=True)
    active_config = tmp_path / "model_selection.json"
    save_model_selection(selection, active_config)
    source_hash, protocol_hash, trace_hash = ("a" * 64, "b" * 64, "c" * 64)
    parameters_hash = content_hash({})
    registry = ConfirmationRegistry(tmp_path / "registry.jsonl")
    attempt = registry.register_finalist(
        CANDIDATE, CHAMPION, "checkpoint-winner", source_hash, parameters_hash, "d" * 64, protocol_hash,
        requested_seasons=(season,), max_family_attempts=1,
    )
    registry.record_checkpoint(
        attempt.attempt_id, checkpoint_gw=checkpoint, completed_gameweeks=weeks, score_trace_hash=trace_hash,
    )
    request = {
        "version": promotion_evidence.CHECKPOINT_EVIDENCE_V2, "checkpoint_gw": checkpoint,
        "registry_path": registry.registry_file.name, "confirmation_attempt_ids": {CANDIDATE: attempt.attempt_id},
    }
    request_path = tmp_path / save_material(tmp_path, "request.json", request)["path"]

    def retained_scientific_pass(
        root: Path, payload: dict[str, Any], *, finalized_bundle_path: Path | None = None,
    ) -> tuple[promotion_evidence.DualTierCheckpointResult, dict[str, Any]]:
        assert root == tmp_path and payload == request
        registry.verify_checkpoint_attempt(
            attempt.attempt_id, candidate_name=CANDIDATE, champion_name=CHAMPION, active_season=season,
            checkpoint_gw=checkpoint, model_source_hash=source_hash, parameters_hash=parameters_hash,
            protocol_hash=protocol_hash, score_trace_hash=trace_hash, max_family_attempts=1,
            finalized_bundle_path=finalized_bundle_path,
        )
        result = promotion_evidence.DualTierCheckpointResult(
            checkpoint_gw=checkpoint, num_finalists=1, alpha_spent=0.0005, action="eligible_for_manual_adopt",
            recommended_champion=CANDIDATE, next_provisional_active=CANDIDATE, requires_manual_adopt=True,
            outcomes={}, reasons=("Isolated retained scientific pass",),
        )
        return result, {
            "candidate_name": CANDIDATE, "former_champion": CHAMPION, "model_source_hash": source_hash,
            "protocol_hash": protocol_hash, "empirical_admission": True, "selection_sha256": content_hash(asdict(selection)),
            "confirmation_attempt_id": attempt.attempt_id, "score_trace_hash": trace_hash,
        }

    monkeypatch.setattr(promotion_evidence, "evaluate_verified_checkpoint_payload", retained_scientific_pass)
    bundle_path = tmp_path / "bundle.json"
    bundle = promotion_evidence.write_checkpoint_recommendation_bundle(request_path, bundle_path)
    final_attempt = registry.get_attempt(attempt.attempt_id)
    assert final_attempt is not None and final_attempt.status == "completed"
    assert final_attempt.bundle_path == "bundle.json" and final_attempt.human_approval_ref is None
    assert load_model_selection(active_config) == selection
    with pytest.raises(ValueError, match="human approval"):
        adopt_champion(bundle_path, config_path=active_config, expected_current_champion=CHAMPION,
                       approved_bundle_hash=bundle["bundle_hash"])
    adopted = adopt_champion(
        bundle_path, config_path=active_config, approval_ref="test-operator-approved",
        expected_current_champion=CHAMPION, approved_bundle_hash=bundle["bundle_hash"],
    )
    assert adopted.champion == CANDIDATE
    assert load_model_selection(active_config) == adopted


def test_real_checkpoint_bundle_writes_relative_bundle_path_and_packs_snapshot(
    retained_verified_checkpoint: Path,
    tmp_path: Path,
) -> None:
    from backtesting.portable_evidence import pack_checkpoint_snapshot
    from backtesting.promotion_evidence import verify_checkpoint_recommendation_bundle, write_checkpoint_recommendation_bundle

    bundle_path = retained_verified_checkpoint.with_name("bundle.json")
    bundle = write_checkpoint_recommendation_bundle(retained_verified_checkpoint, bundle_path)
    assert "serving_model_closure_hash" in bundle
    assert "model_runtime_bindings" in bundle
    assert verify_checkpoint_recommendation_bundle(bundle_path) == bundle

    # Inconclusive pilot fixture cannot pack an immutable release pass snapshot
    with pytest.raises(ValueError, match="finalized empirical scientific pass"):
        pack_checkpoint_snapshot(bundle_path, output_dir=tmp_path / "snapshots")
