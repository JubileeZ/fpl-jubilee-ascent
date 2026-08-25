"""Tests for 2025-26 First-Half Club Occupancy diagnostic."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

RESEARCH_DIR = Path("docs/research/tp-walkforward-gw1-19-2025-26")
sys.path.insert(0, str(RESEARCH_DIR.resolve()))

from occupancy import first_half_occupancy_table, valid_occupancy_indices


def test_valid_occupancy_rejects_four_of_one_club() -> None:
    combos = valid_occupancy_indices(2)
    assert combos
    assert all(max(combo.count(i) for i in set(combo)) <= 3 for combo in combos)


def test_occupancy_table_ranks_easier_backline_first() -> None:
    clubs = pd.DataFrame([
        {"id": 1, "short_name": "AAA"},
        {"id": 2, "short_name": "BBB"},
    ])
    rows = []
    for gw in range(1, 20):
        rows.append({
            "gameweek_id": gw,
            "home_club_id": 1,
            "away_club_id": 2,
            "team_h_difficulty": 2,
            "team_a_difficulty": 5,
        })
    fixtures = pd.DataFrame(rows)
    table = first_half_occupancy_table(clubs, fixtures)
    easiest = table.sort_values("rank_mod_fdr").iloc[0]
    assert easiest["occupancy_key"].count("AAA") >= easiest["occupancy_key"].count("BBB")


def test_committed_2025_26_occupancy_companion_matches_five_slot_combinatorics() -> None:
    path = RESEARCH_DIR / "def_rotation_club_occupancy.csv"
    table = pd.read_csv(path)
    assert len(table) == 42104
    assert table["rank_mod_fdr"].min() == 1
    assert table["rank_mod_fdr"].max() == 42104
