import pandas as pd
import pytest

from models import get_model, list_model_names
from models.asymmetric_finishing_challenger import (
    _FINISHING_SHRINK_NEG,
    _FINISHING_SHRINK_POS,
    AsymmetricFinishingChallengerModel,
)


def _row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "player_id": 1,
        "club_id": 1,
        "opponent_club_id": 2,
        "is_home": True,
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
    # Player 1: goals=2.0, xG=1.0 -> positive residual +1.0
    # Player 2: goals=0.0, xG=1.0 -> negative residual -1.0
    return pd.DataFrame(
        {
            "player_id": [1, 1, 2, 2],
            "fixture_id": [10, 20, 10, 20],
            "gameweek_id": [1, 2, 1, 2],
            "opponent_club_id": [2, 3, 1, 3],
            "was_home": [True, False, False, True],
            "minutes": [90.0, 90.0, 90.0, 90.0],
            "starts": [1.0, 1.0, 1.0, 1.0],
            "goals_scored": [2.0, 0.0, 0.0, 0.0],
            "expected_goals": [0.5, 0.5, 0.5, 0.5],
            "threat": [50.0, 30.0, 20.0, 20.0],
            "assists": [0.0, 1.0, 0.0, 0.0],
            "expected_assists": [0.2, 0.5, 0.1, 0.1],
            "creativity": [20.0, 40.0, 10.0, 10.0],
        }
    )


def test_catalog_discovers_asymmetric_finishing_challenger() -> None:
    assert "asymmetric_finishing_challenger" in list_model_names()
    assert get_model("asymmetric_finishing_challenger").name == "asymmetric_finishing_challenger"


def test_asymmetric_shrinkage_applies_kpos_and_kneg() -> None:
    model = AsymmetricFinishingChallengerModel()
    model.fit(_history())
    
    # Player 1 (positive residual +1.0): shrunk with K_POS (1500)
    expected_pos = 1.0 * 90.0 / (180.0 + _FINISHING_SHRINK_POS)
    assert model.goal_offsets[1] == pytest.approx(expected_pos)

    # Player 2 (negative residual -1.0): shrunk with K_NEG (3000)
    expected_neg = -1.0 * 90.0 / (180.0 + _FINISHING_SHRINK_NEG)
    assert model.goal_offsets[2] == pytest.approx(expected_neg)


def test_predict_reconciles_ledger_and_preserves_component_sum() -> None:
    frame = pd.DataFrame([_row(player_id=1), _row(player_id=2, position_id=3)])
    model = AsymmetricFinishingChallengerModel()
    model.fit(_history())
    out = model.predict(frame, horizon=1)
    components = [col for col in out.columns if col.startswith("xp_")]
    assert (out["projected_points"] - out[components].sum(axis=1)).abs().max() < 1e-9
