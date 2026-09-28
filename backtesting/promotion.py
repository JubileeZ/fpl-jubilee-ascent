"""Historical Promotion Gate and live comparison helpers."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from backtesting.metrics import evaluate_predictions

SEASON_WINDOWS: dict[str, tuple[int, int]] = {
    "cold_start": (1, 4),
    "early_mid": (5, 19),
    "late": (20, 38),
}
_SEGMENT_NAMES = ("cold_start", "early_mid", "late")
_MEANINGFUL_LIVE_LEAD = 0.05

# Statistical gate (ADR 0046). No minimum effect beyond delta > 0; bootstrap bar shared by both seasons (ADR 0049).
MIN_EFFECT_SHARE = 0.0
BOOTSTRAP_MIN_P = 0.60
CONFIRMATION_BOOTSTRAP_MIN_P = 0.60
BOOTSTRAP_DRAWS = 20_000
BOOTSTRAP_BLOCK_GWS = 3
GUARDRAIL_REL_TOL = 0.01
BIAS_ABS_TOL = 0.01
SPEARMAN_ABS_TOL = 0.005


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
    eval_target: str = "actual_points"
    min_effect: float = 0.0
    bootstrap_p: float | None = None


def block_bootstrap_win_probability(
    deltas: Sequence[float], *, draws: int = BOOTSTRAP_DRAWS, block: int = BOOTSTRAP_BLOCK_GWS, seed: int = 0
) -> float:
    """Share of circular block-bootstrap resamples (blocks of consecutive GWs) with mean delta > 0."""
    values = np.asarray(deltas, dtype=float)
    n = len(values)
    if n == 0:
        return 0.0
    size = min(block, n)
    starts = np.random.default_rng(seed).integers(0, n, size=(draws, -(-n // size)))
    idx = ((starts[:, :, None] + np.arange(size)) % n).reshape(draws, -1)[:, :n]
    return float((values[idx].mean(axis=1) > 0).mean())


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
        candidate.xmins_mae <= champion.xmins_mae * (1.0 + GUARDRAIL_REL_TOL)
        and candidate.xp_bias <= champion.xp_bias + BIAS_ABS_TOL
        and candidate.rank_correlation >= champion.rank_correlation - SPEARMAN_ABS_TOL
    )


def segment_metrics(
    df_eval: pd.DataFrame,
    start_gw: int,
    end_gw: int,
    *,
    target_column: str = "actual_points",
) -> dict[str, Any] | None:
    segment = df_eval[(df_eval["gameweek"] >= start_gw) & (df_eval["gameweek"] <= end_gw)]
    if segment.empty:
        return None
    return evaluate_predictions(segment, target_column=target_column)


def metrics_by_season_window(
    df_eval: pd.DataFrame, *, target_column: str = "actual_points"
) -> dict[str, dict[str, Any]]:
    windows: dict[str, dict[str, Any]] = {
        "combined": evaluate_predictions(df_eval, target_column=target_column)
    }
    for name, (start_gw, end_gw) in SEASON_WINDOWS.items():
        segment_metrics_result = segment_metrics(
            df_eval, start_gw, end_gw, target_column=target_column
        )
        if segment_metrics_result is not None:
            windows[name] = segment_metrics_result
    return windows


_REFERENCE_TARGETS = ("actual_points", "process_points")
_REFERENCE_LABELS = {"actual_points": "Realized", "process_points": "Process"}


def evaluate_historical_promotion_gate(
    champion_windows: dict[str, dict[str, Any]],
    candidate_windows: dict[str, dict[str, Any]],
    *,
    eval_target: str = "actual_points",
    reference_windows: dict[str, tuple[dict[str, Any], dict[str, Any]]] | None = None,
    gw_primary_deltas: Sequence[float] | None = None,
    bootstrap_min_p: float = BOOTSTRAP_MIN_P,
) -> PromotionVerdict:
    """Pass = combined delta > 0 and ≥ min effect, ≥2/3 segments, guardrails within tolerance, and
    (when per-GW deltas given) block-bootstrap P(delta > 0) ≥ bootstrap_min_p."""
    combined_champion = champion_windows["combined"]
    combined_candidate = candidate_windows["combined"]
    champion_primary = primary_metric_value(combined_champion)
    candidate_primary = primary_metric_value(combined_candidate)
    combined_delta = champion_primary - candidate_primary
    min_effect = MIN_EFFECT_SHARE * max(champion_primary, 0.0)
    bootstrap_p = None if gw_primary_deltas is None else block_bootstrap_win_probability(gw_primary_deltas)
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
    effect_ok = combined_delta > 0 and combined_delta >= min_effect
    if combined_delta <= 0:
        reasons.append("combined primary metric did not improve")
    elif not effect_ok:
        reasons.append(f"combined improvement {combined_delta:.4f} below minimum effect {min_effect:.4f}")
    significant = bootstrap_p is None or bootstrap_p >= bootstrap_min_p
    if not significant:
        reasons.append(f"bootstrap P(delta>0) {bootstrap_p:.3f} below {bootstrap_min_p:.2f}")
    if segment_wins < 2:
        reasons.append(f"won only {segment_wins}/3 seasonal segments")
    if not guardrails_passed:
        reasons.append("failed one or more Champion guardrails")
    if reference_windows:
        for target in _REFERENCE_TARGETS:
            pair = reference_windows.get(target)
            if pair is None:
                continue
            champion_ref, candidate_ref = pair
            if float(candidate_ref["mae"]) > float(champion_ref["mae"]) * (1.0 + GUARDRAIL_REL_TOL):
                guardrails_passed = False
                reasons.append(
                    f"regressed {_REFERENCE_LABELS[target]} MAE guardrail "
                    f"({float(candidate_ref['mae']):.4f} vs {float(champion_ref['mae']):.4f})"
                )

    passed = effect_ok and significant and segment_wins >= 2 and guardrails_passed
    return PromotionVerdict(
        passed=passed,
        primary_metric=primary_metric_name(combined_champion),
        combined_primary_delta=combined_delta,
        segment_wins=segment_wins,
        guardrails_passed=guardrails_passed,
        reasons=tuple(reasons),
        eval_target=eval_target,
        min_effect=min_effect,
        bootstrap_p=bootstrap_p,
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
