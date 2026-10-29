"""Unit tests for Phase 9 confirmation admission and attempt registry."""

from pathlib import Path
import pytest

from backtesting.confirmation_registry import (
    AdaptiveRunViolationError,
    ConfirmationRegistry,
    DeadLeverViolationError,
    DuplicateAttemptError,
    IncompleteScheduleError,
    SealedDataViolationError,
    TamperedRegistryError,
)


def _make_dummy_ledger(tmp_path: Path) -> Path:
    """Create a temporary test Candidate Ledger with an active dead lever."""
    ledger_path = tmp_path / "test_ledger.csv"
    content = (
        "status,lever,tried_as,baseline,result,evidence_date,revisit_after,evidence_path\n"
        "dead,Assist finishing offsets,off_k1800,hold_chase,FAIL,2026-09-28,2027-09-28,path/to/test\n"
        "shipped,Start-probability shrink,learned_start,hold_chase,PASS,2026-09-28,,path/to/test\n"
    )
    ledger_path.write_text(content, encoding="utf-8")
    return ledger_path


def test_registration_and_hash_integrity(tmp_path: Path) -> None:
    """Verify clean registration, persistence, and cryptographic verification."""
    reg_file = tmp_path / "registry.jsonl"
    registry = ConfirmationRegistry(reg_file)

    rec = registry.register_finalist(
        candidate_name="adaptive_causal_challenger",
        champion_name="def_xg_shrink_challenger",
        mechanism_family="causal_panel",
        model_source_hash="a" * 64,
        parameters_hash="b" * 64,
        dev_selection_record_ref="dev-2025-26-v1",
        protocol_hash="c" * 64,
        registered_gameweeks=tuple(range(1, 39)),
    )

    assert rec.status == "registered"
    assert rec.attempt_number_in_family == 1
    assert registry.verify_integrity() is True

    loaded = registry.get_attempt(rec.attempt_id)
    assert loaded is not None
    assert loaded.candidate_name == "adaptive_causal_challenger"
    assert loaded.record_hash == rec.record_hash


def test_tamper_detection(tmp_path: Path) -> None:
    """Verify registry raises TamperedRegistryError on modified disk record."""
    reg_file = tmp_path / "registry.jsonl"
    registry = ConfirmationRegistry(reg_file)

    registry.register_finalist(
        candidate_name="test_model",
        champion_name="champion",
        mechanism_family="test_fam",
        model_source_hash="1" * 64,
        parameters_hash="2" * 64,
        dev_selection_record_ref="dev-ref",
        protocol_hash="3" * 64,
    )

    # Tamper with file
    content = reg_file.read_text(encoding="utf-8")
    tampered = content.replace("test_model", "hacked_model")
    reg_file.write_text(tampered, encoding="utf-8")

    with pytest.raises(TamperedRegistryError, match="hash mismatch"):
        registry.load_all_records()


def test_duplicate_attempt_prevention(tmp_path: Path) -> None:
    """Verify duplicate finalist registration with identical code and config is blocked."""
    reg_file = tmp_path / "registry.jsonl"
    registry = ConfirmationRegistry(reg_file)

    registry.register_finalist(
        candidate_name="cand_a",
        champion_name="champ",
        mechanism_family="fam_a",
        model_source_hash="1" * 64,
        parameters_hash="2" * 64,
        dev_selection_record_ref="dev-1",
        protocol_hash="3" * 64,
    )

    with pytest.raises(DuplicateAttemptError, match="already registered"):
        registry.register_finalist(
            candidate_name="cand_a",
            champion_name="champ",
            mechanism_family="fam_a",
            model_source_hash="1" * 64,
            parameters_hash="2" * 64,
            dev_selection_record_ref="dev-1",
            protocol_hash="3" * 64,
        )


def test_alias_and_mechanism_family_lineage(tmp_path: Path) -> None:
    """Verify renamed models within the same mechanism family accumulate attempt counts and link parents."""
    reg_file = tmp_path / "registry.jsonl"
    registry = ConfirmationRegistry(reg_file)

    r1 = registry.register_finalist(
        candidate_name="causal_v1",
        champion_name="champ",
        mechanism_family="causal_ml",
        model_source_hash="1" * 64,
        parameters_hash="2" * 64,
        dev_selection_record_ref="dev-1",
        protocol_hash="3" * 64,
    )
    assert r1.attempt_number_in_family == 1

    r2 = registry.register_finalist(
        candidate_name="causal_v2_renamed",
        champion_name="champ",
        mechanism_family="causal_ml",
        model_source_hash="4" * 64,
        parameters_hash="5" * 64,
        dev_selection_record_ref="dev-2",
        protocol_hash="3" * 64,
        known_aliases=["causal_v1"],
    )
    assert r2.attempt_number_in_family == 2
    assert r2.parent_attempt_id == r1.attempt_id


def test_sealed_data_protection(tmp_path: Path) -> None:
    """Verify access to sealed 2026-27 GW6+ is strictly blocked."""
    reg_file = tmp_path / "registry.jsonl"
    registry = ConfirmationRegistry(reg_file)

    # Allowed: 2024-25
    registry.register_finalist(
        candidate_name="cand",
        champion_name="champ",
        mechanism_family="fam",
        model_source_hash="1" * 64,
        parameters_hash="2" * 64,
        dev_selection_record_ref="dev",
        protocol_hash="3" * 64,
        requested_seasons=["2024-25"],
    )

    # Allowed: 2026-27 GW 1-5 only
    registry.register_finalist(
        candidate_name="cand2",
        champion_name="champ",
        mechanism_family="fam2",
        model_source_hash="1" * 64,
        parameters_hash="2" * 64,
        dev_selection_record_ref="dev",
        protocol_hash="3" * 64,
        requested_seasons=["2026-27"],
        registered_gameweeks=(1, 2, 3, 4, 5),
    )

    # Blocked: 2026-27 GW6+
    with pytest.raises(SealedDataViolationError, match="sealed season 2026-27 GW6+"):
        registry.register_finalist(
            candidate_name="cand3",
            champion_name="champ",
            mechanism_family="fam3",
            model_source_hash="1" * 64,
            parameters_hash="2" * 64,
            dev_selection_record_ref="dev",
            protocol_hash="3" * 64,
            requested_seasons=["2026-27"],
            registered_gameweeks=tuple(range(1, 39)),
        )


def test_dead_lever_moratorium_enforcement(tmp_path: Path) -> None:
    """Verify candidate matching an active Dead Lever is blocked from confirmation registration."""
    reg_file = tmp_path / "registry.jsonl"
    ledger = _make_dummy_ledger(tmp_path)
    registry = ConfirmationRegistry(reg_file)

    with pytest.raises(DeadLeverViolationError, match="matches active Dead Lever"):
        registry.register_finalist(
            candidate_name="off_k1800",
            champion_name="champ",
            mechanism_family="assists",
            model_source_hash="1" * 64,
            parameters_hash="2" * 64,
            dev_selection_record_ref="dev",
            protocol_hash="3" * 64,
            ledger_csv_path=ledger,
        )


def test_stopping_rule_incomplete_schedule_rejection(tmp_path: Path) -> None:
    """Verify completing an attempt with partial schedule is rejected."""
    reg_file = tmp_path / "registry.jsonl"
    registry = ConfirmationRegistry(reg_file)

    rec = registry.register_finalist(
        candidate_name="cand",
        champion_name="champ",
        mechanism_family="fam",
        model_source_hash="1" * 64,
        parameters_hash="2" * 64,
        dev_selection_record_ref="dev",
        protocol_hash="3" * 64,
        registered_gameweeks=(1, 2, 3, 4, 5),
    )

    # Partial execution
    registry.transition_attempt_status(
        rec.attempt_id,
        status="in_progress",
        execution_status="partial",
        completed_gameweeks=(1, 2, 3),
    )

    # Stopping early when only 3 out of 5 GWs completed
    with pytest.raises(IncompleteScheduleError, match="does not match registered schedule"):
        registry.transition_attempt_status(
            rec.attempt_id,
            status="completed",
            execution_status="complete",
            completed_gameweeks=(1, 2, 3),
        )


def test_adaptive_reopen_completed_attempt_rejection(tmp_path: Path) -> None:
    """Verify completed attempt cannot be reopened or mutated."""
    reg_file = tmp_path / "registry.jsonl"
    registry = ConfirmationRegistry(reg_file)

    rec = registry.register_finalist(
        candidate_name="cand",
        champion_name="champ",
        mechanism_family="fam",
        model_source_hash="1" * 64,
        parameters_hash="2" * 64,
        dev_selection_record_ref="dev",
        protocol_hash="3" * 64,
        registered_gameweeks=(1, 2),
    )

    registry.transition_attempt_status(
        rec.attempt_id,
        status="completed",
        execution_status="complete",
        scientific_verdict="pass",
        completed_gameweeks=(1, 2),
        bundle_path="data/reports/bundle.json",
        human_approval_ref="APR-20261029-01",
    )

    with pytest.raises(AdaptiveRunViolationError, match="Cannot re-open or overwrite"):
        registry.transition_attempt_status(rec.attempt_id, status="in_progress")


def test_full_confirmation_lifecycle(tmp_path: Path) -> None:
    """Verify full valid confirmation lifecycle from registration to completion."""
    reg_file = tmp_path / "registry.jsonl"
    registry = ConfirmationRegistry(reg_file)

    rec = registry.register_finalist(
        candidate_name="adaptive_causal_challenger",
        champion_name="def_xg_shrink_challenger",
        mechanism_family="causal_panel",
        model_source_hash="a" * 64,
        parameters_hash="b" * 64,
        dev_selection_record_ref="dev-selection-123",
        protocol_hash="c" * 64,
        registered_gameweeks=(1, 2, 3),
    )

    step1 = registry.transition_attempt_status(
        rec.attempt_id,
        status="in_progress",
        execution_status="partial",
        completed_gameweeks=(1,),
    )
    assert step1.status == "in_progress"

    step2 = registry.transition_attempt_status(
        rec.attempt_id,
        status="completed",
        execution_status="complete",
        scientific_verdict="pass",
        completed_gameweeks=(1, 2, 3),
        bundle_path="data/reports/promotion_evidence/eval-123/bundle.json",
        human_approval_ref="APPROVAL-SIG-999",
    )
    assert step2.status == "completed"
    assert step2.scientific_verdict == "pass"
    assert step2.completed_at is not None

    all_records = registry.load_all_records()
    assert len(all_records) == 3
    assert registry.verify_integrity() is True
