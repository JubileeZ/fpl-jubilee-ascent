"""FPL scoring matrix: maps Event Components x Position to fantasy points.

Pure stdlib, no I/O. See ADR-0003 and CONTEXT.md for vocabulary and intent.
"""

import math
from typing import Literal

Position = Literal["GK", "D", "M", "F"]
EventComponent = Literal[
    "minutes",
    "goals",
    "assists",
    "clean_sheets",
    "goals_conceded",
    "saves",
    "bonus",
    "yellow_cards",
    "red_cards",
    "penalties_saved",
    "penalties_missed",
    "own_goals",
]

_GOAL_POINTS: dict[Position, int] = {"F": 6, "M": 5, "D": 4, "GK": 4}
_CLEAN_SHEET_POINTS: dict[Position, int] = {"GK": 4, "D": 4, "M": 1, "F": 0}
# Goals-conceded deduction applies only to keepers and defenders.
_CONCEDES_POINTS: dict[Position, int] = {"GK": -1, "D": -1, "M": 0, "F": 0}


def event_points(component: EventComponent, position: Position, quantity: float) -> float:
    """Return FPL fantasy points for `quantity` of `component` by a player in `position`."""
    if component == "goals":
        return quantity * _GOAL_POINTS[position]
    if component == "assists":
        return quantity * 3.0
    if component == "clean_sheets":
        return quantity * _CLEAN_SHEET_POINTS[position]
    if component == "minutes":
        # ponytail: per-match thresholds (1-59=1, 60+=2); 0 mins=0. Fractional
        # expected minutes round to the band they fall in — fine for xP reconstruction.
        if quantity >= 60:
            return 2.0
        return 1.0 if quantity > 0 else 0.0
    if component == "goals_conceded":
        # ponytail: -1 per 2 conceded for GK/D, 0 for M/F. The "capped at 0 per match"
        # rule (conceded deduction can't take the match total below 0) is applied at
        # reconstruction when all components are summed, not in this per-component call.
        return _CONCEDES_POINTS[position] * math.floor(quantity / 2)
    if component == "saves":
        # ponytail: 1 pt per 3 saves, GK only.
        return math.floor(quantity / 3) if position == "GK" else 0.0
    if component == "bonus":
        return quantity
    if component == "yellow_cards":
        return quantity * -1.0
    if component == "red_cards":
        # ponytail: issue #77 specifies red=-2; official FPL is -3. Revisit if
        # reconstruction underfits red-card xP.
        return quantity * -2.0
    if component == "penalties_saved":
        return quantity * 5.0
    if component == "penalties_missed":
        return quantity * -2.0
    if component == "own_goals":
        return quantity * -2.0
    raise ValueError(f"Unknown event component: {component}")
