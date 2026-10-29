"""Process Points: Realized score with goals/assists from Official expected events."""

from typing import cast

import pandas as pd

from models.scoring_matrix import Position, event_points

_POS_CODES = {1: "GK", 2: "D", 3: "M", 4: "F"}


def _numeric_col(frame: pd.DataFrame, name: str) -> pd.Series:
    if name not in frame.columns:
        return pd.Series(0.0, index=frame.index, dtype=float)
    return pd.to_numeric(frame[name], errors="coerce").fillna(0.0).astype(float)


def process_points_from_performances(gw_perf: pd.DataFrame, *, rules_version: str | None = None) -> pd.Series:
    """Return Process Points per row (fixture grain) given position_id on ``gw_perf``.

    ``total_points − realized goal pts − realized assist pts + xG pts + xA pts``.
    Requires ``position_id``, ``total_points``; missing goal/assist/xG/xA cols → 0.
    """
    if gw_perf.empty:
        return pd.Series(dtype=float)
    if rules_version is not None:
        from backtesting.season_rules import get_rules

        get_rules(rules_version)
        required = ("position_id", "total_points", "goals_scored", "assists", "expected_goals", "expected_assists")
        if any(col not in gw_perf or pd.to_numeric(gw_perf[col], errors="coerce").isna().any() for col in required):
            raise ValueError("Native process components incomplete")
        if not gw_perf["position_id"].isin(_POS_CODES).all():
            raise ValueError("Unknown native position")
    pos = gw_perf["position_id"].map(_POS_CODES).fillna("M")
    goals = _numeric_col(gw_perf, "goals_scored")
    assists = _numeric_col(gw_perf, "assists")
    xg = _numeric_col(gw_perf, "expected_goals")
    xa = _numeric_col(gw_perf, "expected_assists")
    total = _numeric_col(gw_perf, "total_points")
    realized_goal_pts = pd.Series(
        [event_points("goals", cast(Position, str(p)), float(q), rules_version=rules_version)
         for p, q in zip(pos, goals, strict=True)], index=gw_perf.index, dtype=float
    )
    realized_assist_pts = assists * 3.0
    process_goal_pts = pd.Series(
        [
            event_points("goals", cast(Position, str(p)), float(q), rules_version=rules_version)
            for p, q in zip(pos, xg, strict=True)
        ],
        index=gw_perf.index,
        dtype=float,
    )
    process_assist_pts = pd.Series(
        [
            event_points("assists", cast(Position, str(p)), float(q), rules_version=rules_version)
            for p, q in zip(pos, xa, strict=True)
        ],
        index=gw_perf.index,
        dtype=float,
    )
    return total - realized_goal_pts - realized_assist_pts + process_goal_pts + process_assist_pts


def aggregate_process_points(
    gw_perf: pd.DataFrame,
    *,
    player_col: str = "player_id",
    gameweek_col: str = "gameweek_id",
    rules_version: str | None = None,
) -> pd.DataFrame:
    """Sum Process Points to player/gameweek grain."""
    if gw_perf.empty:
        return pd.DataFrame(columns=[player_col, gameweek_col, "process_points"])
    frame = gw_perf.copy()
    frame["process_points"] = process_points_from_performances(frame, rules_version=rules_version)
    return (
        frame.groupby([player_col, gameweek_col], as_index=False)["process_points"]
        .sum()
    )


def blended_points(
    actual: pd.Series, process: pd.Series, weight: float = 0.5
) -> pd.Series:
    """Return Blended Eval Target: ``weight * process + (1 - weight) * actual``.

    Default 50/50 across all positions (ADR 0044). Eval-only; never a
    Feature Contract input.
    """
    if not 0.0 <= weight <= 1.0:
        raise ValueError(f"Blended Eval Target weight must be within [0, 1], got {weight}")
    return weight * process + (1.0 - weight) * actual
