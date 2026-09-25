import pandas as pd
import pytest

from models import get_model, list_model_names
from models.defence_link_challenger import (
    DefenceLinkChallengerModel,
    _CS_SCALE,
    _GC_SCALE,
)
from models.goals_path_challenger import GoalsPathChallengerModel, _GOAL_WEIGHT_SCALE
from models.hold_chase_challenger import HoldChaseChallengerModel


def _row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "player_id": 1,
        "position_id": 2,
        "gameweek_id": 10,
        "fixture_id": 100,
        "difficulty": 3.0,
        "chance_of_playing": 100.0,
        "has_availability_snapshot": False,
        "is_immediate_next_gw": False,
        "p_dnp": 0.0,
        "p_start": 1.0,
        "p_sub_in": 0.0,
        "xmins_if_start": 90.0,
        "xmins_if_sub_in": 20.0,
        "p_60_if_start": 1.0,
        "p_60_if_sub_in": 0.0,
        "appearance_probability": 1.0,
        "avg_mins_3gw": 80.0,
        "per90_xg": 0.10,
        "per90_xa": 0.05,
        "per90_threat": 10.0,
        "per90_creativity": 10.0,
        "per90_goals": 0.0,
        "per90_assists": 0.0,
        "per90_goals_conceded": 1.0,
        "per90_saves": 0.0,
        "per90_yellow_cards": 0.0,
        "per90_red_cards": 0.0,
        "per90_penalties_saved": 0.0,
        "per90_penalties_missed": 0.0,
        "per90_own_goals": 0.0,
        "per90_defensive_contribution": 0.0,
        "attack_multiplier": 1.0,
        "defence_multiplier": 1.0,
        "penalties_order": 0.0,
    }
    row.update(overrides)
    return row


def test_catalog_discovers_defence_link_challenger() -> None:
    assert "defence_link_challenger" in list_model_names()
    assert get_model("defence_link_challenger").name == "defence_link_challenger"


def test_inherits_goals_weight_scale() -> None:
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
    child = DefenceLinkChallengerModel()
    child.fit(history)
    assert child.goal_weights == pytest.approx(parent.goal_weights * _GOAL_WEIGHT_SCALE)


def test_cs_and_conceded_scales_apply() -> None:
    frame = pd.DataFrame([_row(position_id=2, per90_goals_conceded=1.2)])
    parent = GoalsPathChallengerModel().predict(frame, horizon=1).iloc[0]
    child = DefenceLinkChallengerModel().predict(frame, horizon=1).iloc[0]
    assert float(child["xp_clean_sheet"]) == pytest.approx(
        float(parent["xp_clean_sheet"]) * _CS_SCALE
    )
    assert float(child["xp_conceded"]) == pytest.approx(
        float(parent["xp_conceded"]) * _GC_SCALE
    )
    delta = (_CS_SCALE - 1.0) * float(parent["xp_clean_sheet"]) + (
        _GC_SCALE - 1.0
    ) * float(parent["xp_conceded"])
    assert float(child["projected_points"]) == pytest.approx(
        float(parent["projected_points"]) + delta
    )
