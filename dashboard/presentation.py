"""Readable Player and planning metadata for both dashboard workspaces."""

from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any


def availability(player: dict[str, Any]) -> str:
    status = {"a": "Available", "d": "Doubtful", "i": "Injured", "s": "Suspended", "u": "Unavailable", "n": "Not available"}.get(str(player.get("status")), "Availability unknown")
    chance = player.get("chance")
    return f"{status} · Chance of playing: {chance}%" if chance is not None else f"{status} · Chance of playing: not supplied"


def fixture(cell: dict[str, Any]) -> str:
    label = re.sub(r"(\([HA]\))\s+\d+(?:\.\d+)?", r"\1", cell.get("fixture_label") or "")
    return label or "Unavailable / blank"


def utc_time(value: Any) -> datetime | None:
    try:
        stamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return stamp.astimezone(timezone.utc) if stamp.tzinfo else None
    except (ValueError, TypeError):
        return None


def data_age(value: Any) -> str:
    stamp = utc_time(value)
    if stamp is None:
        return "Projection export time unavailable; refresh to establish freshness."
    hours = max(0, int((datetime.now(timezone.utc) - stamp).total_seconds() / 3600))
    return f"Projections exported {stamp:%d %b %Y, %H:%M UTC} · {hours}h ago" + (" · older than 24h; review freshness" if hours >= 24 else "")
