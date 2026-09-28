import numpy as np
import pandas as pd
import pytest

from models import get_model, list_model_names
from models.face_value_challenger import FaceValueChallengerModel
from models.learned_start_challenger import (
    LearnedStartChallengerModel,
    blend_states,
    learned_start_probabilities,
    preserve_mass,
)
from tests.test_multi_feature_assist_challenger import _row


def _start_history(n_gws: int = 12, players_per_club: int = 40) -> pd.DataFrame:
    """Two clubs; first 11 players of each club start every GW, rest never play."""
    rows: list[dict[str, object]] = []
    for gw in range(1, n_gws + 1):
        for club, opp, home in ((1, 2, True), (2, 1, False)):
            for k in range(players_per_club):
                starter = k < 11
                rows.append({
                    "player_id": club * 1000 + k, "fixture_id": gw * 10, "gameweek_id": gw, "opponent_club_id": opp,
                    "was_home": home, "minutes": 90.0 if starter else 0.0, "starts": 1.0 if starter else 0.0,
                    "expected_goals": 0.02, "expected_assists": 0.02, "creativity": 2.0, "goals_scored": 0.0, "threat": 0.0,
                })
    return pd.DataFrame(rows)


def _features(gw: int) -> pd.DataFrame:
    players = [_row(player_id=1000 + k, gameweek_id=gw, fixture_id=gw * 10, p_start=0.5, p_dnp=0.4, p_sub_in=0.1)
               for k in range(40)]
    players += [_row(player_id=2000 + k, club_id=2, opponent_id=1, is_home=False, gameweek_id=gw, fixture_id=gw * 10,
                     p_start=0.5, p_dnp=0.4, p_sub_in=0.1) for k in range(40)]
    return pd.DataFrame(players)


def test_catalog_discovers_learned_start_challenger() -> None:
    assert "learned_start_challenger" in list_model_names()
    assert get_model("learned_start_challenger").name == "learned_start_challenger"


def test_preserve_mass_hits_target_and_respects_cap() -> None:
    out = preserve_mass(np.array([0.9, 0.9, 0.1, 0.1]), target=2.2)
    assert out.sum() == pytest.approx(2.2)
    assert out.max() <= 0.99 + 1e-12


def test_blend_states_moves_start_delta_to_dnp_and_normalizes() -> None:
    p_dnp, p_start, p_sub_in = blend_states(0.3, 0.5, 0.2, 0.7)
    assert (p_dnp, p_start, p_sub_in) == pytest.approx((0.1, 0.7, 0.2))
    p_dnp, p_start, p_sub_in = blend_states(0.1, 0.5, 0.4, 0.9)
    assert p_dnp == 0.0 and p_dnp + p_start + p_sub_in == pytest.approx(1.0)


def test_learned_start_ranks_regular_starters_and_skips_early_gws() -> None:
    history = _start_history()
    assert learned_start_probabilities(history[history["gameweek_id"] < 4], _features(4)) == {}
    probs = learned_start_probabilities(history, _features(13))
    assert min(probs[1000 + k] for k in range(11)) > max(probs[1000 + k] for k in range(11, 40))


def test_predict_reconciles_ledger_and_preserves_start_mass() -> None:
    history, frame = _start_history(), _features(13)
    model = LearnedStartChallengerModel()
    model.fit(history)
    out = model.predict(frame, horizon=1)
    components = [column for column in out.columns if column.startswith("xp_")]
    assert (out["projected_points"] - out[components].sum(axis=1)).abs().max() < 1e-9
    champion_mass = sum(FaceValueChallengerModel._state_probabilities(row)[1] for _, row in frame.iterrows())
    assert sum(model._p_target.values()) == pytest.approx(champion_mass)
