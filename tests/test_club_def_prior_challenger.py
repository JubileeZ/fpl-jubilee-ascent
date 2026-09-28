import pandas as pd
import pytest

from models import get_model, list_model_names
from models.club_def_prior_challenger import ClubDefPriorChallengerModel, attach_club, club_def_ratio
from models.learned_start_challenger import LearnedStartChallengerModel
from tests.test_learned_start_challenger import _features, _start_history


def test_catalog_discovers_club_def_prior_challenger() -> None:
    assert "club_def_prior_challenger" in list_model_names()
    assert get_model("club_def_prior_challenger").name == "club_def_prior_challenger"


def test_attach_club_takes_other_side_of_fixture() -> None:
    hist = pd.DataFrame({"fixture_id": [1, 1], "was_home": [True, False], "opponent_club_id": [20, 10]})
    assert attach_club(hist)["club"].tolist() == [10, 20]


def test_ratio_lifts_defenders_of_high_xg_club_only() -> None:
    rows = []
    for gw in range(1, 11):
        for player, club, opp, home, pos_xg in ((1, 10, 20, True, 0.3), (2, 20, 10, False, 0.05), (3, 10, 20, True, 0.2)):
            rows.append({"player_id": player, "gameweek_id": gw, "minutes": 90.0, "expected_goals": pos_xg,
                         "fixture_id": gw, "was_home": home, "opponent_club_id": opp})
    hist = attach_club(pd.DataFrame(rows))
    current = pd.DataFrame({"player_id": [1, 2, 3], "position_id": [2, 2, 3], "club_id": [10, 20, 10]})
    ratio = club_def_ratio(hist, current)
    assert ratio[1] > 1.0 > ratio[2]
    assert ratio[3] == pytest.approx(1.0)


def test_predict_reconciles_ledger() -> None:
    history, frame = _start_history(), _features(13).assign(position_id=2)
    model = ClubDefPriorChallengerModel()
    model.fit(history)
    out = model.predict(frame, horizon=1)
    components = [column for column in out.columns if column.startswith("xp_")]
    assert (out["projected_points"] - out[components].sum(axis=1)).abs().max() < 1e-9
    champion = LearnedStartChallengerModel()
    champion.fit(history)
    assert len(champion.predict(frame, horizon=1)) == len(out)
