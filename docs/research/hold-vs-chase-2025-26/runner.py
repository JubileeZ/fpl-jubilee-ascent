"""Hold-vs-chase evidence: fixture signal, persistence, and haul concentration.

Recomputes the 2025-26 archive panel behind the hold-vs-chase note and writes
hold_chase_summary.csv (metric, pool, value, n). Fast (~15 s).
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

TOPIC = Path(__file__).resolve().parent
DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "archive" / "2025-26" / "processed"
POS = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}


def main() -> int:
    perf = pd.read_parquet(DATA_DIR / "player_performances.parquet")
    fix = pd.read_parquet(DATA_DIR / "fixtures.parquet")[
        ["id", "team_h_difficulty", "team_a_difficulty"]
    ]
    pos = pd.read_parquet(DATA_DIR / "players.parquet")[
        ["id", "position_id"]
    ].rename(columns={"id": "player_id"})
    g = perf.merge(fix, left_on="fixture_id", right_on="id", how="left")
    g["difficulty"] = np.where(
        g["was_home"], g["team_h_difficulty"], g["team_a_difficulty"]
    )
    pg = g.groupby(["player_id", "gameweek_id"], as_index=False).agg(
        points=("total_points", "sum"),
        minutes=("minutes", "sum"),
        cs=("clean_sheets", "max"),
        difficulty=("difficulty", "mean"),
    )
    pg = pg.merge(pos, on="player_id", how="left")
    pg["pos"] = pg["position_id"].map(POS)

    rows: list[dict[str, object]] = []

    def add(metric: str, pool: str, value: float, n: int) -> None:
        rows.append({"metric": metric, "pool": pool,
                     "value": round(float(value), 4), "n": int(n)})

    add("corr_difficulty_points", "all",
        pg[["difficulty", "points"]].corr().iloc[0, 1], len(pg))
    for pid, name in POS.items():
        s = pg[pg["position_id"] == pid]
        add("corr_difficulty_points", name,
            s[["difficulty", "points"]].corr().iloc[0, 1], len(s))
    d = pg[pg["position_id"].isin([1, 2])]
    add("corr_difficulty_cs", "DEF_GKP",
        d[["difficulty", "cs"]].corr().iloc[0, 1], len(d))

    pg2 = pg.sort_values(["player_id", "gameweek_id"])
    pg2["prev_pts"] = pg2.groupby("player_id")["points"].shift(1)
    pg2["prev_min"] = pg2.groupby("player_id")["minutes"].shift(1)
    q = pg2[(pg2["minutes"] > 0) & (pg2["prev_min"] > 0)]
    add("autocorr_points", "all",
        q[["prev_pts", "points"]].corr().iloc[0, 1], len(q))
    for name in ("DEF", "MID", "FWD"):
        s = q[q["pos"] == name]
        add("autocorr_points", name,
            s[["prev_pts", "points"]].corr().iloc[0, 1], len(s))

    apps = pg[pg["minutes"] > 0].groupby("player_id").size()
    core = apps[apps >= 25].index
    conc = pg[pg["player_id"].isin(core)].groupby("player_id")["points"].apply(
        lambda s: s.nlargest(3).sum() / s.sum()
    )
    add("haul_top3_median", "apps25", float(conc.median()), len(conc))
    add("haul_top3_mean", "apps25", float(conc.mean()), len(conc))

    mf = pg[pg["pos"].isin(["MID", "FWD"]) & (pg["minutes"] >= 60)]
    for pool, m in (("easy_le2", mf[mf["difficulty"] <= 2]),
                    ("mid3", mf[mf["difficulty"] == 3]),
                    ("hard_ge4", mf[mf["difficulty"] >= 4])):
        add("hitrate_pts_ge6", pool, float((m["points"] >= 6).mean()), len(m))
        add("mean_points", pool, float(m["points"].mean()), len(m))
    dg = pg[pg["pos"].isin(["DEF", "GKP"]) & (pg["minutes"] >= 60)]
    for pool, m in (("easy_le2", dg[dg["difficulty"] <= 2]),
                    ("mid3", dg[dg["difficulty"] == 3]),
                    ("hard_ge4", dg[dg["difficulty"] >= 4])):
        add("cs_rate", pool, float(m["cs"].mean()), len(m))

    pg3 = pg.sort_values(["player_id", "gameweek_id"])
    pg3["started"] = (pg3["minutes"] >= 60).astype(int)
    pg3["prev_started"] = pg3.groupby("player_id")["started"].shift(1)
    q3 = pg3[pg3["prev_started"].notna()]
    add("p_start_given_started", "all",
        float(q3[q3["prev_started"] == 1]["started"].mean()), len(q3))
    add("p_start_given_not", "all",
        float(q3[q3["prev_started"] == 0]["started"].mean()), len(q3))
    starts = pg3.groupby("player_id")["started"].sum()
    add("count_nailed_30", "all", float((starts >= 30).sum()), pg3["player_id"].nunique())
    add("count_rotator_10_29", "all",
        float(((starts >= 10) & (starts < 30)).sum()), pg3["player_id"].nunique())
    add("count_fringe_lt10", "all", float((starts < 10).sum()), pg3["player_id"].nunique())
    add("core_absence_rate", "nailed30",
        float(1 - pg3[pg3["player_id"].isin(starts[starts >= 30].index)]["started"].mean()),
        int(starts[starts >= 30].sum()))

    out = TOPIC / "hold_chase_summary.csv"
    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["metric", "pool", "value", "n"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {out} ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
