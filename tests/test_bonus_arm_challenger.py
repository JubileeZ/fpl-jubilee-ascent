"""Tests for bonus_arm_challenger (#126 stub → #129 wire + calibrate)."""

from __future__ import annotations

import pandas as pd
import pytest

from models import get_model, list_model_names
from models import bonus_arm_challenger as bac
from models.bonus_arm_challenger import BonusArmChallengerModel
from models.defence_link_challenger import (
    DefenceLinkChallengerModel,
    _CS_SCALE,
    _GC_SCALE,
)


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


def test_frozen_levers_match_calibrator() -> None:
    assert bac._BONUS_SOFTMAX_T == pytest.approx(8.0)
    assert bac._XBPS_WEIGHTS == pytest.approx((0.1, 96.0, 48.0, 48.0, 24.0, 8.0))


def test_defence_scales_still_apply() -> None:
    frame = pd.DataFrame([_row(position_id=2, per90_goals_conceded=1.2)])
    parent = DefenceLinkChallengerModel().predict(frame, horizon=1).iloc[0]
    child = BonusArmChallengerModel().predict(frame, horizon=1).iloc[0]
    assert float(child["xp_clean_sheet"]) == pytest.approx(float(parent["xp_clean_sheet"]))
    assert float(child["xp_conceded"]) == pytest.approx(float(parent["xp_conceded"]))
    assert float(child["xp_clean_sheet"]) == pytest.approx(
        float(parent["xp_clean_sheet"]) / _CS_SCALE * _CS_SCALE
    )
    assert _CS_SCALE == pytest.approx(1.296903)
    assert _GC_SCALE == pytest.approx(1.145226)


def test_xbps_weights_change_fixture_bonus_vs_parent(monkeypatch: pytest.MonkeyPatch) -> None:
    """Non-flat weights must reshuffle fixture bonus (not identity with parent)."""
    frame = pd.DataFrame(
        [
            _row(player_id=1, fixture_id=100, per90_xg=0.4, per90_threat=40.0),
            _row(
                player_id=2,
                fixture_id=100,
                per90_xg=0.05,
                per90_threat=5.0,
                position_id=3,
                per90_defensive_contribution=0.0,
            ),
        ]
    )
    parent = DefenceLinkChallengerModel().predict(frame, horizon=1)
    monkeypatch.setattr(
        bac,
        "_XBPS_WEIGHTS",
        (0.1, 48.0, 12.0, 12.0, 6.0, 2.0),  # double goals term
    )
    monkeypatch.setattr(bac, "_BONUS_SOFTMAX_T", 6.0)
    child = BonusArmChallengerModel().predict(frame, horizon=1)
    assert child["xp_bonus"].to_numpy() != pytest.approx(
        parent["xp_bonus"].to_numpy(), rel=1e-6, abs=1e-6
    )


def test_softmax_temperature_changes_fixture_bonus(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = pd.DataFrame(
        [
            _row(player_id=1, fixture_id=100, per90_xg=0.4, per90_threat=40.0),
            _row(player_id=2, fixture_id=100, per90_xg=0.05, per90_threat=5.0, position_id=3),
        ]
    )
    monkeypatch.setattr(bac, "_BONUS_SOFTMAX_T", 6.0)
    sharp_t = BonusArmChallengerModel().predict(frame, horizon=1)
    monkeypatch.setattr(bac, "_BONUS_SOFTMAX_T", 20.0)
    flat_t = BonusArmChallengerModel().predict(frame, horizon=1)
    assert sharp_t["xp_bonus"].to_numpy() != pytest.approx(
        flat_t["xp_bonus"].to_numpy(), rel=1e-6, abs=1e-6
    )


def test_identity_weights_and_t_match_parent_bonus(monkeypatch: pytest.MonkeyPatch) -> None:
    """Shipped baseline weights + T=6 must match defence_link bonus ledger."""
    monkeypatch.setattr(bac, "_XBPS_WEIGHTS", (0.1, 24.0, 12.0, 12.0, 6.0, 2.0))
    monkeypatch.setattr(bac, "_BONUS_SOFTMAX_T", 6.0)
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
