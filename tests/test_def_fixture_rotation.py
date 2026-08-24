"""
Unit tests for 5-DEF fixture rotation analysis (GW1-19).
Verifies combinatorial coverage, structural archetypes, metric invariants, and companion CSV integrity.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

RESEARCH_DIR = Path("docs/research/def-fdr-rotation-gw1-19")
sys.path.insert(0, str(RESEARCH_DIR.resolve()))

from club_occupancy import OCCUPANCY_COLUMNS, build_club_occupancy_table

OCCUPANCY_CSV = RESEARCH_DIR / "def_rotation_club_occupancy.csv"
ALLOWED_SHAPES = {"3-2", "3-1-1", "2-2-1", "2-1-1-1", "1-1-1-1-1"}
DISTINCT_CLUB_COUNTS = {2: 380, 3: 6840, 4: 19380, 5: 15504}


@pytest.fixture(scope="module")
def starting_defs_df():
    csv_path = RESEARCH_DIR / "starting_defs_gw1_19.csv"
    assert csv_path.exists(), f"Missing companion artifact: {csv_path}"
    return pd.read_csv(csv_path)


@pytest.fixture(scope="module")
def def_summary_df():
    csv_path = RESEARCH_DIR / "def_rotation_5sets_summary.csv"
    assert csv_path.exists(), f"Missing companion artifact: {csv_path}"
    return pd.read_csv(csv_path)


@pytest.fixture(scope="module")
def def_schedule_df():
    csv_path = RESEARCH_DIR / "gw1_19_def_rotation_schedule_picks.csv"
    assert csv_path.exists(), f"Missing companion artifact: {csv_path}"
    return pd.read_csv(csv_path)


def test_starting_defs_baseline_coverage(starting_defs_df):
    """Verifies all 20 Premier League clubs have a designated starting DEF."""
    assert len(starting_defs_df) == 20
    assert "club_short" in starting_defs_df.columns
    assert "player_name" in starting_defs_df.columns
    assert "cost" in starting_defs_df.columns
    assert "total_mod_fdr" in starting_defs_df.columns
    assert (starting_defs_df["cost"] >= 4.0).all()
    assert (starting_defs_df["cost"] <= 6.0).all()


def test_def_summary_combinatorics_and_archetypes(def_summary_df):
    """Verifies all 42,104 valid multisets are evaluated and classified into valid archetypes."""
    assert len(def_summary_df) == 42104
    archetypes = set(def_summary_df["archetype"].unique())
    expected_archetypes = {"Pure Budget", "1-Premium Anchor", "2-Premium Anchor", "Other"}
    assert archetypes == expected_archetypes

    # Invariants on FDR
    assert (def_summary_df["total_mod_fdr"] >= 135.0).all()
    assert (def_summary_df["total_mod_fdr"] <= 170.0).all()
    assert (def_summary_df["avg_def_mod_fdr"] >= 2.30).all()
    assert (def_summary_df["avg_def_mod_fdr"] <= 3.00).all()

    # Minimum lineup FDR check
    min_fdr = def_summary_df["total_mod_fdr"].min()
    assert min_fdr == pytest.approx(135.75, abs=0.01)


def test_pure_budget_archetype_constraints(def_summary_df):
    """Verifies Pure Budget sets contain 5 defenders at or below £4.5m."""
    budget_sets = def_summary_df[def_summary_df["archetype"] == "Pure Budget"]
    assert len(budget_sets) > 0
    assert (budget_sets["combined_cost"] >= 20.0).all()
    assert (budget_sets["combined_cost"] <= 22.5).all()

    # Best budget set should achieve total mod FDR <= 140.0
    best_budget = budget_sets.sort_values("total_mod_fdr").iloc[0]
    assert best_budget["total_mod_fdr"] <= 140.0


def test_anchor_archetype_constraints(def_summary_df):
    """Verifies 1-Premium and 2-Premium sets have expected cost ranges and improvements."""
    anchor1_sets = def_summary_df[def_summary_df["archetype"] == "1-Premium Anchor"]
    anchor2_sets = def_summary_df[def_summary_df["archetype"] == "2-Premium Anchor"]

    assert len(anchor1_sets) > 0
    assert len(anchor2_sets) > 0

    best_anchor1 = anchor1_sets.sort_values("total_mod_fdr").iloc[0]
    best_anchor2 = anchor2_sets.sort_values("total_mod_fdr").iloc[0]

    assert best_anchor1["total_mod_fdr"] <= 138.0
    assert best_anchor2["total_mod_fdr"] <= 137.0


def test_schedule_picks_integrity(def_schedule_df):
    """Verifies schedule picks companion CSV contains 19 gameweeks per tracked set."""
    labels = def_schedule_df["set_label"].unique()
    assert len(labels) == 6
    assert len(def_schedule_df) == 6 * 19

    for label in labels:
        subset = def_schedule_df[def_schedule_df["set_label"] == label]
        assert len(subset) == 19
        assert sorted(subset["gameweek"].tolist()) == list(range(1, 20))
        assert (subset["lineup_mod_fdr_sum"] >= 5.0).all()
        assert (subset["lineup_mod_fdr_sum"] <= 15.0).all()


def test_club_occupancy_table_ranks_fdr_ties_by_occupancy_key() -> None:
    """Ordinal rank is (total_mod_fdr, occupancy_key); file order is occupancy_key."""
    table = build_club_occupancy_table(
        club_shorts_per_set=(
            ("BOU", "AVL", "AVL", "CHE", "CHE"),
            ("AVL", "AVL", "AVL", "BOU", "CHE"),
            ("CHE", "AVL", "BOU", "BOU", "CHE"),
        ),
        total_mod_fdr=(10.0, 9.0, 10.0),
        total_base_fdr=(11.0, 10.0, 11.0),
    )
    assert list(table["occupancy_key"]) == [
        "AVL-AVL-AVL-BOU-CHE",
        "AVL-AVL-BOU-CHE-CHE",
        "AVL-BOU-BOU-CHE-CHE",
    ]
    assert list(table["club_1"]) == ["AVL", "AVL", "AVL"]
    assert list(table["club_5"]) == ["CHE", "CHE", "CHE"]
    assert list(table["occupancy_shape"]) == ["3-1-1", "2-2-1", "2-2-1"]
    assert list(table["distinct_clubs"]) == [3, 3, 3]
    rank_by_key = dict(zip(table["occupancy_key"], table["rank_mod_fdr"], strict=True))
    assert rank_by_key["AVL-AVL-AVL-BOU-CHE"] == 1
    assert rank_by_key["AVL-AVL-BOU-CHE-CHE"] == 2
    assert rank_by_key["AVL-BOU-BOU-CHE-CHE"] == 3
    assert table["avg_def_mod_fdr"].iloc[0] == pytest.approx(9.0 / 57.0, abs=1e-3)


def test_club_occupancy_csv_is_unique_alpha_source_of_truth() -> None:
    """Companion is one row per Club Occupancy, sorted by occupancy_key, with club_1–club_5."""
    assert OCCUPANCY_CSV.exists(), f"Missing companion artifact: {OCCUPANCY_CSV}"
    occupancy = pd.read_csv(OCCUPANCY_CSV)
    assert list(occupancy.columns) == list(OCCUPANCY_COLUMNS)
    assert len(occupancy) == 42104
    assert occupancy["occupancy_key"].is_unique
    assert occupancy["occupancy_key"].is_monotonic_increasing
    assert occupancy["rank_mod_fdr"].is_unique
    assert set(occupancy["rank_mod_fdr"]) == set(range(1, 42105))
    assert set(occupancy["occupancy_shape"]).issubset(ALLOWED_SHAPES)
    assert set(occupancy["distinct_clubs"]) == {2, 3, 4, 5}
    rebuilt_key = occupancy[["club_1", "club_2", "club_3", "club_4", "club_5"]].agg(
        "-".join, axis=1
    )
    assert (rebuilt_key == occupancy["occupancy_key"]).all()
    for distinct, expected_n in DISTINCT_CLUB_COUNTS.items():
        assert int((occupancy["distinct_clubs"] == distinct).sum()) == expected_n
    rank1 = occupancy.loc[occupancy["rank_mod_fdr"] == 1].iloc[0]
    assert rank1["occupancy_key"] == "AVL-CHE-COV-LIV-MCI"
    assert rank1["total_mod_fdr"] == pytest.approx(135.75, abs=0.01)
    assert rank1["distinct_clubs"] == 5
    assert rank1["occupancy_shape"] == "1-1-1-1-1"
