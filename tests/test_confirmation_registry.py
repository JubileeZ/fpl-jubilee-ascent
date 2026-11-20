"""Unit tests for Phase 9 confirmation admission and attempt registry."""

from dataclasses import replace
import json
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
    """Verify ADR 0069 SeasonLifecycle safety checks across validation, ideation, and sealed seasons."""
    reg_file = tmp_path / "registry.jsonl"
    registry = ConfirmationRegistry(reg_file)

    # Allowed: 2024-25 (historical_filter)
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

    # Allowed: 2026-27 GW1-38 under active_validation for frozen finalist validation
    registry.register_finalist(
        candidate_name="cand2",
        champion_name="champ",
        mechanism_family="fam2",
        model_source_hash="1" * 64,
        parameters_hash="2" * 64,
        dev_selection_record_ref="dev",
        protocol_hash="3" * 64,
        requested_seasons=["2026-27"],
        registered_gameweeks=tuple(range(1, 39)),
    )

    # Blocked: ideation / tuning / dev on active_validation 2026-27
    for bad_purpose in ("ideation", "tuning", "dev"):
        with pytest.raises(SealedDataViolationError):
            registry.check_sealed_data_safety(["2026-27"], tuple(range(1, 39)), purpose=bad_purpose)

    # Blocked: unconfigured / sealed season
    with pytest.raises(SealedDataViolationError):
        registry.register_finalist(
            candidate_name="cand3",
            champion_name="champ",
            mechanism_family="fam3",
            model_source_hash="1" * 64,
            parameters_hash="2" * 64,
            dev_selection_record_ref="dev",
            protocol_hash="3" * 64,
            requested_seasons=["2027-28"],
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


def test_record_checkpoint_progress_records_gw15_and_gw30_without_completing(tmp_path: Path) -> None:
    registry = ConfirmationRegistry(tmp_path / "registry.jsonl")
    rec = registry.register_finalist(
        candidate_name="cand_1",
        champion_name="def_xg_shrink_challenger",
        mechanism_family="fam_a",
        model_source_hash="a" * 64,
        parameters_hash="b" * 64,
        dev_selection_record_ref="dev-ref",
        protocol_hash="c" * 64,
        requested_seasons=("2026-27",),
        registered_gameweeks=tuple(range(1, 39)),
        max_family_attempts=2,
    )
    gw15 = registry.record_checkpoint(
        rec.attempt_id,
        checkpoint_gw=15,
        completed_gameweeks=tuple(range(1, 16)),
        score_trace_hash="d" * 64,
    )
    assert gw15.status == "in_progress"
    assert gw15.execution_status == "partial"
    assert gw15.completed_gameweeks == tuple(range(1, 16))
    assert gw15.score_trace_hash == "d" * 64
    assert registry.verify_integrity() is True

    with pytest.raises(IncompleteScheduleError):
        registry.transition_attempt_status(
            rec.attempt_id,
            "completed",
            execution_status="complete",
            completed_gameweeks=tuple(range(1, 16)),
        )


def test_verify_checkpoint_attempt_binds_registration_trace_and_final_bundle(tmp_path: Path) -> None:
    registry = ConfirmationRegistry(tmp_path / "registry.jsonl")
    identity = {
        "candidate_name": "cand_1",
        "champion_name": "champ",
        "model_source_hash": "a" * 64,
        "parameters_hash": "b" * 64,
        "protocol_hash": "c" * 64,
        "max_family_attempts": 2,
    }
    attempt = registry.register_finalist(
        **identity, mechanism_family="fam_a", dev_selection_record_ref="dev-ref", requested_seasons=("2026-27",)
    )
    scope = {**identity, "active_season": "2026-27", "checkpoint_gw": 15, "score_trace_hash": "d" * 64}
    with pytest.raises(ValueError, match="exact completed"):
        registry.verify_checkpoint_attempt(attempt.attempt_id, **scope)

    progress = registry.record_checkpoint(
        attempt.attempt_id, checkpoint_gw=15, completed_gameweeks=tuple(range(1, 16)), score_trace_hash="d" * 64
    )
    assert registry.verify_checkpoint_attempt(attempt.attempt_id, **scope) == progress
    bundle_path = tmp_path / "bundle.json"
    with pytest.raises(ValueError, match="finalized with a complete pass"):
        registry.verify_checkpoint_attempt(attempt.attempt_id, **scope, finalized_bundle_path=bundle_path)

    mismatches = {
        "candidate_name": ("cand_2", "candidate_name"),
        "champion_name": ("different_champ", "champion_name"),
        "model_source_hash": ("e" * 64, "model_source_hash"),
        "parameters_hash": ("e" * 64, "parameters_hash"),
        "protocol_hash": ("e" * 64, "protocol_hash"),
        "score_trace_hash": ("e" * 64, "score_trace_hash"),
        "max_family_attempts": (3, "history or budget"),
        "active_season": ("2025-26", "prohibits active_validation"),
        "checkpoint_gw": (30, "exact completed"),
    }
    for field, (value, message) in mismatches.items():
        with pytest.raises(ValueError, match=message):
            registry.verify_checkpoint_attempt(attempt.attempt_id, **{**scope, field: value})

    finalized = registry.finalize_early_checkpoint_pass(
        attempt.attempt_id, checkpoint_gw=15, completed_gameweeks=tuple(range(1, 16)),
        score_trace_hash="d" * 64, bundle_path=bundle_path.name,
    )
    assert registry.verify_checkpoint_attempt(attempt.attempt_id, **scope, finalized_bundle_path=bundle_path) == finalized
    with pytest.raises(ValueError, match="different bundle path"):
        registry.verify_checkpoint_attempt(attempt.attempt_id, **scope, finalized_bundle_path=tmp_path / "other.json")

    changed_budget = replace(finalized, max_family_attempts=3)
    changed_budget = replace(changed_budget, record_hash=changed_budget.compute_record_hash())
    registry.registry_file.write_text(
        "\n".join(json.dumps(record.to_dict()) for record in (attempt, progress, changed_budget)) + "\n",
        encoding="utf-8",
    )
    assert registry.verify_integrity()
    with pytest.raises(ValueError, match="history or budget"):
        registry.verify_checkpoint_attempt(attempt.attempt_id, **scope, finalized_bundle_path=bundle_path)


def test_confirmation_registry_enforces_relative_posix_bundle_path_and_prefix_progression(tmp_path: Path) -> None:
    from backtesting.portable_evidence import AdoptionLedger

    registry = ConfirmationRegistry(tmp_path / "registry.jsonl")
    identity = {
        "candidate_name": "cand_1",
        "champion_name": "champ",
        "model_source_hash": "a" * 64,
        "parameters_hash": "b" * 64,
        "protocol_hash": "c" * 64,
        "max_family_attempts": 2,
    }
    rec = registry.register_finalist(
        **identity,
        mechanism_family="fam_a",
        dev_selection_record_ref="dev-ref",
        requested_seasons=("2026-27",),
    )
    h15, h30, h38 = "1" * 64, "2" * 64, "3" * 64

    for bad_path in (str(tmp_path / "abs.json"), "../outside.json", r"sub\win.json", ""):
        with pytest.raises(ValueError):
            registry.record_checkpoint(
                rec.attempt_id,
                checkpoint_gw=15,
                completed_gameweeks=tuple(range(1, 16)),
                score_trace_hash=h15,
                bundle_path=bad_path,
            )
        with pytest.raises(ValueError):
            registry.finalize_early_checkpoint_pass(
                rec.attempt_id,
                checkpoint_gw=15,
                completed_gameweeks=tuple(range(1, 16)),
                score_trace_hash=h15,
                bundle_path=bad_path,
            )

    gw15_bundle = tmp_path / "gw15/bundle.json"
    gw15_bundle.parent.mkdir(parents=True)
    gw15_bundle.write_text("{}", encoding="utf-8")
    p15 = registry.finalize_early_checkpoint_pass(
        rec.attempt_id,
        checkpoint_gw=15,
        completed_gameweeks=tuple(range(1, 16)),
        score_trace_hash=h15,
        bundle_path="gw15/bundle.json",
    )
    assert p15.status == "completed" and p15.scientific_verdict == "pass"
    assert p15.human_approval_ref is None

    # Human rejection in AdoptionLedger does not block advancing canonical confirmation to GW30 / GW38.
    adopt_ledger = AdoptionLedger(tmp_path / "adoption_ledger.jsonl")
    adopt_ledger.record_disposition(
        request_id="req-gw15",
        slate_id="slate-2026-27",
        season="2026-27",
        checkpoint_gw=15,
        candidate_name="cand_1",
        expected_champion="champ",
        bundle_hash="f" * 64,
        disposition="rejected",
        actor="human-op",
    )

    p30_prog = registry.record_checkpoint(
        rec.attempt_id,
        checkpoint_gw=30,
        completed_gameweeks=tuple(range(1, 31)),
        score_trace_hash=h30,
    )
    assert p30_prog.status == "in_progress" and p30_prog.completed_gameweeks == tuple(range(1, 31))
    gw30_bundle = tmp_path / "gw30/bundle.json"
    gw30_bundle.parent.mkdir(parents=True)
    gw30_bundle.write_text("{}", encoding="utf-8")
    p30_pass = registry.finalize_early_checkpoint_pass(
        rec.attempt_id,
        checkpoint_gw=30,
        completed_gameweeks=tuple(range(1, 31)),
        score_trace_hash=h30,
        bundle_path="gw30/bundle.json",
    )
    assert p30_pass.status == "completed" and p30_pass.human_approval_ref is None

    # Advancing past GW15 must NOT break earlier GW15 verification against canonical registry.jsonl!
    scope15 = {**identity, "active_season": "2026-27", "checkpoint_gw": 15, "score_trace_hash": h15}
    verified15 = registry.verify_checkpoint_attempt(rec.attempt_id, **scope15, finalized_bundle_path=gw15_bundle)
    assert verified15.completed_gameweeks == tuple(range(1, 16))

    # Full GW38 completion becomes strictly terminal.
    p38 = registry.transition_attempt_status(
        rec.attempt_id,
        "completed",
        execution_status="complete",
        scientific_verdict="pass",
        completed_gameweeks=tuple(range(1, 39)),
        score_trace_hash=h38,
        bundle_path="gw38/bundle.json",
    )
    assert p38.status == "completed" and p38.completed_gameweeks == tuple(range(1, 39))
    with pytest.raises(AdaptiveRunViolationError):
        registry.transition_attempt_status(rec.attempt_id, "withdrawn")
