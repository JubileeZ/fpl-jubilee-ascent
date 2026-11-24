"""Two-stage rolling-replay calibration runner for Strategic Free Transfer valuation (#229)."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
import json
from pathlib import Path
import sys
import time
from typing import Any, cast

import highspy
import pandas as pd

REPO = Path(__file__).resolve().parents[3]
IDEATION_DIR = REPO / "docs/research/candidate-ideation"
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
if str(IDEATION_DIR) not in sys.path:
    sys.path.insert(0, str(IDEATION_DIR))

from backtesting.native_transfer_solver import (  # noqa: E402
    _HEURISTIC_SEED_GAP,
    _LP_KERNEL_GAP,
    _LP_TIME_CAP,
    _LP_TIME_FRACTION,
    _SEED_AFTER_LP_CAP,
    _SEED_AFTER_LP_FRACTION,
    _SEED_AFTER_LP_MIN,
    _SEED_MIN_BUDGET_SECONDS,
    _SEED_MIN_CANDIDATES,
    _SEED_TIME_CAP,
    _SEED_TIME_FRACTION,
    _build_native_milp,
    _exact_undominated_ids,
    _forecast_universe,
    _inject_mip_start,
    _lp_kernel_candidate_ids,
    _seed_candidate_ids,
    _set_highs_heuristics,
    native_strategic_solve,
)
from backtesting.ownership_anchor import OwnershipAnchor, UniverseSchema, solve_ownership_anchor  # noqa: E402
from backtesting.replay_state import Decision, Lineup, OutcomeBatch, Player, ReplayState, state_hash, transition  # noqa: E402
from backtesting.rolling_replay import (  # noqa: E402
    DEFAULT_CERTIFIED_TIME_LIMIT_SECONDS,
    DEFAULT_HORIZON,
    SolverCertificate,
    UncertifiedSolveError,
    clipped_replay_horizon,
    get_strategic_replay_options,
    refresh_replay_market,
    replay_solver_binary_sha256,
    validate_decision_legality,
)
from backtesting.season_rules import Chip, get_rules, validate_chip_calendar  # noqa: E402
from commands.run_stage_a_and_b import _outcomes_for_gw  # noqa: E402
from historical_replay_inputs import stage_s1_inputs  # noqa: E402
from run_s1_replay import champion_factory, forecast  # noqa: E402
from s2_historical_replay_inputs import stage_s2_inputs  # noqa: E402
from solver.scenarios import effective_horizon_scale  # noqa: E402

ALLOWED_SEASONS = frozenset({"2025-26", "2024-25"})
DEFAULT_CACHE_ROOT = REPO / ".tmp/agent/strategic-ft-calibration"
OUTPUT_DIR = Path(__file__).resolve().parent

V2_GRID: tuple[float, ...] = (1.2, 1.6, 2.0, 2.4)
HOLD_WEIGHT_GRID: tuple[float, ...] = (0.0, 0.08, 0.15)
FT_USE_PENALTY_GRID: tuple[float, ...] = (0.2, 0.4, 0.6)
DIMINISHING_RATIOS: dict[str, float] = {"2": 1.0, "3": 0.6, "4": 0.3, "5": 0.1}
RAW_HIT_COST = 4.0


@dataclass(frozen=True)
class FTConfigSpec:
    """One experimental Strategic FT valuation configuration."""

    config_id: str
    v2: float
    spare_ft_hold_weight: float
    ft_use_penalty: float
    baseline_mode: bool = False
    waive_chip_ft_hold: bool = True
    decay_base: float = 0.85
    early_gw_end: int = 0
    early_v2: float | None = None
    early_spare_ft_hold_weight: float | None = None
    early_ft_use_penalty: float | None = None


def spec_for_gw(spec: FTConfigSpec, gw: int) -> FTConfigSpec:
    """Return active FTConfigSpec for a given GW, supporting two-phase early regimes."""
    if (
        spec.early_gw_end > 0
        and gw <= spec.early_gw_end
        and spec.early_v2 is not None
        and spec.early_spare_ft_hold_weight is not None
        and spec.early_ft_use_penalty is not None
    ):
        return FTConfigSpec(
            config_id=spec.config_id,
            v2=float(spec.early_v2),
            spare_ft_hold_weight=float(spec.early_spare_ft_hold_weight),
            ft_use_penalty=float(spec.early_ft_use_penalty),
            baseline_mode=spec.baseline_mode,
            waive_chip_ft_hold=spec.waive_chip_ft_hold,
            decay_base=spec.decay_base,
        )
    return spec


def validate_calibration_season(season: str) -> None:
    """Enforce ADR 0069 seal boundary: never inspect or tune on 2026-27."""
    if season not in ALLOWED_SEASONS:
        raise ValueError(
            f"Season {season!r} is barred from Strategic FT calibration; allowed={sorted(ALLOWED_SEASONS)}"
        )


def build_grid_configs() -> list[FTConfigSpec]:
    """Build ADR 0065 baseline + 36 unscaled experimental grid cells."""
    configs: list[FTConfigSpec] = [
        FTConfigSpec(
            config_id="baseline_adr0065",
            v2=2.0,
            spare_ft_hold_weight=0.325,
            ft_use_penalty=0.5,
            baseline_mode=True,
            waive_chip_ft_hold=False,
        )
    ]
    for v2 in V2_GRID:
        for w_hold in HOLD_WEIGHT_GRID:
            for p_use in FT_USE_PENALTY_GRID:
                cid = f"v2_{v2:.1f}_h_{w_hold:.2f}_u_{p_use:.1f}".replace(".", "p")
                configs.append(
                    FTConfigSpec(
                        config_id=cid,
                        v2=v2,
                        spare_ft_hold_weight=w_hold,
                        ft_use_penalty=p_use,
                        baseline_mode=False,
                        waive_chip_ft_hold=True,
                    )
                )
    return configs


def compute_ft_hurdles(
    v2: float,
    spare_ft_hold_weight: float,
    ft_use_penalty: float,
    *,
    decay_base: float = 0.85,
    scale_ft_by_horizon: bool = False,
) -> dict[str, Any]:
    """Compute exact discounted 2 -> 1 FT xP hurdles at H=6 and H=10."""
    out: dict[str, Any] = {}
    for horizon in (6, 10):
        scale = effective_horizon_scale(horizon, decay_base=decay_base)
        v2_eff = v2 * scale if scale_ft_by_horizon else v2
        h2 = spare_ft_hold_weight * v2
        perm = v2_eff + h2 * sum(decay_base**k for k in range(horizon - 1)) + ft_use_penalty
        delay1 = (1.0 - decay_base) * (v2_eff + h2 / (1.0 - decay_base) + ft_use_penalty)
        delay4 = (1.0 - decay_base**4) * (v2_eff + h2 / (1.0 - decay_base) + ft_use_penalty)
        out[f"perm_hurdle_h{horizon}"] = round(perm, 4)
        out[f"delay1_h{horizon}"] = round(delay1, 4)
        out[f"delay4_h{horizon}"] = round(delay4, 4)
    out["gate_hurdle_lt4"] = bool(
        out["perm_hurdle_h6"] < RAW_HIT_COST and out["perm_hurdle_h10"] < RAW_HIT_COST
    )
    return out


def build_legacy_adr0065_replay_options(
    horizon: int = DEFAULT_HORIZON,
    decay_base: float = 0.85,
    rules_version: str = "2024-25",
) -> dict[str, Any]:
    """Reproduce frozen pre-#231 ADR 0065 replay options for historical baseline comparisons."""
    base = get_strategic_replay_options(horizon, decay_base=decay_base, rules_version=rules_version)
    rules = get_rules(rules_version)
    scale = effective_horizon_scale(horizon, decay_base=decay_base)
    legacy_ft = {
        k: round(float(v) * scale, 4)
        for k, v in (("2", 2.0), ("3", 1.2), ("4", 0.6), ("5", 0.2))
        if int(k) <= rules.free_transfer_cap
    }
    return {
        **base,
        "horizon_scale": round(scale, 4),
        "ft_use_penalty": 0.5,
        "spare_ft_hold_weight": round(0.325 / scale, 4),
        "ft_value_list": legacy_ft,
    }


def build_experimental_options(
    spec: FTConfigSpec,
    horizon: int,
    rules_version: str,
) -> dict[str, Any]:
    """Assemble replay solver options for either frozen pre-#231 ADR 0065 baseline or unscaled cell."""
    if spec.baseline_mode:
        return build_legacy_adr0065_replay_options(
            horizon,
            decay_base=spec.decay_base,
            rules_version=rules_version,
        )
    rules = get_rules(rules_version)
    base = get_strategic_replay_options(
        horizon,
        decay_base=spec.decay_base,
        rules_version=rules_version,
    )
    ft_values = {
        k: round(spec.v2 * mult, 4)
        for k, mult in DIMINISHING_RATIOS.items()
        if int(k) <= rules.free_transfer_cap
    }
    return {
        **base,
        "ft_value_list": ft_values,
        "spare_ft_hold_weight": float(spec.spare_ft_hold_weight),
        "ft_use_penalty": float(spec.ft_use_penalty),
        "horizon_scale": 1.0,
        "true_horizon_scale": float(base["horizon_scale"]),
        "waive_chip_ft_hold": bool(spec.waive_chip_ft_hold),
    }


def experimental_native_solve(
    state: ReplayState,
    horizon: int,
    forecast_df: pd.DataFrame,
    options: dict[str, Any],
    *,
    baseline_mode: bool = False,
    require_optimal: bool = True,
) -> tuple[Decision, SolverCertificate]:
    """Solve 1..6-GW native Strategic MILP with optional unscaled FT & WC/FH hold waiver."""
    if baseline_mode and require_optimal:
        return native_strategic_solve(state, horizon, forecast_df, options)

    from backtesting.replay_state import validate_squad

    rules = get_rules(state.rules_version)
    validate_squad(state.squad, allow_club_overage=state.deadline > 1)
    if type(horizon) is not int or not 1 <= horizon <= 6 or state.deadline + horizon > 39:
        raise ValueError("Native replay horizon must contain one to six in-season deadlines")
    if state.rules_id != rules.rules_id or options.get("rules_version") != rules.version:
        raise ValueError("Native solver rule identity mismatch")
    if options.get("arm") != "strategic":
        raise ValueError("Native replay requires Strategic options")
    calendar = cast(
        tuple[tuple[int, Chip], ...],
        tuple(tuple(item) for item in options.get("chip_calendar", ())),
    )
    validate_chip_calendar(rules, calendar)
    chip_by_gw = dict(calendar)

    solve_t0 = time.perf_counter()
    players, xp, xmins = _forecast_universe(state, horizon, forecast_df)
    weeks = list(range(state.deadline, state.deadline + horizon))
    ids = _exact_undominated_ids(state, players, xp, xmins, weeks, options)
    target_gap = float(options.get("target_gap", 0.0))
    total_limit = float(options.get("time_limit_seconds", 60.0))

    seed_run_time = 0.0
    total_assembly_seconds = 0.0
    seed_model: highspy.Highs | None = None
    seed_vars: dict[str, Any] | None = None
    has_start = False
    if len(ids) > _SEED_MIN_CANDIDATES and total_limit >= _SEED_MIN_BUDGET_SECONDS:
        has_free_chip = any(chip_by_gw.get(gw) in ("wildcard", "free_hit") for gw in weeks)
        if has_free_chip:
            seed_ids, lp_run_time, lp_asm = _lp_kernel_candidate_ids(
                state,
                ids,
                weeks,
                players,
                xp,
                xmins,
                options,
                chip_by_gw,
                time_limit=min(_LP_TIME_CAP, _LP_TIME_FRACTION * total_limit),
            )
            seed_run_time += lp_run_time
            total_assembly_seconds += lp_asm
            seed_gap = max(target_gap, _LP_KERNEL_GAP)
            seed_budget = min(
                _SEED_AFTER_LP_CAP,
                max(_SEED_AFTER_LP_MIN, _SEED_AFTER_LP_FRACTION * (total_limit - seed_run_time)),
            )
        else:
            seed_ids = _seed_candidate_ids(state, ids, players, xp, xmins, weeks, options)
            seed_gap = max(target_gap, _HEURISTIC_SEED_GAP)
            seed_budget = min(_SEED_TIME_CAP, _SEED_TIME_FRACTION * total_limit)
        seed_model, seed_vars, seed_asm = _build_native_milp(
            state,
            weeks,
            players,
            xp,
            xmins,
            seed_ids,
            options,
            chip_by_gw,
            target_gap=seed_gap,
            time_limit=seed_budget,
            disable_submip=False,
        )
        total_assembly_seconds += seed_asm
        seed_model.run()
        seed_run_time += float(seed_model.getRunTime())
        has_start = (
            seed_model.getSolution().value_valid
            and seed_model.getInfo().primal_solution_status
            == highspy.SolutionStatus.kSolutionStatusFeasible
        )

    elapsed_wall = time.perf_counter() - solve_t0
    remaining_budget = (
        max(1e-3, min(total_limit - seed_run_time - 0.5, total_limit - elapsed_wall))
        if seed_model is not None
        else max(1e-3, total_limit)
    )
    model, hvars, full_asm = _build_native_milp(
        state,
        weeks,
        players,
        xp,
        xmins,
        ids,
        options,
        chip_by_gw,
        target_gap=target_gap,
        time_limit=remaining_budget,
        disable_submip=has_start,
    )
    assembly_time_seconds = round(total_assembly_seconds + full_asm, 6)
    if has_start and seed_model is not None and seed_vars is not None:
        if not _inject_mip_start(seed_model, seed_vars, model, hvars):
            _set_highs_heuristics(model, enabled=True)
    model.run()

    info = model.getInfo()
    status = model.getModelStatus()
    if (
        not model.getSolution().value_valid
        or info.primal_solution_status != highspy.SolutionStatus.kSolutionStatusFeasible
    ):
        raise UncertifiedSolveError(
            f"Native solve has no feasible incumbent: {model.modelStatusToString(status)}"
        )
    if require_optimal and (
        status != highspy.HighsModelStatus.kOptimal or float(info.mip_gap) > target_gap + 1e-8
    ):
        raise UncertifiedSolveError(
            f"Certified solve failed optimality at GW{state.deadline}: "
            f"{model.modelStatusToString(status)} gap={float(info.mip_gap)}"
        )

    def selected(values: Any, gw: int) -> tuple[int, ...]:
        return tuple(p for p in ids if model.val(values[p, gw]) > 0.5)

    gks = [p for p in ids if players[p].position == "GK"]
    outfield = [p for p in ids if players[p].position != "GK"]
    owned_ids = {p.player_id for p in state.squad}
    ft_states = list(range(rules.free_transfer_cap + 1))
    plans: list[dict[str, Any]] = []
    for gw in weeks:
        outgoing = tuple(
            p
            for p in ids
            if model.val(hvars["sell_new"][p, gw])
            + (model.val(hvars["sell_old"][p, gw]) if p in owned_ids else 0.0)
            > 0.5
        )
        incoming = selected(hvars["buy"], gw)
        plans.append(
            {
                "gw": gw,
                "transfers_out": outgoing,
                "transfers_in": incoming,
                "bank": round(model.val(hvars["bank"][gw])),
                "free_transfers": next(f for f in ft_states if model.val(hvars["ft"][gw, f]) > 0.5),
                "post_free_transfers": next(
                    f for f in ft_states if model.val(hvars["ft"][gw + 1, f]) > 0.5
                ),
                "chip": chip_by_gw.get(gw),
            }
        )
    first = weeks[0]
    starters = selected(hvars["start"], first)
    bench0_gk = next(p for p in gks if model.val(hvars["bench0"][p, first]) > 0.5)
    bench_slots = tuple(
        next(p for p in outfield if model.val(hvars["bench_out"][p, first, slot]) > 0.5)
        for slot in (1, 2, 3)
    )
    lineup = Lineup(
        starters=starters,
        bench=(bench0_gk, *bench_slots),
        captain=selected(hvars["captain"], first)[0],
        vice=selected(hvars["vice"], first)[0],
    )
    decision = Decision(
        tuple(zip(plans[0]["transfers_out"], (players[p] for p in plans[0]["transfers_in"]), strict=True)),
        lineup,
        state_hash(state),
        state.deadline,
        chip_by_gw.get(first),
    )
    objective_value, bound = model.getObjectiveValue(), float(info.mip_dual_bound)
    status_str = (
        "OPTIMAL"
        if status == highspy.HighsModelStatus.kOptimal
        else (
            "TIME_LIMIT"
            if status == highspy.HighsModelStatus.kTimeLimit
            else model.modelStatusToString(status).upper().replace(" ", "_")
        )
    )
    cert = SolverCertificate(
        True,
        objective_value,
        bound,
        abs(bound - objective_value),
        float(info.mip_gap),
        status_str,
        round(seed_run_time + float(model.getRunTime()), 6),
        1,
        42,
        f"highs-{model.version()}-native-ft-exp",
        "certified" if status == highspy.HighsModelStatus.kOptimal else "time_capped",
        {
            **options,
            "native_adapter": "native-ft-exp",
            "assembly_time_seconds": assembly_time_seconds,
            "plans": plans,
        },
        solver_binary_sha256=replay_solver_binary_sha256(),
    )
    return decision, cert


def compute_wasted_ft(
    rules_version: str,
    gw: int,
    pre_ft: int,
    n_transfers: int,
    chip: Chip | None,
) -> int:
    """Count wasted FTs at the 5-FT cap during in-season transition into GW+1."""
    if gw <= 1 or gw >= 38:
        return 0
    rules = get_rules(rules_version)
    if chip in ("wildcard", "free_hit"):
        return 0
    if rules.afcon_gw15_topup and gw == 15:
        return 0
    raw_next = max(pre_ft - n_transfers, 0) + 1
    return max(0, raw_next - rules.free_transfer_cap)


def compute_realized_4gw_transfer_gain(
    transfers_by_gw: list[tuple[int, Chip | None, tuple[tuple[int, Player], ...]]],
    actual_points: dict[tuple[int, int], int],
    total_hit_points: int,
) -> dict[str, float]:
    """Compute realized 4-GW net transfer gain across non-WC/FH transfers."""
    gains: list[int] = []
    for gw, chip, pairs in transfers_by_gw:
        if gw <= 1 or chip in ("wildcard", "free_hit"):
            continue
        horizon_end = min(gw + 4, 39)
        for sold_id, bought_player in pairs:
            gain = sum(
                actual_points.get((t, bought_player.player_id), 0)
                - actual_points.get((t, sold_id), 0)
                for t in range(gw, horizon_end)
            )
            gains.append(gain)
    total_gain = float(sum(gains))
    mean_gain = total_gain / float(len(gains)) if gains else 0.0
    return {
        "mean_4gw_transfer_gain": round(mean_gain, 4),
        "total_4gw_transfer_gain": round(total_gain, 4),
        "net_4gw_transfer_gain_after_hits": round(total_gain - float(total_hit_points), 4),
        "scored_non_chip_transfers": float(len(gains)),
    }


def _normalize_wide_forecast_types(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in ("player_id", "position_id", "club_id", "now_cost"):
        out[col] = out[col].astype(int)
    out["purchase_eligible"] = out["purchase_eligible"].astype(bool)
    return out


def prepare_season_cache(season: str, cache_root: Path = DEFAULT_CACHE_ROOT) -> Path:
    """Stage inputs and precompute Champion wide forecasts & outcomes for one season."""
    validate_calibration_season(season)
    season_dir = cache_root / season
    wide_dir = season_dir / "wide_forecasts"
    meta_path = season_dir / "meta.json"
    all_wide_ready = all((wide_dir / f"gw{gw:02d}.parquet").is_file() for gw in range(1, 39))
    if meta_path.is_file() and all_wide_ready:
        return season_dir

    season_dir.mkdir(parents=True, exist_ok=True)
    wide_dir.mkdir(parents=True, exist_ok=True)
    manifest, seed = (
        stage_s1_inputs(season_dir) if season == "2025-26" else stage_s2_inputs(season_dir)
    )
    anchor = solve_ownership_anchor(
        pd.read_parquet(season_dir / "verified_inputs/gw01/market.parquet"),
        season,
        gameweek=1,
        anchor_type="opening",
        schema=UniverseSchema(eligibility_col="purchase_eligible"),
    )
    deadlines = {int(origin["gw"]): str(origin["deadline_utc"]) for origin in manifest["origins"]}
    calendar = [
        [int(row["gameweek"]), str(row["chip"])]
        for row in manifest["shared_chip_calendar"]
    ]
    champ_name, factory, _ = champion_factory()
    if not all_wide_ready:
        proj_out = season_dir / "champ_projections"
        prior_forecasts: list[tuple[int, pd.DataFrame]] = []
        for gw in range(1, 39):
            wide_path = wide_dir / f"gw{gw:02d}.parquet"
            if wide_path.is_file():
                continue
            wide = forecast(
                season_dir,
                proj_out,
                factory,
                seed,
                gw,
                deadlines[gw],
                season=season,
                prior_forecasts=prior_forecasts,
            )
            wide.to_parquet(wide_path, index=False)

    meta = {
        "season": season,
        "champion": champ_name,
        "anchor": anchor.to_dict(),
        "chip_calendar": calendar,
    }
    meta_path.write_text(json.dumps(meta, indent=2, sort_keys=True), encoding="utf-8")
    return season_dir


def load_cached_season_bundle(
    season: str,
    cache_root: Path = DEFAULT_CACHE_ROOT,
) -> tuple[OwnershipAnchor, tuple[tuple[int, Chip], ...], dict[int, pd.DataFrame], dict[int, OutcomeBatch], dict[tuple[int, int], int]]:
    """Load precomputed anchor, chip calendar, wide forecasts, and outcomes from disk."""
    validate_calibration_season(season)
    season_dir = cache_root / season
    meta = json.loads((season_dir / "meta.json").read_text(encoding="utf-8"))
    anchor = OwnershipAnchor.from_dict(meta["anchor"])
    calendar = cast(
        tuple[tuple[int, Chip], ...],
        tuple((int(gw), cast(Chip, str(chip))) for gw, chip in meta["chip_calendar"]),
    )
    wide_by_gw = {
        gw: _normalize_wide_forecast_types(
            pd.read_parquet(season_dir / "wide_forecasts" / f"gw{gw:02d}.parquet")
        )
        for gw in range(1, 39)
    }
    outcomes_by_gw = {gw: _outcomes_for_gw(season, gw) for gw in range(1, 39)}
    actual_points: dict[tuple[int, int], int] = {}
    for gw, batch in outcomes_by_gw.items():
        for pid, outcome in batch.outcomes:
            actual_points[gw, pid] = int(outcome.points)
    return anchor, calendar, wide_by_gw, outcomes_by_gw, actual_points


def run_single_trajectory(
    spec: FTConfigSpec,
    season: str,
    *,
    cache_root: Path = DEFAULT_CACHE_ROOT,
    target_gap: float,
    time_limit_seconds: float,
    require_optimal: bool,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Execute full 38-GW rolling replay for one FT config and compute all metrics."""
    validate_calibration_season(season)
    anchor, calendar, wide_by_gw, outcomes_by_gw, actual_points = load_cached_season_bundle(
        season,
        cache_root=cache_root,
    )
    rules = get_rules(season)
    state = anchor.to_replay_state(season, rules_id=rules.rules_id)
    chip_by_gw = dict(calendar)

    wall_t0 = time.perf_counter()
    gw_rows: list[dict[str, Any]] = []
    transfers_by_gw: list[tuple[int, Chip | None, tuple[tuple[int, Player], ...]]] = []

    for gw in range(1, 39):
        forecast_df = wide_by_gw[gw]
        state = refresh_replay_market(state, forecast_df)
        eff_horizon = clipped_replay_horizon(gw, last_gw=38, horizon=DEFAULT_HORIZON)
        active_spec = spec_for_gw(spec, gw)
        options = build_experimental_options(active_spec, eff_horizon, season)
        options.update(
            chip_calendar=calendar,
            target_gap=float(target_gap),
            time_limit_seconds=float(time_limit_seconds),
        )
        decision, cert = experimental_native_solve(
            state,
            eff_horizon,
            forecast_df,
            options,
            baseline_mode=active_spec.baseline_mode,
            require_optimal=require_optimal,
        )
        validate_decision_legality(state, decision)
        tr = transition(state, decision, outcomes_by_gw[gw])
        chip = chip_by_gw.get(gw)
        n_transfers = len(decision.transfers)
        wasted = compute_wasted_ft(season, gw, state.free_transfers, n_transfers, chip)
        transfers_by_gw.append((gw, chip, decision.transfers))

        gw_rows.append(
            {
                "season": season,
                "config_id": spec.config_id,
                "gameweek": gw,
                "net_points": int(tr.net),
                "gross_points": int(tr.gross + tr.captain_increment),
                "hit_points": int(tr.hit),
                "paid_hits": int(tr.hit // 4),
                "pre_ft": int(state.free_transfers),
                "post_ft": int(tr.state.free_transfers),
                "transfers": int(n_transfers),
                "wasted_ft": int(wasted),
                "chip": chip or "",
                "runtime_seconds": float(cert.runtime_seconds),
                "relative_gap": float(cert.relative_gap),
                "termination_status": str(cert.termination_status),
            }
        )
        state = tr.state

    wall_elapsed = round(time.perf_counter() - wall_t0, 3)
    hurdles = compute_ft_hurdles(
        spec.v2,
        spec.spare_ft_hold_weight,
        spec.ft_use_penalty,
        decay_base=spec.decay_base,
        scale_ft_by_horizon=spec.baseline_mode,
    )
    has_early_phase = (
        spec.early_gw_end > 0
        and spec.early_v2 is not None
        and spec.early_spare_ft_hold_weight is not None
        and spec.early_ft_use_penalty is not None
    )
    if has_early_phase:
        early_hurdles = compute_ft_hurdles(
            float(spec.early_v2),
            float(spec.early_spare_ft_hold_weight),
            float(spec.early_ft_use_penalty),
            decay_base=spec.decay_base,
            scale_ft_by_horizon=spec.baseline_mode,
        )
        hurdles["gate_hurdle_lt4"] = bool(
            hurdles["gate_hurdle_lt4"] and early_hurdles["gate_hurdle_lt4"]
        )
        early_summary_fields: dict[str, Any] = {
            "early_gw_end": int(spec.early_gw_end),
            "early_v2": float(spec.early_v2),
            "early_spare_ft_hold_weight": float(spec.early_spare_ft_hold_weight),
            "early_ft_use_penalty": float(spec.early_ft_use_penalty),
            "early_perm_hurdle_h6": float(early_hurdles["perm_hurdle_h6"]),
            "early_perm_hurdle_h10": float(early_hurdles["perm_hurdle_h10"]),
        }
    else:
        early_summary_fields = {
            "early_gw_end": 0,
            "early_v2": None,
            "early_spare_ft_hold_weight": None,
            "early_ft_use_penalty": None,
            "early_perm_hurdle_h6": None,
            "early_perm_hurdle_h10": None,
        }
    non_chip_gws = [r for r in gw_rows if r["gameweek"] >= 2 and r["chip"] not in ("wildcard", "free_hit")]
    non_chip_post_gws = [
        r for r in non_chip_gws if r["gameweek"] <= 37
    ]
    early_non_chip = [r for r in non_chip_gws if 2 <= r["gameweek"] <= 12]
    late_non_chip = [r for r in non_chip_gws if 13 <= r["gameweek"] <= 38]

    total_net = sum(r["net_points"] for r in gw_rows)
    total_gross = sum(r["gross_points"] for r in gw_rows)
    total_hit_pts = sum(r["hit_points"] for r in gw_rows)
    total_paid_hits = sum(r["paid_hits"] for r in gw_rows)
    wasted_fts = sum(r["wasted_ft"] for r in gw_rows)
    total_non_chip_transfers = sum(r["transfers"] for r in non_chip_gws)
    gain_4gw = compute_realized_4gw_transfer_gain(transfers_by_gw, actual_points, total_hit_pts)

    summary = {
        "season": season,
        "config_id": spec.config_id,
        "baseline_mode": spec.baseline_mode,
        "v2": spec.v2,
        "spare_ft_hold_weight": spec.spare_ft_hold_weight,
        "ft_use_penalty": spec.ft_use_penalty,
        "waive_chip_ft_hold": spec.waive_chip_ft_hold,
        **early_summary_fields,
        **hurdles,
        "total_net_points": int(total_net),
        "total_gross_points": int(total_gross),
        "total_hit_points": int(total_hit_pts),
        "gw1_net": sum(r["net_points"] for r in gw_rows if r["gameweek"] == 1),
        "early_gw2_12_net": sum(r["net_points"] for r in gw_rows if 2 <= r["gameweek"] <= 12),
        "early_gw2_12_hits": sum(r["paid_hits"] for r in gw_rows if 2 <= r["gameweek"] <= 12),
        "mid_late_gw13_38_net": sum(r["net_points"] for r in gw_rows if 13 <= r["gameweek"] <= 38),
        "mid_late_gw13_38_hits": sum(r["paid_hits"] for r in gw_rows if 13 <= r["gameweek"] <= 38),
        "early_gw1_8_net": sum(r["net_points"] for r in gw_rows if 1 <= r["gameweek"] <= 8),
        "gw9_38_net": sum(r["net_points"] for r in gw_rows if 9 <= r["gameweek"] <= 38),
        "gw1_4_net": sum(r["net_points"] for r in gw_rows if 1 <= r["gameweek"] <= 4),
        "gw5_19_net": sum(r["net_points"] for r in gw_rows if 5 <= r["gameweek"] <= 19),
        "gw20_38_net": sum(r["net_points"] for r in gw_rows if 20 <= r["gameweek"] <= 38),
        "avg_ft_bank": round(
            sum(r["pre_ft"] for r in non_chip_gws) / float(len(non_chip_gws)), 4
        ),
        "avg_post_ft_bank": round(
            sum(r["post_ft"] for r in non_chip_post_gws) / float(len(non_chip_post_gws)), 4
        ),
        "non_chip_transfers_per_gw": round(
            total_non_chip_transfers / float(len(non_chip_gws)), 4
        ),
        "early_gw2_12_transfers_per_gw": round(
            sum(r["transfers"] for r in early_non_chip) / float(len(early_non_chip)), 4
        ),
        "mid_late_gw13_38_transfers_per_gw": round(
            sum(r["transfers"] for r in late_non_chip) / float(len(late_non_chip)), 4
        ),
        "total_non_chip_transfers": int(total_non_chip_transfers),
        "total_paid_hits": int(total_paid_hits),
        "hit_weeks": sum(1 for r in gw_rows if r["paid_hits"] > 0),
        "wasted_fts": int(wasted_fts),
        "gate_zero_wasted_ft": bool(wasted_fts == 0),
        "hard_gates_pass": bool(hurdles["gate_hurdle_lt4"] and wasted_fts == 0),
        **gain_4gw,
        "time_limit_gws": sum(1 for r in gw_rows if r["termination_status"] == "TIME_LIMIT"),
        "max_relative_gap": round(max(r["relative_gap"] for r in gw_rows), 6),
        "all_optimal": all(r["termination_status"] == "OPTIMAL" for r in gw_rows),
        "wall_seconds": wall_elapsed,
    }
    return summary, gw_rows


def _run_worker(task: tuple[FTConfigSpec, str, Path, float, float, bool]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    spec, season, cache_root, target_gap, time_limit, require_optimal = task
    return run_single_trajectory(
        spec,
        season,
        cache_root=cache_root,
        target_gap=target_gap,
        time_limit_seconds=time_limit,
        require_optimal=require_optimal,
    )


def select_stage2_finalists(stage1_df: pd.DataFrame, k: int = 5) -> list[str]:
    """Select top-k experimental cells passing both hard gates by S-1 net points."""
    exp = stage1_df[~stage1_df["baseline_mode"]].copy()
    passers = exp[exp["hard_gates_pass"]].sort_values(
        by=["total_net_points", "early_gw2_12_net", "total_paid_hits", "config_id"],
        ascending=[False, False, True, True],
    )
    chosen = passers["config_id"].tolist()[:k]
    if len(chosen) < k:
        fallback = exp[~exp["config_id"].isin(chosen)].sort_values(
            by=["total_net_points", "early_gw2_12_net", "config_id"],
            ascending=[False, False, True],
        )
        chosen.extend(fallback["config_id"].tolist()[: k - len(chosen)])
    return chosen


def _load_partial_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _append_partial_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def run_calibration(
    *,
    stage: str = "all",
    workers: int = 6,
    cache_root: Path = DEFAULT_CACHE_ROOT,
) -> None:
    """Execute Stage 1 fast S-1 sweep and/or Stage 2 certified S-1 + S-2 confirmation."""
    t0 = time.perf_counter()
    print("Preparing cached inputs for 2025-26 and 2024-25...", flush=True)
    prepare_season_cache("2025-26", cache_root=cache_root)
    if stage in ("all", "stage2"):
        prepare_season_cache("2024-25", cache_root=cache_root)

    all_configs = build_grid_configs()
    by_id = {c.config_id: c for c in all_configs}
    stage1_path = OUTPUT_DIR / "stage1_s1_grid.csv"

    if stage in ("all", "stage1"):
        partial_s1_path = cache_root / "stage1_partial.jsonl"
        prior_s1 = {r["config_id"]: r for r in _load_partial_jsonl(partial_s1_path)}
        stage1_rows: list[dict[str, Any]] = list(prior_s1.values())
        pending_s1 = [c for c in all_configs if c.config_id not in prior_s1]
        print(
            f"Stage 1: {len(pending_s1)} pending / {len(all_configs)} total on 2025-26 "
            f"(gap=0.005, limit=90s, workers={workers})...",
            flush=True,
        )
        tasks = [(c, "2025-26", cache_root, 0.005, 90.0, False) for c in pending_s1]
        if tasks:
            with ProcessPoolExecutor(max_workers=workers) as pool:
                futs = {pool.submit(_run_worker, t): t[0].config_id for t in tasks}
                for fut in as_completed(futs):
                    summary, _ = fut.result()
                    stage1_rows.append(summary)
                    _append_partial_jsonl(partial_s1_path, summary)
                    print(
                        f"[Stage 1] {summary['config_id']}: net={summary['total_net_points']} "
                        f"early={summary['early_gw2_12_net']} waste={summary['wasted_fts']} "
                        f"gate={summary['hard_gates_pass']} ({summary['wall_seconds']}s)",
                        flush=True,
                    )
        stage1_df = pd.DataFrame(stage1_rows).sort_values(
            by=["hard_gates_pass", "total_net_points", "early_gw2_12_net", "total_paid_hits", "config_id"],
            ascending=[False, False, False, True, True],
        )
        base_net = int(stage1_df.loc[stage1_df["config_id"] == "baseline_adr0065", "total_net_points"].iloc[0])
        stage1_df["delta_vs_baseline_net"] = stage1_df["total_net_points"] - base_net
        stage1_df.to_csv(stage1_path, index=False)
        print(f"Wrote {stage1_path} ({len(stage1_df)} rows)", flush=True)
    else:
        stage1_df = pd.read_csv(stage1_path)

    if stage in ("all", "stage2"):
        finalist_ids = select_stage2_finalists(stage1_df, k=5)
        stage2_ids = ["baseline_adr0065", *finalist_ids]
        partial_s2_path = cache_root / "stage2_partial.jsonl"
        prior_s2 = {(r["summary"]["season"], r["summary"]["config_id"]): r for r in _load_partial_jsonl(partial_s2_path)}
        stage2_rows: list[dict[str, Any]] = [item["summary"] for item in prior_s2.values()]
        gw_traj_rows: list[dict[str, Any]] = [g for item in prior_s2.values() for g in item["gws"]]
        pending_s2 = [
            (by_id[cid], season, cache_root, 0.0, DEFAULT_CERTIFIED_TIME_LIMIT_SECONDS, True)
            for season in ("2025-26", "2024-25")
            for cid in stage2_ids
            if (season, cid) not in prior_s2
        ]
        print(
            f"Stage 2: {len(pending_s2)} pending / {2 * len(stage2_ids)} total {stage2_ids} "
            "on 2025-26 & 2024-25 (gap=0.0, limit=600s)...",
            flush=True,
        )
        if pending_s2:
            with ProcessPoolExecutor(max_workers=workers) as pool:
                futs = {pool.submit(_run_worker, t): (t[1], t[0].config_id) for t in pending_s2}
                for fut in as_completed(futs):
                    summary, gws = fut.result()
                    stage2_rows.append(summary)
                    gw_traj_rows.extend(gws)
                    _append_partial_jsonl(partial_s2_path, {"summary": summary, "gws": gws})
                    print(
                        f"[Stage 2] {summary['season']} {summary['config_id']}: "
                        f"net={summary['total_net_points']} early={summary['early_gw2_12_net']} "
                        f"waste={summary['wasted_fts']} optimal={summary['all_optimal']} ({summary['wall_seconds']}s)",
                        flush=True,
                    )
        stage2_df = pd.DataFrame(stage2_rows)
        baselines = (
            stage2_df[stage2_df["config_id"] == "baseline_adr0065"]
            .set_index("season")["total_net_points"]
            .to_dict()
        )
        if baselines.get("2025-26") != 2167 or baselines.get("2024-25") != 2299:
            raise AssertionError(
                f"Baseline parity mismatch: expected S-1=2167 S-2=2299, got {baselines}"
            )
        stage2_df["delta_vs_baseline_net"] = stage2_df.apply(
            lambda r: int(r["total_net_points"]) - int(baselines[r["season"]]),
            axis=1,
        )
        base_early = (
            stage2_df[stage2_df["config_id"] == "baseline_adr0065"]
            .set_index("season")["early_gw2_12_net"]
            .to_dict()
        )
        stage2_df["delta_vs_baseline_early_gw2_12"] = stage2_df.apply(
            lambda r: int(r["early_gw2_12_net"]) - int(base_early[r["season"]]),
            axis=1,
        )
        stage2_df = stage2_df.sort_values(
            by=["season", "delta_vs_baseline_net", "config_id"],
            ascending=[False, False, True],
        )
        stage2_path = OUTPUT_DIR / "stage2_certified_finalists.csv"
        stage2_df.to_csv(stage2_path, index=False)

        traj_df = pd.DataFrame(gw_traj_rows).sort_values(
            by=["season", "config_id", "gameweek"],
            ascending=[False, True, True],
        )
        traj_path = OUTPUT_DIR / "stage2_gw_trajectories.csv"
        traj_df.to_csv(traj_path, index=False)
        print(f"Wrote {stage2_path} and {traj_path} in {time.perf_counter() - t0:.1f}s", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("stage1", "stage2", "all"), default="all")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--cache-root", type=Path, default=DEFAULT_CACHE_ROOT)
    args = parser.parse_args()
    run_calibration(stage=args.stage, workers=args.workers, cache_root=args.cache_root)


if __name__ == "__main__":
    main()
