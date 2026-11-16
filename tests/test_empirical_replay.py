"""TDD tests for unified mode='empirical' replay contracts (#178, #179, #189)."""

from __future__ import annotations

from dataclasses import asdict

import pytest

from backtesting.replay_cache import _batch
from backtesting.replay_state import (
    Decision,
    Lineup,
    Outcome,
    OutcomeBatch,
    Player,
    initial_state,
    state_hash,
    transition,
)
from models.scoring_matrix import Position

POSITIONS: tuple[Position, ...] = (
    "GK", "GK", "D", "D", "D", "D", "D", "M", "M", "M", "M", "M", "F", "F", "F"
)


def _squad(*, all_eligible: bool = True) -> tuple[Player, ...]:
    return tuple(
        Player(
            player_id=pid,
            position=pos,
            club=(pid - 1) % 5 + 1,
            purchase=50,
            market=50,
            purchase_eligible=True if (all_eligible or pid != 15) else False,
        )
        for pid, pos in enumerate(POSITIONS, 1)
    )


def test_zero_minute_disciplinary_card_outcome_accepted_only_with_zero_residual() -> None:
    squad = _squad()
    state = initial_state("2025-26", squad)
    starters = (1, 3, 4, 5, 6, 8, 9, 10, 11, 13, 14)
    bench = (2, 7, 12, 15)
    decision = Decision((), Lineup(starters, bench, 8, 9), state_hash(state), 1)
    base_outcomes = {p.player_id: Outcome(2, 90, True) for p in squad}
    # GW22 player_id=218 Barnes pattern: minutes=0, appeared=False, yellow_cards=1, total_points=-1
    # Starter GK(1) gets 0-min yellow card and bench GK(2) did not play -> no GK autosub, so GK(1) scores -1
    card_outcomes = {
        **base_outcomes,
        1: Outcome(-1, 0, False, yellow_cards=1, red_cards=0, component_points_sum=-1),
        2: Outcome(0, 0, False),
    }
    batch = OutcomeBatch("2025-26", 1, "dev-mirror", tuple(card_outcomes.items()))
    result = transition(state, decision, batch)
    assert result.gross == 19
    assert result.net == 21  # 10*2 (captain 8 doubles) + (-1)

    # replay_cache _batch round-trip preserves card metadata
    roundtrip = _batch(asdict(batch))
    assert dict(roundtrip.outcomes)[1].yellow_cards == 1
    assert dict(roundtrip.outcomes)[1].component_points_sum == -1

    # Red card (-3) at 0 minutes with no available outfield bench subs -> -3 counted
    no_sub_base = {**base_outcomes, 7: Outcome(0, 0, False), 12: Outcome(0, 0, False), 15: Outcome(0, 0, False)}
    red_batch = OutcomeBatch(
        "2025-26", 1, "dev-mirror", tuple({**no_sub_base, 14: Outcome(-3, 0, False, red_cards=1, component_points_sum=-3)}.items())
    )
    red_result = transition(state, decision, red_batch)
    assert red_result.gross == 17
    assert red_result.net == 19

    # Non-card zero-minute points or residual mismatch must fail closed
    for bad in (
        Outcome(2, 0, False, yellow_cards=1, component_points_sum=2),
        Outcome(-1, 0, False, yellow_cards=0, red_cards=0, component_points_sum=-1),
        Outcome(-1, 0, False, yellow_cards=1, component_points_sum=1),
        Outcome(-1, 0, True, yellow_cards=1, component_points_sum=-1),
        Outcome(5, 90, True, yellow_cards=0, component_points_sum=2),
    ):
        bad_batch = OutcomeBatch("2025-26", 1, "dev-mirror", tuple({**base_outcomes, 14: bad}.items()))
        with pytest.raises(ValueError, match="Zero-minute|appearance|card|Component"):
            transition(state, decision, bad_batch)

    # Boolean inside yellow_cards/component_points_sum in serialized dict must fail transition validation instead of int(bool) coercion
    d_bad = asdict(batch)
    d_bad["outcomes"][0][1]["yellow_cards"] = True
    with pytest.raises(ValueError, match="Incomplete|outcome"):
        transition(state, decision, _batch(d_bad))


def test_initial_state_requires_purchase_eligible_true_for_all_15() -> None:
    with pytest.raises(ValueError, match="purchase_eligible|Opening"):
        initial_state("2025-26", _squad(all_eligible=False))
