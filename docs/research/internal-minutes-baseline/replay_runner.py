"""Canonical 6-GW rolling Strategic MILP replay comparing Broad Pool Shield vs Internal Minutes Baseline on S-1 and S-2."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
import json
import lzma
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
from typing import Any, cast

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
IDEATION_DIR = ROOT / "docs/research/candidate-ideation"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(IDEATION_DIR) not in sys.path:
    sys.path.insert(0, str(IDEATION_DIR))

from backtesting.native_transfer_solver import native_strategic_solve  # noqa: E402
from backtesting.ownership_anchor import OwnershipAnchor, UniverseSchema, solve_ownership_anchor  # noqa: E402
from backtesting.rolling_replay import (  # noqa: E402
    DEFAULT_CERTIFIED_TIME_LIMIT_SECONDS,
    DEFAULT_HORIZON,
    QualityPolicy,
    run_rolling_replay,
)
from backtesting.season_rules import Chip, get_rules  # noqa: E402
from commands.run_stage_a_and_b import _outcomes_for_gw  # noqa: E402
from features.availability_snapshots import resolve_latest_snapshot  # noqa: E402
from features.builder import build_features, load_xmins_override  # noqa: E402
from features.injury_triage import synthesize_xmins_override  # noqa: E402
from features.internal_xmins import InternalXminsConfig, compute_internal_xmins_from_tables  # noqa: E402
from historical_replay_inputs import stage_s1_inputs  # noqa: E402
from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel  # noqa: E402
from s2_historical_replay_inputs import stage_s2_inputs  # noqa: E402

OUT_DIR = Path(__file__).resolve().parent
CACHE_ROOT = ROOT / ".tmp/agent/internal-minutes-replay"
FROZEN_CFG = InternalXminsConfig(
    enable_gkp_role=True,
    enable_starter_recovery=False,
    enable_availability_ramp=True,
    enable_club_reconciliation=True,
)
ALLOWED_SEASONS = ("2025-26", "2024-25")


def _apply_xmins_override(df_feat: pd.DataFrame, xmins_map: dict[tuple[int, int], float]) -> pd.DataFrame:
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


def _bootstrap_meta_maps(season: str, gw: int) -> tuple[dict[int, str], dict[int, str]]:
    bp = ROOT / f"data/reports/empirical_mirrors/{season}/bootstraps/gw{gw:02d}.json.xz"
    payload = json.loads(lzma.open(bp, "rt", encoding="utf-8").read())
    news = {int(e["id"]): str(e.get("news") or "") for e in payload["elements"]}
    names = {int(e["id"]): str(e.get("web_name") or f"Player_{e['id']}") for e in payload["elements"]}
    return news, names


def _wide_from_long(wide_base: pd.DataFrame, projections: pd.DataFrame, targets: range) -> pd.DataFrame:
    wide = wide_base.copy()
    by_pg = projections.groupby(["player_id", "gameweek_id"])[["projected_points", "projected_minutes"]].sum()
    for target in targets:
        agg = by_pg.xs(target, level="gameweek_id")
        wide[f"{target}_Pts"] = wide["player_id"].map(agg["projected_points"]).astype(float)
        wide[f"{target}_xMins"] = wide["player_id"].map(agg["projected_minutes"]).astype(float)
        assert wide[f"{target}_Pts"].notna().all() and np.isfinite(wide[f"{target}_Pts"]).all()
        assert wide[f"{target}_xMins"].notna().all() and np.isfinite(wide[f"{target}_xMins"]).all()
    for col in ("player_id", "position_id", "club_id", "now_cost"):
        wide[col] = wide[col].astype(int)
    wide["purchase_eligible"] = wide["purchase_eligible"].astype(bool)
    return wide


def _build_gw_wide_forecasts(season: str, gw: int, deadline: str, seed_dir_str: str) -> int:
    season_dir = CACHE_ROOT / season
    shield_out = season_dir / "wide_shield" / f"gw{gw:02d}.parquet"
    internal_out = season_dir / "wide_internal" / f"gw{gw:02d}.parquet"
    if shield_out.is_file() and internal_out.is_file():
        return gw

    gw_dir = season_dir / "verified_inputs" / f"gw{gw:02d}"
    seed_dir = Path(seed_dir_str)
    horizon = min(DEFAULT_HORIZON, 39 - gw)
    targets = range(gw, gw + horizon)
    planning_gws = list(targets)

    df_feat_base = build_features(
        gw_dir,
        gw,
        horizon,
        use_archive_seed=False,
        seed_processed_dir=seed_dir,
        as_of_gw=gw,
        history_before_gw=gw,
        target_deadline=deadline,
        availability_snapshot_root=gw_dir / "snapshots",
        season=season,
        require_availability_snapshot=True,
        minutes_prior_source="seed_state",
    )
    history = pd.read_parquet(gw_dir / "player_performances.parquet")
    if not history.empty:
        assert int(history["gameweek_id"].max()) < gw

    model = DefXgShrinkChallengerModel()
    model.fit(history)
    pred_l1 = model.predict(df_feat_base, horizon)
    agg_l1 = pred_l1.groupby(["player_id", "gameweek_id"])["projected_minutes"].sum()
    native_mins_map = {(int(pid), int(g)): float(val) for (pid, g), val in agg_l1.items()}

    snapshot = resolve_latest_snapshot(gw_dir / "snapshots", season, gw, deadline)
    assert snapshot is not None
    snap_players = cast(pd.DataFrame, snapshot["players"]).copy()
    snap_fixtures = cast(pd.DataFrame, snapshot["fixtures"]).copy()
    news_map, name_map = _bootstrap_meta_maps(season, gw)
    snap_players["news"] = snap_players["id"].astype(int).map(news_map).fillna("")
    snap_players["web_name"] = snap_players["id"].astype(int).map(name_map).fillna("Unknown")
    ref_date = datetime.fromisoformat(deadline).date()

    # 1. Shield (L1_L3b_shield)
    with tempfile.TemporaryDirectory() as td_str:
        td = Path(td_str)
        snap_players.to_parquet(td / "players.parquet", index=False)
        snap_fixtures.to_parquet(td / "fixtures.parquet", index=False)
        history.to_parquet(td / "player_performances.parquet", index=False)
        sh_path = synthesize_xmins_override(
            td, gw, horizon, base_csv_path=None, include_broad_pool_shield=True,
            reference_date=ref_date, output_path=td / "shield.csv",
        )
        shield_map = load_xmins_override(sh_path, planning_gws)

    # 2. Internal Minutes Baseline (M1_M3_M4)
    seed_perfs = pd.read_parquet(seed_dir / "player_performances.parquet")
    seed_players = pd.read_parquet(seed_dir / "players.parquet")
    internal_map = compute_internal_xmins_from_tables(
        snap_players,
        snap_fixtures,
        history,
        gw,
        horizon,
        native_mins_map=native_mins_map,
        seed_perfs=seed_perfs,
        seed_players=seed_players,
        reference_date=ref_date,
        config=FROZEN_CFG,
    )

    wide_base = pd.read_parquet(
        gw_dir / "market.parquet",
        columns=["player_id", "position_id", "club_id", "now_cost", "purchase_eligible"],
    )

    pred_shield = model.predict(_apply_xmins_override(df_feat_base, shield_map), horizon)
    pred_internal = model.predict(_apply_xmins_override(df_feat_base, internal_map), horizon)

    shield_out.parent.mkdir(parents=True, exist_ok=True)
    internal_out.parent.mkdir(parents=True, exist_ok=True)
    _wide_from_long(wide_base, pred_shield, targets).to_parquet(shield_out, index=False)
    _wide_from_long(wide_base, pred_internal, targets).to_parquet(internal_out, index=False)
    return gw


def prepare_season(season: str) -> dict[str, Any]:
    season_dir = CACHE_ROOT / season
    meta_path = season_dir / "meta.json"
    ready = (
        meta_path.is_file()
        and all((season_dir / "wide_shield" / f"gw{gw:02d}.parquet").is_file() for gw in range(1, 39))
        and all((season_dir / "wide_internal" / f"gw{gw:02d}.parquet").is_file() for gw in range(1, 39))
    )
    if ready:
        return json.loads(meta_path.read_text(encoding="utf-8"))

    season_dir.mkdir(parents=True, exist_ok=True)
    manifest, seed_dir = stage_s1_inputs(season_dir) if season == "2025-26" else stage_s2_inputs(season_dir)
    anchor = solve_ownership_anchor(
        pd.read_parquet(season_dir / "verified_inputs/gw01/market.parquet"),
        season,
        gameweek=1,
        anchor_type="opening",
        schema=UniverseSchema(eligibility_col="purchase_eligible"),
    )
    deadlines = {int(o["gw"]): str(o["deadline_utc"]) for o in manifest["origins"]}
    calendar = [[int(r["gameweek"]), str(r["chip"])] for r in manifest["shared_chip_calendar"]]

    max_workers = min(8, os.cpu_count() or 4)
    print(f"[{season}] Precomputing GW1-38 wide forecasts (workers={max_workers})...", flush=True)
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futs = [executor.submit(_build_gw_wide_forecasts, season, gw, deadlines[gw], str(seed_dir)) for gw in range(1, 39)]
        done = 0
        for fut in as_completed(futs):
            fut.result()
            done += 1
            if done % 10 == 0 or done == 38:
                print(f"[{season}] Wide forecasts {done}/38 ready", flush=True)

    meta = {"season": season, "anchor": anchor.to_dict(), "chip_calendar": calendar}
    meta_path.write_text(json.dumps(meta, indent=2, sort_keys=True), encoding="utf-8")
    return meta


def run_replay_task(season: str, arm: str) -> dict[str, Any]:
    season_dir = CACHE_ROOT / season
    meta = json.loads((season_dir / "meta.json").read_text(encoding="utf-8"))
    anchor = OwnershipAnchor.from_dict(meta["anchor"])
    calendar = tuple((int(g), cast(Chip, str(c))) for g, c in meta["chip_calendar"])
    wide_subdir = "wide_shield" if arm == "L1_L3b_shield" else "wide_internal"
    wide_by_gw = {gw: pd.read_parquet(season_dir / wide_subdir / f"gw{gw:02d}.parquet") for gw in range(1, 39)}
    outcomes_by_gw = {gw: _outcomes_for_gw(season, gw) for gw in range(1, 39)}

    cp_dir = season_dir / "checkpoints" / arm
    t0 = time.perf_counter()
    traj = run_rolling_replay(
        arm,
        season,
        anchor,
        lambda gw, _state: wide_by_gw[gw],
        lambda gw: outcomes_by_gw[gw],
        horizon=DEFAULT_HORIZON,
        end_gw=38,
        solve_fn=native_strategic_solve,
        policy=QualityPolicy(mode="certified", target_gap=0.0, time_limit_seconds=DEFAULT_CERTIFIED_TIME_LIMIT_SECONDS),
        checkpoint_dir=cp_dir,
        model_version_hash=f"internal-minutes-baseline-{arm}",
        protocol_hash=f"{season}-strategic-h6",
        chip_calendar=calendar,
    )
    elapsed = round(time.perf_counter() - t0, 2)
    net_audit = traj.audit_reconstructed_net_score()
    assert len(traj.records) == 38
    assert all(r.execution_status == "SUCCESS" for r in traj.records)

    rules = get_rules(season)
    _ = rules
    optimal_gws = sum(1 for r in traj.records if r.certificate.termination_status == "OPTIMAL")
    total_transfers = sum(len(r.decision.transfers) for r in traj.records)
    hit_count = sum(int(r.hit_penalty // 4) for r in traj.records)

    gw1_4_net = sum(r.net_points for r in traj.records if 1 <= r.deadline <= 4)
    gw5_19_net = sum(r.net_points for r in traj.records if 5 <= r.deadline <= 19)
    gw20_38_net = sum(r.net_points for r in traj.records if 20 <= r.deadline <= 38)

    print(
        f"[{season} | {arm}] DONE in {elapsed:.1f}s | net={net_audit} (gross={traj.cumulative_gross}, hits={traj.cumulative_hits}) | opt={optimal_gws}/38",
        flush=True,
    )
    return {
        "season": season,
        "arm": arm,
        "cumulative_gross": int(traj.cumulative_gross),
        "cumulative_hits": int(traj.cumulative_hits),
        "cumulative_net": int(net_audit),
        "total_transfers": int(total_transfers),
        "hit_count": int(hit_count),
        "final_bank": int(traj.final_bank),
        "gw1_4_net": int(gw1_4_net),
        "gw5_19_net": int(gw5_19_net),
        "gw20_38_net": int(gw20_38_net),
        "optimal_gws": int(optimal_gws),
        "runtime_seconds": elapsed,
    }


def main() -> None:
    for season in ALLOWED_SEASONS:
        prepare_season(season)

    tasks = [(s, arm) for s in ALLOWED_SEASONS for arm in ("L1_L3b_shield", "Internal_M1_M3_M4")]
    print(f"\nLaunching {len(tasks)} parallel certified 38-GW Strategic rolling replays...", flush=True)
    rows: list[dict[str, Any]] = []
    with ProcessPoolExecutor(max_workers=min(4, os.cpu_count() or 2)) as executor:
        futs = [executor.submit(run_replay_task, s, arm) for s, arm in tasks]
        for fut in as_completed(futs):
            rows.append(fut.result())

    df = pd.DataFrame(rows).sort_values(["season", "arm"]).reset_index(drop=True)
    shield_nets = df[df["arm"] == "L1_L3b_shield"].set_index("season")["cumulative_net"].to_dict()
    df["delta_net_vs_shield"] = df.apply(lambda r: int(r["cumulative_net"]) - int(shield_nets[r["season"]]), axis=1)
    cols = [
        "season", "arm", "cumulative_gross", "cumulative_hits", "cumulative_net", "delta_net_vs_shield",
        "total_transfers", "hit_count", "final_bank", "gw1_4_net", "gw5_19_net", "gw20_38_net",
        "optimal_gws", "runtime_seconds",
    ]
    df = df[cols]
    out_csv = OUT_DIR / "rolling_replay_summary.csv"
    df.to_csv(out_csv, index=False)
    print("\n=== ROLLING REPLAY SUMMARY ===")
    print(df.to_string(index=False))

    if CACHE_ROOT.exists():
        shutil.rmtree(CACHE_ROOT)


if __name__ == "__main__":
    main()
