"""Unit tests for Phase 9 confirmation admission and attempt registry."""

from pathlib import Path
import pytest

from backtesting.confirmation_registry import (
    AdaptiveRunViolationError,
    AttemptStatus,
    ConfirmationRegistry,
    DeadLeverViolationError,
    DuplicateAttemptError,
    IncompleteScheduleError,
    SealedDataViolationError,
    TamperedRegistryError,
)
from backtesting.evidence_statistics import ScientificVerdict


def _register_attempt(registry: ConfirmationRegistry, attempt_id: str = "synthetic-attempt") -> str:
    return registry.register_finalist(
        candidate_name="synthetic-candidate",
        champion_name="synthetic-champion",
        mechanism_family="synthetic-family",
        model_source_hash="1" * 64,
        parameters_hash="2" * 64,
        dev_selection_record_ref="synthetic-development-record",
        protocol_hash="3" * 64,
        registered_gameweeks=(1, 2),
        attempt_id=attempt_id,
    ).attempt_id


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


def test_registry_hash_chaining_and_reorder_tamper_detection(tmp_path: Path) -> None:
    """Verify registry enforces cryptographic SHA-256 chain links and detects deletions/reordering."""
    reg_file = tmp_path / "chain_registry.jsonl"
    registry = ConfirmationRegistry(reg_file)

    rec1 = registry.register_finalist(
        candidate_name="cand_1",
        champion_name="champ",
        mechanism_family="fam_1",
        model_source_hash="1" * 64,
        parameters_hash="1" * 64,
        dev_selection_record_ref="dev-1",
        protocol_hash="p1" + "0" * 62,
    )
    rec2 = registry.register_finalist(
        candidate_name="cand_2",
        champion_name="champ",
        mechanism_family="fam_2",
        model_source_hash="2" * 64,
        parameters_hash="2" * 64,
        dev_selection_record_ref="dev-2",
        protocol_hash="p2" + "0" * 62,
    )

    assert rec1.prev_record_hash == "0" * 64
    assert rec2.prev_record_hash == rec1.record_hash
    assert registry.verify_integrity() is True

    # Reorder lines in jsonl file
    lines = reg_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    reordered = f"{lines[1]}\n{lines[0]}\n"
    reg_file.write_text(reordered, encoding="utf-8")

    with pytest.raises(TamperedRegistryError, match="Cryptographic chain break"):
        registry.load_all_records()

    # Deleting an earlier record breaks the chain
    reg_file.write_text(f"{lines[1]}\n", encoding="utf-8")
    with pytest.raises(TamperedRegistryError, match="Cryptographic chain break"):
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


def test_attempt_id_cannot_be_reassigned_across_families(tmp_path: Path) -> None:
    registry = ConfirmationRegistry(tmp_path / "registry.jsonl")
    attempt_id = _register_attempt(registry)
    original = registry.get_attempt(attempt_id)
    before = registry.registry_file.read_bytes()
    with pytest.raises(DuplicateAttemptError, match="already registered"):
        registry.register_finalist(
            candidate_name="other-candidate",
            champion_name="other-champion",
            mechanism_family="other-family",
            model_source_hash="4" * 64,
            parameters_hash="5" * 64,
            dev_selection_record_ref="other-development-record",
            protocol_hash="6" * 64,
            attempt_id=attempt_id,
        )
    assert registry.get_attempt(attempt_id) == original
    assert registry.registry_file.read_bytes() == before


@pytest.mark.parametrize("new_status", ["in_progress", "withdrawn", "invalidated"])
def test_completed_attempt_cannot_enter_an_intermediate_state(tmp_path: Path, new_status: AttemptStatus) -> None:
    registry = ConfirmationRegistry(tmp_path / "registry.jsonl")
    attempt_id = _register_attempt(registry)
    completed = registry.transition_attempt_status(
        attempt_id, "completed", execution_status="complete", scientific_verdict="fail", completed_gameweeks=(1, 2)
    )
    with pytest.raises(AdaptiveRunViolationError, match="Cannot re-open or overwrite completed"):
        registry.transition_attempt_status(attempt_id, new_status)
    assert registry.get_attempt(attempt_id) == completed


@pytest.mark.parametrize("new_verdict", ["pass", "inconclusive", "invalid"])
def test_terminal_verdict_cannot_be_replaced(tmp_path: Path, new_verdict: ScientificVerdict) -> None:
    registry = ConfirmationRegistry(tmp_path / "registry.jsonl")
    attempt_id = _register_attempt(registry)
    completed = registry.transition_attempt_status(
        attempt_id,
        "completed",
        execution_status="complete",
        scientific_verdict="fail",
        completed_gameweeks=(1, 2),
        bundle_path="original-bundle.json",
    )
    before = registry.registry_file.read_bytes()
    with pytest.raises(AdaptiveRunViolationError):
        registry.transition_attempt_status(attempt_id, "completed", scientific_verdict=new_verdict)
    with pytest.raises(AdaptiveRunViolationError):
        registry.transition_attempt_status(attempt_id, "completed", bundle_path="replacement-bundle.json")
    assert registry.registry_file.read_bytes() == before
    assert registry.get_attempt(attempt_id) == completed


def test_exact_terminal_retry_does_not_append_or_change_timestamp(tmp_path: Path) -> None:
    registry = ConfirmationRegistry(tmp_path / "registry.jsonl")
    attempt_id = _register_attempt(registry)
    completed = registry.transition_attempt_status(
        attempt_id,
        "completed",
        execution_status="complete",
        scientific_verdict="fail",
        completed_gameweeks=(1, 2),
        bundle_path="original-bundle.json",
    )
    before = registry.registry_file.read_bytes()
    retry = registry.transition_attempt_status(
        attempt_id, "completed", scientific_verdict="fail", completed_gameweeks=(1, 2), bundle_path="original-bundle.json"
    )
    assert retry == completed
    assert retry.completed_at == completed.completed_at
    assert registry.registry_file.read_bytes() == before


@pytest.mark.parametrize("terminal_status", ["withdrawn", "invalidated"])
def test_withdrawn_or_invalidated_attempt_cannot_be_reopened(tmp_path: Path, terminal_status: AttemptStatus) -> None:
    registry = ConfirmationRegistry(tmp_path / "registry.jsonl")
    attempt_id = _register_attempt(registry)
    terminal = registry.transition_attempt_status(attempt_id, terminal_status)
    with pytest.raises(AdaptiveRunViolationError):
        registry.transition_attempt_status(attempt_id, "in_progress")
    assert registry.get_attempt(attempt_id) == terminal


def test_family_attempt_budget_counts_attempts_not_status_records(tmp_path: Path) -> None:
    registry = ConfirmationRegistry(tmp_path / "registry.jsonl")
    attempt_id = _register_attempt(registry)
    registry.transition_attempt_status(attempt_id, "in_progress", execution_status="partial", completed_gameweeks=(1,))
    registry.transition_attempt_status(attempt_id, "completed", execution_status="complete", completed_gameweeks=(1, 2))
    second = registry.register_finalist(
        candidate_name="synthetic-candidate-v2",
        champion_name="synthetic-champion",
        mechanism_family="synthetic-family",
        model_source_hash="4" * 64,
        parameters_hash="5" * 64,
        dev_selection_record_ref="synthetic-development-record-2",
        protocol_hash="3" * 64,
        registered_gameweeks=(1, 2),
    )
    assert second.attempt_number_in_family == 2
    assert second.parent_attempt_id == attempt_id


def test_registered_family_budget_cannot_expand_after_results(tmp_path: Path) -> None:
    registry = ConfirmationRegistry(tmp_path / "registry.jsonl")
    first = registry.register_finalist(
        candidate_name="synthetic-first",
        champion_name="synthetic-champion",
        mechanism_family="synthetic-family",
        model_source_hash="1" * 64,
        parameters_hash="2" * 64,
        dev_selection_record_ref="synthetic-dev-1",
        protocol_hash="3" * 64,
        max_family_attempts=1,
    )
    registry.transition_attempt_status(first.attempt_id, "withdrawn")
    for budget in (1, 10):
        with pytest.raises(AdaptiveRunViolationError, match="budget"):
            registry.register_finalist(
                candidate_name="synthetic-second",
                champion_name="synthetic-champion",
                mechanism_family="synthetic-family",
                model_source_hash="4" * 64,
                parameters_hash="5" * 64,
                dev_selection_record_ref="synthetic-dev-2",
                protocol_hash="3" * 64,
                max_family_attempts=budget,
            )
    assert len(registry.load_all_records()) == 2


def test_completed_execution_trace_is_frozen_before_verdict_finalization(tmp_path: Path) -> None:
    registry = ConfirmationRegistry(tmp_path / "registry.jsonl")
    attempt_id = _register_attempt(registry)
    ready = registry.transition_attempt_status(
        attempt_id,
        "in_progress",
        execution_status="complete",
        completed_gameweeks=(1, 2),
        score_trace_hash="a" * 64,
    )
    with pytest.raises(AdaptiveRunViolationError, match="completed confirmation score trace"):
        registry.transition_attempt_status(attempt_id, "in_progress", score_trace_hash="b" * 64)
    with pytest.raises(AdaptiveRunViolationError, match="completed confirmation score trace"):
        registry.transition_attempt_status(attempt_id, "in_progress", execution_status="partial")
    completed = registry.transition_attempt_status(attempt_id, "completed", scientific_verdict="pass")
    assert completed.score_trace_hash == ready.score_trace_hash
    assert completed.requested_seasons == ("2024-25",)
    assert completed.scientific_verdict == "pass"
    assert registry.verify_integrity() is True


def test_missing_record_hash_is_detected(tmp_path: Path) -> None:
    registry = ConfirmationRegistry(tmp_path / "registry.jsonl")
    _register_attempt(registry)
    original = registry.get_attempt("synthetic-attempt")
    assert original is not None
    content = registry.registry_file.read_text(encoding="utf-8")
    registry.registry_file.write_text(content.replace(original.record_hash, ""), encoding="utf-8")
    with pytest.raises(TamperedRegistryError, match="hash mismatch"):
        registry.load_all_records()
