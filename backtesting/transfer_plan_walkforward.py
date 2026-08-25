"""Transfer Plan Walk-Forward runner (ADR 0019)."""

from __future__ import annotations

import csv
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from backtesting.decision_regret import LineupDecision, PlayerOutcome, score_lineup
from backtesting.strategy_policy import (
    FIRST_HALF_OAT_ARMS,
    WalkforwardArm,
    next_free_transfer_bank,
)

SUMMARY_COLUMNS: tuple[str, ...] = (
    "arm_id",
    "family",
    "locked_starting_shape",
    "transfer_target",
    "tilt",
    "realized_points",
    "status",
    "detail",
)

SolveWeek = Callable[[int, tuple[int, ...], int, WalkforwardArm], "DeadlineWeekPlan"]
OutcomesForWeek = Callable[[int], Mapping[int, PlayerOutcome]]


@dataclass(frozen=True)
class DeadlineWeekPlan:
    squad_ids: tuple[int, ...]
    lineup_ids: tuple[int, ...]
    bench_ids: tuple[int, ...]
    captain_id: int
    vice_id: int
    transfer_count: int


def score_deadline_week(plan: DeadlineWeekPlan, outcomes: Mapping[int, PlayerOutcome]) -> float:
    decision = LineupDecision(
        starters=plan.lineup_ids,
        bench=plan.bench_ids,
        captain=plan.captain_id,
        vice_captain=plan.vice_id,
    )
    return score_lineup(decision, outcomes).points


def run_walkforward_arm(
    arm: WalkforwardArm,
    gameweeks: Sequence[int],
    *,
    solve_week: SolveWeek,
    outcomes_for_week: OutcomesForWeek,
) -> float:
    total = 0.0
    squad: tuple[int, ...] = ()
    ft_bank = 0
    for gw in gameweeks:
        plan = solve_week(int(gw), squad, ft_bank, arm)
        if int(gw) == 1:
            ft_bank = 1
        else:
            ft_bank = next_free_transfer_bank(ft_bank, plan.transfer_count)
        total += score_deadline_week(plan, outcomes_for_week(int(gw)))
        squad = plan.squad_ids
    return total


def blocked_summary_rows(detail: str) -> list[dict[str, str]]:
    return [
        {
            "arm_id": arm.arm_id,
            "family": arm.family,
            "locked_starting_shape": "" if arm.locked_starting_shape is None else arm.locked_starting_shape.value,
            "transfer_target": arm.transfer_target.value,
            "tilt": arm.tilt.value,
            "realized_points": "",
            "status": "blocked_missing_prior_season_seed",
            "detail": detail,
        }
        for arm in FIRST_HALF_OAT_ARMS
    ]


def summary_row(arm: WalkforwardArm, realized_points: float, status: str = "ok", detail: str = "") -> dict[str, str]:
    return {
        "arm_id": arm.arm_id,
        "family": arm.family,
        "locked_starting_shape": "" if arm.locked_starting_shape is None else arm.locked_starting_shape.value,
        "transfer_target": arm.transfer_target.value,
        "tilt": arm.tilt.value,
        "realized_points": f"{realized_points:.2f}",
        "status": status,
        "detail": detail,
    }


def write_summary_csv(path: Path, rows: Sequence[Mapping[str, str]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(SUMMARY_COLUMNS))
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in SUMMARY_COLUMNS})
    return path
