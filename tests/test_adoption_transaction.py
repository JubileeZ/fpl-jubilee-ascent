"""TDD unit tests for the Champion adoption transaction coordinator (#200)."""

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
import pytest

from backtesting import portable_evidence, promotion_evidence
from backtesting.adoption_transaction import (
    AdoptionRequestManager,
    MergeInterruptedError,
    NotificationDispatcher,
     NotificationMessage,
    ReservationConflictError,
    SharedReservationCoordinator,
    StaleAdoptionBlockedError,
    UncertainDeliveryAckError,
    UnresolvedDeliveryError,
    compute_request_id,
)
from backtesting.confirmation_registry import ConfirmationRegistry
from backtesting.portable_evidence import (
    AdoptionLedger,
    BlobStore,
    compute_serving_model_closure,
    pack_checkpoint_snapshot,
)
from backtesting.promotion_evidence import CHECKPOINT_EVIDENCE_V2, content_hash
from models.selection import ModelSelection, load_model_selection, save_model_selection


class FakeMailProvider:
    """Controllable in-memory MailProvider for testing single-notice and uncertain delivery reconciliation."""

    def __init__(self) -> None:
        self.sent_messages: list[NotificationMessage] = []
        self.fail_mode: str | None = None
        self.provider_status_by_request: dict[str, str] = {}

    def send_adoption_notice(self, message: NotificationMessage) -> str:
        if self.fail_mode == "lost_ack_after_accept":
            self.sent_messages.append(message)
            self.provider_status_by_request[message.request_id] = "delivered"
            raise UncertainDeliveryAckError("SMTP connection dropped after DATA acceptance")
        if self.fail_mode == "timeout_unresolved":
            raise UncertainDeliveryAckError("Timeout waiting for provider response")
        self.sent_messages.append(message)
        self.provider_status_by_request[message.request_id] = "delivered"
        return f"msg-{len(self.sent_messages)}"

    def query_delivery_status(self, request_id: str) -> str:
        return self.provider_status_by_request.get(request_id, "unknown")


def _build_verified_snapshot_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    candidate_name: str = "adaptive_causal_challenger",
    checkpoint_gw: int = 15,
    bundle_seed: str = "a",
) -> tuple[Path, Path, Path, str, str]:
    """Create an isolated evidence root, main selection, and portable snapshot archive."""
    root = tmp_path / f"evidence_{candidate_name}_gw{checkpoint_gw}"
    root.mkdir(parents=True, exist_ok=True)
    frozen_sel = ModelSelection(
        champion="def_xg_shrink_challenger",
        candidates=("adaptive_causal_challenger", "club_def_prior_challenger"),
        provisional_active="adaptive_causal_challenger",
        podium_frozen_season="2026-27",
        podium_sealed=True,
    )
    save_model_selection(frozen_sel, root / "selection.json")
    (root / "protocol.json").write_text('{"windows":{"2025-26":[1,2],"2026-27":[1,2,3]}}', encoding="utf-8")
    (root / "parameters.json").write_text("{}", encoding="utf-8")

    reg = ConfirmationRegistry(root / "registry.jsonl")
    attempt_id = f"att-{candidate_name}-{checkpoint_gw}"
    reg.register_finalist(
        candidate_name=candidate_name,
        champion_name="def_xg_shrink_challenger",
        mechanism_family=f"fam-{candidate_name}",
        model_source_hash="1" * 64,
        parameters_hash="2" * 64,
        dev_selection_record_ref="3" * 64,
        protocol_hash="4" * 64,
        attempt_id=attempt_id,
        requested_seasons=("2026-27",),
        max_family_attempts=2,
    )
    if checkpoint_gw in (15, 30):
        reg.finalize_early_checkpoint_pass(
            attempt_id,
            checkpoint_gw=checkpoint_gw,
            completed_gameweeks=tuple(range(1, checkpoint_gw + 1)),
            score_trace_hash="5" * 64,
            bundle_path="bundle.json",
        )
    else:
        reg.record_checkpoint(
            attempt_id,
            checkpoint_gw=38,
            completed_gameweeks=tuple(range(1, 39)),
            score_trace_hash="5" * 64,
            bundle_path="bundle.json",
        )
        reg.transition_attempt_status(
            attempt_id,
            "completed",
            execution_status="complete",
            scientific_verdict="pass",
            bundle_path="bundle.json",
        )
    (root / "exclusions.jsonl").write_bytes(b"")

    closure = compute_serving_model_closure(
        ("def_xg_shrink_challenger", "adaptive_causal_challenger", "club_def_prior_challenger")
    )
    blob_ref = BlobStore(root).write_canonical_json({"hello": candidate_name, "gw": checkpoint_gw})
    request = {
        "version": CHECKPOINT_EVIDENCE_V2,
        "checkpoint_gw": checkpoint_gw,
        "selection_path": "selection.json",
        "registry_path": "registry.jsonl",
        "protocol": {"path": "protocol.json", "sha256": content_hash({"p": 1})},
        "parameters": {"path": "parameters.json", "sha256": content_hash({})},
        "guard_outcome_sources": [{"season": "2026-27", "gameweek": checkpoint_gw, "admission": blob_ref}],
        "development_selections": {},
        "replays": [],
    }
    (root / "request.json").write_bytes(json.dumps(request, sort_keys=True).encode("utf-8"))
    bundle_hash = bundle_seed * 64
    bundle = {
        "version": CHECKPOINT_EVIDENCE_V2,
        "checkpoint_gw": checkpoint_gw,
        "candidate_name": candidate_name,
        "former_champion": "def_xg_shrink_challenger",
        "recommended_champion": candidate_name,
        "scientific_verdict": "pass",
        "execution_status": "complete",
        "empirical_admission": True,
        "confirmation_attempt_id": attempt_id,
        "request_path": "request.json",
        "request_sha256": "6" * 64,
        "selection_sha256": content_hash(asdict(frozen_sel)),
        "serving_model_closure_hash": closure.serving_model_closure_hash,
        "model_runtime_bindings": closure.model_runtime_bindings,
        "protocol_hash": "4" * 64,
        "bundle_hash": bundle_hash,
    }
    bundle_path = root / "bundle.json"
    bundle_path.write_text(json.dumps(bundle, sort_keys=True), encoding="utf-8")

    monkeypatch.setattr(
        promotion_evidence,
        "verify_checkpoint_recommendation_bundle",
        lambda bp, **kw: json.loads(Path(bp).read_bytes()),
    )
    monkeypatch.setattr(
        portable_evidence,
        "_verify_bundle_in_dir",
        lambda bp, **kw: json.loads(Path(bp).read_bytes()),
    )

    packed = pack_checkpoint_snapshot(bundle_path, output_dir=root / "snapshots")
    archive_path = Path(packed["archive_path"])
    archive_sha = str(packed["archive_sha256"])
    return root, bundle_path, archive_path, bundle_hash, archive_sha


def test_request_priority_rejection_and_queue_advancement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root1, bundle1, archive1, bhash1, asha1 = _build_verified_snapshot_fixture(
        tmp_path, monkeypatch, candidate_name="adaptive_causal_challenger", checkpoint_gw=15, bundle_seed="a"
    )
    _, bundle2, archive2, bhash2, asha2 = _build_verified_snapshot_fixture(
        tmp_path, monkeypatch, candidate_name="club_def_prior_challenger", checkpoint_gw=15, bundle_seed="b"
    )
    _, bundle3, archive3, bhash3, asha3 = _build_verified_snapshot_fixture(
        tmp_path, monkeypatch, candidate_name="adaptive_causal_challenger", checkpoint_gw=30, bundle_seed="c"
    )

    shared_root = tmp_path / "shared_evidence"
    shared_root.mkdir()
    save_model_selection(load_model_selection(root1 / "selection.json"), shared_root / "selection.json")
    (shared_root / "exclusions.jsonl").write_bytes(b"")

    manager = AdoptionRequestManager(shared_root)

    # Simultaneous passes at GW15: club_def_prior_challenger has higher net_delta (18.5 vs 12.0)
    # so it wins priority over adaptive_causal_challenger despite podium_index 1 vs 0.
    enqueued = manager.enqueue_passes(
        [
            {
                "slate_id": "slate-2026-27",
                "season": "2026-27",
                "checkpoint_gw": 15,
                "candidate_name": "adaptive_causal_challenger",
                "expected_champion": "def_xg_shrink_challenger",
                "bundle_hash": bhash1,
                "archive_sha256": asha1,
                "snapshot_archive_path": str(archive1),
                "bundle_path": str(bundle1),
                "protocol_hash": "4" * 64,
                "net_delta": 12.0,
                "podium_index": 0,
            },
            {
                "slate_id": "slate-2026-27",
                "season": "2026-27",
                "checkpoint_gw": 15,
                "candidate_name": "club_def_prior_challenger",
                "expected_champion": "def_xg_shrink_challenger",
                "bundle_hash": bhash2,
                "archive_sha256": asha2,
                "snapshot_archive_path": str(archive2),
                "bundle_path": str(bundle2),
                "protocol_hash": "4" * 64,
                "net_delta": 18.5,
                "podium_index": 1,
            },
        ]
    )
    active = manager.active_request_for_slate("slate-2026-27")
    assert active is not None
    assert active.candidate_name == "club_def_prior_challenger"
    assert active.status == "pending_approval"
    queued = manager.queued_requests_for_slate("slate-2026-27")
    assert len(queued) == 1
    assert queued[0].candidate_name == "adaptive_causal_challenger"
    assert queued[0].status == "queued"

    # Later GW30 pass arrives while GW15 request is still pending_approval -> queued
    req_gw30 = manager.enqueue_pass(
        slate_id="slate-2026-27",
        season="2026-27",
        checkpoint_gw=30,
        candidate_name="adaptive_causal_challenger",
        expected_champion="def_xg_shrink_challenger",
        bundle_hash=bhash3,
        archive_sha256=asha3,
        snapshot_archive_path=str(archive3),
        bundle_path=str(bundle3),
        protocol_hash="4" * 64,
        net_delta=25.0,
        podium_index=0,
    )
    assert req_gw30.status == "queued"
    assert len(manager.queued_requests_for_slate("slate-2026-27")) == 2

    # Reject active GW15 request for club_def_prior_challenger
    rejected = manager.reject_request(active.request_id, actor="operator", reason="Defer GW15 promotion")
    assert rejected.status == "rejected"
    assert AdoptionLedger(shared_root / "adoption_ledger.jsonl").latest_for_request(active.request_id).disposition == "rejected"  # type: ignore[union-attr]
    # Rejected request_id can never be reopened
    with pytest.raises(ValueError, match="terminal|rejected"):
        manager.enqueue_pass(
            slate_id="slate-2026-27",
            season="2026-27",
            checkpoint_gw=15,
            candidate_name="club_def_prior_challenger",
            expected_champion="def_xg_shrink_challenger",
            bundle_hash=bhash2,
            archive_sha256=asha2,
            snapshot_archive_path=str(archive2),
            bundle_path=str(bundle2),
            protocol_hash="4" * 64,
            net_delta=18.5,
            podium_index=1,
        )

    # Advance queue: next eligible recorded pass (GW15 adaptive_causal_challenger) becomes pending_approval
    promoted = manager.advance_queue("slate-2026-27", selection_path=shared_root / "selection.json")
    assert promoted is not None
    assert promoted.request_id == enqueued[1].request_id
    assert promoted.candidate_name == "adaptive_causal_challenger"
    assert promoted.checkpoint_gw == 15
    assert promoted.status == "pending_approval"

    # Reject GW15 adaptive_causal_challenger as well -> candidate remains eligible for its LATER GW30 pass!
    manager.reject_request(promoted.request_id, actor="operator", reason="Wait for GW30 confirmation")
    promoted_gw30 = manager.advance_queue("slate-2026-27", selection_path=shared_root / "selection.json")
    assert promoted_gw30 is not None
    assert promoted_gw30.request_id == req_gw30.request_id
    assert promoted_gw30.candidate_name == "adaptive_causal_challenger"
    assert promoted_gw30.checkpoint_gw == 30
    assert promoted_gw30.status == "pending_approval"


def test_notification_dispatcher_deduplication_and_uncertain_delivery_reconciliation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, bundle, archive, bhash, asha = _build_verified_snapshot_fixture(tmp_path, monkeypatch)
    manager = AdoptionRequestManager(root)
    req = manager.enqueue_pass(
        slate_id="slate-2026-27",
        season="2026-27",
        checkpoint_gw=15,
        candidate_name="adaptive_causal_challenger",
        expected_champion="def_xg_shrink_challenger",
        bundle_hash=bhash,
        archive_sha256=asha,
        snapshot_archive_path=str(archive),
        bundle_path=str(bundle),
        protocol_hash="4" * 64,
        net_delta=14.0,
        podium_index=0,
    )
    provider = FakeMailProvider()
    dispatcher = NotificationDispatcher(root, provider=provider)
    review_url = "https://github.com/JubileeZ/fpl-jubilee-ascent/actions/runs/1001"

    # Simulate provider accepting message but losing acknowledgment
    provider.fail_mode = "lost_ack_after_accept"
    rec1 = dispatcher.reconcile_and_dispatch(req, review_url=review_url)
    assert rec1.status == "uncertain"
    assert len(provider.sent_messages) == 1

    # Reconcile when provider confirms it was delivered -> transitions to delivered WITHOUT duplicate send
    provider.fail_mode = None
    rec2 = dispatcher.reconcile_and_dispatch(req, review_url=review_url)
    assert rec2.status == "delivered"
    assert len(provider.sent_messages) == 1

    # Subsequent calls are no-ops
    rec3 = dispatcher.reconcile_and_dispatch(req, review_url=review_url)
    assert rec3.status == "delivered"
    assert len(provider.sent_messages) == 1

    # If delivery state is uncertain and provider status is unknown, blind resend is blocked
    req_unresolved_id = compute_request_id("slate-2026-27", "2026-27", 30, "adaptive_causal_challenger", "d" * 64)
    req_unresolved = manager.reject_request(req.request_id, actor="operator", reason="test")
    del req_unresolved
    req2 = manager.enqueue_pass(
        slate_id="slate-2026-27",
        season="2026-27",
        checkpoint_gw=30,
        candidate_name="adaptive_causal_challenger",
        expected_champion="def_xg_shrink_challenger",
        bundle_hash="d" * 64,
        archive_sha256=asha,
        snapshot_archive_path=str(archive),
        bundle_path=str(bundle),
        protocol_hash="4" * 64,
        net_delta=20.0,
        podium_index=0,
    )
    assert req2.request_id == req_unresolved_id
    provider.fail_mode = "timeout_unresolved"
    u_rec = dispatcher.reconcile_and_dispatch(req2, review_url=review_url)
    assert u_rec.status == "uncertain"
    provider.fail_mode = None
    with pytest.raises(UnresolvedDeliveryError):
        dispatcher.reconcile_and_dispatch(req2, review_url=review_url)
    assert len(provider.sent_messages) == 1


def test_shared_reservation_exclusion_race_and_interrupted_merge_recovery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, bundle, archive, bhash, asha = _build_verified_snapshot_fixture(tmp_path, monkeypatch)
    main_selection_path = tmp_path / "config" / "model_selection.json"
    save_model_selection(load_model_selection(root / "selection.json"), main_selection_path)

    manager = AdoptionRequestManager(root)
    coordinator = SharedReservationCoordinator(root, request_manager=manager)

    req = manager.enqueue_pass(
        slate_id="slate-2026-27",
        season="2026-27",
        checkpoint_gw=15,
        candidate_name="adaptive_causal_challenger",
        expected_champion="def_xg_shrink_challenger",
        bundle_hash=bhash,
        archive_sha256=asha,
        snapshot_archive_path=str(archive),
        bundle_path=str(bundle),
        protocol_hash="4" * 64,
        net_delta=15.0,
        podium_index=0,
    )

    # 1. Independent auto-merge enabled must be rejected
    with pytest.raises(ValueError, match="auto-merge"):
        coordinator.execute_reserved_adoption_merge(
            request_id=req.request_id,
            slate_id="slate-2026-27",
            approval_ref="GH-ENV-APPROVAL-1",
            approved_pr_head_sha="1" * 40,
            pr_head_sha="1" * 40,
            changed_files=("config/model_selection.json", "config/model_selection.adoption.json"),
            checks_green=True,
            auto_merge_enabled=True,
            main_selection_path=main_selection_path,
        )
    assert coordinator.current_reservation() is None

    # 2. Simulate interruption BEFORE merge takes effect on protected main
    def interrupt_before_merge() -> None:
        # While reservation is held in merge_in_flight, competing exclusion writer MUST be blocked
        with pytest.raises(ReservationConflictError):
            coordinator.record_exclusion_under_reservation(
                holder="weekly-collector",
                slate_id="slate-2026-27",
                season="2026-27",
                candidate_name="adaptive_causal_challenger",
                checkpoint_gw=16,
                reason_code="early_harm",
                details="Competing exclusion during merge reservation",
            )
        raise MergeInterruptedError("Simulated runner crash before git merge API call")

    with pytest.raises(MergeInterruptedError):
        coordinator.execute_reserved_adoption_merge(
            request_id=req.request_id,
            slate_id="slate-2026-27",
            approval_ref="GH-ENV-APPROVAL-1",
            approved_pr_head_sha="1" * 40,
            pr_head_sha="1" * 40,
            changed_files=("config/model_selection.json", "config/model_selection.adoption.json"),
            checks_green=True,
            auto_merge_enabled=False,
            main_selection_path=main_selection_path,
            pre_merge_hook=interrupt_before_merge,
        )
    # Reservation MUST be retained in merge_outcome_unknown
    res_unknown = coordinator.current_reservation()
    assert res_unknown is not None
    assert res_unknown.merge_state == "merge_outcome_unknown"
    # Competing exclusion writer and duplicate merge are still blocked while outcome is unknown
    with pytest.raises(ReservationConflictError):
        coordinator.record_exclusion_under_reservation(
            holder="weekly-collector",
            slate_id="slate-2026-27",
            season="2026-27",
            candidate_name="adaptive_causal_challenger",
            checkpoint_gw=16,
            reason_code="early_harm",
            details="Blocked while merge outcome unknown",
        )

    # Reconcile unknown merge: protected main still has pre-adoption Champion -> resets reservation for retry
    rec_before = coordinator.reconcile_unknown_merge(main_selection_path=main_selection_path)
    assert rec_before["status"] == "reconciled_not_merged_reset_for_retry"
    assert rec_before["merged"] is False
    assert coordinator.current_reservation() is None

    # 3. Simulate interruption AFTER merge landed on protected main (lost ack before ledger release)
    def interrupt_after_merge() -> None:
        raise MergeInterruptedError("Simulated network drop after merge landed on protected main")

    with pytest.raises(MergeInterruptedError):
        coordinator.execute_reserved_adoption_merge(
            request_id=req.request_id,
            slate_id="slate-2026-27",
            approval_ref="GH-ENV-APPROVAL-1",
            approved_pr_head_sha="1" * 40,
            pr_head_sha="1" * 40,
            changed_files=("config/model_selection.json", "config/model_selection.adoption.json"),
            checks_green=True,
            auto_merge_enabled=False,
            main_selection_path=main_selection_path,
            post_merge_ack_hook=interrupt_after_merge,
        )
    assert coordinator.current_reservation() is not None
    assert coordinator.current_reservation().merge_state == "merge_outcome_unknown"  # type: ignore[union-attr]
    # Protected main has the new Champion and receipt
    assert load_model_selection(main_selection_path).champion == "adaptive_causal_challenger"
    assert load_model_selection(main_selection_path).podium_sealed is False

    # Reconcile unknown merge: finds matching (request_id, slate_id) in receipt on protected main,
    # finalizes AdoptionLedger, closes slate, and releases reservation without duplicate merge
    rec_after = coordinator.reconcile_unknown_merge(main_selection_path=main_selection_path)
    assert rec_after["status"] == "reconciled_merged"
    assert rec_after["merged"] is True
    assert coordinator.current_reservation() is None
    assert manager.get_request(req.request_id).status == "adopted"  # type: ignore[union-attr]
    assert AdoptionLedger(root / "adoption_ledger.jsonl").latest_for_request(req.request_id).disposition == "adopted"  # type: ignore[union-attr]


def test_exclusion_arriving_after_green_checks_and_before_reservation_blocks_stale_adoption(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, bundle, archive, bhash, asha = _build_verified_snapshot_fixture(tmp_path, monkeypatch)
    main_selection_path = tmp_path / "config" / "model_selection.json"
    save_model_selection(load_model_selection(root / "selection.json"), main_selection_path)

    manager = AdoptionRequestManager(root)
    coordinator = SharedReservationCoordinator(root, request_manager=manager)

    req = manager.enqueue_pass(
        slate_id="slate-2026-27",
        season="2026-27",
        checkpoint_gw=15,
        candidate_name="adaptive_causal_challenger",
        expected_champion="def_xg_shrink_challenger",
        bundle_hash=bhash,
        archive_sha256=asha,
        snapshot_archive_path=str(archive),
        bundle_path=str(bundle),
        protocol_hash="4" * 64,
        net_delta=15.0,
        podium_index=0,
    )

    # Exclusion writer acquires shared reservation after green PR checks and before merger acquires reservation
    coordinator.record_exclusion_under_reservation(
        holder="weekly-collector",
        slate_id="slate-2026-27",
        season="2026-27",
        candidate_name="adaptive_causal_challenger",
        checkpoint_gw=16,
        reason_code="mandatory_guard_failure",
        details="Excluded at GW16 before GW15 adoption merge executed",
    )
    assert coordinator.current_reservation() is None

    # Merger now acquires reservation, rechecks fresh ExclusionLedger, aborts merge, and marks request stale_closed
    with pytest.raises(StaleAdoptionBlockedError, match="excluded"):
        coordinator.execute_reserved_adoption_merge(
            request_id=req.request_id,
            slate_id="slate-2026-27",
            approval_ref="GH-ENV-APPROVAL-2",
            approved_pr_head_sha="2" * 40,
            pr_head_sha="2" * 40,
            changed_files=("config/model_selection.json", "config/model_selection.adoption.json"),
            checks_green=True,
            auto_merge_enabled=False,
            main_selection_path=main_selection_path,
        )
    assert coordinator.current_reservation() is None
    assert load_model_selection(main_selection_path).champion == "def_xg_shrink_challenger"
    assert not main_selection_path.with_suffix(".adoption.json").exists()
    assert manager.get_request(req.request_id).status == "stale_closed"  # type: ignore[union-attr]
    assert AdoptionLedger(root / "adoption_ledger.jsonl").latest_for_request(req.request_id).disposition == "invalidated"  # type: ignore[union-attr]
