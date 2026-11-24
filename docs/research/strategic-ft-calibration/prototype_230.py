"""Issue #230 Prototype: Static FT Plateau vs Early-Season (GW1-8) Regime + Live GW12-21 Sensitivity."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
from pathlib import Path
import sys
import time
from typing import Any

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
REPO = SCRIPT_DIR.parents[2]
for _p in (str(REPO), str(SCRIPT_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from backtesting.rolling_replay import DEFAULT_CERTIFIED_TIME_LIMIT_SECONDS  # noqa: E402
from commands.solve import build_my_data_from_parquet  # noqa: E402
from models.participation_state_hybrid import target_to_states  # noqa: E402
from projections.expected_gw_score import _POS_ID, PlayerGw  # noqa: E402
from runner import (  # noqa: E402
    DEFAULT_CACHE_ROOT,
    DIMINISHING_RATIOS,
    OUTPUT_DIR,
    FTConfigSpec,
    _append_partial_jsonl,
    _load_partial_jsonl,
    _run_worker,
    compute_ft_hurdles,
    compute_wasted_ft,
    prepare_season_cache,
)
from solver.scenarios import (  # noqa: E402
    annotate_plan_with_egs,
    apply_scenario_arm,
    effective_horizon_scale,
)
from solver.solver import prep_data, solve_multi_period_fpl  # noqa: E402
from solver.transfer_plan import serialize_transfer_plan  # noqa: E402
from solver.utils import load_settings  # noqa: E402

LIVE_TARGET_GW = 12
LIVE_HORIZON = 10
LIVE_DATASOURCE = "def_xg_shrink_challenger"
REQUIRED_BASELINES = {"2025-26": 2167, "2024-25": 2299}
INCLUDED_STAGE2_IDS = ("baseline_adr0065", "v2_2p0_h_0p15_u_0p4")


def build_proto230_configs() -> list[FTConfigSpec]:
    """Return the 5 new certified runs for #230 (3 flat upper-plateau + 2 GW1-8 two-phase)."""
    return [
        # Flat static upper plateau candidates (<4.0 strict and <=1.76 below H=10 hit hurdle)
        FTConfigSpec(
            config_id="v2_3p2_h_0p00_u_0p5",
            v2=3.2,
            spare_ft_hold_weight=0.0,
            ft_use_penalty=0.5,
        ),
        FTConfigSpec(
            config_id="v2_2p4_h_0p08_u_0p6",
            v2=2.4,
            spare_ft_hold_weight=0.08,
            ft_use_penalty=0.6,
        ),
        FTConfigSpec(
            config_id="v2_2p4_h_0p15_u_0p6",
            v2=2.4,
            spare_ft_hold_weight=0.15,
            ft_use_penalty=0.6,
        ),
        # Two-phase GW1-8 vs GW9+ regimes (both phases strictly < 4.0 permanent hurdle)
        FTConfigSpec(
            config_id="twophase_early_hi_late_mid",
            v2=2.0,
            spare_ft_hold_weight=0.08,
            ft_use_penalty=0.4,
            early_gw_end=8,
            early_v2=2.0,
            early_spare_ft_hold_weight=0.15,
            early_ft_use_penalty=0.4,
        ),
        FTConfigSpec(
            config_id="twophase_early_lo_late_hi",
            v2=2.0,
            spare_ft_hold_weight=0.15,
            ft_use_penalty=0.4,
            early_gw_end=8,
            early_v2=1.6,
            early_spare_ft_hold_weight=0.0,
            early_ft_use_penalty=0.2,
        ),
    ]


def build_live_sensitivity_configs() -> list[FTConfigSpec]:
    """Return the 5 static schedules compared on live pre-deadline GW12-21 (H=10)."""
    return [
        FTConfigSpec(
            config_id="baseline_adr0065",
            v2=2.0,
            spare_ft_hold_weight=0.325,
            ft_use_penalty=0.5,
            baseline_mode=True,
            waive_chip_ft_hold=False,
        ),
        FTConfigSpec(
            config_id="v2_2p0_h_0p15_u_0p4",
            v2=2.0,
            spare_ft_hold_weight=0.15,
            ft_use_penalty=0.4,
        ),
        *build_proto230_configs()[:3],
    ]


def build_live_h10_options(
    base_options: dict[str, Any],
    spec: FTConfigSpec,
    *,
    free_transfer_bank: int,
    target_gw: int = LIVE_TARGET_GW,
    horizon: int = LIVE_HORIZON,
    decay_base: float = 0.85,
) -> dict[str, Any]:
    """Assemble in-memory live Strategic H=10 options without touching production files."""
    opts = apply_scenario_arm(
        base_options,
        "strategic",
        start_gw=target_gw,
        free_transfer_bank=free_transfer_bank,
        horizon=horizon,
        decay_base=decay_base,
    )
    if spec.baseline_mode:
        scale = effective_horizon_scale(horizon, decay_base=decay_base)
        opts["ft_value_list"] = {
            k: round(float(v) * scale, 4)
            for k, v in (("2", 2.0), ("3", 1.2), ("4", 0.6), ("5", 0.2))
        }
        opts["ft_use_penalty"] = 0.5
        opts["spare_ft_hold_weight"] = round(0.325 / scale, 4)
        return opts

    opts["ft_value_list"] = {
        k: round(float(spec.v2) * mult, 4) for k, mult in DIMINISHING_RATIOS.items()
    }
    opts["ft_use_penalty"] = float(spec.ft_use_penalty)
    opts["spare_ft_hold_weight"] = float(spec.spare_ft_hold_weight)
    return opts


def _build_player_gw_lookup(csv_path: Path, gws: list[int]) -> dict[tuple[int, int], PlayerGw]:
    """Load PlayerGw expected points + appearance probabilities for EGS annotation."""
    csv_df = pd.read_csv(csv_path)
    id_col = "ID" if "ID" in csv_df.columns else "id"
    pos_col = "Pos" if "Pos" in csv_df.columns else "pos"
    lookup: dict[tuple[int, int], PlayerGw] = {}
    for _, r in csv_df.iterrows():
        pid = int(r[id_col])
        pos_id = _POS_ID.get(str(r.get(pos_col)), 3)
        for gw in gws:
            pts = float(r.get(f"{gw}_Pts") or 0.0)
            xmins = float(r.get(f"{gw}_xMins") or 0.0)
            p_start, p_sub_in, _p_dnp, _sm, _subm = target_to_states(xmins)
            p_app = max(0.0, min(1.0, p_start + p_sub_in))
            lookup[(pid, gw)] = PlayerGw(player_id=pid, position_id=pos_id, xp=pts, p_appear=p_app)
    return lookup


def _run_live_specs(
    specs: list[FTConfigSpec],
    *,
    summary_path: Path,
    weekly_path: Path,
    target_gw: int = LIVE_TARGET_GW,
    horizon: int = LIVE_HORIZON,
    datasource: str = LIVE_DATASOURCE,
    secs: int = 180,
    config_id_suffix: str = "",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Execute read-only live H=10 solves across `specs` without mutating data/."""
    bootstrap_path = REPO / "data/raw/bootstrap_static.json"
    fixtures_path = REPO / "data/raw/fixtures_all.json"
    if not bootstrap_path.is_file() or not fixtures_path.is_file():
        raise FileNotFoundError(
            "Missing local data/raw/bootstrap_static.json or fixtures_all.json; cannot run offline."
        )
    fpl_bootstrap = json.loads(bootstrap_path.read_text(encoding="utf-8"))
    fpl_fixtures = json.loads(fixtures_path.read_text(encoding="utf-8"))
    id_to_name = {int(el["id"]): str(el["web_name"]) for el in fpl_bootstrap["elements"]}

    csv_path = REPO / "data" / f"{datasource}.csv"
    if not csv_path.is_file():
        raise FileNotFoundError(f"Missing live forecast CSV: {csv_path}")
    csv_cols = set(pd.read_csv(csv_path, nrows=1).columns)
    gws = list(range(target_gw, min(39, target_gw + horizon)))
    missing_cols = [
        col for gw in gws for col in (f"{gw}_Pts", f"{gw}_xMins") if col not in csv_cols
    ]
    if missing_cols:
        raise ValueError(f"Forecast CSV {csv_path} missing columns: {missing_cols}")

    processed_dir = REPO / "data/processed"
    my_data = build_my_data_from_parquet(processed_dir)
    free_transfer_bank = int(my_data["transfers"]["limit"] or 1)
    lookup = _build_player_gw_lookup(csv_path, gws)

    base_options = load_settings()
    base_options.update(
        {
            "horizon": horizon,
            "decay_base": 0.85,
            "override_next_gw": target_gw,
            "datasource": datasource,
            "gap": 0.0,
            "secs": secs,
            "verbose": False,
            "use_wc": [],
            "use_bb": [],
            "use_fh": [],
            "use_tc": [],
            "banned": [],
            "locked": [],
            "fpl_bootstrap": fpl_bootstrap,
            "fpl_fixtures": fpl_fixtures,
        }
    )

    summary_rows: list[dict[str, Any]] = []
    weekly_rows: list[dict[str, Any]] = []

    for spec in specs:
        t0 = time.perf_counter()
        opts = build_live_h10_options(
            base_options,
            spec,
            free_transfer_bank=free_transfer_bank,
            target_gw=target_gw,
            horizon=horizon,
            decay_base=0.85,
        )
        solver_data = prep_data(my_data, opts)
        solutions = solve_multi_period_fpl(solver_data, opts)
        if not solutions:
            raise RuntimeError(f"Live solve returned no solution for {spec.config_id}")
        best_sol = solutions[0]
        plan = serialize_transfer_plan(
            best_sol,
            champion=datasource,
            horizon=horizon,
            next_gw=target_gw,
            decay_base=0.85,
            booked_chips={"use_wc": [], "use_bb": [], "use_fh": [], "use_tc": []},
        )
        annotated = annotate_plan_with_egs(plan, lookup)
        solve_secs = round(time.perf_counter() - t0, 2)

        weeks = annotated.get("weeks") or []
        hurdles = compute_ft_hurdles(
            spec.v2,
            spec.spare_ft_hold_weight,
            spec.ft_use_penalty,
            decay_base=0.85,
            scale_ft_by_horizon=spec.baseline_mode,
        )
        w0 = weeks[0] if weeks else {}
        w0_buys = [str(b["name"]) for b in (w0.get("buy") or [])]
        w0_sells = [str(s["name"]) for s in (w0.get("sell") or [])]
        w0_moves = (
            f"+{', '.join(w0_buys)} / -{', '.join(w0_sells)}"
            if (w0_buys or w0_sells)
            else "Roll FT"
        )
        ft_banks = [int(round(float(w.get("ft") or 0))) for w in weeks]
        wasted = sum(
            compute_wasted_ft(
                "2026-27",
                int(w["gw"]),
                int(round(float(w.get("ft") or 0))),
                int(round(float(w.get("transfer_count") or 0))),
                None,
            )
            for w in weeks
        )
        rel_gap = best_sol.get("solver_rel_gap")
        rel_gap_val = float(rel_gap) if rel_gap is not None else 0.0
        cid = f"{spec.config_id}{config_id_suffix}"
        summary_rows.append(
            {
                "config_id": cid,
                "baseline_mode": spec.baseline_mode,
                "v2": spec.v2,
                "spare_ft_hold_weight": spec.spare_ft_hold_weight,
                "ft_use_penalty": spec.ft_use_penalty,
                "perm_hurdle_h10": hurdles["perm_hurdle_h10"],
                "delay1_h10": hurdles["delay1_h10"],
                "gate_hurdle_lt4": hurdles["gate_hurdle_lt4"],
                "solver_objective": round(float(best_sol.get("score") or 0.0), 4),
                "total_xp": round(float(best_sol.get("total_xp") or 0.0), 4),
                "horizon_egs": round(float(annotated.get("horizon_egs") or 0.0), 4),
                "gw12_transfers": int(round(float(w0.get("transfer_count") or 0))),
                "gw12_hits": int(round(float(w0.get("hits") or 0))),
                "gw12_moves": w0_moves,
                "total_transfers_10gw": sum(
                    int(round(float(w.get("transfer_count") or 0))) for w in weeks
                ),
                "total_hits_10gw": sum(int(round(float(w.get("hits") or 0))) for w in weeks),
                "avg_ft_bank": round(sum(ft_banks) / float(len(ft_banks)), 4) if ft_banks else 0.0,
                "min_ft_bank": min(ft_banks) if ft_banks else 0,
                "max_ft_bank": max(ft_banks) if ft_banks else 0,
                "wasted_fts": int(wasted),
                "solver_model_status": str(best_sol.get("solver_model_status") or "Optimal"),
                "relative_gap": round(rel_gap_val, 6),
                "solve_seconds": solve_secs,
            }
        )
        for w in weeks:
            cap_id = w.get("captain_id")
            weekly_rows.append(
                {
                    "config_id": cid,
                    "gw": int(w["gw"]),
                    "pre_ft": int(round(float(w.get("ft") or 0))),
                    "transfers": int(round(float(w.get("transfer_count") or 0))),
                    "hits": int(round(float(w.get("hits") or 0))),
                    "post_ft": int(round(float(w.get("ft_after") or 0))),
                    "gw_xp": round(float(w.get("xp") or 0.0), 4),
                    "gw_egs": round(float(w.get("expected_gw_score") or 0.0), 4),
                    "buys": "; ".join(str(b["name"]) for b in (w.get("buy") or [])),
                    "sells": "; ".join(str(s["name"]) for s in (w.get("sell") or [])),
                    "captain": id_to_name.get(int(cap_id), str(cap_id)) if cap_id is not None else "",
                }
            )
        print(
            f"[Live GW12-21] {cid}: EGS={summary_rows[-1]['horizon_egs']:.2f} "
            f"xP={summary_rows[-1]['total_xp']:.2f} tr10={summary_rows[-1]['total_transfers_10gw']} "
            f"hits10={summary_rows[-1]['total_hits_10gw']} waste={wasted} "
            f"GW12='{w0_moves}' ({solve_secs}s)",
            flush=True,
        )

    summary_df = pd.DataFrame(summary_rows)
    weekly_df = pd.DataFrame(weekly_rows)
    summary_df.to_csv(summary_path, index=False)
    weekly_df.to_csv(weekly_path, index=False)
    return summary_df, weekly_df


def run_live_sensitivity(
    *,
    target_gw: int = LIVE_TARGET_GW,
    horizon: int = LIVE_HORIZON,
    datasource: str = LIVE_DATASOURCE,
    secs: int = 180,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run read-only live GW12-21 sensitivity across 5 FT schedules without mutating data/."""
    return _run_live_specs(
        build_live_sensitivity_configs(),
        summary_path=OUTPUT_DIR / "live_gw12_21_sensitivity.csv",
        weekly_path=OUTPUT_DIR / "live_gw12_21_weekly.csv",
        target_gw=target_gw,
        horizon=horizon,
        datasource=datasource,
        secs=secs,
    )


def run_b2_overflow_guard_check(
    *,
    target_gw: int = LIVE_TARGET_GW,
    horizon: int = LIVE_HORIZON,
    datasource: str = LIVE_DATASOURCE,
    secs: int = 180,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Test Option B2 (v2=2.4, w_hold=0.15, u=0.6) under production 5-FT cap-overflow waiver."""
    b2 = next(s for s in build_proto230_configs() if s.config_id == "v2_2p4_h_0p15_u_0p6")
    return _run_live_specs(
        [b2],
        summary_path=OUTPUT_DIR / "live_gw12_21_b2_cap_guard.csv",
        weekly_path=OUTPUT_DIR / "live_gw12_21_b2_cap_guard_weekly.csv",
        target_gw=target_gw,
        horizon=horizon,
        datasource=datasource,
        secs=secs,
        config_id_suffix="_cap_guard",
    )


def _load_existing_stage2_references() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Load already-certified baseline_adr0065 and v2_2p0_h_0p15_u_0p4 rows from #229."""
    stage2_df = pd.read_csv(OUTPUT_DIR / "stage2_certified_finalists.csv")
    stage2_df = stage2_df[stage2_df["config_id"].isin(INCLUDED_STAGE2_IDS)].copy()
    for col, default in (
        ("early_gw_end", 0),
        ("early_v2", None),
        ("early_spare_ft_hold_weight", None),
        ("early_ft_use_penalty", None),
        ("early_perm_hurdle_h6", None),
        ("early_perm_hurdle_h10", None),
    ):
        if col not in stage2_df.columns:
            stage2_df[col] = default
    traj_df = pd.read_csv(OUTPUT_DIR / "stage2_gw_trajectories.csv")
    traj_df = traj_df[traj_df["config_id"].isin(INCLUDED_STAGE2_IDS)].copy()
    return stage2_df.to_dict(orient="records"), traj_df.to_dict(orient="records")


def run_historical_proto230(
    *,
    workers: int = 5,
    cache_root: Path = DEFAULT_CACHE_ROOT,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run certified 2-season shootout comparing upper-plateau static vs GW1-8 two-phase."""
    t0 = time.perf_counter()
    print("Preparing cached inputs for 2025-26 and 2024-25...", flush=True)
    prepare_season_cache("2025-26", cache_root=cache_root)
    prepare_season_cache("2024-25", cache_root=cache_root)

    ref_summaries, ref_gws = _load_existing_stage2_references()
    new_configs = build_proto230_configs()
    by_id = {c.config_id: c for c in new_configs}

    partial_path = cache_root / "proto230_partial.jsonl"
    prior = {
        (r["summary"]["season"], r["summary"]["config_id"]): r
        for r in _load_partial_jsonl(partial_path)
    }
    rows: list[dict[str, Any]] = list(ref_summaries) + [v["summary"] for v in prior.values()]
    gw_rows: list[dict[str, Any]] = list(ref_gws) + [
        g for v in prior.values() for g in v["gws"]
    ]

    pending = [
        (by_id[c.config_id], season, cache_root, 0.0, DEFAULT_CERTIFIED_TIME_LIMIT_SECONDS, True)
        for season in ("2025-26", "2024-25")
        for c in new_configs
        if (season, c.config_id) not in prior
    ]
    print(
        f"Proto #230 certified historical: {len(pending)} pending / {2 * len(new_configs)} new runs "
        f"(gap=0.0, limit=600s, workers={workers})...",
        flush=True,
    )
    if pending:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futs = {pool.submit(_run_worker, t): (t[1], t[0].config_id) for t in pending}
            for fut in as_completed(futs):
                summary, gws = fut.result()
                rows.append(summary)
                gw_rows.extend(gws)
                _append_partial_jsonl(partial_path, {"summary": summary, "gws": gws})
                print(
                    f"[Proto #230] {summary['season']} {summary['config_id']}: "
                    f"net={summary['total_net_points']} early={summary['early_gw2_12_net']} "
                    f"waste={summary['wasted_fts']} optimal={summary['all_optimal']} "
                    f"({summary['wall_seconds']}s)",
                    flush=True,
                )

    df = pd.DataFrame(rows)
    baselines = (
        df[df["config_id"] == "baseline_adr0065"]
        .set_index("season")["total_net_points"]
        .to_dict()
    )
    if baselines != REQUIRED_BASELINES:
        raise AssertionError(f"Baseline parity mismatch: expected {REQUIRED_BASELINES}, got {baselines}")

    base_early = (
        df[df["config_id"] == "baseline_adr0065"]
        .set_index("season")["early_gw2_12_net"]
        .to_dict()
    )
    df["regime_type"] = df.apply(
        lambda r: (
            "baseline"
            if bool(r["baseline_mode"])
            else ("twophase_gw1_8" if int(r.get("early_gw_end") or 0) > 0 else "static_unscaled")
        ),
        axis=1,
    )
    df["delta_vs_baseline_net"] = df.apply(
        lambda r: int(r["total_net_points"]) - int(baselines[r["season"]]),
        axis=1,
    )
    df["delta_vs_baseline_early_gw2_12"] = df.apply(
        lambda r: int(r["early_gw2_12_net"]) - int(base_early[r["season"]]),
        axis=1,
    )

    strict_static = df[(df["regime_type"] == "static_unscaled") & (df["hard_gates_pass"])]
    best_static_by_season = (
        strict_static.groupby("season")["total_net_points"].max().to_dict()
        if not strict_static.empty
        else {}
    )
    df["delta_vs_best_strict_static_net"] = df.apply(
        lambda r: (
            int(r["total_net_points"]) - int(best_static_by_season[r["season"]])
            if r["season"] in best_static_by_season
            else 0
        ),
        axis=1,
    )

    # Evaluate Q9 two-phase parsimony gate: >= +10 on S-1 (2025-26) AND > 0 on S-2 (2024-25)
    two_s1 = df[(df["regime_type"] == "twophase_gw1_8") & (df["season"] == "2025-26")].set_index("config_id")
    two_s2 = df[(df["regime_type"] == "twophase_gw1_8") & (df["season"] == "2024-25")].set_index("config_id")
    q9_pass: dict[str, bool] = {}
    for cid in two_s1.index:
        if cid in two_s2.index:
            ok = bool(
                two_s1.loc[cid, "hard_gates_pass"]
                and two_s2.loc[cid, "hard_gates_pass"]
                and int(two_s1.loc[cid, "delta_vs_best_strict_static_net"]) >= 10
                and int(two_s2.loc[cid, "delta_vs_best_strict_static_net"]) > 0
            )
            q9_pass[str(cid)] = ok
    df["q9_twophase_parsimony_pass"] = df["config_id"].map(lambda c: q9_pass.get(str(c), False))

    df = df.sort_values(
        by=["season", "delta_vs_baseline_net", "config_id"],
        ascending=[False, False, True],
    )
    out_summary = OUTPUT_DIR / "proto230_static_vs_twophase.csv"
    df.to_csv(out_summary, index=False)

    traj_df = pd.DataFrame(gw_rows).sort_values(
        by=["season", "config_id", "gameweek"],
        ascending=[False, True, True],
    )
    out_traj = OUTPUT_DIR / "proto230_gw_trajectories.csv"
    traj_df.to_csv(out_traj, index=False)
    print(f"Wrote {out_summary} ({len(df)} rows) and {out_traj} ({len(traj_df)} rows) in {time.perf_counter() - t0:.1f}s", flush=True)
    return df, traj_df


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=("live", "historical", "all", "b2_guard"),
        default="all",
    )
    parser.add_argument("--workers", type=int, default=5)
    parser.add_argument("--cache-root", type=Path, default=DEFAULT_CACHE_ROOT)
    args = parser.parse_args()
    if args.mode in ("live", "all"):
        run_live_sensitivity()
    if args.mode == "b2_guard":
        run_b2_overflow_guard_check()
    if args.mode in ("historical", "all"):
        run_historical_proto230(workers=args.workers, cache_root=args.cache_root)


if __name__ == "__main__":
    main()
