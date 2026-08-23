"""
Unit tests for 5-DEF fixture rotation analysis (GW1-19).
Verifies combinatorial coverage, structural archetypes, metric invariants, and companion CSV integrity.
"""

from pathlib import Path
import pandas as pd
import pytest

RESEARCH_DIR = Path("docs/research/def-fdr-rotation-gw1-19")


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
