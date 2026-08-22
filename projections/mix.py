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
