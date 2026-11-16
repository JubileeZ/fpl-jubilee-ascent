"""Execute real Stage A (~700-player Champion profiling) -> Stage B verification suites (#179, #189)."""

from __future__ import annotations

import hashlib
import json
import sys
import time
from dataclasses import asdict, replace
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import pandas as pd

REPO = Path("/home/jubileez/fpl-jubilee-ascent")
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

from backtesting.evidence_statistics import PairedGameweekScore, StatisticalProtocolConfig, evaluate_evidence_against_protocol
from backtesting.fplcache_ingest import _unpack_bootstrap_xz
from backtesting.native_transfer_solver import native_strategic_solve
from backtesting.ownership_anchor import UniverseSchema, solve_ownership_anchor
from backtesting.projection_guards import (
    ComponentLedger,
    declare_component_applicability,
    evaluate_non_inferiority_guard,
    reconcile_total_to_ledger,
)
from backtesting.promotion_evidence import MANDATORY_GUARDS, evaluate_replay_evidence
from backtesting.replay_state import (
    Outcome,
    OutcomeBatch,
    Player,
    initial_state,
)
from backtesting.rolling_replay import (
    QualityPolicy,
    ReplayTrajectory,
    get_strategic_replay_options,
    heuristic_zero_transfer_solve,
    run_rolling_replay,
    solve_lineup_milp,
)
from backtesting.season_rules import get_rules, next_free_transfers
from commands.profile_transfer_replay import (
    ProfilingEnvelope,
    ProfilingProblem,
    execute_profiling_experiment,
    save_profiling_report,
)
from features.availability_snapshots import write_availability_snapshot
from features.builder import build_features
from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel
from promotion_evidence_fixture import build_evidence_fixture

MIRROR_ROOT = REPO / "data/reports/empirical_mirrors"
CONFIG_ROOT = REPO / "config"


def _prepare_filtered_seed(season: str, tmp_dir: Path) -> Path:
    src = REPO / "data/archive" / season / "processed"
    dst = tmp_dir / f"seed_{season}"
    dst.mkdir(parents=True, exist_ok=True)
    players = pd.read_parquet(src / "players.parquet")
    non_mgr = players[players["position_id"] != 5].copy()
    non_mgr_ids = set(non_mgr["id"].astype(int))
    non_mgr.to_parquet(dst / "players.parquet", index=False)
    perf = pd.read_parquet(src / "player_performances.parquet")
    perf[perf["player_id"].isin(non_mgr_ids)].copy().to_parquet(dst / "player_performances.parquet", index=False)
    pd.read_parquet(src / "fixtures.parquet").to_parquet(dst / "fixtures.parquet", index=False)
    pd.read_parquet(src / "clubs.parquet").to_parquet(dst / "clubs.parquet", index=False)
    return dst


def _bootstrap_players_and_clubs(bs_xz_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    _, payload = _unpack_bootstrap_xz(bs_xz_path.read_bytes())
    clubs_df = pd.DataFrame(
        [
            {
                "id": int(t["id"]),
                "name": str(t["name"]),
                "short_name": str(t["short_name"]),
                "strength": int(t.get("strength", 3)),
                "strength_overall_home": int(t.get("strength_overall_home", 1100)),
                "strength_overall_away": int(t.get("strength_overall_away", 1100)),
                "strength_attack_home": int(t.get("strength_attack_home", 1100)),
                "strength_attack_away": int(t.get("strength_attack_away", 1100)),
                "strength_defence_home": int(t.get("strength_defence_home", 1100)),
                "strength_defence_away": int(t.get("strength_defence_away", 1100)),
            }
            for t in payload["teams"]
        ]
    )
    rows = []
    for el in payload["elements"]:
        if int(el.get("element_type", 0)) not in (1, 2, 3, 4):
            continue
        can_sel = el.get("can_select")
        purch_elig = bool(can_sel) if can_sel is not None else (el.get("status") != "u" and not bool(el.get("removed", False)))
        rows.append(
            {
                "id": int(el["id"]),
                "player_id": int(el["id"]),
                "code": int(el["code"]),
                "club_id": int(el["team"]),
                "position_id": int(el["element_type"]),
                "now_cost": int(el["now_cost"]),
                "selected_by_percent": float(el.get("selected_by_percent") or 0.0),
                "status": str(el.get("status", "a")),
                "chance_of_playing_next_round": el.get("chance_of_playing_next_round"),
                "news": str(el.get("news", "") or ""),
                "news_added": el.get("news_added"),
                "purchase_eligible": purch_elig,
            }
        )
    return pd.DataFrame(rows), clubs_df


def _stage_causal_gw_inputs(
    *,
    season: str,
    origin_entry: dict[str, Any],
    manifest: dict[str, Any],
    seed_dir: Path | None,
    work_dir: Path,
) -> tuple[Path, Path, pd.DataFrame]:
    """Stage causal pre-deadline files + return (processed_dir, snap_root, players_df)."""
    gw = int(origin_entry["gw"])
    gw_dir = work_dir / f"gw{gw}"
    proc = gw_dir / "processed"
    snaps = gw_dir / "snapshots"
    proc.mkdir(parents=True, exist_ok=True)
    snaps.mkdir(parents=True, exist_ok=True)

    bs_path = MIRROR_ROOT / str(origin_entry["bootstrap"]["local_relpath"])
    fx_path = MIRROR_ROOT / str(origin_entry["fixtures"]["local_relpath"])
    players_df, clubs_df = _bootstrap_players_and_clubs(bs_path)

    fx_raw = pd.read_csv(fx_path)
    fx_df = pd.DataFrame(
        {
            "id": pd.to_numeric(fx_raw["id"], errors="coerce").fillna(-1).astype(int),
            "gameweek_id": pd.to_numeric(fx_raw["event"], errors="coerce"),
            "kickoff_time": fx_raw["kickoff_time"].astype(str),
            "home_club_id": pd.to_numeric(fx_raw["team_h"], errors="coerce").astype(int),
            "away_club_id": pd.to_numeric(fx_raw["team_a"], errors="coerce").astype(int),
            "finished": fx_raw["finished"].astype(str).str.lower().isin({"true", "1"}),
            "started": fx_raw["started"].astype(str).str.lower().isin({"true", "1"}),
            "team_h_difficulty": pd.to_numeric(fx_raw["team_h_difficulty"], errors="coerce").fillna(3).astype(int),
            "team_a_difficulty": pd.to_numeric(fx_raw["team_a_difficulty"], errors="coerce").fillna(3).astype(int),
        }
    )
    fx_df = fx_df[fx_df["gameweek_id"].notna()].copy()
    fx_df["gameweek_id"] = fx_df["gameweek_id"].astype(int)

    # Prior settled history strictly from pre-deadline settled commits (< gw)
    has_defcon = get_rules(season).defensive_contributions
    if gw == 1:
        perf_cols = [
            "player_id", "fixture_id", "gameweek_id", "opponent_club_id", "was_home", "kickoff_time",
            "minutes", "total_points", "goals_scored", "assists", "clean_sheets", "goals_conceded",
            "own_goals", "penalties_saved", "penalties_missed", "yellow_cards", "red_cards", "saves",
            "bonus", "bps", "starts", "expected_goals", "expected_assists", "threat", "creativity",
        ] + (["defensive_contribution"] if has_defcon else [])
        perf_df = pd.DataFrame(columns=perf_cols)
    else:
        prev_sha = manifest["origins"][gw - 2]["settled_outcomes"]["commit_sha"][:10]
        hist_csv = MIRROR_ROOT / season / "outcomes" / f"merged_gw_{prev_sha}.csv"
        if not hist_csv.exists():
            hist_csv = MIRROR_ROOT / str(manifest["origins"][gw - 2]["settled_outcomes"]["local_relpath"])
        raw_h = pd.read_csv(hist_csv, low_memory=False)
        raw_h = raw_h[pd.to_numeric(raw_h["GW"], errors="coerce").astype(int) < gw].copy()
        raw_h = raw_h.drop_duplicates(["element", "fixture"], keep="last")
        perf_dict: dict[str, Any] = {
            "player_id": pd.to_numeric(raw_h["element"], errors="raise").astype(int),
            "fixture_id": pd.to_numeric(raw_h["fixture"], errors="raise").astype(int),
            "gameweek_id": pd.to_numeric(raw_h["GW"], errors="raise").astype(int),
            "opponent_club_id": pd.to_numeric(raw_h["opponent_team"], errors="raise").astype(int),
            "was_home": raw_h["was_home"].astype(bool),
            "kickoff_time": raw_h["kickoff_time"].astype(str),
            "minutes": pd.to_numeric(raw_h["minutes"], errors="raise").astype(int),
            "total_points": pd.to_numeric(raw_h["total_points"], errors="raise").astype(int),
            "goals_scored": pd.to_numeric(raw_h["goals_scored"], errors="raise").astype(int),
            "assists": pd.to_numeric(raw_h["assists"], errors="raise").astype(int),
            "clean_sheets": pd.to_numeric(raw_h["clean_sheets"], errors="raise").astype(int),
            "goals_conceded": pd.to_numeric(raw_h["goals_conceded"], errors="raise").astype(int),
            "own_goals": pd.to_numeric(raw_h["own_goals"], errors="raise").astype(int),
            "penalties_saved": pd.to_numeric(raw_h["penalties_saved"], errors="raise").astype(int),
            "penalties_missed": pd.to_numeric(raw_h["penalties_missed"], errors="raise").astype(int),
            "yellow_cards": pd.to_numeric(raw_h["yellow_cards"], errors="raise").astype(int),
            "red_cards": pd.to_numeric(raw_h["red_cards"], errors="raise").astype(int),
            "saves": pd.to_numeric(raw_h["saves"], errors="raise").astype(int),
            "bonus": pd.to_numeric(raw_h["bonus"], errors="raise").astype(int),
            "bps": pd.to_numeric(raw_h["bps"], errors="raise").astype(int),
            "starts": pd.to_numeric(raw_h["starts"], errors="raise").astype(int),
            "expected_goals": pd.to_numeric(raw_h["expected_goals"], errors="raise").astype(float),
            "expected_assists": pd.to_numeric(raw_h["expected_assists"], errors="raise").astype(float),
            "threat": pd.to_numeric(raw_h["threat"], errors="raise").astype(float),
            "creativity": pd.to_numeric(raw_h["creativity"], errors="raise").astype(float),
        }
        if has_defcon:
            perf_dict["defensive_contribution"] = pd.to_numeric(
                raw_h["defensive_contribution"], errors="raise"
            ).astype(int)
        perf_df = pd.DataFrame(perf_dict)

    clubs_df.to_parquet(proc / "clubs.parquet", index=False)
    players_df.drop(columns=["player_id", "purchase_eligible"], errors="ignore").to_parquet(proc / "players.parquet", index=False)
    fx_df.to_parquet(proc / "fixtures.parquet", index=False)
    perf_df.to_parquet(proc / "player_performances.parquet", index=False)

    snap_players = players_df[["id", "club_id", "position_id", "now_cost", "code", "status", "chance_of_playing_next_round"]].copy()
    snap = write_availability_snapshot(
        snaps,
        season,
        gw,
        origin_entry["deadline_utc"],
        origin_entry["bootstrap"]["capture_upper_utc"],
        snap_players,
        clubs_df,
        fx_df,
        {"kind": "development_mirror"},
    )
    if snap is None:
        raise RuntimeError(f"Availability snapshot outside capture window for {season} GW{gw}")
    return proc, snaps, players_df


def _forecast_for_gw(
    *,
    season: str,
    origin_entry: dict[str, Any],
    manifest: dict[str, Any],
    seed_dir: Path | None,
    work_dir: Path,
    horizon: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, float, float, float]:
    gw = int(origin_entry["gw"])
    proc, snaps, players_df = _stage_causal_gw_inputs(
        season=season, origin_entry=origin_entry, manifest=manifest, seed_dir=seed_dir, work_dir=work_dir
    )
    t0 = time.perf_counter()
    feats = build_features(
        proc,
        gw,
        horizon,
        seed_processed_dir=seed_dir,
        use_archive_seed=False,
        as_of_gw=gw,
        history_before_gw=gw,
        target_deadline=origin_entry["deadline_utc"],
        availability_snapshot_root=snaps,
        season=season,
        require_availability_snapshot=True,
        minutes_prior_source="seed_state",
    )
    t_feat = time.perf_counter() - t0
    hist = feats.loc[feats["gameweek_id"] < gw].copy()
    model = DefXgShrinkChallengerModel()
    t1 = time.perf_counter()
    model.fit(hist)
    t_fit = time.perf_counter() - t1

    t2 = time.perf_counter()
    preds = model.predict(feats, horizon)
    t_proj = time.perf_counter() - t2

    # Aggregate fixture grain -> wide solver DataFrame covering full admitted universe across targets
    targets = list(range(gw, min(gw + horizon, 39)))
    grouped = preds.groupby(["player_id", "gameweek_id"], as_index=False)[["projected_points", "projected_minutes"]].sum()
    pts_w = grouped.pivot(index="player_id", columns="gameweek_id", values="projected_points")
    mins_w = grouped.pivot(index="player_id", columns="gameweek_id", values="projected_minutes")
    wide = players_df[["player_id", "position_id", "club_id", "now_cost", "purchase_eligible"]].copy()
    for w in targets:
        wide[f"{w}_Pts"] = wide["player_id"].map(pts_w[w] if w in pts_w.columns else {}).fillna(0.0).astype(float)
        wide[f"{w}_xMins"] = wide["player_id"].map(mins_w[w] if w in mins_w.columns else {}).fillna(0.0).astype(float)
    return wide, preds, players_df, t_feat, t_fit, t_proj


def _outcomes_for_gw(season: str, gw: int) -> OutcomeBatch:
    proc = REPO / "data/archive" / season / "processed"
    perf = pd.read_parquet(proc / "player_performances.parquet")
    players = pd.read_parquet(proc / "players.parquet")
    non_mgr = set(players[players["position_id"] != 5]["id"].astype(int))
    sub = perf[(perf["gameweek_id"] == gw) & (perf["player_id"].isin(non_mgr))].copy()
    agg = sub.groupby("player_id", as_index=False).agg(
        total_points=("total_points", "sum"),
        minutes=("minutes", "sum"),
        yellow_cards=("yellow_cards", "sum"),
        red_cards=("red_cards", "sum"),
    )
    rows: list[tuple[int, Outcome]] = []
    out_map: dict[int, Outcome] = {}
    for _, r in agg.iterrows():
        pid = int(r["player_id"])
        mins = int(r["minutes"])
        pts = int(r["total_points"])
        yc = int(r["yellow_cards"])
        rc = int(r["red_cards"])
        out_map[pid] = Outcome(
            points=pts,
            minutes=mins,
            appeared=mins > 0,
            yellow_cards=yc,
            red_cards=rc,
            component_points_sum=pts,
        )
    # Also include 0-min non-playing registered players from universe
    for pid in non_mgr:
        rows.append((pid, out_map.get(pid, Outcome(0, 0, False))))
    return OutcomeBatch(season, gw, f"zero_diff:{season}:gw{gw}", tuple(rows))


def run_stage_a() -> dict[str, Any]:
    manifest = json.loads((CONFIG_ROOT / "dev_mirror_2025_26_manifest.json").read_text())
    with TemporaryDirectory(prefix="stage_a_") as tmp_str:
        tmp = Path(tmp_str)
        seed_dir = _prepare_filtered_seed("2024-25", tmp)

        # Measure real 685-player GW1 ownership anchor
        bs1, _ = _bootstrap_players_and_clubs(MIRROR_ROOT / manifest["origins"][0]["bootstrap"]["local_relpath"])
        t_a0 = time.perf_counter()
        anchor = solve_ownership_anchor(
            bs1,
            "2025-26",
            gameweek=1,
            anchor_type="opening",
            schema=UniverseSchema(eligibility_col="purchase_eligible"),
        )
        anchor_cost_s = time.perf_counter() - t_a0
        gw1_state = anchor.to_replay_state("2025-26")

        # Measure real GW1 Champion features + lineup solve
        wide1, _, _, _, _, _ = _forecast_for_gw(
            season="2025-26",
            origin_entry=manifest["origins"][0],
            manifest=manifest,
            seed_dir=seed_dir,
            work_dir=tmp / "prep",
            horizon=1,
        )
        xp1 = {int(r["player_id"]): float(r["1_Pts"]) for _, r in wide1.iterrows()}
        t_l0 = time.perf_counter()
        gw1_lineup = solve_lineup_milp(gw1_state.squad, xp1)
        gw1_lineup_s = time.perf_counter() - t_l0

        # Stage 4 representative ~700-player 6-GW problems from admitted 2025-26 GW2..6
        problem_specs = [
            ("2025-26_gw2_ordinary_6gw", "ordinary", 2, 1, None, gw1_state.bank),
            ("2025-26_gw3_constrained_6gw", "constrained_budget", 3, 1, None, 0),
            ("2025-26_gw4_transfer_heavy_6gw", "transfer_heavy", 4, 2, None, gw1_state.bank + 20),
            ("2025-26_gw6_wildcard_6gw", "chip_enabled", 6, 1, ((6, "wildcard"),), gw1_state.bank),
        ]
        specs_by_id: dict[str, tuple[str, int, int, Any, int]] = {
            pid_str: (arch, gw, ft, cal, bank_val)
            for pid_str, arch, gw, ft, cal, bank_val in problem_specs
        }
        staged_solve_inputs: dict[str, tuple[Any, pd.DataFrame, dict[str, Any]]] = {}
        manifest_problems = [
            ProfilingProblem(pid_str, arch, gw, 6, bank_val, ft)
            for pid_str, arch, gw, ft, cal, bank_val in problem_specs
        ]

        import itertools

        prep_seq = itertools.count(1)

        def prep_hook(prob: ProfilingProblem) -> tuple[float, float, float]:
            _, gw, ft, cal, bank_val = specs_by_id[prob.problem_id]
            wide, _, p_df, tf, tfit, tp = _forecast_for_gw(
                season="2025-26",
                origin_entry=manifest["origins"][gw - 1],
                manifest=manifest,
                seed_dir=seed_dir,
                work_dir=tmp / f"prep_{prob.problem_id}_{next(prep_seq)}",
                horizon=6,
            )
            bs_gw, _ = _bootstrap_players_and_clubs(MIRROR_ROOT / manifest["origins"][gw - 1]["bootstrap"]["local_relpath"])
            by_pid = {int(r["player_id"]): r for _, r in p_df.iterrows()}
            pos_map = {1: "GK", 2: "D", 3: "M", 4: "F"}
            club_counts: dict[int, int] = {}
            for pl in gw1_state.squad:
                c = int(by_pid[pl.player_id]["club_id"])
                club_counts[c] = club_counts.get(c, 0) + 1
            if max(club_counts.values()) > 3:
                gw_anchor = solve_ownership_anchor(
                    bs_gw,
                    "2025-26",
                    gameweek=1,
                    anchor_type="opening",
                    schema=UniverseSchema(eligibility_col="purchase_eligible"),
                )
                base_st = gw_anchor.to_replay_state("2025-26")
            else:
                base_st = gw1_state
            squad_at_gw = tuple(
                replace(
                    pl,
                    position=pos_map[int(by_pid[pl.player_id]["position_id"])],
                    club=int(by_pid[pl.player_id]["club_id"]),
                    market=int(by_pid[pl.player_id]["now_cost"]),
                    purchase_eligible=bool(by_pid[pl.player_id]["purchase_eligible"]),
                )
                for pl in base_st.squad
            )
            st_gw = replace(base_st, deadline=gw, free_transfers=ft, bank=bank_val, squad=squad_at_gw)
            opts = get_strategic_replay_options(6, rules_version="2025-26")
            if cal is not None:
                opts["chip_calendar"] = cal
            staged_solve_inputs[prob.problem_id] = (st_gw, wide, opts)
            return tf, tfit, tp

        def solver_hook(prob: ProfilingProblem, gap: float, tl: float) -> tuple[Any, str]:
            st_gw, wide, base_opts = staged_solve_inputs[prob.problem_id]
            opts = {**base_opts, "target_gap": gap, "time_limit_seconds": tl}
            dec, cert = native_strategic_solve(st_gw, prob.horizon, wide, opts)
            dig = hashlib.sha256(json.dumps(asdict(dec), sort_keys=True).encode()).hexdigest()
            return cert, dig

        env = ProfilingEnvelope(max_optimizer_calls=20, time_limit_per_call_seconds=60.0)
        report = execute_profiling_experiment(
            manifest=tuple(manifest_problems),
            envelope=env,
            solver_hook=solver_hook,
            model_prep_hook=prep_hook,
            anchor_hook=lambda: anchor_cost_s,
            gw1_lineup_hook=lambda: gw1_lineup_s,
            cache_root=tmp / "cache_bench",
            source_id="development_mirror:2025-26",
            protocol_id="adr-0065-parity-v2",
            simulation=False,
        )
        assert report.censored_calls_count == 0
        assert report.workload_projection is not None and report.workload_projection.extrapolation_reliable is True
        assert report.cache_benchmark is not None and report.cache_benchmark.interrupted_resume_verified is True

        save_profiling_report(report, MIRROR_ROOT / "stage_a_report.json")
        return {
            "status": "PASS",
            "anchor_universe_players": len(bs1),
            "anchor_lineup_starters": len(gw1_lineup.starters),
            "total_calls": report.total_calls_executed,
            "censored_calls": report.censored_calls_count,
            "total_elapsed_s": report.total_elapsed_seconds,
            "peak_rss_mb": report.peak_rss_mb,
            "anchor_cost_s": report.workload_projection.measured_anchor_cost_seconds,
            "gw1_lineup_cost_s": report.workload_projection.measured_gw1_lineup_cost_seconds,
            "est_season_s": report.workload_projection.estimated_season_total_seconds,
            "extrapolation_reliable": report.workload_projection.extrapolation_reliable,
            "cache_speedup": report.cache_benchmark.cache_speedup_ratio,
            "interrupted_resume_verified": report.cache_benchmark.interrupted_resume_verified,
            "paired_decisions_match": all(p.immediate_actions_match for p in report.paired_comparisons),
            "paired_summary": [p.to_dict() for p in report.paired_comparisons],
        }


def _replay_mirror_prefix(season: str, gws: list[int], tmp: Path, seed_dir: Path | None) -> tuple[ReplayTrajectory, list[dict[str, Any]], dict[str, Any]]:
    manifest = json.loads((CONFIG_ROOT / f"dev_mirror_{season.replace('-', '_')}_manifest.json").read_text())
    bs1, _ = _bootstrap_players_and_clubs(MIRROR_ROOT / manifest["origins"][0]["bootstrap"]["local_relpath"])
    anchor = solve_ownership_anchor(
        bs1, season, gameweek=1, anchor_type="opening", schema=UniverseSchema(eligibility_col="purchase_eligible")
    )
    chip_cal = tuple((int(x["gameweek"]), str(x["chip"])) for x in manifest["shared_chip_calendar"])
    cache_dir = tmp / f"replay_cache_{season}_{len(gws)}"

    forecasts_by_gw: dict[int, pd.DataFrame] = {}
    preds_by_gw: dict[int, pd.DataFrame] = {}
    outcomes_by_gw: dict[int, OutcomeBatch] = {}
    for gw in gws:
        horizon = min(6, 39 - gw)
        wide, preds, _, _, _, _ = _forecast_for_gw(
            season=season,
            origin_entry=manifest["origins"][gw - 1],
            manifest=manifest,
            seed_dir=seed_dir,
            work_dir=tmp / f"replay_{season}_{len(gws)}",
            horizon=horizon,
        )
        forecasts_by_gw[gw] = wide
        preds_by_gw[gw] = preds
        outcomes_by_gw[gw] = _outcomes_for_gw(season, gw)

    traj = run_rolling_replay(
        model_name="def_xg_shrink_challenger",
        season=season,
        anchor=anchor,
        forecast_provider=lambda gw, _state: forecasts_by_gw[gw],
        outcome_provider=lambda gw: outcomes_by_gw[gw],
        start_gw=min(gws),
        end_gw=max(gws),
        horizon=6,
        solve_fn=native_strategic_solve,
        policy=QualityPolicy(mode="certified", target_gap=0.0, time_limit_seconds=60.0),
        checkpoint_dir=cache_dir,
        model_version_hash="champ-hash-v1",
        protocol_hash="stage-b-proto-v2",
        chip_calendar=chip_cal,  # type: ignore[arg-type]
    )
    # Also test warm cache resume: re-running hits saved checkpoints identically with zero extra solves
    traj_resume = run_rolling_replay(
        model_name="def_xg_shrink_challenger",
        season=season,
        anchor=anchor,
        forecast_provider=lambda gw, _state: forecasts_by_gw[gw],
        outcome_provider=lambda gw: outcomes_by_gw[gw],
        start_gw=min(gws),
        end_gw=max(gws),
        horizon=6,
        solve_fn=native_strategic_solve,
        policy=QualityPolicy(mode="certified", target_gap=0.0, time_limit_seconds=60.0),
        checkpoint_dir=cache_dir,
        model_version_hash="champ-hash-v1",
        protocol_hash="stage-b-proto-v2",
        chip_calendar=chip_cal,  # type: ignore[arg-type]
    )
    assert [r.net_points for r in traj.records] == [r.net_points for r in traj_resume.records]
    assert [r.checkpoint_id for r in traj.records] == [r.checkpoint_id for r in traj_resume.records]
    audited_net = traj.audit_reconstructed_net_score()
    assert audited_net == sum(r.net_points for r in traj.records)

    # Identical-Model Null Control via evaluate_evidence_against_protocol
    paired_nc = [
        PairedGameweekScore(
            season=season,
            gameweek=rec.deadline,
            candidate_net_points=float(rec.net_points),
            champion_net_points=float(rec.net_points),
            candidate_gross_points=float(rec.gross_points),
            champion_gross_points=float(rec.gross_points),
            candidate_hits_deducted=int(rec.hit_penalty),
            champion_hits_deducted=int(rec.hit_penalty),
            is_chip_gameweek=rec.decision.chip is not None,
            segment="h1" if rec.deadline <= 19 else "h2",
        )
        for rec in traj.records
    ]

    # Evaluate all 15 MANDATORY_GUARDS on settled fixture rows across replayed GWs + ledger reconciliation
    guard_outcomes_df = pd.read_parquet(REPO / "data/archive" / season / "processed/player_performances.parquet")
    players_proc = pd.read_parquet(REPO / "data/archive" / season / "processed/players.parquet").rename(columns={"id": "player_id"})
    perf_with_pos = guard_outcomes_df.merge(players_proc[["player_id", "position_id"]], on="player_id", how="inner")
    all_merged = []
    for gw in gws:
        sub_pred = preds_by_gw[gw][preds_by_gw[gw]["gameweek_id"] == gw].copy()
        sub_perf = perf_with_pos[(perf_with_pos["gameweek_id"] == gw) & (perf_with_pos["position_id"] != 5)]
        all_merged.append(sub_pred.merge(sub_perf, on=["player_id", "gameweek_id", "fixture_id"], how="inner"))
    merged = pd.concat(all_merged, ignore_index=True)
    assert len(merged) > 0
    # Verify exact component sum == projected_points AND DefCon native season applicability across all settled rows
    xp_sum = (
        merged["xp_minutes"] + merged["xp_goals"] + merged["xp_assists"] + merged["xp_clean_sheet"]
        + merged["xp_conceded"] + merged["xp_defcon"] + merged["xp_saves"] + merged["xp_yellow_cards"]
        + merged["xp_red_cards"] + merged["xp_penalties_saved"] + merged["xp_penalties_missed"]
        + merged["xp_own_goals"] + merged["xp_bonus"]
    )
    assert float((xp_sum - merged["projected_points"]).abs().max()) < 1e-4
    app = declare_component_applicability(season)
    if app.component_statuses["defensive_contributions"] != "applicable":
        assert float(merged["xp_defcon"].abs().max()) == 0.0
    # Also sanity-check reconcile_total_to_ledger helper cleanly
    assert reconcile_total_to_ledger(
        17.0,
        ComponentLedger(minutes=90.0, goals=1.0, assists=1.0, clean_sheets=1.0, defensive_contributions=1.0),
        "D",
        season="2025-26",
    ).reconciled is True

    # Realized component points vs xp_* component predictions for all 15 MANDATORY_GUARDS
    rules = get_rules(season)
    realized_pts = {
        "points_mse": merged["total_points"].astype(float),
        "minutes_mae": merged["minutes"].astype(float),
        "minutes_points_mse": merged["minutes"].map(lambda m: 2.0 if m >= 60 else (1.0 if m > 0 else 0.0)),
        "goals_points_mse": merged.apply(
            lambda r: float(r["goals_scored"]) * (rules.goalkeeper_goal_points if r["position_id"] == 1 else {2: 6, 3: 5, 4: 4}[r["position_id"]]),
            axis=1,
        ),
        "assists_points_mse": merged["assists"].astype(float) * 3.0,
        "clean_sheet_points_mse": merged.apply(
            lambda r: float(r["clean_sheets"]) * ({1: 4, 2: 4, 3: 1, 4: 0}[r["position_id"]]), axis=1
        ),
        "conceded_points_mse": merged.apply(
            lambda r: -(int(r["goals_conceded"]) // 2) if r["position_id"] in (1, 2) else 0.0, axis=1
        ),
        "saves_points_mse": merged.apply(lambda r: float(int(r["saves"]) // 3) if r["position_id"] == 1 else 0.0, axis=1),
        "defcon_points_mse": (
            merged.apply(
                lambda r: 2.0 if (r["position_id"] == 2 and r["defensive_contribution"] >= 10) or (r["position_id"] in (3, 4) and r["defensive_contribution"] >= 12) else 0.0,
                axis=1,
            )
            if rules.defensive_contributions and "defensive_contribution" in merged.columns
            else pd.Series(0.0, index=merged.index)
        ),
        "bonus_points_mse": merged["bonus"].astype(float),
        "yellow_cards_points_mse": -merged["yellow_cards"].astype(float),
        "red_cards_points_mse": -3.0 * merged["red_cards"].astype(float),
        "penalties_saved_points_mse": 5.0 * merged["penalties_saved"].astype(float),
        "penalties_missed_points_mse": -2.0 * merged["penalties_missed"].astype(float),
        "own_goals_points_mse": -2.0 * merged["own_goals"].astype(float),
    }
    pred_cols = {
        "points_mse": "projected_points",
        "minutes_mae": "projected_minutes",
        "minutes_points_mse": "xp_minutes",
        "goals_points_mse": "xp_goals",
        "assists_points_mse": "xp_assists",
        "clean_sheet_points_mse": "xp_clean_sheet",
        "conceded_points_mse": "xp_conceded",
        "saves_points_mse": "xp_saves",
        "defcon_points_mse": "xp_defcon",
        "bonus_points_mse": "xp_bonus",
        "yellow_cards_points_mse": "xp_yellow_cards",
        "red_cards_points_mse": "xp_red_cards",
        "penalties_saved_points_mse": "xp_penalties_saved",
        "penalties_missed_points_mse": "xp_penalties_missed",
        "own_goals_points_mse": "xp_own_goals",
    }
    guard_outputs = []
    for gname in sorted(MANDATORY_GUARDS):
        diff = merged[pred_cols[gname]].astype(float) - realized_pts[gname].astype(float)
        errs = (diff.abs() if gname == "minutes_mae" else (diff * diff)).tolist()
        guard_outputs.append(evaluate_non_inferiority_guard(errs, errs, metric_name=gname, meaningful_margin=0.05))
    nc_eval = evaluate_evidence_against_protocol(
        paired_nc,
        guard_outputs,
        StatisticalProtocolConfig(
            bootstrap_draws=200,
            bootstrap_block_size=1,
            required_projection_guards=tuple(sorted(MANDATORY_GUARDS)),
        ),
        seed=42,
    )
    assert nc_eval.point_estimate == 0.0 and nc_eval.p_value == 1.0 and nc_eval.projection_guards_passed is True
    return traj, [asdict(r) for r in traj.records], {
        "season": season,
        "gws": gws,
        "audited_net_score": audited_net,
        "settled_fixture_rows": len(merged),
        "null_control_p_value": nc_eval.p_value,
        "null_control_delta": nc_eval.point_estimate,
        "mandatory_guard_count": len(guard_outputs),
        "mandatory_guards_passed": nc_eval.projection_guards_passed,
        "defcon_applicability": app.component_statuses["defensive_contributions"],
        "anchor_id": anchor.anchor_id,
    }


def run_stage_b() -> dict[str, Any]:
    summary: dict[str, Any] = {}
    with TemporaryDirectory(prefix="stage_b_") as tmp_str:
        tmp = Path(tmp_str)
        seed_24_dir = _prepare_filtered_seed("2024-25", tmp)
        seed_23_dir = _prepare_filtered_seed("2023-24", tmp)

        # B1: Synthetic end-to-end promotion_evidence + heuristic refusal at _verify_replay
        req_syn = build_evidence_fixture(tmp / "syn")
        ev_syn = evaluate_replay_evidence(req_syn)
        assert ev_syn["scientific_verdict"] == "inconclusive" and ev_syn["empirical_admission"] is False
        _, cert_heur = heuristic_zero_transfer_solve(initial_state("2025-26", _sample_squad()), 1, pd.DataFrame({"player_id": [1], "projected_points": [1.0]}), {})
        b1_ok = "lineup" in cert_heur.solver_version and any(b in cert_heur.solver_version.lower() for b in ("lineup", "heuristic"))
        assert b1_ok
        summary["b1_synthetic"] = {"status": "PASS", "heuristic_refused": b1_ok, "verdict": ev_syn["scientific_verdict"]}

        # B2: 2025-26 GW1-2 Vertical Empirical Slice
        traj12, _, meta12 = _replay_mirror_prefix("2025-26", [1, 2], tmp, seed_24_dir)
        # Horizon 6 vs 1 check on GW2
        manifest25 = json.loads((CONFIG_ROOT / "dev_mirror_2025_26_manifest.json").read_text())
        wide_gw2, _, p_gw2, _, _, _ = _forecast_for_gw(
            season="2025-26", origin_entry=manifest25["origins"][1], manifest=manifest25, seed_dir=seed_24_dir, work_dir=tmp / "b2_h", horizon=6
        )
        d6, _ = native_strategic_solve(traj12.records[1].pre_state, 6, wide_gw2, get_strategic_replay_options(6, rules_version="2025-26"))
        d1, _ = native_strategic_solve(traj12.records[1].pre_state, 1, wide_gw2, get_strategic_replay_options(1, rules_version="2025-26"))
        summary["b2_2025_26_gw1_2"] = {**meta12, "partial_prefix_non_promotable": True, "h6_transfers": len(d6.transfers), "h1_transfers": len(d1.transfers)}

        # B3: 2025-26 (S-1) GW1-7 contiguous prefix + GW1-38 fail-closed gate + real GW22 Barnes check
        traj17, _, meta17 = _replay_mirror_prefix("2025-26", [1, 2, 3, 4, 5, 6, 7], tmp, seed_24_dir)
        first_blocked_25 = next(o["gw"] for o in manifest25["origins"] if not o["origin_admitted"])
        assert first_blocked_25 == 8
        gw22_batch = _outcomes_for_gw("2025-26", 22)
        gw22_218 = dict(gw22_batch.outcomes)[218]
        assert gw22_218.minutes == 0 and gw22_218.yellow_cards == 1 and gw22_218.points == -1
        summary["b3_2025_26_gw1_7_and_full_gate"] = {
            **meta17,
            "full_1_to_38_first_blocked_gw": first_blocked_25,
            "gw22_player_218_verified": {"minutes": gw22_218.minutes, "yellow_cards": gw22_218.yellow_cards, "points": gw22_218.points},
        }

        # B4: 2024-25 (S-2) GW1 prefix + GW1-38 fail-closed gate + cross-season native rules
        manifest24 = json.loads((CONFIG_ROOT / "dev_mirror_2024_25_manifest.json").read_text())
        traj24_1, _, meta24 = _replay_mirror_prefix("2024-25", [1], tmp, seed_23_dir)
        first_blocked_24 = next(o["gw"] for o in manifest24["origins"] if not o["origin_admitted"])
        # Native rules check across 2023-24, 2024-25, 2025-26 (GW15 AFCON 5-FT top-up)
        r25 = get_rules("2025-26")
        assert next_free_transfers(r25, 1, 0, None, 15) == 5
        assert next_free_transfers(get_rules("2024-25"), 3, 1, "free_hit", 20) == 3
        assert next_free_transfers(get_rules("2023-24"), 2, 1, None, 10) == 2
        assert next_free_transfers(get_rules("2023-24"), 2, 0, "wildcard", 10) == 1
        summary["b4_2024_25_and_cross_season"] = {
            **meta24,
            "full_1_to_38_first_blocked_gw": first_blocked_24,
            "afcon_gw15_ft": 5,
            "cross_season_rules_verified": ["2023-24", "2024-25", "2025-26"],
        }
        del traj24_1

    (MIRROR_ROOT / "stage_b_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def _sample_squad():
    from models.scoring_matrix import Position
    positions: tuple[Position, ...] = ("GK", "GK", "D", "D", "D", "D", "D", "M", "M", "M", "M", "M", "F", "F", "F")
    return tuple(Player(pid, pos, (pid - 1) % 5 + 1, 50, 50, True) for pid, pos in enumerate(positions, 1))


def main() -> None:
    a = run_stage_a()
    print("=== STAGE A PASS ===")
    print(json.dumps(a, indent=2))
    b = run_stage_b()
    print("=== STAGE B PASS ===")
    print(json.dumps(b, indent=2))


if __name__ == "__main__":
    main()
