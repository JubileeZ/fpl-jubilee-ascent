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


def test_def_rotation_artifacts_exist() -> None:
    base_dir = Path("data/research/def-fixture-rotation")
    club_csv = base_dir / "def_club_5way_rotation_matrix.csv"
    tier_csv = base_dir / "def_tier_player_rotations.csv"
    baseline_csv = base_dir / "def_performance_baseline.csv"

    assert club_csv.exists()
    assert tier_csv.exists()
    assert baseline_csv.exists()

    df_clubs = pd.read_csv(club_csv)
    df_tiers = pd.read_csv(tier_csv)
    df_base = pd.read_csv(baseline_csv)

    assert set(df_clubs["horizon"].unique()) >= {"gw1_3", "gw4_19", "gw1_19", "full_season"}
    assert len(df_clubs) == 15504 * 4
    assert len(df_tiers) > 0
    assert len(df_base) >= 50
    assert (df_base["expected_role"].isin(["Nailed Starter", "Regular Starter"])).all()
