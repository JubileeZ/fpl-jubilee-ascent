"""Dream Team: unconstrained legal 15 under current budget (ADR 0028)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from commands.export_dashboard import load_owned_picks, load_user_state
from projections.exporter import pad_solver_csv_horizon
from solver.paths import DATA_DIR
from solver.planning import clamp_planning_horizon
from solver.solver import prep_data, solve_multi_period_fpl
from solver.utils import load_settings

GREENFIELD_BUDGET_M = 100.0


def dream_team_budget_m(processed_dir: Path) -> float:
    """ITB + Selling Prices of the User Squad, or £100.0m when there is no User Squad."""
    owned_ids, _, _, pick_meta = load_owned_picks(processed_dir)
    if not owned_ids:
        return GREENFIELD_BUDGET_M
    itb, _ft = load_user_state(processed_dir)
    selling = 0.0
    for pid in owned_ids:
        meta = pick_meta.get(pid) or {}
        value = meta.get("selling_price")
        selling += float(value) if value is not None else 0.0
    return round(itb + selling, 1)


def dream_team_bank_tenths(processed_dir: Path) -> int:
    return int(round(dream_team_budget_m(processed_dir) * 10))


def dream_team_my_data(processed_dir: Path) -> dict[str, Any]:
    """Blank 15 with current purchasing power. Not a User Squad. Not --preseason ITB overwrite."""
    return {
        "picks": [],
        "chips": [],
        "transfers": {
            "bank": dream_team_bank_tenths(processed_dir),
            "limit": None,
            "cost": 4,
            "made": 0,
        },
    }


def dream_team_options(model_name: str, target_gw: int, horizon: int) -> dict[str, Any]:
    """Frozen unconstrained 15 on Primary Projection Model. No Available Chip gate."""
    options = load_settings()
    options["datasource"] = model_name
    options["horizon"] = clamp_planning_horizon(horizon)
    options["xmin_lb"] = 0
    options["keep_top_ev_percent"] = 100
    options["preseason"] = False
    options["no_trs_except_wc"] = True
    options["use_wc"] = [int(target_gw)]
    options["use_bb"] = []
    options["use_fh"] = []
    options["use_tc"] = []
    options["keep"] = []
    options["banned"] = []
    options["locked"] = []
    options["force_keep_gws"] = []
    options["force_ban_gws"] = []
    options["enabled_chip_windows"] = []
    options["allowed_chip_gws"] = {}
    options["forced_chip_gws"] = {}
    options["chip_limits"] = {"wc": 1, "bb": 0, "fh": 0, "tc": 0}
    options["secs"] = 90
    return options


def execute_dream_team(
    processed_dir: Path,
    *,
    model_name: str,
    target_gw: int,
    horizon: int,
) -> dict[str, Any]:
    """Run MILP for a Dream Team. Does not write the Dashboard Data Contract."""
    options = dream_team_options(model_name, target_gw, horizon)
    horizon = int(options["horizon"])
    options["override_next_gw"] = int(target_gw)
    budget = dream_team_budget_m(processed_dir)
    my_data = dream_team_my_data(processed_dir)
    pad_solver_csv_horizon(DATA_DIR / f"{options['datasource']}.csv", int(target_gw), horizon)
    solver_data = prep_data(my_data, options)
    solutions = solve_multi_period_fpl(solver_data, options)
    best_sol = solutions[0] if isinstance(solutions, list) and solutions else {}
    picks = best_sol.get("picks")
    player_ids: list[int] = []
    leftover_m: float | None = None
    if isinstance(picks, pd.DataFrame) and not picks.empty:
        week1 = picks[(picks["week"] == int(target_gw)) & (picks["squad"] == 1)]
        if week1.empty:
            week1 = picks[picks["squad"] == 1]
        player_ids = [int(i) for i in week1["id"].tolist()]
    stats = best_sol.get("statistics") or {}
    leftover = (stats.get(int(target_gw)) or stats.get(target_gw) or {}).get("itb")
    if leftover is not None:
        leftover_m = round(float(leftover), 1)
    return {
        "player_ids": player_ids,
        "budget": budget,
        "leftover": leftover_m,
        "model": model_name,
        "horizon_start": int(target_gw),
        "horizon": horizon,
    }

