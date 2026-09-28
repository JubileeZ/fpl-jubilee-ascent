import pandas as pd
import pytest

from models import get_model, list_model_names
from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel, shrunk_xg_rates
from models.learned_start_challenger import LearnedStartChallengerModel
from tests.test_learned_start_challenger import _features, _start_history


def test_catalog_discovers_def_xg_shrink_challenger() -> None:
    assert "def_xg_shrink_challenger" in list_model_names()
    assert get_model("def_xg_shrink_challenger").name == "def_xg_shrink_challenger"


def test_def_rates_shrink_harder_than_other_positions() -> None:
    hist = pd.DataFrame({"player_id": [1, 2, 3, 4], "gameweek_id": [1, 1, 1, 1], "minutes": [90.0] * 4,
                         "expected_goals": [0.9, 0.1, 0.9, 0.1]})
    positions = pd.Series({1: 2, 2: 2, 3: 3, 4: 3})
    base, new = shrunk_xg_rates(hist, positions, {}), shrunk_xg_rates(hist, positions, {2: 2400.0})
    assert new[1] < base[1] and new[2] > base[2]
    assert new[3] == pytest.approx(base[3]) and new[4] == pytest.approx(base[4])
    assert abs(new[1] - 0.5) < abs(base[1] - 0.5)


def test_predict_reconciles_ledger_and_matches_champion_without_def_signal() -> None:
    history, frame = _start_history(), _features(13)
    history["expected_goals"] = history["expected_goals"].where(history["player_id"] % 2 == 0, 0.3)
    frame = frame.assign(position_id=2)
    candidate, champion = DefXgShrinkChallengerModel(), LearnedStartChallengerModel()
    candidate.fit(history)
    champion.fit(history)
    out, ref = candidate.predict(frame, horizon=1), champion.predict(frame, horizon=1)
    components = [column for column in out.columns if column.startswith("xp_")]
    assert (out["projected_points"] - out[components].sum(axis=1)).abs().max() < 1e-9
    assert not out["xp_goals"].equals(ref["xp_goals"])
    other = frame.assign(position_id=3)
    candidate.fit(history)
    champion.fit(history)
    assert candidate.predict(other, horizon=1)["xp_goals"].to_numpy() == pytest.approx(
        champion.predict(other, horizon=1)["xp_goals"].to_numpy())
