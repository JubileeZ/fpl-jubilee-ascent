"""Premier League-arrival npxG/xAG before/after from FBref Big 5 dump + Understat.

Writes companions beside this runner. Scratch downloads under .tmp/agent/.
Requires: uv run --with pyreadr python docs/research/epl-arrival-xg-xa-adjustment/runner.py
"""

from __future__ import annotations

import urllib.request
from pathlib import Path

import pandas as pd

try:
    import pyreadr
except ImportError as exc:  # pragma: no cover
    raise SystemExit("pyreadr required: uv run --with pyreadr python .../runner.py") from exc

OUTPUT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = OUTPUT_DIR.parents[2]
TMP_DIR = PROJECT_ROOT / ".tmp" / "agent" / "epl-arrival"

WFR_STANDARD_URL = (
    "https://github.com/JaseZiv/worldfootballR_data/releases/download/"
    "fb_big5_advanced_season_stats/big5_player_standard.rds"
)
UNDERSTAT_ROSTER_URL = (
    "https://github.com/peteowen1/pannadata/releases/download/"
    "understat-latest/understat_roster.parquet"
)
UNDERSTAT_SHOTS_URL = (
    "https://github.com/peteowen1/pannadata/releases/download/"
    "understat-latest/understat_shots.parquet"
)

PL = "Premier League"
NON_PL_BIG5 = ("La Liga", "Bundesliga", "Serie A", "Ligue 1")
FLOOR_PRIMARY = 900
FLOOR_SENS = 450
PRIOR_PL_MAX = 90
XG_SEASON_END_MIN = 2018
PL_ARRIVAL_END_MAX = 2025
WFR_DUMP_UPDATED = "2025-09-18T17:39:48Z"
UNDERSTAT_DUMP_UPDATED = "2026-04-18T08:01:47Z"

BIG6 = frozenset(
    {
        "Arsenal",
        "Chelsea",
        "Liverpool",
        "Manchester City",
        "Manchester Utd",
        "Tottenham",
    }
)
UST_LEAGUE = {
    "ENG": "Premier League",
    "ESP": "La Liga",
    "GER": "Bundesliga",
    "ITA": "Serie A",
    "FRA": "Ligue 1",
    "RUS": "Russian Premier League",
}


def _download(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    req = urllib.request.Request(url, headers={"User-Agent": "FPL-Jubilee-Ascent-research"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        dest.write_bytes(resp.read())
    return dest


def _season_label(end_year: int) -> str:
    return f"{end_year - 1}-{str(end_year)[2:]}"


def _fbref_id(url: str) -> str:
    parts = str(url).rstrip("/").split("/")
    return parts[-2] if len(parts) >= 2 else ""


def _p90(total: float, minutes: float) -> float:
    if minutes is None or minutes <= 0 or pd.isna(total) or pd.isna(minutes):
        return float("nan")
    return 90.0 * float(total) / float(minutes)


def _ratio(pl: float, prior: float) -> float:
    if pd.isna(pl) or pd.isna(prior) or prior <= 0:
        return float("nan")
    return float(pl) / float(prior)


def load_fbref_standard() -> pd.DataFrame:
    path = _download(WFR_STANDARD_URL, TMP_DIR / "big5_player_standard.rds")
    return pyreadr.read_r(str(path))[None]


def fbref_quality(raw: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    n = len(raw)
    rows.append({"check": "raw_rows", "value": n, "handling": "header/sample inspected before aggregates"})
    rows.append({"check": "columns", "value": len(raw.columns), "handling": "npxG_Expected / xAG_Expected / Min_Playing / Url / Comp"})
    rows.append(
        {
            "check": "comps",
            "value": ",".join(sorted(raw["Comp"].dropna().unique().astype(str))),
            "handling": "Big 5 only; Championship/Eredivisie/Primeira absent",
        }
    )
    rows.append({"check": "dup_url_season_squad", "value": int(raw.duplicated(["Url", "Season_End_Year", "Squad"]).sum()), "handling": "expect 0"})
    rows.append(
        {
            "check": "dup_url_season_comp",
            "value": int(raw.duplicated(["Url", "Season_End_Year", "Comp"]).sum()),
            "handling": "same-league mid-season club change; sum minutes/xG/xAG",
        }
    )
    rows.append({"check": "null_minutes", "value": int(raw["Min_Playing"].isna().sum()), "handling": "drop"})
    xg_era = raw.loc[raw["Season_End_Year"] >= XG_SEASON_END_MIN]
    rows.append({"check": "npxg_null_xg_era", "value": int(xg_era["npxG_Expected"].isna().sum()), "handling": "drop player-comp-season if npxG or xAG null"})
    rows.append({"check": "xag_null_xg_era", "value": int(xg_era["xAG_Expected"].isna().sum()), "handling": "same"})
    y26 = raw.loc[raw["Season_End_Year"] == 2026, "Min_Playing"]
    rows.append(
        {
            "check": "season_2026_median_minutes",
            "value": None if y26.empty else float(y26.median()),
            "handling": "incomplete 2025-26 in dump; exclude as arrival and as prior",
        }
    )
    rows.append({"check": "gk_exact_pos", "value": int((raw["Pos"] == "GK").sum()), "handling": "exclude Pos==GK from arrival cohort"})
    return pd.DataFrame(rows)


def aggregate_fbref_player_comp(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    df = df.loc[df["Season_End_Year"].between(XG_SEASON_END_MIN, PL_ARRIVAL_END_MAX)]
    df = df.loc[df["Min_Playing"].notna() & (df["Min_Playing"] > 0)]
    df = df.loc[df["npxG_Expected"].notna() & df["xAG_Expected"].notna()]
    df["is_gk"] = df["Pos"].fillna("") == "GK"
    g = (
        df.groupby(["Url", "Season_End_Year", "Comp"], as_index=False)
        .agg(
            player=("Player", "first"),
            pos=("Pos", "first"),
            age=("Age", "first"),
            squads=("Squad", lambda s: "|".join(sorted({str(x) for x in s}))),
            minutes=("Min_Playing", "sum"),
            npxg=("npxG_Expected", "sum"),
            xag=("xAG_Expected", "sum"),
            xg=("xG_Expected", "sum"),
            pkatt=("PKatt", "sum"),
            pk=("PK", "sum"),
        )
    )
    gk_min = (
        df.loc[df["is_gk"]]
        .groupby(["Url", "Season_End_Year", "Comp"], as_index=False)["Min_Playing"]
        .sum()
        .rename(columns={"Min_Playing": "gk_minutes"})
    )
    g = g.merge(gk_min, on=["Url", "Season_End_Year", "Comp"], how="left")
    g["gk_minutes"] = g["gk_minutes"].fillna(0.0)
    g["npxg_p90"] = [_p90(n, m) for n, m in zip(g["npxg"], g["minutes"], strict=True)]
    g["xag_p90"] = [_p90(a, m) for a, m in zip(g["xag"], g["minutes"], strict=True)]
    g["npxg_xag_p90"] = g["npxg_p90"] + g["xag_p90"]
    g["age_num"] = pd.to_numeric(g["age"], errors="coerce")
    g["fbref_id"] = g["Url"].map(_fbref_id)
    return g


def _prior_non_pl(block: pd.DataFrame) -> pd.Series | None:
    non = block.loc[block["Comp"] != PL]
    if non.empty:
        return None
    return non.sort_values("minutes", ascending=False).iloc[0]


def build_fbref_transitions(agg: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for url, grp in agg.groupby("Url", sort=False):
        by_season = {int(y): g for y, g in grp.groupby("Season_End_Year")}
        years = sorted(by_season)
        for y in years:
            block = by_season[y]
            pl_y = block.loc[block["Comp"] == PL]
            pl_min_y = float(pl_y["minutes"].sum()) if not pl_y.empty else 0.0
            prior_row = _prior_non_pl(block)
            if prior_row is not None and pl_min_y > 0:
                prev = by_season.get(y - 1)
                prev_pl = 0.0 if prev is None else float(prev.loc[prev["Comp"] == PL, "minutes"].sum())
                if prev_pl >= PRIOR_PL_MAX:
                    continue
                rows.append(
                    _transition_row(
                        prior_row,
                        pl_y.sort_values("minutes", ascending=False).iloc[0],
                        pl_min_y,
                        window="january",
                        prior_pl_minutes=prev_pl,
                        same_season=True,
                    )
                )
        for y in years:
            y2 = y + 1
            if y2 not in by_season:
                continue
            prior_block = by_season[y]
            next_block = by_season[y2]
            pl_prior = float(prior_block.loc[prior_block["Comp"] == PL, "minutes"].sum())
            if pl_prior >= PRIOR_PL_MAX:
                continue
            prior_row = _prior_non_pl(prior_block)
            pl_next = next_block.loc[next_block["Comp"] == PL]
            if prior_row is None or pl_next.empty:
                continue
            pl_min = float(pl_next["minutes"].sum())
            pl_rep = pl_next.sort_values("minutes", ascending=False).iloc[0]
            rows.append(
                _transition_row(
                    prior_row,
                    pl_rep,
                    pl_min,
                    window="summer",
                    prior_pl_minutes=pl_prior,
                    same_season=False,
                )
            )
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    out["meets_900"] = (out["prior_minutes"] >= FLOOR_PRIMARY) & (out["pl_minutes"] >= FLOOR_PRIMARY)
    out["meets_450"] = (out["prior_minutes"] >= FLOOR_SENS) & (out["pl_minutes"] >= FLOOR_SENS)
    out["source"] = "fbref_wfr_standard"
    return out


def _transition_row(
    prior: pd.Series,
    pl: pd.Series,
    pl_minutes: float,
    *,
    window: str,
    prior_pl_minutes: float,
    same_season: bool,
) -> dict[str, object]:
    prior_npxg90 = _p90(prior["npxg"], prior["minutes"])
    prior_xag90 = _p90(prior["xag"], prior["minutes"])
    pl_npxg = float(pl["npxg"]) if "npxg" in pl.index else float("nan")
    pl_xag = float(pl["xag"]) if "xag" in pl.index else float("nan")
    if window == "january":
        pl_npxg90 = _p90(pl_npxg, pl_minutes)
        pl_xag90 = _p90(pl_xag, pl_minutes)
        pl_squads = str(pl["squads"])
        pl_end = int(pl["Season_End_Year"])
        prior_end = pl_end
    else:
        pl_npxg90 = _p90(pl_npxg, pl_minutes)
        pl_xag90 = _p90(pl_xag, pl_minutes)
        pl_squads = str(pl["squads"])
        pl_end = int(pl["Season_End_Year"])
        prior_end = int(prior["Season_End_Year"])
    dest_squads = set(str(pl_squads).split("|"))
    return {
        "player": prior["player"],
        "fbref_url": prior["Url"] if "Url" in prior.index else pl.get("Url"),
        "fbref_id": prior["fbref_id"],
        "window": window,
        "prior_season_end_year": prior_end if same_season else int(prior["Season_End_Year"]),
        "pl_season_end_year": pl_end,
        "prior_season": _season_label(prior_end if same_season else int(prior["Season_End_Year"])),
        "pl_season": _season_label(pl_end),
        "prior_league": prior["Comp"],
        "prior_squads": prior["squads"],
        "pl_squads": pl_squads,
        "pos": pl["pos"],
        "age_pl": pl["age_num"],
        "prior_minutes": float(prior["minutes"]),
        "pl_minutes": float(pl_minutes),
        "prior_pl_minutes": float(prior_pl_minutes),
        "prior_npxg": float(prior["npxg"]),
        "pl_npxg": pl_npxg,
        "prior_xag": float(prior["xag"]),
        "pl_xag": pl_xag,
        "prior_npxg_p90": prior_npxg90,
        "pl_npxg_p90": pl_npxg90,
        "prior_xag_p90": prior_xag90,
        "pl_xag_p90": pl_xag90,
        "prior_npxg_xag_p90": prior_npxg90 + prior_xag90,
        "ratio_npxg": _ratio(pl_npxg90, prior_npxg90),
        "ratio_xag": _ratio(pl_xag90, prior_xag90),
        "diff_npxg": pl_npxg90 - prior_npxg90,
        "diff_xag": pl_xag90 - prior_xag90,
        "prior_pkatt": float(prior["pkatt"]) if pd.notna(prior["pkatt"]) else 0.0,
        "pl_pkatt": float(pl["pkatt"]) if pd.notna(pl["pkatt"]) else 0.0,
        "minutes_ratio": float(pl_minutes) / float(prior["minutes"]) if prior["minutes"] else float("nan"),
        "dest_big6": int(bool(dest_squads & BIG6)),
        "gk_prior": int(float(prior["gk_minutes"]) >= 0.5 * float(prior["minutes"])),
        "gk_pl": int(str(pl["pos"]) == "GK"),
    }


def assign_talent(df: pd.DataFrame, mask: pd.Series) -> tuple[pd.DataFrame, dict[str, object]]:
    """Top / average / bottom from prior npxG+xAG/90 quartiles inside each source league."""
    out = df.copy()
    out["talent_split"] = ""
    out["talent_league_n"] = pd.Series(pd.NA, index=out.index, dtype="Int64")
    out["talent_league_p25"] = pd.Series(pd.NA, index=out.index, dtype="Float64")
    out["talent_league_p75"] = pd.Series(pd.NA, index=out.index, dtype="Float64")
    cohort = out.loc[mask]
    cuts: list[dict[str, object]] = []
    for league, sub in cohort.groupby("prior_league", sort=False):
        n = int(len(sub))
        rates = sub["prior_npxg_xag_p90"]
        p25 = float(rates.quantile(0.25))
        p75 = float(rates.quantile(0.75))
        cuts.append({"prior_league": str(league), "n": n, "p25_npxg_xag_p90": p25, "p75_npxg_xag_p90": p75})
        top = rates >= p75
        average = (rates >= p25) & (rates < p75)
        bottom = ~(top | average)
        idx = sub.index
        out.loc[idx, "talent_league_n"] = n
        out.loc[idx, "talent_league_p25"] = p25
        out.loc[idx, "talent_league_p75"] = p75
        out.loc[idx[top.to_numpy()], "talent_split"] = "top"
        out.loc[idx[average.to_numpy()], "talent_split"] = "average"
        out.loc[idx[bottom.to_numpy()], "talent_split"] = "bottom"
    meta: dict[str, object] = {
        "talent_rule": "within_source_league_quartile_summer_900",
        "n_talent_cohort": int(len(cohort)),
        "league_cuts": cuts,
    }
    return out, meta


def load_understat() -> tuple[pd.DataFrame, pd.DataFrame]:
    roster = pd.read_parquet(_download(UNDERSTAT_ROSTER_URL, TMP_DIR / "understat_roster.parquet"))
    shots = pd.read_parquet(_download(UNDERSTAT_SHOTS_URL, TMP_DIR / "understat_shots.parquet"))
    return roster, shots


def aggregate_understat(roster: pd.DataFrame, shots: pd.DataFrame) -> pd.DataFrame:
    r = roster.copy()
    r["minutes"] = pd.to_numeric(r["time"], errors="coerce")
    r["xg"] = pd.to_numeric(r["x_g"], errors="coerce")
    r["xa"] = pd.to_numeric(r["x_a"], errors="coerce")
    r["season_end"] = pd.to_numeric(r["season_input"], errors="coerce") + 1
    r["player_id"] = r["player_id"].astype(str)
    r = r.loc[r["season_end"].between(XG_SEASON_END_MIN, PL_ARRIVAL_END_MAX)]
    r = r.loc[r["minutes"].notna() & (r["minutes"] > 0)]
    r["league"] = r["league_code"].map(UST_LEAGUE)
    r = r.loc[r["league"].notna()]
    gk = (
        r.loc[r["position"] == "GK"]
        .groupby(["player_id", "season_end", "league"], as_index=False)["minutes"]
        .sum()
        .rename(columns={"minutes": "gk_minutes"})
    )
    agg = r.groupby(["player_id", "season_end", "league"], as_index=False).agg(
        player=("player", "first"),
        minutes=("minutes", "sum"),
        xg=("xg", "sum"),
        xa=("xa", "sum"),
        teams=("h_a", "count"),
    )
    team_names = (
        r.assign(club=r["h_a"].map({"h": "home", "a": "away"}))
        .groupby(["player_id", "season_end", "league"], as_index=False)
        .size()
    )
    agg = agg.merge(gk, on=["player_id", "season_end", "league"], how="left")
    agg["gk_minutes"] = agg["gk_minutes"].fillna(0.0)

    s = shots.copy()
    s["xg"] = pd.to_numeric(s["x_g"], errors="coerce")
    s["season_end"] = pd.to_numeric(s["season_input"], errors="coerce") + 1
    s["player_id"] = s["player_id"].astype(str)
    s["league"] = s["league_code"].map(UST_LEAGUE)
    s = s.loc[s["season_end"].between(XG_SEASON_END_MIN, PL_ARRIVAL_END_MAX)]
    s = s.loc[s["league"].notna() & s["xg"].notna()]
    npxg = (
        s.loc[s["situation"] != "Penalty"]
        .groupby(["player_id", "season_end", "league"], as_index=False)["xg"]
        .sum()
        .rename(columns={"xg": "npxg"})
    )
    agg = agg.merge(npxg, on=["player_id", "season_end", "league"], how="left")
    agg["npxg"] = agg["npxg"].fillna(0.0)
    agg["npxg_p90"] = [_p90(n, m) for n, m in zip(agg["npxg"], agg["minutes"], strict=True)]
    agg["xa_p90"] = [_p90(a, m) for a, m in zip(agg["xa"], agg["minutes"], strict=True)]
    agg["npxg_xa_p90"] = agg["npxg_p90"] + agg["xa_p90"]
    _ = team_names
    return agg


def build_understat_transitions(agg: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for pid, grp in agg.groupby("player_id", sort=False):
        by_season = {int(y): g for y, g in grp.groupby("season_end")}
        years = sorted(by_season)
        for y in years:
            y2 = y + 1
            if y2 not in by_season:
                continue
            prior_block = by_season[y]
            next_block = by_season[y2]
            pl_prior = float(prior_block.loc[prior_block["league"] == PL, "minutes"].sum())
            if pl_prior >= PRIOR_PL_MAX:
                continue
            non = prior_block.loc[prior_block["league"] != PL]
            pl_next = next_block.loc[next_block["league"] == PL]
            if non.empty or pl_next.empty:
                continue
            prior = non.sort_values("minutes", ascending=False).iloc[0]
            pl = pl_next.sort_values("minutes", ascending=False).iloc[0]
            if float(prior["gk_minutes"]) >= 0.5 * float(prior["minutes"]):
                continue
            if float(pl["gk_minutes"]) >= 0.5 * float(pl["minutes"]):
                continue
            prior_npxg90 = float(prior["npxg_p90"])
            prior_xa90 = float(prior["xa_p90"])
            pl_npxg90 = float(pl["npxg_p90"])
            pl_xa90 = float(pl["xa_p90"])
            rows.append(
                {
                    "player": prior["player"],
                    "understat_player_id": pid,
                    "window": "summer",
                    "prior_season_end_year": int(prior["season_end"]),
                    "pl_season_end_year": int(pl["season_end"]),
                    "prior_season": _season_label(int(prior["season_end"])),
                    "pl_season": _season_label(int(pl["season_end"])),
                    "prior_league": prior["league"],
                    "prior_minutes": float(prior["minutes"]),
                    "pl_minutes": float(pl["minutes"]),
                    "prior_npxg": float(prior["npxg"]),
                    "pl_npxg": float(pl["npxg"]),
                    "prior_xa": float(prior["xa"]),
                    "pl_xa": float(pl["xa"]),
                    "prior_npxg_p90": prior_npxg90,
                    "pl_npxg_p90": pl_npxg90,
                    "prior_xa_p90": prior_xa90,
                    "pl_xa_p90": pl_xa90,
                    "prior_npxg_xa_p90": prior_npxg90 + prior_xa90,
                    "ratio_npxg": _ratio(pl_npxg90, prior_npxg90),
                    "ratio_xa": _ratio(pl_xa90, prior_xa90),
                    "diff_npxg": pl_npxg90 - prior_npxg90,
                    "diff_xa": pl_xa90 - prior_xa90,
                    "source": "understat_roster_shots",
                }
            )
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    out["meets_900"] = (out["prior_minutes"] >= FLOOR_PRIMARY) & (out["pl_minutes"] >= FLOOR_PRIMARY)
    out["meets_450"] = (out["prior_minutes"] >= FLOOR_SENS) & (out["pl_minutes"] >= FLOOR_SENS)
    return out


def _stat_block(sub: pd.DataFrame, ratio_col: str, diff_col: str, prefix: str) -> dict[str, object]:
    r = pd.to_numeric(sub[ratio_col], errors="coerce")
    d = pd.to_numeric(sub[diff_col], errors="coerce")
    r_ok = r.dropna()
    return {
        f"{prefix}_n": int(len(sub)),
        f"{prefix}_n_ratio": int(len(r_ok)),
        f"{prefix}_mean_ratio": None if r_ok.empty else float(r_ok.mean()),
        f"{prefix}_median_ratio": None if r_ok.empty else float(r_ok.median()),
        f"{prefix}_p25_ratio": None if r_ok.empty else float(r_ok.quantile(0.25)),
        f"{prefix}_p75_ratio": None if r_ok.empty else float(r_ok.quantile(0.75)),
        f"{prefix}_share_ratio_lt_1": None if r_ok.empty else float((r_ok < 1).mean()),
        f"{prefix}_mean_diff": None if d.dropna().empty else float(d.mean()),
        f"{prefix}_median_diff": None if d.dropna().empty else float(d.median()),
    }


def summarise_fbref(trans: pd.DataFrame, talent_meta: dict[str, object]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    def add(slice_name: str, sub: pd.DataFrame, **extra: object) -> None:
        row: dict[str, object] = {"slice": slice_name, "n": int(len(sub)), **extra}
        row.update(_stat_block(sub, "ratio_npxg", "diff_npxg", "npxg"))
        row.update(_stat_block(sub, "ratio_xag", "diff_xag", "xag"))
        if not sub.empty:
            row["mean_prior_npxg_p90"] = float(sub["prior_npxg_p90"].mean())
            row["mean_pl_npxg_p90"] = float(sub["pl_npxg_p90"].mean())
            row["mean_prior_xag_p90"] = float(sub["prior_xag_p90"].mean())
            row["mean_pl_xag_p90"] = float(sub["pl_xag_p90"].mean())
            row["median_minutes_ratio"] = float(sub["minutes_ratio"].median())
            row["share_dest_big6"] = float(sub["dest_big6"].mean())
        rows.append(row)

    summer900 = trans.loc[(trans["window"] == "summer") & trans["meets_900"] & (trans["gk_prior"] == 0) & (trans["gk_pl"] == 0)]
    summer450 = trans.loc[(trans["window"] == "summer") & trans["meets_450"] & (trans["gk_prior"] == 0) & (trans["gk_pl"] == 0)]
    jan900 = trans.loc[(trans["window"] == "january") & trans["meets_900"] & (trans["gk_prior"] == 0) & (trans["gk_pl"] == 0)]
    jan450 = trans.loc[(trans["window"] == "january") & trans["meets_450"] & (trans["gk_prior"] == 0) & (trans["gk_pl"] == 0)]
    add("pooled_summer_900", summer900, talent_rule=talent_meta.get("talent_rule", ""))
    add("pooled_summer_450", summer450)
    add("january_900", jan900)
    add("january_450", jan450)
    for split in ("top", "average", "bottom"):
        add(f"talent_{split}_summer_900", summer900.loc[summer900["talent_split"] == split])
    for league in NON_PL_BIG5:
        for split in ("top", "average", "bottom"):
            add(
                f"league_{league}_talent_{split}_summer_900",
                summer900.loc[(summer900["prior_league"] == league) & (summer900["talent_split"] == split)],
            )
    for league in NON_PL_BIG5:
        add(f"league_{league}_summer_900", summer900.loc[summer900["prior_league"] == league])
        add(f"league_{league}_summer_450", summer450.loc[summer450["prior_league"] == league])
    add("dest_big6_summer_900", summer900.loc[summer900["dest_big6"] == 1])
    add("dest_non_big6_summer_900", summer900.loc[summer900["dest_big6"] == 0])
    young = summer900.loc[summer900["age_pl"] <= 23]
    old = summer900.loc[summer900["age_pl"] >= 28]
    add("age_le23_summer_900", young)
    add("age_ge28_summer_900", old)
    collapse = summer900.loc[summer900["minutes_ratio"] < 0.5]
    add("minutes_collapse_lt_0.5_summer_900", collapse)
    return pd.DataFrame(rows)


def summarise_understat(trans: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    def add(slice_name: str, sub: pd.DataFrame) -> None:
        row: dict[str, object] = {"slice": slice_name, "n": int(len(sub))}
        row.update(_stat_block(sub, "ratio_npxg", "diff_npxg", "npxg"))
        row.update(_stat_block(sub, "ratio_xa", "diff_xa", "xa"))
        rows.append(row)

    s900 = trans.loc[trans["meets_900"]]
    s450 = trans.loc[trans["meets_450"]]
    add("pooled_summer_900", s900)
    add("pooled_summer_450", s450)
    for league in (*NON_PL_BIG5, "Russian Premier League"):
        add(f"league_{league}_summer_900", s900.loc[s900["prior_league"] == league])
    return pd.DataFrame(rows)


def main() -> None:
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    raw = load_fbref_standard()
    quality = fbref_quality(raw)
    agg = aggregate_fbref_player_comp(raw)
    trans = build_fbref_transitions(agg)
    trans = trans.loc[trans["prior_league"].isin(NON_PL_BIG5)]
    primary_mask = (
        (trans["window"] == "summer")
        & trans["meets_900"]
        & (trans["gk_prior"] == 0)
        & (trans["gk_pl"] == 0)
    )
    trans, talent_meta = assign_talent(trans, primary_mask)
    trans = trans.loc[(trans["gk_prior"] == 0) & (trans["gk_pl"] == 0)].copy()
    primary_mask = (trans["window"] == "summer") & trans["meets_900"]
    trans["in_primary"] = primary_mask.astype(int)
    summary = summarise_fbref(trans, talent_meta)

    roster, shots = load_understat()
    ust_agg = aggregate_understat(roster, shots)
    ust = build_understat_transitions(ust_agg)
    ust_summary = summarise_understat(ust)

    keep_cols = [
        "player",
        "fbref_id",
        "fbref_url",
        "window",
        "prior_season",
        "pl_season",
        "prior_league",
        "prior_squads",
        "pl_squads",
        "pos",
        "age_pl",
        "prior_minutes",
        "pl_minutes",
        "minutes_ratio",
        "prior_npxg",
        "pl_npxg",
        "prior_xag",
        "pl_xag",
        "prior_npxg_p90",
        "pl_npxg_p90",
        "prior_xag_p90",
        "pl_xag_p90",
        "prior_npxg_xag_p90",
        "ratio_npxg",
        "ratio_xag",
        "diff_npxg",
        "diff_xag",
        "prior_pkatt",
        "pl_pkatt",
        "dest_big6",
        "talent_split",
        "talent_league_n",
        "talent_league_p25",
        "talent_league_p75",
        "meets_900",
        "meets_450",
        "in_primary",
        "prior_pl_minutes",
        "source",
    ]
    trans[keep_cols].sort_values(["window", "pl_season", "player"]).to_csv(
        OUTPUT_DIR / "arrival_xg_xa_before_after.csv", index=False
    )
    summary.to_csv(OUTPUT_DIR / "arrival_xg_xa_summary.csv", index=False)
    quality.to_csv(OUTPUT_DIR / "data_quality.csv", index=False)
    pd.DataFrame(talent_meta.get("league_cuts", [])).to_csv(OUTPUT_DIR / "talent_league_cuts.csv", index=False)
    ust.sort_values(["pl_season", "player"]).to_csv(OUTPUT_DIR / "arrival_xg_xa_understat_before_after.csv", index=False)
    ust_summary.to_csv(OUTPUT_DIR / "arrival_xg_xa_understat_summary.csv", index=False)

    print(quality.to_string(index=False))
    print(summary.to_string(index=False))
    print("understat")
    print(ust_summary.to_string(index=False))
    print("talent_rule", talent_meta.get("talent_rule"), "n", talent_meta.get("n_talent_cohort"))
    print("primary_n", int(primary_mask.sum()), "ust_900", int(ust["meets_900"].sum()) if not ust.empty else 0)


if __name__ == "__main__":
    main()
