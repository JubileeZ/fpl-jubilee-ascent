"""Versioned rule facts and ADR 0069 season lifecycle policy."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Literal

Chip = Literal["wildcard", "free_hit", "bench_boost", "triple_captain"]
SeasonRole = Literal["active_validation", "development", "historical_filter", "prior_seed_only", "sealed"]
AccessPurpose = Literal[
    "validation",
    "active_validation",
    "live_capture",
    "receipt",
    "ideation",
    "tuning",
    "dev",
    "historical_filter",
]
DEFAULT_LIFECYCLE_PATH = Path(__file__).resolve().parent.parent / "config" / "season_lifecycle.json"

_ALLOWED_ROLES_BY_PURPOSE: Mapping[AccessPurpose, frozenset[SeasonRole]] = {
    "validation": frozenset({"active_validation", "development", "historical_filter"}),
    "active_validation": frozenset({"active_validation"}),
    "live_capture": frozenset({"active_validation", "development", "historical_filter"}),
    "receipt": frozenset({"active_validation", "development", "historical_filter"}),
    "ideation": frozenset({"development"}),
    "tuning": frozenset({"development"}),
    "dev": frozenset({"development"}),
    "historical_filter": frozenset({"historical_filter"}),
}


@dataclass(frozen=True)
class SeasonLifecycleEntry:
    season: str
    role: SeasonRole
    cycle_slot: str
    prior_seed: str | None
    rules_id: str


@dataclass(frozen=True)
class SeasonLifecycle:
    active_season: str
    seasons: Mapping[str, SeasonLifecycleEntry]

    def season_for_role(self, role: SeasonRole) -> str:
        matches = [season for season, entry in self.seasons.items() if entry.role == role]
        if len(matches) != 1:
            raise ValueError(f"Expected unique season for role {role}, found {matches}")
        return matches[0]

    def role_of(self, season: str) -> SeasonRole:
        try:
            return self.seasons[season].role
        except KeyError as exc:
            raise ValueError(f"Unknown season in lifecycle config: {season}") from exc

    def sealed_seasons(self) -> frozenset[str]:
        return frozenset(season for season, entry in self.seasons.items() if entry.role == "sealed")

    def is_sealed_window(self, season: str, gw: int) -> bool:
        entry = self.seasons.get(season)
        return entry is not None and entry.role == "sealed"

    def assert_access(
        self,
        season: str,
        gw: int | None = None,
        *,
        purpose: AccessPurpose = "validation",
        allow_test: bool = True,
    ) -> None:
        if gw is not None and (type(gw) is not int or not 1 <= gw <= 38):
            raise ValueError("Invalid gameweek scope")
        if allow_test and season == "test":
            return
        entry = self.seasons.get(season)
        if entry is None:
            raise ValueError(f"Unknown or sealed scope: {season}")
        if entry.role == "sealed":
            raise ValueError(f"Sealed scope (sealed): {season}" + (f" GW{gw}" if gw is not None else ""))
        allowed_roles = _ALLOWED_ROLES_BY_PURPOSE[purpose]
        if entry.role not in allowed_roles:
            raise ValueError(f"Season {season} ({entry.role}) prohibits {purpose} access")

    def assert_unsealed_storage_path(
        self,
        path: Path,
        *,
        allow_archive: bool = False,
        error_message: str = "Protected storage path",
    ) -> Path:
        resolved = path.resolve()
        forbidden = {".git", ".agents", *self.sealed_seasons()} | (set() if allow_archive else {"archive"})
        if any(part in forbidden for part in resolved.parts):
            raise ValueError(error_message)
        return resolved


def load_season_lifecycle(path: Path | None = None) -> SeasonLifecycle:
    target = path or DEFAULT_LIFECYCLE_PATH
    payload = json.loads(target.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1 or not isinstance(payload.get("seasons"), dict):
        raise ValueError("Invalid season lifecycle schema")
    entries = {
        season: SeasonLifecycleEntry(
            season=season,
            role=spec["role"],
            cycle_slot=str(spec["cycle_slot"]),
            prior_seed=spec.get("prior_seed"),
            rules_id=str(spec["rules_id"]),
        )
        for season, spec in payload["seasons"].items()
    }
    return SeasonLifecycle(active_season=str(payload["active_season"]), seasons=entries)


@dataclass(frozen=True)
class SeasonRules:
    version: str
    rules_id: str
    free_transfer_cap: int
    preserve_chip_transfers: bool
    goalkeeper_goal_points: int
    defensive_contributions: bool
    two_chip_sets: bool = False
    afcon_gw15_topup: bool = False


_RULES = {
    "2023-24": SeasonRules("2023-24", "native-2023-24-v1", 2, False, 6, False, False, False),
    "2024-25": SeasonRules("2024-25", "native-2024-25-v1", 5, True, 10, False, False, False),
    "2025-26": SeasonRules("2025-26", "native-2025-26-v1", 5, True, 10, True, True, True),
    "2026-27": SeasonRules("2026-27", "native-2026-27-v1", 5, True, 10, True, True, False),
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
    if rules.two_chip_sets:
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
    if rules.afcon_gw15_topup and gameweek == 15:
        return 5
    if chip in ("wildcard", "free_hit"):
        return free_transfers if rules.preserve_chip_transfers else 1
    return min(rules.free_transfer_cap, max(free_transfers - transfers, 0) + 1)
