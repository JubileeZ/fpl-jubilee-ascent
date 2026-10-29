"""Versioned rule facts for the supported historical replay subset."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

Chip = Literal["wildcard", "free_hit", "bench_boost", "triple_captain"]


@dataclass(frozen=True)
class SeasonRules:
    version: str
    rules_id: str
    free_transfer_cap: int
    preserve_chip_transfers: bool
    goalkeeper_goal_points: int
    defensive_contributions: bool


_RULES = {
    "2023-24": SeasonRules("2023-24", "native-2023-24-v1", 2, False, 6, False),
    "2024-25": SeasonRules("2024-25", "native-2024-25-v1", 5, True, 10, False),
    "2025-26": SeasonRules("2025-26", "native-2025-26-v1", 5, True, 10, True),
}


def get_rules(version: str) -> SeasonRules:
    try:
        return _RULES[version]
    except KeyError as exc:
        raise ValueError(f"Unsupported rules version: {version}") from exc


def selling_price(purchase: int, market: int) -> int:
    if type(purchase) is not int or type(market) is not int or purchase <= 0 or market <= 0:
        raise ValueError("Prices must be positive tenths")
    return market if market <= purchase else purchase + (market - purchase) // 2


def chip_window(rules: SeasonRules, chip: Chip, gameweek: int) -> int:
    if chip not in ("wildcard", "free_hit", "bench_boost", "triple_captain"):
        raise ValueError("Unsupported chip")
    if type(gameweek) is not int or not 1 <= gameweek <= 38 or (chip == "free_hit" and gameweek == 1):
        raise ValueError("Chip unavailable at deadline")
    if chip == "wildcard":
        first_end = 20 if rules.version == "2023-24" else 19
        return 1 if gameweek <= first_end else 2
    if rules.version == "2025-26":
        return 1 if gameweek <= 19 else 2
    return 1


def validate_chip_calendar(rules: SeasonRules, calendar: tuple[tuple[int, Chip], ...]) -> None:
    seen_deadlines: set[int] = set()
    seen_chips: set[tuple[Chip, int]] = set()
    free_hits: set[int] = set()
    for gameweek, chip in calendar:
        window = chip_window(rules, chip, gameweek)
        if (gameweek == 1 and chip not in ("bench_boost", "triple_captain")) or gameweek in seen_deadlines or (chip, window) in seen_chips:
            raise ValueError("Invalid shared chip calendar")
        seen_deadlines.add(gameweek)
        seen_chips.add((chip, window))
        if chip == "free_hit":
            free_hits.add(gameweek)
    if any(gw + 1 in free_hits for gw in free_hits):
        raise ValueError("Consecutive Free Hits are unsupported")


def afcon_topup_known_at(issue_time: datetime) -> bool:
    if issue_time.tzinfo is None or issue_time.utcoffset() is None:
        raise ValueError("Issue time requires timezone")
    return issue_time.astimezone(UTC) >= datetime(2025, 7, 20, tzinfo=UTC)


def next_free_transfers(
    rules: SeasonRules, free_transfers: int, transfers: int, chip: Chip | None, gameweek: int
) -> int:
    if any(type(value) is not int for value in (free_transfers, transfers, gameweek)):
        raise ValueError("Transfer counters must be integers")
    if gameweek == 1:
        if free_transfers != 0 or transfers != 0 or chip not in (None, "bench_boost", "triple_captain"):
            raise ValueError("GW1 reference squad is locked")
        return 1
    if not 1 <= free_transfers <= rules.free_transfer_cap or transfers < 0 or not 1 <= gameweek <= 38:
        raise ValueError("Invalid transfer state")
    if chip not in (None, "wildcard", "free_hit", "bench_boost", "triple_captain"):
        raise ValueError("Unsupported chip")
    if rules.version == "2025-26" and gameweek == 15:
        return 5
    if chip in ("wildcard", "free_hit"):
        return free_transfers if rules.preserve_chip_transfers else 1
    return min(rules.free_transfer_cap, max(free_transfers - transfers, 0) + 1)
