"""End-to-end local pilot acceptance harness and production preflight tests (#194, #197, #199, #200)."""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from backtesting import portable_evidence
from backtesting.adoption_transaction import AdoptionRequestManager
from backtesting.confirmation_registry import ConfirmationRegistry
from backtesting.portable_evidence import (
    AdoptionLedger,
    compute_serving_model_closure,
    verify_checkpoint_snapshot_archive,
)
from commands import evaluate_model_promotion
from commands.evaluate_model_promotion import adopt_champion
from commands.manage_champion_adoption import main as manage_main
from models.selection import load_model_selection, save_model_selection
from tests.test_adoption_transaction import _build_verified_snapshot_fixture


def test_portable_snapshot_relocation_registry_advancement_and_fault_injections(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify portable snapshot relocation across fresh directory + canonical registry advancement and fail-closed faults."""
    root, bundle_path, archive_path, bundle_hash, archive_sha = _build_verified_snapshot_fixture(
        tmp_path, monkeypatch, candidate_name="adaptive_causal_challenger", checkpoint_gw=15, bundle_seed="a"
    )

    # Relocate snapshot archive to a completely separate directory and advance canonical registry with a second finalist
    relocated_dir = tmp_path / "relocated_runner"
    relocated_dir.mkdir()
    relocated_archive = relocated_dir / archive_path.name
    relocated_archive.write_bytes(archive_path.read_bytes())

    canon_reg_path = relocated_dir / "canonical_registry.jsonl"
    canon_reg_path.write_bytes((root / "registry.jsonl").read_bytes())
    canon_reg = ConfirmationRegistry(canon_reg_path)
    # Advance canonical registry with another finalist registration (chain extension)
    canon_reg.register_finalist(
        candidate_name="club_def_prior_challenger",
        champion_name="def_xg_shrink_challenger",
        mechanism_family="fam-club-def",
        model_source_hash="1" * 64,
        parameters_hash="2" * 64,
        dev_selection_record_ref="3" * 64,
        protocol_hash="4" * 64,
        attempt_id="att-club-def-15",
        requested_seasons=("2026-27",),
        max_family_attempts=2,
    )

    canon_excl_path = relocated_dir / "canonical_exclusions.jsonl"
    canon_excl_path.write_bytes(b"")

    verified = verify_checkpoint_snapshot_archive(
        relocated_archive,
        expected_archive_sha256=archive_sha,
        expected_champion="def_xg_shrink_challenger",
        canonical_registry_path=canon_reg_path,
        canonical_exclusions_path=canon_excl_path,
    )
    assert verified["archive_sha256"] == archive_sha
    assert verified["bundle"]["bundle_hash"] == bundle_hash

    # Fault 1: Altered archive bytes fail closed
    corrupt_archive = relocated_dir / "corrupt.tar.gz"
    corrupt_archive.write_bytes(relocated_archive.read_bytes()[:-4] + b"xxxx")
    with pytest.raises(ValueError, match="archive_sha256"):
        verify_checkpoint_snapshot_archive(corrupt_archive, expected_archive_sha256=archive_sha)

    # Fault 2: Mismatched runtime identity / serving closure fails closed
    fake_closure = compute_serving_model_closure(("def_xg_shrink_challenger",))
    monkeypatch.setattr(portable_evidence, "compute_serving_model_closure", lambda *a, **kw: fake_closure)
    with pytest.raises(ValueError, match="serving_model_closure_hash"):
        verify_checkpoint_snapshot_archive(
            relocated_archive,
            expected_archive_sha256=archive_sha,
            expected_champion="def_xg_shrink_challenger",
        )
    monkeypatch.undo()

    # Fault 3: Synthetic evidence (empirical_admission=False) fails closed at adopt_champion
    synth_bundle = dict(json.loads(bundle_path.read_bytes()))
    synth_bundle["empirical_admission"] = False
    synth_bundle_path = tmp_path / "synth_bundle.json"
    synth_bundle_path.write_text(json.dumps(synth_bundle), encoding="utf-8")
    monkeypatch.setattr(
        evaluate_model_promotion,
        "verify_checkpoint_recommendation_bundle",
        lambda bp, **kw: json.loads(Path(bp).read_bytes()),
    )
    sel_path = tmp_path / "sel_synth.json"
    save_model_selection(load_model_selection(root / "selection.json"), sel_path)
    with pytest.raises(ValueError, match="complete empirical scientific pass required"):
        adopt_champion(
            synth_bundle_path,
            config_path=sel_path,
            approval_ref="GH-SYNTH",
            expected_current_champion="def_xg_shrink_challenger",
            approved_bundle_hash=bundle_hash,
        )
    assert not sel_path.with_suffix(".adoption.json").exists()


def test_full_cli_lifecycle_and_idempotent_protected_merge(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Exercise manage_champion_adoption CLI subcommands end-to-end through protected merge and retry."""
    root, bundle_path, archive_path, bundle_hash, archive_sha = _build_verified_snapshot_fixture(
        tmp_path, monkeypatch, candidate_name="adaptive_causal_challenger", checkpoint_gw=15, bundle_seed="e"
    )
    main_sel_path = tmp_path / "main_config" / "model_selection.json"
    save_model_selection(load_model_selection(root / "selection.json"), main_sel_path)
    pr_sel_path = tmp_path / "pr_config" / "model_selection.json"
    save_model_selection(load_model_selection(root / "selection.json"), pr_sel_path)

    # 1. Enqueue pass via CLI
    assert (
        manage_main(
            [
                "enqueue-pass",
                "--evidence-root",
                str(root),
                "--slate-id",
                "slate-2026-27",
                "--season",
                "2026-27",
                "--checkpoint-gw",
                "15",
                "--candidate-name",
                "adaptive_causal_challenger",
                "--expected-champion",
                "def_xg_shrink_challenger",
                "--bundle-hash",
                bundle_hash,
                "--archive-sha256",
                archive_sha,
                "--snapshot-archive",
                str(archive_path),
                "--bundle-path",
                str(bundle_path),
                "--protocol-hash",
                "4" * 64,
                "--net-delta",
                "16.5",
                "--podium-index",
                "0",
            ]
        )
        == 0
    )
    enq_out = json.loads(capsys.readouterr().out)
    request_id = enq_out["request_id"]
    assert enq_out["status"] == "pending_approval"

    # 2. Dispatch notice via CLI using outbox directory; repeated call produces no duplicate email file
    outbox = tmp_path / "outbox"
    review_url = "https://github.com/JubileeZ/fpl-jubilee-ascent/actions/runs/9001"
    assert (
        manage_main(
            [
                "dispatch-notice",
                "--evidence-root",
                str(root),
                "--request-id",
                request_id,
                "--review-url",
                review_url,
                "--outbox-dir",
                str(outbox),
            ]
        )
        == 0
    )
    disp1 = json.loads(capsys.readouterr().out)
    assert disp1["status"] == "delivered"
    assert len(list(outbox.glob("*.json"))) == 1

    assert (
        manage_main(
            [
                "dispatch-notice",
                "--evidence-root",
                str(root),
                "--request-id",
                request_id,
                "--review-url",
                review_url,
                "--outbox-dir",
                str(outbox),
            ]
        )
        == 0
    )
    disp2 = json.loads(capsys.readouterr().out)
    assert disp2["status"] == "delivered"
    assert len(list(outbox.glob("*.json"))) == 1

    # 3. Prepare adoption PR on PR checkout
    pr_head_sha = "7" * 40
    assert (
        manage_main(
            [
                "prepare-adoption-pr",
                "--evidence-root",
                str(root),
                "--request-id",
                request_id,
                "--approval-ref",
                "GH-APPROVAL-9001",
                "--selection-path",
                str(pr_sel_path),
                "--approved-commit-sha",
                pr_head_sha,
            ]
        )
        == 0
    )
    prep_out = json.loads(capsys.readouterr().out)
    assert prep_out["champion"] == "adaptive_causal_challenger"

    # 4. Verify adoption PR checks on PR checkout
    assert (
        manage_main(
            [
                "verify-adoption-pr",
                "--evidence-root",
                str(root),
                "--request-id",
                request_id,
                "--slate-id",
                "slate-2026-27",
                "--selection-path",
                str(pr_sel_path),
                "--changed-file",
                "config/model_selection.json",
                "--changed-file",
                "config/model_selection.adoption.json",
            ]
        )
        == 0
    )
    ver_out = json.loads(capsys.readouterr().out)
    assert ver_out["verified"] is True

    # Unauthorized file diff in verify-adoption-pr fails closed
    with pytest.raises(ValueError, match="unauthorized file diff"):
        manage_main(
            [
                "verify-adoption-pr",
                "--evidence-root",
                str(root),
                "--request-id",
                request_id,
                "--slate-id",
                "slate-2026-27",
                "--selection-path",
                str(pr_sel_path),
                "--changed-file",
                "config/model_selection.json",
                "--changed-file",
                "config/model_selection.adoption.json",
                "--changed-file",
                "models/malicious.py",
            ]
        )

    # 5. Execute protected merge onto main_sel_path
    assert (
        manage_main(
            [
                "execute-protected-merge",
                "--evidence-root",
                str(root),
                "--request-id",
                request_id,
                "--slate-id",
                "slate-2026-27",
                "--approval-ref",
                "GH-APPROVAL-9001",
                "--approved-pr-head-sha",
                pr_head_sha,
                "--pr-head-sha",
                pr_head_sha,
                "--changed-file",
                "config/model_selection.json",
                "--changed-file",
                "config/model_selection.adoption.json",
                "--checks-green",
                "--main-selection-path",
                str(main_sel_path),
            ]
        )
        == 0
    )
    merge_out = json.loads(capsys.readouterr().out)
    assert merge_out["status"] == "adopted"
    assert merge_out["merged"] is True
    assert load_model_selection(main_sel_path).champion == "adaptive_causal_challenger"
    assert load_model_selection(main_sel_path).podium_sealed is False

    # 6. Retry of execute-protected-merge is idempotent: no duplicate merge or ledger entry
    ledger_count_before = len(AdoptionLedger(root / "adoption_ledger.jsonl").load_all_records())
    assert (
        manage_main(
            [
                "execute-protected-merge",
                "--evidence-root",
                str(root),
                "--request-id",
                request_id,
                "--slate-id",
                "slate-2026-27",
                "--approval-ref",
                "GH-APPROVAL-9001",
                "--approved-pr-head-sha",
                pr_head_sha,
                "--pr-head-sha",
                pr_head_sha,
                "--changed-file",
                "config/model_selection.json",
                "--changed-file",
                "config/model_selection.adoption.json",
                "--checks-green",
                "--main-selection-path",
                str(main_sel_path),
            ]
        )
        == 0
    )
    retry_out = json.loads(capsys.readouterr().out)
    assert retry_out["status"] == "already_adopted"
    assert retry_out["merged"] is False
    assert len(AdoptionLedger(root / "adoption_ledger.jsonl").load_all_records()) == ledger_count_before


def test_production_preflight_read_only_attestation(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Verify read-only production-preflight reports all 10 live rollout gates with blockers & recovery actions."""
    offline_snapshot = {
        "branch_protection": {
            "enabled": True,
            "required_status_checks": {"strict": True, "contexts": ["verify-adoption-pr"]},
            "enforce_admins": True,
        },
        "protected_environment": {
            "name": "champion-adoption-approval",
            "exists": True,
            "required_reviewers": ["JubileeZ"],
        },
        "repo_settings": {
            "allow_auto_merge": False,
            "github_app_configured": True,
        },
        "validation_evidence_branch": {
            "exists": True,
            "releases_accessible": True,
        },
        "mail_provider": {
            "configured": True,
        },
        "variables": {
            "CHAMPION_ADOPTION_LIVE_ENABLED": "false",
        },
    }
    snap_file = tmp_path / "offline_github_snapshot.json"
    snap_file.write_text(json.dumps(offline_snapshot), encoding="utf-8")
    out_file = tmp_path / "preflight_report.json"

    rc = manage_main(
        [
            "production-preflight",
            "--repo",
            "JubileeZ/fpl-jubilee-ascent",
            "--offline-snapshot",
            str(snap_file),
            "--output",
            str(out_file),
        ]
    )
    assert rc == 0
    report = json.loads(out_file.read_text(encoding="utf-8"))
    assert report["read_only"] is True
    assert report["repo"] == "JubileeZ/fpl-jubilee-ascent"
    expected_gates = {
        "branch_protection_main",
        "protected_environment",
        "github_app_and_no_bypass",
        "shared_reservation_wiring",
        "immutable_evidence_and_releases",
        "mail_delivery_and_reconciliation",
        "live_rollout_disabled",
        "certified_protocol",
        "admissible_historical_passing_fixture",
        "sealed_slate_and_operator_signoff",
    }
    assert set(report["gates"]) == expected_gates
    assert report["gates"]["branch_protection_main"]["passed"] is True
    assert report["gates"]["protected_environment"]["passed"] is True
    assert report["gates"]["github_app_and_no_bypass"]["passed"] is True
    assert report["gates"]["shared_reservation_wiring"]["passed"] is True
    assert report["gates"]["live_rollout_disabled"]["passed"] is True
    assert report["gates"]["certified_protocol"]["passed"] is True
    from commands.manage_champion_adoption import CERTIFICATION_DIGEST_EXPECTED

    assert report["gates"]["certified_protocol"]["details"]["certification_digest"] == CERTIFICATION_DIGEST_EXPECTED
    assert report["gates"]["certified_protocol"]["details"]["evaluator_revisions_match"] is True
    assert report["gates"]["certified_protocol"]["details"]["canonical_digest_match"] is True
    # Historical GW15 passing fixture and sealed active slate are accurately reported as blocked
    assert report["gates"]["admissible_historical_passing_fixture"]["passed"] is False
    assert report["gates"]["admissible_historical_passing_fixture"]["blocker"]
    assert report["gates"]["admissible_historical_passing_fixture"]["recovery_action"]
    assert report["gates"]["sealed_slate_and_operator_signoff"]["passed"] is False
    assert report["live_activation_ready"] is False


def test_cli_rejection_queue_advancement_and_reconcile_subcommands(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Exercise record-rejection --advance-queue, reconcile-notice, and reconcile-merge CLI subcommands."""
    from backtesting.adoption_transaction import SharedReservationCoordinator

    root1, bundle1, archive1, bhash1, asha1 = _build_verified_snapshot_fixture(
        tmp_path, monkeypatch, candidate_name="adaptive_causal_challenger", checkpoint_gw=15, bundle_seed="1"
    )
    _, bundle2, archive2, bhash2, asha2 = _build_verified_snapshot_fixture(
        tmp_path, monkeypatch, candidate_name="club_def_prior_challenger", checkpoint_gw=30, bundle_seed="2"
    )
    shared = tmp_path / "cli_shared"
    shared.mkdir()
    save_model_selection(load_model_selection(root1 / "selection.json"), shared / "selection.json")
    (shared / "exclusions.jsonl").write_bytes(b"")

    for gw, cand, bhash, asha, arch, bpath, delta, idx in (
        (15, "adaptive_causal_challenger", bhash1, asha1, archive1, bundle1, 10.0, 0),
        (30, "club_def_prior_challenger", bhash2, asha2, archive2, bundle2, 22.0, 1),
    ):
        manage_main(
            [
                "enqueue-pass",
                "--evidence-root",
                str(shared),
                "--slate-id",
                "slate-2026-27",
                "--season",
                "2026-27",
                "--checkpoint-gw",
                str(gw),
                "--candidate-name",
                cand,
                "--expected-champion",
                "def_xg_shrink_challenger",
                "--bundle-hash",
                bhash,
                "--archive-sha256",
                asha,
                "--snapshot-archive",
                str(arch),
                "--bundle-path",
                str(bpath),
                "--net-delta",
                str(delta),
                "--podium-index",
                str(idx),
            ]
        )
    out1, out2 = [json.loads(line) for line in capsys.readouterr().out.strip().splitlines()]
    assert out1["status"] == "pending_approval"
    assert out2["status"] == "queued"

    # Reject first request and advance queue via CLI
    assert (
        manage_main(
            [
                "record-rejection",
                "--evidence-root",
                str(shared),
                "--request-id",
                out1["request_id"],
                "--actor",
                "operator",
                "--reason",
                "Reject GW15 request",
                "--advance-queue",
                "--selection-path",
                str(shared / "selection.json"),
            ]
        )
        == 0
    )
    rej_out = json.loads(capsys.readouterr().out)
    assert rej_out["rejected"]["status"] == "rejected"
    assert rej_out["next_active"]["request_id"] == out2["request_id"]
    assert rej_out["next_active"]["status"] == "pending_approval"

    # Reconcile notice via CLI
    assert (
        manage_main(
            [
                "reconcile-notice",
                "--evidence-root",
                str(shared),
                "--request-id",
                out2["request_id"],
                "--review-url",
                "https://github.com/JubileeZ/fpl-jubilee-ascent/actions/runs/9002",
                "--outbox-dir",
                str(tmp_path / "outbox2"),
            ]
        )
        == 0
    )
    rec_notice_out = json.loads(capsys.readouterr().out)
    assert rec_notice_out["status"] == "delivered"

    # Simulate unknown merge reservation and reconcile via CLI
    coord = SharedReservationCoordinator(shared)
    res = coord.acquire_reservation(
        holder="github-app",
        purpose="adoption_merge",
        slate_id="slate-2026-27",
        request_id=out2["request_id"],
        approved_pr_head_sha="9" * 40,
    )
    coord._update_reservation_state(res, "merge_outcome_unknown")
    assert (
        manage_main(
            [
                "reconcile-merge",
                "--evidence-root",
                str(shared),
                "--main-selection-path",
                str(shared / "selection.json"),
            ]
        )
        == 0
    )
    rec_merge_out = json.loads(capsys.readouterr().out)
    assert rec_merge_out["status"] == "reconciled_not_merged_reset_for_retry"
    assert coord.current_reservation() is None


def test_webhook_mail_provider_live_pr_checks_api_merge_and_worktree_sync(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Exercise HttpWebhookMailProvider, fail-closed unconfigured dispatch, live PR checks/API merge, and worktree sync."""
    import httpx
    from backtesting.adoption_transaction import AdoptionRequestManager, MergeInterruptedError, NotificationDispatcher, SharedReservationCoordinator
    from commands.manage_champion_adoption import (
        HttpWebhookMailProvider,
        _execute_github_pr_merge,
        _fetch_and_verify_live_pr_checks,
        _sync_evidence_worktree,
    )
    from models.selection import ModelSelection, save_model_selection

    root, bundle_path, archive_path, bundle_hash, archive_sha = _build_verified_snapshot_fixture(
        tmp_path, monkeypatch, candidate_name="adaptive_causal_challenger", checkpoint_gw=15, bundle_seed="f"
    )
    req = AdoptionRequestManager(root).enqueue_pass(
        slate_id="slate-2026-27",
        season="2026-27",
        checkpoint_gw=15,
        candidate_name="adaptive_causal_challenger",
        expected_champion="def_xg_shrink_challenger",
        bundle_hash=bundle_hash,
        archive_sha256=archive_sha,
        snapshot_archive_path=str(archive_path),
        bundle_path=str(bundle_path),
        protocol_hash="4" * 64,
    )

    # 1. dispatch-notice without --outbox-dir or MAIL_PROVIDER_WEBHOOK_URL fails closed
    monkeypatch.delenv("MAIL_PROVIDER_WEBHOOK_URL", raising=False)
    with pytest.raises(ValueError, match="not configured"):
        manage_main(
            [
                "dispatch-notice",
                "--evidence-root",
                str(root),
                "--request-id",
                req.request_id,
                "--review-url",
                "https://github.com/org/repo/actions/runs/1",
            ]
        )

    # 2. HttpWebhookMailProvider uncertain 502 ack + status reconciliation -> no duplicate send
    calls: dict[str, int] = {"post": 0, "status": 0}

    def mail_handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            calls["post"] += 1
            if calls["post"] == 1:
                return httpx.Response(502)
            return httpx.Response(200, json={"provider_message_id": "wh-1"})
        if request.method == "GET":
            calls["status"] += 1
            return httpx.Response(200, json={"status": "delivered"})
        return httpx.Response(404)

    provider = HttpWebhookMailProvider(
        "https://mail.mock/send",
        api_key="tok",
        status_url="https://mail.mock/status/{request_id}",
        transport=httpx.MockTransport(mail_handler),
    )
    disp = NotificationDispatcher(root, provider=provider)
    r1 = disp.reconcile_and_dispatch(req, review_url="https://github.com/org/repo/actions/runs/1")
    assert r1.status == "uncertain"
    r2 = disp.reconcile_and_dispatch(req, review_url="https://github.com/org/repo/actions/runs/1")
    assert r2.status == "delivered"
    assert calls["post"] == 1 and calls["status"] == 1

    # 3. Live PR checks and squash merge via GitHub API mock
    head_sha = "c" * 40
    pr_state = {"conclusion": "success", "auto_merge": None, "merge_code": 200}

    def gh_handler(request: httpx.Request) -> httpx.Response:
        p = request.url.path
        if p.endswith("/pulls/12"):
            return httpx.Response(
                200,
                json={"state": "open", "head": {"sha": head_sha}, "auto_merge": pr_state["auto_merge"]},
            )
        if p.endswith("/pulls/12/files"):
            return httpx.Response(
                200,
                json=[
                    {"filename": "config/model_selection.json"},
                    {"filename": "config/model_selection.adoption.json"},
                ],
            )
        if p.endswith(f"/commits/{head_sha}/check-runs"):
            return httpx.Response(
                200,
                json={
                    "check_runs": [
                        {"name": "verify-adoption-pr", "status": "completed", "conclusion": pr_state["conclusion"]}
                    ]
                },
            )
        if p.endswith("/pulls/12/merge") and request.method == "PUT":
            if pr_state["merge_code"] != 200:
                return httpx.Response(int(pr_state["merge_code"]), json={"message": "server error"})
            return httpx.Response(200, json={"merged": True, "sha": "m" * 40})
        return httpx.Response(404)

    gh_transport = httpx.MockTransport(gh_handler)
    files = _fetch_and_verify_live_pr_checks(
        repo="org/repo", pr_number=12, approved_pr_head_sha=head_sha, pr_head_sha=head_sha,
        token="t", transport=gh_transport,
    )
    assert set(files) == {"config/model_selection.json", "config/model_selection.adoption.json"}

    pr_state["conclusion"] = "failure"
    with pytest.raises(ValueError, match="not green"):
        _fetch_and_verify_live_pr_checks(
            repo="org/repo", pr_number=12, approved_pr_head_sha=head_sha, pr_head_sha=head_sha,
            token="t", transport=gh_transport,
        )
    pr_state["conclusion"] = "success"
    pr_state["auto_merge"] = {"enabled_by": {"login": "bot"}}
    with pytest.raises(ValueError, match="auto-merge"):
        _fetch_and_verify_live_pr_checks(
            repo="org/repo", pr_number=12, approved_pr_head_sha=head_sha, pr_head_sha=head_sha,
            token="t", transport=gh_transport,
        )
    pr_state["auto_merge"] = None
    merged = _execute_github_pr_merge(
        repo="org/repo", pr_number=12, approved_pr_head_sha=head_sha, token="t", transport=gh_transport
    )
    assert merged["merge_commit_sha"] == "m" * 40
    pr_state["merge_code"] = 500
    with pytest.raises(MergeInterruptedError):
        _execute_github_pr_merge(
            repo="org/repo", pr_number=12, approved_pr_head_sha=head_sha, token="t", transport=gh_transport
        )

    # 4. Idempotent execute-protected-merge after reconcile-merge marks request adopted (closed PR)
    closed_pr = {"state": "closed"}

    def reconciled_pr_handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/pulls/12"):
            return httpx.Response(200, json={"state": closed_pr["state"], "head": {"sha": head_sha}, "auto_merge": None})
        return gh_handler(request)

    coord_idem = SharedReservationCoordinator(root)
    mgr_idem = coord_idem.request_manager
    mgr_idem.record_approval(
        req.request_id,
        actor="op",
        approval_ref="APP-IDEM",
        approved_pr_head_sha=head_sha,
    )
    coord_idem.acquire_reservation(
        holder="github-app-adoption-merger",
        purpose="adoption_merge",
        slate_id="slate-2026-27",
        request_id=req.request_id,
        approved_pr_head_sha=head_sha,
    )
    res_rec = coord_idem._update_reservation_state(coord_idem.current_reservation(), "merge_outcome_unknown")  # type: ignore[arg-type]
    assert res_rec.merge_state == "merge_outcome_unknown"
    main_sel_idem = tmp_path / "idem_config" / "model_selection.json"
    main_sel_idem.parent.mkdir(parents=True, exist_ok=True)
    save_model_selection(ModelSelection(champion="adaptive_causal_challenger", candidates=(), podium_sealed=False), main_sel_idem)
    main_sel_idem.with_suffix(".adoption.json").write_text(
        json.dumps(
            {
                "request_id": req.request_id,
                "slate_id": "slate-2026-27",
                "candidate_name": "adaptive_causal_challenger",
                "approval_ref": "APP-IDEM",
            }
        ),
        encoding="utf-8",
    )
    assert coord_idem.reconcile_unknown_merge(main_selection_path=main_sel_idem)["status"] == "reconciled_merged"
    import commands.manage_champion_adoption as mca_mod

    monkeypatch.setattr(mca_mod, "_retrieve_github_token_in_memory", lambda: "tok")
    monkeypatch.setattr(httpx, "Client", lambda **kw: httpx.Client(transport=httpx.MockTransport(reconciled_pr_handler)))
    capsys.readouterr()
    assert (
        manage_main(
            [
                "execute-protected-merge",
                "--evidence-root",
                str(root),
                "--request-id",
                req.request_id,
                "--slate-id",
                "slate-2026-27",
                "--approval-ref",
                "APP-IDEM",
                "--approved-pr-head-sha",
                head_sha,
                "--pr-head-sha",
                head_sha,
                "--repo",
                "org/repo",
                "--pr-number",
                "12",
                "--merge-via-github-api",
                "--require-live-checks",
                "--main-selection-path",
                str(main_sel_idem),
            ]
        )
        == 0
    )
    idem_out = json.loads(capsys.readouterr().out)
    assert idem_out["status"] == "already_adopted"

    # 5. sync-evidence-worktree copies files and removes released reservation.json preserving .git
    src_dir = tmp_path / "sync_src"
    wt_dir = tmp_path / "sync_wt"
    (src_dir / "scorecards").mkdir(parents=True)
    (src_dir / "scorecards" / "gw01.json").write_text("{}", encoding="utf-8")
    (wt_dir / ".git").mkdir(parents=True)
    (wt_dir / ".git" / "HEAD").write_text("ref: refs/heads/validation-evidence\n", encoding="utf-8")
    (wt_dir / "reservation.json").write_text('{"stale": true}', encoding="utf-8")
    _sync_evidence_worktree(src_dir, wt_dir)
    assert (wt_dir / "scorecards" / "gw01.json").is_file()
    assert not (wt_dir / "reservation.json").exists()
    assert (wt_dir / ".git" / "HEAD").is_file()

    # SharedReservationCoordinator type check for unused import sanity
    assert SharedReservationCoordinator is not None


def test_prepare_adoption_pr_does_not_record_approval_on_fail_closed_evidence(tmp_path: Path) -> None:
    """Fail-closed archive/evidence errors in prepare-adoption-pr must leave request pending and ledger clean."""
    from models.selection import ModelSelection

    root = tmp_path / "evidence_fail_closed"
    root.mkdir()
    sel_path = tmp_path / "config" / "model_selection.json"
    initial_sel = ModelSelection(
        champion="def_xg_shrink_challenger",
        candidates=("adaptive_causal_challenger", "club_def_prior_challenger"),
        provisional_active="adaptive_causal_challenger",
        podium_frozen_season="2025-26",
        podium_sealed=True,
    )
    save_model_selection(initial_sel, sel_path)

    manager = AdoptionRequestManager(root)
    req = manager.enqueue_pass(
        slate_id="pilot-fail-closed-order",
        season="2025-26",
        checkpoint_gw=15,
        candidate_name="adaptive_causal_challenger",
        expected_champion="def_xg_shrink_challenger",
        bundle_hash="1" * 64,
        archive_sha256="2" * 64,
        snapshot_archive_path="snapshots/missing_archive.tar.gz",
    )

    with pytest.raises(ValueError, match="Snapshot archive not found"):
        manage_main(
            [
                "prepare-adoption-pr",
                "--evidence-root",
                str(root),
                "--request-id",
                req.request_id,
                "--approval-ref",
                "GH-RUN-MISSING",
                "--actor",
                "JubileeZ",
                "--selection-path",
                str(sel_path),
            ]
        )

    after_req = AdoptionRequestManager(root).get_request(req.request_id)
    assert after_req is not None
    assert after_req.status == "pending_approval"
    assert after_req.approval_ref is None
    assert all(rec.disposition != "approved" for rec in AdoptionLedger(root / "adoption_ledger.jsonl").load_all_records())
    assert load_model_selection(sel_path).champion == "def_xg_shrink_challenger"
    assert not sel_path.with_suffix(".adoption.json").exists()


def test_github_issue_mail_provider_dedupe_reconcile_cli_and_lifecycle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """GitHubIssueMailProvider opens/reconciles one Adoption Review Issue, updates/closes lifecycle, and enforces fail-closed CLI fallback."""
    import httpx

    from backtesting.adoption_transaction import NotificationDispatcher, UnresolvedDeliveryError
    import commands.manage_champion_adoption as mca_mod
    from commands.manage_champion_adoption import GitHubIssueMailProvider

    root = tmp_path / "evidence_gh_issue"
    root.mkdir()
    req = AdoptionRequestManager(root).enqueue_pass(
        slate_id="slate-2026-27",
        season="2026-27",
        checkpoint_gw=15,
        candidate_name="adaptive_causal_challenger",
        expected_champion="def_xg_shrink_challenger",
        bundle_hash="a" * 64,
        archive_sha256="b" * 64,
        snapshot_archive_path="snapshots/gw15.tar.gz",
        net_delta=14.2,
    )
    review_url = "https://github.com/JubileeZ/fpl-jubilee-ascent/actions/runs/777"

    # 1. Direct send creates one issue with label, assignee, marker, summary, and read-only disclaimer
    issues: list[dict[str, object]] = []
    comments: list[tuple[int, str]] = []
    post_count = {"issues": 0}
    fail_mode: dict[str, object] = {"post_502": False, "get_500": False}

    def gh_issue_handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "GET" and path.endswith("/repos/JubileeZ/fpl-jubilee-ascent/issues"):
            if fail_mode["get_500"]:
                return httpx.Response(500, json={"message": "server error"})
            return httpx.Response(200, json=list(issues))
        if request.method == "POST" and path.endswith("/repos/JubileeZ/fpl-jubilee-ascent/issues"):
            post_count["issues"] += 1
            payload = json.loads(request.content.decode("utf-8"))
            num = len(issues) + 1
            issues.append(
                {
                    "number": num,
                    "title": payload["title"],
                    "body": payload["body"],
                    "labels": [{"name": lbl} for lbl in payload.get("labels", [])],
                    "assignees": [{"login": a} for a in payload.get("assignees", [])],
                    "state": "open",
                }
            )
            if fail_mode["post_502"]:
                return httpx.Response(502, text="Bad Gateway")
            return httpx.Response(201, json={"number": num})
        if request.method == "POST" and "/issues/" in path and path.endswith("/comments"):
            num = int(path.split("/issues/")[1].split("/")[0])
            payload = json.loads(request.content.decode("utf-8"))
            comments.append((num, payload["body"]))
            return httpx.Response(201, json={"id": len(comments)})
        if request.method == "PATCH" and "/issues/" in path:
            num = int(path.split("/issues/")[1])
            payload = json.loads(request.content.decode("utf-8"))
            for item in issues:
                if item["number"] == num:
                    item["state"] = payload.get("state", item["state"])
            return httpx.Response(200, json={"number": num, "state": "closed"})
        return httpx.Response(404)

    provider = GitHubIssueMailProvider(
        "JubileeZ/fpl-jubilee-ascent",
        token="tok",
        assignee="JubileeZ",
        transport=httpx.MockTransport(gh_issue_handler),
    )
    msg = NotificationDispatcher.build_message(req, review_url=review_url, recipient="JubileeZ")
    msg_id = provider.send_adoption_notice(msg)
    assert msg_id == "gh-issue-1"
    assert len(issues) == 1
    created = issues[0]
    assert str(created["title"]).startswith("[Champion Adoption Review] adaptive_causal_challenger")
    assert GitHubIssueMailProvider.marker(req.request_id) in str(created["body"])
    assert "never approves or rejects" in str(created["body"]).lower()
    assert created["labels"] == [{"name": "champion-adoption-review"}]
    assert created["assignees"] == [{"login": "JubileeZ"}]

    # 2. Uncertain 502 ack followed by reconcile_and_dispatch finds existing issue without creating a second one
    req2 = AdoptionRequestManager(root).enqueue_pass(
        slate_id="slate-2026-27-b",
        season="2026-27",
        checkpoint_gw=30,
        candidate_name="adaptive_causal_challenger",
        expected_champion="def_xg_shrink_challenger",
        bundle_hash="c" * 64,
        archive_sha256="d" * 64,
        snapshot_archive_path="snapshots/gw30.tar.gz",
    )
    root_reconcile = tmp_path / "evidence_reconcile"
    root_reconcile.mkdir()
    disp = NotificationDispatcher(root_reconcile, provider=provider)
    post_count["issues"] = 0
    fail_mode["post_502"] = True
    rec1 = disp.reconcile_and_dispatch(req2, review_url=review_url, recipient="JubileeZ")
    assert rec1.status == "uncertain"
    assert post_count["issues"] == 1
    fail_mode["post_502"] = False
    rec2 = disp.reconcile_and_dispatch(req2, review_url=review_url, recipient="JubileeZ")
    assert rec2.status == "delivered"
    assert post_count["issues"] == 1
    assert provider.query_delivery_status(req2.request_id) == "delivered"

    # 3. Transient 500 on query_delivery_status fails closed with UnresolvedDeliveryError
    fail_mode["get_500"] = True
    assert provider.query_delivery_status(req2.request_id) == "unknown"
    fail_mode["get_500"] = False
    req3 = AdoptionRequestManager(root).enqueue_pass(
        slate_id="slate-2026-27-d",
        season="2026-27",
        checkpoint_gw=15,
        candidate_name="adaptive_causal_challenger",
        expected_champion="def_xg_shrink_challenger",
        bundle_hash="f" * 64,
    )
    fail_mode["post_502"] = True
    assert disp.reconcile_and_dispatch(req3, review_url=review_url, recipient="JubileeZ").status == "uncertain"
    fail_mode["post_502"] = False
    fail_mode["get_500"] = True
    with pytest.raises(UnresolvedDeliveryError):
        disp.reconcile_and_dispatch(req3, review_url=review_url, recipient="JubileeZ")
    fail_mode["get_500"] = False

    # 4. CLI dispatch-notice routes --github-repo when MAIL_PROVIDER_WEBHOOK_URL unset, and still fails closed when all providers absent
    orig_client = httpx.Client
    monkeypatch.delenv("MAIL_PROVIDER_WEBHOOK_URL", raising=False)
    monkeypatch.setattr(mca_mod, "_retrieve_github_token_in_memory", lambda: "tok")
    monkeypatch.setattr(httpx, "Client", lambda **kw: orig_client(transport=httpx.MockTransport(gh_issue_handler)))
    capsys.readouterr()
    assert (
        manage_main(
            [
                "dispatch-notice",
                "--evidence-root",
                str(root),
                "--request-id",
                req.request_id,
                "--review-url",
                review_url,
                "--github-repo",
                "JubileeZ/fpl-jubilee-ascent",
                "--assignee",
                "JubileeZ",
            ]
        )
        == 0
    )
    disp_out = json.loads(capsys.readouterr().out)
    assert disp_out["status"] == "delivered"

    with pytest.raises(ValueError, match="not configured"):
        manage_main(
            [
                "dispatch-notice",
                "--evidence-root",
                str(root),
                "--request-id",
                req2.request_id,
                "--review-url",
                review_url,
            ]
        )

    # 5. CLI update-review-issue comments open PR, closes on reject/merge, and handles missing issue cleanly
    assert (
        manage_main(
            [
                "update-review-issue",
                "--repo",
                "JubileeZ/fpl-jubilee-ascent",
                "--request-id",
                req.request_id,
                "--comment",
                "PR opened: https://github.com/JubileeZ/fpl-jubilee-ascent/pull/999",
            ]
        )
        == 0
    )
    u1 = json.loads(capsys.readouterr().out)
    assert u1["updated"] is True and u1["closed"] is False and issues[0]["state"] == "open"

    assert (
        manage_main(
            [
                "update-review-issue",
                "--repo",
                "JubileeZ/fpl-jubilee-ascent",
                "--request-id",
                req.request_id,
                "--comment",
                "Merged onto protected main.",
                "--close",
            ]
        )
        == 0
    )
    u2 = json.loads(capsys.readouterr().out)
    assert u2["updated"] is True and u2["closed"] is True and issues[0]["state"] == "closed"

    assert (
        manage_main(
            [
                "update-review-issue",
                "--repo",
                "JubileeZ/fpl-jubilee-ascent",
                "--request-id",
                "req-does-not-exist",
                "--comment",
                "No-op",
                "--close",
            ]
        )
        == 0
    )
    u3 = json.loads(capsys.readouterr().out)
    assert u3["updated"] is False

    # 6. CLI update-review-issue --close-if-terminal skips open pending request and closes expired/invalidated request
    req4 = AdoptionRequestManager(root).enqueue_pass(
        slate_id="slate-2026-27-e",
        season="2026-27",
        checkpoint_gw=15,
        candidate_name="adaptive_causal_challenger",
        expected_champion="def_xg_shrink_challenger",
        bundle_hash="9" * 64,
    )
    msg4 = NotificationDispatcher.build_message(req4, review_url=review_url, recipient="JubileeZ")
    provider.send_adoption_notice(msg4)
    assert issues[-1]["state"] == "open"
    assert (
        manage_main(
            [
                "update-review-issue",
                "--repo",
                "JubileeZ/fpl-jubilee-ascent",
                "--request-id",
                req4.request_id,
                "--evidence-root",
                str(root),
                "--close-if-terminal",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["reason"] == "not_terminal"
    assert issues[-1]["state"] == "open"

    AdoptionRequestManager(root).expire_or_invalidate_request(req4.request_id, reason="request_expired", expired=True)
    assert (
        manage_main(
            [
                "update-review-issue",
                "--repo",
                "JubileeZ/fpl-jubilee-ascent",
                "--request-id",
                req4.request_id,
                "--evidence-root",
                str(root),
                "--close-if-terminal",
            ]
        )
        == 0
    )
    u4 = json.loads(capsys.readouterr().out)
    assert u4["updated"] is True and u4["closed"] is True and issues[-1]["state"] == "closed"


def test_production_preflight_mail_gate_with_github_review_issue(tmp_path: Path) -> None:
    """Preflight passes mail_delivery_and_reconciliation when GitHub Review Issues are enabled & wired, or webhook configured, else fails."""
    from commands.manage_champion_adoption import PROJECT_ROOT, run_production_preflight
    from models.selection import ModelSelection

    # Build a self-contained project_root with Review Issue workflow wiring enabled
    repo_root = tmp_path / "wired_repo"
    wf_dir = repo_root / ".github" / "workflows"
    wf_dir.mkdir(parents=True)
    for wf in (
        "validation-collector.yml",
        "champion-adoption-merge.yml",
        "champion-adoption-pr-checks.yml",
    ):
        (wf_dir / wf).write_text((PROJECT_ROOT / ".github" / "workflows" / wf).read_text(encoding="utf-8"), encoding="utf-8")
    (wf_dir / "champion-adoption-request.yml").write_text(
        "permissions:\n  issues: write\njobs:\n  enqueue-and-notify:\n    concurrency:\n      group: validation-evidence\n"
        "    steps:\n      - run: uv run python -m commands.manage_champion_adoption dispatch-notice --github-repo $REPO\n",
        encoding="utf-8",
    )
    (repo_root / "commands").mkdir()
    (repo_root / "commands" / "produce_validation_evidence.py").write_text(
        "record_exclusion_under_reservation\n", encoding="utf-8"
    )
    cert_dst = repo_root / "docs" / "research" / "sparse-confirmation-certification"
    cert_dst.mkdir(parents=True)
    (cert_dst / "certification_result.json").write_bytes(
        (PROJECT_ROOT / "docs" / "research" / "sparse-confirmation-certification" / "certification_result.json").read_bytes()
    )
    save_model_selection(ModelSelection(champion="def_xg_shrink_challenger", candidates=(), podium_sealed=False), repo_root / "config" / "model_selection.json")
    (repo_root / "config" / "season_lifecycle.json").write_bytes(
        (PROJECT_ROOT / "config" / "season_lifecycle.json").read_bytes()
    )

    base_snap = {
        "api_reachable": True,
        "branch_protection": {"enabled": True, "enforce_admins": True, "required_status_checks": {"strict": True, "contexts": ["verify-adoption-pr"]}},
        "protected_environment": {"exists": True, "required_reviewers": [{"type": "User"}]},
        "repo_settings": {"allow_auto_merge": False, "github_app_configured": True},
        "validation_evidence_branch": {"exists": True, "releases_accessible": True},
        "mail_provider": {"configured": False, "github_issues_enabled": True},
        "variables": {"CHAMPION_ADOPTION_LIVE_ENABLED": "false"},
    }
    snap_gh = tmp_path / "snap_gh.json"
    snap_gh.write_text(json.dumps(base_snap), encoding="utf-8")
    rep_gh = run_production_preflight(repo="JubileeZ/fpl-jubilee-ascent", offline_snapshot_path=snap_gh, project_root=repo_root)
    mail_gate = rep_gh["gates"]["mail_delivery_and_reconciliation"]
    assert mail_gate["passed"] is True
    assert mail_gate["details"]["mode"] == "github_review_issue"

    # Both webhook and github_issues_enabled disabled -> fails closed
    off_snap = dict(base_snap)
    off_snap["mail_provider"] = {"configured": False, "github_issues_enabled": False}
    snap_off = tmp_path / "snap_off.json"
    snap_off.write_text(json.dumps(off_snap), encoding="utf-8")
    rep_off = run_production_preflight(repo="JubileeZ/fpl-jubilee-ascent", offline_snapshot_path=snap_off, project_root=repo_root)
    assert rep_off["gates"]["mail_delivery_and_reconciliation"]["passed"] is False
    assert rep_off["gates"]["mail_delivery_and_reconciliation"]["details"]["mode"] == "unconfigured"


def test_preflight_gate8_and_gate10_integrity_checks(tmp_path: Path) -> None:
    """Gate 8 verifies canonical digests + evaluator_revisions; Gate 10 binds season, protocol_hash, and certification_digest."""
    from backtesting.sparse_certification import EVALUATOR_REVISION_PATHS, compute_canonical_digest
    from commands.manage_champion_adoption import (
        CERTIFICATION_DIGEST_EXPECTED,
        PROJECT_ROOT,
        run_production_preflight,
    )
    from models.selection import ModelSelection

    repo_root = tmp_path / "gate_repo"
    wf_dir = repo_root / ".github" / "workflows"
    wf_dir.mkdir(parents=True)
    for wf in (
        "validation-collector.yml",
        "champion-adoption-request.yml",
        "champion-adoption-merge.yml",
        "champion-adoption-pr-checks.yml",
    ):
        (wf_dir / wf).write_bytes((PROJECT_ROOT / ".github" / "workflows" / wf).read_bytes())
    (repo_root / "commands").mkdir()
    (repo_root / "commands" / "produce_validation_evidence.py").write_text(
        "record_exclusion_under_reservation\n", encoding="utf-8"
    )
    for rel in EVALUATOR_REVISION_PATHS:
        dst = repo_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes((PROJECT_ROOT / rel).read_bytes())

    cert_dst = repo_root / "docs" / "research" / "sparse-confirmation-certification"
    cert_dst.mkdir(parents=True)
    for fname in ("certification_result.json", "preregistration_manifest.json"):
        (cert_dst / fname).write_bytes(
            (PROJECT_ROOT / "docs" / "research" / "sparse-confirmation-certification" / fname).read_bytes()
        )
    (repo_root / "config").mkdir(parents=True, exist_ok=True)
    (repo_root / "config" / "season_lifecycle.json").write_bytes(
        (PROJECT_ROOT / "config" / "season_lifecycle.json").read_bytes()
    )
    save_model_selection(
        ModelSelection(
            champion="def_xg_shrink_challenger",
            candidates=("cand_a",),
            provisional_active="cand_a",
            podium_frozen_season="2026-27",
            podium_sealed=True,
            frozen_protocol_hash="a" * 64,
            frozen_certification_digest=CERTIFICATION_DIGEST_EXPECTED,
        ),
        repo_root / "config" / "model_selection.json",
    )

    snap_path = tmp_path / "snap.json"
    snap_path.write_text(
        json.dumps(
            {
                "api_reachable": True,
                "branch_protection": {
                    "enabled": True,
                    "enforce_admins": True,
                    "required_status_checks": {"strict": True, "contexts": ["verify-adoption-pr"]},
                },
                "protected_environment": {"exists": True, "required_reviewers": [{"type": "User"}]},
                "repo_settings": {"allow_auto_merge": False, "github_app_configured": True},
                "validation_evidence_branch": {"exists": True, "releases_accessible": True},
                "mail_provider": {"configured": False, "github_issues_enabled": True},
                "variables": {"CHAMPION_ADOPTION_LIVE_ENABLED": "false"},
            }
        ),
        encoding="utf-8",
    )

    rep_ok = run_production_preflight(repo="JubileeZ/fpl-jubilee-ascent", offline_snapshot_path=snap_path, project_root=repo_root)
    assert rep_ok["gates"]["certified_protocol"]["passed"] is True
    assert rep_ok["gates"]["certified_protocol"]["details"]["evaluator_revisions_match"] is True
    assert rep_ok["gates"]["sealed_slate_and_operator_signoff"]["passed"] is True

    # Gate 10 rejects mismatched certification_digest or wrong season
    save_model_selection(
        ModelSelection(
            champion="def_xg_shrink_challenger",
            candidates=("cand_a",),
            provisional_active="cand_a",
            podium_frozen_season="2025-26",
            podium_sealed=True,
            frozen_protocol_hash="a" * 64,
            frozen_certification_digest="0" * 64,
        ),
        repo_root / "config" / "model_selection.json",
    )
    rep_bad_g10 = run_production_preflight(repo="JubileeZ/fpl-jubilee-ascent", offline_snapshot_path=snap_path, project_root=repo_root)
    assert rep_bad_g10["gates"]["sealed_slate_and_operator_signoff"]["passed"] is False

    # Gate 8 rejects evaluator_revisions drift even when certification_digest is unchanged
    target_eval = repo_root / "backtesting" / "sparse_certification.py"
    target_eval.write_bytes(target_eval.read_bytes() + b"\n# drift\n")
    rep_drift = run_production_preflight(repo="JubileeZ/fpl-jubilee-ascent", offline_snapshot_path=snap_path, project_root=repo_root)
    assert rep_drift["gates"]["certified_protocol"]["passed"] is False
    assert rep_drift["gates"]["certified_protocol"]["details"]["evaluator_revisions_match"] is False
    assert "backtesting/sparse_certification.py" in rep_drift["gates"]["certified_protocol"]["details"]["drifted_files"]

    # Gate 8 also accepts certified_mode="enforced" when canonical digest and revisions match
    target_eval.write_bytes((PROJECT_ROOT / "backtesting" / "sparse_certification.py").read_bytes())
    cert_res = json.loads((cert_dst / "certification_result.json").read_text(encoding="utf-8"))
    cert_res["certified_mode"] = "enforced"
    summary_body = {
        k: cert_res[k]
        for k in (
            "manifest_digest",
            "parity_passed",
            "tuning",
            "primary_run",
            "fallback_run",
            "retries_used",
            "certified",
            "certified_mode",
            "certification_seed",
            "live_adoption_blocked",
        )
    }
    new_digest = compute_canonical_digest(summary_body)
    cert_res["certification_digest"] = new_digest
    cert_res["certified_protocol_config"]["statistical_early_harm_mode"] = "enforced"
    cert_res["certified_protocol_config"]["certification_digest"] = new_digest
    from backtesting.evidence_statistics import StatisticalProtocolConfig

    cfg_obj = StatisticalProtocolConfig(
        **{
            **cert_res["certified_protocol_config"],
            "required_projection_guards": tuple(cert_res["certified_protocol_config"]["required_projection_guards"]),
            "confirmation_checkpoints": tuple(cert_res["certified_protocol_config"]["confirmation_checkpoints"]),
            "completed_segments": {
                str(cp): tuple((int(lo), int(hi)) for lo, hi in pairs)
                for cp, pairs in cert_res["certified_protocol_config"]["completed_segments"].items()
            },
        }
    )
    cert_res["statistical_protocol_hash"] = cfg_obj.compute_hash()
    (cert_dst / "certification_result.json").write_text(json.dumps(cert_res), encoding="utf-8")

    import commands.manage_champion_adoption as mca
    orig_expected = mca.CERTIFICATION_DIGEST_EXPECTED
    try:
        mca.CERTIFICATION_DIGEST_EXPECTED = new_digest
        rep_enf = run_production_preflight(repo="JubileeZ/fpl-jubilee-ascent", offline_snapshot_path=snap_path, project_root=repo_root)
        assert rep_enf["gates"]["certified_protocol"]["passed"] is True
        assert rep_enf["gates"]["certified_protocol"]["details"]["certified_mode"] == "enforced"
    finally:
        mca.CERTIFICATION_DIGEST_EXPECTED = orig_expected



