"""Execute real Stage A (~700-player Champion profiling) -> Stage B verification suites (#179, #189)."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, replace
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from backtesting.empirical_admission import _valid_outcomes_payload
from backtesting.empirical_mirrors import extract_prior_settled_df, load_empirical_manifest_bundle
from backtesting.evidence_statistics import PairedGameweekScore, StatisticalProtocolConfig, evaluate_evidence_against_protocol
from backtesting.fplcache_ingest import _sanitize_bootstrap, _unpack_bootstrap_xz, _utc
from backtesting.native_transfer_solver import native_strategic_solve
from backtesting.ownership_anchor import UniverseSchema, solve_ownership_anchor
from backtesting.projection_guards import (
    declare_component_applicability,
    evaluate_non_inferiority_guard,
)
from backtesting.promotion_evidence import MANDATORY_GUARDS
from backtesting.replay_state import (
    Decision,
    Lineup,
    Outcome,
    OutcomeBatch,
    Player,
    initial_state,
    state_hash,
    transition,
)
from backtesting.rolling_replay import (
    QualityPolicy,
    ReplayTrajectory,
    get_strategic_replay_options,
    heuristic_zero_transfer_solve,
    run_rolling_replay,
    solve_lineup_milp,
)
from backtesting.season_rules import Chip, get_rules, load_season_lifecycle, next_free_transfers
from backtesting.walkforward import LEDGER_COMPONENTS, _build_actual_components
from commands.profile_transfer_replay import (
    ProfilingEnvelope,
    ProfilingProblem,
    execute_profiling_experiment,
    save_profiling_report,
)
from features.availability_snapshots import write_availability_snapshot
from features.builder import build_features
from models import get_model

MIRROR_ROOT = REPO / "data/reports/empirical_mirrors"
CONFIG_ROOT = REPO / "config"


@dataclass(frozen=True)
class _StageAProbeSpec:
    problem_id: str
    archetype: str
    gw: int
    free_transfers: int
    chip_calendar: tuple[tuple[int, Chip], ...]
    bank: int


def _champion_model_name() -> str:
    payload = json.loads((CONFIG_ROOT / "model_selection.json").read_text(encoding="utf-8"))
    return str(payload["champion"])


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


def _bootstrap_players_and_clubs(bs_xz_path: Path, *, capture_upper: datetime) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Decode, sanitize against capture_upper, and project bootstrap players/clubs frames."""
    _, payload = _unpack_bootstrap_xz(bs_xz_path.read_bytes())
    sanitized, _, bs_issues = _sanitize_bootstrap(payload, capture_upper=capture_upper)
    if bs_issues:
        raise ValueError(f"Bootstrap sanitization issues in {bs_xz_path}: {','.join(bs_issues)}")
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
    rows = [
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
            "purchase_eligible": bool(el["purchase_eligible"]),
        }
        for el in sanitized
    ]
    return pd.DataFrame(rows), clubs_df


def _stage_causal_gw_inputs(
    *,
    season: str,
    origin_entry: dict[str, Any],
    manifest: dict[str, Any],
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
    bs_cap_up = _utc(origin_entry["bootstrap"]["capture_upper_utc"])
    players_df, clubs_df = _bootstrap_players_and_clubs(bs_path, capture_upper=bs_cap_up)

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
        raw_h = extract_prior_settled_df(hist_csv.read_bytes(), before_gw=gw)
        perf_dict: dict[str, Any] = {
            "player_id": pd.to_numeric(raw_h["element"], errors="raise").astype(int),
            "fixture_id": pd.to_numeric(raw_h["fixture"], errors="raise").astype(int),
            "gameweek_id": pd.to_numeric(raw_h["GW"], errors="raise").astype(int),
            "opponent_club_id": pd.to_numeric(raw_h["opponent_team"], errors="raise").astype(int),
            "was_home": raw_h["was_home"].astype(str).str.strip().str.lower().isin({"true", "1"}),
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
            if "defensive_contribution" not in raw_h.columns:
                raise ValueError(f"Missing defensive_contribution in prior settled outcomes for {season} GW<{gw}")
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
        season=season, origin_entry=origin_entry, manifest=manifest, work_dir=work_dir
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
    model = get_model(_champion_model_name())
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
    lifecycle = load_season_lifecycle()
    dev_season = lifecycle.season_for_role("development")
    dev_seed = lifecycle.seasons[dev_season].prior_seed
    assert dev_seed is not None
    manifest_path = CONFIG_ROOT / f"dev_mirror_{dev_season.replace('-', '_')}_manifest.json"
    load_empirical_manifest_bundle(manifest_path, quarantine_root=MIRROR_ROOT, prefix_end_gw=6, require_admitted=True)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    with TemporaryDirectory(prefix="stage_a_") as tmp_str:
        tmp = Path(tmp_str)
        seed_dir = _prepare_filtered_seed(dev_seed, tmp)

        # Measure real 685-player GW1 ownership anchor
        bs1, _ = _bootstrap_players_and_clubs(
            MIRROR_ROOT / manifest["origins"][0]["bootstrap"]["local_relpath"],
            capture_upper=_utc(manifest["origins"][0]["bootstrap"]["capture_upper_utc"]),
        )
        t_a0 = time.perf_counter()
        anchor = solve_ownership_anchor(
            bs1,
            dev_season,
            gameweek=1,
            anchor_type="opening",
            schema=UniverseSchema(eligibility_col="purchase_eligible"),
        )
        anchor_cost_s = time.perf_counter() - t_a0
        gw1_state = anchor.to_replay_state(dev_season)

        # Measure real GW1 Champion features + lineup solve
        wide1, _, _, _, _, _ = _forecast_for_gw(
            season=dev_season,
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

        # Stage 4 representative ~700-player 6-GW problems from admitted GW2..6
        problem_specs: tuple[_StageAProbeSpec, ...] = (
            _StageAProbeSpec(f"{dev_season}_gw2_ordinary_6gw", "ordinary", 2, 1, (), gw1_state.bank),
            _StageAProbeSpec(f"{dev_season}_gw3_constrained_6gw", "constrained_budget", 3, 1, (), 0),
            _StageAProbeSpec(f"{dev_season}_gw4_transfer_heavy_6gw", "transfer_heavy", 4, 2, (), gw1_state.bank + 20),
            _StageAProbeSpec(f"{dev_season}_gw6_wildcard_6gw", "chip_enabled", 6, 1, ((6, "wildcard"),), gw1_state.bank),
        )
        specs_by_id = {spec.problem_id: spec for spec in problem_specs}
        staged_solve_inputs: dict[str, tuple[Any, pd.DataFrame, dict[str, Any], OutcomeBatch]] = {}
        manifest_problems = [
            ProfilingProblem(spec.problem_id, spec.archetype, spec.gw, 6, spec.bank, spec.free_transfers)
            for spec in problem_specs
        ]

        import itertools

        prep_seq = itertools.count(1)

        def prep_hook(prob: ProfilingProblem) -> tuple[float, float, float]:
            spec = specs_by_id[prob.problem_id]
            wide, _, p_df, tf, tfit, tp = _forecast_for_gw(
                season=dev_season,
                origin_entry=manifest["origins"][spec.gw - 1],
                manifest=manifest,
                seed_dir=seed_dir,
                work_dir=tmp / f"prep_{prob.problem_id}_{next(prep_seq)}",
                horizon=6,
            )
            bs_gw, _ = _bootstrap_players_and_clubs(
                MIRROR_ROOT / manifest["origins"][spec.gw - 1]["bootstrap"]["local_relpath"],
                capture_upper=_utc(manifest["origins"][spec.gw - 1]["bootstrap"]["capture_upper_utc"]),
            )
            by_pid = {int(r["player_id"]): r for _, r in p_df.iterrows()}
            pos_map = {1: "GK", 2: "D", 3: "M", 4: "F"}
            club_counts: dict[int, int] = {}
            for pl in gw1_state.squad:
                c = int(by_pid[pl.player_id]["club_id"])
                club_counts[c] = club_counts.get(c, 0) + 1
            if max(club_counts.values()) > 3:
                gw_anchor = solve_ownership_anchor(
                    bs_gw,
                    dev_season,
                    gameweek=1,
                    anchor_type="opening",
                    schema=UniverseSchema(eligibility_col="purchase_eligible"),
                )
                base_st = gw_anchor.to_replay_state(dev_season)
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
            st_gw = replace(
                base_st,
                deadline=spec.gw,
                free_transfers=spec.free_transfers,
                bank=spec.bank,
                squad=squad_at_gw,
                parent_hash=state_hash(base_st),
            )
            opts = get_strategic_replay_options(6, rules_version=dev_season)
            if spec.chip_calendar:
                opts["chip_calendar"] = spec.chip_calendar
            staged_solve_inputs[prob.problem_id] = (st_gw, wide, opts, _outcomes_for_gw(dev_season, spec.gw))
            return tf, tfit, tp

        def solver_hook(prob: ProfilingProblem, gap: float, tl: float) -> tuple[Any, str]:
            st_gw, wide, base_opts, gw_outcomes = staged_solve_inputs[prob.problem_id]
            opts = {**base_opts, "target_gap": gap, "time_limit_seconds": tl}
            dec, cert = native_strategic_solve(st_gw, prob.horizon, wide, opts)
            t_sc0 = time.perf_counter()
            tr_res = transition(st_gw, dec, gw_outcomes)
            _ = hashlib.sha256(
                json.dumps({"net": tr_res.net, "post_hash": state_hash(tr_res.state)}, sort_keys=True).encode()
            ).hexdigest()
            sc_time = max(1e-6, time.perf_counter() - t_sc0)
            cert_with_score = replace(
                cert,
                strategic_audit={**cert.strategic_audit, "scoring_time_seconds": round(sc_time, 6)},
            )
            dig = hashlib.sha256(json.dumps(asdict(dec), sort_keys=True).encode()).hexdigest()
            return cert_with_score, dig

        env = ProfilingEnvelope(max_optimizer_calls=20, time_limit_per_call_seconds=60.0)
        report = execute_profiling_experiment(
            manifest=tuple(manifest_problems),
            envelope=env,
            solver_hook=solver_hook,
            model_prep_hook=prep_hook,
            anchor_hook=lambda: anchor_cost_s,
            gw1_lineup_hook=lambda: gw1_lineup_s,
            cache_root=tmp / "cache_bench",
            source_id=f"development_mirror:{dev_season}",
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
    manifest_path = CONFIG_ROOT / f"dev_mirror_{season.replace('-', '_')}_manifest.json"
    load_empirical_manifest_bundle(manifest_path, quarantine_root=MIRROR_ROOT, prefix_end_gw=max(gws), require_admitted=True)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    bs1, _ = _bootstrap_players_and_clubs(
        MIRROR_ROOT / manifest["origins"][0]["bootstrap"]["local_relpath"],
        capture_upper=_utc(manifest["origins"][0]["bootstrap"]["capture_upper_utc"]),
    )
    anchor = solve_ownership_anchor(
        bs1, season, gameweek=1, anchor_type="opening", schema=UniverseSchema(eligibility_col="purchase_eligible")
    )
    chip_cal = tuple((int(x["gameweek"]), str(x["chip"])) for x in manifest["shared_chip_calendar"])
    cache_dir = tmp / f"replay_cache_{season}_{len(gws)}"
    champion_name = _champion_model_name()

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

    runs: list[ReplayTrajectory] = []
    for _pass in ("cold", "warm_resume"):
        runs.append(
            run_rolling_replay(
                model_name=champion_name,
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
        )
    traj, traj_resume = runs
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

    # Evaluate all 15 MANDATORY_GUARDS over all_admitted_players across leads 0..5 + 13-component ledger reconciliation
    guard_outcomes_df = pd.read_parquet(REPO / "data/archive" / season / "processed/player_performances.parquet")
    players_proc = pd.read_parquet(REPO / "data/archive" / season / "processed/players.parquet").rename(columns={"id": "player_id"})
    non_mgr_players = players_proc[players_proc["position_id"] != 5][["player_id", "position_id"]].copy()
    non_mgr_players["native_rules_version"] = season
    settled_all = _build_actual_components(
        guard_outcomes_df[guard_outcomes_df["player_id"].isin(set(non_mgr_players["player_id"]))].copy(),
        non_mgr_players,
    )
    ledger_residual = settled_all["total_points"] - settled_all[[f"actual_{c}" for c in LEDGER_COMPONENTS]].sum(axis=1)
    assert float(ledger_residual.abs().max()) < 1e-6

    actual_cols = [
        "total_points", "minutes", "actual_xp_minutes", "actual_xp_goals", "actual_xp_assists",
        "actual_xp_clean_sheet", "actual_xp_conceded", "actual_xp_defcon", "actual_xp_saves",
        "actual_xp_yellow_cards", "actual_xp_red_cards", "actual_xp_penalties_saved",
        "actual_xp_penalties_missed", "actual_xp_own_goals", "actual_xp_bonus",
    ]
    actual_gw_agg = settled_all.groupby(["player_id", "gameweek_id"], as_index=False)[actual_cols].sum()
    xp_cols = [
        "projected_points", "projected_minutes", "xp_minutes", "xp_goals", "xp_assists",
        "xp_clean_sheet", "xp_conceded", "xp_defcon", "xp_saves", "xp_yellow_cards",
        "xp_red_cards", "xp_penalties_saved", "xp_penalties_missed", "xp_own_goals", "xp_bonus",
    ]
    lead_frames: list[pd.DataFrame] = []
    for gw in gws:
        pred_gw = preds_by_gw[gw].groupby(["player_id", "gameweek_id"], as_index=False)[xp_cols].sum()
        pred_gw["issue_gw"] = gw
        pred_gw["horizon_lead"] = pred_gw["gameweek_id"] - gw
        assert set(pred_gw["horizon_lead"]) == set(range(min(6, 39 - gw)))
        joined = pred_gw.merge(actual_gw_agg, on=["player_id", "gameweek_id"], how="left")
        joined[actual_cols] = joined[actual_cols].fillna(0.0)
        assert len(joined) == len(pred_gw)
        lead_frames.append(joined)
    merged = pd.concat(lead_frames, ignore_index=True)
    assert len(merged) > 0

    xp_sum = sum(merged[col] for col in xp_cols[2:])
    assert float((xp_sum - merged["projected_points"]).abs().max()) < 1e-4
    app = declare_component_applicability(season)
    if app.component_statuses["defensive_contributions"] != "applicable":
        assert float(merged["xp_defcon"].abs().max()) == 0.0

    guard_to_cols = {
        "points_mse": ("projected_points", "total_points"),
        "minutes_mae": ("projected_minutes", "minutes"),
        "minutes_points_mse": ("xp_minutes", "actual_xp_minutes"),
        "goals_points_mse": ("xp_goals", "actual_xp_goals"),
        "assists_points_mse": ("xp_assists", "actual_xp_assists"),
        "clean_sheet_points_mse": ("xp_clean_sheet", "actual_xp_clean_sheet"),
        "conceded_points_mse": ("xp_conceded", "actual_xp_conceded"),
        "saves_points_mse": ("xp_saves", "actual_xp_saves"),
        "defcon_points_mse": ("xp_defcon", "actual_xp_defcon"),
        "bonus_points_mse": ("xp_bonus", "actual_xp_bonus"),
        "yellow_cards_points_mse": ("xp_yellow_cards", "actual_xp_yellow_cards"),
        "red_cards_points_mse": ("xp_red_cards", "actual_xp_red_cards"),
        "penalties_saved_points_mse": ("xp_penalties_saved", "actual_xp_penalties_saved"),
        "penalties_missed_points_mse": ("xp_penalties_missed", "actual_xp_penalties_missed"),
        "own_goals_points_mse": ("xp_own_goals", "actual_xp_own_goals"),
    }
    guard_outputs = []
    for gname in sorted(MANDATORY_GUARDS):
        pcol, acol = guard_to_cols[gname]
        diff = merged[pcol].astype(float) - merged[acol].astype(float)
        errs = (diff.abs() if gname == "minutes_mae" else (diff * diff)).tolist()
        guard_outputs.append(evaluate_non_inferiority_guard(errs, errs, metric_name=gname, meaningful_margin=0.05))
        if gname == "points_mse":
            zero_errs = (merged[acol].astype(float) ** 2).tolist()
            vs_zero = evaluate_non_inferiority_guard(errs, zero_errs, metric_name=gname, meaningful_margin=0.05)
            assert vs_zero.estimate < 0.0
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
        "champion_model": champion_name,
        "audited_net_score": audited_net,
        "lead_player_gw_rows": len(merged),
        "leads_evaluated": sorted({int(x) for x in merged["horizon_lead"].unique()}),
        "null_control_p_value": nc_eval.p_value,
        "null_control_delta": nc_eval.point_estimate,
        "mandatory_guard_count": len(guard_outputs),
        "mandatory_guards_passed": nc_eval.projection_guards_passed,
        "defcon_applicability": app.component_statuses["defensive_contributions"],
        "anchor_id": anchor.anchor_id,
    }


def run_stage_b() -> dict[str, Any]:
    lifecycle = load_season_lifecycle()
    dev_season = lifecycle.season_for_role("development")
    filter_season = lifecycle.season_for_role("historical_filter")
    dev_seed = lifecycle.seasons[dev_season].prior_seed
    filter_seed = lifecycle.seasons[filter_season].prior_seed
    assert dev_seed is not None and filter_seed is not None

    summary: dict[str, Any] = {}
    with TemporaryDirectory(prefix="stage_b_") as tmp_str:
        tmp = Path(tmp_str)
        seed_dev_dir = _prepare_filtered_seed(dev_seed, tmp)
        seed_filter_dir = _prepare_filtered_seed(filter_seed, tmp)

        # B1: Synthetic promotion_evidence + 8 #178 & 8 #179 negative classes + heuristic refusal via pytest
        b1_suites = [
            "tests/test_stage_controls.py",
            "tests/test_empirical_admission.py",
            "tests/test_empirical_mirrors.py",
            "tests/test_empirical_replay.py",
            "tests/test_strategic_parity_and_profiler.py",
        ]
        subprocess.run([sys.executable, "-m", "pytest", "-q", *b1_suites], cwd=REPO, check=True)
        _, cert_heur = heuristic_zero_transfer_solve(
            initial_state(dev_season, _sample_squad()),
            1,
            pd.DataFrame({"player_id": [1], "projected_points": [1.0]}),
            {},
        )
        b1_ok = "lineup" in cert_heur.solver_version
        assert b1_ok
        summary["b1_synthetic"] = {"status": "PASS", "heuristic_refused": b1_ok, "pytest_suites": b1_suites}

        # B2: Development season GW1-2 Vertical Empirical Slice + horizon=6 vs 1 sensitivity
        traj12, _, meta12 = _replay_mirror_prefix(dev_season, [1, 2], tmp, seed_dev_dir)
        manifest_dev_path = CONFIG_ROOT / f"dev_mirror_{dev_season.replace('-', '_')}_manifest.json"
        manifest_dev = json.loads(manifest_dev_path.read_text(encoding="utf-8"))
        wide_gw2, _, _, _, _, _ = _forecast_for_gw(
            season=dev_season,
            origin_entry=manifest_dev["origins"][1],
            manifest=manifest_dev,
            seed_dir=seed_dev_dir,
            work_dir=tmp / "b2_h",
            horizon=6,
        )
        d6, _ = native_strategic_solve(traj12.records[1].pre_state, 6, wide_gw2, get_strategic_replay_options(6, rules_version=dev_season))
        d1, _ = native_strategic_solve(traj12.records[1].pre_state, 1, wide_gw2, get_strategic_replay_options(1, rules_version=dev_season))
        # Also verify explicit horizon divergence on real dev_season universe (deferred GW3 jump)
        div_df = wide_gw2.copy()
        owned_ids = {p.player_id for p in traj12.records[1].pre_state.squad}
        candidates = div_df[(div_df["purchase_eligible"]) & (~div_df["player_id"].isin(owned_ids)) & (div_df["position_id"] == 4)].head(2)
        assert len(candidates) == 2
        p_fast, p_long = int(candidates.iloc[0]["player_id"]), int(candidates.iloc[1]["player_id"])
        for col_gw in range(2, 8):
            div_df[f"{col_gw}_Pts"] = 4.0
        div_df.loc[div_df["player_id"] == p_fast, "2_Pts"] = 18.0
        div_df.loc[div_df["player_id"] == p_long, ["2_Pts", "3_Pts", "4_Pts", "5_Pts", "6_Pts", "7_Pts"]] = [17.0, 15.0, 15.0, 15.0, 15.0, 15.0]
        d6_div, _ = native_strategic_solve(traj12.records[1].pre_state, 6, div_df, get_strategic_replay_options(6, rules_version=dev_season))
        d1_div, _ = native_strategic_solve(traj12.records[1].pre_state, 1, div_df, get_strategic_replay_options(1, rules_version=dev_season))
        assert d6_div.transfers != d1_div.transfers
        summary["b2_dev_gw1_2"] = {
            **meta12,
            "partial_prefix_non_promotable": True,
            "gw2_h6_transfers": len(d6.transfers),
            "gw2_h1_transfers": len(d1.transfers),
            "horizon_divergence_verified": d6_div.transfers != d1_div.transfers,
        }

        # B3: Dev season GW1-7 contiguous prefix + GW1-38 fail-closed gate + real GW22 player 218 admission & transition
        _, _, meta17 = _replay_mirror_prefix(dev_season, [1, 2, 3, 4, 5, 6, 7], tmp, seed_dev_dir)
        first_blocked_dev = next(o["gw"] for o in manifest_dev["origins"] if not o["origin_admitted"])
        assert first_blocked_dev == 8
        try:
            load_empirical_manifest_bundle(manifest_dev_path, quarantine_root=MIRROR_ROOT, prefix_end_gw=None, require_admitted=True)
            raise AssertionError("Expected full 1..38 dev manifest admission to fail closed at GW8")
        except ValueError as exc:
            assert "GW8" in str(exc)

        gw22_batch = _outcomes_for_gw(dev_season, 22)
        gw22_218 = dict(gw22_batch.outcomes)[218]
        assert gw22_218.minutes == 0 and gw22_218.yellow_cards == 1 and gw22_218.points == -1
        assert _valid_outcomes_payload(
            [
                {
                    "player_id": 218,
                    "total_points": gw22_218.points,
                    "minutes": gw22_218.minutes,
                    "appeared": gw22_218.appeared,
                    "yellow_cards": gw22_218.yellow_cards,
                    "red_cards": gw22_218.red_cards,
                    "component_points_sum": gw22_218.component_points_sum,
                }
            ],
            rules_version=dev_season,
        ) == []
        sq22 = list(_sample_squad())
        sq22[7] = Player(218, "M", 6, 65, 65, True)
        st22 = initial_state(dev_season, tuple(sq22))
        dec22 = Decision((), Lineup((1, 3, 4, 5, 6, 218, 9, 10, 11, 13, 14), (2, 7, 12, 15), 9, 10), state_hash(st22), 1)
        tr22 = transition(
            st22,
            dec22,
            OutcomeBatch(dev_season, 1, "gw22-card", tuple((p.player_id, gw22_218 if p.player_id == 218 else Outcome(2, 90, True)) for p in sq22)),
        )
        assert tr22.gross == 22
        tr22_card = transition(
            st22,
            dec22,
            OutcomeBatch(
                dev_season,
                1,
                "gw22-card-nosub",
                tuple(
                    (p.player_id, gw22_218 if p.player_id == 218 else (Outcome(0, 0, False) if p.player_id in (2, 7, 12, 15) else Outcome(2, 90, True)))
                    for p in sq22
                ),
            ),
        )
        assert tr22_card.gross == 19
        summary["b3_dev_gw1_7_and_full_gate"] = {
            **meta17,
            "full_1_to_38_first_blocked_gw": first_blocked_dev,
            "gw22_player_218_verified": {"minutes": gw22_218.minutes, "yellow_cards": gw22_218.yellow_cards, "points": gw22_218.points},
        }

        # B4: Historical Filter season GW1 prefix + GW1-38 fail-closed gate + cross-season native rules
        manifest_filter_path = CONFIG_ROOT / f"dev_mirror_{filter_season.replace('-', '_')}_manifest.json"
        manifest_filter = json.loads(manifest_filter_path.read_text(encoding="utf-8"))
        _, _, meta_filter = _replay_mirror_prefix(filter_season, [1], tmp, seed_filter_dir)
        first_blocked_filter = next(o["gw"] for o in manifest_filter["origins"] if not o["origin_admitted"])
        try:
            load_empirical_manifest_bundle(manifest_filter_path, quarantine_root=MIRROR_ROOT, prefix_end_gw=None, require_admitted=True)
            raise AssertionError("Expected full 1..38 filter manifest admission to fail closed")
        except ValueError as exc:
            assert f"GW{first_blocked_filter}" in str(exc)

        r_dev = get_rules(dev_season)
        assert next_free_transfers(r_dev, 1, 0, None, 15) == (5 if r_dev.afcon_gw15_topup else 2)
        assert next_free_transfers(get_rules(filter_season), 3, 1, "free_hit", 20) == 3
        assert next_free_transfers(get_rules(filter_seed), 2, 1, None, 10) == 2
        assert next_free_transfers(get_rules(filter_seed), 2, 0, "wildcard", 10) == 1
        summary["b4_filter_and_cross_season"] = {
            **meta_filter,
            "full_1_to_38_first_blocked_gw": first_blocked_filter,
            "afcon_gw15_ft": 5 if r_dev.afcon_gw15_topup else 2,
            "cross_season_rules_verified": sorted([s for s, e in lifecycle.seasons.items() if e.role != "sealed"]),
        }

    (MIRROR_ROOT / "stage_b_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def _sample_squad() -> tuple[Player, ...]:
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
