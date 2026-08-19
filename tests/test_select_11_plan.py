"""Select-11 plan CSVs match published starter flags and FPL formation bounds."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

CANON = Path("data/research/gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/gw1-6_select_11.csv")
DUAL = Path("data/research/gw1-19-first-half-chip-path/first_half_select_11.csv")


def test_canonical_select_11_counts_and_xp() -> None:
    if not CANON.exists():
        pytest.skip("canonical select-11 CSV not on disk")
    df = pd.read_csv(CANON)
    counts = df.groupby("gw").size()
    assert int(counts.loc[1]) == 15
    for gw in range(2, 7):
        assert int(counts.loc[gw]) == 11
    week = df.groupby("gw").first()
    assert float(week.loc[1, "week_xp"]) == pytest.approx(float(week.loc[1, "published_week_xp"]))
    assert week.loc[1, "captain"]
    gw2 = df[df["gw"] == 2]
    assert set(gw2["position"]) == {"GKP", "DEF", "MID", "FWD"}
    assert int((gw2["position"] == "GKP").sum()) == 1
    assert int((gw2["position"] == "DEF").sum()) == 5


def test_dual_vector_wc4_select_11_bounds() -> None:
    if not DUAL.exists():
        pytest.skip("dual-vector select-11 CSV not on disk")
    df = pd.read_csv(DUAL)
    counts = df.groupby("gw").size()
    assert int(counts.loc[1]) == 15
    for gw in range(2, 20):
        assert int(counts.loc[gw]) == 11
        g = df[df["gw"] == gw]
        assert int((g["position"] == "GKP").sum()) == 1
        n_def = int((g["position"] == "DEF").sum())
        n_mid = int((g["position"] == "MID").sum())
        n_fwd = int((g["position"] == "FWD").sum())
        assert 3 <= n_def <= 5
        assert 2 <= n_mid <= 5
        assert 1 <= n_fwd <= 3
        assert n_def + n_mid + n_fwd == 10
    fh = df[df["gw"] == 12]
    assert "Raya" in set(fh["web_name"])
    assert fh["captain"].iloc[0] == "Isak"
