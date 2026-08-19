"""Defensive Composite Score (DCS) rotation runner and live CSV headlines."""

from __future__ import annotations

import importlib.util
from collections import Counter
from pathlib import Path
from types import ModuleType

import numpy as np
import pandas as pd
import pytest


def _load_mod() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "defensive_rotation",
        "docs/research/defensive-fixture-rotation/run_defensive_rotation_analysis.py",
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def dcs_mod() -> ModuleType:
    return _load_mod()


def test_dcs_weights_score_and_risk(dcs_mod: ModuleType) -> None:
    dcs_score_only, oc_hi, risk_zero = dcs_mod.compute_two_factor_dcs(
        rot_xp_per_gw=8.0,
        total_price=8.5,
        floor_price=8.5,
        rot_avg_fdr=3.5,
        no_diff_pct=0.0,
        fdr_corr=1.0,
        min_xp_bound=5.0,
        max_xp_bound=8.0,
        gamma=0.2944,
    )
    assert oc_hi == 8.0
    assert risk_zero == 0.0
    assert dcs_score_only == 60.0

    dcs_risk_only, oc_lo, risk_full = dcs_mod.compute_two_factor_dcs(
        rot_xp_per_gw=5.0,
        total_price=8.5,
        floor_price=8.5,
        rot_avg_fdr=2.0,
        no_diff_pct=100.0,
        fdr_corr=-1.0,
        min_xp_bound=5.0,
        max_xp_bound=8.0,
        gamma=0.2944,
    )
    assert oc_lo == 5.0
    assert risk_full == 100.0
    assert dcs_risk_only == 40.0


def test_dcs_perfect_and_floor_bounds(dcs_mod: ModuleType) -> None:
    dcs_max, oc_max, s_risk_max = dcs_mod.compute_two_factor_dcs(
        rot_xp_per_gw=8.0,
        total_price=8.5,
        floor_price=8.5,
        rot_avg_fdr=2.0,
        no_diff_pct=100.0,
        fdr_corr=-1.0,
        min_xp_bound=5.0,
        max_xp_bound=8.0,
        gamma=0.2944,
    )
    assert oc_max == 8.0
    assert s_risk_max == 100.0
    assert dcs_max == 100.0

    dcs_min, oc_min, s_risk_min = dcs_mod.compute_two_factor_dcs(
        rot_xp_per_gw=5.0,
        total_price=8.5,
        floor_price=8.5,
        rot_avg_fdr=3.5,
        no_diff_pct=0.0,
        fdr_corr=1.0,
        min_xp_bound=5.0,
        max_xp_bound=8.0,
        gamma=0.2944,
    )
    assert oc_min == 5.0
    assert s_risk_min == 0.0
    assert dcs_min == 0.0


def test_oc_score_applies_gamma_above_floor(dcs_mod: ModuleType) -> None:
    _, oc, _ = dcs_mod.compute_two_factor_dcs(
        rot_xp_per_gw=6.69,
        total_price=10.0,
        floor_price=8.5,
        rot_avg_fdr=2.42,
        no_diff_pct=100.0,
        fdr_corr=-0.07,
        min_xp_bound=5.0,
        max_xp_bound=7.0,
        gamma=0.2944,
    )
    assert oc == pytest.approx(6.69 - 0.2944 * 1.5, abs=1e-3)


def test_precompute_pairwise_corr_diagonal_is_one(dcs_mod: ModuleType) -> None:
    dummy_fdr = np.array([[2.0, 3.0, 4.0], [3.0, 2.0, 4.0]], dtype=float)
    corr_mat = dcs_mod.precompute_pairwise_corr(dummy_fdr)
    assert corr_mat[0, 0] == 1.0
    assert corr_mat[1, 1] == 1.0


def test_promoted_clubs_are_cov_hul_ips(dcs_mod: ModuleType) -> None:
    assert dcs_mod.PROMOTED_CLUBS == frozenset({"COV", "HUL", "IPS"})


def test_valid_def_multisets_cap_two_per_club(dcs_mod: ModuleType) -> None:
    idx_to_short = {i: f"C{i:02d}" for i in range(20)}
    combos, _patterns, uniques, names = dcs_mod.generate_valid_def_club_multisets(idx_to_short)
    assert len(combos) == len(names) == len(uniques)
    assert len(combos) > 10_000
    for row in combos:
        assert max(Counter(row.tolist()).values()) <= dcs_mod.MAX_DEF_PER_CLUB
    assert set(uniques) == {3, 4, 5}


def test_live_gkp_strategy_csv_dcs_columns() -> None:
    path = Path("data/research/defensive-fixture-rotation/gkp_strategy_comparison.csv")
    df = pd.read_csv(path)
    assert {"dcs", "oc_score", "tot_rot_xp", "horizon"}.issubset(df.columns)
    assert "rqi" not in df.columns
    gw119 = df[df["horizon"] == "gw1_19"].sort_values("dcs", ascending=False)
    assert len(gw119) >= 1
    top = gw119.iloc[0]
    assert 0.0 <= float(top["dcs"]) <= 100.0
    assert float(top["tot_rot_xp"]) > 0.0


def test_live_club_fdr_min_csv() -> None:
    path = Path("data/research/defensive-fixture-rotation/def_club_partitions_matrix.csv")
    if not path.exists():
        pytest.skip("partitions CSV not on disk")
    part = pd.read_csv(path)
    five = part[(part["horizon"] == "gw1_19") & (part["num_unique_clubs"] == 5)]
    top = five.sort_values("rot_avg_fdr").iloc[0]
    assert isinstance(top["clubs"], str) and "-" in str(top["clubs"])
    assert 1.2 <= float(top["rot_avg_fdr"]) <= 5.4


def test_live_backline_and_tier_artifacts_exist() -> None:
    base = Path("data/research/defensive-fixture-rotation")
    for name in (
        "gkp_strategy_comparison.csv",
        "gkp_rotation_matrix.csv",
        "def_tier_player_rotations.csv",
        "def_bb1_wc4_club_matrix.csv",
        "backline_bb1_wc4_lineups.csv",
        "backline_gw4_19_lineups.csv",
        "backline_gw1_19_lineups.csv",
        "gkp_performance_baseline.csv",
        "def_performance_baseline.csv",
    ):
        assert (base / name).exists(), name
    tiers = pd.read_csv(base / "def_tier_player_rotations.csv")
    assert "dcs" in tiers.columns
    assert "oc_score" in tiers.columns
    back = pd.read_csv(base / "backline_gw1_19_lineups.csv")
    assert "dcs" in back.columns
