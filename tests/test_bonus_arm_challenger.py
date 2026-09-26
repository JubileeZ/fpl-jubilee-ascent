"""Tests for bonus_arm_challenger prototype stub (#126)."""

from __future__ import annotations

import pandas as pd
import pytest

from models import get_model, list_model_names
from models.bonus_arm_challenger import BonusArmChallengerModel, _BONUS_SOFTMAX_T
from models.defence_link_challenger import DefenceLinkChallengerModel


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


def test_catalog_discovers_bonus_arm_challenger() -> None:
    assert "bonus_arm_challenger" in list_model_names()
    assert get_model("bonus_arm_challenger").name == "bonus_arm_challenger"


def test_identity_defaults_match_defence_link() -> None:
    """Stub with shipped T=6 matches parent ledger (no tuned lever yet)."""
    assert _BONUS_SOFTMAX_T == pytest.approx(6.0)
    frame = pd.DataFrame(
        [
            _row(player_id=1, fixture_id=100, per90_xg=0.2),
            _row(player_id=2, fixture_id=100, per90_xg=0.05, position_id=3),
        ]
    )
    parent = DefenceLinkChallengerModel().predict(frame, horizon=1)
    stub = BonusArmChallengerModel().predict(frame, horizon=1)
    for col in ("projected_points", "xp_bonus", "xp_clean_sheet", "xp_conceded", "xp_goals"):
        assert stub[col].to_numpy() == pytest.approx(parent[col].to_numpy(), rel=1e-9, abs=1e-9)
