from pathlib import Path

import pytest

from backtesting.decision_regret import PlayerOutcome
from backtesting.strategy_policy import FIRST_HALF_OAT_ARMS, Tilt, TransferTarget
from backtesting.transfer_plan_walkforward import (
    DeadlineWeekPlan,
    blocked_summary_rows,
    run_walkforward_arm,
    score_deadline_week,
    write_summary_csv,
)


def _legal_squad_outcomes(points: float = 2.0, minutes: float = 90.0) -> dict[int, PlayerOutcome]:
    positions = {
        1: 1, 15: 1,
        2: 2, 3: 2, 4: 2, 5: 2, 6: 2,
        7: 3, 8: 3, 9: 3, 10: 3, 11: 3,
        12: 4, 13: 4, 14: 4,
    }
    return {
        player_id: PlayerOutcome(player_id, position, points, minutes)
        for player_id, position in positions.items()
    }


def _plan(*, transfer_count: int = 0) -> DeadlineWeekPlan:
    lineup = (1, 2, 3, 4, 7, 8, 9, 10, 12, 13, 14)
    bench = (5, 6, 11, 15)
    return DeadlineWeekPlan(
        squad_ids=lineup + bench,
        lineup_ids=lineup,
        bench_ids=bench,
        captain_id=12,
        vice_id=13,
        transfer_count=transfer_count,
    )


def test_score_deadline_week_counts_autosubs_and_captain() -> None:
    outcomes = _legal_squad_outcomes()
    outcomes[2] = PlayerOutcome(2, 2, 0.0, 0.0)
    outcomes[5] = PlayerOutcome(5, 2, 8.0, 90.0)
    outcomes[12] = PlayerOutcome(12, 4, 6.0, 90.0)
    scored = score_deadline_week(_plan(), outcomes)
    assert scored == pytest.approx(38.0)


def test_walkforward_sums_realized_points_and_banks_free_transfers() -> None:
    seen: list[tuple[int, int]] = []

    def solve_week(gw: int, squad: tuple[int, ...], ft_bank: int, arm: object) -> DeadlineWeekPlan:
        seen.append((gw, ft_bank))
        transfers = 0 if gw == 1 else 1
        return _plan(transfer_count=transfers)

    def outcomes_for_week(_gw: int) -> dict[int, PlayerOutcome]:
        return _legal_squad_outcomes(points=1.0)

    total = run_walkforward_arm(
        FIRST_HALF_OAT_ARMS[0],
        [1, 2, 3],
        solve_week=solve_week,
        outcomes_for_week=outcomes_for_week,
    )
    assert seen == [(1, 0), (2, 1), (3, 1)]
    # 11 starters * 1pt + captain extra 1pt = 12 per GW * 3
    assert total == pytest.approx(36.0)


def test_walkforward_rejects_a_hit_after_gw1() -> None:
    def solve_week(gw: int, squad: tuple[int, ...], ft_bank: int, arm: object) -> DeadlineWeekPlan:
        return _plan(transfer_count=0 if gw == 1 else 2)

    with pytest.raises(ValueError, match="Hit"):
        run_walkforward_arm(
            FIRST_HALF_OAT_ARMS[0],
            [1, 2],
            solve_week=solve_week,
            outcomes_for_week=lambda _gw: _legal_squad_outcomes(),
        )


def test_blocked_summary_lists_all_oat_arms() -> None:
    rows = blocked_summary_rows("missing Prior-Season Seed")
    assert len(rows) == 10
    assert rows[0]["arm_id"] == "baseline"
    assert rows[0]["status"] == "blocked_missing_prior_season_seed"
    assert rows[0]["realized_points"] == ""
    assert rows[6]["transfer_target"] == TransferTarget.ATTACK.value


def test_write_summary_csv_round_trips(tmp_path: Path) -> None:
    path = tmp_path / "tp_walkforward_summary.csv"
    write_summary_csv(path, blocked_summary_rows("missing Prior-Season Seed"))
    text = path.read_text()
    assert "arm_id" in text
    assert "baseline" in text
    assert Tilt.DEFCON_FLOOR.value in text
