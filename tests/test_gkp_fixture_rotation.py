"""GKP fixture rotation: FDR-min pick, horizon-matched xP, RQI."""

from __future__ import annotations

import importlib.util
from types import ModuleType

import numpy as np
import pandas as pd


def _load_mod() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "gkp_rotation",
        "docs/research/gkp-fixture-rotation/run_gkp_rotation_analysis.py",
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


mod = _load_mod()


def test_fdr_min_pick_prefers_easier_fixture() -> None:
    # GKP1 harder (FDR 4) but higher xP; GKP2 easier (FDR 2)
    assert mod.pick_rotated_xp(xp1=5.0, xp2=3.0, fdr1=4.0, fdr2=2.0) == 3.0


def test_fdr_min_tie_prefers_home() -> None:
    assert mod.pick_rotated_xp(xp1=4.0, xp2=5.0, fdr1=3.0, fdr2=3.0, home1=True, home2=False) == 4.0
    assert mod.pick_rotated_xp(xp1=4.0, xp2=5.0, fdr1=3.0, fdr2=3.0, home1=False, home2=True) == 5.0


def test_horizon_rotation_sums_match_window_length() -> None:
    xp1 = np.array([4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 3.0, 3.0], dtype=float)
    xp2 = np.array([2.0, 2.0, 5.0, 5.0, 2.0, 2.0, 4.0, 4.0], dtype=float)
    fdr1 = np.array([2.0, 2.0, 4.0, 4.0, 2.0, 2.0, 5.0, 5.0], dtype=float)
    fdr2 = np.array([4.0, 4.0, 2.0, 2.0, 4.0, 4.0, 2.0, 2.0], dtype=float)
    home1 = np.array([True] * 8)
    home2 = np.array([False] * 8)

    short = mod.summarize_rotation(xp1[:6], xp2[:6], fdr1[:6], fdr2[:6], home1[:6], home2[:6])
    full = mod.summarize_rotation(xp1, xp2, fdr1, fdr2, home1, home2)

    assert short["num_gws"] == 6
    assert full["num_gws"] == 8
    # FDR-min: weeks 1-2 g1, 3-4 g2, 5-6 g1, 7-8 g2 → 4+4+5+5+4+4+4+4 = 34
    assert full["tot_rot_xp"] == 34.0
    assert short["tot_rot_xp"] == 26.0
    assert full["tot_rot_xp"] != short["tot_rot_xp"]
    # max(xP): 4,4,5,5,4,4,4,4 = 34
    assert full["tot_rot_xp_maxxp"] == 34.0


def test_rqi_uses_per_gw_rotated_xp() -> None:
    # Same per-GW quality → same RQI regardless of horizon length scaling of totals
    rqi_6 = mod.compute_rqi(
        tot_rot_xp=24.0,
        num_gws=6,
        rot_avg_fdr=2.5,
        fdr_corr=-0.5,
        easy_gw_pct=50.0,
        total_price=9.5,
    )
    rqi_38 = mod.compute_rqi(
        tot_rot_xp=24.0 * (38 / 6),
        num_gws=38,
        rot_avg_fdr=2.5,
        fdr_corr=-0.5,
        easy_gw_pct=50.0,
        total_price=9.5,
    )
    assert rqi_6 == rqi_38


def test_promoted_clubs_are_cov_hul_ips() -> None:
    assert mod.PROMOTED_CLUBS == frozenset({"COV", "HUL", "IPS"})


def test_run_analysis_full_season_xp_not_gw1_6_capped() -> None:
    df: pd.DataFrame = mod.run_analysis()
    assert set(df["horizon"].unique()) >= {"gw1_6", "gw1_10", "gw1_19", "full_season"}
    required = {
        "tot_rot_xp",
        "tot_rot_xp_maxxp",
        "xp_gain_vs_best_single",
        "fdr_corr",
        "rotated_avg_fdr",
        "easy_gws",
        "rqi",
        "per90_saves1",
        "per90_goals_conceded1",
        "per90_saves2",
        "per90_goals_conceded2",
    }
    assert required.issubset(df.columns)
    assert "tot_rot_xp_gw1_6" not in df.columns

    g6 = df[df["horizon"] == "gw1_6"]
    fs = df[df["horizon"] == "full_season"]
    merged = fs.merge(
        g6[["club1", "gkp1", "club2", "gkp2", "tot_rot_xp"]],
        on=["club1", "gkp1", "club2", "gkp2"],
        suffixes=("_fs", "_g6"),
    )
    assert len(merged) > 0
    # Season total must exceed the 6-GW window for at least some pairs
    assert (merged["tot_rot_xp_fs"] > merged["tot_rot_xp_g6"]).any()
    assert (fs["end_gw"] == 38).all()
    assert (g6["end_gw"] == 6).all()


def test_baseline_table_uses_expected_stats_rates() -> None:
    base: pd.DataFrame = mod.build_performance_baseline()
    assert "per90_saves" in base.columns
    assert "per90_goals_conceded" in base.columns
    assert "cs_per_90" not in base.columns
    assert "xgc_per_90" not in base.columns
    assert (base["expected_role"].isin(["Nailed Starter", "Regular Starter"])).all()
    assert len(base) >= 10
