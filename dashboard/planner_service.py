"""Streamlit adapter for operational data and the existing transfer solver."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from dashboard.planner import Planner, digest
from features.builder import resolve_operational_processed_dir
from models import get_default_model_name
from solver.scenarios import (ARM_NAMES, apply_scenario_arm, compute_scenarios_digest,
                              find_protected_one_match_missed_starters, find_unowned_flagged_players)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class PlannerPaths:
    dataset: Path
    processed: Path
    storage: Path

    @classmethod
    def configured(cls) -> PlannerPaths:
        return cls(
            Path(os.environ.get("FPL_PLANNER_DATASET", PROJECT_ROOT / "dashboard/dashboard_data.json")),
            Path(os.environ["FPL_PLANNER_PROCESSED_DIR"]) if os.environ.get("FPL_PLANNER_PROCESSED_DIR") else resolve_operational_processed_dir(PROJECT_ROOT),
            Path(os.environ.get("FPL_PLANNER_STORAGE", PROJECT_ROOT / "data/planner")),
        )


def load_dataset(paths: PlannerPaths) -> dict[str, Any]:
    if not paths.dataset.exists():
        return {"meta": {}, "players": []}
    dataset = json.loads(paths.dataset.read_text(encoding="utf-8"))
    if not isinstance(dataset, dict) or not isinstance(dataset.get("players"), list):
        raise ValueError("Projection data invalid. Preserve file and refresh projections.")
    return dataset


def source_digest(paths: PlannerPaths) -> str:
    from solver.paths import DATA_DIR

    files = [paths.dataset, *(paths.processed / name for name in (
        "players.parquet", "user_picks.parquet", "user_state.parquet", "user_chips.parquet",
        "player_performances.parquet", "gameweeks.parquet")), DATA_DIR / f"{get_default_model_name()}.csv",
        DATA_DIR / "comprehensive_settings.json", DATA_DIR / "user_settings.json",
        PROJECT_ROOT / "data/raw/bootstrap_static.json", PROJECT_ROOT / "data/raw/fixtures_all.json"]
    return digest({str(path): hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None for path in files})


def make_solve_request(planner: Planner, paths: PlannerPaths) -> dict[str, Any]:
    if planner.stale:
        raise ValueError("Draft uses older squad/projections. Start a new plan from refreshed data before solving.")
    model = planner.dataset.get("meta", {}).get("default_model")
    if model is not None and model != get_default_model_name():
        raise ValueError("Projections use a different model from current Champion. Refresh before solving.")
    if paths.dataset.exists() and any(path.exists() and path.stat().st_mtime > paths.dataset.stat().st_mtime
                                     for path in (paths.processed / name for name in ("players.parquet", "user_picks.parquet", "user_state.parquet", "player_performances.parquet"))):
        raise ValueError("Operational data newer than projections. Refresh projections before solving.")
    weeks = planner.weeks()
    conflicts = [f"GW{week['gw']}: {message}" for week in weeks for message in week["conflicts"]]
    if conflicts:
        raise ValueError("Resolve draft before solving: " + "; ".join(dict.fromkeys(conflicts)))
    return {"kind": "solve", "state": planner.state, "dataset": planner.dataset,
            "snapshot": planner.snapshot(), "data_digest": planner.data_digest,
            "source_digest": source_digest(paths)}


def solver_options(planner: Planner, paths: PlannerPaths) -> dict[str, Any]:
    from commands.solve import transfer_plan_options_for_dashboard

    booked = {f"use_{chip}": [int(gw) for gw, value in planner.state["chips"].items() if value == chip]
              for chip in ("wc", "bb", "fh", "tc")}
    options = transfer_plan_options_for_dashboard(
        booked, planner.state["end"] - planner.state["start"] + 1,
        target_gw=planner.state["start"],
        available=planner.dataset.get("meta", {}).get("transfer_plan_available_chips", []),
    )
    options.update(gap=0.0, secs=1200, parallel="off", threads=1,
                   parent_state={"lineup": {"slots": {str(index): pid for index, pid in enumerate(planner.state["base_ids"], 1)}},
                                 "evaluation": {"bankRemaining": planner.state["base_bank"],
                                                "freeTransfersNext": planner.state["base_ft"]}})
    booked_transfers = []
    force_keep = []
    for gw, moves in planner.state["edits"].items():
        chip = planner.state["chips"].get(gw)
        if chip == "fh":
            force_keep.extend([pid, int(gw)] for pid in planner.week(int(gw))["squad_ids"])
        else:
            booked_transfers.extend({"gw": int(gw), "transfer_out": move["out"], "transfer_in": move["in"]} for move in moves)
    options["booked_transfers"] = booked_transfers
    for key, option in (("bench", "force_bench_gws"), ("captain", "force_captain_gws"), ("vice", "force_vice_gws")):
        pairs = []
        for gw, override in planner.state["overrides"].items():
            ids = override.get(key) or []
            if isinstance(ids, int):
                ids = [ids]
            pairs.extend([pid, int(gw)] for pid in ids)
        options[option] = pairs
        force_keep.extend(pairs)
    options["force_keep_gws"] = force_keep
    options["keep"] = sorted({pid for pid, _gw in force_keep})
    for key, filename in (("fpl_bootstrap", "bootstrap_static.json"), ("fpl_fixtures", "fixtures_all.json")):
        path = PROJECT_ROOT / "data/raw" / filename
        if path.exists():
            options[key] = json.loads(path.read_text(encoding="utf-8"))
    return options


def solve_request(request: dict[str, Any], paths: PlannerPaths) -> dict[str, Any]:
    from commands.solve import execute_transfer_plan

    if source_digest(paths) != request["source_digest"]:
        raise ValueError("Operational inputs changed before solve. Refresh and retry.")
    planner = Planner(request["dataset"], request["state"])
    options = solver_options(planner, paths)
    players = pd.read_parquet(paths.processed / "players.parquet")
    performance_path = paths.processed / "player_performances.parquet"
    performances = pd.read_parquet(performance_path) if performance_path.exists() else pd.DataFrame()
    owned = planner.state["base_ids"]
    flagged = find_unowned_flagged_players(players, owned)
    protected = find_protected_one_match_missed_starters(performances, owned)
    plans: dict[str, Any] = {}
    errors: dict[str, str] = {}
    run_directory = paths.storage / "solutions" / request["snapshot"]

    def solve_arm(arm: str) -> dict[str, Any]:
        arm_options = apply_scenario_arm(options, arm=arm, start_gw=planner.state["start"],
                                         free_transfer_bank=planner.state["base_ft"],
                                         banned_next_gw=flagged, locked_next_gw=protected)
        plan = execute_transfer_plan(arm_options, processed_dir=paths.processed,
                                     target_gw=planner.state["start"], solution_path=run_directory / f"{arm}.json")
        if not plan.get("weeks"):
            raise ValueError("No feasible plan returned. Revise transfer choices or scenario policy.")
        return plan

    with ThreadPoolExecutor(max_workers=3) as executor:
        pending = {executor.submit(solve_arm, arm): arm for arm in ARM_NAMES}
        for future in as_completed(pending):
            arm = pending[future]
            try:
                plans[arm] = future.result()
            except Exception as exc:
                errors[arm] = str(exc)
    if source_digest(paths) != request["source_digest"]:
        raise ValueError("Operational inputs changed during solve. Result files retained; refresh and retry.")
    if not plans:
        raise ValueError("No scenario solved: " + "; ".join(f"{ARM_NAMES[arm]}: {error}" for arm, error in errors.items()))
    return {"plans": plans, "errors": errors}


def import_cached_recommendations(planner: Planner, paths: PlannerPaths) -> bool:
    cached_path = PROJECT_ROOT / "data/transfer_plan_scenarios.json"
    if not cached_path.exists() or planner.state["recommendations"] or planner.state["edits"]:
        return False
    cached = json.loads(cached_path.read_text(encoding="utf-8"))
    expected = compute_scenarios_digest(processed_dir=paths.processed, target_gw=planner.state["start"],
                                        horizon=planner.state["end"] - planner.state["start"] + 1,
                                        champion=get_default_model_name(), gap=0.0)
    meta = cached.get("meta", {})
    if meta.get("data_digest") != expected or meta.get("status") != "ok" or meta.get("stale"):
        return False
    return planner.accept_recommendations({row["id"]: row["plan"] for row in cached.get("scenarios", [])},
                                           planner.snapshot(), planner.data_digest)


def refresh_request(request: dict[str, Any], paths: PlannerPaths) -> dict[str, Any]:
    from commands.export_dashboard import run_dashboard_export
    from commands.refresh_data import main

    if os.environ.get("FPL_PLANNER_PROCESSED_DIR"):
        raise ValueError("Live Refresh targets repository data. Clear custom processed path or refresh that dataset separately.")
    asyncio.run(main([]))
    run_dashboard_export(output_path=paths.dataset)
    return {"refreshed": True}


def player_history(paths: PlannerPaths, player_id: int) -> list[dict[str, Any]]:
    path = paths.processed / "player_performances.parquet"
    if not path.exists():
        return []
    data = pd.read_parquet(path)
    columns = [column for column in ("gameweek_id", "total_points", "minutes") if column in data.columns]
    if "player_id" not in data.columns or not columns:
        return []
    return data.loc[data["player_id"] == player_id, columns].sort_values(columns[0], ascending=False).head(6).to_dict("records")
