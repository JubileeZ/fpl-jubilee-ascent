"""Differentials Ranking rows for Ownership Explorer (requires complete EO)."""

from __future__ import annotations

from typing import Any, Mapping, Sequence


def build_differentials_ranking(
    players: Sequence[Mapping[str, Any]],
    eo_by_player: Mapping[int, float],
    *,
    owned_ids: set[int],
    itb: float,
    owned_selling_prices: Mapping[int, float],
) -> list[dict[str, Any]]:
    """Non–User Squad shortlist: horizon xP ↓, EO ↑. Empty when no User Squad."""
    if not owned_ids:
        return []
    max_sell = max((float(v) for v in owned_selling_prices.values()), default=0.0)
    budget = float(itb) + max_sell
    rows: list[dict[str, Any]] = []
    for player in players:
        pid = int(player["id"])
        if pid in owned_ids:
            continue
        if pid not in eo_by_player:
            continue
        price = float(player.get("price") or 0.0)
        rows.append(
            {
                "id": pid,
                "name": str(player.get("name") or pid),
                "pos": str(player.get("pos") or ""),
                "team": str(player.get("team") or ""),
                "price": price,
                "total_xp_horizon": float(player.get("total_xp_horizon") or 0.0),
                "eo_pct": float(eo_by_player[pid]),
                "affordable": price <= budget + 1e-9,
            }
        )
    rows.sort(key=lambda row: (-row["total_xp_horizon"], row["eo_pct"], row["name"]))
    return rows
