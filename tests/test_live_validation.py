"""Unit tests for Phase 10 prospective capture, shadow replay, and live review."""

from pathlib import Path
from dataclasses import replace
from typing import Any, cast
import pytest

from backtesting.replay_state import Decision, Outcome, OutcomeBatch, Player, ReplayState, initial_state, state_hash
from backtesting.rolling_replay import solve_lineup_milp
from backtesting.season_rules import Chip
from models.scoring_matrix import Position

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
    positions = cast(list[Position], ["GK"] * 2 + ["D"] * 5 + ["M"] * 5 + ["F"] * 3)
    squad = tuple(Player(i, position, (i - 1) % 6 + 1, 50, 50) for i, position in enumerate(positions, 1))
    opening = initial_state("2024-25", squad)
    native = replace(opening, deadline=2, free_transfers=1, parent_hash=state_hash(opening))
    squad_base = tuple(p.player_id for p in native.squad)
    lineup = solve_lineup_milp(native.squad, {p.player_id: 5.0 for p in native.squad})

    cand_state = ShadowReplayState(
        model_role="adopted_candidate",
        season="2024-25",
        gameweek=1,
        owned_fifteen=squad_base,
        bank_tenths=native.bank,
        free_transfers=1,
        transfers_made=0,
        hit_cost=0,
        lineup_starters=lineup.starters,
        captain_id=lineup.captain,
        vice_id=lineup.vice,
        gross_points=60.0,
        net_points=60.0,
        native_state=native,
    )
    champ_state = ShadowReplayState(
        model_role="former_champion",
        season="2024-25",
        gameweek=1,
        owned_fifteen=squad_base,
        bank_tenths=native.bank,
        free_transfers=1,
        transfers_made=0,
        hit_cost=0,
        lineup_starters=lineup.starters,
        captain_id=lineup.captain,
        vice_id=lineup.vice,
        gross_points=60.0,
        net_points=60.0,
        native_state=native,
    )

    bought = Player(20, "M", 5, 60, 60)
    updated = tuple(p for p in native.squad if p.player_id != 8) + (bought,)
    candidate_lineup = solve_lineup_milp(updated, {p.player_id: 20.0 if p.player_id == 20 else 5.0 for p in updated})
    batch = OutcomeBatch("2024-25", 2, "synthetic-live", tuple((pid, Outcome(12 if pid == 20 else 5, 90, True)) for pid in (*squad_base, 20)))

    cand_step = mgr.step_shadow_state(
        cand_state,
        native_decision=Decision(((8, bought),), candidate_lineup, state_hash(native), 2),
        outcome_batch=batch,
    )

    champ_step = mgr.step_shadow_state(
        champ_state,
        native_decision=Decision((), lineup, state_hash(native), 2),
        outcome_batch=batch,
    )

    assert 20 in cand_step.owned_fifteen
    assert 8 in champ_step.owned_fifteen
    assert cand_step.bank_tenths == native.bank - 10
    assert champ_step.bank_tenths == native.bank
    assert cand_step.native_state is not None
    assert cand_step.native_state.squad[-1].purchase == 60
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


def test_evaluate_live_review_top_level_convenience() -> None:
    """Verify top-level evaluate_live_review convenience function works directly."""
    from backtesting.live_capture import evaluate_live_review

    gws = [2, 3, 4, 5]
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
            gross_points=20.0,
            net_points=20.0,
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
            gross_points=18.0,
            net_points=18.0,
        )
        for gw in gws
    ]

    rev = evaluate_live_review(
        season="2025-26",
        gameweeks=gws,
        adopted_history=adopted_hist,
        champion_history=champ_hist,
    )
    assert rev.should_rollback is False
    assert rev.net_delta == 8.0
    assert len(rev.bundle_hash) == 64


@pytest.mark.parametrize("season,cap", [("2023-24", 2), ("2024-25", 5)])
@pytest.mark.parametrize("chip", ["wildcard", "free_hit", "bench_boost", "triple_captain"])
def test_native_shadow_chips_finances_and_vice(tmp_path: Path, season: str, cap: int, chip: Chip) -> None:
    positions = cast(list[Position], ["GK"] * 2 + ["D"] * 5 + ["M"] * 5 + ["F"] * 3)
    squad = tuple(Player(i, position, (i - 1) % 6 + 1, 43 if i == 8 else 50, 50) for i, position in enumerate(positions, 1))
    native = ReplayState(season, squad, 250, f"native-{season}-v1", 2, cap, parent_hash="a" * 64)
    free = chip in ("wildcard", "free_hit")
    bought = Player(20, "M", 5, 60, 60)
    active = tuple(p for p in native.squad if p.player_id != 8) + (bought,) if free else native.squad
    lineup = solve_lineup_milp(active, {p.player_id: float(p.player_id) for p in active})
    prior = ShadowReplayState("adopted_candidate", season, 1, tuple(p.player_id for p in squad), native.bank, cap,
                              0, 0, lineup.starters, lineup.captain, lineup.vice, 0.0, 0.0, native_state=native)
    decision = Decision(((8, bought),) if free else (), lineup, state_hash(native), 2, chip)
    batch = OutcomeBatch(season, 2, "finalized-synthetic", tuple((p.player_id, Outcome(0, 0, False) if p.player_id == lineup.captain
                        else Outcome(7 if p.player_id == lineup.vice else 2, 90, True)) for p in active))
    result = LiveCaptureManager(tmp_path).step_shadow_state(prior, native_decision=decision, outcome_batch=batch)
    assert result.hit_cost == 0
    assert result.bank_tenths == (236 if chip == "wildcard" else 250)
    assert (20 in result.owned_fifteen) == (chip == "wildcard")
    assert result.free_transfers == (1 if free and season == "2023-24" else cap)
    assert result.net_points == (40.0 if chip == "bench_boost" else 41.0 if chip == "triple_captain" else 34.0)


def test_sparse_shadow_inputs_fail_closed(tmp_path: Path) -> None:
    prior = ShadowReplayState("adopted_candidate", "2024-25", 1, tuple(range(1, 16)), 10, 1, 0, 0,
                              tuple(range(1, 12)), 1, 2, 0.0, 0.0)
    with pytest.raises(ValueError, match="Native ReplayState"):
        LiveCaptureManager(tmp_path).step_shadow_state(prior, outcomes_by_player={1: 10.0})


def test_capture_collision_cannot_replace_forecasts(tmp_path: Path) -> None:
    from backtesting.live_capture import LiveCaptureError

    manager = LiveCaptureManager(tmp_path)
    kwargs: dict[str, Any] = {"season": "2024-25", "gameweek": 2, "deadline_time_utc": "2024-08-24T10:00:00Z",
              "capture_time_utc": "2024-08-24T09:00:00Z", "model_name": "test", "model_version_hash": "a" * 64,
              "policy_settings_hash": "b" * 64, "forecasts": _sample_forecasts()}
    first = manager.record_deadline_capture(**kwargs)
    kwargs["forecasts"] = [replace(_sample_forecasts()[0], projected_points=999.0)]
    with pytest.raises(LiveCaptureError, match="Immutable"):
        manager.record_deadline_capture(**kwargs)
    assert first.capture_hash in (tmp_path / "captures" / f"{first.capture_id}.json").read_text()
