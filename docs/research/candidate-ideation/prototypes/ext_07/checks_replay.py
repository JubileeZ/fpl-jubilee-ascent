from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))
sys.path.insert(0, str(Path(__file__).resolve().parents[5] / "tests"))

from prototypes import ExposureReplay
from test_face_value_challenger import _row

from backtesting.walkforward import LEDGER_COMPONENTS
from models.adaptive_causal_challenger import AdaptiveCausalChallengerModel
from models.scoring_matrix import event_points


class FixedAssistReplay(ExposureReplay):
    def _fit_assist_rates(self, features_df: pd.DataFrame) -> dict[tuple[int, int], float]:
        return {(int(row["player_id"]), int(row["fixture_id"])): 0.123 for _, row in features_df.iterrows()}


def frame(**overrides: object) -> pd.DataFrame:
    return pd.DataFrame([_row(player_id=i, position_id=i, **overrides) for i in range(1, 5)])


def test_unchanged_states_reproduce_inherited_decoder_with_assist_cache() -> None:
    model = FixedAssistReplay()
    model.fit(pd.DataFrame())
    features = frame(p_start=0.8, p_sub_in=0.1, p_dnp=0.1)
    original = model.predict(features, 1)
    replay = model._replay(features, original, np.ones(4), np.ones(4))
    np.testing.assert_allclose(replay[list(LEDGER_COMPONENTS)], original[list(LEDGER_COMPONENTS)], atol=1e-12)
    np.testing.assert_allclose(replay["projected_points"], original["projected_points"], atol=1e-12)
    assert model._assist_rates[(1, 100)] == 0.123


def test_state_simplex_cap_and_component_sum() -> None:
    model = ExposureReplay()
    model.fit(pd.DataFrame())
    features = frame(xmins_cap=30.0)
    final = model.predict(features, 1)
    final["p_start"], final["p_sub_in"], final["p_dnp"] = 0.95, 0.25, 0.4
    final["xmins_if_start"], final["xmins_if_sub_in"] = 90.0, 20.0
    replay = model._replay(features, final, np.ones(4), np.ones(4))
    assert np.allclose(replay["p_start"], 0.95)
    assert np.allclose(replay["p_sub_in"], 0.05)
    assert np.allclose(replay["projected_minutes"], 30.0)
    assert np.allclose(replay["projected_points"], replay[list(LEDGER_COMPONENTS)].sum(axis=1))


@pytest.mark.parametrize("override", [
    {"external_xmins": 62.0},
    {"fixture_id": -1},
    {"chance_of_playing": 0.0, "is_immediate_next_gw": True, "has_availability_snapshot": True},
])
def test_oracle_blank_and_hard_dnp(override: dict[str, object]) -> None:
    model = ExposureReplay()
    model.fit(pd.DataFrame())
    features = frame(**override)
    original = model.predict(features, 1)
    replay = model._replay(features, original, np.ones(4), np.ones(4))
    np.testing.assert_allclose(replay[list(LEDGER_COMPONENTS)], original[list(LEDGER_COMPONENTS)], atol=1e-12)
    np.testing.assert_allclose(replay["projected_minutes"], original["projected_minutes"], atol=1e-12)


def test_group_multipliers_apply_once_and_bps_uses_scoring_counts() -> None:
    model = FixedAssistReplay()
    model.fit(pd.DataFrame())
    features = frame()
    original = model.predict(features, 1)
    replay = model._replay(features, original, np.full(4, 1.10), np.full(4, 0.90))
    np.testing.assert_allclose(replay["xp_goals"], original["xp_goals"] * 1.10)
    np.testing.assert_allclose(replay["xp_assists"], original["xp_assists"] * 0.90)
    assert event_points("goals", "GK", 1.0) == 10.0
    assert np.isclose(replay["xp_bonus"].sum(), 6.0)


def test_early_gameweeks_equal_champion() -> None:
    features = frame(gameweek_id=19)
    candidate = ExposureReplay()
    champion = AdaptiveCausalChallengerModel()
    candidate.fit(pd.DataFrame())
    champion.fit(pd.DataFrame())
    pd.testing.assert_frame_equal(candidate.predict(features, 1), champion.predict(features, 1))


def test_replay_keeps_prepared_defender_rate_without_second_adjustment() -> None:
    features = pd.DataFrame([_row(player_id=i, position_id=2, per90_xg=0.4) for i in (1, 2)])
    history = pd.DataFrame({
        "player_id": [1, 2], "gameweek_id": [1, 1], "minutes": [90.0, 90.0],
        "goals_scored": [0.0, 1.0], "expected_goals": [0.01, 1.0],
    })
    model = FixedAssistReplay()
    model.fit(history)
    original = model.predict(features, 1)
    assert model._effective_rows[(1, 10, 100)]["per90_xg"] != 0.4
    replay = model._replay(features, original, np.ones(2), np.ones(2))
    np.testing.assert_allclose(replay[list(LEDGER_COMPONENTS)], original[list(LEDGER_COMPONENTS)], atol=1e-12)
