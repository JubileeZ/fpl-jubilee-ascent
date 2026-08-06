"""Test suite for Expected Stats GW1–5 research note and projection engine."""

import importlib.util


def _import_from_path(module_name: str, file_path: str):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


build_mod = _import_from_path(
    "build_expected_stats",
    "docs/research/gw1-6-preseason-pipeline/02-expected-stats-gw1-5/build_expected_stats.py",
)
project_mod = _import_from_path(
    "project_expected_points",
    "docs/research/gw1-6-preseason-pipeline/02-expected-stats-gw1-5/project_expected_points.py",
)


def test_build_expected_stats_outputs():
    df_stats = build_mod.build_expected_stats()
    assert len(df_stats) == 340
    assert set(df_stats["expected_role"].unique()).issubset({"Nailed Starter", "Regular Starter", "Rotation", "Cameo"})
    assert "per90_xg" in df_stats.columns
    assert "per90_xa" in df_stats.columns
    assert "per90_defcon" in df_stats.columns
    assert (df_stats["per90_xg"] >= 0).all()


def test_project_gw1_5_points_outputs():
    df_proj = project_mod.project_gw1_5_points()
    assert len(df_proj) == 194
    assert "total_5gw_xp" in df_proj.columns
    assert "gw1_xp" in df_proj.columns
    assert "gw5_xp" in df_proj.columns

    # Verify Saliba is excluded across GW1-5
    saliba = df_proj[df_proj["web_name"] == "Saliba"]
    if len(saliba) > 0:
        assert saliba.iloc[0]["total_5gw_xp"] == 0.0

    # Verify J.Timber is excluded for GW1 but projects positive points across GW2-5
    timber = df_proj[df_proj["web_name"] == "J.Timber"]
    if len(timber) > 0:
        assert timber.iloc[0]["gw1_xp"] == 0.0
        assert timber.iloc[0]["total_5gw_xp"] > 0.0
