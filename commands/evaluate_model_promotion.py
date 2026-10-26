"""Automatic Historical Promotion for registered Model Candidates."""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from clients.env_loader import configure_utf8_stdio, load_env

load_env()
configure_utf8_stdio()

from backtesting.model_evaluation import (
    CandidateComparison,
    build_evidence_record,
    compare_to_reference,
    compare_two_season_gate,
    promote_candidate,
    write_promotion_evidence,
)
from backtesting.promotion import (
    BOOTSTRAP_MIN_P,
    CONFIRMATION_BOOTSTRAP_MIN_P,
    POOLED_BOOTSTRAP_MIN_P,
    PromotionVerdict,
)
from backtesting.walkforward import WalkforwardConfig, run_walkforward_backtest
from commands.backtest import resolve_backtest_data_dir, resolve_seed_processed_dir
from models.selection import DEFAULT_CONFIG_PATH, load_model_selection, save_model_selection

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
):
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
) -> tuple[object, list[CandidateComparison], tuple[Path, Path] | None]:
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
    updated = selection
    promoted = False
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
        if apply and verdict.passed and not promoted:
            updated = promote_candidate(
                updated,
                candidate,
                snapshot_backed=candidate_result.snapshot_backed,
            )
            promoted = True

    evidence_paths = None
    if apply:
        if promoted:
            save_model_selection(updated, config_path)
        record = build_evidence_record(
            selection_before=selection,
            selection_after=updated,
            comparisons=comparisons,
            evaluation_season=snapshot_season or data_dir.parent.name,
            git_commit=_git_commit(),
        )
        evidence_paths = write_promotion_evidence(record, EVIDENCE_DIR)
    return updated, comparisons, evidence_paths


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
) -> tuple[object, list[CandidateComparison], tuple[Path, Path] | None]:
    """Evaluate and optionally apply 2-season gate across Dev and Confirmation seasons (ADR 0064, Ticket #171)."""
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
    updated = selection
    promoted = False
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
        if apply and two_season.passed and not promoted:
            updated = promote_candidate(
                updated,
                candidate,
                snapshot_backed=snapshot_backed,
            )
            promoted = True

    evidence_paths = None
    if apply:
        if promoted:
            save_model_selection(updated, config_path)
        record = build_evidence_record(
            selection_before=selection,
            selection_after=updated,
            comparisons=comparisons,
            evaluation_season="2025-26 + 2024-25",
            git_commit=_git_commit(),
        )
        evidence_paths = write_promotion_evidence(record, EVIDENCE_DIR)
    return updated, comparisons, evidence_paths


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Evaluate and apply Automatic Historical Promotion.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--gw_range", type=str, default="1-38")
    parser.add_argument("--data_dir", type=str, default="data/processed")
    parser.add_argument("--seed_season", type=str, default=None)
    parser.add_argument("--snapshot_root", type=str, default=None)
    parser.add_argument("--season", type=str, default=None)
    parser.add_argument("--require_snapshots", action="store_true")
    parser.add_argument("--apply", action="store_true", help="Update Comparison Slate when gate passes")
    parser.add_argument("--confirmation", action="store_true", help="Confirmation season gate: bootstrap bar 0.65 (ADR 0064)")
    parser.add_argument("--two_season", action="store_true", help="Evaluate 2-season gate (Dev 2025-26 + Conf 2024-25 with pooled stratified bootstrap >= 0.85)")
    args = parser.parse_args(argv)

    start_gw, end_gw = _parse_gw_range(args.gw_range)
    snapshot_root = Path(args.snapshot_root).resolve() if args.snapshot_root else None

    if args.two_season:
        dev_dir = resolve_backtest_data_dir((PROJECT_ROOT / "data" / "processed").resolve())
        conf_dir = resolve_backtest_data_dir((PROJECT_ROOT / "data" / "archive" / "2024-25" / "processed").resolve())
        updated, comparisons, evidence_paths = evaluate_and_apply_two_season(
            config_path=args.config,
            dev_data_dir=dev_dir,
            conf_data_dir=conf_dir,
            start_gw=start_gw,
            end_gw=end_gw,
            dev_seed_season=args.seed_season or "2024-25",
            conf_seed_season="2023-24",
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
    print("AUTOMATIC HISTORICAL PROMOTION")
    print("=" * 60)
    print(f"Champion        : {updated.champion}")
    print(f"Candidates      : {', '.join(updated.candidates) or 'none'}")
    print(f"Promotion status: {updated.promotion_status}")
    for comparison in comparisons:
        outcome = "PASS" if comparison.verdict.passed else "FAIL"
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
