"""Archive MILP adapter for First-Half Transfer Plan Walk-Forward (ADR 0020)."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

import pandas as pd

from backtesting.archive_static import (
    apply_deadline_prices,
    bootstrap_from_processed,
    fixtures_from_processed,
)
from backtesting.decision_regret import PlayerOutcome
from backtesting.strategy_policy import (
    FIRST_HALF_OAT_ARMS,
    Tilt,
    WalkforwardArm,
    apply_shape_to_type_data,
    locked_player_ids,
    winner_cross_arm,
)
from backtesting.transfer_plan_walkforward import (
    DeadlineWeekPlan,
    OutcomesForWeek,
    SolveWeek,
    run_walkforward_arm,
    summary_row,
)
from features.builder import build_features
from models import get_default_model_name, get_model
from projections.exporter import export_projections
from solver.solver import prep_data, solve_multi_period_fpl
from solver.utils import load_settings

FIRST_HALF_LAST_GW = 19
PLANNING_HORIZON = 5
GREENFIELD_BANK_TENTHS = 1000
_TILT_POSITIONS = frozenset({2, 3})


def clipped_horizon(
    deadline_gw: int,
    *,
    last_gw: int = FIRST_HALF_LAST_GW,
    horizon: int = PLANNING_HORIZON,
) -> int:
    remaining = int(last_gw) - int(deadline_gw) + 1
    return max(1, min(int(horizon), remaining))


def prices_at_deadline(performances: pd.DataFrame, gw: int) -> dict[int, int]:
    week = performances[performances["gameweek_id"] == int(gw)]
    if week.empty or "price" not in week.columns:
        return {}
    return {int(player_id): int(price) for player_id, price in week.groupby("player_id")["price"].last().items()}


def tilt_projected_points(predictions: pd.DataFrame, tilt: Tilt) -> pd.DataFrame:
    out = predictions.copy()
    if tilt is Tilt.VANILLA or "xp_defcon" not in out.columns:
        return out
    position = out["position_id"].astype(int)
    xp = out["projected_points"].astype(float)
    defcon = out["xp_defcon"].astype(float)
    mask = position.isin(_TILT_POSITIONS)
    if tilt is Tilt.DEFCON_FLOOR:
        out.loc[mask, "projected_points"] = xp[mask] + defcon[mask]
    else:
        out.loc[mask, "projected_points"] = xp[mask] - defcon[mask]
    return out


def walkforward_solver_options(
    arm: WalkforwardArm,
    *,
    deadline_gw: int,
    locked_ids: Sequence[int],
) -> dict[str, object]:
    options = load_settings()
    horizon = clipped_horizon(deadline_gw)
    gw1 = int(deadline_gw) == 1
    options.update({
        "horizon": horizon,
        "override_next_gw": int(deadline_gw),
        "preseason": gw1,
        "weekly_hit_limit": 0,
        "hit_limit": 0,
        "chip_limits": {"wc": 1 if gw1 else 0, "bb": 0, "fh": 0, "tc": 0},
        "use_wc": [int(deadline_gw)] if gw1 else [],
        "use_bb": [],
        "use_fh": [],
        "use_tc": [],
        "locked": [int(pid) for pid in locked_ids],
        "keep_top_ev_percent": 100,
        "xmin_lb": 0,
        "verbose": False,
        "delete_tmp": True,
        "num_iterations": 1,
        "datasource": get_default_model_name(),
    })
    return options


def deadline_my_data(
    deadline_gw: int,
    squad_ids: Sequence[int],
    owned: Mapping[int, Mapping[str, int]],
    ft_bank: int,
    *,
    bank: int = GREENFIELD_BANK_TENTHS,
) -> dict[str, object]:
    if int(deadline_gw) == 1:
        return {
            "picks": [],
            "chips": [],
            "team_id": None,
            "transfers": {"bank": int(bank), "limit": None, "made": 0, "cost": 4, "value": 0},
        }
    picks = []
    for player_id in squad_ids:
        meta = owned[int(player_id)]
        price = int(meta["price"])
        picks.append({
            "element": int(player_id),
            "purchase_price": price,
            "selling_price": price,
            "element_type": int(meta["position_id"]),
        })
    return {
        "picks": picks,
        "chips": [],
        "team_id": None,
        "transfers": {"bank": int(bank), "limit": int(ft_bank), "made": 0, "cost": 4, "value": 0},
    }


def plan_from_picks(picks: pd.DataFrame, deadline_gw: int) -> DeadlineWeekPlan:
    week = picks[(picks["week"] == int(deadline_gw)) & (picks["squad"] == 1)].copy()
    lineup = tuple(int(pid) for pid in week.loc[week["lineup"] == 1, "id"].tolist())
    bench_rows = week.loc[week["lineup"] != 1].sort_values("bench")
    bench = tuple(int(pid) for pid in bench_rows["id"].tolist())
    captain_id = int(week.loc[week["captain"] == 1, "id"].iloc[0])
    vice_id = int(week.loc[week["vicecaptain"] == 1, "id"].iloc[0])
    transfer_count = int(week["transfer_count"].iloc[0])
    squad_ids = tuple(int(pid) for pid in week["id"].tolist())
    return DeadlineWeekPlan(squad_ids, lineup, bench, captain_id, vice_id, transfer_count)


def outcomes_from_performances(
    performances: pd.DataFrame,
    players: pd.DataFrame,
    gw: int,
) -> dict[int, PlayerOutcome]:
    week = performances[performances["gameweek_id"] == int(gw)]
    if week.empty:
        aggregated = pd.DataFrame(columns=["player_id", "points", "minutes"])
    else:
        aggregated = (
            week.groupby("player_id", as_index=False)
            .agg(points=("total_points", "sum"), minutes=("minutes", "sum"))
        )
    points_map = {int(row.player_id): float(row.points) for row in aggregated.itertuples(index=False)}
    minutes_map = {int(row.player_id): float(row.minutes) for row in aggregated.itertuples(index=False)}
    outcomes: dict[int, PlayerOutcome] = {}
    for _, player in players.iterrows():
        player_id = int(player["id"])
        outcomes[player_id] = PlayerOutcome(
            player_id,
            int(player["position_id"]),
            points_map.get(player_id, 0.0),
            minutes_map.get(player_id, 0.0),
        )
    return outcomes


def run_first_half_ranking(
    *,
    gameweeks: Sequence[int],
    solve_week: SolveWeek,
    outcomes_for_week: OutcomesForWeek,
    arms: Sequence[WalkforwardArm] = FIRST_HALF_OAT_ARMS,
) -> list[dict[str, str]]:
    scores: dict[str, float] = {}
    rows: list[dict[str, str]] = []
    for arm in arms:
        points = run_walkforward_arm(
            arm,
            gameweeks,
            solve_week=solve_week,
            outcomes_for_week=outcomes_for_week,
        )
        scores[arm.arm_id] = points
        rows.append(summary_row(arm, points))
    best_shape = max((arm for arm in arms if arm.family == "shape"), key=lambda arm: scores[arm.arm_id])
    best_ft = max((arm for arm in arms if arm.family == "ft"), key=lambda arm: scores[arm.arm_id])
    best_tilt = max((arm for arm in arms if arm.family == "tilt"), key=lambda arm: scores[arm.arm_id])
    cross = winner_cross_arm(best_shape.locked_starting_shape, best_ft.transfer_target, best_tilt.tilt)
    if cross is not None:
        points = run_walkforward_arm(
            cross,
            gameweeks,
            solve_week=solve_week,
            outcomes_for_week=outcomes_for_week,
        )
        rows.append(summary_row(cross, points))
    return rows


def _owned_meta(
    squad_ids: Sequence[int],
    players: pd.DataFrame,
    prices: Mapping[int, int],
) -> dict[int, dict[str, int]]:
    position = players.set_index("id")["position_id"].to_dict()
    owned: dict[int, dict[str, int]] = {}
    for player_id in squad_ids:
        pid = int(player_id)
        owned[pid] = {
            "position_id": int(position[pid]),
            "price": int(prices.get(pid, int(players.loc[players["id"] == pid, "now_cost"].iloc[0]))),
        }
    return owned


def _lock_rows(
    squad_ids: Sequence[int],
    players: pd.DataFrame,
    projections: pd.DataFrame,
    deadline_gw: int,
) -> list[dict[str, object]]:
    week = projections[projections["gameweek_id"] == int(deadline_gw)] if "gameweek_id" in projections.columns else projections
    position = players.set_index("id")["position_id"].to_dict()
    rows: list[dict[str, object]] = []
    for player_id in squad_ids:
        pid = int(player_id)
        p_dnp = 0.0
        if not week.empty and "player_id" in week.columns:
            match = week[week["player_id"] == pid]
            if not match.empty and "p_dnp" in match.columns:
                p_dnp = float(match["p_dnp"].iloc[0])
        rows.append({"player_id": pid, "position_id": int(position[pid]), "p_dnp": p_dnp})
    return rows


def _project_deadline(processed_dir: Path, seed_dir: Path, deadline_gw: int, horizon: int) -> pd.DataFrame:
    features = build_features(
        processed_dir,
        target_gw=int(deadline_gw),
        horizon=horizon,
        seed_processed_dir=seed_dir,
        use_archive_seed=False,
        minutes_prior_source="seed_state",
        as_of_gw=int(deadline_gw),
    )
    model = get_model(get_default_model_name())
    performances = pd.read_parquet(processed_dir / "player_performances.parquet")
    if hasattr(model, "fit"):
        model.fit(performances[performances["gameweek_id"] < int(deadline_gw)])
    predicted = model.predict(features, horizon)
    if "position_id" not in predicted.columns:
        players = pd.read_parquet(processed_dir / "players.parquet")
        predicted = predicted.merge(
            players[["id", "position_id"]].rename(columns={"id": "player_id"}),
            on="player_id",
            how="left",
        )
    return predicted


def _run_milp(my_data: dict[str, object], options: dict[str, object], arm: WalkforwardArm) -> pd.DataFrame:
    data = prep_data(my_data, options)
    data["type_data"] = apply_shape_to_type_data(data["type_data"], arm.locked_starting_shape)
    solutions = solve_multi_period_fpl(data, options)
    picks = solutions[0]["picks"]
    if picks is None or getattr(picks, "empty", True) or "week" not in picks.columns:
        raise RuntimeError(f"MILP returned no picks for {arm.arm_id} GW{options.get('override_next_gw')}")
    return picks


def make_solve_week(
    *,
    processed_dir: Path,
    seed_dir: Path,
    work_dir: Path,
    project: Callable[[int, int], pd.DataFrame] | None = None,
    run_milp: Callable[[dict[str, object], dict[str, object], WalkforwardArm], pd.DataFrame] | None = None,
) -> SolveWeek:
    players = pd.read_parquet(processed_dir / "players.parquet")
    clubs = pd.read_parquet(processed_dir / "clubs.parquet")
    performances = pd.read_parquet(processed_dir / "player_performances.parquet")
    fixtures = fixtures_from_processed(processed_dir)
    project_fn = project or (lambda gw, horizon: _project_deadline(processed_dir, seed_dir, gw, horizon))
    milp_fn = run_milp or _run_milp
    projection_cache: dict[tuple[int, int], pd.DataFrame] = {}
    work_dir.mkdir(parents=True, exist_ok=True)

    def solve_week(gw: int, squad: tuple[int, ...], ft_bank: int, arm: WalkforwardArm) -> DeadlineWeekPlan:
        horizon = clipped_horizon(gw)
        cache_key = (int(gw), horizon)
        if cache_key not in projection_cache:
            projection_cache[cache_key] = project_fn(int(gw), horizon)
        tilted = tilt_projected_points(projection_cache[cache_key], arm.tilt)
        prices = prices_at_deadline(performances, gw)
        bootstrap = apply_deadline_prices(bootstrap_from_processed(processed_dir), prices)
        for event in bootstrap.get("events", []):
            event["is_next"] = int(event["id"]) == int(gw)
            event["finished"] = int(event["id"]) < int(gw)
        priced_players = players.copy()
        if prices:
            priced_players["now_cost"] = [
                int(prices.get(int(pid), int(cost)))
                for pid, cost in zip(priced_players["id"], priced_players["now_cost"], strict=False)
            ]
        if "projected_minutes" not in tilted.columns:
            tilted = tilted.copy()
            tilted["projected_minutes"] = 0.0
        csv_path = work_dir / f"proj_gw{gw}_{arm.arm_id}.csv"
        export_projections(tilted, priced_players, clubs, csv_path)
        locked = locked_player_ids(_lock_rows(squad, players, tilted, gw), arm.transfer_target)
        options = walkforward_solver_options(arm, deadline_gw=gw, locked_ids=locked)
        options["fpl_bootstrap"] = bootstrap
        options["fpl_fixtures"] = fixtures
        options["projections_path"] = str(csv_path)
        owned = _owned_meta(squad, players, prices)
        my_data = deadline_my_data(gw, squad, owned, ft_bank)
        picks = milp_fn(my_data, options, arm)
        return plan_from_picks(picks, gw)

    return solve_week
