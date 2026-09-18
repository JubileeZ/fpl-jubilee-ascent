"""Parallel Transfer Plan Scenarios with progressive disk payload."""

from __future__ import annotations

import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
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
ProgressCallback = Callable[[dict[str, Any]], None]


class UserSquadRequired(ValueError):
    """Transfer Plan Scenarios need a live User Squad."""


def serial_arm_options(options: dict[str, Any]) -> dict[str, Any]:
    """Each concurrent arm uses serial HiGHS (no nested parallel thrash)."""
    out = dict(options)
    out["parallel"] = "off"
    out["threads"] = 1
    return out


def write_scenarios_payload(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_scenarios_payload(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def mark_scenarios_stale(path: Path) -> dict[str, Any] | None:
    """Keep last scenarios after Dashboard Refresh; flag for re-solve."""
    payload = load_scenarios_payload(path)
    if payload is None:
        return None
    meta = dict(payload.get("meta") or {})
    meta["stale"] = True
    if meta.get("status") == "running":
        meta["status"] = "ok"
    payload = {**payload, "meta": meta}
    write_scenarios_payload(path, payload)
    return payload


def build_scenarios_payload(
    *,
    rows: list[dict[str, Any]],
    arms: tuple[str, ...],
    target_gw: int,
    horizon: int,
    free_transfers: int,
    status: str,
    stale: bool = False,
) -> dict[str, Any]:
    completed = [str(row["id"]) for row in rows]
    pending = [arm for arm in arms if arm not in set(completed)]
    ranked = rank_scenarios(rows) if rows else []
    return {
        "meta": {
            "champion": get_default_model_name(),
            "target_gw": int(target_gw),
            "horizon": int(horizon),
            "free_transfers": int(free_transfers),
            "arms": list(arms),
            "status": status,
            "stale": bool(stale),
            "completed_arms": completed,
            "pending_arms": pending,
        },
        "scenarios": ranked,
    }


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
    on_progress: ProgressCallback | None = None,
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
    arms = feasible_scenario_arms(free_transfers)
    completed: dict[str, dict[str, Any]] = {}
    publish_lock = threading.Lock()

    def publish(status: str) -> dict[str, Any]:
        with publish_lock:
            payload = build_scenarios_payload(
                rows=list(completed.values()),
                arms=arms,
                target_gw=target_gw,
                horizon=horizon,
                free_transfers=free_transfers,
                status=status,
                stale=False,
            )
            write_scenarios_payload(scenarios_path, payload)
            if status == "ok" and payload["scenarios"]:
                solution_path.parent.mkdir(parents=True, exist_ok=True)
                solution_path.write_text(
                    json.dumps(payload["scenarios"][0]["plan"], indent=2),
                    encoding="utf-8",
                )
            if on_progress is not None:
                on_progress(payload)
            return payload

    def solve_one(arm: str) -> dict[str, Any]:
        options = serial_arm_options(
            apply_scenario_arm(base, arm, start_gw=target_gw, free_transfer_bank=free_transfers)
        )
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
        return {
            "id": arm,
            "name": ARM_NAMES[arm],
            "horizon_egs": annotated["horizon_egs"],
            "solver_objective": (annotated.get("meta") or {}).get("solver_objective"),
            "plan": annotated,
        }

    publish("running")
    with ThreadPoolExecutor(max_workers=max(1, len(arms))) as pool:
        futures = {pool.submit(solve_one, arm): arm for arm in arms}
        for fut in as_completed(futures):
            row = fut.result()
            with publish_lock:
                completed[str(row["id"])] = row
            publish("running")
    return publish("ok")
