"""GW1–5 Chip Strategy Simulation Engine.

Simulates 5-Gameweek trajectories across three primary chip strategies:
1. Scenario A: BB1 + WC4 (Bench Boost GW1, Wildcard GW4)
2. Scenario B: BB2 + WC4 (Bench Boost GW2, Wildcard GW4)
3. Scenario C: Standard WC4 (No Early BB, Wildcard GW4)

Sources projections from data/research/expected-stats-gw1-5/gw1-5_projections.csv.

XI-aware MILP: select (x) + start (y) binaries so non-BB weeks score XI only;
BB weeks score all 15. GW1–3 keeps £0.5m ITB (budget ≤ 99.5).
Captain = highest XI xP (2×). No Triple Captain in this sim.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp

ITB_BUFFER = 0.5  # £m held for WC4 price rises
MAX_BUDGET = 100.0


def load_data() -> pd.DataFrame:
    df_proj = pd.read_csv("data/research/expected-stats-gw1-5/gw1-5_projections.csv")
    df_players = pd.read_parquet("data/processed/players.parquet")
    df = df_proj.merge(
        df_players[["id", "now_cost", "selected_by_percent"]],
        left_on="player_id",
        right_on="id",
        how="left",
    )
    df["cost"] = df["now_cost"] / 10.0
    df["selected_by_percent"] = df["selected_by_percent"].fillna(0.0)
    return df[df["draft_availability"] == "eligible"].reset_index(drop=True)


def _squad_constraints(
    df: pd.DataFrame,
    n: int,
    max_spend: float,
) -> tuple[list[np.ndarray], list[float], list[float]]:
    """Constraints on select vars x[0:n] only (ignore trailing start vars)."""
    a_rows: list[np.ndarray] = []
    b_l: list[float] = []
    b_u: list[float] = []

    cost_row = np.zeros(2 * n)
    cost_row[:n] = df["cost"].values
    a_rows.append(cost_row)
    b_l.append(0.0)
    b_u.append(max_spend)

    for pos, qty in [("GKP", 2), ("DEF", 5), ("MID", 5), ("FWD", 3)]:
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

    return a_rows, b_l, b_u


def _xi_link_constraints(n: int) -> tuple[list[np.ndarray], list[float], list[float]]:
    """y <= x; sum y = 11."""
    a_rows: list[np.ndarray] = []
    b_l: list[float] = []
    b_u: list[float] = []

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

    return a_rows, b_l, b_u


def _xi_position_constraints(
    df: pd.DataFrame, n: int
) -> tuple[list[np.ndarray], list[float], list[float]]:
    """Valid XI on start vars y: 1 GKP, DEF 3–5, MID 2–5, FWD 1–3."""
    a_rows: list[np.ndarray] = []
    b_l: list[float] = []
    b_u: list[float] = []
    for pos, lo, hi in [("GKP", 1, 1), ("DEF", 3, 5), ("MID", 2, 5), ("FWD", 1, 3)]:
        row = np.zeros(2 * n)
        row[n:] = (df["position"] == pos).astype(float).values
        a_rows.append(row)
        b_l.append(float(lo))
        b_u.append(float(hi))
    return a_rows, b_l, b_u


def solve_squad(
    df: pd.DataFrame,
    gw_weights: dict[int, float],
    bb_gw: int | None = None,
    max_spend: float = MAX_BUDGET - ITB_BUFFER,
) -> pd.DataFrame:
    """Pick 15 + latent XI maximizing weighted GW xP (BB week counts all 15)."""
    n = len(df)
    c = np.zeros(2 * n)
    for gw, w in gw_weights.items():
        xp = df[f"gw{gw}_xp"].values
        if bb_gw == gw:
            c[:n] -= w * xp
        else:
            c[n:] -= w * xp

    a_rows, b_l, b_u = _squad_constraints(df, n, max_spend)
    for rows, lo, hi in (_xi_link_constraints(n), _xi_position_constraints(df, n)):
        a_rows.extend(rows)
        b_l.extend(lo)
        b_u.extend(hi)

    res = milp(
        c=c,
        integrality=np.ones(2 * n),
        bounds=Bounds(0, 1),
        constraints=LinearConstraint(np.array(a_rows), b_l, b_u),
    )
    if res.x is None or res.status != 0:
        raise RuntimeError(f"MILP failed status={res.status} message={res.message}")
    selected = df.iloc[np.where(res.x[:n] > 0.5)[0]].copy()
    selected.attrs["spend"] = float(selected["cost"].sum())
    selected.attrs["itb"] = MAX_BUDGET - selected.attrs["spend"]
    return selected


def pick_xi(squad_df: pd.DataFrame, gw: int) -> pd.DataFrame:
    """Formation-safe XI: 1 GKP, ≥3 DEF, ≥2 MID, ≥1 FWD; no 2nd GKP in fill."""
    col = f"gw{gw}_xp"
    squad = squad_df.sort_values(col, ascending=False)
    gkp = squad[squad["position"] == "GKP"].iloc[0:1]
    defs = squad[squad["position"] == "DEF"].iloc[0:3]
    mids = squad[squad["position"] == "MID"].iloc[0:2]
    fwds = squad[squad["position"] == "FWD"].iloc[0:1]
    locked = pd.concat([gkp, defs, mids, fwds])
    rem = squad[
        (~squad["player_id"].isin(locked["player_id"])) & (squad["position"] != "GKP")
    ].sort_values(col, ascending=False)
    return pd.concat([locked, rem.iloc[0:4]])


def evaluate_gameweek(squad_df: pd.DataFrame, gw: int, is_bb: bool = False) -> dict:
    """Simulate one GW score for a 15-player squad. Captain = top XI xP (2×)."""
    col = f"gw{gw}_xp"
    if is_bb:
        starters = squad_df.copy()
        points = float(squad_df[col].sum())
    else:
        starters = pick_xi(squad_df, gw)
        points = float(starters[col].sum())
        counts = starters["position"].value_counts()
        assert len(starters) == 11
        assert counts.get("GKP", 0) == 1
        assert counts.get("DEF", 0) >= 3
        assert counts.get("MID", 0) >= 2
        assert counts.get("FWD", 0) >= 1

    c_cand = starters.sort_values(col, ascending=False).iloc[0]
    c_pts = float(c_cand[col])
    points += c_pts  # 2x total

    return {
        "gw": gw,
        "points": round(points, 2),
        "captain": c_cand["web_name"],
        "captain_pts": round(c_pts, 2),
        "c_mode": "C",
        "is_bb": is_bb,
        "starters_count": len(starters),
    }


def run_simulations() -> dict:
    df = load_data()
    scenarios: dict = {}

    configs = [
        ("BB1_WC4", "Scenario A: BB1 + WC4", 1),
        ("BB2_WC4", "Scenario B: BB2 + WC4", 2),
        ("Standard_WC4", "Scenario C: Standard WC4 (No Early BB)", None),
    ]

    wc4 = solve_squad(
        df,
        gw_weights={4: 1.0, 5: 1.0},
        bb_gw=None,
        max_spend=MAX_BUDGET,
    )

    for key, name, bb_gw in configs:
        weights = {1: 0.9, 2: 0.9, 3: 0.9}
        if bb_gw == 1:
            weights = {1: 1.0, 2: 0.9, 3: 0.9}
        elif bb_gw == 2:
            weights = {1: 0.9, 2: 1.0, 3: 0.9}

        sq = solve_squad(df, gw_weights=weights, bb_gw=bb_gw)
        evals = [
            evaluate_gameweek(sq, 1, is_bb=(bb_gw == 1)),
            evaluate_gameweek(sq, 2, is_bb=(bb_gw == 2)),
            evaluate_gameweek(sq, 3, is_bb=False),
            evaluate_gameweek(wc4, 4, is_bb=False),
            evaluate_gameweek(wc4, 5, is_bb=False),
        ]
        total = round(sum(e["points"] for e in evals), 2)
        scenarios[key] = {
            "name": name,
            "squad_gw1": sq,
            "squad_wc4": wc4,
            "evals": evals,
            "total_xp": total,
            "spend": round(float(sq["cost"].sum()), 1),
            "itb": round(MAX_BUDGET - float(sq["cost"].sum()), 1),
        }
        print(
            f"{key}: total={total} spend={scenarios[key]['spend']} "
            f"ITB={scenarios[key]['itb']} "
            + " | ".join(f"GW{e['gw']}={e['points']}(C:{e['captain']})" for e in evals)
        )

    sim_rows = [
        {
            "scenario_key": sc_key,
            "scenario_name": sc["name"],
            "gameweek": ev["gw"],
            "projected_points": ev["points"],
            "captain": ev["captain"],
            "captain_pts": ev["captain_pts"],
            "captain_mode": ev["c_mode"],
            "is_bench_boost": ev["is_bb"],
            "squad_spend": sc["spend"],
            "squad_itb": sc["itb"],
        }
        for sc_key, sc in scenarios.items()
        for ev in sc["evals"]
    ]
    out_csv = Path("data/research/gw1-5-chip-simulation/gw1-5_chip_simulation.csv")
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(sim_rows).to_csv(out_csv, index=False)
    print(f"Exported simulation CSV to {out_csv}")
    return scenarios


def _self_check() -> None:
    """ponytail: fails if formation/ITB/captain regressions return."""
    df = load_data()
    sq = solve_squad(df, gw_weights={1: 1.0, 2: 0.9, 3: 0.9}, bb_gw=1)
    assert float(sq["cost"].sum()) <= MAX_BUDGET - ITB_BUFFER + 1e-6
    xi = pick_xi(sq, 1)
    assert (xi["position"] == "GKP").sum() == 1
    ev = evaluate_gameweek(sq, 3, is_bb=False)
    assert ev["c_mode"] == "C"
    bb = evaluate_gameweek(sq, 1, is_bb=True)
    nobb = evaluate_gameweek(sq, 1, is_bb=False)
    delta = bb["points"] - nobb["points"]
    assert 0 < delta < 25, f"BB delta out of band: {delta}"
    print(f"self_check ok (BB1 delta={delta:.2f}, ITB={MAX_BUDGET - float(sq['cost'].sum()):.1f})")


if __name__ == "__main__":
    _self_check()
    run_simulations()
