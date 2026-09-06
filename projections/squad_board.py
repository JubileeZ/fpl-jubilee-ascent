"""Squad What-If scoring for Ownership Explorer Squad Board."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

XI_MAX_INDEX = 11
CLUB_CAP = 3
STARTING_SHAPE = {
    "G": (1, 1),
    "D": (3, 5),
    "M": (2, 5),
    "F": (1, 3),
}


@dataclass(frozen=True)
class SquadSlot:
    player_id: int
    pos: str
    club_id: int
    lineup_index: int
    price: float
    selling_price: float
    gw_xp: dict[int, float]


def xi_slots(slots: list[SquadSlot]) -> list[SquadSlot]:
    return [slot for slot in slots if 1 <= slot.lineup_index <= XI_MAX_INDEX]


def _gw_xp(slot: SquadSlot, gameweek_id: int) -> float:
    return float(slot.gw_xp.get(gameweek_id, 0.0))


def auto_captain_id(slots: list[SquadSlot], gameweek_id: int) -> int | None:
    xi = xi_slots(slots)
    if not xi:
        return None
    return max(xi, key=lambda slot: (_gw_xp(slot, gameweek_id), -slot.lineup_index)).player_id


def auto_vice_captain_id(slots: list[SquadSlot], gameweek_id: int) -> int | None:
    captain = auto_captain_id(slots, gameweek_id)
    rest = [slot for slot in xi_slots(slots) if slot.player_id != captain]
    if not rest:
        return None
    return max(rest, key=lambda slot: (_gw_xp(slot, gameweek_id), -slot.lineup_index)).player_id


def squad_xp(slots: list[SquadSlot], gameweek_id: int) -> float:
    total = sum(_gw_xp(slot, gameweek_id) for slot in slots)
    captain = auto_captain_id(slots, gameweek_id)
    extra = next((_gw_xp(slot, gameweek_id) for slot in slots if slot.player_id == captain), 0.0)
    return round(total + extra, 2)


def itb_after_transfers(base_itb: float, owned: list[SquadSlot], what_if: list[SquadSlot]) -> float:
    owned_by_id = {slot.player_id: slot for slot in owned}
    what_if_by_id = {slot.player_id: slot for slot in what_if}
    sold = [owned_by_id[pid] for pid in owned_by_id if pid not in what_if_by_id]
    bought = [what_if_by_id[pid] for pid in what_if_by_id if pid not in owned_by_id]
    return round(base_itb + sum(slot.selling_price for slot in sold) - sum(slot.price for slot in bought), 1)


def hit_count(owned_ids: list[int], what_if_ids: list[int], free_transfers: int) -> int:
    transfers = len(set(what_if_ids) - set(owned_ids))
    return max(0, transfers - max(0, free_transfers))


def rule_breaches(slots: list[SquadSlot], itb: float) -> list[str]:
    breaches: list[str] = []
    if any(count > CLUB_CAP for count in Counter(slot.club_id for slot in slots).values()):
        breaches.append("club_cap")
    if itb < 0:
        breaches.append("itb")
    counts = Counter(slot.pos for slot in xi_slots(slots))
    shape_ok = all(
        lo <= counts.get(pos, 0) <= hi for pos, (lo, hi) in STARTING_SHAPE.items()
    ) and len(xi_slots(slots)) == XI_MAX_INDEX
    if not shape_ok:
        breaches.append("starting_shape")
    return breaches
