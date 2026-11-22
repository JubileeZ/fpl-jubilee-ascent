"""CLI coordinator for protected Champion adoption requests, reserved merge, and production preflight (#197, #199, #200)."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any, Mapping

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backtesting.adoption_transaction import (
    AUTHORIZED_ADOPTION_DIFF_FILES,
    TERMINAL_REQUEST_STATUSES,
    AdoptionRequestManager,
    MergeInterruptedError,
    NotificationDispatcher,
    NotificationMessage,
    ProviderDeliveryStatus,
    ReservationRecord,
    SharedReservationCoordinator,
    UncertainDeliveryAckError,
)
from backtesting.portable_evidence import ExclusionLedger
from backtesting.season_rules import load_season_lifecycle
from backtesting.sparse_certification import verify_certification_artifacts
from clients.env_loader import configure_utf8_stdio
from commands.evaluate_model_promotion import adopt_champion
from commands.inventory_pilot_fixture import build_pilot_fixture_inventory
from models.selection import DEFAULT_CONFIG_PATH, load_model_selection

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CERTIFICATION_DIGEST_EXPECTED = "243962e549d2516b2008d96f874a569e0b208cea28b2c72912d5e4889b8cfb6a"


def _github_api_headers(token: str | None) -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "fpl-jubilee-ascent-coordinator/1.0",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _post_json_delivery(
    url: str,
    payload: Mapping[str, Any],
    headers: Mapping[str, str],
    *,
    transport: httpx.BaseTransport | None,
    timeout_seconds: float,
    context: str,
) -> dict[str, Any]:
    """POST JSON notice payload and classify network/5xx/non-JSON responses as UncertainDeliveryAckError."""
    try:
        with httpx.Client(timeout=timeout_seconds, transport=transport) as client:
            resp = client.post(url, json=dict(payload), headers=dict(headers))
    except (httpx.TimeoutException, httpx.RequestError) as exc:
        raise UncertainDeliveryAckError(f"{context} ack lost or timed out: {exc}") from exc
    if resp.status_code >= 500:
        raise UncertainDeliveryAckError(f"{context} server error {resp.status_code}")
    if not 200 <= resp.status_code < 300:
        raise RuntimeError(f"{context} rejected delivery with HTTP {resp.status_code}")
    try:
        data = resp.json()
    except Exception as exc:
        raise UncertainDeliveryAckError(f"{context} returned non-JSON ack: {exc}") from exc
    if not isinstance(data, dict):
        raise UncertainDeliveryAckError(f"{context} returned non-object JSON ack")
    return data


class HttpWebhookMailProvider:
    """Controlled HTTP webhook MailProvider for remote single-notice delivery & status reconciliation."""

    def __init__(
        self,
        webhook_url: str,
        *,
        api_key: str | None = None,
        status_url: str | None = None,
        transport: httpx.BaseTransport | None = None,
        timeout_seconds: float = 15.0,
    ) -> None:
        if not webhook_url.strip():
            raise ValueError("MAIL_PROVIDER_WEBHOOK_URL cannot be empty")
        self.webhook_url = webhook_url.strip()
        self.api_key = api_key.strip() if isinstance(api_key, str) and api_key.strip() else None
        self.status_url = status_url.strip() if isinstance(status_url, str) and status_url.strip() else None
        self.transport = transport
        self.timeout_seconds = float(timeout_seconds)

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def send_adoption_notice(self, message: NotificationMessage) -> str:
        payload = {"request_id": message.request_id, "message": message.to_dict()}
        data = _post_json_delivery(
            self.webhook_url,
            payload,
            self._headers(),
            transport=self.transport,
            timeout_seconds=self.timeout_seconds,
            context="Webhook provider",
        )
        msg_id = (
            data.get("provider_message_id")
            or data.get("message_id")
            or data.get("id")
        )
        return str(msg_id).strip() if isinstance(msg_id, str) and msg_id.strip() else f"webhook-{message.request_id}"

    def query_delivery_status(self, request_id: str) -> str:
        if not self.status_url:
            return "unknown"
        url = (
            self.status_url.format(request_id=request_id)
            if "{request_id}" in self.status_url
            else f"{self.status_url.rstrip('/')}/{request_id}"
        )
        try:
            with httpx.Client(timeout=self.timeout_seconds, transport=self.transport) as client:
                resp = client.get(url, headers=self._headers())
        except (httpx.TimeoutException, httpx.RequestError):
            return "unknown"
        if resp.status_code == 404:
            return "not_found"
        if resp.status_code != 200:
            return "unknown"
        try:
            data = resp.json()
        except Exception:
            return "unknown"
        status = str(data.get("status", "")).strip().lower()
        if status in ("delivered", "not_found"):
            return status
        return "unknown"


class FileOutboxMailProvider:
    """Durable file-backed mail provider for pilot harness and offline/reconciled notice delivery."""

    def __init__(self, outbox_dir: Path | str, *, override_status: str | None = None) -> None:
        self.outbox_dir = Path(outbox_dir).resolve()
        self.override_status = override_status

    def _msg_path(self, request_id: str) -> Path:
        return self.outbox_dir / f"{request_id}.json"

    def send_adoption_notice(self, message: NotificationMessage) -> str:
        self.outbox_dir.mkdir(parents=True, exist_ok=True)
        dest = self._msg_path(message.request_id)
        msg_id = f"outbox-{message.request_id}"
        payload = {
            "provider_message_id": msg_id,
            "delivered_at_utc": datetime.now(UTC).isoformat(),
            "message": message.to_dict(),
        }
        raw = json.dumps(payload, indent=2, sort_keys=True, allow_nan=False).encode("utf-8") + b"\n"
        tmp = dest.with_suffix(".json.tmp")
        try:
            tmp.write_bytes(raw)
            os.replace(tmp, dest)
        finally:
            tmp.unlink(missing_ok=True)
        return msg_id

    def query_delivery_status(self, request_id: str) -> str:
        if self.override_status is not None:
            return self.override_status
        return "delivered" if self._msg_path(request_id).is_file() else "not_found"


class GitHubIssueMailProvider:
    """GitHub-native Adoption Review Issue provider with marker-based idempotency and status reconciliation."""

    REVIEW_LABEL = "champion-adoption-review"

    def __init__(
        self,
        repo: str,
        *,
        token: str | None = None,
        assignee: str | None = None,
        transport: httpx.BaseTransport | None = None,
        timeout_seconds: float = 15.0,
    ) -> None:
        cleaned_repo = repo.strip()
        if not cleaned_repo or "/" not in cleaned_repo:
            raise ValueError(f"Invalid GitHub repository '{repo}'")
        self.repo = cleaned_repo
        self.token = token.strip() if isinstance(token, str) and token.strip() else None
        self.assignee = assignee.strip() if isinstance(assignee, str) and assignee.strip() else None
        self.label = self.REVIEW_LABEL
        self.transport = transport
        self.timeout_seconds = float(timeout_seconds)

    @staticmethod
    def marker(request_id: str) -> str:
        return f"<!-- adoption-request-id:{request_id} -->"

    def _issues_url(self) -> str:
        return f"https://api.github.com/repos/{self.repo}/issues"

    def _issue_body(self, message: NotificationMessage) -> str:
        return "\n".join(
            [
                "### Verified Champion Adoption Review",
                "",
                (
                    "**Read-only notification & review surface:** commenting on or closing this issue "
                    "never approves or rejects Champion adoption. Approve or reject only at the protected "
                    "GitHub Environment gate (`champion-adoption-approval`)."
                ),
                "",
                "| Field | Value |",
                "|---|---|",
                f"| **Request ID** | `{message.request_id}` |",
                f"| **Slate ID** | `{message.slate_id}` |",
                f"| **Season / Checkpoint** | `{message.season}` GW{message.checkpoint_gw} |",
                f"| **Candidate** | `{message.candidate_name}` |",
                f"| **Expected Champion** | `{message.expected_champion}` |",
                f"| **Bundle SHA-256** | `{message.bundle_hash}` |",
                f"| **Archive SHA-256** | `{message.archive_sha256 or 'none'}` |",
                f"| **Protected Approval Run** | {message.review_url} |",
                "",
                self.marker(message.request_id),
            ]
        )

    def _lookup_issue_status(self, request_id: str) -> tuple[ProviderDeliveryStatus, int | None]:
        tag = self.marker(request_id)
        headers = _github_api_headers(self.token)
        page = 1
        try:
            with httpx.Client(timeout=self.timeout_seconds, transport=self.transport) as client:
                while True:
                    resp = client.get(
                        self._issues_url(),
                        headers=headers,
                        params={"state": "all", "labels": self.label, "per_page": 100, "page": page},
                    )
                    if resp.status_code != 200:
                        return "unknown", None
                    items = resp.json()
                    if not isinstance(items, list):
                        return "unknown", None
                    for item in items:
                        if not isinstance(item, dict) or "pull_request" in item:
                            continue
                        if tag in str(item.get("body") or "") and isinstance(item.get("number"), int):
                            return "delivered", int(item["number"])
                    if len(items) < 100:
                        return "not_found", None
                    page += 1
        except (httpx.TimeoutException, httpx.RequestError, ValueError):
            return "unknown", None

    def find_issue_number(self, request_id: str) -> int | None:
        status, number = self._lookup_issue_status(request_id)
        if status == "unknown":
            raise UncertainDeliveryAckError(f"Unable to reconcile GitHub Review Issue status for '{request_id}'")
        return number

    def query_delivery_status(self, request_id: str) -> ProviderDeliveryStatus:
        status, _ = self._lookup_issue_status(request_id)
        return status

    def send_adoption_notice(self, message: NotificationMessage) -> str:
        existing = self.find_issue_number(message.request_id)
        if existing is not None:
            return f"gh-issue-{existing}"
        payload: dict[str, Any] = {
            "title": (
                f"[Champion Adoption Review] {message.candidate_name} "
                f"(GW{message.checkpoint_gw}, {message.request_id})"
            ),
            "body": self._issue_body(message),
            "labels": [self.label],
        }
        if self.assignee:
            payload["assignees"] = [self.assignee]
        data = _post_json_delivery(
            self._issues_url(),
            payload,
            _github_api_headers(self.token),
            transport=self.transport,
            timeout_seconds=self.timeout_seconds,
            context="GitHub Issues API",
        )
        number = data.get("number")
        if not isinstance(number, int) or isinstance(number, bool):
            raise UncertainDeliveryAckError("GitHub Issues API response missing integer issue number")
        return f"gh-issue-{number}"

    def update_review_issue(
        self,
        request_id: str,
        *,
        comment: str | None = None,
        close: bool = False,
    ) -> dict[str, Any]:
        issue_num = self.find_issue_number(request_id)
        if issue_num is None:
            return {
                "request_id": request_id,
                "issue_number": None,
                "updated": False,
                "closed": False,
                "commented": False,
            }
        headers = _github_api_headers(self.token)
        cleaned_comment = comment.strip() if isinstance(comment, str) and comment.strip() else None
        issue_url = f"{self._issues_url()}/{issue_num}"
        with httpx.Client(timeout=self.timeout_seconds, transport=self.transport) as client:
            if cleaned_comment is not None:
                c_resp = client.post(f"{issue_url}/comments", json={"body": cleaned_comment}, headers=headers)
                if not 200 <= c_resp.status_code < 300:
                    raise RuntimeError(
                        f"Failed to comment on Adoption Review Issue #{issue_num} (HTTP {c_resp.status_code})"
                    )
            if close:
                p_resp = client.patch(issue_url, json={"state": "closed"}, headers=headers)
                if not 200 <= p_resp.status_code < 300:
                    raise RuntimeError(
                        f"Failed to close Adoption Review Issue #{issue_num} (HTTP {p_resp.status_code})"
                    )
        return {
            "request_id": request_id,
            "issue_number": issue_num,
            "updated": True,
            "closed": bool(close),
            "commented": cleaned_comment is not None,
        }


def _enqueue_pass_command(args: argparse.Namespace) -> int:
    manager = AdoptionRequestManager(args.evidence_root)
    req = manager.enqueue_pass(
        slate_id=str(args.slate_id),
        season=str(args.season),
        checkpoint_gw=int(args.checkpoint_gw),
        candidate_name=str(args.candidate_name),
        expected_champion=str(args.expected_champion),
        bundle_hash=str(args.bundle_hash),
        archive_sha256=args.archive_sha256,
        snapshot_archive_path=args.snapshot_archive,
        bundle_path=args.bundle_path,
        protocol_hash=str(args.protocol_hash or ""),
        serving_model_closure_hash=args.serving_model_closure_hash,
        net_delta=float(args.net_delta),
        podium_index=int(args.podium_index),
        expires_at_utc=args.expires_at_utc,
        actor=str(args.actor),
    )
    print(json.dumps(req.to_dict(), sort_keys=True))
    return 0


def _dispatch_or_reconcile_notice_command(args: argparse.Namespace) -> int:
    root = Path(args.evidence_root).resolve()
    manager = AdoptionRequestManager(root)
    req = manager.get_request(str(args.request_id))
    if req is None:
        raise ValueError(f"Adoption request '{args.request_id}' not found")
    provider: FileOutboxMailProvider | HttpWebhookMailProvider | GitHubIssueMailProvider
    webhook_url = (getattr(args, "webhook_url", None) or os.environ.get("MAIL_PROVIDER_WEBHOOK_URL") or "").strip()
    github_repo = (getattr(args, "github_repo", None) or "").strip()
    if args.outbox_dir:
        provider = FileOutboxMailProvider(
            Path(args.outbox_dir).resolve(),
            override_status=getattr(args, "provider_status", None),
        )
    elif webhook_url:
        provider = HttpWebhookMailProvider(
            webhook_url,
            api_key=os.environ.get("MAIL_PROVIDER_API_KEY"),
            status_url=os.environ.get("MAIL_PROVIDER_STATUS_URL"),
        )
    elif github_repo:
        assignee = (getattr(args, "assignee", None) or "").strip() or None
        provider = GitHubIssueMailProvider(
            github_repo,
            token=_retrieve_github_token_in_memory(),
            assignee=assignee,
        )
    else:
        raise ValueError(
            "Controlled mail provider not configured: set MAIL_PROVIDER_WEBHOOK_URL, --github-repo, or --outbox-dir explicitly"
        )
    dispatcher = NotificationDispatcher(root, provider=provider)
    rec = dispatcher.reconcile_and_dispatch(
        req,
        review_url=str(args.review_url),
        recipient=str(args.recipient),
    )
    print(json.dumps(rec.to_dict(), sort_keys=True))
    return 0


def _update_review_issue_command(args: argparse.Namespace) -> int:
    request_id = str(args.request_id)
    comment = args.comment
    close = bool(args.close)
    if args.close_if_terminal:
        if not args.evidence_root:
            raise ValueError("--close-if-terminal requires --evidence-root")
        req = AdoptionRequestManager(args.evidence_root).get_request(request_id)
        if req is None or req.status not in TERMINAL_REQUEST_STATUSES:
            print(json.dumps({"request_id": request_id, "updated": False, "closed": False, "reason": "not_terminal"}, sort_keys=True))
            return 0
        close = True
        if not comment:
            detail = f": {req.reason}" if req.reason else ""
            comment = f"Adoption request closed ({req.status}){detail}."
    provider = GitHubIssueMailProvider(
        str(args.repo),
        token=_retrieve_github_token_in_memory(),
    )
    result = provider.update_review_issue(
        request_id,
        comment=comment,
        close=close,
    )
    print(json.dumps(result, sort_keys=True))
    return 0


def _record_approval_command(args: argparse.Namespace) -> int:
    root = Path(args.evidence_root).resolve()
    manager = AdoptionRequestManager(root)
    approved = manager.record_approval(
        str(args.request_id),
        actor=str(args.actor),
        approval_ref=str(args.approval_ref),
        approved_pr_head_sha=args.approved_pr_head_sha,
        reason=str(args.reason),
    )
    print(json.dumps(approved.to_dict(), sort_keys=True))
    return 0


def _sync_evidence_worktree(source_dir: Path, worktree_dir: Path) -> None:
    """Copy evidence files into `worktree_dir` and prune released `reservation.json` without touching `.git`."""
    src = Path(source_dir).resolve()
    dst = Path(worktree_dir).resolve()
    if src.is_dir():
        for item in sorted(src.rglob("*")):
            if item.is_symlink():
                raise ValueError(f"Symlink forbidden in evidence sync: {item}")
            rel = item.relative_to(src)
            if rel.parts and rel.parts[0] == ".git":
                continue
            target = dst / rel
            if item.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            elif item.is_file():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, target)
    src_res = src / "reservation.json"
    dst_res = dst / "reservation.json"
    if not src_res.is_file() and dst_res.is_file():
        dst_res.unlink(missing_ok=True)


def _sync_evidence_worktree_command(args: argparse.Namespace) -> int:
    _sync_evidence_worktree(Path(args.source_dir), Path(args.worktree_dir))
    print(json.dumps({"synced": True, "source": str(args.source_dir), "worktree": str(args.worktree_dir)}, sort_keys=True))
    return 0


def _record_rejection_command(args: argparse.Namespace) -> int:
    root = Path(args.evidence_root).resolve()
    manager = AdoptionRequestManager(root)
    rejected = manager.reject_request(
        str(args.request_id),
        actor=str(args.actor),
        reason=str(args.reason),
    )
    next_active = None
    if args.advance_queue:
        next_active = manager.advance_queue(
            rejected.slate_id,
            selection_path=args.selection_path,
            actor=str(args.actor),
        )
    print(
        json.dumps(
            {
                "rejected": rejected.to_dict(),
                "next_active": next_active.to_dict() if next_active is not None else None,
            },
            sort_keys=True,
        )
    )
    return 0


def _prepare_adoption_pr_command(args: argparse.Namespace) -> int:
    root = Path(args.evidence_root).resolve()
    manager = AdoptionRequestManager(root)
    req = manager.get_request(str(args.request_id))
    if req is None:
        raise ValueError(f"Adoption request '{args.request_id}' not found")
    if req.status not in ("pending_approval", "approved"):
        raise ValueError(f"Cannot prepare adoption PR for request '{req.request_id}' in status '{req.status}'")
    actor = str(args.actor).strip()
    approval_ref = str(args.approval_ref).strip()
    if not actor or not approval_ref:
        raise ValueError("Approval requires non-empty actor and approval_ref")
    manager.assert_not_expired(req, actor=actor)

    bundle_arg: Path | str
    if req.snapshot_archive_path is not None:
        snap = Path(req.snapshot_archive_path)
        bundle_arg = snap if snap.is_absolute() else (root / snap).resolve()
    elif req.bundle_path is not None:
        bp = Path(req.bundle_path)
        bundle_arg = bp if bp.is_absolute() else (root / bp).resolve()
    else:
        raise ValueError(f"Request '{req.request_id}' lacks snapshot_archive_path and bundle_path")

    reg_path = root / "registry.jsonl"
    excl_path = root / "exclusions.jsonl"
    # Verify evidence and mutate PR config BEFORE persisting status='approved' so fail-closed rejections never leave an approved ledger entry.
    updated = adopt_champion(
        bundle_arg,
        config_path=args.selection_path,
        approval_ref=approval_ref,
        expected_current_champion=req.expected_champion,
        candidate_name=req.candidate_name,
        approved_bundle_hash=req.bundle_hash,
        snapshot_archive_path=bundle_arg if req.snapshot_archive_path is not None else None,
        expected_archive_sha256=req.archive_sha256,
        canonical_registry_path=reg_path if reg_path.is_file() else None,
        canonical_exclusions_path=excl_path if excl_path.is_file() else None,
        request_id=req.request_id,
        slate_id=req.slate_id,
        approved_commit_sha=args.approved_commit_sha,
    )
    approved = manager.record_approval(
        req.request_id,
        actor=actor,
        approval_ref=approval_ref,
        approved_pr_head_sha=args.approved_commit_sha,
    )
    print(
        json.dumps(
            {
                "request_id": approved.request_id,
                "slate_id": approved.slate_id,
                "champion": updated.champion,
                "candidates": list(updated.candidates),
                "podium_sealed": updated.podium_sealed,
                "approval_ref": approved.approval_ref,
            },
            sort_keys=True,
        )
    )
    return 0


def _verify_adoption_pr_command(args: argparse.Namespace) -> int:
    root = Path(args.evidence_root).resolve()
    manager = AdoptionRequestManager(root)
    req = manager.get_request(str(args.request_id))
    if req is None:
        raise ValueError(f"Adoption request '{args.request_id}' not found")
    if req.slate_id != str(args.slate_id):
        raise ValueError(f"Request '{req.request_id}' slate_id mismatch: expected '{req.slate_id}', got '{args.slate_id}'")
    manager.assert_not_expired(req)
    if req.status not in ("pending_approval", "approved"):
        raise ValueError(f"Request '{req.request_id}' is not open for PR checks (status='{req.status}')")
    if args.head_sha and req.approved_pr_head_sha and req.approved_pr_head_sha != str(args.head_sha):
        raise ValueError(
            f"PR head SHA mismatch: approved '{req.approved_pr_head_sha}', got '{args.head_sha}'"
        )

    if args.changed_file:
        changed = set(args.changed_file)
        if changed != AUTHORIZED_ADOPTION_DIFF_FILES:
            raise ValueError(f"Adoption PR contains unauthorized file diff: {sorted(changed)}")

    if args.base_selection_path is not None:
        base_sel = load_model_selection(Path(args.base_selection_path).resolve())
        if (
            base_sel.champion != req.expected_champion
            or not base_sel.podium_sealed
            or req.candidate_name not in base_sel.candidates
        ):
            raise ValueError(
                f"Base protected main selection does not match sealed slate for '{req.request_id}'"
            )

    sel_path = Path(args.selection_path).resolve()
    receipt_path = sel_path.with_suffix(".adoption.json")
    if not sel_path.is_file() or not receipt_path.is_file():
        raise ValueError("Adoption PR requires both model_selection.json and model_selection.adoption.json")

    sel = load_model_selection(sel_path)
    receipt = json.loads(receipt_path.read_bytes())
    if sel.champion != req.candidate_name:
        raise ValueError(f"PR selection Champion '{sel.champion}' differs from request candidate '{req.candidate_name}'")
    if sel.podium_sealed or sel.provisional_active is not None or sel.podium_frozen_season is not None:
        raise ValueError("Adoption PR must close the frozen slate (podium_sealed=False, provisional_active=None)")
    if (
        receipt.get("request_id") != req.request_id
        or receipt.get("slate_id") != req.slate_id
        or receipt.get("bundle_hash") != req.bundle_hash
        or receipt.get("candidate_name") != req.candidate_name
        or receipt.get("former_champion") != req.expected_champion
    ):
        raise ValueError("Adoption receipt fields do not match registered adoption request")

    excl_path = root / "exclusions.jsonl"
    if excl_path.is_file():
        excl = ExclusionLedger(excl_path)
        if excl.is_candidate_excluded(req.candidate_name, slate_id=req.slate_id, season=req.season):
            raise ValueError(f"Candidate '{req.candidate_name}' is excluded in ExclusionLedger")

    manager.verify_request_evidence(req)

    print(
        json.dumps(
            {
                "verified": True,
                "request_id": req.request_id,
                "slate_id": req.slate_id,
                "candidate_name": req.candidate_name,
                "former_champion": req.expected_champion,
                "bundle_hash": req.bundle_hash,
            },
            sort_keys=True,
        )
    )
    return 0


def _fetch_and_verify_live_pr_checks(
    *,
    repo: str,
    pr_number: int,
    approved_pr_head_sha: str,
    pr_head_sha: str,
    token: str | None,
    transport: httpx.BaseTransport | None = None,
) -> list[str]:
    """Query GitHub PR state, files, auto_merge flag, and `verify-adoption-pr` check run."""
    base = f"https://api.github.com/repos/{repo}"
    headers = _github_api_headers(token)
    with httpx.Client(timeout=20.0, transport=transport) as client:
        pr_resp = client.get(f"{base}/pulls/{pr_number}", headers=headers)
        if pr_resp.status_code != 200:
            raise ValueError(f"Failed to query PR #{pr_number} (HTTP {pr_resp.status_code})")
        pr = pr_resp.json()
        if pr.get("state") != "open":
            raise ValueError(f"PR #{pr_number} is not open (state={pr.get('state')})")
        if pr.get("auto_merge") is not None:
            raise ValueError(f"Independent auto-merge is enabled on PR #{pr_number}")
        head_sha = str((pr.get("head") or {}).get("sha") or "")
        if head_sha != approved_pr_head_sha or head_sha != pr_head_sha:
            raise ValueError(
                f"Live PR #{pr_number} head SHA '{head_sha}' mismatches approved '{approved_pr_head_sha}'"
            )

        files_resp = client.get(f"{base}/pulls/{pr_number}/files", headers=headers)
        if files_resp.status_code != 200:
            raise ValueError(f"Failed to query PR #{pr_number} files (HTTP {files_resp.status_code})")
        changed_files = [str(f["filename"]) for f in files_resp.json() if isinstance(f, Mapping) and "filename" in f]
        if set(changed_files) != AUTHORIZED_ADOPTION_DIFF_FILES:
            raise ValueError(f"Live PR #{pr_number} contains unauthorized diff: {sorted(changed_files)}")

        checks_resp = client.get(f"{base}/commits/{head_sha}/check-runs", headers=headers)
        if checks_resp.status_code != 200:
            raise ValueError(f"Failed to query check-runs for {head_sha} (HTTP {checks_resp.status_code})")
        runs = [r for r in checks_resp.json().get("check_runs", ()) if isinstance(r, Mapping)]
        matching = [r for r in runs if str(r.get("name", "")) == "verify-adoption-pr"]
        if not any(r.get("status") == "completed" and r.get("conclusion") == "success" for r in matching):
            raise ValueError(f"Required check 'verify-adoption-pr' is not green on PR #{pr_number} ({head_sha})")
    return changed_files


def _execute_github_pr_merge(
    *,
    repo: str,
    pr_number: int,
    approved_pr_head_sha: str,
    token: str | None,
    transport: httpx.BaseTransport | None = None,
) -> dict[str, Any]:
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/merge"
    headers = _github_api_headers(token)
    payload = {"sha": approved_pr_head_sha, "merge_method": "squash"}
    try:
        with httpx.Client(timeout=30.0, transport=transport) as client:
            resp = client.put(url, json=payload, headers=headers)
    except (httpx.TimeoutException, httpx.RequestError) as exc:
        raise MergeInterruptedError(f"GitHub PR #{pr_number} merge request interrupted: {exc}") from exc
    if resp.status_code != 200:
        raise MergeInterruptedError(f"GitHub PR #{pr_number} merge failed (HTTP {resp.status_code})")
    data = resp.json()
    if not data.get("merged"):
        raise MergeInterruptedError(f"GitHub PR #{pr_number} merge response returned merged=False")
    return {
        "merge_commit_sha": data.get("sha"),
        "pr_number": pr_number,
    }


def _push_worktree_reservation_state(source_dir: Path, worktree_dir: Path, message: str) -> None:
    _sync_evidence_worktree(source_dir, worktree_dir)
    status_proc = subprocess.run(
        ["git", "-C", str(worktree_dir), "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=True,
    )
    if not status_proc.stdout.strip():
        return
    subprocess.run(["git", "-C", str(worktree_dir), "add", "-A"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(worktree_dir),
            "-c",
            "user.name=github-actions[bot]",
            "-c",
            "user.email=41898282+github-actions[bot]@users.noreply.github.com",
            "commit",
            "-m",
            message,
        ],
        check=True,
    )
    subprocess.run(["git", "-C", str(worktree_dir), "push", "origin", "HEAD:validation-evidence"], check=True)


def _execute_protected_merge_command(args: argparse.Namespace) -> int:
    root = Path(args.evidence_root).resolve()
    coordinator = SharedReservationCoordinator(root)
    changed_files: tuple[str, ...] = (
        tuple(args.changed_file) if args.changed_file else tuple(sorted(AUTHORIZED_ADOPTION_DIFF_FILES))
    )
    checks_green = bool(args.checks_green)
    existing_req = coordinator.request_manager.get_request(str(args.request_id))
    already_done = bool(
        existing_req is not None
        and existing_req.slate_id == str(args.slate_id)
        and existing_req.status == "adopted"
        and coordinator.current_reservation() is None
    )
    need_gh_token = (not already_done) and bool(args.require_live_checks or args.merge_via_github_api)
    token = _retrieve_github_token_in_memory() if need_gh_token else None

    if already_done:
        checks_green = True
    elif args.require_live_checks:
        if not args.repo or args.pr_number is None:
            raise ValueError("--require-live-checks requires --repo and --pr-number")
        live_files = _fetch_and_verify_live_pr_checks(
            repo=str(args.repo),
            pr_number=int(args.pr_number),
            approved_pr_head_sha=str(args.approved_pr_head_sha),
            pr_head_sha=str(args.pr_head_sha),
            token=token,
        )
        changed_files = tuple(live_files)
        checks_green = True

    merge_executor = None
    if not already_done and args.merge_via_github_api:
        if not args.repo or args.pr_number is None:
            raise ValueError("--merge-via-github-api requires --repo and --pr-number")

        def _do_api_merge() -> dict[str, Any]:
            return _execute_github_pr_merge(
                repo=str(args.repo),
                pr_number=int(args.pr_number),
                approved_pr_head_sha=str(args.approved_pr_head_sha),
                token=token,
            )

        merge_executor = _do_api_merge

    persist_hook = None
    if args.worktree_dir is not None:
        wt_dir = Path(args.worktree_dir).resolve()

        def _sync_res(rec: ReservationRecord | None) -> None:
            label = f"sync reservation ({rec.merge_state})" if rec is not None else "release reservation"
            _push_worktree_reservation_state(root, wt_dir, f"adoption: {args.request_id} {label}")

        persist_hook = _sync_res

    result = coordinator.execute_reserved_adoption_merge(
        request_id=str(args.request_id),
        slate_id=str(args.slate_id),
        approval_ref=str(args.approval_ref),
        approved_pr_head_sha=str(args.approved_pr_head_sha),
        pr_head_sha=str(args.pr_head_sha),
        changed_files=changed_files,
        checks_green=checks_green,
        auto_merge_enabled=bool(args.auto_merge_enabled),
        main_selection_path=args.main_selection_path,
        holder=str(args.holder),
        merge_executor=merge_executor,
        persist_reservation_hook=persist_hook,
    )
    print(json.dumps(result, sort_keys=True))
    return 0


def _reconcile_merge_command(args: argparse.Namespace) -> int:
    root = Path(args.evidence_root).resolve()
    coordinator = SharedReservationCoordinator(root)
    remote_sel: Mapping[str, Any] | None = None
    remote_rec: Mapping[str, Any] | None = None
    if args.remote_main_ref:
        ref = str(args.remote_main_ref)
        sel_proc = subprocess.run(
            ["git", "show", f"{ref}:config/model_selection.json"],
            capture_output=True,
            text=True,
            check=False,
        )
        rec_proc = subprocess.run(
            ["git", "show", f"{ref}:config/model_selection.adoption.json"],
            capture_output=True,
            text=True,
            check=False,
        )
        if sel_proc.returncode == 0 and rec_proc.returncode == 0:
            remote_sel = json.loads(sel_proc.stdout)
            remote_rec = json.loads(rec_proc.stdout)
    result = coordinator.reconcile_unknown_merge(
        main_selection_path=args.main_selection_path,
        remote_main_selection=remote_sel,
        remote_main_receipt=remote_rec,
        actor=str(args.actor),
    )
    print(json.dumps(result, sort_keys=True))
    return 0


def _retrieve_github_token_in_memory() -> str | None:
    """Retrieve GitHub credential in-memory via `git credential fill` without ever logging or persisting it."""
    env_tok = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if env_tok and env_tok.strip():
        return env_tok.strip()
    try:
        proc = subprocess.run(
            ["git", "credential", "fill"],
            input="protocol=https\nhost=github.com\n\n",
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if proc.returncode != 0:
            return None
        for line in proc.stdout.splitlines():
            if line.startswith("password="):
                val = line.split("=", 1)[1].strip()
                return val or None
    except Exception:
        return None
    return None


def _github_get_json(url: str, token: str | None) -> tuple[int, dict[str, Any] | list[Any] | None]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "fpl-jubilee-ascent-preflight/1.0",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url, headers=headers)
        if not 200 <= resp.status_code < 300:
            return int(resp.status_code), None
        return int(resp.status_code), (resp.json() if resp.content else {})
    except Exception:
        return 0, None


def _query_live_github_snapshot(repo: str) -> dict[str, Any]:
    token = _retrieve_github_token_in_memory()
    base = f"https://api.github.com/repos/{repo}"

    repo_code, repo_data = _github_get_json(base, token)
    bp_code, bp_data = _github_get_json(f"{base}/branches/main/protection", token)
    rules_code, rules_data = _github_get_json(f"{base}/rules/branches/main", token)
    env_code, env_data = _github_get_json(f"{base}/environments/champion-adoption-approval", token)
    var_code, var_data = _github_get_json(f"{base}/actions/variables/CHAMPION_ADOPTION_LIVE_ENABLED", token)
    vars_code, vars_list_data = _github_get_json(f"{base}/actions/variables", token)
    secrets_code, secrets_data = _github_get_json(f"{base}/actions/secrets", token)
    ev_code, _ = _github_get_json(f"{base}/branches/validation-evidence", token)
    rel_code, _ = _github_get_json(f"{base}/releases?per_page=1", token)

    req_checks = bp_data.get("required_status_checks", {}) if isinstance(bp_data, dict) else {}
    strict_checks = bool(req_checks.get("strict"))
    contexts = list(req_checks.get("contexts", ()))
    bp_enabled = bp_code == 200
    if not bp_enabled and rules_code == 200 and isinstance(rules_data, list):
        for rule in rules_data:
            if isinstance(rule, dict) and rule.get("type") == "required_status_checks":
                bp_enabled = True
                params = rule.get("parameters", {})
                if isinstance(params, dict):
                    strict_checks = strict_checks or bool(params.get("strict_required_status_checks_policy"))
                    for chk in params.get("required_status_checks", ()):
                        if isinstance(chk, dict) and chk.get("context"):
                            contexts.append(str(chk["context"]))
    enforce_admins = (
        bool(bp_data.get("enforce_admins", {}).get("enabled"))
        if isinstance(bp_data, dict) and isinstance(bp_data.get("enforce_admins"), dict)
        else False
    )
    protection_rules = env_data.get("protection_rules", []) if isinstance(env_data, dict) else []
    reviewers = [r for r in protection_rules if isinstance(r, dict) and r.get("type") == "required_reviewers"]

    secret_names = (
        {str(s["name"]) for s in secrets_data.get("secrets", ()) if isinstance(s, dict) and s.get("name")}
        if secrets_code == 200 and isinstance(secrets_data, dict)
        else set()
    )
    vars_map = (
        {
            str(v["name"]): str(v.get("value", ""))
            for v in vars_list_data.get("variables", ())
            if isinstance(v, dict) and v.get("name")
        }
        if vars_code == 200 and isinstance(vars_list_data, dict)
        else {}
    )
    live_var_val = str(var_data.get("value", "false")).lower() if (var_code == 200 and isinstance(var_data, dict)) else "false"
    allow_auto_merge = bool(repo_data.get("allow_auto_merge", False)) if isinstance(repo_data, dict) else False

    return {
        "api_reachable": repo_code == 200,
        "branch_protection": {
            "http_status": bp_code if bp_code == 200 else rules_code,
            "enabled": bp_enabled,
            "required_status_checks": {
                "strict": strict_checks,
                "contexts": contexts,
            },
            "enforce_admins": enforce_admins,
        },
        "protected_environment": {
            "http_status": env_code,
            "name": "champion-adoption-approval",
            "exists": env_code == 200,
            "required_reviewers": reviewers,
        },
        "repo_settings": {
            "http_status": repo_code,
            "allow_auto_merge": allow_auto_merge,
            "github_app_configured": {"CHAMPION_ADOPTION_APP_ID", "CHAMPION_ADOPTION_APP_PRIVATE_KEY"}.issubset(
                secret_names
            ),
        },
        "validation_evidence_branch": {
            "branch_http_status": ev_code,
            "exists": ev_code == 200,
            "releases_accessible": rel_code == 200,
        },
        "mail_provider": {
            "configured": bool(vars_map.get("MAIL_PROVIDER_ENDPOINT") or "MAIL_PROVIDER_WEBHOOK_URL" in secret_names),
            "github_issues_enabled": bool(repo_data.get("has_issues", False)) if isinstance(repo_data, dict) else False,
        },
        "variables": {
            "CHAMPION_ADOPTION_LIVE_ENABLED": live_var_val,
        },
    }


def run_production_preflight(
    *,
    repo: str = "JubileeZ/fpl-jubilee-ascent",
    offline_snapshot_path: Path | None = None,
    project_root: Path | None = None,
) -> dict[str, Any]:
    """Run strictly read-only production parity preflight across all 10 #197 live rollout gates."""
    root = (project_root or PROJECT_ROOT).resolve()
    if offline_snapshot_path is not None:
        gh = json.loads(Path(offline_snapshot_path).read_bytes())
    else:
        gh = _query_live_github_snapshot(repo)

    gates: dict[str, dict[str, Any]] = {}

    # 1. branch_protection_main
    bp = gh.get("branch_protection", {})
    bp_checks = bp.get("required_status_checks", {}) if isinstance(bp.get("required_status_checks"), dict) else {}
    bp_passed = bool(
        bp.get("enabled")
        and bp_checks.get("strict") is True
        and "verify-adoption-pr" in (bp_checks.get("contexts") or ())
    )
    gates["branch_protection_main"] = {
        "passed": bp_passed,
        "status": "pass" if bp_passed else "blocked",
        "blocker": None
        if bp_passed
        else "Protected main branch lacks strict up-to-date required status check 'verify-adoption-pr'",
        "recovery_action": "Enable branch protection on main requiring strict up-to-date status check 'verify-adoption-pr'.",
        "details": bp,
    }

    # 2. protected_environment
    pe = gh.get("protected_environment", {})
    pe_passed = bool(pe.get("exists") and pe.get("required_reviewers"))
    gates["protected_environment"] = {
        "passed": pe_passed,
        "status": "pass" if pe_passed else "blocked",
        "blocker": None
        if pe_passed
        else "Protected GitHub Environment 'champion-adoption-approval' missing or has no required human reviewers",
        "recovery_action": "Create 'champion-adoption-approval' GitHub Environment and assign required human reviewer(s).",
        "details": pe,
    }

    # 3. github_app_and_no_bypass
    rs = gh.get("repo_settings", {})
    app_passed = bool(
        rs.get("github_app_configured") is True
        and rs.get("allow_auto_merge") is False
        and bp.get("enforce_admins") is True
    )
    gates["github_app_and_no_bypass"] = {
        "passed": app_passed,
        "status": "pass" if app_passed else "blocked",
        "blocker": None
        if app_passed
        else "Dedicated GitHub App merger not configured, independent auto-merge enabled, or admin bypass permitted",
        "recovery_action": "Configure dedicated Champion adoption GitHub App, disable repository allow_auto_merge, and enable enforce_admins on main.",
        "details": {"repo_settings": rs, "enforce_admins": bp.get("enforce_admins")},
    }

    # 4. shared_reservation_wiring
    writer_wfs = (
        ".github/workflows/validation-collector.yml",
        ".github/workflows/champion-adoption-request.yml",
        ".github/workflows/champion-adoption-merge.yml",
    )
    all_wfs = (*writer_wfs, ".github/workflows/champion-adoption-pr-checks.yml")
    wf_present = all((root / rel).is_file() for rel in all_wfs)
    shared_concurrency_ok = wf_present and all(
        "group: validation-evidence" in (root / rel).read_text(encoding="utf-8")
        for rel in writer_wfs
    )
    no_direct_push_ok = wf_present and (
        "git push origin HEAD:main" not in (root / ".github/workflows/champion-adoption-merge.yml").read_text(encoding="utf-8")
    )
    prod_ev_path = root / "commands" / "produce_validation_evidence.py"
    collector_wired = prod_ev_path.is_file() and (
        "record_exclusion_under_reservation" in prod_ev_path.read_text(encoding="utf-8")
    )
    coord_wired = hasattr(SharedReservationCoordinator, "record_exclusion_under_reservation") and hasattr(
        SharedReservationCoordinator, "execute_reserved_adoption_merge"
    )
    wiring_passed = wf_present and coord_wired and shared_concurrency_ok and no_direct_push_ok and collector_wired
    gates["shared_reservation_wiring"] = {
        "passed": wiring_passed,
        "status": "pass" if wiring_passed else "blocked",
        "blocker": None if wiring_passed else "SharedReservationCoordinator, shared workflow concurrency, or PR-only merge wiring incomplete",
        "recovery_action": "Ensure all evidence workflows share group validation-evidence, collector reserves exclusions, and merge uses GitHub PR merge API.",
        "details": {
            "workflows_present": wf_present,
            "shared_concurrency_group": shared_concurrency_ok,
            "no_direct_main_push": no_direct_push_ok,
            "collector_exclusion_reservation": collector_wired,
            "coordinator_wired": coord_wired,
        },
    }

    # 5. immutable_evidence_and_releases
    ev = gh.get("validation_evidence_branch", {})
    ev_passed = bool(ev.get("exists") and ev.get("releases_accessible"))
    gates["immutable_evidence_and_releases"] = {
        "passed": ev_passed,
        "status": "pass" if ev_passed else "blocked",
        "blocker": None
        if ev_passed
        else "Orphan branch 'validation-evidence' or GitHub Releases endpoint not initialized on remote",
        "recovery_action": "Initialize 'validation-evidence' branch and verify release publishing permissions.",
        "details": ev,
    }

    # 6. mail_delivery_and_reconciliation
    mp = gh.get("mail_provider", {}) if isinstance(gh.get("mail_provider"), dict) else {}
    req_wf = root / ".github" / "workflows" / "champion-adoption-request.yml"
    merge_wf = root / ".github" / "workflows" / "champion-adoption-merge.yml"
    req_wf_text = req_wf.read_text(encoding="utf-8") if req_wf.is_file() else ""
    merge_wf_text = merge_wf.read_text(encoding="utf-8") if merge_wf.is_file() else ""
    review_issue_wf_wired = (
        "issues: write" in req_wf_text
        and "--github-repo" in req_wf_text
        and "issues: write" in merge_wf_text
        and "update-review-issue" in merge_wf_text
        and hasattr(GitHubIssueMailProvider, "query_delivery_status")
    )
    webhook_configured = bool(mp.get("configured"))
    github_issues_enabled = bool(mp.get("github_issues_enabled"))
    github_issue_ready = bool(github_issues_enabled and review_issue_wf_wired)
    if github_issue_ready and webhook_configured:
        notice_mode = "github_review_issue+webhook"
    elif github_issue_ready:
        notice_mode = "github_review_issue"
    elif webhook_configured:
        notice_mode = "webhook"
    else:
        notice_mode = "unconfigured"
    mail_passed = bool((github_issue_ready or webhook_configured) and hasattr(NotificationDispatcher, "reconcile_and_dispatch"))
    gates["mail_delivery_and_reconciliation"] = {
        "passed": mail_passed,
        "status": "pass" if mail_passed else "blocked",
        "blocker": None if mail_passed else "Neither GitHub Review Issues nor webhook mail provider configured",
        "recovery_action": "Enable GitHub Issues with champion-adoption-request.yml Review Issue wiring (or set MAIL_PROVIDER_WEBHOOK_URL).",
        "details": {**mp, "review_issue_workflow_wired": review_issue_wf_wired, "mode": notice_mode},
    }

    # 7. live_rollout_disabled
    live_var = str(gh.get("variables", {}).get("CHAMPION_ADOPTION_LIVE_ENABLED", "false")).lower()
    live_disabled = live_var != "true"
    gates["live_rollout_disabled"] = {
        "passed": live_disabled,
        "status": "pass" if live_disabled else "blocked",
        "blocker": None if live_disabled else "CHAMPION_ADOPTION_LIVE_ENABLED is prematurely set to 'true'",
        "recovery_action": "Keep CHAMPION_ADOPTION_LIVE_ENABLED unset or 'false' until all live activation gates pass.",
        "details": {"CHAMPION_ADOPTION_LIVE_ENABLED": live_var},
    }

    # 8. certified_protocol
    cert_dir = root / "docs" / "research" / "sparse-confirmation-certification"
    cert_path = cert_dir / "certification_result.json"
    cert_ver = verify_certification_artifacts(
        cert_dir,
        expected_digest=CERTIFICATION_DIGEST_EXPECTED,
        project_root=root,
        check_evaluator_revisions=True,
    )
    cert_passed = bool(cert_ver["passed"])
    cert_details: dict[str, Any] = {
        "path": cert_path.relative_to(root).as_posix(),
        "exists": cert_path.is_file(),
        "certified": cert_ver.get("certified"),
        "certified_mode": cert_ver.get("certified_mode"),
        "certification_digest": cert_ver.get("certification_digest"),
        "expected_certification_digest": CERTIFICATION_DIGEST_EXPECTED,
        "statistical_protocol_hash": cert_ver.get("statistical_protocol_hash"),
        "manifest_digest_match": cert_ver.get("manifest_digest_match"),
        "canonical_digest_match": cert_ver.get("canonical_digest_match"),
        "evaluator_revisions_match": cert_ver.get("evaluator_revisions_match"),
        "drifted_files": cert_ver.get("drifted_files", []),
        "errors": cert_ver.get("errors", []),
    }
    gates["certified_protocol"] = {
        "passed": cert_passed,
        "status": "pass" if cert_passed else "blocked",
        "blocker": None
        if cert_passed
        else "; ".join(cert_ver.get("errors") or ["Sparse confirmation protocol certification failed"]),
        "recovery_action": (
            "Run `uv run python -m commands.certify_sparse_confirmation`, update CERTIFICATION_DIGEST_EXPECTED, "
            "and commit verified certification artifacts."
        ),
        "details": cert_details,
    }

    # 9. admissible_historical_passing_fixture
    inv = build_pilot_fixture_inventory(project_root=root, verify_fixture=False)
    has_fixture = bool(inv.get("has_admissible_historical_gw15_passing_fixture"))
    gates["admissible_historical_passing_fixture"] = {
        "passed": has_fixture,
        "status": "pass" if has_fixture else "blocked",
        "blocker": None
        if has_fixture
        else "No real historical >=15-GW empirically admitted passing fixture exists (has_admissible_historical_gw15_passing_fixture=False)",
        "recovery_action": "Hydrate >=15-GW pre-deadline empirical mirror prefix and qualifying finalist pair without relaxing empirical_admission.py.",
        "details": {
            "has_admissible_historical_gw15_passing_fixture": has_fixture,
            "missing_prerequisites": inv.get("missing_prerequisites", []),
        },
    }

    # 10. sealed_slate_and_operator_signoff
    sel = load_model_selection(root / "config" / "model_selection.json")
    lifecycle_file = root / "config" / "season_lifecycle.json"
    active_season = (
        load_season_lifecycle(lifecycle_file) if lifecycle_file.is_file() else load_season_lifecycle()
    ).season_for_role("active_validation")
    proto_hash_ok = isinstance(sel.frozen_protocol_hash, str) and bool(
        re.fullmatch(r"[0-9a-f]{64}", sel.frozen_protocol_hash)
    )
    cert_digest_matches = sel.frozen_certification_digest == CERTIFICATION_DIGEST_EXPECTED
    slate_shape_ok = (
        1 <= len(sel.candidates) <= 2
        and sel.champion not in sel.candidates
        and len(set(sel.candidates)) == len(sel.candidates)
    )
    season_matches = sel.podium_frozen_season == active_season
    slate_passed = bool(
        sel.podium_sealed
        and slate_shape_ok
        and season_matches
        and proto_hash_ok
        and cert_digest_matches
    )
    gates["sealed_slate_and_operator_signoff"] = {
        "passed": slate_passed,
        "status": "pass" if slate_passed else "blocked",
        "blocker": None
        if slate_passed
        else (
            f"Comparison Slate not sealed and bound for active validation {active_season!r} "
            f"(champion={sel.champion!r}, candidates={list(sel.candidates)!r}, "
            f"provisional_active={sel.provisional_active!r}, podium_sealed={sel.podium_sealed}, "
            f"podium_frozen_season={sel.podium_frozen_season!r}, "
            f"certification_digest_matches={cert_digest_matches}, protocol_hash_ok={proto_hash_ok}) "
            "and operator sign-off pending"
        ),
        "recovery_action": (
            "Seal Comparison Slate (1..2 candidates distinct from Champion) for active_validation season, "
            "bind frozen_protocol_hash and CERTIFICATION_DIGEST_EXPECTED, and record named operator sign-off."
        ),
        "details": {
            "champion": sel.champion,
            "candidates": list(sel.candidates),
            "provisional_active": sel.provisional_active,
            "podium_frozen_season": sel.podium_frozen_season,
            "active_validation_season": active_season,
            "podium_sealed": sel.podium_sealed,
            "frozen_protocol_hash": sel.frozen_protocol_hash,
            "frozen_certification_digest": sel.frozen_certification_digest,
            "certification_digest_matches": cert_digest_matches,
        },
    }

    return {
        "repo": repo,
        "read_only": True,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "live_activation_ready": all(g["passed"] for g in gates.values()),
        "gates": gates,
    }


def _production_preflight_command(args: argparse.Namespace) -> int:
    report = run_production_preflight(
        repo=str(args.repo),
        offline_snapshot_path=args.offline_snapshot,
    )
    formatted = json.dumps(report, indent=2, sort_keys=True)
    if args.output is not None:
        out_path = Path(args.output).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(formatted + "\n", encoding="utf-8")
    print(formatted)
    return 0


def main(argv: list[str] | None = None) -> int:
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description="Manage protected Champion adoption workflow and preflight (#200).")
    sub = parser.add_subparsers(dest="subcommand", required=True)

    p_enq = sub.add_parser("enqueue-pass", help="Enqueue verified checkpoint pass for frozen slate")
    p_enq.add_argument("--evidence-root", required=True)
    p_enq.add_argument("--slate-id", required=True)
    p_enq.add_argument("--season", required=True)
    p_enq.add_argument("--checkpoint-gw", type=int, required=True)
    p_enq.add_argument("--candidate-name", required=True)
    p_enq.add_argument("--expected-champion", required=True)
    p_enq.add_argument("--bundle-hash", required=True)
    p_enq.add_argument("--archive-sha256", default=None)
    p_enq.add_argument("--snapshot-archive", default=None)
    p_enq.add_argument("--bundle-path", default=None)
    p_enq.add_argument("--protocol-hash", default="")
    p_enq.add_argument("--serving-model-closure-hash", default=None)
    p_enq.add_argument("--net-delta", type=float, default=0.0)
    p_enq.add_argument("--podium-index", type=int, default=0)
    p_enq.add_argument("--expires-at-utc", default=None)
    p_enq.add_argument("--actor", default="checkpoint-evaluator")

    p_disp = sub.add_parser("dispatch-notice", help="Send or deduplicate single adoption notice for request_id")
    p_disp.add_argument("--evidence-root", required=True)
    p_disp.add_argument("--request-id", required=True)
    p_disp.add_argument("--review-url", required=True)
    p_disp.add_argument("--recipient", default="operator@example.com")
    p_disp.add_argument("--outbox-dir", default=None)
    p_disp.add_argument("--webhook-url", default=None)
    p_disp.add_argument("--github-repo", default=None)
    p_disp.add_argument("--assignee", default=None)

    p_rec_notice = sub.add_parser("reconcile-notice", help="Reconcile uncertain notice delivery state for request_id")
    p_rec_notice.add_argument("--evidence-root", required=True)
    p_rec_notice.add_argument("--request-id", required=True)
    p_rec_notice.add_argument("--review-url", required=True)
    p_rec_notice.add_argument("--recipient", default="operator@example.com")
    p_rec_notice.add_argument("--outbox-dir", default=None)
    p_rec_notice.add_argument("--webhook-url", default=None)
    p_rec_notice.add_argument("--github-repo", default=None)
    p_rec_notice.add_argument("--assignee", default=None)
    p_rec_notice.add_argument("--provider-status", choices=["delivered", "not_found", "unknown"], default=None)

    p_upd_issue = sub.add_parser("update-review-issue", help="Comment on and optionally close Adoption Review Issue")
    p_upd_issue.add_argument("--repo", required=True)
    p_upd_issue.add_argument("--request-id", required=True)
    p_upd_issue.add_argument("--comment", default=None)
    p_upd_issue.add_argument("--close", action="store_true")
    p_upd_issue.add_argument("--close-if-terminal", action="store_true")
    p_upd_issue.add_argument("--evidence-root", default=None)

    p_app = sub.add_parser("record-approval", help="Bind human approval and approved PR head SHA")
    p_app.add_argument("--evidence-root", required=True)
    p_app.add_argument("--request-id", required=True)
    p_app.add_argument("--approval-ref", required=True)
    p_app.add_argument("--approved-pr-head-sha", default=None)
    p_app.add_argument("--actor", default="operator")
    p_app.add_argument("--reason", default="Human approved protected adoption request")

    p_sync = sub.add_parser("sync-evidence-worktree", help="Mirror evidence updates and released reservation into git worktree")
    p_sync.add_argument("--source-dir", required=True)
    p_sync.add_argument("--worktree-dir", required=True)

    p_rej = sub.add_parser("record-rejection", help="Terminally reject active request and optionally advance queue")
    p_rej.add_argument("--evidence-root", required=True)
    p_rej.add_argument("--request-id", required=True)
    p_rej.add_argument("--actor", required=True)
    p_rej.add_argument("--reason", required=True)
    p_rej.add_argument("--advance-queue", action="store_true")
    p_rej.add_argument("--selection-path", type=Path, default=None)

    p_prep = sub.add_parser("prepare-adoption-pr", help="Record human approval and stage 2-file adoption PR changes")
    p_prep.add_argument("--evidence-root", required=True)
    p_prep.add_argument("--request-id", required=True)
    p_prep.add_argument("--approval-ref", required=True)
    p_prep.add_argument("--actor", default="operator")
    p_prep.add_argument("--selection-path", type=Path, default=DEFAULT_CONFIG_PATH)
    p_prep.add_argument("--approved-commit-sha", default=None)

    p_ver = sub.add_parser("verify-adoption-pr", help="Verify adoption PR diff, snapshot archive, and eligibility")
    p_ver.add_argument("--evidence-root", required=True)
    p_ver.add_argument("--request-id", required=True)
    p_ver.add_argument("--slate-id", required=True)
    p_ver.add_argument("--selection-path", type=Path, default=DEFAULT_CONFIG_PATH)
    p_ver.add_argument("--base-selection-path", type=Path, default=None)
    p_ver.add_argument("--head-sha", default=None)
    p_ver.add_argument("--changed-file", action="append", default=None)

    p_merge = sub.add_parser("execute-protected-merge", help="Acquire shared reservation and execute atomic merge")
    p_merge.add_argument("--evidence-root", required=True)
    p_merge.add_argument("--request-id", required=True)
    p_merge.add_argument("--slate-id", required=True)
    p_merge.add_argument("--approval-ref", required=True)
    p_merge.add_argument("--approved-pr-head-sha", required=True)
    p_merge.add_argument("--pr-head-sha", required=True)
    p_merge.add_argument("--changed-file", action="append", default=None)
    p_merge.add_argument("--checks-green", action="store_true")
    p_merge.add_argument("--auto-merge-enabled", action="store_true")
    p_merge.add_argument("--main-selection-path", type=Path, default=DEFAULT_CONFIG_PATH)
    p_merge.add_argument("--holder", default="github-app-adoption-merger")
    p_merge.add_argument("--repo", default=None)
    p_merge.add_argument("--pr-number", type=int, default=None)
    p_merge.add_argument("--merge-via-github-api", action="store_true")
    p_merge.add_argument("--require-live-checks", action="store_true")
    p_merge.add_argument("--worktree-dir", type=Path, default=None)

    p_rec_merge = sub.add_parser("reconcile-merge", help="Reconcile interrupted merge reservation from protected main")
    p_rec_merge.add_argument("--evidence-root", required=True)
    p_rec_merge.add_argument("--main-selection-path", type=Path, default=DEFAULT_CONFIG_PATH)
    p_rec_merge.add_argument("--remote-main-ref", default=None)
    p_rec_merge.add_argument("--actor", default="adoption-reconciler")

    p_preflight = sub.add_parser("production-preflight", help="Run read-only production parity preflight (#197)")
    p_preflight.add_argument("--repo", default="JubileeZ/fpl-jubilee-ascent")
    p_preflight.add_argument("--output", type=Path, default=None)
    p_preflight.add_argument("--offline-snapshot", type=Path, default=None)

    args = parser.parse_args(argv)
    if args.subcommand == "enqueue-pass":
        return _enqueue_pass_command(args)
    if args.subcommand in ("dispatch-notice", "reconcile-notice"):
        return _dispatch_or_reconcile_notice_command(args)
    if args.subcommand == "update-review-issue":
        return _update_review_issue_command(args)
    if args.subcommand == "record-approval":
        return _record_approval_command(args)
    if args.subcommand == "sync-evidence-worktree":
        return _sync_evidence_worktree_command(args)
    if args.subcommand == "record-rejection":
        return _record_rejection_command(args)
    if args.subcommand == "prepare-adoption-pr":
        return _prepare_adoption_pr_command(args)
    if args.subcommand == "verify-adoption-pr":
        return _verify_adoption_pr_command(args)
    if args.subcommand == "execute-protected-merge":
        return _execute_protected_merge_command(args)
    if args.subcommand == "reconcile-merge":
        return _reconcile_merge_command(args)
    if args.subcommand == "production-preflight":
        return _production_preflight_command(args)
    raise ValueError(f"Unknown subcommand: {args.subcommand}")


if __name__ == "__main__":
    raise SystemExit(main())
