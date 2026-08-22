"""Planning Horizon, Chip Set, Force Keep/Ban, and dashboard-to-solver mapping."""

from __future__ import annotations

from typing import Any

CHIP_KEYS: tuple[str, ...] = ("wc", "bb", "fh", "tc")
CHIP_TO_OPTION: dict[str, str] = {
    "wc": "use_wc",
    "bb": "use_bb",
    "fh": "use_fh",
    "tc": "use_tc",
}
FPL_CHIP_TO_KEY: dict[str, str] = {
    "wildcard": "wc",
    "bboost": "bb",
    "benchboost": "bb",
    "freehit": "fh",
    "3xc": "tc",
    "triplecaptain": "tc",
}
MIN_PLANNING_HORIZON = 1
MAX_PLANNING_HORIZON = 5
CHIP_SET_1_END = 19
SEASON_END_GW = 38


def clamp_planning_horizon(horizon: int) -> int:
    return max(MIN_PLANNING_HORIZON, min(MAX_PLANNING_HORIZON, int(horizon)))


def planning_gameweeks(target_gw: int, horizon: int) -> list[int]:
    start = int(target_gw)
    length = clamp_planning_horizon(horizon)
    return [gw for gw in range(start, start + length) if 1 <= gw <= SEASON_END_GW]


def chip_set_for_gw(gameweek: int) -> int:
    return 1 if int(gameweek) <= CHIP_SET_1_END else 2


def chip_set_from_row(row: dict[str, Any]) -> int:
    if row.get("chip_set") in (1, 2):
        return int(row["chip_set"])
    start = row.get("start_event")
    stop = row.get("stop_event")
    number = row.get("number")
    if number in (1, 2):
        return int(number)
    if start is not None and int(start) >= 20:
        return 2
    if stop is not None and int(stop) <= CHIP_SET_1_END:
        return 1
    if start is not None and int(start) <= CHIP_SET_1_END:
        return 1
    return 1


def normalize_chip_key(name: str) -> str | None:
    raw = str(name).strip().lower().replace("_", "").replace("-", "")
    if raw in CHIP_KEYS:
        return raw
    return FPL_CHIP_TO_KEY.get(raw)


def _empty_booked() -> dict[str, list[int]]:
    return {CHIP_TO_OPTION[key]: [] for key in CHIP_KEYS}


def available_chips(
    planning_gws: list[int],
    user_chips: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return Available Chips for weeks in the Planning Horizon."""
    weeks_by_set: dict[int, list[int]] = {1: [], 2: []}
    for gw in planning_gws:
        weeks_by_set[chip_set_for_gw(gw)].append(int(gw))

    if not user_chips:
        preferred = 1 if weeks_by_set[1] else 2
        weeks = weeks_by_set[preferred]
        if not weeks:
            return []
        return [
            {"chip": chip, "chip_set": preferred, "gws": list(weeks)}
            for chip in CHIP_KEYS
        ]

    by_key: dict[tuple[str, int], str] = {}
    for row in user_chips:
        chip = normalize_chip_key(str(row.get("chip") or row.get("name") or ""))
        if chip is None:
            continue
        chip_set = chip_set_from_row(row)
        status = str(row.get("status") or "available").lower()
        by_key[(chip, chip_set)] = status

    out: list[dict[str, Any]] = []
    for chip_set, weeks in weeks_by_set.items():
        if not weeks:
            continue
        for chip in CHIP_KEYS:
            status = by_key.get((chip, chip_set))
            if status != "available":
                continue
            out.append({"chip": chip, "chip_set": chip_set, "gws": list(weeks)})
    return out


def booked_weeks(booked_chips: dict[str, list[int]]) -> dict[int, str]:
    used: dict[int, str] = {}
    for chip, option in CHIP_TO_OPTION.items():
        for gw in booked_chips.get(option, []):
            used[int(gw)] = chip
    return used


def validate_enabled_chips(
    enabled_chips: list[dict[str, Any]],
    booked_chips: dict[str, list[int]],
    planning_gws: list[int],
    available: list[dict[str, Any]],
) -> None:
    planning = set(int(gw) for gw in planning_gws)
    available_keys = {(c["chip"], c["chip_set"]) for c in available}
    booked: dict[int, str] = {}
    booked_set_keys: set[tuple[str, int]] = set()
    for chip, option in CHIP_TO_OPTION.items():
        for raw in booked_chips.get(option, []):
            gw = int(raw)
            if gw not in planning:
                raise ValueError(f"Booked Chip {chip} uses GW{gw} outside the Planning Horizon")
            if gw in booked:
                raise ValueError(f"at most one chip may be booked in GW{gw}")
            key = (chip, chip_set_for_gw(gw))
            if key not in available_keys:
                raise ValueError(f"{chip} Set {key[1]} is not an Available Chip")
            if key in booked_set_keys:
                raise ValueError(f"{chip} Set {key[1]} is booked more than once")
            booked[gw] = chip
            booked_set_keys.add(key)
    free_weeks = [gw for gw in planning_gws if gw not in booked]
    if len(enabled_chips) > len(free_weeks):
        raise ValueError(
            f"Enabled Chip count {len(enabled_chips)} exceeds free gameweeks {len(free_weeks)}"
        )
    seen_enabled: set[tuple[str, int]] = set()
    for item in enabled_chips:
        chip = str(item["chip"])
        chip_set = int(item["chip_set"])
        key = (chip, chip_set)
        if key in seen_enabled:
            raise ValueError(f"Enabled Chip {chip} Set {chip_set} listed twice")
        seen_enabled.add(key)
        if key not in available_keys:
            raise ValueError(f"{chip} Set {chip_set} is not an Available Chip")
        if key in booked_set_keys:
            raise ValueError(f"{chip} Set {chip_set} is already a Booked Chip")
        weeks = [gw for gw in planning_gws if chip_set_for_gw(gw) == chip_set and gw not in booked]
        if not weeks:
            raise ValueError(f"Enabled Chip {chip} Set {chip_set} has no free gameweek in the Planning Horizon")


def solver_options_from_plan(
    *,
    booked_chips: dict[str, list[int]],
    enabled_chips: list[dict[str, Any]],
    force_keep: list[dict[str, Any]],
    force_ban: list[dict[str, Any]],
    planning_gws: list[int],
    available: list[dict[str, Any]],
    horizon: int,
) -> dict[str, Any]:
    booked = {key: [int(g) for g in booked_chips.get(key, [])] for key in _empty_booked()}
    validate_enabled_chips(enabled_chips, booked, planning_gws, available)
    booked_by_gw = booked_weeks(booked)
    windows: list[dict[str, Any]] = []
    for item in enabled_chips:
        chip = str(item["chip"])
        chip_set = int(item["chip_set"])
        gws = [
            gw for gw in planning_gws
            if chip_set_for_gw(gw) == chip_set and gw not in booked_by_gw
        ]
        windows.append({"chip": chip, "chip_set": chip_set, "gws": gws})
    planning = set(int(gw) for gw in planning_gws)
    keep = [[int(row["player_id"]), int(row["gw"])] for row in force_keep]
    ban = [[int(row["player_id"]), int(row["gw"])] for row in force_ban]
    for label, rows in (("Force Keep", keep), ("Force Ban", ban)):
        for _player_id, gw in rows:
            if gw not in planning:
                raise ValueError(f"{label} GW{gw} is outside the Planning Horizon")
    return {
        "horizon": clamp_planning_horizon(horizon),
        **booked,
        "enabled_chip_windows": windows,
        "force_keep_gws": keep,
        "force_ban_gws": ban,
    }
