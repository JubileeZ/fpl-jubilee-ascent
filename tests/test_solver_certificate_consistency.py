"""Objective-quality evidence cannot claim a false closed relative gap."""

from dataclasses import replace
from typing import Any

import pandas as pd
import pytest

from backtesting.replay_state import Decision, Outcome, OutcomeBatch, Player, ReplayState, initial_state, state_hash
from backtesting.rolling_replay import SolverCertificate, UncertifiedSolveError, execute_replay_deadline, solve_lineup_milp, validate_solver_certificate_consistency
from models.scoring_matrix import Position


def _certificate() -> SolverCertificate:
    return SolverCertificate(True, 10.0, 10.0, 0.0, 0.0, "OPTIMAL", 0.01, 1, 42, "fixture", "certified", {})


@pytest.mark.parametrize("objective,bound,absolute_gap,relative_gap,valid", [
    (10.0, 11.0, 1.0, 0.1, True),
    (-10.0, -9.0, 1.0, 0.1, True),
    (10.0, 11.0, 1.0, 0.0, False),
    (0.0, 1.0, 1.0, 0.0, False),
    (0.0, 0.0, 0.0, 0.0, True),
])
def test_objective_bound_gap_consistency(objective: float, bound: float, absolute_gap: float, relative_gap: float, valid: bool) -> None:
    certificate = replace(_certificate(), objective=objective, objective_bound=bound, absolute_gap=absolute_gap, relative_gap=relative_gap)
    if valid:
        validate_solver_certificate_consistency(certificate)
    else:
        with pytest.raises(UncertifiedSolveError):
            validate_solver_certificate_consistency(certificate)


def test_execute_deadline_refuses_fabricated_zero_relative_gap() -> None:
    positions: tuple[Position, ...] = ("GK", "GK", "D", "D", "D", "D", "D", "M", "M", "M", "M", "M", "F", "F", "F")
    state = initial_state("2024-25", tuple(Player(pid, position, (pid - 1) % 5 + 1, 50, 50) for pid, position in enumerate(positions, 1)))
    def false_certificate(current: ReplayState, horizon: int, forecasts: pd.DataFrame, options: dict[str, Any]) -> tuple[Decision, SolverCertificate]:
        decision = Decision((), solve_lineup_milp(current.squad, {}), state_hash(current), current.deadline)
        return decision, replace(_certificate(), objective_bound=11.0, absolute_gap=1.0)
    outcomes = OutcomeBatch("2024-25", 1, "fixture", tuple((player.player_id, Outcome(2, 90, True)) for player in state.squad))
    with pytest.raises(UncertifiedSolveError, match="relative gap contradicts"):
        execute_replay_deadline(state, pd.DataFrame(), outcomes, solve_fn=false_certificate)
