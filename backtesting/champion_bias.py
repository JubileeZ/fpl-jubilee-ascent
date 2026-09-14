"""Champion signed-bias record (ADR 0033). Bias = projected_points − actual_points."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import pandas as pd

from backtesting.walkforward import WalkforwardResult


def signed_bias(frame: pd.DataFrame) -> float:
    return float((frame["projected_points"] - frame["actual_points"]).mean())


def champion_bias_row(
    result: WalkforwardResult,
    *,
    evaluation_season: str,
    seed_season: str | None,
) -> dict[str, Any]:
    minutes = result.metrics.get("minutes_forecast_metrics") or {}
    return {
        "model": result.model_name,
        "evaluation_season": evaluation_season,
        "gw_start": result.start_gw,
        "gw_end": result.end_gw,
        "seed_season": seed_season or "",
        "sample_count": int(len(result.df_eval)),
        "signed_bias": signed_bias(result.df_eval),
        "mae": float((result.df_eval["projected_points"] - result.df_eval["actual_points"]).abs().mean()),
        "minutes_bias": float(minutes["bias"]) if "bias" in minutes else "",
        "snapshot_backed": str(result.snapshot_backed).lower(),
    }


def write_champion_bias_csv(path: Path, rows: list[dict[str, Any]]) -> Path:
    if not rows:
        raise ValueError("champion bias CSV needs at least one row")
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path
