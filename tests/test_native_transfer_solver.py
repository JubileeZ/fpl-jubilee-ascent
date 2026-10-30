from dataclasses import replace
from typing import cast

import pandas as pd
import pytest

from backtesting.native_transfer_solver import native_strategic_solve
from backtesting.replay_state import Lineup, Player, ReplayState, initial_state, state_hash
from backtesting.rolling_replay import get_strategic_replay_options, validate_decision_legality
from models.scoring_matrix import Position


def native_problem(season: str = "2024-25", deadline: int = 2, horizon: int = 6) -> tuple[ReplayState, pd.DataFrame]:
    positions = cast(list[Position], ["GK"] * 2 + ["D"] * 5 + ["M"] * 5 + ["F"] * 3)
    squad = tuple(Player(i, position, (i - 1) % 6 + 1, 50, 50) for i, position in enumerate(positions, 1))
    opening = initial_state(season, squad)
    state = opening if deadline == 1 else replace(opening, deadline=deadline, free_transfers=1, parent_hash=state_hash(opening))
    rows = []
    for player in [*squad, Player(16, "M", 6, 50, 50), Player(17, "D", 5, 50, 50)]:
        row = {"player_id": player.player_id, "position_id": {"GK": 1, "D": 2, "M": 3, "F": 4}[player.position],
               "club_id": player.club, "now_cost": player.market, "purchase_eligible": True}
        row.update({f"{gw}_{suffix}": (90.0 if suffix == "xMins" else (25.0 if player.player_id == 16 else 5.0))
                    for gw in range(deadline, deadline + horizon) for suffix in ("Pts", "xMins")})
        rows.append(row)
    return state, pd.DataFrame(rows)


def test_actual_six_week_transfer_solve_and_certificate() -> None:
    state, forecasts = native_problem()
    options = get_strategic_replay_options(6)
    decision, certificate = native_strategic_solve(state, 6, forecasts, options)
    validate_decision_legality(state, decision)
    assert 16 in {p.player_id for _, p in decision.transfers}
    assert len(certificate.strategic_audit["plans"]) == 6
    assert certificate.termination_status == "OPTIMAL"
    assert certificate.objective == pytest.approx(certificate.objective_bound)
    assert certificate.relative_gap == pytest.approx(0)
    assert certificate.runtime_seconds > 0
    assert certificate.solver_version.startswith("highs-")


@pytest.mark.parametrize("season,cap", [("2023-24", 2), ("2024-25", 5)])
def test_solver_uses_native_ft_cap_and_chip_reset(season: str, cap: int) -> None:
    state, forecasts = native_problem(season)
    state = replace(state, free_transfers=cap)
    options = get_strategic_replay_options(6, rules_version=season)
    options["chip_calendar"] = ((2, "wildcard"), (4, "free_hit"))
    decision, certificate = native_strategic_solve(state, 6, forecasts, options)
    assert decision.chip == "wildcard"
    plans = certificate.strategic_audit["plans"]
    assert plans[1]["free_transfers"] == (1 if season == "2023-24" else cap)
    assert all(1 <= plan["free_transfers"] <= cap for plan in plans)
    assert plans[3]["free_transfers"] == (1 if season == "2023-24" else plans[2]["free_transfers"])


def test_native_gw1_lock_and_shared_captain_chip() -> None:
    state, forecasts = native_problem(deadline=1)
    options = get_strategic_replay_options(6)
    options["chip_calendar"] = ((1, "triple_captain"),)
    decision, _ = native_strategic_solve(state, 6, forecasts, options)
    assert not decision.transfers
    assert decision.chip == "triple_captain"
    assert isinstance(decision.lineup, Lineup)
    validate_decision_legality(state, decision)


def test_native_solver_rejects_padding_and_unavailable_player() -> None:
    state, forecasts = native_problem(horizon=1)
    with pytest.raises(ValueError, match="every target"):
        native_strategic_solve(state, 6, forecasts, get_strategic_replay_options(6))
    forecasts.loc[forecasts.player_id == 16, "purchase_eligible"] = False
    decision, _ = native_strategic_solve(state, 1, forecasts, get_strategic_replay_options(1))
    assert 16 not in {p.player_id for _, p in decision.transfers}


def test_future_horizon_changes_immediate_transfer_despite_current_loss() -> None:
    state, forecasts = native_problem()
    for pid, position, club in ((18, 4, 4), (19, 3, 3)):
        row = forecasts.iloc[-1].to_dict()
        row.update(player_id=pid, position_id=position, club_id=club)
        forecasts = pd.concat([forecasts, pd.DataFrame([row])], ignore_index=True)
    for gw in range(2, 8):
        forecasts.loc[forecasts.player_id >= 16, f"{gw}_Pts"] = 0.0 if gw == 2 else 100.0
    immediate, _ = native_strategic_solve(state, 1, forecasts, get_strategic_replay_options(1))
    planned, cert = native_strategic_solve(state, 6, forecasts, get_strategic_replay_options(6))
    assert not immediate.transfers
    assert len(planned.transfers) == 2
    assert len(cert.strategic_audit["plans"]) == 6


def test_native_profit_rounding_and_unaffordable_purchase() -> None:
    state, forecasts = native_problem(horizon=1)
    changed = tuple(replace(p, purchase=43, market=50) if p.player_id == 8 else p for p in state.squad)
    state = replace(state, squad=changed, bank=0)
    forecasts.loc[forecasts.player_id.isin([9, 10, 11, 12]), "2_Pts"] = 100.0
    forecasts.loc[forecasts.player_id == 16, "now_cost"] = 47
    decision, _ = native_strategic_solve(state, 1, forecasts, get_strategic_replay_options(1))
    assert not decision.transfers
    forecasts.loc[forecasts.player_id == 16, "now_cost"] = 46
    decision, cert = native_strategic_solve(state, 1, forecasts, get_strategic_replay_options(1))
    assert [(sold, bought.player_id) for sold, bought in decision.transfers] == [(8, 16)]
    assert cert.strategic_audit["plans"][0]["bank"] == 0
