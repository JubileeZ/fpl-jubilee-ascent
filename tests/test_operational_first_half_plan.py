"""Operational First-Half Plan CSVs: frozen 15s, no greedy FTs."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

OUT = Path("data/research/gw1-19-operational-plan")
FH_SQUADS = Path("data/research/gw1-19-first-half-chip-path/first_half_squads.csv")
SUMMARY = OUT / "operational_summary.csv"
SELECT = OUT / "operational_select_11.csv"
SQUADS = OUT / "operational_squads.csv"
WEEKS = OUT / "operational_weeks.csv"
HURDLES = OUT / "operational_ft_hurdles.csv"


@pytest.fixture()
def summary() -> pd.DataFrame:
    if not SUMMARY.exists():
        pytest.skip("operational summary CSV not on disk")
    return pd.read_csv(SUMMARY)


@pytest.fixture()
def select11() -> pd.DataFrame:
    if not SELECT.exists():
        pytest.skip("operational select-11 CSV not on disk")
    return pd.read_csv(SELECT)


@pytest.fixture()
def squads() -> pd.DataFrame:
    if not SQUADS.exists():
        pytest.skip("operational squads CSV not on disk")
    return pd.read_csv(SQUADS)


def test_summary_identity_and_chips(summary: pd.DataFrame) -> None:
    assert len(summary) == 1
    row = summary.iloc[0]
    assert row["plan_id"] == "OP1"
    assert int(row["bb"]) == 1
    assert int(row["wc"]) == 4
    assert int(row["fh"]) == 12
    assert int(row["tc"]) == 17
    assert str(row["ft_engine"]) == "bank_state_hurdle"
    assert str(row["fh_15_status"]) == "rebuild_at_deadline"
    assert str(row["follows_greedy_ft_csv"]).lower() in {"false", "0"}


def test_pre_wc_and_rebuild_match_first_half_wc4(squads: pd.DataFrame) -> None:
    if not FH_SQUADS.exists():
        pytest.skip("first-half squads CSV not on disk")
    fh = pd.read_csv(FH_SQUADS)
    wc4 = fh[fh["wc"] == 4]
    pre = set(int(x) for x in squads.loc[squads["plan_phase"] == "pre-WC", "player_id"])
    post = set(int(x) for x in squads.loc[squads["plan_phase"] == "WC rebuild", "player_id"])
    fh_pre = set(int(x) for x in wc4.loc[wc4["phase"] == "pre-WC", "player_id"])
    fh_post = set(int(x) for x in wc4.loc[wc4["phase"] == "WC rebuild", "player_id"])
    assert pre == fh_pre
    assert post == fh_post
    assert len(pre) == 15
    assert len(post) == 15


def test_frozen_xi_has_no_greedy_tavernier_after_wc(select11: pd.DataFrame) -> None:
    gw6 = select11[select11["gw"] == 6]
    names = set(gw6["web_name"])
    assert "Sarr" in names
    assert "Tavernier" not in names
    gw15 = select11[select11["gw"] == 15]
    assert str(gw15["captain"].iloc[0]) == "Tzolis"


def test_select_11_bounds_and_week_sum(select11: pd.DataFrame, summary: pd.DataFrame) -> None:
    counts = select11.groupby("gw").size()
    assert int(counts.loc[1]) == 15
    for gw in range(2, 20):
        assert int(counts.loc[gw]) == 11
        g = select11[select11["gw"] == gw]
        assert int((g["position"] == "GKP").sum()) == 1
        n_def = int((g["position"] == "DEF").sum())
        n_mid = int((g["position"] == "MID").sum())
        n_fwd = int((g["position"] == "FWD").sum())
        assert 3 <= n_def <= 5
        assert 2 <= n_mid <= 5
        assert 1 <= n_fwd <= 3
        assert n_def + n_mid + n_fwd == 10
    weeks = select11.groupby("gw")["week_xp"].first()
    assert float(weeks.sum()) == pytest.approx(float(summary.loc[0, "frozen_19gw_xi_xp"]))


def test_hurdle_table_present() -> None:
    if not HURDLES.exists():
        pytest.skip("operational FT hurdle CSV not on disk")
    h = pd.read_csv(HURDLES)
    assert set(h["fts_at_deadline"].astype(int)) >= {0, 1, 2, 3, 4, 5}
    nth = pd.to_numeric(h["nth_at_five"], errors="coerce")
    cap = h[(h["fts_at_deadline"] == 5) & (nth == 1)]
    assert float(cap["hurdle_xp"].iloc[0]) == pytest.approx(0.2)
    if not WEEKS.exists():
        pytest.skip("operational weeks CSV not on disk")
    w = pd.read_csv(WEEKS)
    assert int(w.loc[w["gw"] == 12, "gw"].iloc[0]) == 12
    assert str(w.loc[w["gw"] == 12, "fh_15_status"].iloc[0]) == "rebuild_at_deadline"
