"""Compare models and apply Automatic Historical Promotion."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from backtesting.metrics import evaluate_predictions, formation_xi_regret_by_gameweek
from backtesting.promotion import (
    BOOTSTRAP_MIN_P,
    CONFIRMATION_BOOTSTRAP_MIN_P,
    POOLED_BOOTSTRAP_MIN_P,
    PromotionVerdict,
    TwoSeasonGateVerdict,
    compute_playable_pool_metrics,
    evaluate_historical_promotion_gate,
    evaluate_two_season_gate,
    identify_active_gameweeks,
    metrics_by_season_window,
    primary_metric_name,
)
from backtesting.walkforward import WalkforwardResult
from models.selection import ModelSelection


@dataclass(frozen=True)
class CandidateComparison:
    candidate: str
    verdict: PromotionVerdict
    snapshot_backed: bool


def promote_candidate(selection: ModelSelection, candidate: str, *, snapshot_backed: bool) -> ModelSelection:
    if candidate == selection.champion:
        raise ValueError("Cannot promote the current Model Champion")
    former_champion = selection.champion
    candidates = [name for name in selection.candidates if name != candidate]
    candidates = [former_champion, *candidates]
    return ModelSelection(
        champion=candidate,
        candidates=tuple(candidates[:2]),
        promotion_status="validated" if snapshot_backed else "provisional",
        schema_version=selection.schema_version,
    )


def replace_candidate(selection: ModelSelection, incoming: str, outgoing: str) -> ModelSelection:
    candidates = [name for name in selection.candidates if name != outgoing]
    if incoming not in candidates:
        candidates.append(incoming)
    return ModelSelection(
        champion=selection.champion,
        candidates=tuple(candidates[:2]),
        promotion_status=selection.promotion_status,
        schema_version=selection.schema_version,
    )


def _attach_playable_metrics(
    window_dict: dict[str, Any], playable_metrics: dict[str, Any]
) -> None:
    if playable_metrics:
        window_dict["playable_mae"] = playable_metrics.get("mae")
        window_dict["playable_bias"] = playable_metrics.get("bias")
        if "sample_count" in playable_metrics:
            window_dict["playable_count"] = playable_metrics["sample_count"]


def _paired_regret_deltas(
    reference_df: pd.DataFrame,
    candidate_df: pd.DataFrame,
    *,
    primary_target: str,
    active_gws: list[int],
    all_gws: set[int],
) -> tuple[list[float], list[float] | None]:
    paired = pd.concat(
        [
            formation_xi_regret_by_gameweek(reference_df, target_column=primary_target).rename("champion"),
            formation_xi_regret_by_gameweek(candidate_df, target_column=primary_target).rename("candidate"),
        ],
        axis=1,
        join="inner",
    ).sort_index()
    gw_deltas = (paired["champion"] - paired["candidate"]).tolist()
    active_gw_deltas = None
    if active_gws and set(active_gws) != all_gws:
        paired_active = paired.loc[paired.index.isin(active_gws)]
        active_gw_deltas = (paired_active["champion"] - paired_active["candidate"]).tolist()
    return gw_deltas, active_gw_deltas


def compare_to_reference(
    reference: WalkforwardResult,
    candidate: WalkforwardResult,
    *,
    primary_target: str = "blended_points",
    bootstrap_min_p: float = BOOTSTRAP_MIN_P,
    segment_tolerances: Mapping[str, float] | None = None,
) -> PromotionVerdict:
    reference_windows = {
        target: (
            metrics_by_season_window(reference.df_eval, target_column=target)["combined"],
            metrics_by_season_window(candidate.df_eval, target_column=target)["combined"],
        )
        for target in ("actual_points", "process_points")
        if target != primary_target
        and target in reference.df_eval.columns
        and target in candidate.df_eval.columns
    }
    champion_windows = metrics_by_season_window(reference.df_eval, target_column=primary_target)
    candidate_windows = metrics_by_season_window(candidate.df_eval, target_column=primary_target)

    champ_playable, cand_playable = compute_playable_pool_metrics(
        reference.df_eval, candidate.df_eval, target_column=primary_target
    )
    _attach_playable_metrics(champion_windows["combined"], champ_playable)
    _attach_playable_metrics(candidate_windows["combined"], cand_playable)

    # Active-window guardrails (ADR 0064)
    active_gws = identify_active_gameweeks(reference.df_eval, candidate.df_eval)
    all_gws = set(reference.df_eval["gameweek"].unique())
    if not active_gws or set(active_gws) == all_gws:
        champion_windows["active"] = dict(champion_windows["combined"])
        candidate_windows["active"] = dict(candidate_windows["combined"])
    else:
        ref_active = reference.df_eval[reference.df_eval["gameweek"].isin(active_gws)]
        cand_active = candidate.df_eval[candidate.df_eval["gameweek"].isin(active_gws)]
        active_champ_metrics = evaluate_predictions(ref_active, target_column=primary_target)
        active_cand_metrics = evaluate_predictions(cand_active, target_column=primary_target)
        champ_play_act, cand_play_act = compute_playable_pool_metrics(
            ref_active, cand_active, target_column=primary_target
        )
        _attach_playable_metrics(active_champ_metrics, champ_play_act)
        _attach_playable_metrics(active_cand_metrics, cand_play_act)
        champion_windows["active"] = active_champ_metrics
        candidate_windows["active"] = active_cand_metrics

    gw_deltas = None
    active_gw_deltas = None
    if primary_metric_name(champion_windows["combined"]) == "decision_regret":
        gw_deltas, active_gw_deltas = _paired_regret_deltas(
            reference.df_eval,
            candidate.df_eval,
            primary_target=primary_target,
            active_gws=active_gws,
            all_gws=all_gws,
        )

    return evaluate_historical_promotion_gate(
        champion_windows,
        candidate_windows,
        eval_target=primary_target,
        reference_windows=reference_windows or None,
        gw_primary_deltas=gw_deltas,
        bootstrap_min_p=bootstrap_min_p,
        active_champion_metrics=champion_windows.get("active"),
        active_candidate_metrics=candidate_windows.get("active"),
        active_gameweeks=active_gws,
        active_gw_primary_deltas=active_gw_deltas,
        all_gameweeks=sorted(all_gws),
        segment_tolerances=segment_tolerances,
    )


def compare_two_season_gate(
    dev_reference: WalkforwardResult,
    dev_candidate: WalkforwardResult,
    conf_reference: WalkforwardResult,
    conf_candidate: WalkforwardResult,
    *,
    primary_target: str = "blended_points",
    dev_min_p: float = BOOTSTRAP_MIN_P,
    conf_min_p: float = CONFIRMATION_BOOTSTRAP_MIN_P,
    pooled_min_p: float = POOLED_BOOTSTRAP_MIN_P,
    dev_segment_tolerances: Mapping[str, float] | None = None,
    conf_segment_tolerances: Mapping[str, float] | None = None,
    seed: int = 0,
) -> TwoSeasonGateVerdict:
    """Compare candidate vs reference across dev and confirmation seasons with pooled stratified bootstrap."""
    dev_verdict = compare_to_reference(
        dev_reference,
        dev_candidate,
        primary_target=primary_target,
        bootstrap_min_p=dev_min_p,
        segment_tolerances=dev_segment_tolerances,
    )
    conf_verdict = compare_to_reference(
        conf_reference,
        conf_candidate,
        primary_target=primary_target,
        bootstrap_min_p=conf_min_p,
        segment_tolerances=conf_segment_tolerances,
    )
    dev_active_gws = identify_active_gameweeks(dev_reference.df_eval, dev_candidate.df_eval)
    dev_all_gws = set(dev_reference.df_eval["gameweek"].unique())
    dev_gw_deltas, dev_active_deltas = _paired_regret_deltas(
        dev_reference.df_eval,
        dev_candidate.df_eval,
        primary_target=primary_target,
        active_gws=dev_active_gws,
        all_gws=dev_all_gws,
    )
    conf_active_gws = identify_active_gameweeks(conf_reference.df_eval, conf_candidate.df_eval)
    conf_all_gws = set(conf_reference.df_eval["gameweek"].unique())
    conf_gw_deltas, conf_active_deltas = _paired_regret_deltas(
        conf_reference.df_eval,
        conf_candidate.df_eval,
        primary_target=primary_target,
        active_gws=conf_active_gws,
        all_gws=conf_all_gws,
    )
    return evaluate_two_season_gate(
        dev_verdict,
        conf_verdict,
        dev_gw_deltas=dev_gw_deltas,
        conf_gw_deltas=conf_gw_deltas,
        dev_active_gameweeks=dev_active_gws,
        conf_active_gameweeks=conf_active_gws,
        dev_active_gw_deltas=dev_active_deltas,
        conf_active_gw_deltas=conf_active_deltas,
        dev_all_gameweeks=sorted(dev_all_gws),
        conf_all_gameweeks=sorted(conf_all_gws),
        dev_min_p=dev_min_p,
        conf_min_p=conf_min_p,
        pooled_min_p=pooled_min_p,
        seed=seed,
    )


def build_evidence_record(
    *,
    selection_before: ModelSelection,
    selection_after: ModelSelection,
    comparisons: list[CandidateComparison],
    evaluation_season: str,
    git_commit: str | None,
) -> dict[str, Any]:
    return {
        "evaluated_at": datetime.now(UTC).isoformat(),
        "evaluation_season": evaluation_season,
        "git_commit": git_commit,
        "selection_before": {
            "champion": selection_before.champion,
            "candidates": list(selection_before.candidates),
            "promotion_status": selection_before.promotion_status,
        },
        "selection_after": {
            "champion": selection_after.champion,
            "candidates": list(selection_after.candidates),
            "promotion_status": selection_after.promotion_status,
        },
        "comparisons": [
            {
                "candidate": comparison.candidate,
                "passed": comparison.verdict.passed,
                "eval_target": comparison.verdict.eval_target,
                "primary_metric": comparison.verdict.primary_metric,
                "combined_primary_delta": comparison.verdict.combined_primary_delta,
                "min_effect": comparison.verdict.min_effect,
                "bootstrap_p": comparison.verdict.bootstrap_p,
                "segment_wins": comparison.verdict.segment_wins,
                "segment_guardrails_passed": comparison.verdict.segment_guardrails_passed,
                "guardrails_passed": comparison.verdict.guardrails_passed,
                "active_guardrails_passed": comparison.verdict.active_guardrails_passed,
                "reasons": list(comparison.verdict.reasons),
                "snapshot_backed": comparison.snapshot_backed,
            }
            for comparison in comparisons
        ],
    }


def write_promotion_evidence(record: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    champion = record["selection_after"]["champion"]
    json_path = output_dir / f"{stamp}-{champion}.json"
    md_path = output_dir / f"{stamp}-{champion}.md"
    json_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Promotion Evidence Record",
        "",
        f"- Evaluated at: {record['evaluated_at']}",
        f"- Evaluation season: {record['evaluation_season']}",
        f"- Git commit: {record.get('git_commit') or 'unknown'}",
        "",
        "## Comparison Slate",
        "",
        f"- Champion: `{record['selection_after']['champion']}`",
        f"- Candidates: {', '.join(f'`{name}`' for name in record['selection_after']['candidates']) or 'none'}",
        f"- Promotion status: `{record['selection_after']['promotion_status']}`",
        "",
        "## Candidate Results",
        "",
    ]
    for comparison in record["comparisons"]:
        outcome = "passed" if comparison["passed"] else "failed"
        lines.append(f"### `{comparison['candidate']}` ({outcome})")
        lines.append(
            f"- Primary metric: `{comparison['primary_metric']}` "
            f"(delta {comparison['combined_primary_delta']:.4f}, min effect {comparison.get('min_effect', 0.0):.4f})"
        )
        if comparison.get("bootstrap_p") is not None:
            lines.append(f"- Block-bootstrap P(delta>0): {comparison['bootstrap_p']:.3f}")
        lines.append(f"- Eval target: `{comparison.get('eval_target', 'actual_points')}`")
        lines.append(f"- Segment wins: {comparison['segment_wins']}/3")
        lines.append(f"- Segment guardrails passed: {comparison['segment_guardrails_passed']}")
        lines.append(f"- Guardrails passed: {comparison['guardrails_passed']}")
        lines.append(f"- Active guardrails passed: {comparison.get('active_guardrails_passed', True)}")
        lines.append(f"- Snapshot backed: {comparison['snapshot_backed']}")
        if comparison["reasons"]:
            lines.append(f"- Reasons: {', '.join(comparison['reasons'])}")
        lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path
