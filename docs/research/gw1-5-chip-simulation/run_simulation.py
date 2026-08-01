"""GW1–5 Chip Strategy Simulation Engine.

Simulates 5-Gameweek trajectories across three primary chip strategies:
1. Scenario A: BB1 + WC4 (Bench Boost GW1, Wildcard GW4)
2. Scenario B: BB2 + WC4 (Bench Boost GW2, Wildcard GW4)
3. Scenario C: Standard WC4 (No Early BB, Wildcard GW4)

Sources projections from data/research/expected-stats-gw1-5/gw1-5_projections.csv.
"""

from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import LinearConstraint, Bounds, milp

def load_data():
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
    df = df[df["draft_availability"] == "eligible"].reset_index(drop=True)
    return df

def solve_squad_gw1_3(df, bb_gw=None, force_haaland=True):
    """Solve initial 15-player GW1 squad optimized for GW1-3 performance given BB gameweek."""
    N = len(df)
    
    # Calculate weighted objective for GW1-3
    # If BB in GW1: all 15 score in GW1
    # If BB in GW2: 11 score in GW1, 15 score in GW2
    # Plus Captain (top scorer in GW * 1.0) and GW3 starter scores
    
    # For initial squad selection, we maximize total projected points across GW1-3
    if bb_gw == 1:
        # All 15 score in GW1 + 15 in GW2 (bench boost or top starters)
        weights = df["gw1_xp"] * 1.0 + df["gw2_xp"] * 0.9 + df["gw3_xp"] * 0.9
    elif bb_gw == 2:
        weights = df["gw1_xp"] * 0.9 + df["gw2_xp"] * 1.0 + df["gw3_xp"] * 0.9
    else:
        weights = df["gw1_xp"] * 0.9 + df["gw2_xp"] * 0.9 + df["gw3_xp"] * 0.9
        
    c = -weights.values

    A_rows = []
    b_l = []
    b_u = []

    # Budget <= 100.0
    A_rows.append(df["cost"].values)
    b_l.append(0)
    b_u.append(100.0)

    # Positional
    for pos, qty in [("GKP", 2), ("DEF", 5), ("MID", 5), ("FWD", 3)]:
        row = (df["position"] == pos).astype(float).values
        A_rows.append(row)
        b_l.append(qty)
        b_u.append(qty)

    # Max 3 per club
    for club in df["club_short"].unique():
        row = (df["club_short"] == club).astype(float).values
        A_rows.append(row)
        b_l.append(0)
        b_u.append(3.0)

    # Force Haaland if requested
    if force_haaland:
        haaland_idx = df[df["player_id"] == 411].index[0]
        row_h = np.zeros(N)
        row_h[haaland_idx] = 1.0
        A_rows.append(row_h)
        b_l.append(1.0)
        b_u.append(1.0)

    A = np.array(A_rows)
    constraints = LinearConstraint(A, b_l, b_u)
    integrality = np.ones(N)
    bounds = Bounds(0, 1)

    res = milp(c=c, integrality=integrality, bounds=bounds, constraints=constraints)
    selected = df.iloc[np.where(res.x > 0.5)[0]].copy()
    return selected

def solve_wc4_squad(df, force_haaland=True):
    """Solve Wildcard 4 squad optimized for GW4-5 (and horizon beyond)."""
    N = len(df)
    
    # Minimize bench cost on WC to maximize XI budget!
    # Objectives: Maximize GW4-5 XI starters while maintaining budget
    weights = df["gw4_xp"] * 1.0 + df["gw5_xp"] * 1.0
    c = -weights.values

    A_rows = []
    b_l = []
    b_u = []

    # Budget <= 100.0
    A_rows.append(df["cost"].values)
    b_l.append(0)
    b_u.append(100.0)

    for pos, qty in [("GKP", 2), ("DEF", 5), ("MID", 5), ("FWD", 3)]:
        row = (df["position"] == pos).astype(float).values
        A_rows.append(row)
        b_l.append(qty)
        b_u.append(qty)

    for club in df["club_short"].unique():
        row = (df["club_short"] == club).astype(float).values
        A_rows.append(row)
        b_l.append(0)
        b_u.append(3.0)

    if force_haaland:
        haaland_idx = df[df["player_id"] == 411].index[0]
        row_h = np.zeros(N)
        row_h[haaland_idx] = 1.0
        A_rows.append(row_h)
        b_l.append(1.0)
        b_u.append(1.0)

    A = np.array(A_rows)
    constraints = LinearConstraint(A, b_l, b_u)
    integrality = np.ones(N)
    bounds = Bounds(0, 1)

    res = milp(c=c, integrality=integrality, bounds=bounds, constraints=constraints)
    selected = df.iloc[np.where(res.x > 0.5)[0]].copy()
    return selected

def evaluate_gameweek(squad_df, gw, is_bb=False, is_tc=False, tc_player_id=411):
    """Simulate single gameweek score for a 15-player squad."""
    squad = squad_df.sort_values(f"gw{gw}_xp", ascending=False).copy()
    
    if is_bb:
        # All 15 play
        starters = squad.copy()
        points = squad[f"gw{gw}_xp"].sum()
    else:
        # Select valid 11 starters: 1 GKP, >=3 DEF, >=2 MID, >=1 FWD
        gkp = squad[squad["position"] == "GKP"].iloc[0:1]
        defs = squad[squad["position"] == "DEF"].iloc[0:3]
        mids = squad[squad["position"] == "MID"].iloc[0:2]
        fwds = squad[squad["position"] == "FWD"].iloc[0:1]

        rem = squad[~squad["player_id"].isin(pd.concat([gkp, defs, mids, fwds])["player_id"])].sort_values(f"gw{gw}_xp", ascending=False)
        outfield_needed = 11 - (1 + 3 + 2 + 1) # 4 more
        add_starters = rem.iloc[0:outfield_needed]

        starters = pd.concat([gkp, defs, mids, fwds, add_starters])
        points = starters[f"gw{gw}_xp"].sum()

    # Captain
    c_cand = starters.sort_values(f"gw{gw}_xp", ascending=False).iloc[0]
    c_pts = c_cand[f"gw{gw}_xp"]
    
    if is_tc and c_cand["player_id"] == tc_player_id:
        points += c_pts * 2.0 # 3x total (+2x additional)
        c_mode = "TC"
    else:
        points += c_pts * 1.0 # 2x total (+1x additional)
        c_mode = "C"

    return {
        "gw": gw,
        "points": round(points, 2),
        "captain": c_cand["web_name"],
        "captain_pts": round(c_pts, 2),
        "c_mode": c_mode,
        "is_bb": is_bb,
        "starters_count": len(starters),
    }

def run_simulations():
    df = load_data()
    
    scenarios = {}
    
    # --- SCENARIO 1: BB1 + WC4 ---
    sq_bb1 = solve_squad_gw1_3(df, bb_gw=1, force_haaland=True)
    wc4_sq1 = solve_wc4_squad(df, force_haaland=True)
    
    gw1_eval = evaluate_gameweek(sq_bb1, 1, is_bb=True)
    gw2_eval = evaluate_gameweek(sq_bb1, 2, is_bb=False)
    gw3_eval = evaluate_gameweek(sq_bb1, 3, is_bb=False, is_tc=True, tc_player_id=411) # TC Haaland GW3
    gw4_eval = evaluate_gameweek(wc4_sq1, 4, is_bb=False) # WC4
    gw5_eval = evaluate_gameweek(wc4_sq1, 5, is_bb=False)
    
    tot_scen1 = gw1_eval["points"] + gw2_eval["points"] + gw3_eval["points"] + gw4_eval["points"] + gw5_eval["points"]
    scenarios["BB1_WC4"] = {
        "name": "Scenario A: BB1 + WC4 (TC3 Haaland)",
        "squad_gw1": sq_bb1,
        "squad_wc4": wc4_sq1,
        "evals": [gw1_eval, gw2_eval, gw3_eval, gw4_eval, gw5_eval],
        "total_xp": round(tot_scen1, 2),
    }

    # --- SCENARIO 2: BB2 + WC4 ---
    sq_bb2 = solve_squad_gw1_3(df, bb_gw=2, force_haaland=True)
    wc4_sq2 = solve_wc4_squad(df, force_haaland=True)
    
    gw1_eval = evaluate_gameweek(sq_bb2, 1, is_bb=False)
    gw2_eval = evaluate_gameweek(sq_bb2, 2, is_bb=True)
    gw3_eval = evaluate_gameweek(sq_bb2, 3, is_bb=False, is_tc=True, tc_player_id=411) # TC Haaland GW3
    gw4_eval = evaluate_gameweek(wc4_sq2, 4, is_bb=False) # WC4
    gw5_eval = evaluate_gameweek(wc4_sq2, 5, is_bb=False)
    
    tot_scen2 = gw1_eval["points"] + gw2_eval["points"] + gw3_eval["points"] + gw4_eval["points"] + gw5_eval["points"]
    scenarios["BB2_WC4"] = {
        "name": "Scenario B: BB2 + WC4 (TC3 Haaland)",
        "squad_gw1": sq_bb2,
        "squad_wc4": wc4_sq2,
        "evals": [gw1_eval, gw2_eval, gw3_eval, gw4_eval, gw5_eval],
        "total_xp": round(tot_scen2, 2),
    }

    # --- SCENARIO 3: Standard WC4 (No Early BB) ---
    sq_std = solve_squad_gw1_3(df, bb_gw=None, force_haaland=True)
    wc4_sq3 = solve_wc4_squad(df, force_haaland=True)
    
    gw1_eval = evaluate_gameweek(sq_std, 1, is_bb=False)
    gw2_eval = evaluate_gameweek(sq_std, 2, is_bb=False)
    gw3_eval = evaluate_gameweek(sq_std, 3, is_bb=False, is_tc=True, tc_player_id=411)
    gw4_eval = evaluate_gameweek(wc4_sq3, 4, is_bb=False)
    gw5_eval = evaluate_gameweek(wc4_sq3, 5, is_bb=False)
    
    tot_scen3 = gw1_eval["points"] + gw2_eval["points"] + gw3_eval["points"] + gw4_eval["points"] + gw5_eval["points"]
    scenarios["Standard_WC4"] = {
        "name": "Scenario C: Standard WC4 (No Early BB)",
        "squad_gw1": sq_std,
        "squad_wc4": wc4_sq3,
        "evals": [gw1_eval, gw2_eval, gw3_eval, gw4_eval, gw5_eval],
        "total_xp": round(tot_scen3, 2),
    }

    # Export machine-readable simulation CSV
    sim_rows = []
    for sc_key, sc in scenarios.items():
        for ev in sc["evals"]:
            sim_rows.append({
                "scenario_key": sc_key,
                "scenario_name": sc["name"],
                "gameweek": ev["gw"],
                "projected_points": ev["points"],
                "captain": ev["captain"],
                "captain_pts": ev["captain_pts"],
                "captain_mode": ev["c_mode"],
                "is_bench_boost": ev["is_bb"],
            })
    
    df_sim = pd.DataFrame(sim_rows)
    out_csv = Path("data/research/gw1-5-chip-simulation/gw1-5_chip_simulation.csv")
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df_sim.to_csv(out_csv, index=False)
    print(f"Exported simulation CSV to {out_csv}")
    
    return scenarios

if __name__ == "__main__":
    run_simulations()
