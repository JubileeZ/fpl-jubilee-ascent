"""Process Points: Realized score with goals/assists from Official expected events."""

from typing import cast

import pandas as pd

from models.scoring_matrix import Position, event_points

_POS_CODES = {1: "GK", 2: "D", 3: "M", 4: "F"}
_GOAL_POINTS = {"GK": 10.0, "D": 6.0, "M": 5.0, "F": 4.0}


def process_points_from_performances(gw_perf: pd.DataFrame) -> pd.Series:
    """Return Process Points per row (fixture grain) given position_id on ``gw_perf``.

    ``total_points − realized goal pts − realized assist pts + xG pts + xA pts``.
    Requires ``position_id``, ``total_points``, ``goals_scored``, ``assists``,
    ``expected_goals``, ``expected_assists``.
    """
    if gw_perf.empty:
        return pd.Series(dtype=float)
    pos = gw_perf["position_id"].map(_POS_CODES).fillna("M")
    goals = pd.to_numeric(gw_perf.get("goals_scored", 0), errors="coerce").fillna(0.0)
    assists = pd.to_numeric(gw_perf.get("assists", 0), errors="coerce").fillna(0.0)
    xg = pd.to_numeric(gw_perf.get("expected_goals", 0), errors="coerce").fillna(0.0)
    xa = pd.to_numeric(gw_perf.get("expected_assists", 0), errors="coerce").fillna(0.0)
    total = pd.to_numeric(gw_perf["total_points"], errors="coerce").fillna(0.0)
    realized_goal_pts = goals * pos.map(_GOAL_POINTS)
    realized_assist_pts = assists * 3.0
    process_goal_pts = pd.Series(
        [
            event_points("goals", cast(Position, str(p)), float(q))
            for p, q in zip(pos, xg, strict=True)
        ],
        index=gw_perf.index,
        dtype=float,
    )
    process_assist_pts = pd.Series(
        [
            event_points("assists", cast(Position, str(p)), float(q))
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
) -> pd.DataFrame:
    """Sum Process Points to player/gameweek grain."""
    if gw_perf.empty:
        return pd.DataFrame(columns=[player_col, gameweek_col, "process_points"])
    frame = gw_perf.copy()
    frame["process_points"] = process_points_from_performances(frame)
    return (
        frame.groupby([player_col, gameweek_col], as_index=False)["process_points"]
        .sum()
    )
