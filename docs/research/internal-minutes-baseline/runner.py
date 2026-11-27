"""76-GW ablation and untuned cross-check runner for Internal Minutes Baseline (S-1: 2025-26, S-2: 2024-25)."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
import json
import lzma
import os
from pathlib import Path
import sys
import tempfile
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backtesting.metrics import _formation_xi_stats, select_squad_and_formation_xi  # noqa: E402
from features.builder import build_features, load_fit_history, load_xmins_override  # noqa: E402
from features.injury_triage import resolve_gw_reference_date, synthesize_xmins_override  # noqa: E402
from features.internal_xmins import InternalXminsConfig, compute_internal_xmins_from_tables  # noqa: E402
from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel  # noqa: E402

OUT_DIR = Path(__file__).resolve().parent
POS_NAMES = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}
_WORKER_CACHE: dict[tuple[str, str], dict[str, Any]] = {}


def _bootstrap_elements_to_players_df(bootstrap_path: Path) -> pd.DataFrame:
    """Convert raw bootstrap-static elements list into processed players.parquet schema."""
    payload = json.loads(lzma.open(bootstrap_path, "rt", encoding="utf-8").read())
    df = pd.DataFrame(payload["elements"])
    rename_map = {"team": "club_id", "element_type": "position_id"}
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
    df = df[df["position_id"].isin([1, 2, 3, 4])].copy()
    if "chance_of_playing_next_round" not in df.columns:
        df["chance_of_playing_next_round"] = np.nan
    if "news" not in df.columns:
        df["news"] = ""
    return df


def _apply_xmins_override_to_features(df_feat: pd.DataFrame, xmins_map: dict[tuple[int, int], float]) -> pd.DataFrame:
    """Inject (player_id, gw) -> xMins into FeatureContract matching features.builder DGW splitting."""
    out = df_feat.copy()
    valid_fix = out["fixture_id"].fillna(-1).astype(int) >= 0
    gw_fix_counts = out[valid_fix].groupby(["player_id", "gameweek_id"])["fixture_id"].transform("count")
    fix_count = pd.Series(1, index=out.index, dtype=int)
    fix_count.loc[valid_fix] = gw_fix_counts.astype(int)

    ext_vals: list[float] = []
    for pid, gw, fid, n_fix in zip(
        out["player_id"].astype(int),
        out["gameweek_id"].astype(int),
        out["fixture_id"].fillna(-1).astype(int),
        fix_count,
    ):
        if (pid, gw) in xmins_map:
            if fid < 0:
                ext_vals.append(0.0)
            else:
                per_fix = float(xmins_map[(pid, gw)]) / max(1, int(n_fix))
                ext_vals.append(min(90.0, max(0.0, per_fix)))
        else:
            ext_vals.append(float("nan"))
    out["external_xmins"] = ext_vals
    return out


def save_s1_chance_calibration() -> pd.DataFrame:
    """Compute and save empirical chance_of_playing_next_round ratios on 2025-26 S-1."""
    archive = ROOT / "data/archive/2025-26/processed"
    perfs = pd.read_parquet(archive / "player_performances.parquet")
    realized = perfs.groupby(["player_id", "gameweek_id"], as_index=False).agg(
        actual_minutes=("minutes", "sum"),
        actual_starts=("starts", "max"),
    )

    rows = []
    for gw in range(1, 39):
        bp = ROOT / f"data/reports/empirical_mirrors/2025-26/bootstraps/gw{gw:02d}.json.xz"
        elems = _bootstrap_elements_to_players_df(bp)[["id", "status", "chance_of_playing_next_round"]].rename(
            columns={"id": "player_id"}
        )
        prior = perfs[perfs["gameweek_id"] < gw]
        st = prior.groupby("player_id", as_index=False).agg(prior_starts=("starts", "sum"))
        start_m = prior[prior["starts"] > 0].groupby("player_id")["minutes"].mean().rename("prior_start_mins")
        df = elems.merge(st, on="player_id", how="left").merge(start_m, on="player_id", how="left")
        df["prior_starts"] = df["prior_starts"].fillna(0)
        for t in (0, 1, 2):
            tgw = gw + t
            if tgw > 38:
                continue
            sub = df.merge(realized[realized["gameweek_id"] == tgw], on="player_id", how="left")
            sub["actual_minutes"] = sub["actual_minutes"].fillna(0.0)
            sub["actual_starts"] = sub["actual_starts"].fillna(0.0)
            sub["t"] = t
            rows.append(sub)

    all_df = pd.concat(rows, ignore_index=True)
    starters = all_df[all_df["prior_starts"] >= 2].copy()

    def bucket(r: pd.Series) -> str:
        s = str(r["status"])
        c = r["chance_of_playing_next_round"]
        if s == "a" and (pd.isna(c) or c >= 100):
            return "a_100"
        if s == "d" and c in (75, 50, 25):
            return f"d_{int(c)}"
        if c == 0:
            return f"{s}_0"
        return f"{s}_{c}"

    starters["bucket"] = starters.apply(bucket, axis=1)
    summary = starters.groupby(["t", "bucket"], as_index=False).agg(
        n=("player_id", "count"),
        p_played=("actual_minutes", lambda x: float((x > 0).mean())),
        p_started=("actual_starts", "mean"),
        mean_mins=("actual_minutes", "mean"),
        mean_prior_start_mins=("prior_start_mins", "mean"),
    )
    summary["ratio_vs_prior_start"] = summary["mean_mins"] / summary["mean_prior_start_mins"]
    a100 = summary[summary["bucket"] == "a_100"].set_index("t")["ratio_vs_prior_start"].to_dict()
    summary["ratio_vs_healthy_a100"] = summary.apply(
        lambda r: float(r["ratio_vs_prior_start"]) / float(a100.get(int(r["t"]), 1.0)), axis=1
    )
    summary = summary[summary["n"] >= 10].sort_values(["t", "bucket"]).reset_index(drop=True)
    summary.to_csv(OUT_DIR / "s1_chance_calibration.csv", index=False)
    return summary


def compute_arm_metrics(df: pd.DataFrame, mins_col: str, pts_col: str) -> dict[str, float]:
    """Compute minutes fidelity, start calibration, and xP error metrics."""
    pm = df[mins_col].to_numpy(dtype=float)
    am = df["actual_minutes"].to_numpy(dtype=float)
    ast = df["actual_starts"].to_numpy(dtype=float)
    pp = df[pts_col].to_numpy(dtype=float)
    ap = df["actual_points"].to_numpy(dtype=float)
    p_start_proxy = np.clip(pm / 90.0, 0.0, 1.0)
    mask_ge45 = pm >= 45.0
    mask_act60 = am >= 60.0
    return {
        "n": float(len(df)),
        "mins_mae": float(np.mean(np.abs(pm - am))),
        "mins_rmse": float(np.sqrt(np.mean((pm - am) ** 2))),
        "mins_bias": float(np.mean(pm - am)),
        "start_brier": float(np.mean((p_start_proxy - ast) ** 2)),
        "false_start_pct": float(np.mean(am[mask_ge45] == 0.0) * 100.0) if mask_ge45.any() else float("nan"),
        "missed_starter_pct": float(np.mean(pm[mask_act60] <= 15.0) * 100.0) if mask_act60.any() else float("nan"),
        "xp_mae": float(np.mean(np.abs(pp - ap))),
        "xp_rmse": float(np.sqrt(np.mean((pp - ap) ** 2))),
        "xp_bias": float(np.mean(pp - ap)),
    }


def _get_worker_tables(season: str, seed_season: str) -> dict[str, Any]:
    key = (season, seed_season)
    if key not in _WORKER_CACHE:
        archive = ROOT / f"data/archive/{season}/processed"
        seed_dir = ROOT / f"data/archive/{seed_season}/processed"
        perfs_all = pd.read_parquet(archive / "player_performances.parquet")
        assert not perfs_all.duplicated(["player_id", "fixture_id"]).any(), f"Duplicate keys in {season}"
        assert perfs_all["minutes"].between(0, 90).all(), f"Out-of-range minutes in {season}"
        realized = perfs_all.groupby(["player_id", "gameweek_id"], as_index=False).agg(
            actual_minutes=("minutes", "sum"),
            actual_starts=("starts", "max"),
            actual_points=("total_points", "sum"),
        )
        _WORKER_CACHE[key] = {
            "seed_dir": seed_dir,
            "boot_dir": ROOT / f"data/reports/empirical_mirrors/{season}/bootstraps",
            "perfs_all": perfs_all,
            "fixtures_all": pd.read_parquet(archive / "fixtures.parquet"),
            "clubs_all": pd.read_parquet(archive / "clubs.parquet"),
            "gws_all": pd.read_parquet(archive / "gameweeks.parquet"),
            "seed_perfs": pd.read_parquet(seed_dir / "player_performances.parquet"),
            "seed_players": pd.read_parquet(seed_dir / "players.parquet"),
            "realized": realized,
        }
    return _WORKER_CACHE[key]


def _evaluate_single_gw(
    season: str,
    seed_season: str,
    gw: int,
    arm_configs: dict[str, InternalXminsConfig | None],
) -> tuple[int, pd.DataFrame, pd.DataFrame]:
    """Evaluate all arms for one gameweek in isolation."""
    t = _get_worker_tables(season, seed_season)
    perfs_all = t["perfs_all"]
    fixtures_all = t["fixtures_all"]
    clubs_all = t["clubs_all"]
    gws_all = t["gws_all"]
    seed_dir = t["seed_dir"]
    seed_perfs = t["seed_perfs"]
    seed_players = t["seed_players"]
    realized = t["realized"]

    horizon = min(3, 39 - gw)
    planning_gws = list(range(gw, gw + horizon))
    bp_path = t["boot_dir"] / f"gw{gw:02d}.json.xz"
    df_players_gw = _bootstrap_elements_to_players_df(bp_path)
    valid_pids = set(df_players_gw["id"].astype(int))

    perfs_lt = perfs_all[(perfs_all["gameweek_id"] < gw) & (perfs_all["player_id"].isin(valid_pids))].copy()
    fixtures_pit = fixtures_all.copy()
    if "finished" in fixtures_pit.columns:
        fixtures_pit["finished"] = fixtures_pit["gameweek_id"] < gw
    if "finished_provisional" in fixtures_pit.columns:
        fixtures_pit["finished_provisional"] = fixtures_pit["gameweek_id"] < gw

    with tempfile.TemporaryDirectory() as td_str:
        td = Path(td_str)
        df_players_gw.to_parquet(td / "players.parquet", index=False)
        fixtures_pit.to_parquet(td / "fixtures.parquet", index=False)
        clubs_all.to_parquet(td / "clubs.parquet", index=False)
        gws_all.to_parquet(td / "gameweeks.parquet", index=False)
        perfs_lt.to_parquet(td / "player_performances.parquet", index=False)

        fit_hist = load_fit_history(td, gw)
        if gw > 1:
            assert fit_hist is not None and int(fit_hist["gameweek_id"].max()) < gw
        model = DefXgShrinkChallengerModel()
        model.fit(fit_hist if fit_hist is not None else pd.DataFrame())

        df_feat_base = build_features(
            td,
            gw,
            horizon=horizon,
            seed_processed_dir=seed_dir,
            history_before_gw=gw,
            as_of_gw=None,
        )

        pred_l1 = model.predict(df_feat_base, horizon)
        agg_l1 = pred_l1.groupby(["player_id", "gameweek_id"], as_index=False).agg(
            L1_native_mins=("projected_minutes", "sum"),
            L1_native_pts=("projected_points", "sum"),
        )
        native_mins_map = {
            (int(r["player_id"]), int(r["gameweek_id"])): float(r["L1_native_mins"])
            for _, r in agg_l1.iterrows()
        }

        ref_date = resolve_gw_reference_date(td, gw)
        merged = agg_l1.copy()

        for arm_name, cfg in arm_configs.items():
            if arm_name == "L1_native":
                continue
            if arm_name == "L1_L3b_shield":
                sh_path = synthesize_xmins_override(
                    td, gw, horizon, base_csv_path=None, include_broad_pool_shield=True,
                    reference_date=ref_date, output_path=td / "shield.csv",
                )
                xmins_map = load_xmins_override(sh_path, planning_gws)
            else:
                assert cfg is not None
                xmins_map = compute_internal_xmins_from_tables(
                    df_players_gw,
                    fixtures_pit,
                    perfs_lt,
                    gw,
                    horizon,
                    native_mins_map=native_mins_map,
                    seed_perfs=seed_perfs,
                    seed_players=seed_players,
                    reference_date=ref_date,
                    config=cfg,
                )

            df_feat_arm = _apply_xmins_override_to_features(df_feat_base, xmins_map)
            pred_arm = model.predict(df_feat_arm, horizon)
            agg_arm = pred_arm.groupby(["player_id", "gameweek_id"], as_index=False).agg(
                projected_minutes=("projected_minutes", "sum"),
                projected_points=("projected_points", "sum"),
            ).rename(columns={
                "projected_minutes": f"{arm_name}_mins",
                "projected_points": f"{arm_name}_pts",
            })
            merged = merged.merge(agg_arm, on=["player_id", "gameweek_id"], how="left")

    meta_cols = df_players_gw[["id", "web_name", "position_id", "club_id", "now_cost", "status", "chance_of_playing_next_round"]].rename(
        columns={"id": "player_id"}
    )
    merged = merged.merge(meta_cols, on="player_id", how="left")
    merged = merged.merge(realized, on=["player_id", "gameweek_id"], how="left")
    merged["actual_minutes"] = merged["actual_minutes"].fillna(0.0)
    merged["actual_starts"] = merged["actual_starts"].fillna(0.0)
    merged["actual_points"] = merged["actual_points"].fillna(0.0)

    prior_3 = perfs_lt[perfs_lt["gameweek_id"] >= gw - 3]
    last_1 = perfs_lt[perfs_lt["gameweek_id"] == gw - 1]
    h_all = perfs_lt.groupby("player_id", as_index=False).agg(prior_starts_all=("starts", "sum"))
    h_3 = prior_3.groupby("player_id", as_index=False).agg(starts_last3=("starts", "sum"), mins_last3=("minutes", "sum"))
    h_1 = last_1.groupby("player_id", as_index=False).agg(mins_last1=("minutes", "sum"))
    merged = merged.merge(h_all, on="player_id", how="left").merge(h_3, on="player_id", how="left").merge(h_1, on="player_id", how="left")
    for c in ("prior_starts_all", "starts_last3", "mins_last3", "mins_last1"):
        merged[c] = merged[c].fillna(0.0)

    raw_ch = pd.to_numeric(merged["chance_of_playing_next_round"], errors="coerce")
    is_flagged = (merged["status"].astype(str) != "a") | (raw_ch.notna() & (raw_ch < 100.0))
    merged["segment"] = np.where(
        is_flagged,
        "Flagged_API",
        np.where(
            (merged["mins_last1"] == 0.0) & (merged["prior_starts_all"] >= 1.0),
            "Returning_or_Absent_Last1",
            np.where(
                merged["starts_last3"] >= 2.0,
                "Established_Starter",
                np.where(merged["mins_last3"] > 0.0, "Rotation_or_Sub", "Deep_Bench_or_New"),
            ),
        ),
    )
    merged["issue_gw"] = gw
    merged["lead_step"] = merged["gameweek_id"] - gw

    t0 = merged[merged["lead_step"] == 0]
    fix_counts = fixtures_pit[fixtures_pit["gameweek_id"] == gw]
    active_clubs = set(fix_counts["home_club_id"].astype(int)) | set(fix_counts["away_club_id"].astype(int))
    t0_active = t0[t0["club_id"].isin(active_clubs)]
    mins_cols = [f"{a}_mins" for a in arm_configs] + ["actual_minutes"]
    cg = t0_active.groupby("club_id", as_index=False)[mins_cols].sum()
    club_nfix: dict[int, int] = {}
    for _, fr in fix_counts.iterrows():
        for col in ("home_club_id", "away_club_id"):
            cid = int(fr[col])
            club_nfix[cid] = club_nfix.get(cid, 0) + 1
    cg["n_fix"] = cg["club_id"].map(club_nfix).fillna(1).astype(float)
    for mc in mins_cols:
        cg[mc] = cg[mc] / (90.0 * cg["n_fix"])
    cg["issue_gw"] = gw
    return gw, merged, cg


def run_season_evaluation(
    season: str,
    seed_season: str,
    arm_configs: dict[str, InternalXminsConfig | None],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run GW1..38 causal point-in-time evaluation across specified arms in parallel."""
    max_workers = min(8, os.cpu_count() or 4)
    results_by_gw: dict[int, tuple[pd.DataFrame, pd.DataFrame]] = {}

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_evaluate_single_gw, season, seed_season, gw, arm_configs): gw
            for gw in range(1, 39)
        }
        done_count = 0
        for fut in as_completed(futures):
            gw_done, merged, cg = fut.result()
            results_by_gw[gw_done] = (merged, cg)
            done_count += 1
            if done_count % 10 == 0 or done_count == 38:
                print(f"[{season}] Completed {done_count}/38 GWs (workers={max_workers})", flush=True)

    ordered_gws = sorted(results_by_gw.keys())
    full_df = pd.concat([results_by_gw[gw][0] for gw in ordered_gws], ignore_index=True)
    club_df = pd.concat([results_by_gw[gw][1] for gw in ordered_gws], ignore_index=True)

    t0_df = full_df[full_df["lead_step"] == 0].copy()
    summary_rows = []
    for arm_name in arm_configs:
        mc, pc = f"{arm_name}_mins", f"{arm_name}_pts"
        m_t0 = compute_arm_metrics(t0_df, mc, pc)
        m_t02 = compute_arm_metrics(full_df, mc, pc)

        df_xi = t0_df[["issue_gw", "player_id", "position_id", "now_cost", "club_id", "actual_points", "actual_minutes", pc]].rename(
            columns={"issue_gw": "gameweek", pc: "projected_points"}
        )
        regrets = []
        tot_xi_pts = 0.0
        for _, grp in df_xi.groupby("gameweek"):
            _, reg, _ = _formation_xi_stats(grp, target_column="actual_points", budget_cap=1000.0, max_per_club=3)
            opt_xi, _ = select_squad_and_formation_xi(grp, "actual_points", squad_budget=1000.0, bench_weight=0.0, max_per_club=3)
            regrets.append(reg)
            tot_xi_pts += float(opt_xi["actual_points"].sum()) - reg

        summary_rows.append({
            "season": season,
            "arm": arm_name,
            "t0_mins_mae": m_t0["mins_mae"],
            "t0_mins_rmse": m_t0["mins_rmse"],
            "t0_mins_bias": m_t0["mins_bias"],
            "t0_false_start_pct": m_t0["false_start_pct"],
            "t0_missed_starter_pct": m_t0["missed_starter_pct"],
            "t0_xp_mae": m_t0["xp_mae"],
            "t0_xp_rmse": m_t0["xp_rmse"],
            "t02_mins_mae": m_t02["mins_mae"],
            "t02_mins_rmse": m_t02["mins_rmse"],
            "t02_mins_bias": m_t02["mins_bias"],
            "club_x90_mean": float(club_df[mc].mean()),
            "club_x90_std": float(club_df[mc].std()),
            "actual_club_x90_mean": float(club_df["actual_minutes"].mean()),
            "xi_total_pts": tot_xi_pts,
            "xi_mean_regret": float(np.mean(regrets)),
        })

    seg_rows = []
    for seg_name in ("Flagged_API", "Returning_or_Absent_Last1", "Established_Starter", "Rotation_or_Sub", "Deep_Bench_or_New"):
        sub = t0_df[t0_df["segment"] == seg_name]
        for arm_name in arm_configs:
            m = compute_arm_metrics(sub, f"{arm_name}_mins", f"{arm_name}_pts")
            seg_rows.append({
                "season": season, "slice_type": "segment", "slice_val": seg_name,
                "arm": arm_name, "n": int(m["n"]),
                "mins_mae": m["mins_mae"], "mins_bias": m["mins_bias"],
            })
    for pos_id, pname in POS_NAMES.items():
        sub = t0_df[t0_df["position_id"] == pos_id]
        for arm_name in arm_configs:
            m = compute_arm_metrics(sub, f"{arm_name}_mins", f"{arm_name}_pts")
            seg_rows.append({
                "season": season, "slice_type": "position", "slice_val": pname,
                "arm": arm_name, "n": int(m["n"]),
                "mins_mae": m["mins_mae"], "mins_bias": m["mins_bias"],
            })

    return pd.DataFrame(summary_rows), pd.DataFrame(seg_rows)


def main() -> None:
    print("=== Step 1: S-1 (2025-26) Pre-Deadline Chance Calibration ===", flush=True)
    cal = save_s1_chance_calibration()
    print(cal[cal["t"] == 0].to_string(index=False, float_format=lambda x: f"{x:6.3f}"), flush=True)

    s1_arms: dict[str, InternalXminsConfig | None] = {
        "L1_native": None,
        "L1_L3b_shield": None,
        "Solo_M1_gkp": InternalXminsConfig(True, False, False, False),
        "Solo_M2_recovery": InternalXminsConfig(False, True, False, False),
        "Solo_M3_avail_ramp": InternalXminsConfig(False, False, True, False),
        "Solo_M4_club_reconcile": InternalXminsConfig(False, False, False, True),
        "Cum_M1_M2": InternalXminsConfig(True, True, False, False),
        "Cum_M1_M2_M3": InternalXminsConfig(True, True, True, False),
        "M1_M3_M4": InternalXminsConfig(True, False, True, True),
        "Full_M1_M2_M3_M4": InternalXminsConfig(True, True, True, True),
    }

    print("\n=== Step 2: S-1 (2025-26) 38-GW Ablation ===", flush=True)
    s1_sum, s1_seg = run_season_evaluation("2025-26", "2024-25", s1_arms)
    s1_sum.to_csv(OUT_DIR / "s1_ablation_summary.csv", index=False)
    s1_seg.to_csv(OUT_DIR / "s1_segment_summary.csv", index=False)
    print(s1_sum.to_string(index=False, float_format=lambda x: f"{x:6.3f}"), flush=True)

    # Prefer M1_M3_M4 when M2 fails solo or M1_M3_M4 beats/matches Full_M1_M2_M3_M4
    m134_row = s1_sum[s1_sum["arm"] == "M1_M3_M4"].iloc[0]
    full_row = s1_sum[s1_sum["arm"] == "Full_M1_M2_M3_M4"].iloc[0]
    winner_arm = (
        "M1_M3_M4"
        if (m134_row["t0_mins_mae"] <= full_row["t0_mins_mae"] + 0.05 and m134_row["xi_mean_regret"] <= full_row["xi_mean_regret"])
        else "Full_M1_M2_M3_M4"
    )
    print(f"\nFrozen S-1 winner selected for S-2 cross-check: {winner_arm}", flush=True)

    s2_arms: dict[str, InternalXminsConfig | None] = {
        "L1_native": None,
        "L1_L3b_shield": None,
        "M1_M3_M4": s1_arms["M1_M3_M4"],
        "Full_M1_M2_M3_M4": s1_arms["Full_M1_M2_M3_M4"],
    }

    print("\n=== Step 3: S-2 (2024-25) Untuned 38-GW Cross-Check ===", flush=True)
    s2_sum, s2_seg = run_season_evaluation("2024-25", "2023-24", s2_arms)
    s2_sum["is_frozen_s1_winner"] = s2_sum["arm"] == winner_arm
    s2_sum.to_csv(OUT_DIR / "s2_crosscheck_summary.csv", index=False)
    s2_seg.to_csv(OUT_DIR / "s2_segment_summary.csv", index=False)
    print(s2_sum.to_string(index=False, float_format=lambda x: f"{x:6.3f}"), flush=True)


if __name__ == "__main__":
    main()
