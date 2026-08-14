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


def test_club_slot_hamming(rotation_mod: ModuleType) -> None:
    assert rotation_mod.club_slot_hamming("LIV-MCI-NFO-SUN-SUN", "AVL-CHE-LIV-MCI-NFO") == 2
    assert rotation_mod.club_slot_hamming("AVL-CHE-LIV-MCI-SUN", "AVL-CHE-LIV-MCI-NFO") == 1
    assert rotation_mod.club_slot_hamming("ARS-MUN-MUN-NFO-SUN", "AVL-CHE-LIV-MCI-NFO") == 4


def test_club_5way_sort_is_correlation_first(rotation_mod: ModuleType) -> None:
    frame = pd.DataFrame(
        [
            {"horizon": "gw4_19", "clubs": "HIGH-CORR", "rot_avg_fdr": 2.4375, "no_diff_pct": 100.0, "avg_fdr_corr": -0.05, "all_easy_pct": 25.0},
            {"horizon": "gw4_19", "clubs": "BEST-CORR", "rot_avg_fdr": 2.4375, "no_diff_pct": 100.0, "avg_fdr_corr": -0.10, "all_easy_pct": 18.0},
            {"horizon": "gw4_19", "clubs": "WORSE-FDR", "rot_avg_fdr": 2.4583, "no_diff_pct": 100.0, "avg_fdr_corr": -0.20, "all_easy_pct": 30.0},
        ]
    )
    sorted_frame, _ = rotation_mod.apply_ranking_sorts(
        frame,
        pd.DataFrame(
            [{"effective_avg_fdr": 2.27, "gw1_avg_fdr": 2.0, "gw2_3_rot_fdr": 2.5, "avg_fdr_corr": 0.4, "clubs": "A"}]
        ),
    )
    assert list(sorted_frame["clubs"]) == ["BEST-CORR", "HIGH-CORR", "WORSE-FDR"]


def test_bridge_dest_prefers_more_negative_corr(rotation_mod: ModuleType) -> None:
    easy_worse_corr = rotation_mod.bridge_destination_key(
        post_no_diff_pct=100.0, path_fdr=2.4237, post_rot_fdr=2.4375,
        post_corr=-0.0529, post_easy_pct=25.0, gw1_avg_fdr=2.4, n_swaps=2,
        pre_eff_fdr=2.3636, post_j=0,
    )
    harder_better_corr = rotation_mod.bridge_destination_key(
        post_no_diff_pct=100.0, path_fdr=2.4237, post_rot_fdr=2.4375,
        post_corr=-0.0994, post_easy_pct=18.8, gw1_avg_fdr=2.4, n_swaps=2,
        pre_eff_fdr=2.3636, post_j=1,
    )
    assert harder_better_corr < easy_worse_corr


def test_path_effective_fdr_weights(rotation_mod: ModuleType) -> None:
    # 11 GW1-3 starts vs 48 GW4-19 starts
    assert rotation_mod.path_effective_fdr(2.3636, 2.4375) == pytest.approx(
        (11 * 2.3636 + 48 * 2.4375) / 59.0
    )


def test_def_rotation_artifacts_exist() -> None:
    base_dir = Path("data/research/def-fixture-rotation")
    club_csv = base_dir / "def_club_5way_rotation_matrix.csv"
    tier_csv = base_dir / "def_tier_player_rotations.csv"
    bb_club_csv = base_dir / "def_bb1_wc4_club_matrix.csv"
    bb_tier_csv = base_dir / "def_bb1_wc4_tier_lineups.csv"
    bb2_club_csv = base_dir / "def_bb2_wc4_club_matrix.csv"
    bb2_tier_csv = base_dir / "def_bb2_wc4_tier_lineups.csv"
    baseline_csv = base_dir / "def_performance_baseline.csv"
    sun_bridge_csv = base_dir / "def_wc4_sun_bridge_matrix.csv"

    overall_bridge_csv = base_dir / "def_wc4_overall_bridge_matrix.csv"

    assert club_csv.exists()
    assert tier_csv.exists()
    assert bb_club_csv.exists()
    assert bb_tier_csv.exists()
    assert bb2_club_csv.exists()
    assert bb2_tier_csv.exists()
    assert baseline_csv.exists()
    assert sun_bridge_csv.exists()
    assert overall_bridge_csv.exists()

    df_clubs = pd.read_csv(club_csv)
    df_tiers = pd.read_csv(tier_csv)
    df_bb_clubs = pd.read_csv(bb_club_csv)
    df_bb_tiers = pd.read_csv(bb_tier_csv)
    df_bb2_clubs = pd.read_csv(bb2_club_csv)
    df_bb2_tiers = pd.read_csv(bb2_tier_csv)
    df_base = pd.read_csv(baseline_csv)
    df_bridge = pd.read_csv(sun_bridge_csv)
    df_overall = pd.read_csv(overall_bridge_csv)

    assert set(df_clubs["horizon"].unique()) >= {"gw1_3", "gw4_19", "gw1_19", "full_season"}
    gw4_5 = df_clubs[(df_clubs["horizon"] == "gw4_19") & (df_clubs["num_unique_clubs"] == 5)].iloc[0]
    assert gw4_5["clubs"] == "AVL-BOU-CHE-LIV-NFO"
    assert gw4_5["avg_fdr_corr"] == pytest.approx(-0.0994, abs=1e-4)
    assert len(df_clubs) == 41344 * 4
    assert set(df_clubs["num_unique_clubs"].unique()) == {2, 3, 4, 5}
    assert len(df_tiers) > 0
    assert len(df_bb_clubs) > 1000
    assert set(df_bb_clubs["num_unique_clubs"].unique()) == {2, 3, 4, 5}
    assert len(df_bb_tiers) > 100
    assert len(df_bb2_clubs) > 1000
    assert set(df_bb2_clubs["num_unique_clubs"].unique()) == {2, 3, 4, 5}
    assert len(df_bb2_tiers) > 100
    assert (df_bb2_clubs["gw2_max_fdr"] <= 3.0).all()
    assert len(df_base) >= 50
    assert (df_base["expected_role"].isin(["Nailed Starter", "Regular Starter"])).all()
    assert (df_bb_clubs["gw1_max_fdr"] <= 3.0).all()
    assert len(df_bridge) > 100
    assert df_bridge["pre_sun"].isin([1, 2]).all()
    assert df_bridge["n_swaps"].isin([1, 2]).all()
    assert df_bridge["pre_unique"].isin([4, 5]).all()
    top = df_bridge[df_bridge["scenario_rank"] == 1].iloc[0]
    assert top["gw419_rot_fdr"] == pytest.approx(2.4375)
    assert int(top["n_swaps"]) == 2
    assert "SUN" in str(top["out_clubs"])
    assert len(df_overall) > len(df_bridge)
    assert df_overall["n_swaps"].isin([1, 2]).all()
    assert df_overall["pre_unique"].isin([4, 5]).all()
    overall_top = df_overall[df_overall["scenario_rank"] == 1].iloc[0]
    assert overall_top["gw419_rot_fdr"] == pytest.approx(2.4375)
    assert int(overall_top["pre_sun"]) == 0
    assert Path("docs/research/def-fixture-rotation/wc4-sun-bridge.md").exists()
    assert Path("docs/research/def-fixture-rotation/wc4-overall-bridge.md").exists()
