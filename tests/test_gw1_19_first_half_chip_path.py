"""Tests for Prior-Season Dual-Vector Seed and First-Half Chip Path helpers."""

from __future__ import annotations

import importlib.util

import pandas as pd


def _load(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


SEED = _load(
    "dv_seed_test",
    "docs/archive/gw1-19-first-half-chip-path/build_dual_vector_seed.py",
)
CHIPS = _load(
    "dv_chips_test",
    "docs/archive/gw1-19-first-half-chip-path/run_chip_path.py",
)


def test_club_xgc_is_one_team_value_not_sum_of_players() -> None:
    clubs = pd.DataFrame({"id": [1], "short_name": ["AAA"]})
    fixtures = pd.DataFrame({"id": [10], "home_club_id": [1], "away_club_id": [2]})
    rows = []
    for i in range(11):
        rows.append({
            "fixture_id": 10,
            "player_id": i,
            "was_home": True,
            "minutes": 90,
            "expected_goals": "0.10",
            "expected_goals_conceded": "1.70",
        })
    perf = pd.DataFrame(rows)
    rates = SEED._club_fixture_rates(perf, fixtures, clubs)
    assert len(rates) == 1
    assert abs(float(rates.iloc[0]["xg"]) - 1.1) < 1e-9
    assert abs(float(rates.iloc[0]["xgc"]) - 1.7) < 1e-9


def test_promoted_clubs_are_league_average() -> None:
    live = pd.DataFrame({"id": [7], "short_name": ["COV"]})
    seed = pd.DataFrame({
        "club_short": ["COV"],
        "strength_attack_home": [1.0],
        "strength_attack_away": [1.0],
        "strength_defence_home": [1.0],
        "strength_defence_away": [1.0],
    })
    patched = SEED.apply_seed_to_clubs(live, seed)
    assert float(patched.iloc[0]["strength_attack_home"]) == 1.0
    assert float(patched.iloc[0]["strength_defence_away"]) == 1.0


def test_pre_and_post_wc_skip_free_hit_week() -> None:
    assert CHIPS.pre_wc_gws(4, 2) == [1, 3]
    assert CHIPS.pre_wc_gws(3, 2) == [1]
    assert CHIPS.pre_wc_gws(4, 12) == [1, 2, 3]
    assert 12 not in CHIPS.post_wc_gws(4, 12)
    assert 4 in CHIPS.post_wc_gws(4, 12)
    assert 7 not in CHIPS.post_wc_gws(3, 7)
    assert 3 in CHIPS.post_wc_gws(3, 7)
