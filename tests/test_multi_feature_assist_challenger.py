import numpy as np
import pandas as pd
import pytest

from models import get_model, list_model_names
from models.face_value_challenger import FaceValueChallengerModel
from models.multi_feature_assist_challenger import (
    MultiFeatureAssistChallengerModel,
    _club_fixture_table,
    _poisson_ridge,
)


def _row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "player_id": 1,
        "position_id": 3,
        "club_id": 1,
        "opponent_id": 2,
        "is_home": True,
        "gameweek_id": 5,
        "fixture_id": 500,
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
        "per90_xg": 0.30,
        "per90_xa": 0.20,
        "per90_threat": 30.0,
        "per90_creativity": 30.0,
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
    }
    row.update(overrides)
    return row


def _history(n_gws: int = 4, players_per_club: int = 60) -> pd.DataFrame:
    """Two clubs (1 home vs 2) play each GW; club 1 creates far more xG than club 2."""
    rng = np.random.default_rng(0)
    rows: list[dict[str, object]] = []
    for gw in range(1, n_gws + 1):
        for club, opp, home, xg in ((1, 2, True, 0.06), (2, 1, False, 0.01)):
            for k in range(players_per_club):
                xa = float(rng.uniform(0.0, 0.1))
                rows.append({
                    "player_id": club * 1000 + k, "fixture_id": gw * 10, "gameweek_id": gw, "opponent_club_id": opp,
                    "was_home": home, "minutes": 90.0, "expected_goals": xg, "expected_assists": xa,
                    "creativity": 100.0 * xa, "goals_scored": 0.0, "threat": 0.0,
                })
    return pd.DataFrame(rows)


def test_catalog_discovers_multi_feature_assist_challenger() -> None:
    assert "multi_feature_assist_challenger" in list_model_names()
    assert get_model("multi_feature_assist_challenger").name == "multi_feature_assist_challenger"


def test_poisson_ridge_recovers_log_rate_slope() -> None:
    rng = np.random.default_rng(1)
    z = rng.normal(size=(5000, 1))
    y = rng.poisson(np.exp(0.2 + 0.5 * z[:, 0])).astype(float)
    beta = _poisson_ridge(z, y, np.zeros(len(y)), lam=1.0)
    assert beta == pytest.approx([0.2, 0.5], abs=0.05)


def test_club_fixture_table_assigns_club_as_other_side() -> None:
    table = _club_fixture_table(_history(n_gws=1))
    by_club = table.set_index("club")
    assert by_club.loc[1, "xg_for"] == pytest.approx(60 * 0.06)
    assert by_club.loc[1, "xg_against"] == pytest.approx(60 * 0.01)
    assert by_club.loc[2, "opp"] == 1


def test_cold_start_keeps_champion_projection() -> None:
    frame = pd.DataFrame([_row(gameweek_id=3)])
    history = _history(n_gws=2)
    champion, candidate = FaceValueChallengerModel(), MultiFeatureAssistChallengerModel()
    champion.fit(history)
    candidate.fit(history)
    pd.testing.assert_frame_equal(champion.predict(frame, horizon=1), candidate.predict(frame, horizon=1))


def test_glm_assists_replace_champion_and_reconcile_ledger() -> None:
    players = [_row(player_id=1000 + k, fixture_id=500) for k in range(3)]
    players += [_row(player_id=2000 + k, club_id=2, opponent_id=1, is_home=False, fixture_id=500) for k in range(3)]
    players.append(_row(player_id=2999, position_id=1, club_id=2, opponent_id=1, is_home=False, fixture_id=500))
    frame = pd.DataFrame(players)
    history = _history()
    champion, candidate = FaceValueChallengerModel(), MultiFeatureAssistChallengerModel()
    champion.fit(history)
    candidate.fit(history)
    base = champion.predict(frame, horizon=1).set_index("player_id")
    out = candidate.predict(frame, horizon=1).set_index("player_id")
    components = [column for column in out.columns if column.startswith("xp_")]
    assert (out["projected_points"] - out[components].sum(axis=1)).abs().max() < 1e-9
    assert (1000, 500) in candidate._assist_rates and (2999, 500) not in candidate._assist_rates
    assert out.loc[2999, "xp_assists"] == pytest.approx(base.loc[2999, "xp_assists"])
    assert not np.allclose(out.loc[1000, "xp_assists"], base.loc[1000, "xp_assists"])
    unchanged = [column for column in components if column not in ("xp_assists", "xp_bonus")]
    pd.testing.assert_frame_equal(out[unchanged], base[unchanged])
