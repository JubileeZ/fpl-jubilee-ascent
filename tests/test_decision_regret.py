import pytest

from backtesting.decision_regret import (
    LineupDecision,
    PlayerOutcome,
    evaluate_decision_regret,
    optimize_model_lineup,
    score_lineup,
)
from commands.decision_regret import _actual_decision


def _squad_outcomes() -> dict[int, PlayerOutcome]:
    positions = {
        1: 1,
        2: 2,
        3: 2,
        4: 2,
        5: 2,
        6: 2,
        7: 3,
        8: 3,
        9: 3,
        10: 3,
        11: 3,
        12: 4,
        13: 4,
        14: 4,
        15: 4,
    }
    return {
        player_id: PlayerOutcome(player_id, position, float(player_id), 90.0)
        for player_id, position in positions.items()
    }


def test_bench_order_changes_automatic_substitution():
    outcomes = _squad_outcomes()
    outcomes[2] = PlayerOutcome(2, 2, 0.0, 0.0)
    outcomes[5] = PlayerOutcome(5, 2, 2.0, 90.0)
    outcomes[6] = PlayerOutcome(6, 2, 8.0, 90.0)
    starters = (1, 2, 3, 4, 7, 8, 9, 10, 12, 13, 14)

    first = score_lineup(
        LineupDecision(starters, (5, 6, 11, 15), 12, 13),
        outcomes,
    )
    second = score_lineup(
        LineupDecision(starters, (6, 5, 11, 15), 12, 13),
        outcomes,
    )

    assert 5 in first.final_starters
    assert 6 in second.final_starters
    assert second.points > first.points


def test_vice_captain_fallback_applies_when_captain_does_not_play():
    outcomes = _squad_outcomes()
    outcomes[12] = PlayerOutcome(12, 4, 6.0, 0.0)
    outcomes[13] = PlayerOutcome(13, 4, 5.0, 90.0)
    starters = (1, 2, 3, 4, 7, 8, 9, 10, 12, 13, 14)
    decision = LineupDecision(starters, (5, 6, 11, 15), 12, 13)

    result = score_lineup(decision, outcomes)

    assert result.points == pytest.approx(sum(outcomes[player].points for player in result.final_starters) + 5.0)


def test_model_and_oracle_stay_inside_historical_squad():
    outcomes = _squad_outcomes()
    squad = tuple(outcomes)
    model = optimize_model_lineup(squad, outcomes)
    report = evaluate_decision_regret(model, model, squad, outcomes)
    oracle = report["oracle_decision"]

    assert set(model.starters + model.bench) == set(squad)
    assert set(oracle.starters + oracle.bench) == set(squad)
    assert report["model_regret"] == pytest.approx(
        report["oracle_points"] - report["model_points"]
    )


def test_illegal_squad_formation_is_rejected():
    outcomes = {
        player_id: PlayerOutcome(player_id, 3, 1.0, 90.0)
        for player_id in range(1, 16)
    }

    with pytest.raises(ValueError, match="legal FPL formation"):
        optimize_model_lineup(tuple(outcomes), outcomes)


def test_public_picks_convert_to_actual_lineup():
    picks = [
        {
            "element": player_id,
            "position": position,
            "is_captain": player_id == 1,
            "is_vice_captain": player_id == 2,
            "multiplier": 2 if player_id == 1 else 1,
        }
        for position, player_id in enumerate(range(1, 16), start=1)
    ]

    decision = _actual_decision(picks)

    assert len(decision.starters) == 11
    assert decision.bench == (12, 13, 14, 15)
    assert decision.captain == 1
    assert decision.vice_captain == 2
