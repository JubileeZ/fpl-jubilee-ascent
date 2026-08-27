import pandas as pd

from features.builder import _fixture_maps
from features.fdr import modified_fdr, official_fdr


def test_official_fdr_parses_and_rejects_missing() -> None:
    assert official_fdr(4) == 4.0
    assert official_fdr("5") == 5.0
    assert official_fdr(None) is None
    assert official_fdr(float("nan")) is None


def test_modified_fdr_home_away_and_missing() -> None:
    assert modified_fdr(4.0, True) == 3.75
    assert modified_fdr(5.0, False) == 5.25
    assert modified_fdr(2.0, True) == 1.75
    assert modified_fdr(None, True) == 3.0
    assert modified_fdr(None, False) == 3.0


def test_fixture_maps_use_modified_fdr_when_strength_zero() -> None:
    clubs = pd.DataFrame([
        {
            "id": 1,
            "strength": None,
            "strength_attack_home": 0,
            "strength_defence_home": 0,
            "strength_attack_away": 0,
            "strength_defence_away": 0,
        },
        {
            "id": 2,
            "strength": None,
            "strength_attack_home": 0,
            "strength_defence_home": 0,
            "strength_attack_away": 0,
            "strength_defence_away": 0,
        },
    ])
    fixtures = pd.DataFrame([
        {
            "id": 10,
            "gameweek_id": 2,
            "home_club_id": 1,
            "away_club_id": 2,
            "team_h_difficulty": 4,
            "team_a_difficulty": 5,
        },
    ])
    maps = _fixture_maps(fixtures, clubs, [2]).set_index("club_id")
    home = maps.loc[1]
    away = maps.loc[2]
    assert home["difficulty"] == 3.75
    assert away["difficulty"] == 5.25
    assert home["attack_multiplier"] == (6.0 - 3.75) / 3.0
    assert away["defence_multiplier"] == 5.25 / 3.0


def test_fixture_maps_missing_official_stays_unmodified_default() -> None:
    clubs = pd.DataFrame([
        {"id": 1, "strength": None, "strength_attack_home": 0, "strength_defence_home": 0},
        {"id": 2, "strength": None, "strength_attack_away": 0, "strength_defence_away": 0},
    ])
    fixtures = pd.DataFrame([
        {
            "id": 10,
            "gameweek_id": 2,
            "home_club_id": 1,
            "away_club_id": 2,
            "team_h_difficulty": None,
            "team_a_difficulty": None,
        },
    ])
    maps = _fixture_maps(fixtures, clubs, [2]).set_index("club_id")
    assert maps.loc[1, "difficulty"] == 3.0
    assert maps.loc[2, "difficulty"] == 3.0
