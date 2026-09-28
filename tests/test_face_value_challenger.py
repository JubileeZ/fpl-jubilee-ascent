import pandas as pd
import pytest

from models import get_model, list_model_names
from models.face_value_challenger import _FINISHING_SHRINK_MINUTES, FaceValueChallengerModel
from models.hold_chase_challenger import HoldChaseChallengerModel


def _row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "player_id": 1,
        "position_id": 4,
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
        "per90_xg": 0.60,
        "per90_xa": 0.20,
        "per90_threat": 40.0,
        "per90_creativity": 20.0,
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


def _history() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "player_id": [1, 1, 2, 3],
            "minutes": [90.0, 90.0, 10.0, 0.0],
            "goals_scored": [2.0, 0.0, 1.0, 1.0],
            "expected_goals": [0.5, 0.5, 0.1, 0.0],
            "threat": [50.0, 30.0, 5.0, 0.0],
            "assists": [0.0, 1.0, 0.0, 0.0],
            "expected_assists": [0.2, 0.5, 0.1, 0.0],
            "creativity": [20.0, 40.0, 10.0, 0.0],
        }
    )


def test_catalog_discovers_face_value_challenger() -> None:
    assert "face_value_challenger" in list_model_names()
    assert get_model("face_value_challenger").name == "face_value_challenger"


def test_fit_keeps_face_value_weights_and_pools_goal_offsets_over_minutes() -> None:
    model = FaceValueChallengerModel()
    model.fit(_history())
    assert list(model.goal_weights) == [1.0, 0.0]
    assert list(model.assist_weights) == [1.0, 0.0]
    assert model.goal_offsets[1] == pytest.approx((2.0 - 1.0) * 90.0 / (180.0 + _FINISHING_SHRINK_MINUTES))
    assert model.goal_offsets[2] == pytest.approx(0.9 * 90.0 / (10.0 + _FINISHING_SHRINK_MINUTES))
    assert 3 not in model.goal_offsets
    assert model.assist_offsets == {}


def test_fit_on_empty_history_leaves_no_offsets() -> None:
    model = FaceValueChallengerModel()
    model.fit(pd.DataFrame())
    assert model.goal_offsets == {}


def test_start_shrink_moves_mid_range_start_mass_to_dnp() -> None:
    row = pd.Series(_row(p_dnp=0.5, p_start=0.5, p_sub_in=0.0, appearance_probability=0.5, avg_mins_3gw=40.0))
    _, parent_start, _ = HoldChaseChallengerModel._state_probabilities(row)
    p_dnp, p_start, p_sub_in = FaceValueChallengerModel._state_probabilities(row)
    assert p_start < parent_start
    assert p_dnp + p_start + p_sub_in == pytest.approx(1.0)


def test_predict_reconciles_ledger() -> None:
    frame = pd.DataFrame([_row(), _row(player_id=2, position_id=3, per90_xg=0.1)])
    model = FaceValueChallengerModel()
    model.fit(_history())
    out = model.predict(frame, horizon=1)
    components = [column for column in out.columns if column.startswith("xp_")]
    assert (out["projected_points"] - out[components].sum(axis=1)).abs().max() < 1e-9
