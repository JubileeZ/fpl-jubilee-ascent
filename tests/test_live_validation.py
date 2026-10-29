"""Unit tests for Phase 10 prospective capture, shadow replay, and live review."""

from pathlib import Path
import pytest

from backtesting.live_capture import (
    InsufficientLiveEvidenceError,
    LateCaptureError,
    LiveCaptureManager,
    OutcomeNotFinalizedError,
    PlayerForecastSnapshot,
    SealedLiveSeasonError,
    ShadowReplayState,
)


def _sample_forecasts() -> list[PlayerForecastSnapshot]:
    return [
        PlayerForecastSnapshot(
            player_id=1,
            player_name="Haaland",
            team_code=11,
            position="FWD",
            expected_minutes=85.0,
            projected_points=7.5,
            goals=0.8,
            assists=0.2,
        ),
        PlayerForecastSnapshot(
            player_id=2,
            player_name="Salah",
            team_code=14,
            position="MID",
            expected_minutes=90.0,
            projected_points=7.0,
            goals=0.6,
            assists=0.4,
        ),
    ]


def test_ontime_deadline_capture_success(tmp_path: Path) -> None:
    """Verify on-time forecast capture computes cryptographic hash and writes JSON."""
    mgr = LiveCaptureManager(tmp_path)
    cap = mgr.record_deadline_capture(
        season="2025-26",
        gameweek=10,
        deadline_time_utc="2025-10-25T10:00:00+00:00",
        capture_time_utc="2025-10-25T09:45:00+00:00",
        model_name="adaptive_causal_challenger",
        model_version_hash="1" * 64,
        policy_settings_hash="2" * 64,
        forecasts=_sample_forecasts(),
    )

    assert cap.is_late is False
    assert len(cap.capture_hash) == 64
    out_file = tmp_path / "captures" / f"{cap.capture_id}.json"
    assert out_file.is_file()


def test_late_capture_rejection(tmp_path: Path) -> None:
    """Verify late capture after deadline raises LateCaptureError and fails closed."""
    mgr = LiveCaptureManager(tmp_path)
    with pytest.raises(LateCaptureError, match="is 900.0s after deadline"):
        mgr.record_deadline_capture(
            season="2025-26",
            gameweek=10,
            deadline_time_utc="2025-10-25T10:00:00+00:00",
            capture_time_utc="2025-10-25T10:15:00+00:00",
            model_name="candidate",
            model_version_hash="1" * 64,
            policy_settings_hash="2" * 64,
            forecasts=_sample_forecasts(),
        )


def test_sealed_season_live_rejection(tmp_path: Path) -> None:
    """Verify prospective capture on sealed season 2026-27 GW6+ is strictly blocked."""
    mgr = LiveCaptureManager(tmp_path)
    with pytest.raises(SealedLiveSeasonError, match="sealed 2026-27 GW6+"):
        mgr.record_deadline_capture(
            season="2026-27",
            gameweek=6,
            deadline_time_utc="2026-09-20T10:00:00+00:00",
            capture_time_utc="2026-09-20T09:00:00+00:00",
            model_name="candidate",
            model_version_hash="1" * 64,
            policy_settings_hash="2" * 64,
            forecasts=_sample_forecasts(),
        )


def test_outcome_not_finalized_rejection(tmp_path: Path) -> None:
    """Verify shadow replay raises OutcomeNotFinalizedError when fixtures are not yet final."""
    mgr = LiveCaptureManager(tmp_path)
    initial_state = ShadowReplayState(
        model_role="adopted_candidate",
        season="2025-26",
        gameweek=1,
        owned_fifteen=tuple(range(1, 16)),
        bank_tenths=10,
        free_transfers=1,
        transfers_made=0,
        hit_cost=0,
        lineup_starters=tuple(range(1, 12)),
        captain_id=1,
        vice_id=2,
        gross_points=50.0,
        net_points=50.0,
    )

    with pytest.raises(OutcomeNotFinalizedError, match="outcomes not finalized"):
        mgr.step_shadow_state(
            initial_state,
            new_transfers_in=[100],
            new_transfers_out=[15],
            lineup_starters=tuple(range(1, 12)),
            captain_id=1,
            vice_id=2,
            outcomes_by_player={},
            outcomes_finalized=False,
        )


def test_dual_shadow_replay_divergence(tmp_path: Path) -> None:
    """Verify dual shadow replay tracks independent transfers, finances, and hits."""
    mgr = LiveCaptureManager(tmp_path)
    squad_base = tuple(range(1, 16))

    cand_state = ShadowReplayState(
        model_role="adopted_candidate",
        season="2025-26",
        gameweek=1,
        owned_fifteen=squad_base,
        bank_tenths=5,
        free_transfers=1,
        transfers_made=0,
        hit_cost=0,
        lineup_starters=tuple(range(1, 12)),
        captain_id=1,
        vice_id=2,
        gross_points=60.0,
        net_points=60.0,
    )
    champ_state = ShadowReplayState(
        model_role="former_champion",
        season="2025-26",
        gameweek=1,
        owned_fifteen=squad_base,
        bank_tenths=5,
        free_transfers=1,
        transfers_made=0,
        hit_cost=0,
        lineup_starters=tuple(range(1, 12)),
        captain_id=1,
        vice_id=2,
        gross_points=60.0,
        net_points=60.0,
    )

    # Realized outcomes
    outcomes = {pid: 5.0 for pid in range(1, 150)}
    outcomes[1] = 10.0  # Captain: 20 pts
    outcomes[20] = 12.0  # Candidate transfer-in hauls
    outcomes[30] = 2.0   # Champion transfer-in blanks

    cand_step = mgr.step_shadow_state(
        cand_state,
        new_transfers_in=[20],
        new_transfers_out=[15],
        lineup_starters=(20,) + tuple(range(2, 12)),
        captain_id=1,
        vice_id=2,
        outcomes_by_player=outcomes,
    )

    champ_step = mgr.step_shadow_state(
        champ_state,
        new_transfers_in=[30],
        new_transfers_out=[15],
        lineup_starters=(30,) + tuple(range(2, 12)),
        captain_id=1,
        vice_id=2,
        outcomes_by_player=outcomes,
    )

    assert 20 in cand_step.owned_fifteen
    assert 30 in champ_step.owned_fifteen
    assert cand_step.net_points > champ_step.net_points


def test_fixed_review_point_insufficient_evidence(tmp_path: Path) -> None:
    """Verify peeking with fewer than min_gameweeks raises InsufficientLiveEvidenceError."""
    mgr = LiveCaptureManager(tmp_path)
    with pytest.raises(InsufficientLiveEvidenceError, match="below minimum fixed horizon"):
        mgr.evaluate_live_review(
            season="2025-26",
            gameweeks=[2, 3],
            adopted_history=[],
            champion_history=[],
            min_gameweeks=4,
        )


def test_fixed_review_point_material_harm_rollback_recommendation(tmp_path: Path) -> None:
    """Verify material harm triggers rollback recommendation with human approval barrier."""
    mgr = LiveCaptureManager(tmp_path)
    gws = [2, 3, 4, 5]

    # Adopted candidate regressed severely: 40 pts vs Champion 55 pts => delta = -15 pts (exceeds 8.0 pt limit)
    adopted_hist = [
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
            gross_points=10.0,
            net_points=10.0,
        )
        for gw in gws
    ]
    champ_hist = [
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
            gross_points=15.0,
            net_points=15.0,
        )
        for gw in gws
    ]

    rev = mgr.evaluate_live_review(
        season="2025-26",
        gameweeks=gws,
        adopted_history=adopted_hist,
        champion_history=champ_hist,
        material_loss_limit=8.0,
        min_gameweeks=4,
    )

    assert rev.should_rollback is True
    assert rev.requires_human_approval is True
    assert rev.net_delta == -20.0
    assert any("exceeding live material loss limit" in r for r in rev.rollback_reasons)
    assert len(rev.bundle_hash) == 64
