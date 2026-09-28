import pandas as pd
import pytest

from models import get_model, list_model_names
from models.goals_path_challenger import GoalsPathChallengerModel, _GOAL_WEIGHT_SCALE
from models.hold_chase_challenger import HoldChaseChallengerModel
from models.position_goals_challenger import PositionGoalsChallengerModel
from tests.test_goals_path_challenger import _row


def test_catalog_discovers_position_goals_challenger() -> None:
    assert "position_goals_challenger" in list_model_names()
    assert get_model("position_goals_challenger").name == "position_goals_challenger"


def test_fit_scales_non_fwd_weights_only() -> None:
    history = pd.DataFrame(
        {
            "player_id": [1, 1, 2, 2],
            "minutes": [90.0, 90.0, 90.0, 90.0],
            "goals_scored": [1.0, 0.0, 1.0, 0.0],
            "expected_goals": [0.8, 0.4, 0.7, 0.3],
            "threat": [50.0, 30.0, 40.0, 20.0],
            "assists": [0.0, 1.0, 0.0, 0.0],
            "expected_assists": [0.2, 0.5, 0.1, 0.2],
            "creativity": [20.0, 40.0, 10.0, 15.0],
        }
    )
    parent = HoldChaseChallengerModel()
    parent.fit(history)
    child = PositionGoalsChallengerModel()
    child.fit(history)
    assert child._fwd_goal_weights == pytest.approx(parent.goal_weights)
    assert child.goal_weights == pytest.approx(parent.goal_weights * _GOAL_WEIGHT_SCALE)


def _history() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "player_id": [1, 1, 2, 2],
            "minutes": [90.0, 90.0, 90.0, 90.0],
            "goals_scored": [1.0, 0.0, 1.0, 0.0],
            "expected_goals": [0.8, 0.4, 0.7, 0.3],
            "threat": [50.0, 30.0, 40.0, 20.0],
            "assists": [0.0, 1.0, 0.0, 0.0],
            "expected_assists": [0.2, 0.5, 0.1, 0.2],
            "creativity": [20.0, 40.0, 10.0, 15.0],
        }
    )


def test_fwd_matches_hold_chase_and_mid_matches_goals_path() -> None:
    history = _history()
    fwd = pd.DataFrame([_row(player_id=1, position_id=4, per90_xg=0.60, per90_xa=0.20)])
    mid = pd.DataFrame([_row(player_id=2, position_id=3, per90_xg=0.50, per90_xa=0.10, fixture_id=101)])
    hold = HoldChaseChallengerModel()
    goals = GoalsPathChallengerModel()
    split = PositionGoalsChallengerModel()
    hold.fit(history)
    goals.fit(history)
    split.fit(history)

    hold_f = hold.predict(fwd, horizon=1).iloc[0]
    split_f = split.predict(fwd, horizon=1).iloc[0]
    assert float(split_f["xp_goals"]) == pytest.approx(float(hold_f["xp_goals"]))
    assert float(split_f["projected_minutes"]) == pytest.approx(float(hold_f["projected_minutes"]))

    goals_m = goals.predict(mid, horizon=1).iloc[0]
    split_m = split.predict(mid, horizon=1).iloc[0]
    hold_m = hold.predict(mid, horizon=1).iloc[0]
    assert float(split_m["xp_goals"]) == pytest.approx(float(goals_m["xp_goals"]))
    assert float(split_m["xp_goals"]) < float(hold_m["xp_goals"])
