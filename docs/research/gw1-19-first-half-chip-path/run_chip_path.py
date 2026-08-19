"""First-Half Chip Path: GW1 BB, WC3 or WC4, FH+TC search, greedy FTs, zero hits."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp

sys.path.insert(0, ".")

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUT_DIR = ROOT / "data/research/gw1-19-first-half-chip-path"
PROJ_CSV = OUT_DIR / "gw1-19_projections.csv"
END_GW = 19
MAX_BUDGET = 100.0
DECAY = 0.84
DRAFT_ROLES = ("Nailed Starter", "Regular Starter")
POS_COUNTS = {"GKP": 2, "DEF": 5, "MID": 5, "FWD": 3}

_PROJ_SPEC = importlib.util.spec_from_file_location("project_gw1_19_fh", HERE / "project_gw1_19.py")
_PROJ_MOD = importlib.util.module_from_spec(_PROJ_SPEC)
assert _PROJ_SPEC.loader is not None
_PROJ_SPEC.loader.exec_module(_PROJ_MOD)


def xp_col(gw: int) -> str:
    return f"gw{gw}_xp"


def solve_squad(
    df: pd.DataFrame,
    gw_list: list[int],
    bb_gw: int | None = None,
    decay_base: float = 1.0,
    anchor_gw: int | None = None,
) -> pd.DataFrame:
    df = df[df["expected_role"].isin(DRAFT_ROLES)].copy().reset_index(drop=True)
    n = len(df)
    if not gw_list:
        raise ValueError("gw_list empty")
    anchor = gw_list[0] if anchor_gw is None else anchor_gw
    c = np.zeros(2 * n)
    for gw in gw_list:
        w = decay_base ** (gw - anchor)
        xp = df[xp_col(gw)].values
        if bb_gw == gw:
            c[:n] -= xp * w
        else:
            c[n:] -= xp * w
    a_rows: list[np.ndarray] = []
    b_l: list[float] = []
    b_u: list[float] = []
    cost_row = np.zeros(2 * n)
    cost_row[:n] = df["cost"].values
    a_rows.append(cost_row)
    b_l.append(0.0)
    b_u.append(MAX_BUDGET)
    for pos, qty in POS_COUNTS.items():
        row = np.zeros(2 * n)
        row[:n] = (df["position"] == pos).astype(float).values
        a_rows.append(row)
        b_l.append(float(qty))
        b_u.append(float(qty))
    for club in df["club_short"].unique():
        row = np.zeros(2 * n)
        row[:n] = (df["club_short"] == club).astype(float).values
        a_rows.append(row)
        b_l.append(0.0)
        b_u.append(3.0)
    for i in range(n):
        row = np.zeros(2 * n)
        row[i] = -1.0
        row[n + i] = 1.0
        a_rows.append(row)
        b_l.append(-np.inf)
        b_u.append(0.0)
    sum_y = np.zeros(2 * n)
    sum_y[n:] = 1.0
    a_rows.append(sum_y)
    b_l.append(11.0)
    b_u.append(11.0)
    for pos, lo, hi in [("GKP", 1, 1), ("DEF", 3, 5), ("MID", 2, 5), ("FWD", 1, 3)]:
        row = np.zeros(2 * n)
        row[n:] = (df["position"] == pos).astype(float).values
        a_rows.append(row)
        b_l.append(float(lo))
        b_u.append(float(hi))
    res = milp(c=c, integrality=np.ones(2 * n), bounds=Bounds(0, 1), constraints=LinearConstraint(np.array(a_rows), b_l, b_u))
    if res.x is None or res.status != 0:
        raise RuntimeError(f"MILP failed status={res.status} gws={gw_list}")
    squad = df.iloc[np.where(res.x[:n] > 0.5)[0]].copy()
    squad.attrs["spend"] = float(squad["cost"].sum())
    return squad


def get_gw_starters(df_squad: pd.DataFrame, gw: int, bb_gw: int | None = None) -> tuple[pd.DataFrame, float]:
    col = xp_col(gw)
    if bb_gw == gw:
        return df_squad.copy(), float(df_squad[col].sum())
    gkps = df_squad[df_squad["position"] == "GKP"].sort_values(col, ascending=False)
    best_gkp = gkps.iloc[0:1]
    outfield = df_squad[df_squad["position"] != "GKP"].copy()
    n = len(outfield)
    c = -outfield[col].values
    a_rows = [np.ones(n)]
    b_l = [10.0]
    b_u = [10.0]
    for pos, lo, hi in [("DEF", 3, 5), ("MID", 2, 5), ("FWD", 1, 3)]:
        a_rows.append((outfield["position"] == pos).astype(float).values)
        b_l.append(float(lo))
        b_u.append(float(hi))
    res = milp(c=c, integrality=np.ones(n), bounds=Bounds(0, 1), constraints=LinearConstraint(np.array(a_rows), b_l, b_u))
    selected_outfield = outfield.iloc[np.where(res.x > 0.5)[0]]
    starters = pd.concat([best_gkp, selected_outfield])
    return starters, float(starters[col].sum())


def score_week(squad: pd.DataFrame, gw: int, *, bb: bool = False, tc: bool = False) -> tuple[float, str, pd.DataFrame]:
    starters, base = get_gw_starters(squad, gw, bb_gw=gw if bb else None)
    cap = starters.sort_values(xp_col(gw), ascending=False).iloc[0]
    cap_xp = float(cap[xp_col(gw)])
    extra = 2.0 * cap_xp if tc else cap_xp
    return base + extra, str(cap["web_name"]), starters


def _xp_matrix(df: pd.DataFrame) -> np.ndarray:
    return df[[xp_col(g) for g in range(1, END_GW + 1)]].to_numpy(dtype=float)


def approx_remaining_idx(
    xp: np.ndarray,
    pos: np.ndarray,
    idx: np.ndarray,
    start_gw: int,
    skip: set[int],
    decay_base: float,
) -> float:
    total = 0.0
    sub = xp[idx]
    is_gk = pos[idx] == "GKP"
    for gw in range(start_gw, END_GW + 1):
        if gw in skip:
            continue
        col = sub[:, gw - 1]
        gk = col[is_gk].max() if is_gk.any() else 0.0
        out = np.sort(col[~is_gk])[-10:].sum() if (~is_gk).sum() else 0.0
        cap = float(col.max())
        total += (decay_base ** (gw - start_gw)) * (float(gk) + float(out) + cap)
    return total


def greedy_fts(
    pool: pd.DataFrame,
    squad: pd.DataFrame,
    start_gw: int,
    skip: set[int],
    bank_end_prev: int,
) -> tuple[pd.DataFrame, list[dict]]:
    pool = pool.reset_index(drop=True)
    xp = _xp_matrix(pool)
    pos = pool["position"].to_numpy()
    club = pool["club_short"].to_numpy()
    cost = pool["cost"].to_numpy(dtype=float)
    pid = pool["player_id"].to_numpy()
    names = pool["web_name"].to_numpy()
    idx = np.array([int(np.where(pid == int(p))[0][0]) for p in squad["player_id"]], dtype=int)
    bank = bank_end_prev
    log: list[dict] = []
    for gw in range(start_gw, END_GW + 1):
        bank = min(5, bank + 1)
        if gw in skip:
            continue
        remaining = [g for g in range(gw, END_GW + 1) if g not in skip]
        rest = xp[:, [g - 1 for g in remaining]].sum(axis=1)
        while bank >= 1:
            current_val = approx_remaining_idx(xp, pos, idx, gw, skip, DECAY)
            held = set(idx.tolist())
            itb = MAX_BUDGET - float(cost[idx].sum())
            best: tuple[float, int, int] | None = None
            for out_i, si in enumerate(idx):
                cand = np.where((pos == pos[si]) & ~np.isin(np.arange(len(pool)), list(held)))[0]
                cand = cand[np.argsort(-rest[cand])][:40]
                for tj in cand:
                    if cost[tj] - cost[si] > itb + 1e-9:
                        continue
                    clubs = [club[k] for k in idx if k != si] + [club[tj]]
                    if clubs.count(club[tj]) > 3:
                        continue
                    trial = idx.copy()
                    trial[out_i] = tj
                    gain = approx_remaining_idx(xp, pos, trial, gw, skip, DECAY) - current_val
                    if best is None or gain > best[0]:
                        best = (gain, out_i, int(tj))
            if best is None or best[0] <= 0.05:
                break
            _, out_i, tj = best
            si = int(idx[out_i])
            log.append({
                "gameweek": gw,
                "out": names[si],
                "out_id": int(pid[si]),
                "in": names[tj],
                "in_id": int(pid[tj]),
                "approx_gain": round(float(best[0]), 3),
                "bank_after": bank - 1,
            })
            idx[out_i] = tj
            bank -= 1
    out_squad = pool.iloc[idx].copy()
    out_squad.attrs["spend"] = float(out_squad["cost"].sum())
    return out_squad, log


def pre_wc_gws(wc: int, fh: int) -> list[int]:
    return [g for g in range(1, wc) if g != fh]


def post_wc_gws(wc: int, fh: int) -> list[int]:
    return [g for g in range(wc, END_GW + 1) if g != fh]


def starting_bank(wc: int) -> int:
    """Unused FTs through WC week (GW1 starts at 0; +1 each later GW; WC spends 0)."""
    bank = 0
    for gw in range(1, wc + 1):
        if gw > 1:
            bank = min(5, bank + 1)
    return bank


def evaluate_calendar(pool: pd.DataFrame, wc: int, fh: int, cache: dict) -> dict:
    tc_candidates = [g for g in range(2, END_GW + 1) if g not in {wc, fh}]
    pre_key = ("pre", wc, tuple(pre_wc_gws(wc, fh)))
    if pre_key not in cache:
        gws = pre_wc_gws(wc, fh)
        cache[pre_key] = solve_squad(pool, gws, bb_gw=1, decay_base=1.0)
    fh_key = ("fh", fh)
    if fh_key not in cache:
        cache[fh_key] = solve_squad(pool, [fh], bb_gw=None, decay_base=1.0)
    post_key = ("post", wc, tuple(post_wc_gws(wc, fh)))
    if post_key not in cache:
        gws = post_wc_gws(wc, fh)
        cache[post_key] = solve_squad(pool, gws, bb_gw=None, decay_base=DECAY, anchor_gw=wc)
    pre = cache[pre_key]
    fh_squad = cache[fh_key]
    post0 = cache[post_key]
    skip = {fh}
    post, ft_log = greedy_fts(pool, post0, wc + 1, skip, starting_bank(wc))

    def squad_for(gw: int) -> pd.DataFrame:
        if gw == fh:
            return fh_squad
        if gw < wc:
            return pre
        if gw == wc:
            return post0
        return post

    weeks: list[dict] = []
    total = 0.0
    best_tc = (-1.0, tc_candidates[0])
    for gw in range(1, END_GW + 1):
        chip = "BB" if gw == 1 else ("FH" if gw == fh else ("WC" if gw == wc else ""))
        xp, cap, _ = score_week(squad_for(gw), gw, bb=(gw == 1), tc=False)
        if gw in tc_candidates:
            tc_total, _, _ = score_week(squad_for(gw), gw, bb=False, tc=True)
            delta = tc_total - xp
            if delta > best_tc[0]:
                best_tc = (delta, gw)
        weeks.append({"gw": gw, "xp": xp, "captain": cap, "chip": chip, "squad": "fh" if gw == fh else ("pre" if gw < wc else ("wc" if gw == wc else "post"))})
        total += xp

    tc_gw = int(best_tc[1])
    for w in weeks:
        if w["gw"] != tc_gw:
            continue
        tc_total, tc_cap, _ = score_week(squad_for(tc_gw), tc_gw, bb=False, tc=True)
        total += tc_total - w["xp"]
        w["xp"] = tc_total
        w["captain"] = tc_cap
        w["chip"] = "TC"
        break

    return {
        "wc": wc,
        "fh": fh,
        "tc": tc_gw,
        "total_19gw_xp": round(total, 2),
        "pre": pre,
        "fh_squad": fh_squad,
        "post0": post0,
        "post": post,
        "ft_log": ft_log,
        "weeks": weeks,
        "pre_spend": float(pre.attrs["spend"]),
        "fh_spend": float(fh_squad.attrs["spend"]),
        "post_spend": float(post.attrs["spend"]),
        "n_fts": len(ft_log),
    }


def squad_rows(cal: dict, phase: str, squad: pd.DataFrame) -> list[dict]:
    rows = []
    for _, r in squad.iterrows():
        rows.append({
            "wc": cal["wc"],
            "fh": cal["fh"],
            "tc": cal["tc"],
            "phase": phase,
            "player_id": int(r["player_id"]),
            "web_name": r["web_name"],
            "club_short": r["club_short"],
            "position": r["position"],
            "cost": float(r["cost"]),
            "expected_role": r["expected_role"],
        })
    return rows


def rescore_canonical_s1(pool: pd.DataFrame) -> dict:
    sim = pd.read_csv(ROOT / "data/research/gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/gw1-6_wc4_simulation.csv")
    pre_ids = sim[sim["phase"].str.contains("Pre-WC")]["player_id"].tolist()
    post_ids = sim[sim["phase"].str.contains("Post-WC")]["player_id"].tolist()
    pre = pool[pool["player_id"].isin(pre_ids)].copy()
    post = pool[pool["player_id"].isin(post_ids)].copy()
    if len(pre) < 15 or len(post) < 15:
        return {"note": "Canonical S1 ids missing from Dual-Vector draft pool", "total_6gw_xp_dv": None}
    total = 0.0
    caps = {}
    for gw, squad, bb in [(1, pre, True), (2, pre, False), (3, pre, False), (4, post, False), (5, post, False), (6, post, False)]:
        xp, cap, _ = score_week(squad, gw, bb=bb, tc=False)
        total += xp
        caps[gw] = cap
    summary = pd.read_csv(
        ROOT / "data/research/gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/gw1-6_wc4_summary.csv"
    )
    canonical_fdr_xp = round(float(summary.iloc[0]["total_6gw_xp"]), 2)
    return {
        "note": "Canonical S1 15s re-scored on Prior-Season Dual-Vector Seed (not live FDR-xP)",
        "total_6gw_xp_dv": round(total, 2),
        "captains": caps,
        "canonical_fdr_xp": canonical_fdr_xp,
    }


def user_baseline(pool: pd.DataFrame) -> dict | None:
    path = Path("data/processed/user_picks.parquet")
    if not path.exists():
        return None
    picks = pd.read_parquet(path)
    ids = [int(x) for x in picks["player_id"]]
    squad = pool[pool["player_id"].isin(ids)].copy()
    if len(squad) < 11:
        return {"note": "User Squad not fully in Dual-Vector draft pool", "n": len(squad)}
    total = 0.0
    for gw in range(1, END_GW + 1):
        xp, _, _ = score_week(squad, gw, bb=(gw == 1), tc=False)
        total += xp
    return {
        "n_mapped": len(squad),
        "total_19gw_xp_bb1_only": round(total, 2),
        "spend": round(float(squad["cost"].sum()), 1),
    }


def run_chip_path() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if not PROJ_CSV.exists():
        _PROJ_MOD.project_gw1_19()
    pool = pd.read_csv(PROJ_CSV)
    cache: dict = {}
    search_rows = []
    winners: dict[int, dict] = {}
    for wc in (3, 4):
        best: dict | None = None
        for fh in range(2, END_GW + 1):
            if fh == wc:
                continue
            print(f"Evaluating WC{wc} FH{fh}...", flush=True)
            cal = evaluate_calendar(pool, wc, fh, cache)
            search_rows.append({
                "wc": wc,
                "fh": fh,
                "tc": cal["tc"],
                "total_19gw_xp": cal["total_19gw_xp"],
                "n_fts": cal["n_fts"],
                "pre_spend": round(cal["pre_spend"], 1),
                "post_spend": round(cal["post_spend"], 1),
            })
            if best is None or cal["total_19gw_xp"] > best["total_19gw_xp"]:
                best = cal
        assert best is not None
        winners[wc] = best
        print(f"Winner WC{wc}: FH{best['fh']} TC{best['tc']} {best['total_19gw_xp']} xP")

    pd.DataFrame(search_rows).sort_values(["wc", "total_19gw_xp"], ascending=[True, False]).to_csv(
        OUT_DIR / "fh_week_search.csv", index=False
    )
    summary_rows = []
    sim_rows: list[dict] = []
    week_rows: list[dict] = []
    ft_rows: list[dict] = []
    for wc, cal in winners.items():
        summary_rows.append({
            "path": f"WC{wc}",
            "bb": 1,
            "wc": cal["wc"],
            "fh": cal["fh"],
            "tc": cal["tc"],
            "total_19gw_xp": cal["total_19gw_xp"],
            "n_fts": cal["n_fts"],
            "pre_spend": round(cal["pre_spend"], 1),
            "fh_spend": round(cal["fh_spend"], 1),
            "post_spend": round(cal["post_spend"], 1),
            "hits": 0,
        })
        sim_rows.extend(squad_rows(cal, "pre-WC", cal["pre"]))
        sim_rows.extend(squad_rows(cal, "FH", cal["fh_squad"]))
        sim_rows.extend(squad_rows(cal, "WC rebuild", cal["post0"]))
        sim_rows.extend(squad_rows(cal, "after FTs", cal["post"]))
        for w in cal["weeks"]:
            week_rows.append({"path": f"WC{wc}", **w, "xp": round(w["xp"], 2)})
        for tr in cal["ft_log"]:
            ft_rows.append({"path": f"WC{wc}", **tr})
    df_summary = pd.DataFrame(summary_rows)
    df_summary.to_csv(OUT_DIR / "first_half_summary.csv", index=False)
    pd.DataFrame(sim_rows).to_csv(OUT_DIR / "first_half_squads.csv", index=False)
    pd.DataFrame(week_rows).to_csv(OUT_DIR / "first_half_weeks.csv", index=False)
    pd.DataFrame(ft_rows).to_csv(OUT_DIR / "first_half_transfers.csv", index=False)

    canon = rescore_canonical_s1(pool)
    user = user_baseline(pool)
    pd.DataFrame([{**canon, **{f"user_{k}": v for k, v in (user or {}).items()}}]).to_csv(
        OUT_DIR / "canonical_s1_dual_vector_rescore.csv", index=False
    )
    print(df_summary.to_string(index=False))
    print("Canonical S1 Dual-Vector re-score:", canon)
    print("User baseline:", user)


if __name__ == "__main__":
    run_chip_path()
