from __future__ import annotations

import hashlib
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import pytest

from backtesting.input_evidence import (
    FieldEvidence, FreshnessRule, SourceEvidence, assess_field,
    load_receipt, retain_receipt, validate_player_inputs, validate_schedule_inputs,
)


def test_unknown_historical_capture_is_unresolved_not_invented() -> None:
    raw = b"retained inputs"
    source = SourceEvidence("historical", raw, hashlib.sha256(raw).hexdigest(),
                            "unknown", None, None, None, ("pinned-commit",))
    field = FieldEvidence("availability", source, (), "population-proof")
    assessment = assess_field(field, datetime(2025, 8, 22, 17, 30, tzinfo=timezone.utc))
    assert assessment.status == "unresolved"
    assert "capture_bounds_missing" in assessment.reasons
    assert assessment.promotion_authority is False


def test_bounded_reconstruction_can_be_supported_without_exact_capture() -> None:
    cutoff = datetime(2025, 8, 22, 17, 30, tzinfo=timezone.utc)
    source = SourceEvidence("bounded", b"input", hashlib.sha256(b"input").hexdigest(),
                            "bounded_reconstruction", cutoff.replace(hour=12), cutoff.replace(hour=13),
                            cutoff.replace(hour=14), ("reviewed-lineage-artifact",))
    field = FieldEvidence("price", source, (), "verified-universe", FreshnessRule(21600, "fixture-only", True))
    assert assess_field(field, cutoff).status == "supported"
    assert assess_field(replace(field, freshness=None), cutoff).status == "unresolved"
    crossing = replace(source, capture_upper=cutoff.replace(hour=18))
    assert "capture_crosses_cutoff" in assess_field(replace(field, source=crossing), cutoff).reasons
    future = replace(source, capture_lower=cutoff.replace(hour=18), capture_upper=cutoff.replace(hour=19))
    assert assess_field(replace(field, source=future), cutoff).status == "invalid"
    corrupted = replace(source, raw=b"changed")
    assert "source_identity_or_hash" in assess_field(replace(field, source=corrupted), cutoff).reasons


def test_invalid_players_and_unknown_chance_are_distinct() -> None:
    player = {"id": 1, "team": 2, "element_type": 3, "now_cost": 50,
              "status": "a", "chance_of_playing_next_round": None}
    assert validate_player_inputs([player], {2}) == ()
    broken = {**player, "now_cost": float("nan"), "chance_of_playing_next_round": 150}
    issues = validate_player_inputs([player, broken], {2})
    assert "duplicate_player_id" in issues
    assert "invalid_price" in issues
    assert "invalid_availability_chance" in issues
    assert player["chance_of_playing_next_round"] is None


def test_incomplete_schedule_is_not_a_blank_week() -> None:
    row = {"id": 1, "event": 2, "team_h": 1, "team_a": 2, "kickoff_time": "2025-08-22T19:00:00Z"}
    assert "schedule_target_coverage_missing" in validate_schedule_inputs([row], (2, 3), {1, 2})
    assert validate_schedule_inputs([row], (2, 3), {1, 2}, frozenset({3})) == ()
    assert "blank_with_fixture" in validate_schedule_inputs([row], (2,), {1, 2}, frozenset({2}))


def test_receipt_retains_bytes_and_local_clock_without_claiming_admission(tmp_path: Path) -> None:
    receipt = retain_receipt(tmp_path, season="test", gw=2, endpoint="bootstrap-static",
                             deadline=datetime(2000, 1, 1, tzinfo=timezone.utc), payload=b"raw receipt")
    loaded, raw = load_receipt(tmp_path, receipt["receipt_id"])
    assert raw == b"raw receipt"
    assert loaded["late"] is True
    assert loaded["promotion_authority"] is False
    assert loaded["source_capture_time"] is None
    (tmp_path / "raw" / receipt["payload_sha256"]).write_bytes(b"tampered")
    with pytest.raises(ValueError, match="hash"):
        load_receipt(tmp_path, receipt["receipt_id"])


def test_sealed_receipt_is_rejected_before_storage(tmp_path: Path) -> None:
    target = tmp_path / "untouched"
    with pytest.raises(ValueError, match="sealed"):
        retain_receipt(target, season="2026-27", gw=6, endpoint="fixtures",
                       deadline=datetime(2030, 1, 1, tzinfo=timezone.utc), payload=b"never store")
    assert not target.exists()


def test_outcome_source_cannot_support_issue_inputs() -> None:
    source = SourceEvidence("outcome", b"results", hashlib.sha256(b"results").hexdigest(),
                            "unknown", None, None, None, (), role="outcome")
    result = assess_field(FieldEvidence("price", source, (), None), datetime.now(timezone.utc))
    assert result.status == "invalid"
    assert "outcome_used_as_input" in result.reasons
