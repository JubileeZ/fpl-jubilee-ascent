"""CLI coordinator for protected Champion adoption requests, reserved merge, and production preflight (#197, #199, #200)."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any
import urllib.error
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backtesting.adoption_transaction import (
    AUTHORIZED_ADOPTION_DIFF_FILES,
    AdoptionRequestManager,
    NotificationDispatcher,
    NotificationMessage,
    SharedReservationCoordinator,
)
from backtesting.portable_evidence import ExclusionLedger, verify_checkpoint_snapshot_archive
from backtesting.promotion_evidence import (
    CHECKPOINT_EVIDENCE_V2,
    CHECKPOINT_EVIDENCE_VERSION,
    verify_checkpoint_recommendation_bundle,
    verify_recommendation_bundle,
)
from clients.env_loader import configure_utf8_stdio
from commands.evaluate_model_promotion import adopt_champion
from commands.inventory_pilot_fixture import build_pilot_fixture_inventory
from models.selection import DEFAULT_CONFIG_PATH, load_model_selection

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CERTIFICATION_Digest_EXPECTED = "9e7234b17fc73543eb8330817f3d5ec519735de4f3264485f2592c7f46d53c56"


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
    outbox_dir = Path(args.outbox_dir).resolve() if args.outbox_dir else (root / "outbox")
    provider = FileOutboxMailProvider(
        outbox_dir,
        override_status=getattr(args, "provider_status", None),
    )
    dispatcher = NotificationDispatcher(root, provider=provider)
    rec = dispatcher.reconcile_and_dispatch(
        req,
        review_url=str(args.review_url),
        recipient=str(args.recipient),
    )
    print(json.dumps(rec.to_dict(), sort_keys=True))
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

    approved = manager.record_approval(
        req.request_id,
        actor=str(args.actor),
        approval_ref=str(args.approval_ref),
        approved_pr_head_sha=args.approved_commit_sha,
    )
    bundle_arg: Path | str
    if approved.snapshot_archive_path is not None:
        snap = Path(approved.snapshot_archive_path)
        bundle_arg = snap if snap.is_absolute() else (root / snap).resolve()
    elif approved.bundle_path is not None:
        bp = Path(approved.bundle_path)
        bundle_arg = bp if bp.is_absolute() else (root / bp).resolve()
    else:
        raise ValueError(f"Request '{approved.request_id}' lacks snapshot_archive_path and bundle_path")

    reg_path = root / "registry.jsonl"
    excl_path = root / "exclusions.jsonl"
    updated = adopt_champion(
        bundle_arg,
        config_path=args.selection_path,
        approval_ref=str(args.approval_ref),
        expected_current_champion=approved.expected_champion,
        candidate_name=approved.candidate_name,
        approved_bundle_hash=approved.bundle_hash,
        snapshot_archive_path=bundle_arg if approved.snapshot_archive_path is not None else None,
        expected_archive_sha256=approved.archive_sha256,
        canonical_registry_path=reg_path if reg_path.is_file() else None,
        canonical_exclusions_path=excl_path if excl_path.is_file() else None,
        request_id=approved.request_id,
        slate_id=approved.slate_id,
        approved_commit_sha=args.approved_commit_sha,
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
    if req.status not in ("pending_approval", "approved"):
        raise ValueError(f"Request '{req.request_id}' is not open for PR checks (status='{req.status}')")

    if args.changed_file:
        changed = set(args.changed_file)
        if changed != AUTHORIZED_ADOPTION_DIFF_FILES:
            raise ValueError(f"Adoption PR contains unauthorized file diff: {sorted(changed)}")

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
        if excl.is_excluded(req.candidate_name, slate_id=req.slate_id, season=req.season) or excl.is_excluded(
            req.candidate_name, season=req.season
        ):
            raise ValueError(f"Candidate '{req.candidate_name}' is excluded in ExclusionLedger")

    reg_path = root / "registry.jsonl"
    if req.snapshot_archive_path is not None:
        snap = Path(req.snapshot_archive_path)
        snap_target = snap if snap.is_absolute() else (root / snap).resolve()
        verify_checkpoint_snapshot_archive(
            snap_target,
            expected_archive_sha256=req.archive_sha256,
            expected_champion=req.expected_champion,
            canonical_registry_path=reg_path if reg_path.is_file() else None,
            canonical_exclusions_path=excl_path if excl_path.is_file() else None,
        )
    elif req.bundle_path is not None:
        bp = Path(req.bundle_path)
        b_target = bp if bp.is_absolute() else (root / bp).resolve()
        raw = json.loads(b_target.read_bytes())
        if raw.get("version") in (CHECKPOINT_EVIDENCE_VERSION, CHECKPOINT_EVIDENCE_V2):
            verify_checkpoint_recommendation_bundle(b_target, require_finalized=True)
        else:
            verify_recommendation_bundle(b_target, require_finalized=True)
    else:
        raise ValueError(f"Request '{req.request_id}' lacks snapshot_archive_path and bundle_path")

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


def _execute_protected_merge_command(args: argparse.Namespace) -> int:
    root = Path(args.evidence_root).resolve()
    coordinator = SharedReservationCoordinator(root)
    changed_files = tuple(args.changed_file) if args.changed_file else tuple(sorted(AUTHORIZED_ADOPTION_DIFF_FILES))
    result = coordinator.execute_reserved_adoption_merge(
        request_id=str(args.request_id),
        slate_id=str(args.slate_id),
        approval_ref=str(args.approval_ref),
        approved_pr_head_sha=str(args.approved_pr_head_sha),
        pr_head_sha=str(args.pr_head_sha),
        changed_files=changed_files,
        checks_green=bool(args.checks_green),
        auto_merge_enabled=bool(args.auto_merge_enabled),
        main_selection_path=args.main_selection_path,
        holder=str(args.holder),
    )
    print(json.dumps(result, sort_keys=True))
    return 0


def _reconcile_merge_command(args: argparse.Namespace) -> int:
    root = Path(args.evidence_root).resolve()
    coordinator = SharedReservationCoordinator(root)
    result = coordinator.reconcile_unknown_merge(
        main_selection_path=args.main_selection_path,
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
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode("utf-8")
            return int(resp.status), json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        return int(exc.code), None
    except Exception:
        return 0, None


def _query_live_github_snapshot(repo: str) -> dict[str, Any]:
    token = _retrieve_github_token_in_memory()
    base = f"https://api.github.com/repos/{repo}"

    repo_code, repo_data = _github_get_json(base, token)
    bp_code, bp_data = _github_get_json(f"{base}/branches/main/protection", token)
    env_code, env_data = _github_get_json(f"{base}/environments/champion-adoption-approval", token)
    var_code, var_data = _github_get_json(f"{base}/actions/variables/CHAMPION_ADOPTION_LIVE_ENABLED", token)
    ev_code, _ = _github_get_json(f"{base}/branches/validation-evidence", token)
    rel_code, _ = _github_get_json(f"{base}/releases?per_page=1", token)

    req_checks = bp_data.get("required_status_checks", {}) if isinstance(bp_data, dict) else {}
    enforce_admins = (
        bool(bp_data.get("enforce_admins", {}).get("enabled"))
        if isinstance(bp_data, dict) and isinstance(bp_data.get("enforce_admins"), dict)
        else False
    )
    protection_rules = env_data.get("protection_rules", []) if isinstance(env_data, dict) else []
    reviewers = [r for r in protection_rules if isinstance(r, dict) and r.get("type") == "required_reviewers"]

    live_var_val = str(var_data.get("value", "false")).lower() if (var_code == 200 and isinstance(var_data, dict)) else "false"
    allow_auto_merge = bool(repo_data.get("allow_auto_merge", False)) if isinstance(repo_data, dict) else False

    return {
        "api_reachable": repo_code == 200,
        "branch_protection": {
            "http_status": bp_code,
            "enabled": bp_code == 200,
            "required_status_checks": {
                "strict": bool(req_checks.get("strict")),
                "contexts": list(req_checks.get("contexts", ())),
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
            "github_app_configured": False,
        },
        "validation_evidence_branch": {
            "branch_http_status": ev_code,
            "exists": ev_code == 200,
            "releases_accessible": rel_code == 200,
        },
        "mail_provider": {
            "configured": False,
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
    wf_files = (
        ".github/workflows/champion-adoption-request.yml",
        ".github/workflows/champion-adoption-pr-checks.yml",
        ".github/workflows/champion-adoption-merge.yml",
    )
    wf_present = all((root / rel).is_file() for rel in wf_files)
    coord_wired = hasattr(SharedReservationCoordinator, "record_exclusion_under_reservation") and hasattr(
        SharedReservationCoordinator, "execute_reserved_adoption_merge"
    )
    wiring_passed = wf_present and coord_wired
    gates["shared_reservation_wiring"] = {
        "passed": wiring_passed,
        "status": "pass" if wiring_passed else "blocked",
        "blocker": None if wiring_passed else "SharedReservationCoordinator or protected workflows missing",
        "recovery_action": "Ensure SharedReservationCoordinator and champion-adoption-*.yml workflows are committed.",
        "details": {"workflows_present": wf_present, "coordinator_wired": coord_wired},
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
    mp = gh.get("mail_provider", {})
    mail_passed = bool(mp.get("configured") and hasattr(NotificationDispatcher, "reconcile_and_dispatch"))
    gates["mail_delivery_and_reconciliation"] = {
        "passed": mail_passed,
        "status": "pass" if mail_passed else "blocked",
        "blocker": None if mail_passed else "Production mail provider credentials/inbox not configured",
        "recovery_action": "Configure controlled mail provider credentials and verify single-notice reconciliation.",
        "details": mp,
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
    cert_path = root / "docs" / "research" / "sparse-confirmation-certification" / "certification_result.json"
    cert_passed = False
    cert_details: dict[str, Any] = {"path": cert_path.relative_to(root).as_posix(), "exists": cert_path.is_file()}
    if cert_path.is_file():
        cert_data = json.loads(cert_path.read_bytes())
        cert_passed = bool(
            cert_data.get("certified") is True
            and cert_data.get("certified_mode") == "advisory"
            and cert_data.get("certification_digest") == CERTIFICATION_Digest_EXPECTED
        )
        cert_details.update(
            {
                "certified": cert_data.get("certified"),
                "certified_mode": cert_data.get("certified_mode"),
                "certification_digest": cert_data.get("certification_digest"),
            }
        )
    gates["certified_protocol"] = {
        "passed": cert_passed,
        "status": "pass" if cert_passed else "blocked",
        "blocker": None if cert_passed else "Sparse confirmation protocol certification missing or digest mismatch",
        "recovery_action": "Run #201 sparse confirmation certification runner and commit verified certification_result.json.",
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
    slate_passed = bool(sel.podium_sealed and sel.candidates and sel.podium_frozen_season)
    gates["sealed_slate_and_operator_signoff"] = {
        "passed": slate_passed,
        "status": "pass" if slate_passed else "blocked",
        "blocker": None
        if slate_passed
        else (
            f"Comparison Slate not sealed for active validation (champion='{sel.champion}', "
            f"provisional_active={sel.provisional_active!r}, podium_sealed={sel.podium_sealed}) and operator sign-off pending"
        ),
        "recovery_action": "Seal Comparison Slate with >=1 qualified finalist and record named operator sign-off for season and checkpoint.",
        "details": {
            "champion": sel.champion,
            "candidates": list(sel.candidates),
            "provisional_active": sel.provisional_active,
            "podium_frozen_season": sel.podium_frozen_season,
            "podium_sealed": sel.podium_sealed,
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

    p_rec_notice = sub.add_parser("reconcile-notice", help="Reconcile uncertain notice delivery state for request_id")
    p_rec_notice.add_argument("--evidence-root", required=True)
    p_rec_notice.add_argument("--request-id", required=True)
    p_rec_notice.add_argument("--review-url", required=True)
    p_rec_notice.add_argument("--recipient", default="operator@example.com")
    p_rec_notice.add_argument("--outbox-dir", default=None)
    p_rec_notice.add_argument("--provider-status", choices=["delivered", "not_found", "unknown"], default=None)

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

    p_rec_merge = sub.add_parser("reconcile-merge", help="Reconcile interrupted merge reservation from protected main")
    p_rec_merge.add_argument("--evidence-root", required=True)
    p_rec_merge.add_argument("--main-selection-path", type=Path, default=DEFAULT_CONFIG_PATH)
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
