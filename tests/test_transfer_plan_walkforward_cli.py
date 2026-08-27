from pathlib import Path

import pandas as pd

from backtesting.decision_regret import PlayerOutcome
from backtesting.strategy_policy import FIRST_HALF_OAT_ARMS
from backtesting.transfer_plan_walkforward import DeadlineWeekPlan
from commands.transfer_plan_walkforward import main


def test_cli_writes_blocked_summary_without_seed(tmp_path: Path) -> None:
    output = tmp_path / "tp_walkforward_summary.csv"
    seed = tmp_path / "missing" / "processed"
    code = main(["--seed_dir", str(seed), "--output", str(output)])
    assert code == 1
    text = output.read_text(encoding="utf-8")
    assert "baseline" in text
    assert "blocked_missing_prior_season_seed" in text


def test_cli_runs_ranking_when_seed_present(tmp_path: Path) -> None:
    seed = tmp_path / "seed"
    seed.mkdir()
    pd.DataFrame({"id": [1]}).to_parquet(seed / "players.parquet")
    pd.DataFrame({"element": [1], "round": [1]}).to_parquet(seed / "player_performances.parquet")
    output = tmp_path / "tp_walkforward_summary.csv"

    def solve_week(gw: int, squad: tuple[int, ...], ft_bank: int, arm: object) -> DeadlineWeekPlan:
        lineup = (1, 2, 3, 4, 7, 8, 9, 10, 12, 13, 14)
        bench = (5, 6, 11, 15)
        return DeadlineWeekPlan(lineup + bench, lineup, bench, 12, 13, 0 if gw == 1 else 1)

    def outcomes_for_week(_gw: int) -> dict[int, PlayerOutcome]:
        positions = {
            1: 1, 15: 1,
            2: 2, 3: 2, 4: 2, 5: 2, 6: 2,
            7: 3, 8: 3, 9: 3, 10: 3, 11: 3,
            12: 4, 13: 4, 14: 4,
        }
        return {pid: PlayerOutcome(pid, pos, 1.0, 90.0) for pid, pos in positions.items()}

    code = main(
        ["--seed_dir", str(seed), "--output", str(output)],
        solve_week=solve_week,
        outcomes_for_week=outcomes_for_week,
    )
    assert code == 0
    text = output.read_text(encoding="utf-8")
    assert "baseline" in text
    assert "ok" in text
    assert FIRST_HALF_OAT_ARMS[0].arm_id in text
