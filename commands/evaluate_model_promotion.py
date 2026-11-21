"""Model Promotion Evaluation and Adoption (ADR 0066)."""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import tempfile
from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from clients.env_loader import configure_utf8_stdio, load_env

load_env()
configure_utf8_stdio()

from backtesting.confirmation_registry import ConfirmationRegistry
from backtesting.model_evaluation import (
    CandidateComparison,
    build_evidence_record,
    compare_to_reference,
    compare_two_season_gate,
    promote_candidate,
    write_promotion_evidence,
)
from backtesting.portable_evidence import (
    AdoptionLedger,
    ExclusionLedger,
    compute_serving_model_closure,
    verify_chain_extends,
    verify_checkpoint_snapshot_archive,
)
from backtesting.promotion import (
    BOOTSTRAP_MIN_P,
    CONFIRMATION_BOOTSTRAP_MIN_P,
    POOLED_BOOTSTRAP_MIN_P,
    PromotionVerdict,
)
from backtesting.promotion_evidence import (
    CHECKPOINT_EVIDENCE_V2,
    CHECKPOINT_EVIDENCE_VERSION,
    content_hash,
    evaluate_checkpoint_payload,
    evaluate_verified_checkpoint_payload,
    verify_checkpoint_recommendation_bundle,
    verify_recommendation_bundle,
    write_checkpoint_recommendation_bundle,
    write_recommendation_bundle,
)
from backtesting.season_rules import SeasonLifecycle, SeasonRules, rollover_season_lifecycle
from backtesting.walkforward import WalkforwardConfig, WalkforwardResult, run_walkforward_backtest
from commands.backtest import resolve_backtest_data_dir, resolve_seed_processed_dir
from models.selection import DEFAULT_CONFIG_PATH, ModelSelection, load_model_selection, save_model_selection

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = PROJECT_ROOT / "data" / "reports" / "promotion_evidence"


def _parse_gw_range(gw_range: str) -> tuple[int, int]:
    start_gw, end_gw = map(int, gw_range.split("-"))
    return start_gw, end_gw


def _git_commit() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _run_model(
    *,
    model_name: str,
    data_dir: Path,
    start_gw: int,
    end_gw: int,
    seed_season: str | None,
    snapshot_root: Path | None,
    snapshot_season: str | None,
    require_snapshots: bool,
) -> WalkforwardResult:
    seed_processed_dir = resolve_seed_processed_dir(data_dir, model_name, seed_season)
    return run_walkforward_backtest(
        WalkforwardConfig(
            model_name=model_name,
            data_dir=data_dir,
            start_gw=start_gw,
            end_gw=end_gw,
            seed_processed_dir=seed_processed_dir,
            seed_season=seed_season,
            snapshot_root=snapshot_root,
            snapshot_season=snapshot_season,
            require_snapshots=require_snapshots,
            eval_target="blended_points",
        )
    )


def _stage_evidence_and_recommendation(
    *,
    selection: ModelSelection,
    passing_candidate: str | None,
    comparisons: list[CandidateComparison],
    evaluation_season: str,
    apply: bool,
    commit_hash: str | None = None,
) -> tuple[ModelSelection, list[CandidateComparison], tuple[Path, Path] | None]:
    updated = selection
    evidence_paths = None
    if apply:
        record = build_evidence_record(
            selection_before=selection,
            selection_after=updated,
            comparisons=comparisons,
            evaluation_season=evaluation_season,
            git_commit=commit_hash or _git_commit(),
        )
        evidence_paths = write_promotion_evidence(record, EVIDENCE_DIR)
    return updated, comparisons, evidence_paths


def evaluate_and_apply(
    *,
    config_path: Path,
    data_dir: Path,
    start_gw: int,
    end_gw: int,
    seed_season: str | None,
    snapshot_root: Path | None,
    snapshot_season: str | None,
    require_snapshots: bool,
    apply: bool,
    bootstrap_min_p: float = BOOTSTRAP_MIN_P,
) -> tuple[ModelSelection, list[CandidateComparison], tuple[Path, Path] | None]:
    selection = load_model_selection(config_path)
    champion_result = _run_model(
        model_name=selection.champion,
        data_dir=data_dir,
        start_gw=start_gw,
        end_gw=end_gw,
        seed_season=seed_season,
        snapshot_root=snapshot_root,
        snapshot_season=snapshot_season,
        require_snapshots=require_snapshots,
    )

    comparisons: list[CandidateComparison] = []
    passing_candidate: str | None = None
    for candidate in selection.candidates:
        candidate_result = _run_model(
            model_name=candidate,
            data_dir=data_dir,
            start_gw=start_gw,
            end_gw=end_gw,
            seed_season=seed_season,
            snapshot_root=snapshot_root,
            snapshot_season=snapshot_season,
            require_snapshots=require_snapshots,
        )
        verdict = compare_to_reference(champion_result, candidate_result, bootstrap_min_p=bootstrap_min_p)
        comparisons.append(
            CandidateComparison(
                candidate=candidate,
                verdict=verdict,
                snapshot_backed=candidate_result.snapshot_backed,
            )
        )
        if verdict.passed and passing_candidate is None:
            passing_candidate = candidate

    evaluation_season = snapshot_season or data_dir.parent.name
    return _stage_evidence_and_recommendation(
        selection=selection,
        passing_candidate=passing_candidate,
        comparisons=comparisons,
        evaluation_season=evaluation_season,
        apply=apply,
    )


def evaluate_and_apply_two_season(
    *,
    config_path: Path,
    dev_data_dir: Path,
    conf_data_dir: Path,
    start_gw: int,
    end_gw: int,
    dev_seed_season: str | None = "2024-25",
    conf_seed_season: str | None = "2023-24",
    snapshot_root: Path | None = None,
    require_snapshots: bool = False,
    apply: bool = False,
    dev_min_p: float = BOOTSTRAP_MIN_P,
    conf_min_p: float = CONFIRMATION_BOOTSTRAP_MIN_P,
    pooled_min_p: float = POOLED_BOOTSTRAP_MIN_P,
) -> tuple[ModelSelection, list[CandidateComparison], tuple[Path, Path] | None]:
    """Evaluate and optionally apply 2-season gate across Dev and Confirmation seasons (ADR 0064)."""
    selection = load_model_selection(config_path)
    dev_champ = _run_model(
        model_name=selection.champion,
        data_dir=dev_data_dir,
        start_gw=start_gw,
        end_gw=end_gw,
        seed_season=dev_seed_season,
        snapshot_root=snapshot_root,
        snapshot_season="2025-26",
        require_snapshots=require_snapshots,
    )
    conf_champ = _run_model(
        model_name=selection.champion,
        data_dir=conf_data_dir,
        start_gw=start_gw,
        end_gw=end_gw,
        seed_season=conf_seed_season,
        snapshot_root=snapshot_root,
        snapshot_season="2024-25",
        require_snapshots=require_snapshots,
    )

    comparisons: list[CandidateComparison] = []
    passing_candidate: str | None = None
    for candidate in selection.candidates:
        dev_cand = _run_model(
            model_name=candidate,
            data_dir=dev_data_dir,
            start_gw=start_gw,
            end_gw=end_gw,
            seed_season=dev_seed_season,
            snapshot_root=snapshot_root,
            snapshot_season="2025-26",
            require_snapshots=require_snapshots,
        )
        conf_cand = _run_model(
            model_name=candidate,
            data_dir=conf_data_dir,
            start_gw=start_gw,
            end_gw=end_gw,
            seed_season=conf_seed_season,
            snapshot_root=snapshot_root,
            snapshot_season="2024-25",
            require_snapshots=require_snapshots,
        )
        two_season = compare_two_season_gate(
            dev_champ,
            dev_cand,
            conf_champ,
            conf_cand,
            dev_min_p=dev_min_p,
            conf_min_p=conf_min_p,
            pooled_min_p=pooled_min_p,
        )
        snapshot_backed = dev_cand.snapshot_backed and conf_cand.snapshot_backed
        dev_v = two_season.dev_verdict
        effective_verdict = dev_v if two_season.passed else PromotionVerdict(
            passed=False,
            eval_target=dev_v.eval_target,
            primary_metric=dev_v.primary_metric,
            combined_primary_delta=dev_v.combined_primary_delta,
            min_effect=dev_v.min_effect,
            bootstrap_p=two_season.pooled_bootstrap_p,
            segment_wins=dev_v.segment_wins,
            segment_guardrails_passed=dev_v.segment_guardrails_passed,
            guardrails_passed=dev_v.guardrails_passed,
            active_guardrails_passed=dev_v.active_guardrails_passed,
            reasons=two_season.reasons,
        )
        comparisons.append(
            CandidateComparison(
                candidate=candidate,
                verdict=effective_verdict,
                snapshot_backed=snapshot_backed,
            )
        )
        if two_season.passed and passing_candidate is None:
            passing_candidate = candidate

    return _stage_evidence_and_recommendation(
        selection=selection,
        passing_candidate=passing_candidate,
        comparisons=comparisons,
        evaluation_season="2025-26 + 2024-25",
        apply=apply,
    )


def adopt_champion(
    bundle_path: Path | str,
    *,
    config_path: Path | None = None,
    approval_ref: str | None = None,
    expected_current_champion: str | None = None,
    candidate_name: str | None = None,
    approved_bundle_hash: str | None = None,
    snapshot_archive_path: Path | str | None = None,
    expected_archive_sha256: str | None = None,
    canonical_registry_path: Path | str | None = None,
    canonical_exclusions_path: Path | str | None = None,
    adoption_ledger_path: Path | str | None = None,
    request_id: str | None = None,
    slate_id: str | None = None,
    approved_commit_sha: str | None = None,
) -> ModelSelection:
    """Explicitly adopt an approved candidate as the new Model Champion with human approval."""
    if not approval_ref or not approval_ref.strip():
        raise ValueError("Cannot adopt candidate: missing required human approval reference")
    if not expected_current_champion:
        raise ValueError("Cannot adopt candidate: explicit expected current Champion required")
    if not approved_bundle_hash:
        raise ValueError("Cannot adopt candidate: exact approved bundle hash required")

    bundle_file = Path(bundle_path)
    is_archive_bundle = str(bundle_path).endswith((".tar.gz", ".tgz"))
    archive_target = (
        Path(snapshot_archive_path)
        if snapshot_archive_path is not None
        else (bundle_file if is_archive_bundle else None)
    )
    archive_sha256: str | None = None
    if archive_target is not None:
        verified_snap = verify_checkpoint_snapshot_archive(
            archive_target,
            expected_archive_sha256=expected_archive_sha256,
            expected_champion=expected_current_champion,
            canonical_registry_path=canonical_registry_path,
            canonical_exclusions_path=canonical_exclusions_path,
        )
        data: dict[str, Any] = dict(verified_snap["bundle"])
        archive_sha256 = str(verified_snap["archive_sha256"])
    else:
        if expected_archive_sha256 is not None:
            raise ValueError("Cannot verify expected_archive_sha256 without a snapshot archive")
        raw_bundle: dict[str, Any] = {}
        if bundle_file.is_file():
            try:
                loaded = json.loads(bundle_file.read_bytes())
                if isinstance(loaded, dict):
                    raw_bundle = loaded
            except (OSError, ValueError):
                raw_bundle = {}
        if raw_bundle.get("version") in (CHECKPOINT_EVIDENCE_VERSION, CHECKPOINT_EVIDENCE_V2):
            data = verify_checkpoint_recommendation_bundle(bundle_path, require_finalized=True)
        else:
            data = verify_recommendation_bundle(bundle_path, require_finalized=True)

        if canonical_registry_path is not None and data.get("request_path"):
            req_file = (bundle_file.parent / str(data["request_path"])).resolve()
            if req_file.is_file():
                req_payload = json.loads(req_file.read_bytes())
                if req_payload.get("registry_path"):
                    snap_reg = ConfirmationRegistry((bundle_file.parent / str(req_payload["registry_path"])).resolve())
                    canon_reg = ConfirmationRegistry(canonical_registry_path)
                    verify_chain_extends(snap_reg.load_all_records(), canon_reg.load_all_records())
                    att_id = data.get("confirmation_attempt_id")
                    if att_id:
                        latest_canon = canon_reg.get_attempt(str(att_id))
                        if latest_canon is None or latest_canon.status in ("withdrawn", "invalidated"):
                            raise ValueError(f"Canonical registry invalidated or withdrew attempt '{att_id}'")

    if approved_bundle_hash != data["bundle_hash"]:
        raise ValueError("Human approval refers to a different evidence bundle hash")
    if data["scientific_verdict"] != "pass" or data["execution_status"] != "complete" or not data["empirical_admission"]:
        raise ValueError("Cannot adopt candidate: complete empirical scientific pass required")
    cand_name = str(data.get("recommended_champion") or data["candidate_name"])
    if candidate_name is not None and candidate_name != cand_name:
        raise ValueError("Candidate override differs from approved evidence")

    selection_path = config_path or DEFAULT_CONFIG_PATH
    current_sel = load_model_selection(selection_path)

    if canonical_exclusions_path is not None:
        canon_excl = ExclusionLedger(canonical_exclusions_path)
        if archive_target is None and bundle_file.is_file():
            local_excl_file = bundle_file.parent / "exclusions.jsonl"
            if local_excl_file.is_file():
                verify_chain_extends(
                    ExclusionLedger(local_excl_file).load_all_records(),
                    canon_excl.load_all_records(),
                )
        if canon_excl.is_candidate_excluded(cand_name, slate_id=slate_id, season=current_sel.podium_frozen_season):
            raise ValueError(f"Candidate '{cand_name}' was excluded in canonical ExclusionLedger")
    elif archive_target is None and bundle_file.is_file():
        local_excl_file = bundle_file.parent / "exclusions.jsonl"
        if local_excl_file.is_file() and ExclusionLedger(local_excl_file).is_candidate_excluded(
            cand_name, slate_id=slate_id, season=current_sel.podium_frozen_season
        ):
            raise ValueError(f"Candidate '{cand_name}' is excluded in ExclusionLedger")

    if data.get("version") == CHECKPOINT_EVIDENCE_V2:
        possible_provisional = dict.fromkeys((current_sel.provisional_active, None, *current_sel.candidates))
        valid_sel_hashes = {
            content_hash(asdict(replace(current_sel, provisional_active=pa)))
            for pa in possible_provisional
            if pa != current_sel.champion
        }
        if not current_sel.podium_sealed or data.get("selection_sha256") not in valid_sel_hashes:
            raise ValueError("Current sealed podium differs from the approved checkpoint selection")

    if current_sel.champion != expected_current_champion or data["former_champion"] != expected_current_champion:
        raise ValueError(
            f"Current Champion mismatch: expected '{expected_current_champion}', found '{current_sel.champion}'"
        )
    if cand_name == current_sel.champion:
        raise ValueError(f"Candidate '{cand_name}' is already the active Model Champion")
    if cand_name not in current_sel.candidates:
        raise ValueError("Approved candidate is absent from current Comparison Slate")

    serving_closure_hash: str | None = data.get("serving_model_closure_hash")
    if serving_closure_hash is not None:
        closure = compute_serving_model_closure((current_sel.champion, *current_sel.candidates))
        if closure.serving_model_closure_hash != serving_closure_hash:
            raise ValueError("Current serving model closure differs from approved evidence")
        if data.get("model_runtime_bindings") is not None and closure.model_runtime_bindings != data["model_runtime_bindings"]:
            raise ValueError("Current model runtime bindings differ from approved evidence")

    updated = promote_candidate(current_sel, cand_name, snapshot_backed=False)
    adopted_at_utc = datetime.now(UTC).isoformat()
    receipt: dict[str, Any] = {
        "version": 1,
        "request_id": request_id,
        "slate_id": slate_id,
        "bundle_hash": approved_bundle_hash,
        "archive_sha256": archive_sha256,
        "protocol_hash": data["protocol_hash"],
        "serving_model_closure_hash": serving_closure_hash,
        "approval_ref": approval_ref,
        "approved_commit_sha": approved_commit_sha,
        "adopted_at_utc": adopted_at_utc,
        "former_champion": current_sel.champion,
        "candidate_name": cand_name,
        "selection_before": {
            "champion": current_sel.champion,
            "candidates": list(current_sel.candidates),
            "promotion_status": current_sel.promotion_status,
            "schema_version": current_sel.schema_version,
            "provisional_active": current_sel.provisional_active,
            "podium_frozen_season": current_sel.podium_frozen_season,
            "podium_sealed": current_sel.podium_sealed,
        },
        "selection_after": {
            "champion": updated.champion,
            "candidates": list(updated.candidates),
            "promotion_status": updated.promotion_status,
            "schema_version": updated.schema_version,
            "provisional_active": updated.provisional_active,
            "podium_frozen_season": updated.podium_frozen_season,
            "podium_sealed": updated.podium_sealed,
        },
    }
    receipt_path = selection_path.with_suffix(".adoption.json")
    selection_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=selection_path.parent, suffix=".selection.tmp", delete=False) as tmp_sel:
        temp_selection_path = Path(tmp_sel.name)
    with tempfile.NamedTemporaryFile(dir=selection_path.parent, suffix=".adoption.tmp", delete=False) as tmp_rec:
        temp_receipt_path = Path(tmp_rec.name)
    try:
        save_model_selection(updated, temp_selection_path)
        temp_receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        if load_model_selection(selection_path) != current_sel:
            raise ValueError("Current Champion configuration changed during adoption")
        os.replace(temp_selection_path, selection_path)
        os.replace(temp_receipt_path, receipt_path)
    finally:
        temp_selection_path.unlink(missing_ok=True)
        temp_receipt_path.unlink(missing_ok=True)

    if adoption_ledger_path is not None:
        AdoptionLedger(adoption_ledger_path).record_disposition(
            request_id=request_id or f"adopt-{approved_bundle_hash[:12]}",
            slate_id=slate_id or (current_sel.podium_frozen_season or "default-slate"),
            season=str(current_sel.podium_frozen_season or data.get("season") or "unknown"),
            checkpoint_gw=int(data.get("checkpoint_gw", 38)),
            candidate_name=cand_name,
            expected_champion=current_sel.champion,
            bundle_hash=approved_bundle_hash,
            disposition="adopted",
            actor=approval_ref,
            approval_ref=approval_ref,
            reason="Adopted as Confirmed Champion",
            recorded_at=adopted_at_utc,
        )

    logger.info(
        "Successfully adopted candidate '%s' as Model Champion (approval: %s, former: %s)",
        cand_name,
        approval_ref,
        current_sel.champion,
    )
    return updated


def evaluate_checkpoint_request(request_path: Path | str) -> dict[str, Any]:
    """Read-only ADR 0069 GW15/GW30/GW38 checkpoint evaluator from a retained JSON request."""
    path = Path(request_path).resolve()
    payload = json.loads(path.read_bytes())
    if payload.get("version") == CHECKPOINT_EVIDENCE_V2:
        result, _ = evaluate_verified_checkpoint_payload(path.parent, payload)
    else:
        raw_sel = payload.get("selection_path")
        selection = load_model_selection((path.parent / raw_sel).resolve() if raw_sel else None)
        result, _ = evaluate_checkpoint_payload(payload, selection)
    return {
        "checkpoint_gw": result.checkpoint_gw,
        "num_finalists": result.num_finalists,
        "alpha_spent": result.alpha_spent,
        "action": result.action,
        "recommended_champion": result.recommended_champion,
        "next_provisional_active": result.next_provisional_active,
        "requires_manual_adopt": result.requires_manual_adopt,
        "reasons": list(result.reasons),
        "outcomes": {
            cand: {
                "net_delta": out.net_delta,
                "mean_delta": out.mean_delta,
                "p_value_superiority": out.hac_result.p_value_superiority,
                "p_value_harm": out.hac_result.p_value_harm,
                "one_sided_lower": out.hac_result.one_sided_lower,
                "early_harm_triggered": out.early_harm.triggered,
                "guards_passed": out.guards_passed,
                "superior": out.superior,
            }
            for cand, out in result.outcomes.items()
        },
    }


def perform_annual_rollover(
    *,
    new_season: str,
    gameweeks_df: Any = None,
    bootstrap_payload: dict[str, Any] | None = None,
    lifecycle_path: Path | None = None,
    selection_path: Path | None = None,
    new_rules: SeasonRules | None = None,
    persist: bool = True,
) -> tuple[SeasonLifecycle, ModelSelection]:
    """Execute ADR 0069 summer rollover: rotate lifecycle and clear unconfirmed provisional state."""
    current_sel = load_model_selection(selection_path)
    new_lifecycle = rollover_season_lifecycle(
        new_season=new_season,
        gameweeks_df=gameweeks_df,
        bootstrap_payload=bootstrap_payload,
        lifecycle_path=lifecycle_path,
        new_rules=new_rules,
        persist=persist,
    )
    updated_sel = ModelSelection(
        champion=current_sel.champion,
        candidates=current_sel.candidates,
        promotion_status=current_sel.promotion_status,
        schema_version=current_sel.schema_version,
        provisional_active=None,
        podium_frozen_season=None,
        podium_sealed=False,
    )
    if persist:
        save_model_selection(updated_sel, selection_path)
    return new_lifecycle, updated_sel


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Evaluate candidate models and manage manual promotion adoption.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--gw_range", type=str, default="1-38")
    parser.add_argument("--data_dir", type=str, default="data/processed")
    parser.add_argument("--seed_season", type=str, default=None)
    parser.add_argument("--snapshot_root", type=str, default=None)
    parser.add_argument("--season", type=str, default=None)
    parser.add_argument("--require_snapshots", action="store_true")
    parser.add_argument("--apply", action="store_true", help="Produce evidence record for evaluation (read-only for Champion config)")
    parser.add_argument("--confirmation", action="store_true", help="Confirmation season gate: bootstrap bar 0.65 (ADR 0064)")
    parser.add_argument("--two_season", action="store_true", help="Evaluate 2-season gate (Dev 2025-26 + Conf 2024-25 with pooled stratified bootstrap >= 0.85)")
    parser.add_argument("--confirmation_data_dir", type=str, default=None, help="Confirmation season data directory for 2-season evaluation")
    parser.add_argument("--confirmation_seed_season", type=str, default=None, help="Confirmation seed season")
    parser.add_argument("--adopt", type=Path, default=None, help="Explicitly adopt a candidate from verified evidence bundle")
    parser.add_argument("--approval_ref", type=str, default=None, help="Human approval reference for manual adoption")
    parser.add_argument("--expected_champion", type=str, default=None, help="Expected current champion name for safe adoption")
    parser.add_argument("--bundle_hash", type=str, default=None, help="Exact evidence bundle hash approved by human")
    parser.add_argument("--snapshot_archive", type=Path, default=None, help="Immutable checkpoint snapshot archive (.tar.gz)")
    parser.add_argument("--archive_sha256", type=str, default=None, help="Expected SHA-256 of snapshot archive")
    parser.add_argument("--canonical_registry", type=Path, default=None, help="Canonical registry.jsonl for chain extension check")
    parser.add_argument("--canonical_exclusions", type=Path, default=None, help="Canonical exclusions.jsonl for eligibility check")
    parser.add_argument("--adoption_ledger", type=Path, default=None, help="Adoption ledger jsonl to record adopted disposition")
    parser.add_argument("--request_id", type=str, default=None, help="Durable adoption request identifier")
    parser.add_argument("--slate_id", type=str, default=None, help="Frozen comparison slate identifier")
    parser.add_argument("--approved_commit_sha", type=str, default=None, help="Exact approved commit SHA")
    parser.add_argument("--evidence_request", type=Path, default=None, help="Reconstruct final recommendation from registered retained replay evidence")
    parser.add_argument("--checkpoint_request", type=Path, default=None, help="Evaluate ADR 0069 GW15/GW30/GW38 checkpoint request (read-only)")
    parser.add_argument("--output_bundle", type=Path, default=None, help="Verified bundle destination alongside retained request")
    args = parser.parse_args(argv)

    if args.adopt is not None:
        if not args.approval_ref:
            print("[ERROR] Manual adoption requires --approval_ref <ref>", file=sys.stderr)
            sys.exit(1)
        try:
            updated = adopt_champion(
                bundle_path=args.adopt,
                config_path=args.config,
                approval_ref=args.approval_ref,
                expected_current_champion=args.expected_champion,
                approved_bundle_hash=args.bundle_hash,
                snapshot_archive_path=args.snapshot_archive,
                expected_archive_sha256=args.archive_sha256,
                canonical_registry_path=args.canonical_registry,
                canonical_exclusions_path=args.canonical_exclusions,
                adoption_ledger_path=args.adoption_ledger,
                request_id=args.request_id,
                slate_id=args.slate_id,
                approved_commit_sha=args.approved_commit_sha,
            )
            print("\n" + "=" * 60)
            print("MANUAL CHAMPION ADOPTION COMPLETED")
            print("=" * 60)
            print(f"New Champion    : {updated.champion}")
            print(f"Candidates      : {', '.join(updated.candidates) or 'none'}")
            print(f"Approval Ref    : {args.approval_ref}")
            print("=" * 60 + "\n")
            return
        except Exception as exc:
            print(f"[ERROR] Adoption failed: {exc}", file=sys.stderr)
            sys.exit(1)

    if args.evidence_request is not None:
        output = args.output_bundle or args.evidence_request.with_name("recommendation_bundle.json")
        bundle = write_recommendation_bundle(args.evidence_request, output)
        print(f"Scientific verdict: {bundle['scientific_verdict']}\nBundle hash: {bundle['bundle_hash']}\nEvidence bundle: {output}")
        return

    if args.checkpoint_request is not None:
        if args.output_bundle is not None:
            bundle = write_checkpoint_recommendation_bundle(args.checkpoint_request, args.output_bundle)
            print(json.dumps(bundle, indent=2))
            return
        summary = evaluate_checkpoint_request(args.checkpoint_request)
        print(json.dumps(summary, indent=2))
        return

    if args.apply:
        print("[NOTICE] --apply in evaluation is read-only for Model Champion. Evidence is recorded; selection config is untouched.")
    print("[NOTICE] Legacy proxy evaluation is diagnostic only. Final scientific verdict: inconclusive; registered rolling evidence required via --evidence_request.")

    start_gw, end_gw = _parse_gw_range(args.gw_range)
    snapshot_root = Path(args.snapshot_root).resolve() if args.snapshot_root else None

    if args.two_season or args.confirmation_data_dir:
        if args.data_dir != "data/processed":
            dev_dir = (PROJECT_ROOT / args.data_dir).resolve()
        else:
            default_dev = (PROJECT_ROOT / "data" / "archive" / "2025-26" / "processed").resolve()
            dev_dir = default_dev if default_dev.exists() else resolve_backtest_data_dir((PROJECT_ROOT / args.data_dir).resolve())

        if args.confirmation_data_dir:
            raw_conf = Path(args.confirmation_data_dir)
            conf_dir = raw_conf.resolve() if raw_conf.is_absolute() else (PROJECT_ROOT / raw_conf).resolve()
        else:
            conf_default = (PROJECT_ROOT / "data" / "archive" / "2024-25" / "processed").resolve()
            conf_dir = conf_default if conf_default.exists() else resolve_backtest_data_dir(conf_default)

        conf_seed = args.confirmation_seed_season or "2023-24"
        updated, comparisons, evidence_paths = evaluate_and_apply_two_season(
            config_path=args.config,
            dev_data_dir=dev_dir,
            conf_data_dir=conf_dir,
            start_gw=start_gw,
            end_gw=end_gw,
            dev_seed_season=args.seed_season or "2024-25",
            conf_seed_season=conf_seed,
            snapshot_root=snapshot_root,
            require_snapshots=args.require_snapshots,
            apply=args.apply,
        )
    else:
        data_dir = resolve_backtest_data_dir((PROJECT_ROOT / args.data_dir).resolve())
        snapshot_season = args.season or (data_dir.parent.name if data_dir.parent.name != "data" else None)

        seed_season = args.seed_season
        if seed_season is None and args.confirmation and snapshot_season in ("2024-25", None):
            seed_season = "2023-24"

        updated, comparisons, evidence_paths = evaluate_and_apply(
            config_path=args.config,
            data_dir=data_dir,
            start_gw=start_gw,
            end_gw=end_gw,
            seed_season=seed_season,
            snapshot_root=snapshot_root,
            snapshot_season=snapshot_season,
            require_snapshots=args.require_snapshots,
            apply=args.apply,
            bootstrap_min_p=CONFIRMATION_BOOTSTRAP_MIN_P if args.confirmation else BOOTSTRAP_MIN_P,
        )

    print("\n" + "=" * 60)
    print("LEGACY MODEL DIAGNOSTICS (NO PROMOTION AUTHORITY)")
    print("=" * 60)
    print(f"Champion        : {updated.champion}")
    print(f"Candidates      : {', '.join(updated.candidates) or 'none'}")
    print(f"Promotion status: {updated.promotion_status}")
    for comparison in comparisons:
        outcome = "SCREEN_PASS" if comparison.verdict.passed else "SCREEN_NOT_PASSED"
        verdict = comparison.verdict
        boot = "n/a" if verdict.bootstrap_p is None else f"{verdict.bootstrap_p:.3f}"
        print(
            f"- {comparison.candidate}: {outcome} (delta {verdict.combined_primary_delta:+.4f}, "
            f"min {verdict.min_effect:.4f}, segs {verdict.segment_wins}/3, boot P {boot})"
        )
        if comparison.verdict.reasons:
            print(f"  reasons: {', '.join(comparison.verdict.reasons)}")
    if evidence_paths:
        print(f"Evidence JSON   : {evidence_paths[0]}")
        print(f"Evidence Markdown : {evidence_paths[1]}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
