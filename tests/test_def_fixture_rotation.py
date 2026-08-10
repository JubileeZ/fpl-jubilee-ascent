"""Tests for 5-DEF fixture rotation and diversification research."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pandas as pd
import pytest


def _load_mod() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "def_rotation",
        "docs/research/def-fixture-rotation/run_def_rotation_analysis.py",
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def rotation_mod() -> ModuleType:
    return _load_mod()


def test_def_rqi_scoring_bounds(rotation_mod: ModuleType) -> None:
    # High quality: 16.5 xP/GW, 2.0 avg FDR, 100% no-diff, -1.0 corr, £20.0m price
    rqi_max = rotation_mod.compute_def_rqi(
        tot_rot_xp=16.5 * 19,
        num_gws=19,
        rot_avg_fdr=2.0,
        no_diff_pct=100.0,
        fdr_corr=-1.0,
        total_price=20.0,
    )
    assert rqi_max == 100.0

    # Low quality: 9.0 xP/GW, 3.5 avg FDR, 0% no-diff, +1.0 corr, £28.0m price
    rqi_min = rotation_mod.compute_def_rqi(
        tot_rot_xp=9.0 * 19,
        num_gws=19,
        rot_avg_fdr=3.5,
        no_diff_pct=0.0,
        fdr_corr=1.0,
        total_price=28.0,
    )
    assert rqi_min == 0.0


def test_bb_rqi_scoring_bounds(rotation_mod: ModuleType) -> None:
    # Max quality: 60.0 xP across 11 starts, 2.0 GW1 FDR, 2.0 GW2-3 FDR, 2.0 eff FDR, -1.0 corr, £20.0m price
    bb_rqi_max = rotation_mod.compute_bb_rqi(
        tot_effective_xp=60.0,
        gw1_avg_fdr=2.0,
        gw2_3_rot_fdr=2.0,
        effective_avg_fdr=2.0,
        avg_corr=-1.0,
        total_price=20.0,
    )
    assert bb_rqi_max == 100.0

    # Min quality: 38.0 xP, 3.5 GW1 FDR, 3.5 GW2-3 FDR, 3.5 eff FDR, +1.0 corr, £28.0m price
    bb_rqi_min = rotation_mod.compute_bb_rqi(
        tot_effective_xp=38.0,
        gw1_avg_fdr=3.5,
        gw2_3_rot_fdr=3.5,
        effective_avg_fdr=3.5,
        avg_corr=1.0,
        total_price=28.0,
    )
    assert bb_rqi_min == 0.0


def test_def_rotation_artifacts_exist() -> None:
    base_dir = Path("data/research/def-fixture-rotation")
    club_csv = base_dir / "def_club_5way_rotation_matrix.csv"
    tier_csv = base_dir / "def_tier_player_rotations.csv"
    bb_club_csv = base_dir / "def_bb1_wc4_club_matrix.csv"
    bb_tier_csv = base_dir / "def_bb1_wc4_tier_lineups.csv"
    baseline_csv = base_dir / "def_performance_baseline.csv"

    assert club_csv.exists()
    assert tier_csv.exists()
    assert bb_club_csv.exists()
    assert bb_tier_csv.exists()
    assert baseline_csv.exists()

    df_clubs = pd.read_csv(club_csv)
    df_tiers = pd.read_csv(tier_csv)
    df_bb_clubs = pd.read_csv(bb_club_csv)
    df_bb_tiers = pd.read_csv(bb_tier_csv)
    df_base = pd.read_csv(baseline_csv)

    assert set(df_clubs["horizon"].unique()) >= {"gw1_3", "gw4_19", "gw1_19", "full_season"}
    assert len(df_clubs) == 15504 * 4
    assert len(df_tiers) > 0
    assert len(df_bb_clubs) > 1000
    assert len(df_bb_tiers) > 100
    assert len(df_base) >= 50
    assert (df_base["expected_role"].isin(["Nailed Starter", "Regular Starter"])).all()
    assert (df_bb_clubs["gw1_max_fdr"] <= 3.0).all()
