"""Protected Champion adoption transaction coordinator (#194, #197, #200)."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Literal, Protocol

from backtesting.portable_evidence import (
    AdoptionDisposition,
    AdoptionLedger,
    ExclusionLedger,
    ExclusionRecord,
    _append_chained_jsonl,
    _canonical_json_bytes,
    _compute_chain_record_hash,
    _load_chained_jsonl,
    _validate_sha256_hex,
    verify_checkpoint_snapshot_archive,
)
from backtesting.promotion_evidence import (
    CHECKPOINT_EVIDENCE_V2,
    CHECKPOINT_EVIDENCE_VERSION,
    verify_checkpoint_recommendation_bundle,
    verify_recommendation_bundle,
)
from backtesting.season_rules import load_season_lifecycle
from commands.evaluate_model_promotion import adopt_champion
from models.selection import DEFAULT_CONFIG_PATH, load_model_selection

AUTHORIZED_ADOPTION_DIFF_FILES: frozenset[str] = frozenset(
    {
        "config/model_selection.json",
        "config/model_selection.adoption.json",
    }
)

RequestStatus = Literal[
    "pending_approval",
    "queued",
    "approved",
    "rejected",
    "expired",
    "stale_closed",
    "adopted",
]
TERMINAL_REQUEST_STATUSES: frozenset[str] = frozenset(
    {
        "rejected",
        "expired",
        "stale_closed",
        "adopted",
    }
)
NotificationStatus = Literal["send_attempted", "delivered", "uncertain"]
ProviderDeliveryStatus = Literal["delivered", "not_found", "unknown"]
ReservationPurpose = Literal["adoption_merge", "exclusion_write"]
MergeState = Literal["held", "merge_in_flight", "merge_outcome_unknown"]


class UncertainDeliveryAckError(RuntimeError):
    """Raised when a mail provider accepted or may have accepted a notice before acknowledgment was lost."""


class UnresolvedDeliveryError(RuntimeError):
    """Raised when a notice is in uncertain state and the provider cannot confirm delivery or non-delivery."""


class ReservationConflictError(RuntimeError):
    """Raised when the shared durable adoption/exclusion reservation is already held."""


class StaleAdoptionBlockedError(ValueError):
    """Raised when an adoption merge is aborted under reservation due to stale state or fresh exclusion."""


class MergeInterruptedError(RuntimeError):
    """Raised when an adoption merge is interrupted while merge_in_flight."""


def compute_request_id(
    slate_id: str,
    season: str,
    checkpoint_gw: int,
    candidate_name: str,
    bundle_hash: str,
) -> str:
    """Compute deterministic durable request ID for a verified checkpoint pass."""
    clean_bundle = _validate_sha256_hex(bundle_hash, "bundle_hash")
    if not slate_id.strip() or not season.strip() or not candidate_name.strip():
        raise ValueError("compute_request_id requires non-empty slate_id, season, and candidate_name")
    if type(checkpoint_gw) is not int or not 1 <= checkpoint_gw <= 38:
        raise ValueError(f"Invalid checkpoint_gw: {checkpoint_gw}")
    payload = {
        "slate_id": slate_id.strip(),
        "season": season.strip(),
        "checkpoint_gw": checkpoint_gw,
        "candidate_name": candidate_name.strip(),
        "bundle_hash": clean_bundle,
    }
    digest = hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()
    return f"req-{season.strip()}-gw{checkpoint_gw:02d}-{digest[:16]}"


@dataclass(frozen=True)
class AdoptionRequest:
    """Durable adoption request record tracked per frozen comparison slate."""

    request_id: str
    slate_id: str
    season: str
    checkpoint_gw: int
    candidate_name: str
    expected_champion: str
    bundle_hash: str
    archive_sha256: str | None
    snapshot_archive_path: str | None
    bundle_path: str | None
    protocol_hash: str
    serving_model_closure_hash: str | None
    net_delta: float
    podium_index: int
    status: RequestStatus
    created_at_utc: str
    updated_at_utc: str
    expires_at_utc: str | None = None
    approval_ref: str | None = None
    approved_pr_head_sha: str | None = None
    actor: str | None = None
    reason: str = ""
    sequence_number: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "AdoptionRequest":
        return cls(
            request_id=str(data["request_id"]),
            slate_id=str(data["slate_id"]),
            season=str(data["season"]),
            checkpoint_gw=int(data["checkpoint_gw"]),
            candidate_name=str(data["candidate_name"]),
            expected_champion=str(data["expected_champion"]),
            bundle_hash=str(data["bundle_hash"]),
            archive_sha256=str(data["archive_sha256"]) if data.get("archive_sha256") is not None else None,
            snapshot_archive_path=(
                str(data["snapshot_archive_path"]) if data.get("snapshot_archive_path") is not None else None
            ),
            bundle_path=str(data["bundle_path"]) if data.get("bundle_path") is not None else None,
            protocol_hash=str(data.get("protocol_hash", "")),
            serving_model_closure_hash=(
                str(data["serving_model_closure_hash"]) if data.get("serving_model_closure_hash") is not None else None
            ),
            net_delta=float(data.get("net_delta", 0.0)),
            podium_index=int(data.get("podium_index", 0)),
            status=data["status"],
            created_at_utc=str(data["created_at_utc"]),
            updated_at_utc=str(data["updated_at_utc"]),
            expires_at_utc=str(data["expires_at_utc"]) if data.get("expires_at_utc") is not None else None,
            approval_ref=str(data["approval_ref"]) if data.get("approval_ref") is not None else None,
            approved_pr_head_sha=(
                str(data["approved_pr_head_sha"]) if data.get("approved_pr_head_sha") is not None else None
            ),
            actor=str(data["actor"]) if data.get("actor") is not None else None,
            reason=str(data.get("reason", "")),
            sequence_number=int(data.get("sequence_number", 0)),
        )


def _priority_sort_key(req: AdoptionRequest) -> tuple[int, float, int, int]:
    """Priority order: first checkpoint GW, then higher net_delta, then smaller podium_index, then arrival seq."""
    return (req.checkpoint_gw, -req.net_delta, req.podium_index, req.sequence_number)


class AdoptionRequestManager:
    """Manages one active adoption request per frozen slate with priority, queuing, and terminal dispositions."""

    def __init__(self, evidence_root: Path | str) -> None:
        raw_root = Path(evidence_root).resolve()
        self.evidence_root = load_season_lifecycle().assert_unsealed_storage_path(
            raw_root, error_message="Protected adoption evidence root"
        )
        self.requests_file = self.evidence_root / "adoption_requests.json"
        self.adoption_ledger = AdoptionLedger(self.evidence_root / "adoption_ledger.jsonl")
        self.exclusion_ledger = ExclusionLedger(self.evidence_root / "exclusions.jsonl")

    def _load_state(self) -> tuple[list[AdoptionRequest], set[str], int]:
        if not self.requests_file.is_file():
            return [], set(), 0
        payload = json.loads(self.requests_file.read_bytes())
        requests = [AdoptionRequest.from_dict(item) for item in payload.get("requests", ())]
        closed_slates = {str(s) for s in payload.get("closed_slates", ())}
        seq = int(payload.get("next_sequence", len(requests)))
        return requests, closed_slates, seq

    def _save_state(
        self,
        requests: Sequence[AdoptionRequest],
        closed_slates: set[str],
        next_sequence: int,
    ) -> None:
        self.evidence_root.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": 1,
            "next_sequence": next_sequence,
            "closed_slates": sorted(closed_slates),
            "requests": [req.to_dict() for req in requests],
        }
        raw = json.dumps(payload, indent=2, sort_keys=True, allow_nan=False).encode("utf-8") + b"\n"
        tmp = self.requests_file.with_suffix(".json.tmp")
        try:
            tmp.write_bytes(raw)
            os.replace(tmp, self.requests_file)
        finally:
            tmp.unlink(missing_ok=True)

    def all_requests(self, *, slate_id: str | None = None) -> list[AdoptionRequest]:
        requests, _, _ = self._load_state()
        if slate_id is not None:
            return [r for r in requests if r.slate_id == slate_id]
        return requests

    def get_request(self, request_id: str) -> AdoptionRequest | None:
        for req in self.all_requests():
            if req.request_id == request_id:
                return req
        return None

    def is_slate_closed(self, slate_id: str) -> bool:
        requests, closed_slates, _ = self._load_state()
        return slate_id in closed_slates or any(r.slate_id == slate_id and r.status == "adopted" for r in requests)

    def active_request_for_slate(self, slate_id: str) -> AdoptionRequest | None:
        for req in self.all_requests(slate_id=slate_id):
            if req.status in ("pending_approval", "approved"):
                return req
        return None

    def queued_requests_for_slate(self, slate_id: str) -> list[AdoptionRequest]:
        queued = [r for r in self.all_requests(slate_id=slate_id) if r.status == "queued"]
        return sorted(queued, key=_priority_sort_key)

    def enqueue_passes(self, passes: Sequence[Mapping[str, Any]]) -> list[AdoptionRequest]:
        """Enqueue one or more verified full passes, applying simultaneous pass tie-break `(net_delta, -podium_index)`."""
        if not passes:
            return []
        ordered_inputs = sorted(
            passes,
            key=lambda p: (
                int(p["checkpoint_gw"]),
                -float(p.get("net_delta", 0.0)),
                int(p.get("podium_index", 0)),
            ),
        )
        results: list[AdoptionRequest] = []
        for item in ordered_inputs:
            results.append(
                self.enqueue_pass(
                    slate_id=str(item["slate_id"]),
                    season=str(item["season"]),
                    checkpoint_gw=int(item["checkpoint_gw"]),
                    candidate_name=str(item["candidate_name"]),
                    expected_champion=str(item["expected_champion"]),
                    bundle_hash=str(item["bundle_hash"]),
                    archive_sha256=(
                        str(item["archive_sha256"]) if item.get("archive_sha256") is not None else None
                    ),
                    snapshot_archive_path=(
                        str(item["snapshot_archive_path"]) if item.get("snapshot_archive_path") is not None else None
                    ),
                    bundle_path=str(item["bundle_path"]) if item.get("bundle_path") is not None else None,
                    protocol_hash=str(item.get("protocol_hash", "")),
                    serving_model_closure_hash=(
                        str(item["serving_model_closure_hash"])
                        if item.get("serving_model_closure_hash") is not None
                        else None
                    ),
                    net_delta=float(item.get("net_delta", 0.0)),
                    podium_index=int(item.get("podium_index", 0)),
                    expires_at_utc=(
                        str(item["expires_at_utc"]) if item.get("expires_at_utc") is not None else None
                    ),
                    actor=str(item.get("actor", "checkpoint-evaluator")),
                )
            )
        return results

    def enqueue_pass(
        self,
        *,
        slate_id: str,
        season: str,
        checkpoint_gw: int,
        candidate_name: str,
        expected_champion: str,
        bundle_hash: str,
        archive_sha256: str | None = None,
        snapshot_archive_path: str | None = None,
        bundle_path: str | None = None,
        protocol_hash: str = "",
        serving_model_closure_hash: str | None = None,
        net_delta: float = 0.0,
        podium_index: int = 0,
        expires_at_utc: str | None = None,
        actor: str = "checkpoint-evaluator",
    ) -> AdoptionRequest:
        """Record a verified checkpoint pass; activates immediately if no request is open on slate, else queues."""
        _validate_sha256_hex(bundle_hash, "bundle_hash")
        if archive_sha256 is not None:
            _validate_sha256_hex(archive_sha256, "archive_sha256")
        request_id = compute_request_id(slate_id, season, checkpoint_gw, candidate_name, bundle_hash)
        requests, closed_slates, next_seq = self._load_state()
        if slate_id in closed_slates or any(r.slate_id == slate_id and r.status == "adopted" for r in requests):
            raise ValueError(f"Frozen slate '{slate_id}' is already closed by an adopted Champion")
        if self.exclusion_ledger.ledger_file.is_file() and self.exclusion_ledger.is_excluded(
            candidate_name, slate_id=slate_id, season=season
        ):
            raise ValueError(f"Cannot enqueue excluded candidate '{candidate_name}' on slate '{slate_id}'")

        for existing in requests:
            if existing.request_id == request_id:
                if existing.status in TERMINAL_REQUEST_STATUSES:
                    raise ValueError(
                        f"Request '{request_id}' is already terminal ({existing.status}) and cannot be reopened"
                    )
                return existing

        has_active = any(r.slate_id == slate_id and r.status in ("pending_approval", "approved") for r in requests)
        initial_status: RequestStatus = "queued" if has_active else "pending_approval"
        now_iso = datetime.now(UTC).isoformat()
        created = AdoptionRequest(
            request_id=request_id,
            slate_id=slate_id,
            season=season,
            checkpoint_gw=checkpoint_gw,
            candidate_name=candidate_name,
            expected_champion=expected_champion,
            bundle_hash=bundle_hash,
            archive_sha256=archive_sha256,
            snapshot_archive_path=snapshot_archive_path,
            bundle_path=bundle_path,
            protocol_hash=protocol_hash,
            serving_model_closure_hash=serving_model_closure_hash,
            net_delta=float(net_delta),
            podium_index=int(podium_index),
            status=initial_status,
            created_at_utc=now_iso,
            updated_at_utc=now_iso,
            expires_at_utc=expires_at_utc,
            actor=actor,
            sequence_number=next_seq,
        )
        requests.append(created)
        self._save_state(requests, closed_slates, next_seq + 1)
        if initial_status == "pending_approval":
            self.adoption_ledger.record_disposition(
                request_id=request_id,
                slate_id=slate_id,
                season=season,
                checkpoint_gw=checkpoint_gw,
                candidate_name=candidate_name,
                expected_champion=expected_champion,
                bundle_hash=bundle_hash,
                disposition="requested",
                actor=actor,
                reason=f"Active adoption request at GW{checkpoint_gw}",
                recorded_at=now_iso,
            )
        return created

    def record_approval(
        self,
        request_id: str,
        *,
        actor: str,
        approval_ref: str,
        approved_pr_head_sha: str | None = None,
        reason: str = "Human approved protected adoption request",
    ) -> AdoptionRequest:
        """Bind human approval and optional PR head SHA to the active request."""
        requests, closed_slates, next_seq = self._load_state()
        updated_list: list[AdoptionRequest] = []
        target: AdoptionRequest | None = None
        now_iso = datetime.now(UTC).isoformat()
        for req in requests:
            if req.request_id == request_id:
                if req.status not in ("pending_approval", "approved"):
                    raise ValueError(f"Cannot approve request '{request_id}' in status '{req.status}'")
                target = replace(
                    req,
                    status="approved",
                    approval_ref=approval_ref,
                    approved_pr_head_sha=approved_pr_head_sha or req.approved_pr_head_sha,
                    actor=actor,
                    reason=reason,
                    updated_at_utc=now_iso,
                )
                updated_list.append(target)
            else:
                updated_list.append(req)
        if target is None:
            raise ValueError(f"Adoption request '{request_id}' not found")
        self._save_state(updated_list, closed_slates, next_seq)
        self.adoption_ledger.record_disposition(
            request_id=target.request_id,
            slate_id=target.slate_id,
            season=target.season,
            checkpoint_gw=target.checkpoint_gw,
            candidate_name=target.candidate_name,
            expected_champion=target.expected_champion,
            bundle_hash=target.bundle_hash,
            disposition="approved",
            actor=actor,
            approval_ref=approval_ref,
            reason=reason,
            recorded_at=now_iso,
        )
        return target

    def reject_request(
        self,
        request_id: str,
        *,
        actor: str,
        reason: str,
    ) -> AdoptionRequest:
        """Terminally reject an adoption request without mutating Champion selection or excluding finalist."""
        if not actor.strip() or not reason.strip():
            raise ValueError("Rejection requires non-empty actor and reason")
        return self._transition_terminal(
            request_id,
            new_status="rejected",
            ledger_disposition="rejected",
            actor=actor,
            reason=reason,
        )

    def expire_or_invalidate_request(
        self,
        request_id: str,
        *,
        reason: str,
        expired: bool = False,
        actor: str = "adoption-coordinator",
    ) -> AdoptionRequest:
        """Terminally close a pending or queued request due to expiry, exclusion, or changed Champion/evidence."""
        new_status: RequestStatus = "expired" if expired else "stale_closed"
        disposition: AdoptionDisposition = "expired" if expired else "invalidated"
        return self._transition_terminal(
            request_id,
            new_status=new_status,
            ledger_disposition=disposition,
            actor=actor,
            reason=reason,
        )

    def mark_adopted(
        self,
        request_id: str,
        *,
        actor: str,
        approval_ref: str,
        approved_pr_head_sha: str | None = None,
        reason: str = "Merged onto protected main",
        record_in_ledger: bool = True,
    ) -> AdoptionRequest:
        """Mark request adopted, close the frozen slate, and invalidate any remaining queued requests on that slate."""
        requests, closed_slates, next_seq = self._load_state()
        now_iso = datetime.now(UTC).isoformat()
        target: AdoptionRequest | None = None
        target_slate: str | None = None
        for req in requests:
            if req.request_id == request_id:
                target_slate = req.slate_id
                break
        if target_slate is None:
            raise ValueError(f"Adoption request '{request_id}' not found")

        closed_slates.add(target_slate)
        updated_list: list[AdoptionRequest] = []
        for req in requests:
            if req.request_id == request_id:
                if req.status == "adopted":
                    target = req
                    updated_list.append(req)
                    continue
                if req.status in ("rejected", "expired", "stale_closed"):
                    raise ValueError(f"Cannot mark terminal request '{request_id}' ({req.status}) as adopted")
                target = replace(
                    req,
                    status="adopted",
                    approval_ref=approval_ref,
                    approved_pr_head_sha=approved_pr_head_sha or req.approved_pr_head_sha,
                    actor=actor,
                    reason=reason,
                    updated_at_utc=now_iso,
                )
                updated_list.append(target)
            elif req.slate_id == target_slate and req.status in ("queued", "pending_approval", "approved"):
                closed_req = replace(
                    req,
                    status="stale_closed",
                    actor=actor,
                    reason=f"Slate '{target_slate}' closed by adoption of '{request_id}'",
                    updated_at_utc=now_iso,
                )
                updated_list.append(closed_req)
                self.adoption_ledger.record_disposition(
                    request_id=closed_req.request_id,
                    slate_id=closed_req.slate_id,
                    season=closed_req.season,
                    checkpoint_gw=closed_req.checkpoint_gw,
                    candidate_name=closed_req.candidate_name,
                    expected_champion=closed_req.expected_champion,
                    bundle_hash=closed_req.bundle_hash,
                    disposition="invalidated",
                    actor=actor,
                    reason=closed_req.reason,
                    recorded_at=now_iso,
                )
            else:
                updated_list.append(req)
        assert target is not None
        self._save_state(updated_list, closed_slates, next_seq)
        if record_in_ledger:
            latest = self.adoption_ledger.latest_for_request(target.request_id)
            if latest is None or latest.disposition != "adopted":
                self.adoption_ledger.record_disposition(
                    request_id=target.request_id,
                    slate_id=target.slate_id,
                    season=target.season,
                    checkpoint_gw=target.checkpoint_gw,
                    candidate_name=target.candidate_name,
                    expected_champion=target.expected_champion,
                    bundle_hash=target.bundle_hash,
                    disposition="adopted",
                    actor=actor,
                    approval_ref=approval_ref,
                    reason=reason,
                    recorded_at=now_iso,
                )
        return target

    def _transition_terminal(
        self,
        request_id: str,
        *,
        new_status: RequestStatus,
        ledger_disposition: AdoptionDisposition,
        actor: str,
        reason: str,
    ) -> AdoptionRequest:
        requests, closed_slates, next_seq = self._load_state()
        now_iso = datetime.now(UTC).isoformat()
        updated_list: list[AdoptionRequest] = []
        target: AdoptionRequest | None = None
        for req in requests:
            if req.request_id == request_id:
                if req.status == new_status:
                    return req
                if req.status in TERMINAL_REQUEST_STATUSES:
                    raise ValueError(
                        f"Cannot transition request '{request_id}' from terminal '{req.status}' to '{new_status}'"
                    )
                target = replace(
                    req,
                    status=new_status,
                    actor=actor,
                    reason=reason,
                    updated_at_utc=now_iso,
                )
                updated_list.append(target)
            else:
                updated_list.append(req)
        if target is None:
            raise ValueError(f"Adoption request '{request_id}' not found")
        self._save_state(updated_list, closed_slates, next_seq)
        self.adoption_ledger.record_disposition(
            request_id=target.request_id,
            slate_id=target.slate_id,
            season=target.season,
            checkpoint_gw=target.checkpoint_gw,
            candidate_name=target.candidate_name,
            expected_champion=target.expected_champion,
            bundle_hash=target.bundle_hash,
            disposition=ledger_disposition,
            actor=actor,
            approval_ref=target.approval_ref,
            reason=reason,
            recorded_at=now_iso,
        )
        return target

    def _verify_request_evidence(self, req: AdoptionRequest) -> None:
        canon_reg = self.evidence_root / "registry.jsonl"
        canon_excl = self.evidence_root / "exclusions.jsonl"
        if req.snapshot_archive_path:
            snap_path = Path(req.snapshot_archive_path)
            if not snap_path.is_absolute():
                snap_path = (self.evidence_root / snap_path).resolve()
            verified = verify_checkpoint_snapshot_archive(
                snap_path,
                expected_archive_sha256=req.archive_sha256,
                expected_champion=req.expected_champion,
                canonical_registry_path=canon_reg if canon_reg.is_file() else None,
                canonical_exclusions_path=canon_excl if canon_excl.is_file() else None,
            )
            bundle = verified["bundle"]
        elif req.bundle_path:
            bpath = Path(req.bundle_path)
            if not bpath.is_absolute():
                bpath = (self.evidence_root / bpath).resolve()
            raw = json.loads(bpath.read_bytes())
            if raw.get("version") in (CHECKPOINT_EVIDENCE_VERSION, CHECKPOINT_EVIDENCE_V2):
                bundle = verify_checkpoint_recommendation_bundle(bpath, require_finalized=True)
            else:
                bundle = verify_recommendation_bundle(bpath, require_finalized=True)
        else:
            raise ValueError(f"Request '{req.request_id}' has neither snapshot_archive_path nor bundle_path")

        if bundle.get("bundle_hash") != req.bundle_hash:
            raise ValueError(f"Request '{req.request_id}' bundle_hash mismatch")
        if (
            bundle.get("scientific_verdict") != "pass"
            or bundle.get("execution_status") != "complete"
            or bundle.get("empirical_admission") is not True
        ):
            raise ValueError(f"Request '{req.request_id}' is not an empirically admitted complete pass")

    def advance_queue(
        self,
        slate_id: str,
        *,
        selection_path: Path | None = None,
        now_utc: str | None = None,
        actor: str = "adoption-coordinator",
    ) -> AdoptionRequest | None:
        """Promote the highest-priority valid queued pass to pending_approval after rechecking eligibility & evidence."""
        active = self.active_request_for_slate(slate_id)
        if active is not None:
            return active

        sel_file = selection_path or (
            self.evidence_root / "selection.json"
            if (self.evidence_root / "selection.json").is_file()
            else DEFAULT_CONFIG_PATH
        )
        current_sel = load_model_selection(sel_file)
        now_dt = (
            datetime.fromisoformat(now_utc.replace("Z", "+00:00"))
            if now_utc is not None
            else datetime.now(UTC)
        )

        for queued_req in self.queued_requests_for_slate(slate_id):
            if self.is_slate_closed(slate_id) or not current_sel.podium_sealed:
                self.expire_or_invalidate_request(
                    queued_req.request_id,
                    reason="slate_closed_or_unsealed",
                    actor=actor,
                )
                continue
            if queued_req.expires_at_utc is not None:
                exp_dt = datetime.fromisoformat(queued_req.expires_at_utc.replace("Z", "+00:00"))
                if now_dt > exp_dt:
                    self.expire_or_invalidate_request(
                        queued_req.request_id,
                        reason="request_expired",
                        expired=True,
                        actor=actor,
                    )
                    continue
            if current_sel.champion != queued_req.expected_champion or (
                queued_req.candidate_name not in current_sel.candidates
            ):
                self.expire_or_invalidate_request(
                    queued_req.request_id,
                    reason="expected_champion_or_slate_changed",
                    actor=actor,
                )
                continue
            if self.exclusion_ledger.ledger_file.is_file() and (
                self.exclusion_ledger.is_excluded(
                    queued_req.candidate_name, slate_id=slate_id, season=queued_req.season
                )
                or self.exclusion_ledger.is_excluded(queued_req.candidate_name, season=queued_req.season)
            ):
                self.expire_or_invalidate_request(
                    queued_req.request_id,
                    reason="candidate_excluded_in_ledger",
                    actor=actor,
                )
                continue
            try:
                self._verify_request_evidence(queued_req)
            except Exception as exc:
                self.expire_or_invalidate_request(
                    queued_req.request_id,
                    reason=f"evidence_verification_failed:{exc}",
                    actor=actor,
                )
                continue

            # Promote this queued pass to pending_approval requiring fresh human review
            requests, closed_slates, next_seq = self._load_state()
            ts = datetime.now(UTC).isoformat()
            promoted: AdoptionRequest | None = None
            updated_list: list[AdoptionRequest] = []
            for req in requests:
                if req.request_id == queued_req.request_id:
                    promoted = replace(
                        req,
                        status="pending_approval",
                        approval_ref=None,
                        approved_pr_head_sha=None,
                        actor=actor,
                        reason=f"Promoted from queue for fresh approval at GW{req.checkpoint_gw}",
                        updated_at_utc=ts,
                    )
                    updated_list.append(promoted)
                else:
                    updated_list.append(req)
            assert promoted is not None
            self._save_state(updated_list, closed_slates, next_seq)
            self.adoption_ledger.record_disposition(
                request_id=promoted.request_id,
                slate_id=promoted.slate_id,
                season=promoted.season,
                checkpoint_gw=promoted.checkpoint_gw,
                candidate_name=promoted.candidate_name,
                expected_champion=promoted.expected_champion,
                bundle_hash=promoted.bundle_hash,
                disposition="requested",
                actor=actor,
                reason=promoted.reason,
                recorded_at=ts,
            )
            return promoted
        return None


@dataclass(frozen=True)
class NotificationMessage:
    """Single-email notification payload bound to a durable adoption request ID."""

    request_id: str
    slate_id: str
    season: str
    checkpoint_gw: int
    candidate_name: str
    expected_champion: str
    bundle_hash: str
    archive_sha256: str | None
    review_url: str
    recipient: str
    subject: str
    body: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class MailProvider(Protocol):
    """Pluggable mail provider supporting delivery status reconciliation by request_id."""

    def send_adoption_notice(self, message: NotificationMessage) -> str: ...

    def query_delivery_status(self, request_id: str) -> str: ...


@dataclass(frozen=True)
class NotificationRecord:
    """Append-only SHA-256 hash-chained notification ledger record (`notifications.jsonl`)."""

    request_id: str
    slate_id: str
    season: str
    checkpoint_gw: int
    candidate_name: str
    expected_champion: str
    bundle_hash: str
    archive_sha256: str | None
    review_url: str
    recipient: str
    status: NotificationStatus
    recorded_at: str
    provider_message_id: str | None = None
    details: str = ""
    prev_record_hash: str = "0" * 64
    record_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def hash_payload(self) -> dict[str, Any]:
        data = self.to_dict()
        data.pop("record_hash", None)
        return data

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "NotificationRecord":
        return cls(
            request_id=str(data["request_id"]),
            slate_id=str(data["slate_id"]),
            season=str(data["season"]),
            checkpoint_gw=int(data["checkpoint_gw"]),
            candidate_name=str(data["candidate_name"]),
            expected_champion=str(data["expected_champion"]),
            bundle_hash=str(data["bundle_hash"]),
            archive_sha256=str(data["archive_sha256"]) if data.get("archive_sha256") is not None else None,
            review_url=str(data["review_url"]),
            recipient=str(data["recipient"]),
            status=data["status"],
            recorded_at=str(data["recorded_at"]),
            provider_message_id=(
                str(data["provider_message_id"]) if data.get("provider_message_id") is not None else None
            ),
            details=str(data.get("details", "")),
            prev_record_hash=str(data["prev_record_hash"]),
            record_hash=str(data["record_hash"]),
        )


class NotificationDispatcher:
    """Deduplicates adoption notices by durable request_id and reconciles uncertain delivery before retry."""

    def __init__(self, evidence_root: Path | str, *, provider: MailProvider) -> None:
        raw_root = Path(evidence_root).resolve()
        self.evidence_root = load_season_lifecycle().assert_unsealed_storage_path(
            raw_root, error_message="Protected notification ledger root"
        )
        self.ledger_file = self.evidence_root / "notifications.jsonl"
        self.provider = provider

    def load_all_records(self) -> list[NotificationRecord]:
        return _load_chained_jsonl(
            self.ledger_file,
            NotificationRecord.from_dict,
            NotificationRecord.hash_payload,
        )

    def latest_for_request(self, request_id: str) -> NotificationRecord | None:
        matches = [r for r in self.load_all_records() if r.request_id == request_id]
        return matches[-1] if matches else None

    def _append_record(
        self,
        *,
        request: AdoptionRequest,
        review_url: str,
        recipient: str,
        status: NotificationStatus,
        provider_message_id: str | None = None,
        details: str = "",
    ) -> NotificationRecord:
        existing = self.load_all_records()
        prev_hash = existing[-1].record_hash if existing else ("0" * 64)
        draft = NotificationRecord(
            request_id=request.request_id,
            slate_id=request.slate_id,
            season=request.season,
            checkpoint_gw=request.checkpoint_gw,
            candidate_name=request.candidate_name,
            expected_champion=request.expected_champion,
            bundle_hash=request.bundle_hash,
            archive_sha256=request.archive_sha256,
            review_url=review_url,
            recipient=recipient,
            status=status,
            recorded_at=datetime.now(UTC).isoformat(),
            provider_message_id=provider_message_id,
            details=details,
            prev_record_hash=prev_hash,
            record_hash="",
        )
        final = replace(draft, record_hash=_compute_chain_record_hash(draft.hash_payload()))
        _append_chained_jsonl(self.ledger_file, final.to_dict())
        return final

    @staticmethod
    def build_message(
        request: AdoptionRequest,
        *,
        review_url: str,
        recipient: str,
    ) -> NotificationMessage:
        if not review_url.strip() or not recipient.strip():
            raise ValueError("Notification requires non-empty review_url and recipient")
        subject = (
            f"[FPL Champion Adoption] Approval required: {request.candidate_name} "
            f"(GW{request.checkpoint_gw}, {request.request_id})"
        )
        body = "\n".join(
            [
                "Verified Champion adoption pass awaiting protected GitHub Actions review.",
                f"Review URL        : {review_url}",
                f"Request ID        : {request.request_id}",
                f"Slate ID          : {request.slate_id}",
                f"Season / GW       : {request.season} GW{request.checkpoint_gw}",
                f"Candidate         : {request.candidate_name}",
                f"Expected Champion : {request.expected_champion}",
                f"Bundle SHA-256    : {request.bundle_hash}",
                f"Archive SHA-256   : {request.archive_sha256 or 'none'}",
            ]
        )
        return NotificationMessage(
            request_id=request.request_id,
            slate_id=request.slate_id,
            season=request.season,
            checkpoint_gw=request.checkpoint_gw,
            candidate_name=request.candidate_name,
            expected_champion=request.expected_champion,
            bundle_hash=request.bundle_hash,
            archive_sha256=request.archive_sha256,
            review_url=review_url,
            recipient=recipient,
            subject=subject,
            body=body,
        )

    def reconcile_and_dispatch(
        self,
        request: AdoptionRequest,
        *,
        review_url: str,
        recipient: str = "operator@example.com",
    ) -> NotificationRecord:
        """Send at most one notice per request_id; reconcile uncertain state before any retry."""
        if request.status != "pending_approval":
            raise ValueError(
                f"Cannot dispatch adoption notice for request '{request.request_id}' in status '{request.status}'"
            )

        latest = self.latest_for_request(request.request_id)
        if latest is not None:
            if latest.status == "delivered":
                return latest
            if latest.status in ("uncertain", "send_attempted"):
                provider_status = self.provider.query_delivery_status(request.request_id)
                if provider_status == "delivered":
                    return self._append_record(
                        request=request,
                        review_url=review_url,
                        recipient=recipient,
                        status="delivered",
                        provider_message_id=latest.provider_message_id or f"reconciled-{request.request_id}",
                        details="Reconciled delivered notice from provider without resending",
                    )
                if provider_status != "not_found":
                    raise UnresolvedDeliveryError(
                        f"Delivery status for request '{request.request_id}' is '{provider_status}'; "
                        "blocking blind resend until reconciled"
                    )

        message = self.build_message(request, review_url=review_url, recipient=recipient)
        self._append_record(
            request=request,
            review_url=review_url,
            recipient=recipient,
            status="send_attempted",
            details="Persisted send attempt before provider dispatch",
        )
        try:
            msg_id = self.provider.send_adoption_notice(message)
        except (UncertainDeliveryAckError, TimeoutError) as exc:
            return self._append_record(
                request=request,
                review_url=review_url,
                recipient=recipient,
                status="uncertain",
                details=f"Provider acknowledgment lost or uncertain: {exc}",
            )
        if not isinstance(msg_id, str) or not msg_id.strip():
            return self._append_record(
                request=request,
                review_url=review_url,
                recipient=recipient,
                status="uncertain",
                details="Provider returned empty message_id",
            )
        return self._append_record(
            request=request,
            review_url=review_url,
            recipient=recipient,
            status="delivered",
            provider_message_id=msg_id.strip(),
            details="Provider confirmed notice delivery",
        )


@dataclass(frozen=True)
class ReservationRecord:
    """Durable shared lock record between adoption merger and ExclusionLedger writers (`reservation.json`)."""

    holder: str
    purpose: ReservationPurpose
    slate_id: str
    acquired_at_utc: str
    merge_state: MergeState
    request_id: str | None = None
    approved_pr_head_sha: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ReservationRecord":
        return cls(
            holder=str(data["holder"]),
            purpose=data["purpose"],
            slate_id=str(data["slate_id"]),
            acquired_at_utc=str(data["acquired_at_utc"]),
            merge_state=data["merge_state"],
            request_id=str(data["request_id"]) if data.get("request_id") is not None else None,
            approved_pr_head_sha=(
                str(data["approved_pr_head_sha"]) if data.get("approved_pr_head_sha") is not None else None
            ),
        )


class SharedReservationCoordinator:
    """Coordinates exclusive durable reservation across ExclusionLedger writers and protected adoption merge."""

    def __init__(
        self,
        evidence_root: Path | str,
        *,
        request_manager: AdoptionRequestManager | None = None,
    ) -> None:
        raw_root = Path(evidence_root).resolve()
        self.evidence_root = load_season_lifecycle().assert_unsealed_storage_path(
            raw_root, error_message="Protected reservation root"
        )
        self.reservation_file = self.evidence_root / "reservation.json"
        self.exclusions_path = self.evidence_root / "exclusions.jsonl"
        self.registry_path = self.evidence_root / "registry.jsonl"
        self.adoption_ledger_path = self.evidence_root / "adoption_ledger.jsonl"
        self.request_manager = request_manager or AdoptionRequestManager(self.evidence_root)

    def current_reservation(self) -> ReservationRecord | None:
        if not self.reservation_file.is_file():
            return None
        return ReservationRecord.from_dict(json.loads(self.reservation_file.read_bytes()))

    def acquire_reservation(
        self,
        *,
        holder: str,
        purpose: ReservationPurpose,
        slate_id: str,
        request_id: str | None = None,
        approved_pr_head_sha: str | None = None,
    ) -> ReservationRecord:
        if not holder.strip() or not slate_id.strip():
            raise ValueError("Reservation requires non-empty holder and slate_id")
        self.evidence_root.mkdir(parents=True, exist_ok=True)
        existing = self.current_reservation()
        if existing is not None:
            raise ReservationConflictError(
                f"Shared reservation already held by '{existing.holder}' for '{existing.purpose}' "
                f"(state={existing.merge_state}, request_id={existing.request_id})"
            )
        rec = ReservationRecord(
            holder=holder,
            purpose=purpose,
            slate_id=slate_id,
            acquired_at_utc=datetime.now(UTC).isoformat(),
            merge_state="held",
            request_id=request_id,
            approved_pr_head_sha=approved_pr_head_sha,
        )
        raw = json.dumps(rec.to_dict(), indent=2, sort_keys=True, allow_nan=False).encode("utf-8") + b"\n"
        try:
            with self.reservation_file.open("xb") as handle:
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
        except FileExistsError as exc:
            cur = self.current_reservation()
            raise ReservationConflictError(
                f"Shared reservation conflict with '{cur.holder if cur else 'unknown'}'"
            ) from exc
        return rec

    def _update_reservation_state(self, rec: ReservationRecord, merge_state: MergeState) -> ReservationRecord:
        updated = replace(rec, merge_state=merge_state)
        raw = json.dumps(updated.to_dict(), indent=2, sort_keys=True, allow_nan=False).encode("utf-8") + b"\n"
        tmp = self.reservation_file.with_suffix(".json.tmp")
        try:
            tmp.write_bytes(raw)
            os.replace(tmp, self.reservation_file)
        finally:
            tmp.unlink(missing_ok=True)
        return updated

    def release_reservation(self, *, force_unknown: bool = False) -> None:
        cur = self.current_reservation()
        if cur is None:
            return
        if cur.merge_state == "merge_outcome_unknown" and not force_unknown:
            raise ReservationConflictError(
                "Cannot release reservation while merge_state is 'merge_outcome_unknown' without reconciliation"
            )
        self.reservation_file.unlink(missing_ok=True)

    def record_exclusion_under_reservation(
        self,
        *,
        holder: str,
        slate_id: str,
        season: str,
        candidate_name: str,
        checkpoint_gw: int,
        reason_code: str,
        details: str,
        evidence_hash: str | None = None,
    ) -> ExclusionRecord:
        """Acquire shared reservation, append finalist exclusion to ExclusionLedger, and release reservation."""
        self.acquire_reservation(
            holder=holder,
            purpose="exclusion_write",
            slate_id=slate_id,
        )
        try:
            ledger = ExclusionLedger(self.exclusions_path)
            return ledger.record_exclusion(
                slate_id=slate_id,
                season=season,
                candidate_name=candidate_name,
                checkpoint_gw=checkpoint_gw,
                reason_code=reason_code,
                details=details,
                evidence_hash=evidence_hash,
            )
        finally:
            self.release_reservation()

    def execute_reserved_adoption_merge(
        self,
        *,
        request_id: str,
        slate_id: str,
        approval_ref: str,
        approved_pr_head_sha: str,
        pr_head_sha: str,
        changed_files: Sequence[str],
        checks_green: bool,
        auto_merge_enabled: bool = False,
        main_selection_path: Path | None = None,
        holder: str = "github-app-adoption-merger",
        pre_merge_hook: Callable[[], None] | None = None,
        post_merge_ack_hook: Callable[[], None] | None = None,
    ) -> dict[str, Any]:
        """Acquire shared reservation, recheck eligibility & freshness, and atomically merge selection + receipt."""
        sel_path = main_selection_path or DEFAULT_CONFIG_PATH
        req = self.request_manager.get_request(request_id)
        if req is None:
            raise ValueError(f"Adoption request '{request_id}' not found")
        if req.slate_id != slate_id:
            raise ValueError(f"Request '{request_id}' belongs to slate '{req.slate_id}', not '{slate_id}'")

        # Idempotent retry check if request was already adopted and no unknown reservation is held
        if req.status == "adopted" and self.current_reservation() is None:
            receipt_file = sel_path.with_suffix(".adoption.json")
            if receipt_file.is_file():
                receipt_data = json.loads(receipt_file.read_bytes())
                if receipt_data.get("request_id") == request_id and receipt_data.get("slate_id") == slate_id:
                    return {
                        "status": "already_adopted",
                        "merged": False,
                        "request_id": request_id,
                        "slate_id": slate_id,
                        "champion": load_model_selection(sel_path).champion,
                    }

        reservation = self.acquire_reservation(
            holder=holder,
            purpose="adoption_merge",
            slate_id=slate_id,
            request_id=request_id,
            approved_pr_head_sha=approved_pr_head_sha,
        )
        retain_unknown_reservation = False
        try:
            if auto_merge_enabled:
                raise ValueError("Independent auto-merge must be disabled for Champion adoption PRs")
            if not checks_green:
                raise ValueError("Required PR checks must be green before Champion adoption merge")
            if req.status not in ("pending_approval", "approved"):
                raise StaleAdoptionBlockedError(
                    f"Request '{request_id}' is in non-mergeable status '{req.status}'"
                )
            if not approved_pr_head_sha.strip() or pr_head_sha != approved_pr_head_sha:
                raise ValueError(
                    f"Approved PR head SHA mismatch: approved '{approved_pr_head_sha}', current '{pr_head_sha}'"
                )
            if set(changed_files) != AUTHORIZED_ADOPTION_DIFF_FILES:
                raise ValueError(
                    f"Adoption PR contains unauthorized file diff: {sorted(changed_files)}"
                )

            # Recheck fresh ExclusionLedger under reservation before merging
            if self.exclusions_path.is_file():
                excl_ledger = ExclusionLedger(self.exclusions_path)
                if excl_ledger.is_excluded(req.candidate_name, slate_id=slate_id, season=req.season) or (
                    excl_ledger.is_excluded(req.candidate_name, season=req.season)
                ):
                    self.request_manager.expire_or_invalidate_request(
                        request_id,
                        reason="candidate_excluded_after_pr_checks_before_merge",
                        actor=holder,
                    )
                    raise StaleAdoptionBlockedError(
                        f"Candidate '{req.candidate_name}' was excluded in ExclusionLedger before merge reservation"
                    )

            # Recheck fresh protected main selection
            current_main_sel = load_model_selection(sel_path)
            if (
                current_main_sel.champion != req.expected_champion
                or not current_main_sel.podium_sealed
                or req.candidate_name not in current_main_sel.candidates
            ):
                self.request_manager.expire_or_invalidate_request(
                    request_id,
                    reason="protected_main_champion_or_slate_changed",
                    actor=holder,
                )
                raise StaleAdoptionBlockedError(
                    "Protected main selection changed or slate unsealed before adoption merge"
                )

            if req.status == "pending_approval":
                req = self.request_manager.record_approval(
                    request_id,
                    actor=holder,
                    approval_ref=approval_ref,
                    approved_pr_head_sha=approved_pr_head_sha,
                )

            bundle_arg: Path | str
            if req.snapshot_archive_path is not None:
                snap = Path(req.snapshot_archive_path)
                bundle_arg = snap if snap.is_absolute() else (self.evidence_root / snap).resolve()
            elif req.bundle_path is not None:
                bp = Path(req.bundle_path)
                bundle_arg = bp if bp.is_absolute() else (self.evidence_root / bp).resolve()
            else:
                raise ValueError(f"Request '{request_id}' lacks snapshot_archive_path and bundle_path")

            # Enter merge_in_flight: any interruption from here retains reservation as merge_outcome_unknown
            reservation = self._update_reservation_state(reservation, "merge_in_flight")
            try:
                if pre_merge_hook is not None:
                    pre_merge_hook()

                updated_sel = adopt_champion(
                    bundle_arg,
                    config_path=sel_path,
                    approval_ref=approval_ref,
                    expected_current_champion=req.expected_champion,
                    candidate_name=req.candidate_name,
                    approved_bundle_hash=req.bundle_hash,
                    snapshot_archive_path=bundle_arg if req.snapshot_archive_path is not None else None,
                    expected_archive_sha256=req.archive_sha256,
                    canonical_registry_path=self.registry_path if self.registry_path.is_file() else None,
                    canonical_exclusions_path=self.exclusions_path if self.exclusions_path.is_file() else None,
                    request_id=req.request_id,
                    slate_id=req.slate_id,
                    approved_commit_sha=approved_pr_head_sha,
                )

                if post_merge_ack_hook is not None:
                    post_merge_ack_hook()
            except Exception:
                retain_unknown_reservation = True
                self._update_reservation_state(reservation, "merge_outcome_unknown")
                raise

            self.request_manager.mark_adopted(
                request_id,
                actor=holder,
                approval_ref=approval_ref,
                approved_pr_head_sha=approved_pr_head_sha,
            )
            return {
                "status": "adopted",
                "merged": True,
                "request_id": request_id,
                "slate_id": slate_id,
                "champion": updated_sel.champion,
                "podium_sealed": updated_sel.podium_sealed,
            }
        finally:
            if not retain_unknown_reservation:
                self.release_reservation()

    def reconcile_unknown_merge(
        self,
        *,
        main_selection_path: Path | None = None,
        actor: str = "adoption-reconciler",
    ) -> dict[str, Any]:
        """Reconcile an in-flight or unknown merge reservation by inspecting protected main's selection & receipt."""
        cur = self.current_reservation()
        if cur is None:
            return {"status": "no_reservation", "reconciled": False, "merged": False}
        if cur.purpose != "adoption_merge" or cur.merge_state not in ("merge_in_flight", "merge_outcome_unknown"):
            raise ValueError(
                f"Cannot reconcile reservation with purpose='{cur.purpose}', merge_state='{cur.merge_state}'"
            )

        sel_path = main_selection_path or DEFAULT_CONFIG_PATH
        receipt_path = sel_path.with_suffix(".adoption.json")
        if receipt_path.is_file() and cur.request_id is not None:
            receipt = json.loads(receipt_path.read_bytes())
            main_sel = load_model_selection(sel_path)
            if (
                receipt.get("request_id") == cur.request_id
                and receipt.get("slate_id") == cur.slate_id
                and main_sel.champion == receipt.get("candidate_name")
            ):
                self.request_manager.mark_adopted(
                    cur.request_id,
                    actor=actor,
                    approval_ref=str(receipt.get("approval_ref") or "reconciled-from-main"),
                    approved_pr_head_sha=cur.approved_pr_head_sha,
                    reason="Reconciled unknown merge from matching receipt on protected main",
                )
                self.release_reservation(force_unknown=True)
                return {
                    "status": "reconciled_merged",
                    "reconciled": True,
                    "merged": True,
                    "request_id": cur.request_id,
                    "slate_id": cur.slate_id,
                    "champion": main_sel.champion,
                }

        # Protected main still has pre-adoption selection: reset unknown reservation so retry re-verifies from scratch
        self.release_reservation(force_unknown=True)
        return {
            "status": "reconciled_not_merged_reset_for_retry",
            "reconciled": True,
            "merged": False,
            "request_id": cur.request_id,
            "slate_id": cur.slate_id,
        }
