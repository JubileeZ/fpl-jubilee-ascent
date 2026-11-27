"""One-shot frozen read-only 2026-27 GW6-11 benchmark: SP_Soft_Shield_M1 vs L1_L3b_shield vs Solio (ADR 0069)."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
RESEARCH_DIR = Path(__file__).resolve().parent
for p in (str(ROOT), str(RESEARCH_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from ablation_replay_runner import (  # noqa: E402
    StatePreservingDefXgShrinkModel,
    _apply_xmins_override,
    _soft_shield_details,
    build_soft_shield_m1_map,
)
from backtesting.metrics import _formation_xi_stats, select_squad_and_formation_xi  # noqa: E402
from features.builder import build_features, load_fit_history, load_xmins_override  # noqa: E402
from features.injury_triage import resolve_gw_reference_date, synthesize_xmins_override  # noqa: E402
from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel  # noqa: E402

ARCHIVE_26_27 = ROOT / "data/archive/2026-27/processed"
SEED_25_26 = ROOT / "data/archive/2025-26/processed"
SOLIO_DIR = ROOT / "data/external/solio/2026-27"

SNAPSHOT_PATHS: dict[int, str] = {
    6: "data/availability-snapshots/2026-27/GW6/20261010T033819Z-c3c496b67adb",
    7: "data/availability-snapshots/2026-27/GW7/20261017T072234Z-c2fe824c916f",
    8: "data/availability-snapshots/2026-27/GW8/20261023T153345Z-31c79cb3c571",
    9: "data/availability-snapshots/2026-27/GW9/20261031T074846Z-31642b208c12",
    11: "data/availability-snapshots/2026-27/GW11/20261121T034001Z-81d298f154c3",
}
POS_NAMES = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}


def extract_snapshot_to_dir(gw: int, dest: Path) -> None:
    """Extract immutable pre-deadline snapshot tables from origin/availability-snapshots."""
    snap_rel = SNAPSHOT_PATHS[gw]
    for fname in ("players.parquet", "fixtures.parquet", "clubs.parquet", "metadata.json"):
        raw = subprocess.check_output(
            ["git", "show", f"origin/availability-snapshots:{snap_rel}/{fname}"],
            cwd=ROOT,
        )
        (dest / fname).write_bytes(raw)


def _compute_metrics(df: pd.DataFrame, mins_col: str, pts_col: str) -> dict[str, float]:
    pm = df[mins_col].to_numpy(dtype=float)
    am = df["actual_minutes"].to_numpy(dtype=float)
    pp = df[pts_col].to_numpy(dtype=float)
    ap = df["actual_points"].to_numpy(dtype=float)
    mask_ge45 = pm >= 45.0
    mask_act60 = am >= 60.0
    return {
        "n": int(len(df)),
        "mins_mae": float(np.mean(np.abs(pm - am))),
        "mins_rmse": float(np.sqrt(np.mean((pm - am) ** 2))),
        "mins_bias": float(np.mean(pm - am)),
        "false_start_pct": float(np.mean(am[mask_ge45] == 0.0) * 100.0) if mask_ge45.any() else float("nan"),
        "missed_starter_pct": float(np.mean(pm[mask_act60] <= 15.0) * 100.0) if mask_act60.any() else float("nan"),
        "xp_mae": float(np.mean(np.abs(pp - ap))),
        "xp_rmse": float(np.sqrt(np.mean((pp - ap) ** 2))),
    }


def _agg_long(pred: pd.DataFrame, mcol: str, pcol: str) -> pd.DataFrame:
    return (
        pred.groupby(["player_id", "gameweek_id"], as_index=False)
        .agg(projected_minutes=("projected_minutes", "sum"), projected_points=("projected_points", "sum"))
        .rename(columns={"projected_minutes": mcol, "projected_points": pcol})
    )


def _club_x90_stats(t0_full: pd.DataFrame, col: str) -> tuple[float, float]:
    grp = t0_full.groupby(["issue_gw", "club_id"], as_index=False)[col].sum()
    vals = grp[col] / 90.0
    return float(vals.mean()), float(vals.std())


def _xi_stats(t0_full: pd.DataFrame, pts_col: str) -> tuple[float, float]:
    df_eval = t0_full[
        ["issue_gw", "player_id", "position_id", "now_cost", "club_id", "actual_points", "actual_minutes", pts_col]
    ].rename(columns={"issue_gw": "gameweek", pts_col: "projected_points"})
    regrets: list[float] = []
    pts_list: list[float] = []
    for _gw, grp in df_eval.groupby("gameweek"):
        _, reg, _ = _formation_xi_stats(grp, target_column="actual_points", budget_cap=1000.0, max_per_club=3)
        opt_xi, _ = select_squad_and_formation_xi(
            grp, "actual_points", squad_budget=1000.0, bench_weight=0.0, max_per_club=3
        )
        opt_pts = float(opt_xi["actual_points"].sum())
        regrets.append(float(reg))
        pts_list.append(opt_pts - float(reg))
    return float(sum(pts_list)), float(np.mean(regrets))


def main() -> None:
    manifest = json.loads((SOLIO_DIR / "manifest.json").read_text(encoding="utf-8"))
    latest_solio: dict[int, dict[str, Any]] = {
        int(e["first_gw"]): e for e in manifest["snapshots"] if e.get("is_latest_pre_deadline")
    }
    perfs_all = pd.read_parquet(ARCHIVE_26_27 / "player_performances.parquet")
    realized = (
        perfs_all[perfs_all["gameweek_id"].between(6, 11)]
        .groupby(["player_id", "gameweek_id"], as_index=False)
        .agg(
            actual_minutes=("minutes", "sum"),
            actual_points=("total_points", "sum"),
        )
    )
    seed_perfs = pd.read_parquet(SEED_25_26 / "player_performances.parquet")
    seed_players = pd.read_parquet(SEED_25_26 / "players.parquet")

    issue_gws = [6, 7, 8, 9, 11]
    all_rows: list[pd.DataFrame] = []

    for gw in issue_gws:
        entry = latest_solio[gw]
        sol_path = SOLIO_DIR / entry["filename"]
        sol_df = pd.read_csv(sol_path)
        horizon = min(3, 12 - gw)
        target_gws = list(range(gw, gw + horizon))

        with tempfile.TemporaryDirectory() as td_str:
            td = Path(td_str)
            extract_snapshot_to_dir(gw, td)
            shutil.copy2(ARCHIVE_26_27 / "gameweeks.parquet", td / "gameweeks.parquet")
            perfs_lt = perfs_all[perfs_all["gameweek_id"] < gw].copy()
            perfs_lt.to_parquet(td / "player_performances.parquet", index=False)

            fit_hist = load_fit_history(td, gw)
            assert fit_hist is not None and int(fit_hist["gameweek_id"].max()) < gw, f"Leakage GW{gw}"

            m_std = DefXgShrinkChallengerModel()
            m_std.fit(fit_hist)
            m_sp = StatePreservingDefXgShrinkModel()
            m_sp.fit(fit_hist)

            snap_players = pd.read_parquet(td / "players.parquet")
            snap_fixtures = pd.read_parquet(td / "fixtures.parquet")
            ref_date = resolve_gw_reference_date(td, gw)

            feat_base = build_features(
                td, gw, horizon=horizon, seed_processed_dir=SEED_25_26, history_before_gw=gw, as_of_gw=None
            )
            pred_l1 = m_std.predict(feat_base, horizon)
            agg_l1 = pred_l1.groupby(["player_id", "gameweek_id"])["projected_minutes"].sum()
            native_mins_map = {(int(pid), int(g)): float(val) for (pid, g), val in agg_l1.items()}

            # 1. Legacy Broad Pool Shield (L1_L3b_shield) & Legacy Solio Cascade (L1_L2_L3b_cascade)
            shield_csv = synthesize_xmins_override(
                td, gw, horizon, base_csv_path=None, include_broad_pool_shield=True,
                reference_date=ref_date, output_path=td / "shield.csv",
            )
            cascade_csv = synthesize_xmins_override(
                td, gw, horizon, base_csv_path=sol_path, include_broad_pool_shield=True,
                reference_date=ref_date, output_path=td / "cascade.csv",
            )
            pred_shield = m_std.predict(
                build_features(td, gw, horizon=horizon, seed_processed_dir=SEED_25_26, history_before_gw=gw, as_of_gw=None, xmins_override=shield_csv),
                horizon,
            )
            pred_cascade = m_std.predict(
                build_features(td, gw, horizon=horizon, seed_processed_dir=SEED_25_26, history_before_gw=gw, as_of_gw=None, xmins_override=cascade_csv),
                horizon,
            )

            # 2. Frozen SP_Soft_Shield_M1 (Solio-free internal baseline)
            sp_soft_m1_map = build_soft_shield_m1_map(
                snap_players, snap_fixtures, fit_hist, gw, horizon, native_mins_map, seed_perfs, seed_players, ref_date
            )
            pred_sp_soft_m1 = m_sp.predict(_apply_xmins_override(feat_base, sp_soft_m1_map), horizon)

            # 3. Frozen SP_Solio_Soft_Shield (Solio Layer 2 + Soft Shield hard guards + State-Preserving scaling)
            sol_map = load_xmins_override(sol_path, target_gws)
            soft_map, hard_zero_keys = _soft_shield_details(
                snap_players, snap_fixtures, fit_hist, gw, horizon, native_mins_map, seed_perfs, seed_players, ref_date
            )
            # Replicate Soft Shield hard guards (pre-return 0.0, u 0.0, n parent-club t=0 0.0, i 20/65 ramp, chance<=0 t=0 0.0)
            # plus fallback baseline where Solio == 0.0 post-return
            solio_soft_map: dict[tuple[int, int], float] = dict(sol_map)
            for k, val in soft_map.items():
                if k in hard_zero_keys:
                    solio_soft_map[k] = 0.0
                elif k not in sol_map or float(sol_map[k]) <= 0.0:
                    solio_soft_map[k] = val
                elif val in (20.0, 40.0, 65.0) and k in soft_map:
                    # Keep injury ramp caps (20m/65m per fixture) if lower than stale Solio
                    solio_soft_map[k] = min(float(sol_map[k]), val) if val <= 65.0 else float(sol_map[k])
            # Match canonical hard guard precedence accurately via return-date guard
            hard_only = synthesize_xmins_override(
                td, gw, horizon, base_csv_path=sol_path, include_broad_pool_shield=True,
                reference_date=ref_date, output_path=td / "cascade_raw.csv",
            )
            legacy_cascade_map = load_xmins_override(hard_only, target_gws)
            # Replace legacy unknown-return 0.0 across horizon with Soft Shield curves when Solio exists
            for k, val in legacy_cascade_map.items():
                if k in soft_map and k not in hard_zero_keys and val == 0.0 and sol_map.get(k, 0.0) > 0.0:
                    solio_soft_map[k] = float(sol_map[k]) * 0.0 + float(soft_map[k])
                elif val == 0.0 and k in hard_zero_keys:
                    solio_soft_map[k] = 0.0
                elif k not in solio_soft_map:
                    solio_soft_map[k] = val
            pred_sp_solio_soft = m_sp.predict(_apply_xmins_override(feat_base, solio_soft_map), horizon)

            sol_long_parts = [
                pd.DataFrame({
                    "player_id": sol_df["ID"].astype(int),
                    "gameweek_id": int(t_gw),
                    "Solio_mins": pd.to_numeric(sol_df[f"{t_gw}_xMins"], errors="coerce"),
                    "Solio_pts": pd.to_numeric(sol_df[f"{t_gw}_Pts"], errors="coerce"),
                })
                for t_gw in target_gws
            ]
            p_sol_direct = pd.concat(sol_long_parts, ignore_index=True)

            base = _agg_long(pred_l1, "L1_mins", "L1_pts")
            for df_arm in (
                _agg_long(pred_shield, "L1_L3b_mins", "L1_L3b_pts"),
                _agg_long(pred_sp_soft_m1, "SP_Soft_M1_mins", "SP_Soft_M1_pts"),
                _agg_long(pred_cascade, "L1_L2_L3b_mins", "L1_L2_L3b_pts"),
                _agg_long(pred_sp_solio_soft, "SP_Solio_Soft_mins", "SP_Solio_Soft_pts"),
                p_sol_direct,
            ):
                base = base.merge(df_arm, on=["player_id", "gameweek_id"], how="left")

            meta_cols = snap_players[["id", "position_id", "club_id", "now_cost"]].rename(columns={"id": "player_id"})
            base = base.merge(meta_cols, on="player_id", how="left")
            base = base.merge(realized, on=["player_id", "gameweek_id"], how="left")
            base["actual_minutes"] = base["actual_minutes"].fillna(0.0)
            base["actual_points"] = base["actual_points"].fillna(0.0)
            base["issue_gw"] = gw
            base["lead_step"] = base["gameweek_id"] - gw
            base["in_solio"] = base["Solio_mins"].notna()
            base["Solio_full_mins"] = base["Solio_mins"].fillna(base["L1_mins"])
            base["Solio_full_pts"] = base["Solio_pts"].fillna(base["L1_pts"])
            all_rows.append(base)

    full_df = pd.concat(all_rows, ignore_index=True)
    common = full_df[full_df["in_solio"]].copy()

    arm_defs_common = [
        ("L1_native", "L1_mins", "L1_pts"),
        ("L1_L3b_shield", "L1_L3b_mins", "L1_L3b_pts"),
        ("SP_Soft_Shield_M1", "SP_Soft_M1_mins", "SP_Soft_M1_pts"),
        ("L1_L2_L3b_cascade", "L1_L2_L3b_mins", "L1_L2_L3b_pts"),
        ("SP_Solio_Soft_Shield", "SP_Solio_Soft_mins", "SP_Solio_Soft_pts"),
        ("Solio_Pts_full", "Solio_mins", "Solio_pts"),
    ]
    arm_defs_full = [
        ("L1_native", "L1_mins", "L1_pts"),
        ("L1_L3b_shield", "L1_L3b_mins", "L1_L3b_pts"),
        ("SP_Soft_Shield_M1", "SP_Soft_M1_mins", "SP_Soft_M1_pts"),
        ("L1_L2_L3b_cascade", "L1_L2_L3b_mins", "L1_L2_L3b_pts"),
        ("SP_Solio_Soft_Shield", "SP_Solio_Soft_mins", "SP_Solio_Soft_pts"),
        ("Solio_Pts_full", "Solio_full_mins", "Solio_full_pts"),
    ]

    t0_full = full_df[full_df["lead_step"] == 0].copy()
    xi_cache = {label: _xi_stats(t0_full, pcol) for label, _mc, pcol in arm_defs_full}
    x90_cache = {label: _club_x90_stats(t0_full, mcol) for label, mcol, _pc in arm_defs_full}

    summary_rows: list[dict[str, Any]] = []
    for pool_name, pool_df, defs in (
        ("common_solio", common, arm_defs_common),
        ("full_snapshot", full_df, arm_defs_full),
    ):
        for win_name, sub in (("t0", pool_df[pool_df["lead_step"] == 0]), ("t0_2", pool_df)):
            for label, mc, pc in defs:
                m = _compute_metrics(sub, mc, pc)
                x90_mean, x90_std = x90_cache[label]
                xi_pts, xi_reg = xi_cache[label]
                summary_rows.append({
                    "pool": pool_name,
                    "window": win_name,
                    "arm": label,
                    "n": m["n"],
                    "mins_mae": round(m["mins_mae"], 4),
                    "mins_rmse": round(m["mins_rmse"], 4),
                    "mins_bias": round(m["mins_bias"], 4),
                    "false_start_pct": round(m["false_start_pct"], 3),
                    "missed_starter_pct": round(m["missed_starter_pct"], 3),
                    "xp_mae": round(m["xp_mae"], 4),
                    "xp_rmse": round(m["xp_rmse"], 4),
                    "club_x90_mean": round(x90_mean, 3),
                    "club_x90_std": round(x90_std, 3),
                    "xi_total_pts": round(xi_pts, 1),
                    "xi_mean_regret": round(xi_reg, 2),
                })

    summary_df = pd.DataFrame(summary_rows)
    out_main = RESEARCH_DIR / "frozen_2026_27_benchmark.csv"
    summary_df.to_csv(out_main, index=False)

    t0_common = common[common["lead_step"] == 0]
    pos_rows: list[dict[str, Any]] = []
    for pid_code, pname in POS_NAMES.items():
        sub_p = t0_common[t0_common["position_id"] == pid_code]
        for label, mc, pc in arm_defs_common:
            m = _compute_metrics(sub_p, mc, pc)
            pos_rows.append({
                "position": pname,
                "arm": label,
                "n": m["n"],
                "mins_mae": round(m["mins_mae"], 4),
                "mins_bias": round(m["mins_bias"], 4),
                "xp_mae": round(m["xp_mae"], 4),
            })
    pos_df = pd.DataFrame(pos_rows)
    out_pos = RESEARCH_DIR / "frozen_2026_27_position_benchmark.csv"
    pos_df.to_csv(out_pos, index=False)

    print(f"Saved -> {out_main}")
    print(summary_df[summary_df["pool"] == "common_solio"].to_string(index=False))
    print(f"\nSaved -> {out_pos}")
    print(pos_df[pos_df["position"] == "GKP"].to_string(index=False))


if __name__ == "__main__":
    main()
