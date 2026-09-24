"""Champion Trust evidence for Explorer and Transfer Plan Surface."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from pandas.errors import EmptyDataError

from models.selection import load_model_selection


def _read_artifact(path: Path) -> pd.DataFrame | None:
    """Return artifact frame, or None when missing/unparseable (optional input)."""
    if not path.exists():
        return None
    try:
        return pd.read_csv(path)
    except EmptyDataError:
        return None

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BIAS = ROOT / "docs" / "research" / "champion-signed-bias-2025-26" / "champion_bias_summary.csv"
DEFAULT_WALKFORWARD = ROOT / "docs" / "research" / "tp-walkforward-gw1-19-2025-26" / "tp_walkforward_summary.csv"
DEFAULT_REGRET = ROOT / "data" / "reports" / "decision_regret.csv"


def _signed_bias_row(path: Path, champion: str) -> pd.Series | None:
    df = _read_artifact(path)
    if df is None:
        return None
    if df.empty or "model" not in df.columns:
        return None
    rows = df[df["model"].astype(str) == champion]
    if rows.empty:
        return None
    if {"evaluation_season", "gw_start", "gw_end"}.issubset(rows.columns):
        gate = rows[
            (rows["evaluation_season"].astype(str) == "2025-26")
            & (rows["gw_start"].astype(int) == 1)
            & (rows["gw_end"].astype(int) == 38)
        ]
        if not gate.empty:
            return gate.iloc[0]
    return rows.iloc[0]


def _walkforward(path: Path) -> tuple[str | None, float | None, list[dict[str, Any]]]:
    df = _read_artifact(path)
    if df is None:
        return None, None, []
    if df.empty or "realized_points" not in df.columns:
        return None, None, []
    ok = df if "status" not in df.columns else df[df["status"].astype(str) == "ok"]
    if ok.empty:
        return None, None, []
    ranked = ok.sort_values("realized_points", ascending=False)
    best = ranked.iloc[0]
    arm = str(best["arm_id"]) if "arm_id" in ranked.columns else None
    ranking: list[dict[str, Any]] = []
    for _, row in ranked.head(3).iterrows():
        ranking.append({
            "arm_id": str(row["arm_id"]) if "arm_id" in ranked.columns else "",
            "realized_points": round(float(row["realized_points"]), 2),
        })
    return arm, float(best["realized_points"]), ranking


def _regret_mean(path: Path) -> float | None:
    df = _read_artifact(path)
    if df is None:
        return None
    col = "model_regret" if "model_regret" in df.columns else None
    if col is None:
        return None
    series = pd.to_numeric(df[col], errors="coerce").dropna()
    if series.empty:
        return None
    return round(float(series.mean()), 4)


def load_champion_trust(
    *,
    selection_path: Path | None = None,
    bias_path: Path | None = None,
    walkforward_path: Path | None = None,
    regret_path: Path | None = None,
) -> dict[str, Any]:
    selection = load_model_selection(selection_path)
    bias_row = _signed_bias_row(bias_path or DEFAULT_BIAS, selection.champion)
    arm, points, ranking = _walkforward(walkforward_path or DEFAULT_WALKFORWARD)
    return {
        "champion": selection.champion,
        "promotion_status": selection.promotion_status,
        "signed_bias": None if bias_row is None else round(float(bias_row["signed_bias"]), 4),
        "bias_season": None if bias_row is None or "evaluation_season" not in bias_row else str(bias_row["evaluation_season"]),
        "walkforward_best_arm": arm,
        "walkforward_best_points": None if points is None else round(float(points), 2),
        "walkforward_ranking": ranking,
        "decision_regret_mean": _regret_mean(regret_path or DEFAULT_REGRET),
    }
