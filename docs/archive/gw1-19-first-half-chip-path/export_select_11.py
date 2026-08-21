"""Export Dual-Vector WC4 select-11 plan with FTs applied at recorded weeks."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUT_DIR = ROOT / "docs/archive/gw1-19-first-half-chip-path"
POS_ORDER = {"GKP": 0, "DEF": 1, "MID": 2, "FWD": 3}

_SPEC = importlib.util.spec_from_file_location("dv_chips_xi", HERE / "run_chip_path.py")
CHIPS = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(CHIPS)


def _ids(df: pd.DataFrame) -> list[int]:
    return [int(x) for x in df["player_id"].tolist()]


def _squad_at(gw: int, wc: int, fh: int, pre: list[int], fh_ids: list[int], post0: list[int], fts: pd.DataFrame) -> list[int]:
    if gw == fh:
        return list(fh_ids)
    if gw < wc:
        return list(pre)
    ids = list(post0)
    if gw == wc:
        return ids
    for _, ft in fts.iterrows():
        if int(ft["gameweek"]) <= gw:
            out_id = int(ft["out_id"])
            in_id = int(ft["in_id"])
            ids = [in_id if i == out_id else i for i in ids]
            if in_id not in ids:
                ids.append(in_id)
            ids = list(dict.fromkeys(ids))
    return ids


def export_select_11(path: str = "WC4") -> pd.DataFrame:
    wc = int(path.replace("WC", ""))
    pool = pd.read_csv(OUT_DIR / "gw1-19_projections.csv")
    squads = pd.read_csv(OUT_DIR / "first_half_squads.csv")
    weeks = pd.read_csv(OUT_DIR / "first_half_weeks.csv")
    fts = pd.read_csv(OUT_DIR / "first_half_transfers.csv")
    squads = squads[squads["wc"] == wc]
    weeks = weeks[weeks["path"] == path].copy()
    fts = fts[fts["path"] == path]
    pre = _ids(squads[squads["phase"] == "pre-WC"])
    fh_ids = _ids(squads[squads["phase"] == "FH"])
    post0 = _ids(squads[squads["phase"] == "WC rebuild"])
    fh = int(weeks.loc[weeks["chip"] == "FH", "gw"].iloc[0])
    rows: list[dict] = []
    for gw in range(1, 20):
        ids = _squad_at(gw, wc, fh, pre, fh_ids, post0, fts)
        squad = pool[pool["player_id"].isin(ids)].copy()
        if len(squad) != 15:
            raise RuntimeError(f"GW{gw} squad size {len(squad)} ids={ids}")
        week = weeks[weeks["gw"] == gw].iloc[0]
        chip = str(week["chip"]) if pd.notna(week["chip"]) else ""
        bb = gw == 1
        tc = chip == "TC"
        xp, cap, starters = CHIPS.score_week(squad, gw, bb=bb, tc=tc)
        starters = starters.copy()
        starters["_pos"] = starters["position"].map(POS_ORDER)
        xp_col = CHIPS.xp_col(gw)
        starters = starters.sort_values(["_pos", xp_col], ascending=[True, False])
        n_def = int((starters["position"] == "DEF").sum())
        n_mid = int((starters["position"] == "MID").sum())
        n_fwd = int((starters["position"] == "FWD").sum())
        formation = "BB-15" if bb else f"{n_def}-{n_mid}-{n_fwd}"
        held = set(int(x) for x in starters["player_id"])
        bench = squad[~squad["player_id"].isin(held)].sort_values(["position", "web_name"])
        xi_xp = float(starters[xp_col].sum())
        for _, r in starters.iterrows():
            rows.append({
                "path": path,
                "gw": gw,
                "chip": chip,
                "formation": formation,
                "captain": cap,
                "player_id": int(r["player_id"]),
                "web_name": r["web_name"],
                "club_short": r["club_short"],
                "position": r["position"],
                "cost": float(r["cost"]),
                "xp": round(float(r[xp_col]), 2),
                "is_captain": r["web_name"] == cap,
                "xi_xp": round(xi_xp, 2),
                "week_xp": round(float(xp), 2),
                "published_week_xp": round(float(week["xp"]), 2),
                "bench": ", ".join(bench["web_name"].tolist()),
            })
    out = pd.DataFrame(rows)
    dest = OUT_DIR / "first_half_select_11.csv"
    out.to_csv(dest, index=False)
    return out


if __name__ == "__main__":
    df = export_select_11("WC4")
    print(df.groupby("gw").agg(n=("web_name", "count"), form=("formation", "first"), cap=("captain", "first")).to_string())
    print("Wrote", OUT_DIR / "first_half_select_11.csv")
