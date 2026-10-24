"""Prototype Simulation: Short-Panel Priors & Continuous Neff Shrinkage (Ticket #168).

Simulates:
1. Continuous Sample-Size Blending (alpha_g) under warm-seeded vs unseeded regimes.
2. Empirical Bayes positional price-tier shrinkage on small samples (T < 15).
3. Z-score feature stability under CausalFeatureScaler with and without EB prior.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def compute_alpha_g(
    gw: int,
    n_seed: int,
    rows_per_gw: float = 715.0,
    n_min: float = 3500.0,
    n_full: float = 7500.0,
) -> tuple[float, float]:
    """Calculate effective sample size and continuous blend factor alpha_g."""
    n_in_season = max(0.0, (gw - 1) * rows_per_gw)
    n_eff = 0.5 * n_seed + n_in_season
    alpha = float(np.clip((n_eff - n_min) / (n_full - n_min), 0.0, 1.0))
    return n_eff, alpha


def empirical_bayes_shrinkage(
    raw_metric: float,
    t_obs: float,
    pos: int,
    cost: float,
    k_prior: float = 12.0,
) -> tuple[float, float, float]:
    """Shrink raw player rate to positional price-tier baseline.

    Positions: 1=GKP, 2=DEF, 3=MID, 4=FWD.
    Cost: FPL cost (e.g. 50 = £5.0m, 105 = £10.5m).
    """
    # Positional price-tier empirical priors for xG90
    tier_priors = {
        # GKP
        1: {40: 0.00, 45: 0.00, 50: 0.00, 55: 0.00},
        # DEF: budget <=4.5: 0.02, mid 5.0-5.5: 0.05, premium >=6.0: 0.10
        2: {40: 0.02, 45: 0.03, 50: 0.05, 55: 0.07, 60: 0.10},
        # MID: budget <=5.0: 0.08, mid 5.5-7.5: 0.18, premium 8.0-10.0: 0.32, elite >=10.5: 0.45
        3: {45: 0.06, 50: 0.09, 55: 0.14, 65: 0.20, 75: 0.26, 85: 0.32, 100: 0.42, 125: 0.52},
        # FWD: budget <=5.5: 0.18, mid 6.0-7.5: 0.30, premium 8.0-11.0: 0.45, elite >=11.5: 0.68
        4: {50: 0.18, 55: 0.22, 65: 0.30, 75: 0.38, 85: 0.45, 115: 0.60, 140: 0.72},
    }

    pos_table = tier_priors.get(pos, tier_priors[3])
    # Find closest tier cost
    costs = np.array(list(pos_table.keys()))
    closest_cost = costs[np.argmin(np.abs(costs - cost))]
    mu_prior = pos_table[closest_cost]

    # Shrinkage weight
    w_sample = t_obs / (t_obs + k_prior)
    shrunk_val = w_sample * raw_metric + (1.0 - w_sample) * mu_prior
    return mu_prior, w_sample, shrunk_val


def simulate_season_alpha_trajectory() -> pd.DataFrame:
    """Compare alpha_g trajectory across all 38 gameweeks."""
    gws = list(range(1, 39))
    records = []
    for g in gws:
        # Warm seeded: 2023-24 archive has ~7600 active player matches
        n_eff_warm, a_warm = compute_alpha_g(g, n_seed=7600)
        # Cold start unseeded: n_seed = 0
        n_eff_cold, a_cold = compute_alpha_g(g, n_seed=0)
        records.append({
            "gw": g,
            "neff_warm": round(n_eff_warm, 1),
            "alpha_warm": round(a_warm, 4),
            "neff_cold": round(n_eff_cold, 1),
            "alpha_cold": round(a_cold, 4),
        })
    return pd.DataFrame(records)


def simulate_player_archetypes() -> pd.DataFrame:
    """Simulate shrinkage on representative archetypes."""
    archetypes = [
        {"name": "Early Talisman Haul (Palmer GW4)", "pos": 3, "cost": 105, "t_obs": 4.0, "raw_xg90": 1.25},
        {"name": "Established Talisman (Salah GW30)", "pos": 3, "cost": 125, "t_obs": 30.0, "raw_xg90": 0.72},
        {"name": "Budget Midfield Fluke (GW3)", "pos": 3, "cost": 50, "t_obs": 3.0, "raw_xg90": 0.65},
        {"name": "Bench Warmer Flash (GW2)", "pos": 3, "cost": 45, "t_obs": 1.5, "raw_xg90": 0.50},
        {"name": "Budget Starter Grinder (GW15)", "pos": 2, "cost": 45, "t_obs": 15.0, "raw_xg90": 0.04},
        {"name": "Attacking Fullback Haul (GW5)", "pos": 2, "cost": 60, "t_obs": 5.0, "raw_xg90": 0.35},
        {"name": "Elite Forward Steady (GW10)", "pos": 4, "cost": 140, "t_obs": 10.0, "raw_xg90": 0.85},
    ]

    results = []
    # Assumed league standard deviation of raw xG90 on small sample vs shrunk
    std_raw = 0.22
    for arc in archetypes:
        mu_prior, w_sample, shrunk_val = empirical_bayes_shrinkage(
            raw_metric=arc["raw_xg90"],
            t_obs=arc["t_obs"],
            pos=arc["pos"],
            cost=arc["cost"],
            k_prior=12.0,
        )
        z_raw = (arc["raw_xg90"] - mu_prior) / std_raw
        # Under shrinkage, deviation from prior is moderated
        z_shrunk = (shrunk_val - mu_prior) / std_raw
        results.append({
            "archetype": arc["name"],
            "t_obs": arc["t_obs"],
            "raw_val": arc["raw_xg90"],
            "prior_baseline": mu_prior,
            "sample_weight": round(w_sample, 3),
            "shrunk_val": round(shrunk_val, 3),
            "dampening_pct": round((1.0 - w_sample) * 100, 1),
            "raw_z": round(z_raw, 2),
            "shrunk_z": round(z_shrunk, 2),
        })
    return pd.DataFrame(results)


if __name__ == "__main__":
    print("=== 1. Effective Sample Size & Continuous Blend Trajectory (alpha_g) ===")
    df_alpha = simulate_season_alpha_trajectory()
    print(df_alpha.iloc[[0, 1, 3, 5, 7, 11, 14, 19, 29, 37]].to_string(index=False))

    print("\n=== 2. Empirical Bayes Positional Price-Tier Shrinkage on Archetypes ===")
    df_arc = simulate_player_archetypes()
    print(df_arc.to_string(index=False))
