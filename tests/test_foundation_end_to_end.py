"""Offline end-to-end foundation integration test (Phases 0-14, ADR 0066).

Exercises complete lifecycle:
1. Admitted toy inputs and neutral GW1 ownership anchor.
2. Forecast component ledger reconciliation and projection guards.
3. Independent rolling transfer plan replay and offline checkpoint net-score reconstruction.
4. Candidate registration in immutable confirmation attempt registry.
5. Statistical evaluation with stored-score block bootstrap and 4-way scientific verdict.
6. Evidence bundle format and protocol result validation.
7. Explicit manual champion adoption with human approval reference.
8. Prospective pre-deadline shadow replay and live review rollback monitoring.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from backtesting.confirmation_registry import ConfirmationRegistry
from backtesting.evaluation_protocol import validate_result
from backtesting.evidence_statistics import (
    PairedGameweekScore,
    StatisticalProtocolConfig,
    evaluate_evidence_against_protocol,
)
from backtesting.live_capture import (
    LiveCaptureManager,
    PlayerForecastSnapshot,
    ShadowReplayState,
    evaluate_live_review,
)
from backtesting.ownership_anchor import solve_ownership_anchor
from backtesting.projection_guards import (
    ComponentLedger,
    GuardOutput,
    reconcile_total_to_ledger,
)
from backtesting.replay_state import Outcome, OutcomeBatch, ReplayState
from backtesting.rolling_replay import (
    record_from_dict,
    run_rolling_replay,
)
from commands.evaluate_model_promotion import adopt_champion
from models.selection import ModelSelection, load_model_selection, save_model_selection


def _build_test_universe() -> pd.DataFrame:
    players = []
    pid = 1
    for i in range(4):
        players.append({
            "player_id": pid,
            "position_id": 1,
            "club_id": (i % 6) + 1,
            "now_cost": 45 + i * 5,
            "selected_by_percent": 15.0 + i * 5.0,
        })
        pid += 1
    for i in range(8):
        players.append({
            "player_id": pid,
            "position_id": 2,
            "club_id": (i % 6) + 1,
            "now_cost": 40 + i * 3,
            "selected_by_percent": 10.0 + i * 3.0,
        })
        pid += 1
    for i in range(8):
        players.append({
            "player_id": pid,
            "position_id": 3,
            "club_id": (i % 6) + 1,
            "now_cost": 45 + i * 4,
            "selected_by_percent": 8.0 + i * 4.0,
        })
        pid += 1
    for i in range(4):
        players.append({
            "player_id": pid,
            "position_id": 4,
            "club_id": (i % 6) + 1,
            "now_cost": 55 + i * 8,
            "selected_by_percent": 12.0 + i * 5.0,
        })
        pid += 1
    return pd.DataFrame(players)


def test_complete_foundation_lifecycle_end_to_end(tmp_path: Path) -> None:
    """Validate full evaluation, admission, replay, registry, adoption, and review lifecycle."""
    # 1. Neutral GW1 ownership anchor
    df_univ = _build_test_universe()
    anchor = solve_ownership_anchor(df_univ, season="2024-25")
    assert len(anchor.player_ids) == 15
    assert sum(anchor.acquisition_prices.values()) <= 1000

    # 2. Projection component ledger reconciliation
    comps = ComponentLedger(
        minutes=85.0,
        goals=0.5,
        assists=0.2,
        clean_sheets=0.0,
        saves=0.0,
        defensive_contributions=0.0,
        bonus=0.3,
    )
    # Forward: 2 pts (60+ mins) + 0.5*4 (goals) + 0.2*3 (assists) + 0 (clean sheet) + 0.3*1 (bonus) = 4.9
    recon = reconcile_total_to_ledger(total_xp=4.9, components=comps, position="F", season="2024-25")
    assert recon.reconciled is True
    assert recon.discrepancy == pytest.approx(0.0)

    # 3. Independent rolling replay for Candidate vs Champion
    def candidate_forecast_provider(gw: int, state: ReplayState) -> pd.DataFrame:
        return pd.DataFrame([
            {"player_id": pid, "projected_points": float(12.0 + (pid % 4) * 2.5)}
            for pid in range(1, 25)
        ])

    def champion_forecast_provider(gw: int, state: ReplayState) -> pd.DataFrame:
        return pd.DataFrame([
            {"player_id": pid, "projected_points": float(10.0 + (pid % 5) * 1.5)}
            for pid in range(1, 25)
        ])

    def outcome_provider(gw: int) -> OutcomeBatch:
        return OutcomeBatch(
            rules_version="2024-25",
            deadline=gw,
            source_identity=f"synth-gw-{gw}",
            outcomes=tuple(
                (pid, Outcome(points=4 + (gw * pid) % 7, minutes=90, appeared=True))
                for pid in range(1, 25)
            ),
        )

    cand_cp = tmp_path / "cand_checkpoints"
    champ_cp = tmp_path / "champ_checkpoints"

    cand_traj = run_rolling_replay(
        model_name="candidate_alpha",
        season="2024-25",
        anchor=anchor,
        forecast_provider=candidate_forecast_provider,
        outcome_provider=outcome_provider,
        start_gw=1,
        end_gw=3,
        checkpoint_dir=cand_cp,
    )
    champ_traj = run_rolling_replay(
        model_name="def_xg_shrink_challenger",
        season="2024-25",
        anchor=anchor,
        forecast_provider=champion_forecast_provider,
        outcome_provider=outcome_provider,
        start_gw=1,
        end_gw=3,
        checkpoint_dir=champ_cp,
    )

    # Verify offline net score reconstruction from saved JSON checkpoints
    saved_cand_files = sorted(cand_cp.glob("checkpoint_gw_*.json"))
    assert len(saved_cand_files) == 3
    disk_records = [record_from_dict(json.loads(f.read_text(encoding="utf-8"))) for f in saved_cand_files]
    reconstructed_net = sum(r.net_points for r in disk_records)
    assert reconstructed_net == cand_traj.cumulative_net

    # 4. Confirmation attempt registration
    registry_file = tmp_path / "confirmation_registry.jsonl"
    registry = ConfirmationRegistry(registry_file)
    entry = registry.register_finalist(
        candidate_name="candidate_alpha",
        champion_name="def_xg_shrink_challenger",
        mechanism_family="candidate_alpha_family",
        model_source_hash="a" * 64,
        parameters_hash="b" * 64,
        dev_selection_record_ref="docs/research/my-topic/dev.csv",
        protocol_hash="c" * 64,
        attempt_id="att_test_01",
        registered_gameweeks=list(range(1, 4)),
    )
    assert entry.attempt_id == "att_test_01"
    assert registry.verify_integrity() is True

    # 5. Numerical and statistical evaluation protocol
    paired_scores = [
        PairedGameweekScore(
            season="2024-25",
            gameweek=gw,
            candidate_net_points=float(c_rec.net_points),
            champion_net_points=float(h_rec.net_points),
            candidate_gross_points=float(c_rec.gross_points),
            champion_gross_points=float(h_rec.gross_points),
            candidate_hits_deducted=int(c_rec.hit_penalty // 4),
            champion_hits_deducted=int(h_rec.hit_penalty // 4),
        )
        for gw, c_rec, h_rec in zip(cand_traj.deadlines, cand_traj.records, champ_traj.records, strict=True)
    ]
    guard = GuardOutput(
        metric_name="minutes_mae",
        passed=True,
        status="PASS",
        estimate=-0.2,
        margin=1.0,
        standard_error=0.1,
        ci_lower=-0.4,
        ci_upper=0.0,
        coverage=1.0,
        sample_size=24,
        direction="lower_is_better",
        reason="Playing time non-inferior",
    )
    protocol_config = StatisticalProtocolConfig(
        nominal_alpha=0.05,
        bootstrap_draws=200,
        family_error_control="none",
        approved_by_human=True,
    )
    eval_result = evaluate_evidence_against_protocol(
        paired_scores=paired_scores,
        projection_guards=[guard],
        config=protocol_config,
        is_confirmation_available=True,
    )
    assert eval_result.verdict in ("pass", "fail", "inconclusive")

    # 6. Contract result verification
    protocol_payload = {
        "version": 1,
        "execution_status": "complete",
        "scientific_verdict": "pass",
        "reasons": ["Demonstrated non-inferiority and positive net delta"],
        "evidence_complete": True,
        "limitations": ["Evaluated on synthetic test schedule"],
        "started_at": "2026-10-29T20:00:00+00:00",
        "finished_at": "2026-10-29T20:05:00+00:00",
        "identity": {
            "model_source": "a" * 64,
            "dirty_source": "0" * 64,
            "parameters_training_seed": "b" * 64,
            "input_manifests": "c" * 64,
            "feature_scoring_code": "d" * 64,
            "forecast_schema": "e" * 64,
            "anchor": "1" * 64,
            "rules_calendar": "2" * 64,
            "solver": "3" * 64,
            "evaluation_statistics": "4" * 64,
            "protocol": "5" * 64,
        },
    }
    validate_result(protocol_payload)

    # 7. Manual Champion Adoption
    config_file = tmp_path / "model_selection.json"
    save_model_selection(
        ModelSelection(
            champion="def_xg_shrink_challenger",
            candidates=("candidate_alpha",),
        ),
        config_file,
    )
    bundle_file = tmp_path / "evidence_bundle.json"
    bundle_payload = {
        "scientific_verdict": "pass",
        "execution_status": "complete",
        "candidate_name": "candidate_alpha",
        "former_champion": "def_xg_shrink_challenger",
        "snapshot_backed": True,
    }
    bundle_file.write_text(json.dumps(bundle_payload), encoding="utf-8")

    updated_sel = adopt_champion(
        bundle_path=bundle_file,
        config_path=config_file,
        approval_ref="RFC-20261029-TEST",
        expected_current_champion="def_xg_shrink_challenger",
    )
    assert updated_sel.champion == "candidate_alpha"
    assert load_model_selection(config_file).champion == "candidate_alpha"

    # 8. Prospective pre-deadline capture and live review
    capture_mgr = LiveCaptureManager(tmp_path / "live_capture")
    capture_mgr.record_deadline_capture(
        season="2025-26",
        gameweek=1,
        deadline_time_utc="2025-08-15T17:30:00+00:00",
        capture_time_utc="2025-08-15T17:00:00+00:00",
        model_name="candidate_alpha",
        model_version_hash="a" * 64,
        policy_settings_hash="b" * 64,
        forecasts=[
            PlayerForecastSnapshot(
                player_id=1,
                player_name="Haaland",
                team_code=11,
                position="FWD",
                expected_minutes=90.0,
                projected_points=7.5,
                goals=0.8,
                assists=0.2,
            )
        ],
    )

    live_gws = [1, 2, 3, 4]
    adopted_shadow = [
        ShadowReplayState(
            model_role="adopted_candidate",
            season="2025-26",
            gameweek=gw,
            owned_fifteen=tuple(range(1, 16)),
            bank_tenths=0,
            free_transfers=1,
            transfers_made=0,
            hit_cost=0,
            lineup_starters=tuple(range(1, 12)),
            captain_id=1,
            vice_id=2,
            gross_points=15.0,
            net_points=15.0,
        )
        for gw in live_gws
    ]
    former_shadow = [
        ShadowReplayState(
            model_role="former_champion",
            season="2025-26",
            gameweek=gw,
            owned_fifteen=tuple(range(1, 16)),
            bank_tenths=0,
            free_transfers=1,
            transfers_made=0,
            hit_cost=0,
            lineup_starters=tuple(range(1, 12)),
            captain_id=1,
            vice_id=2,
            gross_points=14.0,
            net_points=14.0,
        )
        for gw in live_gws
    ]

    review = evaluate_live_review(
        season="2025-26",
        gameweeks=live_gws,
        adopted_history=adopted_shadow,
        champion_history=former_shadow,
        material_loss_limit=8.0,
        min_gameweeks=4,
    )
    assert review.should_rollback is False
    assert review.net_delta == 4.0
    assert len(review.bundle_hash) == 64
