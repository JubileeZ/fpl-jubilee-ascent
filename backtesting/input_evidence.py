"""Offline input evidence diagnostics. No empirical admission capability is issued."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal


@dataclass(frozen=True)
class SourceEvidence:
    source_id: str
    raw: bytes
    sha256: str
    timing_basis: Literal["receipt", "bounded_reconstruction", "unknown"]
    capture_lower: datetime | None
    capture_upper: datetime | None
    publication_upper: datetime | None
    references: tuple[str, ...]
    role: Literal["input", "outcome"] = "input"


@dataclass(frozen=True)
class FreshnessRule:
    max_age_seconds: int | None
    reference: str
    approved: bool


@dataclass(frozen=True)
class FieldEvidence:
    name: str
    source: SourceEvidence | None
    content_issues: tuple[str, ...]
    coverage_reference: str | None
    freshness: FreshnessRule | None = None
    limitations: tuple[str, ...] = ()


@dataclass(frozen=True)
class FieldAssessment:
    name: str
    status: Literal["supported", "unresolved", "invalid"]
    reasons: tuple[str, ...]
    limitations: tuple[str, ...]
    source_id: str | None = None
    promotion_authority: Literal[False] = False


def assess_field(field: FieldEvidence, cutoff: datetime) -> FieldAssessment:
    """Check supplied evidence claims, not independently certify their truth."""
    unresolved: list[str] = []
    invalid: list[str] = list(field.content_issues)
    if cutoff.utcoffset() is None:
        raise ValueError("Timezone-aware decision cutoff required")
    source = field.source
    if source is None:
        unresolved.append("source_missing")
    else:
        if source.role != "input":
            invalid.append("outcome_used_as_input")
        if not source.source_id or hashlib.sha256(source.raw).hexdigest() != source.sha256:
            invalid.append("source_identity_or_hash")
        if source.timing_basis not in ("receipt", "bounded_reconstruction", "unknown"):
            invalid.append("timing_basis_invalid")
        times = (source.capture_lower, source.capture_upper, source.publication_upper)
        if any(value is not None and value.utcoffset() is None for value in times):
            invalid.append("timestamp_timezone")
        else:
            lower, upper, publication = times
            if lower is None or upper is None:
                unresolved.append("capture_bounds_missing")
            elif lower > upper:
                invalid.append("capture_bounds_reversed")
            elif lower > cutoff:
                invalid.append("capture_after_cutoff")
            elif upper > cutoff:
                unresolved.append("capture_crosses_cutoff")
            if publication is None:
                unresolved.append("publication_bound_missing")
            elif publication > cutoff:
                unresolved.append("publication_crosses_cutoff")
            if source.timing_basis == "unknown":
                unresolved.append("timing_basis_unknown")
            if not source.references or any(not ref.strip() for ref in source.references):
                unresolved.append("timing_references_missing")
            rule = field.freshness
            if rule is None or not rule.reference.strip() or not rule.approved:
                unresolved.append("freshness_policy_unapproved")
            elif rule.max_age_seconds is not None:
                if type(rule.max_age_seconds) is not int or rule.max_age_seconds < 0:
                    invalid.append("freshness_limit_invalid")
                elif lower is not None and (cutoff - lower).total_seconds() > rule.max_age_seconds:
                    unresolved.append("source_stale")
    if not field.coverage_reference or not field.coverage_reference.strip():
        unresolved.append("coverage_or_lineage_unverified")
    status: Literal["supported", "unresolved", "invalid"] = (
        "invalid" if invalid else "unresolved" if unresolved else "supported"
    )
    return FieldAssessment(field.name, status, tuple(invalid + unresolved), field.limitations,
                           source_id=source.source_id if source else None)


def _integer(value: Any) -> int:
    if isinstance(value, bool) or float(value) != int(value):
        raise ValueError("Integer required")
    return int(value)


def validate_player_inputs(
    rows: Sequence[Mapping[str, Any]], clubs: set[int], *, require_ownership: bool = False,
) -> tuple[str, ...]:
    issues: set[str] = set()
    ids: set[int] = set()
    if not rows:
        issues.add("player_population_empty")
    for row in rows:
        try:
            player_id = _integer(row.get("id"))
            if player_id <= 0:
                raise ValueError("Player ID")
            if player_id in ids:
                issues.add("duplicate_player_id")
            ids.add(player_id)
        except (ValueError, TypeError, OverflowError):
            issues.add("invalid_player_id")
        try:
            if _integer(row.get("team")) not in clubs or _integer(row.get("element_type")) not in (1, 2, 3, 4):
                raise ValueError("Club/position")
        except (ValueError, TypeError, OverflowError):
            issues.add("invalid_club_or_position")
        try:
            price = row.get("now_cost")
            if price is None or isinstance(price, bool) or not math.isfinite(float(price)) or _integer(price) <= 0:
                raise ValueError("Price")
        except (ValueError, TypeError, OverflowError):
            issues.add("invalid_price")
        if not isinstance(row.get("status"), str) or not row["status"].strip():
            issues.add("availability_status_missing")
        chance = row.get("chance_of_playing_next_round")
        if chance is not None:
            try:
                if isinstance(chance, bool) or not 0 <= float(chance) <= 100:
                    raise ValueError("Chance")
            except (ValueError, TypeError, OverflowError):
                issues.add("invalid_availability_chance")
        if require_ownership:
            try:
                ownership = row.get("selected_by_percent")
                if ownership is None or isinstance(ownership, bool) or not 0 <= float(ownership) <= 100:
                    raise ValueError("Ownership")
            except (ValueError, TypeError, OverflowError):
                issues.add("opening_ownership_missing_or_invalid")
    return tuple(sorted(issues))


def validate_schedule_inputs(
    rows: Sequence[Mapping[str, Any]], horizon: tuple[int, ...], clubs: set[int],
    declared_blank_gws: frozenset[int] = frozenset(),
) -> tuple[str, ...]:
    issues: set[str] = set()
    ids: set[int] = set()
    represented: set[int] = set()
    for row in rows:
        try:
            gw = _integer(row.get("event"))
            if gw not in horizon:
                issues.add("fixture_outside_horizon")
            represented.add(gw)
            fixture = _integer(row.get("id"))
            home, away = _integer(row.get("team_h")), _integer(row.get("team_a"))
            if fixture <= 0 or fixture in ids:
                issues.add("invalid_or_duplicate_fixture_id")
            ids.add(fixture)
            if home not in clubs or away not in clubs or home == away:
                issues.add("invalid_fixture_clubs")
            kickoff = datetime.fromisoformat(str(row.get("kickoff_time")).replace("Z", "+00:00"))
            if kickoff.utcoffset() is None:
                issues.add("kickoff_timezone_missing")
        except (ValueError, TypeError, OverflowError):
            issues.add("fixture_input_missing_or_invalid")
    if set(horizon) - represented - declared_blank_gws:
        issues.add("schedule_target_coverage_missing")
    if represented & declared_blank_gws:
        issues.add("blank_with_fixture")
    if declared_blank_gws - set(horizon):
        issues.add("blank_outside_horizon")
    return tuple(sorted(issues))


def _scope(season: str, gw: int) -> None:
    if (season != "test" and not re.fullmatch(r"20\d{2}-\d{2}", season)) or type(gw) is not int or not 1 <= gw <= 38:
        raise ValueError("Invalid receipt scope")
    if season != "test" and (int(season[:4]) + 1) % 100 != int(season[-2:]):
        raise ValueError("Invalid season years")
    if season == "2026-27" and gw >= 6:
        raise ValueError("Receipt scope is sealed")


def _digest(value: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _receipt_storage(storage: Path) -> Path:
    resolved = storage.resolve()
    if any(part in {"archive", "2026-27", ".git", ".agents"} for part in resolved.parts):
        raise ValueError("Protected receipt storage")
    return resolved


def retain_receipt(
    storage: Path, *, season: str, gw: int, endpoint: Literal["bootstrap-static", "fixtures"],
    deadline: datetime, payload: bytes,
) -> dict[str, Any]:
    """Retain caller-supplied raw bytes with local receipt UTC; no HTTP or admission."""
    _scope(season, gw)
    storage = _receipt_storage(storage)
    if endpoint not in ("bootstrap-static", "fixtures") or deadline.utcoffset() is None or not isinstance(payload, bytes):
        raise ValueError("Invalid receipt input")
    received = datetime.now(timezone.utc)
    digest = hashlib.sha256(payload).hexdigest()
    record: dict[str, Any] = {
        "version": 1, "season": season, "gw": gw, "endpoint": endpoint,
        "source_url": f"https://fantasy.premierleague.com/api/{endpoint}/",
        "received_at": received.isoformat(), "deadline": deadline.isoformat(),
        "source_capture_time": None, "payload_sha256": digest, "payload_size": len(payload),
        "late": received > deadline, "promotion_authority": False,
    }
    receipt_id = _digest(record)
    record["receipt_id"] = receipt_id
    (storage / "raw").mkdir(parents=True, exist_ok=True)
    raw_path = storage / "raw" / digest
    try:
        with raw_path.open("xb") as handle:
            handle.write(payload)
    except FileExistsError:
        if raw_path.read_bytes() != payload:
            raise ValueError("Existing receipt hash mismatch") from None
    with (storage / f"{receipt_id}.json").open("x") as handle:
        handle.write(json.dumps(record, indent=2, sort_keys=True) + "\n")
    return record


def load_receipt(storage: Path, receipt_id: str) -> tuple[dict[str, Any], bytes]:
    storage = _receipt_storage(storage)
    if not re.fullmatch(r"[0-9a-f]{64}", receipt_id):
        raise ValueError("Invalid receipt ID")
    record = json.loads((storage / f"{receipt_id}.json").read_text())
    if not isinstance(record, dict) or record.get("receipt_id") != receipt_id:
        raise ValueError("Invalid receipt manifest")
    required = {"version", "season", "gw", "endpoint", "source_url", "received_at", "deadline",
                "source_capture_time", "payload_sha256", "payload_size", "late", "promotion_authority", "receipt_id"}
    if set(record) != required or record["version"] != 1 or record["promotion_authority"] is not False or record["source_capture_time"] is not None:
        raise ValueError("Invalid receipt contract")
    _scope(record["season"], record["gw"])
    if _digest({key: value for key, value in record.items() if key != "receipt_id"}) != receipt_id:
        raise ValueError("Receipt manifest hash mismatch")
    endpoint = record["endpoint"]
    received, deadline = (datetime.fromisoformat(record[key]) for key in ("received_at", "deadline"))
    if (endpoint not in ("bootstrap-static", "fixtures")
            or record["source_url"] != f"https://fantasy.premierleague.com/api/{endpoint}/"
            or received.utcoffset() is None or deadline.utcoffset() is None
            or type(record["late"]) is not bool or record["late"] != (received > deadline)):
        raise ValueError("Invalid receipt timing or endpoint")
    digest = record.get("payload_sha256")
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValueError("Invalid payload hash")
    raw = (storage / "raw" / digest).read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest or len(raw) != record["payload_size"]:
        raise ValueError("Receipt payload hash mismatch")
    return record, raw
