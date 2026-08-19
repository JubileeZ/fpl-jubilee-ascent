"""Season Window and Score Mode slicing for the Ownership Explorer."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Literal

from models.scoring_matrix import Position, event_points

SeasonWindow = Literal["first_half", "second_half", "full_season"]
ScoreMode = Literal["all_projection", "realized_points", "remaining_projection"]

WINDOW_GAMEWEEKS: dict[SeasonWindow, tuple[int, ...]] = {
    "first_half": tuple(range(1, 20)),
    "second_half": tuple(range(20, 39)),
    "full_season": tuple(range(1, 39)),
}

COMPONENT_KEYS = (
    "xp_minutes",
    "xp_goals",
    "xp_assists",
    "xp_clean_sheet",
    "xp_conceded",
    "xp_defcon",
    "xp_saves",
    "xp_bonus",
)


def select_slice_gameweeks(
    season_window: SeasonWindow,
    score_mode: ScoreMode,
    finished_gameweeks: set[int],
) -> tuple[int, ...] | None:
    """Return gameweeks in the Score Mode slice, or None to hide Realized Points."""
    window = WINDOW_GAMEWEEKS[season_window]
    finished_in_window = tuple(gw for gw in window if gw in finished_gameweeks)
    unfinished_in_window = tuple(gw for gw in window if gw not in finished_gameweeks)
    if score_mode == "all_projection":
        return window
    if score_mode == "realized_points":
        return finished_in_window if finished_in_window else None
    if score_mode == "remaining_projection":
        return unfinished_in_window
    raise ValueError(f"unknown score_mode: {score_mode}")


@dataclass(frozen=True)
class GameweekScore:
    points: float
    minutes: float
    xp_minutes: float = 0.0
    xp_goals: float = 0.0
    xp_assists: float = 0.0
    xp_clean_sheet: float = 0.0
    xp_conceded: float = 0.0
    xp_defcon: float = 0.0
    xp_saves: float = 0.0
    xp_bonus: float = 0.0


@dataclass(frozen=True)
class SliceMetrics:
    total: float
    minutes: float
    avg_minutes: float
    rate_per_90: float | None
    per_gameweek: float
    n_gameweeks: int
    xp_minutes: float
    xp_goals: float
    xp_assists: float
    xp_clean_sheet: float
    xp_conceded: float
    xp_defcon: float
    xp_saves: float
    xp_bonus: float


def aggregate_slice(
    per_gw: Mapping[int, GameweekScore],
    slice_gws: tuple[int, ...],
) -> SliceMetrics:
    """Sum points, minutes, and Event Component xP over the Score Mode slice."""
    n = len(slice_gws)
    total = 0.0
    minutes = 0.0
    components = {key: 0.0 for key in COMPONENT_KEYS}
    for gw in slice_gws:
        row = per_gw.get(gw)
        if row is None:
            continue
        total += row.points
        minutes += row.minutes
        components["xp_minutes"] += row.xp_minutes
        components["xp_goals"] += row.xp_goals
        components["xp_assists"] += row.xp_assists
        components["xp_clean_sheet"] += row.xp_clean_sheet
        components["xp_conceded"] += row.xp_conceded
        components["xp_defcon"] += row.xp_defcon
        components["xp_saves"] += row.xp_saves
        components["xp_bonus"] += row.xp_bonus
    avg_minutes = round(minutes / n, 1) if n else 0.0
    rate_per_90 = round(total / (minutes / 90.0), 4) if minutes > 0 else None
    per_gameweek = round(total / n, 4) if n else 0.0
    return SliceMetrics(
        total=round(total, 2),
        minutes=round(minutes, 1),
        avg_minutes=avg_minutes,
        rate_per_90=rate_per_90,
        per_gameweek=per_gameweek,
        n_gameweeks=n,
        xp_minutes=round(components["xp_minutes"], 2),
        xp_goals=round(components["xp_goals"], 2),
        xp_assists=round(components["xp_assists"], 2),
        xp_clean_sheet=round(components["xp_clean_sheet"], 2),
        xp_conceded=round(components["xp_conceded"], 2),
        xp_defcon=round(components["xp_defcon"], 2),
        xp_saves=round(components["xp_saves"], 2),
        xp_bonus=round(components["xp_bonus"], 2),
    )


_POS_ID: dict[int, Position] = {1: "GK", 2: "D", 3: "M", 4: "F"}
_DEFCON_THRESHOLD: dict[Position, int] = {"GK": 10**9, "D": 10, "M": 12, "F": 12}


def _number(row: Mapping[str, Any], key: str, default: float = 0.0) -> float:
    value = row.get(key, default)
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def realized_gameweek_score(
    fixture_rows: Iterable[Mapping[str, Any]],
    position_id: int,
) -> GameweekScore:
    """Official points plus Event Component points from performance rows in one GW."""
    position = _POS_ID.get(position_id, "M")
    points = 0.0
    minutes = 0.0
    xp_minutes = 0.0
    xp_goals = 0.0
    xp_assists = 0.0
    xp_clean_sheet = 0.0
    xp_conceded = 0.0
    xp_defcon = 0.0
    xp_saves = 0.0
    xp_bonus = 0.0
    for row in fixture_rows:
        mins = _number(row, "minutes")
        points += _number(row, "total_points")
        minutes += mins
        xp_minutes += event_points("minutes", position, mins)
        xp_goals += event_points("goals", position, _number(row, "goals_scored"))
        xp_assists += event_points("assists", position, _number(row, "assists"))
        xp_clean_sheet += event_points("clean_sheets", position, _number(row, "clean_sheets"))
        xp_conceded += event_points("goals_conceded", position, _number(row, "goals_conceded"))
        defcon_count = _number(row, "defensive_contribution")
        defcon_hit = 1.0 if defcon_count >= _DEFCON_THRESHOLD[position] else 0.0
        xp_defcon += event_points("defensive_contributions", position, defcon_hit)
        xp_saves += event_points("saves", position, _number(row, "saves"))
        xp_bonus += event_points("bonus", position, _number(row, "bonus"))
    return GameweekScore(
        points=points,
        minutes=minutes,
        xp_minutes=xp_minutes,
        xp_goals=xp_goals,
        xp_assists=xp_assists,
        xp_clean_sheet=xp_clean_sheet,
        xp_conceded=xp_conceded,
        xp_defcon=xp_defcon,
        xp_saves=xp_saves,
        xp_bonus=xp_bonus,
    )


def build_explorer_slices(
    projection_by_gw: Mapping[int, GameweekScore],
    realized_by_gw: Mapping[int, GameweekScore],
    finished_gameweeks: set[int],
) -> dict[str, dict[str, dict[str, float | int | None] | None]]:
    """Precompute Season Window × Score Mode metrics for one Player."""
    out: dict[str, dict[str, dict[str, float | int | None] | None]] = {}
    for window in WINDOW_GAMEWEEKS:
        window_slices: dict[str, dict[str, float | int | None] | None] = {}
        for mode in ("all_projection", "realized_points", "remaining_projection"):
            slice_gws = select_slice_gameweeks(window, mode, finished_gameweeks)
            if slice_gws is None:
                window_slices[mode] = None
                continue
            source = realized_by_gw if mode == "realized_points" else projection_by_gw
            window_slices[mode] = slice_metrics_to_dict(aggregate_slice(source, slice_gws))
        out[window] = window_slices
    return out


def slice_metrics_to_dict(metrics: SliceMetrics) -> dict[str, float | int | None]:
    return {
        "total": metrics.total,
        "minutes": metrics.minutes,
        "avg_minutes": metrics.avg_minutes,
        "rate_per_90": metrics.rate_per_90,
        "per_gameweek": metrics.per_gameweek,
        "n_gameweeks": metrics.n_gameweeks,
        "xp_minutes": metrics.xp_minutes,
        "xp_goals": metrics.xp_goals,
        "xp_assists": metrics.xp_assists,
        "xp_clean_sheet": metrics.xp_clean_sheet,
        "xp_conceded": metrics.xp_conceded,
        "xp_defcon": metrics.xp_defcon,
        "xp_saves": metrics.xp_saves,
        "xp_bonus": metrics.xp_bonus,
    }
