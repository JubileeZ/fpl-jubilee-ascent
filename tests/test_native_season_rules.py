import pytest
import pandas as pd
from datetime import UTC, datetime
from dataclasses import replace
from typing import cast

from backtesting.season_rules import Chip, afcon_topup_known_at, chip_window, get_rules, next_free_transfers, selling_price, validate_chip_calendar
from models.scoring_matrix import Position, event_points
from models.component_baseline import ComponentBaseline
from projections.explorer_slice import realized_gameweek_score
from backtesting.walkforward import _build_actual_components
from backtesting.replay_state import Decision, Lineup, Outcome, OutcomeBatch, Player, ReplayState, Transition, initial_state, score_lineup, state_hash, transfer_squad, transition


def apply_decision(state: ReplayState, transfers: tuple[tuple[int, Player], ...], lineup: Lineup, outcomes: dict[int, Outcome], chip: Chip | None = None) -> Transition:
    decision = Decision(transfers, lineup, state_hash(state), state.deadline, chip)
    batch = OutcomeBatch(state.rules_version, state.deadline, "test-source", tuple(outcomes.items()))
    return transition(state, decision, batch)


def test_prices_and_transfer_rollover() -> None:
    assert selling_price(50, 53) == 51
    assert selling_price(50, 49) == 49
    assert next_free_transfers(get_rules("2023-24"), 2, 0, None, 4) == 2
    assert next_free_transfers(get_rules("2024-25"), 2, 0, None, 4) == 3
    assert next_free_transfers(get_rules("2024-25"), 2, 3, None, 4) == 1
    assert next_free_transfers(get_rules("2023-24"), 2, 3, "wildcard", 4) == 1
    assert next_free_transfers(get_rules("2024-25"), 2, 3, "free_hit", 4) == 2
    assert next_free_transfers(get_rules("2025-26"), 1, 0, None, 15) == 5
    assert next_free_transfers(get_rules("2024-25"), 0, 0, None, 1) == 1
    with pytest.raises(ValueError):
        next_free_transfers(get_rules("2024-25"), 0, 1, None, 1)


def test_native_scoring_and_default_compatibility() -> None:
    assert event_points("goals", "GK", 1, rules_version="2023-24") == 6
    assert event_points("goals", "GK", 1, rules_version="2024-25") == 10
    assert event_points("goals", "GK", 1) == 10
    assert event_points("defensive_contributions", "D", 1, rules_version="2024-25") == 0
    assert event_points("defensive_contributions", "D", 1, rules_version="2025-26") == 2
    with pytest.raises(ValueError):
        get_rules("unknown")


def test_initial_capital_and_price_preservation() -> None:
    positions: tuple[Position, ...] = ("GK", "GK", "D", "D", "D", "D", "D", "M", "M", "M", "M", "M", "F", "F", "F")
    players = tuple(Player(i + 1, position, i // 3 + 1, 50, 50) for i, position in enumerate(positions))
    state = initial_state("2024-25", players)
    assert state.bank == 250
    assert state.free_transfers == 0
    changed = tuple(Player(p.player_id, p.position, p.club, p.purchase, 53 if p.player_id == 1 else 50) for p in players)
    bought = Player(100, "GK", 6, 55, 55)
    squad, bank = transfer_squad(changed, 10, ((1, bought),))
    assert bank == 6
    assert next(p for p in squad if p.player_id == 2).purchase == 50
    assert next(p for p in squad if p.player_id == 100).purchase == 55
    with pytest.raises(ValueError):
        transfer_squad(changed, 0, ((1, bought),))


def test_component_model_receives_explicit_native_rules() -> None:
    row = {"player_id": 1, "position_id": 1, "gameweek_id": 2, "has_seed": True,
           "avg_mins_3gw": 90, "per90_goals": 1, "difficulty": 3}
    model = ComponentBaseline()
    native = model.predict(pd.DataFrame([{**row, "native_rules_version": "2023-24"}]), 1)
    default = model.predict(pd.DataFrame([row]), 1)
    assert native.iloc[0]["xp_goals"] == 6
    assert default.iloc[0]["xp_goals"] == 10
    with pytest.raises(ValueError):
        model.predict(pd.DataFrame([{**row, "native_rules_version": None}]), 1)


def test_chip_windows() -> None:
    assert chip_window(get_rules("2023-24"), "wildcard", 20) == 1
    assert chip_window(get_rules("2023-24"), "wildcard", 21) == 2
    assert chip_window(get_rules("2024-25"), "wildcard", 20) == 2
    assert chip_window(get_rules("2025-26"), "bench_boost", 19) == 1
    assert chip_window(get_rules("2025-26"), "bench_boost", 20) == 2
    with pytest.raises(ValueError):
        chip_window(get_rules("2025-26"), "free_hit", 1)
    with pytest.raises(ValueError):
        validate_chip_calendar(get_rules("2025-26"), ((19, "free_hit"), (20, "free_hit")))
    assert not afcon_topup_known_at(datetime(2025, 7, 19, tzinfo=UTC))
    assert afcon_topup_known_at(datetime(2025, 7, 20, tzinfo=UTC))


def test_lineup_captain_and_atomic_opening_transition() -> None:
    positions: tuple[Position, ...] = ("GK", "GK", "D", "D", "D", "D", "D", "M", "M", "M", "M", "M", "F", "F", "F")
    players = tuple(Player(i + 1, position, i // 3 + 1, 50, 50) for i, position in enumerate(positions))
    lineup = Lineup((1, 3, 4, 5, 8, 9, 10, 11, 13, 14, 15), (2, 6, 7, 12), 8, 9)
    outcomes = {p.player_id: Outcome(2, 90, True) for p in players}
    outcomes[8] = Outcome(0, 0, False)
    outcomes[9] = Outcome(5, 90, True)
    gross, increment = score_lineup(players, lineup, outcomes, "triple_captain")
    assert (gross, increment) == (25, 10)
    result = apply_decision(initial_state("2024-25", players), (), lineup, outcomes)
    assert (result.gross, result.captain_increment, result.hit, result.net) == (25, 5, 0, 30)
    assert result.state.deadline == 2 and result.state.free_transfers == 1
    assert result.state.parent_hash is not None
    with pytest.raises(ValueError):
        apply_decision(initial_state("2024-25", players), (), lineup, {})


def test_free_hit_restoration_and_hit_once() -> None:
    positions: tuple[Position, ...] = ("GK", "GK", "D", "D", "D", "D", "D", "M", "M", "M", "M", "M", "F", "F", "F")
    players = tuple(Player(i + 1, position, i // 3 + 1, 50, 50) for i, position in enumerate(positions))
    lineup = Lineup((1, 3, 4, 5, 8, 9, 10, 11, 13, 14, 15), (2, 6, 7, 12), 8, 9)
    outcomes = {p.player_id: Outcome(2, 90, True) for p in players}
    state = apply_decision(initial_state("2024-25", players), (), lineup, outcomes).state
    replacement = Player(100, "GK", 6, 55, 55)
    new_lineup = Lineup((100, *lineup.starters[1:]), lineup.bench, 8, 9)
    changed_outcomes = {**outcomes, 100: Outcome(2, 90, True)}
    del changed_outcomes[1]
    free_hit = apply_decision(state, ((1, replacement),), new_lineup, changed_outcomes, "free_hit")
    assert free_hit.state.squad == state.squad and free_hit.state.bank == state.bank
    assert free_hit.state.free_transfers == 1 and free_hit.hit == 0
    spent = apply_decision(state, ((1, replacement),), new_lineup, changed_outcomes).state
    replacement2 = Player(101, "GK", 6, 55, 55)
    next_lineup = Lineup((101, *lineup.starters[1:]), lineup.bench, 8, 9)
    next_outcomes = {**changed_outcomes, 101: Outcome(2, 90, True)}
    del next_outcomes[100]
    replacement3 = Player(102, "D", 7, 50, 50)
    next_lineup = Lineup(tuple(102 if i == 3 else i for i in next_lineup.starters), next_lineup.bench, 8, 9)
    del next_outcomes[3]
    next_outcomes[102] = Outcome(2, 90, True)
    result = apply_decision(spent, ((100, replacement2), (3, replacement3)), next_lineup, next_outcomes)
    assert result.hit == 4 and result.net == result.gross + result.captain_increment - 4


def test_native_observed_components_require_complete_fixture() -> None:
    row = {"minutes": 90, "total_points": 12, "goals_scored": 1, "assists": 0,
           "clean_sheets": 1, "goals_conceded": 0, "saves": 0, "bonus": 0}
    assert realized_gameweek_score([row], 1, rules_version="2023-24").xp_goals == 6
    assert realized_gameweek_score([row], 1, rules_version="2024-25").xp_goals == 10
    with pytest.raises(ValueError):
        realized_gameweek_score([{"minutes": 90}], 1, rules_version="2023-24")
    with pytest.raises(ValueError):
        realized_gameweek_score([], 1, rules_version="2023-24")
    for bad in ("unfinished", float("nan"), float("inf")):
        with pytest.raises(ValueError):
            realized_gameweek_score([{**row, "minutes": bad}], 1, rules_version="2023-24")
    with pytest.raises(ValueError):
        realized_gameweek_score([row], 99, rules_version="2023-24")


def test_native_actual_components() -> None:
    row = {"player_id": 1, "total_points": 10, "minutes": 90, "goals_scored": 1, "assists": 0, "clean_sheets": 1,
           "goals_conceded": 0, "saves": 0, "penalties_saved": 0, "penalties_missed": 0,
           "own_goals": 0, "yellow_cards": 0, "red_cards": 0, "bonus": 0}
    feature = pd.DataFrame([{"player_id": 1, "position_id": 1, "native_rules_version": "2023-24"}])
    assert _build_actual_components(pd.DataFrame([row]), feature).iloc[0]["actual_xp_goals"] == 6
    assert _build_actual_components(pd.DataFrame([row]), feature).iloc[0]["actual_xp_defcon"] == 0
    with pytest.raises(ValueError):
        _build_actual_components(pd.DataFrame([{**row, "assists": float("nan")}]), feature)


def test_ordered_autosubs_goalkeeper_and_formation() -> None:
    positions: tuple[Position, ...] = ("GK", "GK", "D", "D", "D", "D", "D", "M", "M", "M", "M", "M", "F", "F", "F")
    players = tuple(Player(i + 1, position, i // 3 + 1, 50, 50) for i, position in enumerate(positions))
    lineup = Lineup((1, 3, 4, 5, 8, 9, 10, 11, 13, 14, 15), (2, 12, 6, 7), 8, 9)
    outcomes = {p.player_id: Outcome(2, 90, True) for p in players}
    outcomes[1] = outcomes[3] = Outcome(0, 0, False)
    outcomes[2] = Outcome(5, 90, True)
    outcomes[12] = Outcome(9, 90, True)
    outcomes[6] = Outcome(4, 90, True)
    gross, _ = score_lineup(players, lineup, outcomes, None)
    assert gross == 27
    boosted, _ = score_lineup(players, lineup, outcomes, "bench_boost")
    assert boosted == sum(o.points for o in outcomes.values())
    outcomes[3] = Outcome(1, 0, False)
    with pytest.raises(ValueError):
        score_lineup(players, lineup, outcomes, None)


def test_decision_and_outcome_scope() -> None:
    positions: tuple[Position, ...] = ("GK", "GK", "D", "D", "D", "D", "D", "M", "M", "M", "M", "M", "F", "F", "F")
    players = tuple(Player(i + 1, position, i // 3 + 1, 50, 50) for i, position in enumerate(positions))
    state = initial_state("2024-25", players)
    lineup = Lineup((1, 3, 4, 5, 8, 9, 10, 11, 13, 14, 15), (2, 6, 7, 12), 8, 9)
    decision = Decision((), lineup, state_hash(state), 1, "bench_boost")
    batch = OutcomeBatch("2024-25", 1, "synthetic-source", tuple((p.player_id, Outcome(2, 90, True)) for p in players))
    for bad in (Outcome(2, -1, True), Outcome(cast(int, []), 90, True)):
        with pytest.raises(ValueError):
            transition(state, decision, replace(batch, outcomes=(*batch.outcomes, (100, bad))))
    result = transition(state, decision, batch)
    assert result.state.free_transfers == 1 and result.gross == 30
    shared = OutcomeBatch("2024-25", 2, "synthetic-source", (*batch.outcomes, (100, Outcome(3, 90, True))))
    changed_squad = tuple(Player(100, "GK", 6, 50, 50) if p.player_id == 1 else p for p in players)
    other = replace(result.state, squad=changed_squad)
    other_lineup = replace(lineup, starters=tuple(100 if i == 1 else i for i in lineup.starters))
    assert transition(result.state, Decision((), lineup, state_hash(result.state), 2), shared).gross == 22
    assert transition(other, Decision((), other_lineup, state_hash(other), 2), shared).gross == 23
    with pytest.raises(ValueError):
        transition(result.state, decision, batch)
    with pytest.raises(ValueError):
        transition(state, decision, OutcomeBatch("2023-24", 1, "synthetic-source", batch.outcomes))
    with pytest.raises(ValueError):
        transition(result.state, Decision((), lineup, state_hash(result.state), 2), batch)
    with pytest.raises(ValueError):
        apply_decision(replace(result.state, free_transfers=1.5), (), lineup, dict(batch.outcomes))
    with pytest.raises(ValueError):
        apply_decision(replace(result.state, chip_history=((1, "bench_boost", 1), (1, "triple_captain", 1))), (), lineup, dict(batch.outcomes))
