"""Run ranked Transfer Plan Scenarios for the dashboard."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from commands.export_dashboard import load_owned_picks, load_user_chips, load_user_state
from commands.solve import execute_transfer_plan, transfer_plan_options_for_dashboard
from models import get_default_model_name
from projections.expected_gw_score import player_gw_from_dashboard
from solver.planning import available_chips, clamp_planning_horizon, planning_gameweeks
from solver.scenarios import (
    ARM_NAMES,
    annotate_plan_with_egs,
    apply_scenario_arm,
    feasible_scenario_arms,
    rank_scenarios,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCENARIOS_PATH = PROJECT_ROOT / "data" / "transfer_plan_scenarios.json"
SOLUTION_PATH = PROJECT_ROOT / "data" / "solution.json"

ExecutePlan = Callable[..., dict]


class UserSquadRequired(ValueError):
    """Transfer Plan Scenarios need a live User Squad."""


def execute_transfer_plan_scenarios(
    *,
    processed_dir: Path,
    target_gw: int,
    horizon: int,
    dataset: dict[str, Any],
    booked_chips: dict[str, list[int]] | None = None,
    enabled_chips: list[dict[str, object]] | None = None,
    available: list[dict[str, object]] | None = None,
    execute_plan: ExecutePlan = execute_transfer_plan,
    scenarios_path: Path = SCENARIOS_PATH,
    solution_path: Path = SOLUTION_PATH,
) -> dict[str, Any]:
    owned_ids, _c, _v, _meta = load_owned_picks(processed_dir)
    if not owned_ids:
        raise UserSquadRequired(
            "Transfer Plan Scenarios need a User Squad. Refresh with FPL_EMAIL and FPL_PASSWORD."
        )
    _itb, free_transfers = load_user_state(processed_dir)
    horizon = clamp_planning_horizon(horizon)
    gws = planning_gameweeks(target_gw, horizon)
    chips = booked_chips or {"use_wc": [], "use_bb": [], "use_fh": [], "use_tc": []}
    user_chips = load_user_chips(processed_dir)
    base = transfer_plan_options_for_dashboard(
        chips,
        horizon,
        enabled_chips=enabled_chips or [],
        available=available if available is not None else available_chips(gws, user_chips),
        target_gw=target_gw,
    )
    lookup = player_gw_from_dashboard(dataset)
    rows: list[dict[str, Any]] = []
    for arm in feasible_scenario_arms(free_transfers):
        options = apply_scenario_arm(base, arm, start_gw=target_gw, free_transfer_bank=free_transfers)
        arm_path = scenarios_path.parent / f".arm_{arm}.json"
        try:
            plan = execute_plan(
                options,
                processed_dir=processed_dir,
                target_gw=target_gw,
                solution_path=arm_path,
            )
        finally:
            if arm_path.exists():
                arm_path.unlink()
        annotated = annotate_plan_with_egs(plan, lookup)
        rows.append(
            {
                "id": arm,
                "name": ARM_NAMES[arm],
                "horizon_egs": annotated["horizon_egs"],
                "solver_objective": (annotated.get("meta") or {}).get("solver_objective"),
                "plan": annotated,
            }
        )
    ranked = rank_scenarios(rows)
    payload = {
        "meta": {
            "champion": get_default_model_name(),
            "target_gw": int(target_gw),
            "horizon": horizon,
            "free_transfers": int(free_transfers),
            "arms": [arm for arm in feasible_scenario_arms(free_transfers)],
        },
        "scenarios": ranked,
    }
    scenarios_path.parent.mkdir(parents=True, exist_ok=True)
    scenarios_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    if ranked:
        solution_path.write_text(json.dumps(ranked[0]["plan"], indent=2), encoding="utf-8")
    return payload
