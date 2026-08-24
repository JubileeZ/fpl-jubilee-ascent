"""View-only Mix totals for Ownership Explorer."""

from __future__ import annotations

from typing import Any

MAX_MIX_SIZE = 5


def mix_comparable(left: list[Any], right: list[Any]) -> bool:
    return len(left) == len(right) and 1 <= len(left) <= MAX_MIX_SIZE


def mix_bundle(players: list[dict[str, Any]], planning_gws: list[int]) -> dict[str, Any]:
    if not 1 <= len(players) <= MAX_MIX_SIZE:
        raise ValueError(f"Mix size must be 1–{MAX_MIX_SIZE}")
    price = round(sum(float(p["price"]) for p in players), 1)
    per_gw: list[float] = []
    for gw in planning_gws:
        key = f"gw{gw}"
        week_total = 0.0
        for player in players:
            projections = player.get("projections") or {}
            week = projections.get(key) or {}
            week_total += float(week.get("total_xp") or 0.0)
        per_gw.append(round(week_total, 2))
    return {
        "size": len(players),
        "price": price,
        "per_gw": per_gw,
        "total": round(sum(per_gw), 2),
    }


def apply_mix_letter(
    mix_a: list[int],
    mix_b: list[int],
    player_id: int,
    side: str,
) -> tuple[list[int], list[int], str | None]:
    current = "a" if player_id in mix_a else "b" if player_id in mix_b else None
    next_a = [pid for pid in mix_a if pid != player_id]
    next_b = [pid for pid in mix_b if pid != player_id]
    if current == side:
        return next_a, next_b, None
    dest = next_a if side == "a" else next_b
    if len(dest) >= MAX_MIX_SIZE:
        label = "A" if side == "a" else "B"
        return list(mix_a), list(mix_b), f"Mix {label} is full (5)."
    dest.append(player_id)
    if side == "a":
        return dest, next_b, None
    return next_a, dest, None


def remove_mix_member(
    mix_a: list[int],
    mix_b: list[int],
    player_id: int,
) -> tuple[list[int], list[int], str | None]:
    next_a = [pid for pid in mix_a if pid != player_id]
    next_b = [pid for pid in mix_b if pid != player_id]
    return next_a, next_b, None


def move_mix_member(
    mix_a: list[int],
    mix_b: list[int],
    player_id: int,
    dest: str,
) -> tuple[list[int], list[int], str | None]:
    current = "a" if player_id in mix_a else "b" if player_id in mix_b else None
    if current is None or current == dest:
        return list(mix_a), list(mix_b), None
    return apply_mix_letter(mix_a, mix_b, player_id, dest)
