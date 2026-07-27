"""Compare models and apply Automatic Historical Promotion."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from backtesting.promotion import (
    PromotionVerdict,
    evaluate_historical_promotion_gate,
    metrics_by_season_window,
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


def compare_to_reference(
    reference: WalkforwardResult,
    candidate: WalkforwardResult,
) -> PromotionVerdict:
    return evaluate_historical_promotion_gate(
        metrics_by_season_window(reference.df_eval),
        metrics_by_season_window(candidate.df_eval),
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
                "primary_metric": comparison.verdict.primary_metric,
                "combined_primary_delta": comparison.verdict.combined_primary_delta,
                "segment_wins": comparison.verdict.segment_wins,
                "guardrails_passed": comparison.verdict.guardrails_passed,
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
            f"(delta {comparison['combined_primary_delta']:.4f})"
        )
        lines.append(f"- Segment wins: {comparison['segment_wins']}/3")
        lines.append(f"- Guardrails passed: {comparison['guardrails_passed']}")
        lines.append(f"- Snapshot backed: {comparison['snapshot_backed']}")
        if comparison["reasons"]:
            lines.append(f"- Reasons: {', '.join(comparison['reasons'])}")
        lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path
