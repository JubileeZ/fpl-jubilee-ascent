"""Export Canonical GW1–6 select-11 plan from published starter flags."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
SIM = ROOT / "docs/archive/gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/gw1-6_wc4_simulation.csv"
SUMMARY = ROOT / "docs/archive/gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/gw1-6_wc4_summary.csv"
OUT = ROOT / "docs/archive/gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/gw1-6_select_11.csv"
POS_ORDER = {"GKP": 0, "DEF": 1, "MID": 2, "FWD": 3}


def _truthy(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().isin(["true", "1"])


def export_select_11() -> pd.DataFrame:
    sim = pd.read_csv(SIM)
    summary = pd.read_csv(SUMMARY).iloc[0]
    chips = {1: "BB", 2: "", 3: "", 4: "WC", 5: "", 6: ""}
    rows: list[dict] = []
    for gw in range(1, 7):
        flag = f"is_starter_gw{gw}"
        xp_col = f"gw{gw}_xp"
        starters = sim[_truthy(sim[flag])].copy()
        starters["_pos"] = starters["position"].map(POS_ORDER)
        starters = starters.sort_values(["_pos", xp_col], ascending=[True, False])
        cap_name = str(summary[f"gw{gw}_captain"])
        n_def = int((starters["position"] == "DEF").sum())
        n_mid = int((starters["position"] == "MID").sum())
        n_fwd = int((starters["position"] == "FWD").sum())
        formation = "BB-15" if gw == 1 else f"{n_def}-{n_mid}-{n_fwd}"
        xi_xp = float(starters[xp_col].sum())
        cap_xp = float(starters.loc[starters["web_name"] == cap_name, xp_col].iloc[0])
        week_xp = xi_xp + cap_xp
        bench = sim[(sim["phase"] == starters["phase"].iloc[0]) & ~_truthy(sim[flag])]
        bench_names = ", ".join(bench.sort_values(["position", "web_name"])["web_name"].tolist())
        for _, r in starters.iterrows():
            rows.append({
                "gw": gw,
                "chip": chips[gw],
                "formation": formation,
                "captain": cap_name,
                "player_id": int(r["player_id"]),
                "web_name": r["web_name"],
                "club_short": r["club_short"],
                "position": r["position"],
                "cost": float(r["cost"]),
                "xp": round(float(r[xp_col]), 2),
                "is_captain": bool(r["web_name"] == cap_name),
                "xi_xp": round(xi_xp, 2),
                "week_xp": round(week_xp, 2),
                "published_week_xp": round(float(summary[f"gw{gw}_xp"]), 2),
                "bench": bench_names,
            })
    out = pd.DataFrame(rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT, index=False)
    return out


if __name__ == "__main__":
    df = export_select_11()
    print(df.groupby("gw")["web_name"].count().to_string())
    print(f"Wrote {OUT}")
