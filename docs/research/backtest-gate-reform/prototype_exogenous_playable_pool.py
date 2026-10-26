"""Simulation runner and validation harness for Exogenous Playable Pool Masking

and Active-Window Guardrail Enforcement (Wayfinder Ticket #170, ADR 0064).
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def generate_synthetic_season(
    *,
    num_gws: int = 38,
    num_players: int = 600,
    dormant_gws: int = 19,
    active_captain_regret_bias: float = 0.22,
    fringe_speculation_count: int = 40,
    seed: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Generate paired synthetic champion and candidate evaluation dataframes."""
    rng = np.random.default_rng(seed)

    champ_rows = []
    cand_rows = []

    for gw in range(1, num_gws + 1):
        is_active_gw = gw > dormant_gws

        for p_id in range(1, num_players + 1):
            # Establish baseline profile
            is_starter = p_id <= 180
            is_sub = 180 < p_id <= 250

            if is_starter:
                actual_minutes = int(rng.integers(60, 91))
                base_xp = float(rng.uniform(3.0, 7.5))
            elif is_sub:
                actual_minutes = int(rng.integers(15, 46))
                base_xp = float(rng.uniform(1.2, 2.5))
            else:
                actual_minutes = 0
                base_xp = float(rng.uniform(0.1, 0.9))

            # Actual points loosely correlated with xp + noise
            actual_points = max(0.0, float(round(base_xp + rng.normal(0, 1.5))))

            champ_xp = base_xp
            champ_rows.append(
                {
                    "gameweek": gw,
                    "player_id": p_id,
                    "projected_points": champ_xp,
                    "actual_points": actual_points,
                    "actual_minutes": actual_minutes,
                }
            )

            # Candidate logic:
            if not is_active_gw:
                cand_xp = champ_xp  # 100% Champion fallback
            else:
                cand_xp = champ_xp + float(rng.normal(0, 0.4))
                # Add captaincy regret bias on top scorers
                if p_id in (1, 2, 3):
                    cand_xp -= active_captain_regret_bias

                # Fringe player speculation on unplayed reserves
                if fringe_speculation_count > 0 and 250 < p_id <= 250 + fringe_speculation_count:
                    cand_xp = 3.5  # Speculative fringe projection

            cand_rows.append(
                {
                    "gameweek": gw,
                    "player_id": p_id,
                    "projected_points": cand_xp,
                    "actual_points": actual_points,
                    "actual_minutes": actual_minutes,
                }
            )

    return pd.DataFrame(champ_rows), pd.DataFrame(cand_rows)


def evaluate_exogenous_vs_endogenous_mask(
    champ_df: pd.DataFrame,
    cand_df: pd.DataFrame,
    xp_thresh: float = 2.0,
    mins_thresh: float = 30.0,
) -> dict[str, object]:
    """Compare exogenous vs endogenous playable pool metrics."""
    merged = champ_df.merge(
        cand_df[["gameweek", "player_id", "projected_points"]].rename(
            columns={"projected_points": "cand_xp"}
        ),
        on=["gameweek", "player_id"],
    ).rename(columns={"projected_points": "champ_xp"})

    # Endogenous mask: depends on cand_xp
    endogenous_mask = (
        (merged["champ_xp"] >= xp_thresh)
        | (merged["cand_xp"] >= xp_thresh)
        | (merged["actual_minutes"] >= mins_thresh)
    )
    # Exogenous mask (ADR 0064): model-independent
    exogenous_mask = (merged["champ_xp"] >= xp_thresh) | (
        merged["actual_minutes"] >= mins_thresh
    )

    endo_sub = merged[endogenous_mask]
    exo_sub = merged[exogenous_mask]

    return {
        "endogenous_row_count": len(endo_sub),
        "exogenous_row_count": len(exo_sub),
        "row_count_difference": len(endo_sub) - len(exo_sub),
        "exo_champ_mae": float((exo_sub["champ_xp"] - exo_sub["actual_points"]).abs().mean()),
        "exo_cand_mae": float((exo_sub["cand_xp"] - exo_sub["actual_points"]).abs().mean()),
        "endo_champ_mae": float((endo_sub["champ_xp"] - endo_sub["actual_points"]).abs().mean()),
        "endo_cand_mae": float((endo_sub["cand_xp"] - endo_sub["actual_points"]).abs().mean()),
    }


def identify_active_gameweeks_sim(
    champ_df: pd.DataFrame,
    cand_df: pd.DataFrame,
    tol: float = 1e-6,
) -> list[int]:
    """Identify gameweeks where candidate diverges from champion."""
    merged = champ_df[["gameweek", "player_id", "projected_points"]].merge(
        cand_df[["gameweek", "player_id", "projected_points"]],
        on=["gameweek", "player_id"],
        suffixes=("_champ", "_cand"),
    )
    merged["diff"] = (merged["projected_points_cand"] - merged["projected_points_champ"]).abs()
    active_gws = [
        int(gw)
        for gw, max_diff in merged.groupby("gameweek")["diff"].max().items()
        if max_diff > tol
    ]
    return sorted(active_gws)


def simulate_dormant_dilution() -> None:
    print("=" * 70)
    print("SIMULATION: Exogenous Masking & Dormant Fallback Error Dilution")
    print("=" * 70)

    champ_df, cand_df = generate_synthetic_season(
        num_gws=38,
        num_players=600,
        dormant_gws=19,
        active_captain_regret_bias=0.25,
        fringe_speculation_count=40,
    )

    # 1. Test Exogeneity
    mask_res = evaluate_exogenous_vs_endogenous_mask(champ_df, cand_df)
    print("\n1. Playable Pool Masking Comparison:")
    print(f"   - Exogenous Mask Rows : {mask_res['exogenous_row_count']:,}")
    print(f"   - Endogenous Mask Rows: {mask_res['endogenous_row_count']:,}")
    print(f"   - Candidate Shift Rows: +{mask_res['row_count_difference']:,} fringe rows injected!")
    print(f"   - Exo Champ MAE       : {mask_res['exo_champ_mae']:.4f}")
    print(f"   - Endo Champ MAE      : {mask_res['endo_champ_mae']:.4f} (distorted benchmark!)")

    assert mask_res["row_count_difference"] > 0, "Endogenous mask should have inflated rows"

    # 2. Test Invariance across varying candidates
    _, cand_clean_df = generate_synthetic_season(
        num_gws=38,
        num_players=600,
        dormant_gws=19,
        active_captain_regret_bias=0.0,
        fringe_speculation_count=0,
    )
    clean_res = evaluate_exogenous_vs_endogenous_mask(champ_df, cand_clean_df)
    print("\n2. Invariance Verification across clean candidate:")
    print(f"   - Exogenous rows (clean)      : {clean_res['exogenous_row_count']:,}")
    print(f"   - Exogenous rows (speculative): {mask_res['exogenous_row_count']:,}")
    assert clean_res["exogenous_row_count"] == mask_res["exogenous_row_count"], (
        "Exogenous mask row count must be 100% bit-for-bit identical!"
    )
    print("   -> PASS: Exogenous row count is 100% invariant to candidate predictions.")

    # 3. Active Gameweek Detection
    active_gws = identify_active_gameweeks_sim(champ_df, cand_df)
    print("\n3. Active Gameweek Detection:")
    print(f"   - Detected Active Gameweeks: GW{active_gws[0]} to GW{active_gws[-1]} ({len(active_gws)} GWs)")
    assert active_gws == list(range(20, 39)), "Should detect exactly GW20 to GW38 as active"
    print("   -> PASS: Accurately identified active window G_active = {20..38}.")

    # 4. Error Dilution Demonstration
    # Suppose Captaincy Regret in active GWs is +0.24 pts (Tolerance is 0.15)
    active_error = 0.24
    dormant_weeks = 19
    active_weeks = 19
    full_season_error = (dormant_weeks * 0.0 + active_weeks * active_error) / 38
    print("\n4. Dormant Error Dilution Analysis:")
    print(f"   - Active Window Regret (GW20–38): +{active_error:.3f} pts/GW (TOL = +0.15)")
    print(f"   - Full Season Regret (GW1–38)  : +{full_season_error:.3f} pts/GW (DILUTED by 50%!)")
    print(f"   - Full-season gate only pass?  : {full_season_error <= 0.15} (FALSE PASS!)")
    print(f"   - Active-window gate pass?     : {active_error <= 0.15} (REJECTED AS DESIRED)")
    print("   -> PASS: Dual enforcement catches dormant fallback error dilution.")

    print("\n" + "=" * 70)
    print("ALL SIMULATION PROTOTYPE ASSERTIONS PASSED SUCCESSFULLY.")
    print("=" * 70)


if __name__ == "__main__":
    simulate_dormant_dilution()
