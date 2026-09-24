"""Process Points reconstruction and eval-target wiring."""

import pandas as pd
import pytest

from backtesting.metrics import evaluate_predictions
from backtesting.process_points import (
    aggregate_process_points,
    blended_points,
    process_points_from_performances,
)


def test_process_points_missing_event_columns_are_zero() -> None:
    row = pd.DataFrame(
        [
            {
                "player_id": 1,
                "gameweek_id": 1,
                "position_id": 3,
                "total_points": 2.0,
            }
        ]
    )
    pts = process_points_from_performances(row)
    assert float(pts.iloc[0]) == 2.0


def test_process_points_replaces_goal_assist_luck() -> None:
    row = pd.DataFrame(
        [
            {
                "player_id": 1,
                "gameweek_id": 1,
                "position_id": 4,
                "total_points": 10.0,  # 2 min + 8 from 2 goals
                "goals_scored": 2,
                "assists": 0,
                "expected_goals": 0.5,
                "expected_assists": 0.0,
                "minutes": 90,
            }
        ]
    )
    # FWD: 2 goals = 8 pts realized; 0.5 xG = 2.0 process goal pts → 10 - 8 + 2 = 4
    pts = process_points_from_performances(row)
    assert float(pts.iloc[0]) == 4.0


def test_evaluate_predictions_process_target() -> None:
    df = pd.DataFrame(
        [
            {
                "player_id": 1,
                "gameweek": 1,
                "projected_points": 5.0,
                "actual_points": 10.0,
                "process_points": 4.0,
            },
            {
                "player_id": 2,
                "gameweek": 1,
                "projected_points": 3.0,
                "actual_points": 2.0,
                "process_points": 3.0,
            },
        ]
    )
    realized = evaluate_predictions(df, target_column="actual_points")
    process = evaluate_predictions(df, target_column="process_points")
    assert realized["eval_target"] == "actual_points"
    assert process["eval_target"] == "process_points"
    # vs process: errors (5-4)=1, (3-3)=0 → mae 0.5; vs realized mae ((5-10)+(3-2))/2 = 3.0
    assert abs(float(process["mae"]) - 0.5) < 1e-9
    assert abs(float(realized["mae"]) - 3.0) < 1e-9


def test_aggregate_process_points_sums_fixtures() -> None:
    rows = pd.DataFrame(
        [
            {
                "player_id": 1,
                "gameweek_id": 1,
                "position_id": 3,
                "total_points": 5.0,
                "goals_scored": 1,
                "assists": 0,
                "expected_goals": 0.2,
                "expected_assists": 0.0,
            },
            {
                "player_id": 1,
                "gameweek_id": 1,
                "position_id": 3,
                "total_points": 2.0,
                "goals_scored": 0,
                "assists": 0,
                "expected_goals": 0.1,
                "expected_assists": 0.0,
            },
        ]
    )
    out = aggregate_process_points(rows)
    assert len(out) == 1
    # fixture1: 5 - 5 + 0.2*5 = 1.0; fixture2: 2 - 0 + 0.5 = 2.5; sum 3.5
    assert abs(float(out["process_points"].iloc[0]) - 3.5) < 1e-9


def test_blended_points_default_is_fifty_fifty() -> None:
    actual = pd.Series([10.0, 2.0])
    process = pd.Series([4.0, 3.0])
    out = blended_points(actual, process)
    assert list(out) == [7.0, 2.5]


def test_blended_points_weight_favors_process_at_one() -> None:
    actual = pd.Series([10.0])
    process = pd.Series([4.0])
    out = blended_points(actual, process, weight=1.0)
    assert float(out.iloc[0]) == 4.0


def test_blended_points_rejects_out_of_range_weight() -> None:
    with pytest.raises(ValueError, match="weight"):
        blended_points(pd.Series([1.0]), pd.Series([1.0]), weight=1.5)


def test_evaluate_predictions_blend_target() -> None:
    df = pd.DataFrame(
        [
            {
                "player_id": 1,
                "gameweek": 1,
                "projected_points": 5.0,
                "actual_points": 10.0,
                "process_points": 4.0,
                "blended_points": 7.0,
            },
            {
                "player_id": 2,
                "gameweek": 1,
                "projected_points": 3.0,
                "actual_points": 2.0,
                "process_points": 3.0,
                "blended_points": 2.5,
            },
        ]
    )
    blend = evaluate_predictions(df, target_column="blended_points")
    assert blend["eval_target"] == "blended_points"
    # errors (5-7)=-2, (3-2.5)=0.5 → mae 1.25
    assert abs(float(blend["mae"]) - 1.25) < 1e-9
