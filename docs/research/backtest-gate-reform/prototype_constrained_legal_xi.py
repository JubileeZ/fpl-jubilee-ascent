"""Prototype Simulation: Constrained Legal Formation XI & Top-15 Squad Churn (Ticket #169).

Simulates:
1. Formulation of select_legal_formation_xi with:
   - 1 GKP, (d, m, f) outfielders across 8 legal formations
   - Max 3 players per club
   - Starting XI budget cap (default £83.5m / 835.0 units)
   - Deterministic tie-breaking: [-points, cost, player_id]
2. Top-15 budget-feasible squad selection (£100.0m budget, 2 GKP, 5 DEF, 5 MID, 3 FWD, max 3 per club).
3. Weekly squad churn Churn_g = 15 - |S_g cap S_{g-1}| and guardrail evaluation.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp


_POS_GKP = 1
_POS_DEF = 2
_POS_MID = 3
_POS_FWD = 4

_LEGAL_FORMATIONS = (
    (3, 5, 2),
    (3, 4, 3),
    (4, 4, 2),
    (4, 3, 3),
    (4, 5, 1),
    (5, 3, 2),
    (5, 4, 1),
    (5, 2, 3),
)


def select_legal_formation_xi(
    group: pd.DataFrame,
    sort_col: str = "projected_points",
    *,
    budget_cap: float | None = 835.0,
    max_per_club: int = 3,
    cost_col: str = "now_cost",
    club_col: str = "club_id",
) -> pd.DataFrame:
    """Select optimal 11-player lineup subject to formation, club, and budget constraints.

    Uses scipy.optimize.milp for fast deterministic integer programming.
    Tie-breaking: higher sort_col, then lower cost, then lower player_id.
    """
    if "position_id" not in group.columns or len(group) < 11:
        return group.nlargest(min(11, len(group)), sort_col)

    # Candidate reduction: top candidates per position to keep MILP ultra-fast (<5ms)
    # 15 GKPs, 30 DEFs, 35 MIDs, 20 FWDs is plenty for any legal XI
    gkp_cand = group[group["position_id"] == _POS_GKP].nlargest(min(15, len(group)), sort_col)
    def_cand = group[group["position_id"] == _POS_DEF].nlargest(min(30, len(group)), sort_col)
    mid_cand = group[group["position_id"] == _POS_MID].nlargest(min(35, len(group)), sort_col)
    fwd_cand = group[group["position_id"] == _POS_FWD].nlargest(min(20, len(group)), sort_col)

    pool = pd.concat([gkp_cand, def_cand, mid_cand, fwd_cand]).drop_duplicates("player_id").reset_index(drop=True)
    n = len(pool)
    if n < 11:
        return group.nlargest(min(11, len(group)), sort_col)

    # Deterministic tie-breaking objective:
    # Maximize: sort_col - 1e-5 * cost - 1e-9 * player_id
    costs = pool[cost_col].to_numpy(dtype=float) if cost_col in pool.columns else np.zeros(n)
    player_ids = pool["player_id"].to_numpy(dtype=float) if "player_id" in pool.columns else np.arange(n, dtype=float)
    scores = pool[sort_col].to_numpy(dtype=float)

    # Normalize cost if in £m (e.g. 8.5 vs 85)
    cost_scale = 10.0 if np.max(costs) <= 20.0 and np.max(costs) > 0 else 1.0
    scaled_costs = costs * cost_scale
    effective_budget = budget_cap if budget_cap is not None else float("inf")

    # Scipy minimizes c @ x -> c = -(scores - 1e-5 * scaled_costs - 1e-9 * player_ids)
    c = -(scores - 1e-5 * scaled_costs - 1e-9 * player_ids)

    positions = pool["position_id"].to_numpy(dtype=int)
    clubs = pool[club_col].to_numpy() if club_col in pool.columns else np.zeros(n, dtype=int)
    unique_clubs = np.unique(clubs) if club_col in pool.columns else []

    A_rows = []
    lb = []
    ub = []

    # 1. Total XI = 11
    A_rows.append(np.ones(n))
    lb.append(11.0)
    ub.append(11.0)

    # 2. GKP = 1
    A_rows.append((positions == _POS_GKP).astype(float))
    lb.append(1.0)
    ub.append(1.0)

    # 3. DEF in [3, 5]
    A_rows.append((positions == _POS_DEF).astype(float))
    lb.append(3.0)
    ub.append(5.0)

    # 4. MID in [2, 5]
    A_rows.append((positions == _POS_MID).astype(float))
    lb.append(2.0)
    ub.append(5.0)

    # 5. FWD in [1, 3]
    A_rows.append((positions == _POS_FWD).astype(float))
    lb.append(1.0)
    ub.append(3.0)

    # 6. Budget cap
    if budget_cap is not None and cost_col in pool.columns:
        A_rows.append(scaled_costs)
        lb.append(0.0)
        ub.append(effective_budget)

    # 7. Max per club <= 3
    if club_col in pool.columns and max_per_club > 0:
        for cl in unique_clubs:
            A_rows.append((clubs == cl).astype(float))
            lb.append(0.0)
            ub.append(float(max_per_club))

    A = np.array(A_rows)
    constraints = LinearConstraint(A, lb, ub)
    integrality = np.ones(n)
    bounds = Bounds(0, 1)

    res = milp(c=c, integrality=integrality, bounds=bounds, constraints=constraints)

    if res.success:
        selected_idx = np.where(res.x > 0.5)[0]
        selected_df = pool.iloc[selected_idx].copy()
        # Sort by deterministic key
        sort_order = np.lexsort((
            selected_df["player_id"] if "player_id" in selected_df.columns else np.arange(len(selected_df)),
            selected_df[cost_col] if cost_col in selected_df.columns else np.zeros(len(selected_df)),
            -selected_df[sort_col],
        ))
        return selected_df.iloc[sort_order].reset_index(drop=True)

    # Fallback to legacy best_legal_xi if unfeasible under tight budget
    return _legacy_best_legal_xi(group, sort_col)


def _legacy_best_legal_xi(group: pd.DataFrame, sort_col: str) -> pd.DataFrame:
    """Legacy unconstrained formation scan (ADR 0054)."""
    gkp = group[group["position_id"] == _POS_GKP].nlargest(1, sort_col)
    defs = group[group["position_id"] == _POS_DEF].nlargest(5, sort_col)
    mids = group[group["position_id"] == _POS_MID].nlargest(5, sort_col)
    fwds = group[group["position_id"] == _POS_FWD].nlargest(3, sort_col)

    if len(gkp) < 1 or len(defs) < 3 or len(mids) < 2 or len(fwds) < 1:
        return group.nlargest(min(11, len(group)), sort_col)

    best_xi: pd.DataFrame | None = None
    best_score = float("-inf")
    for d, m, f in _LEGAL_FORMATIONS:
        if len(defs) >= d and len(mids) >= m and len(fwds) >= f:
            candidate = pd.concat([gkp, defs.iloc[:d], mids.iloc[:m], fwds.iloc[:f]])
            score = float(candidate[sort_col].sum())
            if score > best_score:
                best_score = score
                best_xi = candidate
    return best_xi if best_xi is not None else group.nlargest(min(11, len(group)), sort_col)


def select_top_15_squad(
    group: pd.DataFrame,
    sort_col: str = "projected_points",
    *,
    squad_budget: float = 1000.0,
    max_per_club: int = 3,
    cost_col: str = "now_cost",
    club_col: str = "club_id",
) -> pd.DataFrame:
    """Select optimal 15-player squad (2 GKP, 5 DEF, 5 MID, 3 FWD) subject to £100.0m budget."""
    if "position_id" not in group.columns or len(group) < 15:
        return group.nlargest(min(15, len(group)), sort_col)

    pool = group.reset_index(drop=True)
    n = len(pool)

    costs = pool[cost_col].to_numpy(dtype=float) if cost_col in pool.columns else np.zeros(n)
    player_ids = pool["player_id"].to_numpy(dtype=float) if "player_id" in pool.columns else np.arange(n, dtype=float)
    scores = pool[sort_col].to_numpy(dtype=float)

    cost_scale = 10.0 if np.max(costs) <= 20.0 and np.max(costs) > 0 else 1.0
    scaled_costs = costs * cost_scale

    c = -(scores - 1e-5 * scaled_costs - 1e-9 * player_ids)

    positions = pool["position_id"].to_numpy(dtype=int)
    clubs = pool[club_col].to_numpy() if club_col in pool.columns else np.zeros(n, dtype=int)
    unique_clubs = np.unique(clubs) if club_col in pool.columns else []

    A_rows = [
        np.ones(n),  # total 15
        (positions == _POS_GKP).astype(float),  # 2 GKP
        (positions == _POS_DEF).astype(float),  # 5 DEF
        (positions == _POS_MID).astype(float),  # 5 MID
        (positions == _POS_FWD).astype(float),  # 3 FWD
        scaled_costs,  # budget <= 1000.0
    ]
    lb = [15.0, 2.0, 5.0, 5.0, 3.0, 0.0]
    ub = [15.0, 2.0, 5.0, 5.0, 3.0, squad_budget]

    if club_col in pool.columns and max_per_club > 0:
        for cl in unique_clubs:
            A_rows.append((clubs == cl).astype(float))
            lb.append(0.0)
            ub.append(float(max_per_club))

    A = np.array(A_rows)
    constraints = LinearConstraint(A, lb, ub)
    integrality = np.ones(n)
    bounds = Bounds(0, 1)

    res = milp(c=c, integrality=integrality, bounds=bounds, constraints=constraints)
    if res.success:
        selected_idx = np.where(res.x > 0.5)[0]
        return pool.iloc[selected_idx].copy().reset_index(drop=True)
    return group.nlargest(min(15, len(group)), sort_col)


def compute_weekly_squad_churn(squads_by_gw: dict[int, set[int]]) -> pd.Series:
    """Calculate weekly squad churn Churn_g = 15 - |S_g cap S_{g-1}|."""
    sorted_gws = sorted(squads_by_gw.keys())
    churn_dict: dict[int, float] = {}
    for i in range(1, len(sorted_gws)):
        gw_prev = sorted_gws[i - 1]
        gw_curr = sorted_gws[i]
        s_prev = squads_by_gw[gw_prev]
        s_curr = squads_by_gw[gw_curr]
        overlap = len(s_prev & s_curr)
        churn = float(15 - overlap)
        churn_dict[gw_curr] = churn
    return pd.Series(churn_dict, dtype=float)


if __name__ == "__main__":
    print("Testing Constrained Legal Formation XI...")
    # Create test scenario with 20 players:
    # 4 Arsenal players (Raya, Gabriel, Saliba, Saka) with high points
    # High premium costs to test budget cap £83.5m
    test_players = [
        {"player_id": 1, "web_name": "Raya", "position_id": 1, "club_id": 1, "now_cost": 55.0, "projected_points": 5.5, "actual_points": 6.0},
        {"player_id": 2, "web_name": "Pickford", "position_id": 1, "club_id": 2, "now_cost": 50.0, "projected_points": 4.5, "actual_points": 3.0},
        # Arsenal DEF
        {"player_id": 11, "web_name": "Gabriel", "position_id": 2, "club_id": 1, "now_cost": 62.0, "projected_points": 5.8, "actual_points": 6.0},
        {"player_id": 12, "web_name": "Saliba", "position_id": 2, "club_id": 1, "now_cost": 60.0, "projected_points": 5.7, "actual_points": 6.0},
        # Other DEF
        {"player_id": 13, "web_name": "Alexander-Arnold", "position_id": 2, "club_id": 3, "now_cost": 72.0, "projected_points": 6.5, "actual_points": 7.0},
        {"player_id": 14, "web_name": "Gvardiol", "position_id": 2, "club_id": 4, "now_cost": 60.0, "projected_points": 5.2, "actual_points": 5.0},
        {"player_id": 15, "web_name": "Robinson", "position_id": 2, "club_id": 5, "now_cost": 47.0, "projected_points": 4.0, "actual_points": 2.0},
        {"player_id": 16, "web_name": "Greaves", "position_id": 2, "club_id": 6, "now_cost": 40.0, "projected_points": 3.2, "actual_points": 2.0},
        # MIDs
        {"player_id": 21, "web_name": "Saka", "position_id": 3, "club_id": 1, "now_cost": 101.0, "projected_points": 7.5, "actual_points": 8.0},
        {"player_id": 22, "web_name": "Palmer", "position_id": 3, "club_id": 7, "now_cost": 108.0, "projected_points": 8.0, "actual_points": 10.0},
        {"player_id": 23, "web_name": "Salah", "position_id": 3, "club_id": 3, "now_cost": 126.0, "projected_points": 8.5, "actual_points": 12.0},
        {"player_id": 24, "web_name": "Mbeumo", "position_id": 3, "club_id": 8, "now_cost": 75.0, "projected_points": 6.2, "actual_points": 7.0},
        {"player_id": 25, "web_name": "Rogers", "position_id": 3, "club_id": 9, "now_cost": 54.0, "projected_points": 5.0, "actual_points": 6.0},
        {"player_id": 26, "web_name": "Smith Rowe", "position_id": 3, "club_id": 5, "now_cost": 57.0, "projected_points": 5.0, "actual_points": 3.0},
        # FWDs
        {"player_id": 31, "web_name": "Haaland", "position_id": 4, "club_id": 4, "now_cost": 153.0, "projected_points": 9.5, "actual_points": 13.0},
        {"player_id": 32, "web_name": "Watkins", "position_id": 4, "club_id": 9, "now_cost": 91.0, "projected_points": 6.8, "actual_points": 8.0},
        {"player_id": 33, "web_name": "Solanke", "position_id": 4, "club_id": 10, "now_cost": 76.0, "projected_points": 5.9, "actual_points": 6.0},
        {"player_id": 34, "web_name": "Wood", "position_id": 4, "club_id": 11, "now_cost": 63.0, "projected_points": 5.5, "actual_points": 5.0},
        {"player_id": 35, "web_name": "Delap", "position_id": 4, "club_id": 6, "now_cost": 56.0, "projected_points": 4.5, "actual_points": 2.0},
    ]
    df = pd.DataFrame(test_players)

    unconstrained = _legacy_best_legal_xi(df, "projected_points")
    print(f"Unconstrained XI cost: {unconstrained['now_cost'].sum():.1f}, Arsenal count: {(unconstrained['club_id'] == 1).sum()}")
    print("Unconstrained lineup:\n", unconstrained[["web_name", "position_id", "club_id", "now_cost", "projected_points"]])

    constrained = select_legal_formation_xi(df, "projected_points", budget_cap=835.0, max_per_club=3)
    print(f"\nConstrained XI cost: {constrained['now_cost'].sum():.1f}, Arsenal count: {(constrained['club_id'] == 1).sum()}")
    print("Constrained lineup:\n", constrained[["web_name", "position_id", "club_id", "now_cost", "projected_points"]])

    assert len(constrained) == 11
    assert constrained["now_cost"].sum() <= 835.0
    assert (constrained["club_id"] == 1).sum() <= 3
    print("\nConstraints verified successfully!")

    print("\nSimulating 5 Gameweeks of Top-15 Squad Churn...")
    # Model A: Stable Champion (low turnover)
    # Model B: Fluke-chasing Candidate (high turnover)
    np.random.seed(42)
    squads_champ = {}
    squads_cand = {}

    # Pool of 40 players across 4 positions
    base_pool = []
    # 4 GKP
    for i in range(1, 5):
        base_pool.append({"player_id": i, "position_id": 1, "club_id": i % 10 + 1, "now_cost": 45.0 + (i % 3) * 5.0, "base_xp": 4.0 + (i % 2) * 0.5})
    # 15 DEF
    for i in range(11, 26):
        base_pool.append({"player_id": i, "position_id": 2, "club_id": (i * 2) % 15 + 1, "now_cost": 45.0 + (i % 5) * 5.0, "base_xp": 4.2 + (i % 4) * 0.4})
    # 15 MID
    for i in range(31, 46):
        base_pool.append({"player_id": i, "position_id": 3, "club_id": (i * 3) % 15 + 1, "now_cost": 50.0 + (i % 6) * 10.0, "base_xp": 5.0 + (i % 5) * 0.6})
    # 8 FWD
    for i in range(51, 59):
        base_pool.append({"player_id": i, "position_id": 4, "club_id": (i * 4) % 15 + 1, "now_cost": 55.0 + (i % 5) * 12.0, "base_xp": 5.5 + (i % 4) * 0.8})

    df_base = pd.DataFrame(base_pool)

    for gw in range(1, 6):
        # Champion: modest fixture swing noise (~0.2 std)
        df_gw_champ = df_base.copy()
        df_gw_champ["projected_points"] = df_gw_champ["base_xp"] + np.random.normal(0, 0.25, len(df_gw_champ))
        s_champ = select_top_15_squad(df_gw_champ, "projected_points")
        squads_champ[gw] = set(s_champ["player_id"])

        # Candidate: noisy / over-reactive fixture chasing (~1.5 std swing)
        df_gw_cand = df_base.copy()
        df_gw_cand["projected_points"] = df_gw_cand["base_xp"] + np.random.normal(0, 1.20, len(df_gw_cand))
        s_cand = select_top_15_squad(df_gw_cand, "projected_points")
        squads_cand[gw] = set(s_cand["player_id"])

    churn_champ = compute_weekly_squad_churn(squads_champ)
    churn_cand = compute_weekly_squad_churn(squads_cand)

    print(f"Champion Weekly Churn (mean = {churn_champ.mean():.2f}):\n{churn_champ.to_dict()}")
    print(f"Candidate Weekly Churn (mean = {churn_cand.mean():.2f}):\n{churn_cand.to_dict()}")

    churn_delta = churn_cand.mean() - churn_champ.mean()
    guardrail_pass = churn_delta <= 0.50
    print(f"\nMean Churn Delta: {churn_delta:+.2f} players/GW (Threshold: <= +0.50)")
    print(f"Guardrail Verdict: {'PASS' if guardrail_pass else 'FAIL (Excessive Squad Churn)'}")

