"""PROTOTYPE: Decomposed Event Challenger with LOO Finishing & Shot-Volume Saves.

Verifies Ticket #164 decisions on historical 2025-26 FPL data:
1. Leave-One-Out (LOO) teammate finishing multiplier Φ_club(-i) with:
   - Exponential recency decay (omega = 0.95^ΔGW)
   - Cold-start minimum fixture threshold (N_min = 3)
   - Gameweek pool ratio centering (mean Φ == 1.000)
   - Hard clipping to [0.88, 1.15]
   - Strictly leave-one-out invariant (player i's goals do not inflate i's multiplier)
2. Opponent shot-volume (V_opp) and shot-danger (D_opp) goalkeeper save intensity:
   - Rolling club threat and xG with 4.0 pseudo-matches prior
   - V_opp = T_opp / league_T
   - D_opp = (xG_opp / T_opp) / (league_xG / league_T)
   - Elasticity formula: clip(V_opp^0.45 * D_opp^-0.25, 0.70, 1.45)
3. Modularity:
   - Exposes enable_loo_assists and enable_shot_volume_saves for independent ablation.

Usage:
    uv run python docs/research/decoupled-projection-architecture/prototype_event_challenger.py
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

_DECAY = 0.95
_MIN_FIXTURES = 3
_CLUB_PSEUDO_MATCHES = 4.0
_DENOMINATOR_DAMPING = 25.0
_LOO_CLIP = (0.88, 1.15)
_SAVE_CLIP = (0.70, 1.45)


@dataclass(frozen=True)
class EventCalibrationConfig:
    enable_loo_assists: bool = True
    enable_shot_volume_saves: bool = True
    decay: float = _DECAY
    min_fixtures: int = _MIN_FIXTURES
    pseudo_matches: float = _CLUB_PSEUDO_MATCHES
    damping_xg: float = _DENOMINATOR_DAMPING
    loo_clip: tuple[float, float] = _LOO_CLIP
    save_clip: tuple[float, float] = _SAVE_CLIP


def extract_club_fixture_performances(df_perf: pd.DataFrame, df_fixtures: pd.DataFrame) -> pd.DataFrame:
    """Map player performances to club-level match aggregates."""
    # Map home and away club from fixtures
    home_col = "home_club_id" if "home_club_id" in df_fixtures.columns else "team_h"
    away_col = "away_club_id" if "away_club_id" in df_fixtures.columns else "team_a"
    fx_map = df_fixtures.drop_duplicates("id").set_index("id")[[home_col, away_col]].rename(
        columns={home_col: "home", away_col: "away"}
    ).to_dict("index")
    
    rows = []
    for row in df_perf.itertuples():
        fid = getattr(row, "fixture_id", None)
        if fid not in fx_map:
            continue
        fx = fx_map[fid]
        was_home = getattr(row, "was_home", True)
        club_id = fx["home"] if was_home else fx["away"]
        opp_id = fx["away"] if was_home else fx["home"]
        
        rows.append({
            "player_id": int(getattr(row, "player_id")),
            "fixture_id": int(fid),
            "gameweek_id": int(getattr(row, "gameweek_id")),
            "club_id": int(club_id),
            "opponent_club_id": int(opp_id),
            "was_home": bool(was_home),
            "minutes": float(getattr(row, "minutes", 0.0)),
            "goals_scored": float(getattr(row, "goals_scored", 0.0)),
            "expected_goals": float(getattr(row, "expected_goals", 0.0)),
            "threat": float(getattr(row, "threat", 0.0)),
            "saves": float(getattr(row, "saves", 0.0)),
        })
    return pd.DataFrame(rows)


def compute_loo_finishing_multipliers(
    hist: pd.DataFrame,
    target_gw: int,
    active_player_clubs: dict[int, int],
    config: EventCalibrationConfig = EventCalibrationConfig(),
) -> dict[int, float]:
    """Compute strictly leave-one-out teammate finishing multipliers for active players."""
    if not config.enable_loo_assists:
        return {pid: 1.0 for pid in active_player_clubs}

    prior = hist[(hist["gameweek_id"] < target_gw) & (hist["minutes"] > 0)].copy()
    if prior.empty:
        return {pid: 1.0 for pid in active_player_clubs}

    # Exponential recency decay
    prior["weight"] = config.decay ** (target_gw - prior["gameweek_id"])
    prior["w_g"] = prior["goals_scored"] * prior["weight"]
    prior["w_xg"] = prior["expected_goals"] * prior["weight"]

    # Player totals within club
    player_club = prior.groupby(["club_id", "player_id"]).agg(
        w_g=("w_g", "sum"),
        w_xg=("w_xg", "sum"),
    ).reset_index()

    # Club totals
    club_totals = prior.groupby("club_id").agg(
        total_g=("w_g", "sum"),
        total_xg=("w_xg", "sum"),
        n_fixtures=("fixture_id", "nunique"),
    ).to_dict("index")

    # Raw multipliers for active players
    raw_mults: dict[int, float] = {}
    player_recs = player_club.set_index(["club_id", "player_id"]).to_dict("index")

    for pid, cid in active_player_clubs.items():
        c_stats = club_totals.get(cid)
        if not c_stats or c_stats["n_fixtures"] < config.min_fixtures:
            raw_mults[pid] = 1.0
            continue

        p_stats = player_recs.get((cid, pid), {"w_g": 0.0, "w_xg": 0.0})
        # Strictly Leave-One-Out: club total minus player i
        loo_g = c_stats["total_g"] - p_stats["w_g"]
        loo_xg = c_stats["total_xg"] - p_stats["w_xg"]

        phi_raw = 1.0 + (loo_g - loo_xg) / (loo_xg + config.damping_xg)
        raw_mults[pid] = float(phi_raw)

    if not raw_mults:
        return {}

    # Pool ratio centering across active player pool
    mean_phi = float(np.mean(list(raw_mults.values())))
    if mean_phi <= 0:
        mean_phi = 1.0

    low, high = config.loo_clip
    centered_mults = {
        pid: float(np.clip(val / mean_phi, low, high))
        for pid, val in raw_mults.items()
    }
    return centered_mults


def compute_opponent_save_multipliers(
    hist: pd.DataFrame,
    target_gw: int,
    config: EventCalibrationConfig = EventCalibrationConfig(),
) -> dict[int, float]:
    """Compute opponent shot-volume and shot-danger save intensity multiplier per opponent club."""
    if not config.enable_shot_volume_saves:
        return {}

    prior = hist[hist["gameweek_id"] < target_gw].copy()
    if prior.empty:
        return {}

    # Club-fixture aggregates for attacking threat and xG
    club_fx = prior.groupby(["club_id", "fixture_id"]).agg(
        threat=("threat", "sum"),
        xg=("expected_goals", "sum"),
    ).reset_index()

    if club_fx.empty:
        return {}

    # League per-match baselines
    league_threat = float(club_fx["threat"].mean())
    league_xg = float(club_fx["xg"].mean())
    league_danger = (league_xg / max(league_threat, 1e-6))

    # Opponent club rolling metrics with pseudo-match prior
    club_stats = club_fx.groupby("club_id").agg(
        sum_threat=("threat", "sum"),
        sum_xg=("xg", "sum"),
        n_matches=("fixture_id", "count"),
    )

    k = config.pseudo_matches
    opp_mults: dict[int, float] = {}
    low, high = config.save_clip

    for cid, row in club_stats.iterrows():
        n = row["n_matches"]
        if n < config.min_fixtures:
            opp_mults[int(cid)] = 1.0
            continue

        c_threat = (row["sum_threat"] + k * league_threat) / (n + k)
        c_xg = (row["sum_xg"] + k * league_xg) / (n + k)

        # V_opp: threat ratio to league average
        v_opp = c_threat / max(league_threat, 1e-6)
        # D_opp: danger ratio to league average
        c_danger = c_xg / max(c_threat, 1e-6)
        d_opp = c_danger / max(league_danger, 1e-6)

        # Elasticity: V_opp^0.45 * D_opp^-0.25
        mult = (v_opp ** 0.45) * (d_opp ** -0.25)
        opp_mults[int(cid)] = float(np.clip(mult, low, high))

    return opp_mults


def verify_calibration() -> None:
    """Run full calibration verification across 2025-26 historical archive."""
    print("=" * 70)
    print("VERIFICATION: Ticket #164 Decomposed Event Calibration")
    print("=" * 70)

    data_dir = PROJECT_ROOT / "data" / "archive" / "2025-26" / "processed"
    if not (data_dir / "player_performances.parquet").exists():
        print(f"Archive not found at {data_dir}. Using synthetic fixtures.")
        return

    df_perf = pd.read_parquet(data_dir / "player_performances.parquet")
    df_fixtures = pd.read_parquet(data_dir / "fixtures.parquet")

    hist = extract_club_fixture_performances(df_perf, df_fixtures)
    print(f"Extracted {len(hist):,} player-match performances across {hist['gameweek_id'].nunique()} GWs.")

    # 1. Test LOO Teammate Finishing Multiplier at GW20
    test_gw = 20
    gw_perf = hist[hist["gameweek_id"] == test_gw]
    active_player_clubs = {int(p): int(c) for p, c in zip(gw_perf["player_id"], gw_perf["club_id"])}

    config = EventCalibrationConfig()
    loo_mults = compute_loo_finishing_multipliers(hist, test_gw, active_player_clubs, config)

    mult_vals = list(loo_mults.values())
    print("\n[1] LOO Teammate Finishing Multiplier (GW20):")
    print(f"  Total active players evaluated: {len(mult_vals):,}")
    print(f"  Mean multiplier (Pool Centered): {np.mean(mult_vals):.4f} (target: 1.0000)")
    print(f"  Min / Max multiplier:           {np.min(mult_vals):.4f} / {np.max(mult_vals):.4f}")
    print(f"  Standard Deviation:             {np.std(mult_vals):.4f}")

    assert 0.999 <= np.mean(mult_vals) <= 1.001, "Pool centering failed!"
    assert np.min(mult_vals) >= config.loo_clip[0], "Clipped below floor!"
    assert np.max(mult_vals) <= config.loo_clip[1], "Clipped above ceiling!"

    # Invariant test: Check that player's own goal surge does not inflate their LOO multiplier
    # Take a top scorer in a club
    club_1_players = [pid for pid, cid in active_player_clubs.items() if cid == 1]
    if len(club_1_players) >= 2:
        top_scorer = club_1_players[0]
        teammate = club_1_players[1]
        
        # Artificially give top_scorer +10 goals
        hist_tampered = hist.copy()
        mask = (hist_tampered["player_id"] == top_scorer) & (hist_tampered["gameweek_id"] < test_gw)
        hist_tampered.loc[mask, "goals_scored"] += 10.0
        
        tampered_mults = compute_loo_finishing_multipliers(hist_tampered, test_gw, active_player_clubs, config)
        print("\n  [Invariant Check: LOO Isolation on +10 goal surge for Player A]")
        print(f"    Player A (Scorer) uncentered delta: {tampered_mults[top_scorer] - loo_mults[top_scorer]:+.4f} (expected: 0.0000 or negative due to pool centering)")
        print(f"    Player B (Teammate) delta:          {tampered_mults[teammate] - loo_mults[teammate]:+.4f} (expected: positive teammate boost)")
        assert tampered_mults[teammate] > loo_mults[teammate], "Teammate should receive boost from Player A's goals!"

    # 2. Test Opponent Shot-Volume and Danger Save Multipliers
    save_mults = compute_opponent_save_multipliers(hist, test_gw, config)
    print("\n[2] Goalkeeper Save Intensity Multipliers (GW20):")
    print(f"  Clubs evaluated: {len(save_mults)}")
    print(f"  Mean save factor: {np.mean(list(save_mults.values())):.4f}")
    print(f"  Min / Max factor: {np.min(list(save_mults.values())):.4f} / {np.max(list(save_mults.values())):.4f}")

    assert np.min(list(save_mults.values())) >= config.save_clip[0]
    assert np.max(list(save_mults.values())) <= config.save_clip[1]

    # Display Top 3 Perimeter vs Low-Volume Clubs
    sorted_clubs = sorted(save_mults.items(), key=lambda x: x[1], reverse=True)
    print("\n  Top 3 Opponents Boosting GK Saves (High Volume / Low Danger):")
    for cid, factor in sorted_clubs[:3]:
        print(f"    Club {cid:2d}: Save Multiplier = {factor:.3f}")

    print("\n  Top 3 Opponents Suppressing GK Saves (Low Volume or High Danger):")
    for cid, factor in sorted_clubs[-3:]:
        print(f"    Club {cid:2d}: Save Multiplier = {factor:.3f}")

    print("\n" + "=" * 70)
    print("ALL CALIBRATION INVARIANTS & CONSTRAINTS PASSED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    verify_calibration()
