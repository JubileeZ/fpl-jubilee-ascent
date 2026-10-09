"""Dream Team and advanced solver workers using the shared dashboard queue."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from dashboard.planner_service import PlannerPaths, source_digest


def run_tool(request: dict[str, Any], paths: PlannerPaths) -> dict[str, Any]:
    if request["source_digest"] != source_digest(paths):
        raise ValueError("Inputs changed before solve. Refresh this page and retry.")
    if request["kind"] == "dream_team":
        from commands.dream_team import execute_dream_team

        result = execute_dream_team(paths.processed, model_name=request["model"], target_gw=request["start"], horizon=request["horizon"])
    elif request["kind"] == "strategy":
        from commands.solve import execute_transfer_plan
        from solver.utils import load_settings

        options = load_settings()
        options.update(request["options"])
        options.update(gap=0.0, secs=1200, threads=1)
        result = execute_transfer_plan(options, processed_dir=paths.processed, target_gw=request["start"],
                                       solution_path=paths.storage / "strategy" / f"{uuid4().hex}.json")
    else:
        raise ValueError("Unknown dashboard job.")
    return {"payload": result, "stale": request["source_digest"] != source_digest(paths)}
