"""Confirmation admission and immutable attempt registry.

Implements Phase 9 requirements:
1. One frozen finalist per confirmation round: model dependency/source hashes, parameters,
   training/seed, dev selection reference, protocol hash, and family history.
2. Registry append-only atomicity and tamper-evident integrity hashing.
3. Family-wise continuity across aliases and model renames; prevents history reset.
4. Prevention of duplicate, adaptive, or peeking runs; requires registered complete schedule.
5. Sealed-path protection enforcing strict holdout boundaries (2026-27 GW6+).
6. Candidate Ledger integration preventing re-evaluation of active Dead Levers without explicit override.
7. Verification of completed schedules before verdict admission.
"""

from __future__ import annotations

from collections.abc import Sequence
import csv
from dataclasses import asdict, dataclass, replace
from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from backtesting.evidence_statistics import ScientificVerdict

AttemptStatus = Literal["registered", "in_progress", "completed", "withdrawn", "invalidated"]
ExecutionStatus = Literal["not_run", "partial", "censored", "complete"]


class RegistryError(Exception):
    """Base exception for confirmation registry errors."""


class DuplicateAttemptError(RegistryError):
    """Raised when registering an identical finalist attempt that is already active or completed."""


class SealedDataViolationError(RegistryError):
    """Raised when an evaluation attempt references sealed or protected holdout seasons."""


class DeadLeverViolationError(RegistryError):
    """Raised when an attempt tests an active dead lever before its revisit_after moratorium date."""


class AdaptiveRunViolationError(RegistryError):
    """Raised when attempting to mutate or selectively reset prior attempt history."""


class IncompleteScheduleError(RegistryError):
    """Raised when an attempt is prematurely finalized before completing its registered schedule."""


class TamperedRegistryError(RegistryError):
    """Raised when disk records fail cryptographic tamper-evident verification."""


@dataclass(frozen=True)
class FinalistRegistration:
    """Immutable audit record for a single confirmation round finalist."""

    attempt_id: str
    candidate_name: str
    champion_name: str
    mechanism_family: str
    parent_attempt_id: str | None
    model_source_hash: str
    parameters_hash: str
    dev_selection_record_ref: str
    protocol_hash: str
    status: AttemptStatus
    execution_status: ExecutionStatus
    scientific_verdict: ScientificVerdict | None
    attempt_number_in_family: int
    registered_at: str
    completed_at: str | None = None
    bundle_path: str | None = None
    human_approval_ref: str | None = None
    known_aliases: tuple[str, ...] = ()
    registered_gameweeks: tuple[int, ...] = tuple(range(1, 39))
    completed_gameweeks: tuple[int, ...] = ()
    prev_record_hash: str = "0" * 64
    record_hash: str = ""
    requested_seasons: tuple[str, ...] = ()
    max_family_attempts: int | None = None
    score_trace_hash: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["known_aliases"] = list(self.known_aliases)
        data["registered_gameweeks"] = list(self.registered_gameweeks)
        data["completed_gameweeks"] = list(self.completed_gameweeks)
        data["requested_seasons"] = list(self.requested_seasons)
        data["prev_record_hash"] = self.prev_record_hash
        return data

    def compute_record_hash(self) -> str:
        """Compute tamper-evident SHA256 digest of record contents excluding the hash itself."""
        payload = {
            "attempt_id": self.attempt_id,
            "candidate_name": self.candidate_name,
            "champion_name": self.champion_name,
            "mechanism_family": self.mechanism_family,
            "parent_attempt_id": self.parent_attempt_id,
            "model_source_hash": self.model_source_hash,
            "parameters_hash": self.parameters_hash,
            "dev_selection_record_ref": self.dev_selection_record_ref,
            "protocol_hash": self.protocol_hash,
            "status": self.status,
            "execution_status": self.execution_status,
            "scientific_verdict": self.scientific_verdict,
            "attempt_number_in_family": self.attempt_number_in_family,
            "registered_at": self.registered_at,
            "completed_at": self.completed_at,
            "bundle_path": self.bundle_path,
            "human_approval_ref": self.human_approval_ref,
            "known_aliases": sorted(self.known_aliases),
            "registered_gameweeks": list(self.registered_gameweeks),
            "completed_gameweeks": list(self.completed_gameweeks),
            "prev_record_hash": self.prev_record_hash,
        }
        if self.requested_seasons:
            payload["requested_seasons"] = list(self.requested_seasons)
        if self.max_family_attempts is not None:
            payload["max_family_attempts"] = self.max_family_attempts
        if self.score_trace_hash is not None:
            payload["score_trace_hash"] = self.score_trace_hash
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


class ConfirmationRegistry:
    """Append-only, tamper-evident registry tracking candidate confirmation attempts."""

    def __init__(self, registry_file: Path | str | None = None) -> None:
        if registry_file is None:
            self.registry_file = Path("data/reports/confirmation_registry/registry.jsonl")
        else:
            self.registry_file = Path(registry_file)

    def _ensure_dir(self) -> None:
        self.registry_file.parent.mkdir(parents=True, exist_ok=True)

    def load_all_records(self) -> list[FinalistRegistration]:
        """Load and verify all registration records from disk."""
        if not self.registry_file.is_file():
            return []

        records: list[FinalistRegistration] = []
        with open(self.registry_file, encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                raw = line.strip()
                if not raw:
                    continue
                try:
                    data = json.loads(raw)
                    rec = FinalistRegistration(
                        attempt_id=data["attempt_id"],
                        candidate_name=data["candidate_name"],
                        champion_name=data["champion_name"],
                        mechanism_family=data["mechanism_family"],
                        parent_attempt_id=data.get("parent_attempt_id"),
                        model_source_hash=data["model_source_hash"],
                        parameters_hash=data["parameters_hash"],
                        dev_selection_record_ref=data["dev_selection_record_ref"],
                        protocol_hash=data["protocol_hash"],
                        status=data["status"],
                        execution_status=data["execution_status"],
                        scientific_verdict=data.get("scientific_verdict"),
                        attempt_number_in_family=int(data["attempt_number_in_family"]),
                        registered_at=data["registered_at"],
                        completed_at=data.get("completed_at"),
                        bundle_path=data.get("bundle_path"),
                        human_approval_ref=data.get("human_approval_ref"),
                        known_aliases=tuple(data.get("known_aliases", ())),
                        registered_gameweeks=tuple(data.get("registered_gameweeks", ())),
                        completed_gameweeks=tuple(data.get("completed_gameweeks", ())),
                        prev_record_hash=data.get("prev_record_hash", "0" * 64),
                        record_hash=data.get("record_hash", ""),
                        requested_seasons=tuple(data.get("requested_seasons", ())),
                        max_family_attempts=data.get("max_family_attempts"),
                        score_trace_hash=data.get("score_trace_hash"),
                    )
                    expected_hash = rec.compute_record_hash()
                    if rec.record_hash != expected_hash:
                        raise TamperedRegistryError(
                            f"Cryptographic hash mismatch at line {line_no} for attempt '{rec.attempt_id}'"
                        )
                    expected_prev = records[-1].record_hash if records else ("0" * 64)
                    if rec.prev_record_hash != expected_prev:
                        raise TamperedRegistryError(
                            f"Cryptographic chain break at line {line_no} for attempt '{rec.attempt_id}': "
                            f"expected prev_record_hash '{expected_prev}', got '{rec.prev_record_hash}'"
                        )
                    records.append(rec)
                except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
                    raise TamperedRegistryError(f"Corrupt registry record at line {line_no}: {exc}") from exc

        return records

    def verify_integrity(self) -> bool:
        """Cryptographically verify all records in the registry."""
        self.load_all_records()
        return True

    def get_attempt(self, attempt_id: str) -> FinalistRegistration | None:
        """Find the latest state of a specific attempt by ID."""
        records = [r for r in self.load_all_records() if r.attempt_id == attempt_id]
        return records[-1] if records else None

    def find_family_history(
        self,
        mechanism_family: str,
        candidate_name: str | None = None,
        aliases: Sequence[str] | None = None,
    ) -> list[FinalistRegistration]:
        """Find all registered attempts within the same declared mechanism family or aliases."""
        alias_set = set(aliases or ())
        if candidate_name:
            alias_set.add(candidate_name)

        history: list[FinalistRegistration] = []
        for r in self.load_all_records():
            matches_family = r.mechanism_family == mechanism_family
            matches_alias = bool(alias_set and (r.candidate_name in alias_set or any(a in alias_set for a in r.known_aliases)))
            if matches_family or matches_alias:
                history.append(r)
        return history

    def check_sealed_data_safety(
        self,
        requested_seasons: Sequence[str],
        requested_gameweeks: Sequence[int] | None = None,
    ) -> None:
        """Enforce strict holdout boundary: season 2026-27 GW6+ is completely sealed."""
        for season in requested_seasons:
            if season == "2026-27":
                gws = requested_gameweeks or tuple(range(1, 39))
                if any(gw >= 6 for gw in gws):
                    raise SealedDataViolationError(
                        "Access to sealed season 2026-27 GW6+ strictly prohibited without approved protocol amendment"
                    )

    def check_candidate_ledger_safety(
        self,
        candidate_name: str,
        lever_description: str,
        ledger_csv_path: Path | str | None = None,
    ) -> None:
        """Enforce 1-year Dead Lever moratorium in Candidate Ledger."""
        path = Path(ledger_csv_path or "docs/research/candidate-ledger/candidate_ledger.csv")
        if not path.is_file():
            return

        today = date.today()
        cand_lower = candidate_name.lower().strip()
        lever_lower = lever_description.lower().strip()

        with open(path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                status = row.get("status", "").lower().strip()
                if status != "dead":
                    continue
                revisit_str = row.get("revisit_after", "").strip()
                if not revisit_str:
                    continue
                try:
                    revisit_date = date.fromisoformat(revisit_str)
                except ValueError:
                    continue

                if today < revisit_date:
                    tried_as = [item.strip().lower() for item in row.get("tried_as", "").split()]
                    row_lever = row.get("lever", "").lower().strip()
                    if cand_lower in tried_as or cand_lower == row_lever or (lever_lower and lever_lower in row_lever):
                        raise DeadLeverViolationError(
                            f"Candidate '{candidate_name}' matches active Dead Lever '{row.get('lever')}' "
                            f"locked until {revisit_str}. Reopening requires explicit user authorization."
                        )

    def register_finalist(
        self,
        candidate_name: str,
        champion_name: str,
        mechanism_family: str,
        model_source_hash: str,
        parameters_hash: str,
        dev_selection_record_ref: str,
        protocol_hash: str,
        *,
        attempt_id: str | None = None,
        parent_attempt_id: str | None = None,
        known_aliases: Sequence[str] = (),
        registered_gameweeks: Sequence[int] = tuple(range(1, 39)),
        human_approval_ref: str | None = None,
        ledger_csv_path: Path | str | None = None,
        candidate_lever_description: str = "",
        requested_seasons: Sequence[str] = ("2024-25",),
        max_family_attempts: int = 10,
    ) -> FinalistRegistration:
        """Register a new finalist confirmation round."""
        self._ensure_dir()

        self.check_sealed_data_safety(requested_seasons, registered_gameweeks)
        self.check_candidate_ledger_safety(candidate_name, candidate_lever_description, ledger_csv_path)

        family_history = self.find_family_history(mechanism_family, candidate_name, known_aliases)
        for prior in family_history:
            if (
                prior.candidate_name == candidate_name
                and prior.model_source_hash == model_source_hash
                and prior.parameters_hash == parameters_hash
                and prior.protocol_hash == protocol_hash
                and prior.status in ("registered", "in_progress", "completed")
            ):
                raise DuplicateAttemptError(
                    f"Candidate '{candidate_name}' with identical code and parameters is already {prior.status} "
                    f"in attempt '{prior.attempt_id}'. Adaptive reruns or overwrites are prohibited."
                )

        existing_records = self.load_all_records()
        prev_hash = existing_records[-1].record_hash if existing_records else ("0" * 64)

        attempt_number = len({record.attempt_id for record in family_history}) + 1
        if max_family_attempts < 1 or attempt_number > max_family_attempts:
            raise AdaptiveRunViolationError("Registered mechanism family attempt budget exhausted or invalid")
        if any(record.max_family_attempts != max_family_attempts for record in family_history):
            raise AdaptiveRunViolationError("Cannot change an existing mechanism family's registered attempt budget")
        schedule = tuple(registered_gameweeks)
        if not schedule or len(set(schedule)) != len(schedule) or any(not 1 <= gw <= 38 for gw in schedule):
            raise RegistryError("Registered gameweeks must be a nonempty unique schedule within [1, 38]")
        if not requested_seasons or len(set(requested_seasons)) != len(requested_seasons):
            raise RegistryError("Requested seasons must be nonempty and unique")
        now_iso = datetime.now(timezone.utc).isoformat()

        if attempt_id is None:
            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            generated_id = f"eval-{candidate_name}-{ts}-{uuid4().hex[:12]}"
        else:
            generated_id = attempt_id
        if not generated_id.strip() or any(record.attempt_id == generated_id for record in existing_records):
            raise DuplicateAttemptError(f"Attempt ID '{generated_id}' is empty or already registered")

        if parent_attempt_id is None and family_history:
            parent_attempt_id = family_history[-1].attempt_id

        reg = FinalistRegistration(
            attempt_id=generated_id,
            candidate_name=candidate_name,
            champion_name=champion_name,
            mechanism_family=mechanism_family,
            parent_attempt_id=parent_attempt_id,
            model_source_hash=model_source_hash,
            parameters_hash=parameters_hash,
            dev_selection_record_ref=dev_selection_record_ref,
            protocol_hash=protocol_hash,
            status="registered",
            execution_status="not_run",
            scientific_verdict=None,
            attempt_number_in_family=attempt_number,
            registered_at=now_iso,
            known_aliases=tuple(known_aliases),
            registered_gameweeks=tuple(registered_gameweeks),
            completed_gameweeks=(),
            human_approval_ref=human_approval_ref,
            prev_record_hash=prev_hash,
            requested_seasons=tuple(requested_seasons),
            max_family_attempts=max_family_attempts,
        )

        record_hash = reg.compute_record_hash()
        final_reg = replace(reg, record_hash=record_hash)

        self._append_record(final_reg)
        return final_reg

    def transition_attempt_status(
        self,
        attempt_id: str,
        status: AttemptStatus,
        *,
        execution_status: ExecutionStatus | None = None,
        scientific_verdict: ScientificVerdict | None = None,
        completed_gameweeks: Sequence[int] | None = None,
        bundle_path: str | None = None,
        human_approval_ref: str | None = None,
        score_trace_hash: str | None = None,
    ) -> FinalistRegistration:
        """Append a state transition record for an existing attempt."""
        prior = self.get_attempt(attempt_id)
        if prior is None:
            raise RegistryError(f"Attempt '{attempt_id}' not found in registry")

        transition_graph: dict[AttemptStatus, tuple[AttemptStatus, ...]] = {
            "registered": ("in_progress", "completed", "withdrawn", "invalidated"),
            "in_progress": ("in_progress", "completed", "withdrawn", "invalidated"),
            "completed": (),
            "withdrawn": (),
            "invalidated": (),
        }
        requested_fields = {
            "execution_status": execution_status,
            "scientific_verdict": scientific_verdict,
            "completed_gameweeks": tuple(completed_gameweeks) if completed_gameweeks is not None else None,
            "bundle_path": bundle_path,
            "human_approval_ref": human_approval_ref,
            "score_trace_hash": score_trace_hash,
        }
        unchanged = status == prior.status and all(
            value is None or value == getattr(prior, name) for name, value in requested_fields.items()
        )
        if unchanged:
            return prior
        if status not in transition_graph.get(prior.status, ()):
            raise AdaptiveRunViolationError(
                f"Cannot re-open or overwrite {prior.status} confirmation attempt '{attempt_id}' with status '{status}'"
            )

        new_completed_gws = tuple(completed_gameweeks) if completed_gameweeks is not None else prior.completed_gameweeks
        if (
            len(set(new_completed_gws)) != len(new_completed_gws)
            or not set(prior.completed_gameweeks) <= set(new_completed_gws) <= set(prior.registered_gameweeks)
        ):
            raise IncompleteScheduleError("Completed gameweeks must progress monotonically within the registered schedule")
        if prior.execution_status == "complete" and (
            (execution_status is not None and execution_status != "complete")
            or new_completed_gws != prior.completed_gameweeks
            or (score_trace_hash is not None and score_trace_hash != prior.score_trace_hash)
        ):
            raise AdaptiveRunViolationError("Cannot replace a completed confirmation score trace or execution state")
        if score_trace_hash is not None and (
            len(score_trace_hash) != 64 or any(char not in "0123456789abcdef" for char in score_trace_hash)
        ):
            raise RegistryError("Score trace hash must be a SHA256 hex digest")

        # Enforce complete schedule before completion
        if status == "completed" or execution_status == "complete":
            if set(new_completed_gws) != set(prior.registered_gameweeks):
                raise IncompleteScheduleError(
                    f"Attempt '{attempt_id}' has completed gameweeks {sorted(new_completed_gws)}, "
                    f"which does not match registered schedule {sorted(prior.registered_gameweeks)}. "
                    f"Stopping when intermediate results look favorable is strictly prohibited."
                )
        if status == "completed" and (execution_status or prior.execution_status) != "complete":
            raise IncompleteScheduleError("Completed attempt requires complete execution status")

        existing_records = self.load_all_records()
        prev_hash = existing_records[-1].record_hash if existing_records else ("0" * 64)

        now_iso = datetime.now(timezone.utc).isoformat()
        updated_dict = prior.to_dict()
        updated_dict["status"] = status
        updated_dict["prev_record_hash"] = prev_hash
        if execution_status is not None:
            updated_dict["execution_status"] = execution_status
        if scientific_verdict is not None:
            updated_dict["scientific_verdict"] = scientific_verdict
        if completed_gameweeks is not None:
            updated_dict["completed_gameweeks"] = list(new_completed_gws)
        if bundle_path is not None:
            updated_dict["bundle_path"] = bundle_path
        if human_approval_ref is not None:
            updated_dict["human_approval_ref"] = human_approval_ref
        if score_trace_hash is not None:
            updated_dict["score_trace_hash"] = score_trace_hash
        if status == "completed":
            updated_dict["completed_at"] = now_iso

        updated = FinalistRegistration(
            attempt_id=updated_dict["attempt_id"],
            candidate_name=updated_dict["candidate_name"],
            champion_name=updated_dict["champion_name"],
            mechanism_family=updated_dict["mechanism_family"],
            parent_attempt_id=updated_dict.get("parent_attempt_id"),
            model_source_hash=updated_dict["model_source_hash"],
            parameters_hash=updated_dict["parameters_hash"],
            dev_selection_record_ref=updated_dict["dev_selection_record_ref"],
            protocol_hash=updated_dict["protocol_hash"],
            status=updated_dict["status"],
            execution_status=updated_dict["execution_status"],
            scientific_verdict=updated_dict.get("scientific_verdict"),
            attempt_number_in_family=int(updated_dict["attempt_number_in_family"]),
            registered_at=updated_dict["registered_at"],
            completed_at=updated_dict.get("completed_at"),
            bundle_path=updated_dict.get("bundle_path"),
            human_approval_ref=updated_dict.get("human_approval_ref"),
            known_aliases=tuple(updated_dict.get("known_aliases", ())),
            registered_gameweeks=tuple(updated_dict.get("registered_gameweeks", ())),
            completed_gameweeks=tuple(updated_dict.get("completed_gameweeks", ())),
            prev_record_hash=prev_hash,
            record_hash="",
            requested_seasons=tuple(updated_dict.get("requested_seasons", ())),
            max_family_attempts=updated_dict.get("max_family_attempts"),
            score_trace_hash=updated_dict.get("score_trace_hash"),
        )

        record_hash = updated.compute_record_hash()
        final_rec = replace(updated, record_hash=record_hash)

        self._append_record(final_rec)
        return final_rec

    def _append_record(self, record: FinalistRegistration) -> None:
        """Append record line to registry file."""
        self._ensure_dir()
        line = json.dumps(record.to_dict(), sort_keys=True) + "\n"
        with open(self.registry_file, "a", encoding="utf-8") as f:
            f.write(line)
            f.flush()
            os.fsync(f.fileno())
