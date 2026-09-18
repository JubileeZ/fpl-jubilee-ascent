"""Top-10k Effective Ownership aggregate and complete-only cache."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class EffectiveOwnershipResult:
    n: int
    by_player: dict[int, float]
    label: str


def overall_league_id(entry_summary: Mapping[str, Any]) -> int | None:
    classic = (entry_summary.get("leagues") or {}).get("classic") or []
    for league in classic:
        if str(league.get("short_name", "")).lower() == "overall":
            return int(league["id"])
    return None


def aggregate_effective_ownership(
    entry_pick_lists: Sequence[Sequence[Mapping[str, Any]]],
    *,
    rank_cap: int = 10_000,
) -> EffectiveOwnershipResult:
    """EO% = Σ multiplier / N × 100 for owned (1), C (2), TC (3)."""
    n = len(entry_pick_lists)
    if n == 0:
        return EffectiveOwnershipResult(n=0, by_player={}, label="Overall top 0")
    weights: dict[int, float] = {}
    for picks in entry_pick_lists:
        for pick in picks:
            pid = int(pick["element"])
            mult = float(pick.get("multiplier") or 0)
            if mult <= 0:
                continue
            weights[pid] = weights.get(pid, 0.0) + mult
    by_player = {pid: round(total / n * 100.0, 4) for pid, total in weights.items()}
    label = f"Overall top {n}" if n < rank_cap else f"Overall top {rank_cap}"
    return EffectiveOwnershipResult(n=n, by_player=by_player, label=label)


def load_complete_eo_cache(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict) or not payload.get("complete"):
        return None
    raw = payload.get("by_player") or {}
    by_player = {int(k): float(v) for k, v in raw.items()}
    return {
        "complete": True,
        "n": int(payload["n"]),
        "gameweek_id": int(payload["gameweek_id"]),
        "league_id": int(payload["league_id"]),
        "label": str(payload.get("label") or f"Overall top {payload['n']}"),
        "captured_at": str(payload.get("captured_at") or ""),
        "by_player": by_player,
    }


def save_complete_eo_cache(
    path: Path,
    *,
    n: int,
    gameweek_id: int,
    league_id: int,
    by_player: Mapping[int, float],
    label: str,
    captured_at: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "complete": True,
        "n": int(n),
        "gameweek_id": int(gameweek_id),
        "league_id": int(league_id),
        "label": label,
        "captured_at": captured_at,
        "by_player": {str(int(pid)): float(eo) for pid, eo in by_player.items()},
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
