"""Dream Team and advanced solver workers using the shared dashboard queue."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from dashboard.planner_service import PlannerPaths, source_digest


def strategy_errors(start: int, options: dict[str, Any], names: dict[int, str] | None = None) -> list[str]:
    errors = []
    horizon = int(options.get("horizon", 6))
    if not 1 <= start <= 38 or not 1 <= horizon <= min(10, 39 - start):
        errors.append("Strategy horizon must contain 1–10 Gameweeks within GW1–38.")
    booked: dict[int, list[str]] = {}
    for chip, label in (("wc", "Wildcard"), ("fh", "Free Hit"), ("bb", "Bench Boost"), ("tc", "Triple Captain")):
        for gw in options.get(f"use_{chip}", []):
            if not start <= gw < start + horizon:
                errors.append(f"{label} lies outside strategy horizon. Choose a Gameweek inside the horizon or Unbooked.")
            booked.setdefault(gw, []).append(label)
    errors.extend(f"GW{gw}: {', '.join(chips)} conflict. Use one chip per Gameweek; move another chip or select Unbooked."
                  for gw, chips in booked.items() if len(chips) > 1)
    if overlap := set(options.get("locked", [])) & set(options.get("banned", [])):
        labels = ", ".join((names or {}).get(pid, f"Player {pid}") for pid in sorted(overlap))
        errors.append(f"Locked and banned: {labels}. Remove each Player from one list.")
    return errors


def run_tool(request: dict[str, Any], paths: PlannerPaths) -> dict[str, Any]:
    if request["source_digest"] != source_digest(paths):
        raise ValueError("Inputs changed before solve. Refresh this page and retry.")
    if request["kind"] == "dream_team":
        from commands.dream_team import execute_dream_team

        result = execute_dream_team(paths.processed, model_name=request["model"], target_gw=request["start"], horizon=request["horizon"])
    elif request["kind"] == "strategy":
        if errors := strategy_errors(request["start"], request["options"]):
            raise ValueError(" ".join(errors))
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
