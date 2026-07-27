"""Historical Promotion Gate and live comparison helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from backtesting.metrics import evaluate_predictions

SEASON_WINDOWS: dict[str, tuple[int, int]] = {
    "cold_start": (1, 4),
    "early_mid": (5, 19),
    "late": (20, 38),
}
_SEGMENT_NAMES = ("cold_start", "early_mid", "late")
_MEANINGFUL_LIVE_LEAD = 0.05


@dataclass(frozen=True)
class GuardrailMetrics:
    xmins_mae: float
    xp_bias: float
    rank_correlation: float


@dataclass(frozen=True)
class PromotionVerdict:
    passed: bool
    primary_metric: str
    combined_primary_delta: float
    segment_wins: int
    guardrails_passed: bool
    reasons: tuple[str, ...]


def _regret_is_informative(metrics: dict[str, Any]) -> bool:
    return bool(metrics.get("valid_rank_gameweeks")) and metrics.get("top_11_regret") is not None


def primary_metric_name(metrics: dict[str, Any]) -> str:
    return "decision_regret" if _regret_is_informative(metrics) else "xp_mae"


def primary_metric_value(metrics: dict[str, Any]) -> float:
    if _regret_is_informative(metrics):
        return float(metrics["top_11_regret"])
    return float(metrics["mae"])


def guardrail_metrics(metrics: dict[str, Any]) -> GuardrailMetrics:
    minutes = metrics.get("minutes_forecast_metrics") or {}
    spearman = metrics.get("spearman")
    return GuardrailMetrics(
        xmins_mae=float(minutes.get("mae", float("inf"))),
        xp_bias=abs(float(metrics["bias"])),
        rank_correlation=float(spearman if spearman is not None else -1.0),
    )


def metrics_meet_guardrails(candidate: GuardrailMetrics, champion: GuardrailMetrics) -> bool:
    return (
        candidate.xmins_mae <= champion.xmins_mae
        and candidate.xp_bias <= champion.xp_bias
        and candidate.rank_correlation >= champion.rank_correlation
    )


def segment_metrics(df_eval: pd.DataFrame, start_gw: int, end_gw: int) -> dict[str, Any] | None:
    segment = df_eval[(df_eval["gameweek"] >= start_gw) & (df_eval["gameweek"] <= end_gw)]
    if segment.empty:
        return None
    return evaluate_predictions(segment)


def metrics_by_season_window(df_eval: pd.DataFrame) -> dict[str, dict[str, Any]]:
    windows: dict[str, dict[str, Any]] = {"combined": evaluate_predictions(df_eval)}
    for name, (start_gw, end_gw) in SEASON_WINDOWS.items():
        segment_metrics_result = segment_metrics(df_eval, start_gw, end_gw)
        if segment_metrics_result is not None:
            windows[name] = segment_metrics_result
    return windows


def evaluate_historical_promotion_gate(
    champion_windows: dict[str, dict[str, Any]],
    candidate_windows: dict[str, dict[str, Any]],
) -> PromotionVerdict:
    combined_champion = champion_windows["combined"]
    combined_candidate = candidate_windows["combined"]
    champion_primary = primary_metric_value(combined_champion)
    candidate_primary = primary_metric_value(combined_candidate)
    combined_delta = champion_primary - candidate_primary
    guardrails_passed = metrics_meet_guardrails(
        guardrail_metrics(combined_candidate),
        guardrail_metrics(combined_champion),
    )

    segment_wins = 0
    for segment in _SEGMENT_NAMES:
        if segment not in champion_windows or segment not in candidate_windows:
            continue
        if primary_metric_value(candidate_windows[segment]) < primary_metric_value(champion_windows[segment]):
            segment_wins += 1

    reasons: list[str] = []
    if combined_delta <= 0:
        reasons.append("combined primary metric did not improve")
    if segment_wins < 2:
        reasons.append(f"won only {segment_wins}/3 seasonal segments")
    if not guardrails_passed:
        reasons.append("failed one or more Champion guardrails")

    passed = combined_delta > 0 and segment_wins >= 2 and guardrails_passed
    return PromotionVerdict(
        passed=passed,
        primary_metric=primary_metric_name(combined_champion),
        combined_primary_delta=combined_delta,
        segment_wins=segment_wins,
        guardrails_passed=guardrails_passed,
        reasons=tuple(reasons),
    )


def classify_live_lead(champion_primary: float, candidate_primary: float) -> str:
    if champion_primary <= 0:
        return "unclear"
    improvement = (champion_primary - candidate_primary) / champion_primary
    if improvement >= _MEANINGFUL_LIVE_LEAD:
        return "meaningful"
    if improvement <= -_MEANINGFUL_LIVE_LEAD:
        return "meaningful_loss"
    return "unclear"
