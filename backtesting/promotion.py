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

# Statistical gate (ADR 0046, 0049, 0062). No minimum effect beyond delta > 0; bootstrap bar shared by both seasons.
MIN_EFFECT_SHARE = 0.0
BOOTSTRAP_MIN_P = 0.60
CONFIRMATION_BOOTSTRAP_MIN_P = 0.60
BOOTSTRAP_DRAWS = 20_000
BOOTSTRAP_BLOCK_GWS = 3
GUARDRAIL_REL_TOL = 0.01
BIAS_ABS_TOL = 0.01
SPEARMAN_ABS_TOL = 0.005
CAPTAIN_REGRET_ABS_TOL = 0.15
PLAYABLE_XP_THRESHOLD = 2.0
PLAYABLE_MINUTES_THRESHOLD = 30.0

# Non-catastrophic segment loss guardrails (ADR 0062, replacing binary segs >= 2/3)
SEGMENT_REGRESSION_TOL: float = 0.15
COLD_START_PARITY_TOL: float = 0.05


@dataclass(frozen=True)
class GuardrailMetrics:
    xmins_mae: float
    xp_bias: float
    rank_correlation: float
    captain_regret: float | None = None
    playable_mae: float | None = None
    playable_bias: float | None = None


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
    segment_guardrails_passed: bool = True


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
    return bool(metrics.get("valid_rank_gameweeks")) and (
        metrics.get("formation_xi_regret") is not None or metrics.get("top_11_regret") is not None
    )


def primary_metric_name(metrics: dict[str, Any]) -> str:
    return "decision_regret" if _regret_is_informative(metrics) else "xp_mae"


def primary_metric_value(metrics: dict[str, Any]) -> float:
    if _regret_is_informative(metrics):
        if metrics.get("formation_xi_regret") is not None:
            return float(metrics["formation_xi_regret"])
        return float(metrics["top_11_regret"])
    return float(metrics["mae"])


def guardrail_metrics(metrics: dict[str, Any]) -> GuardrailMetrics:
    minutes = metrics.get("minutes_forecast_metrics") or {}
    spearman = metrics.get("spearman")
    cap_regret = metrics.get("captain_regret")
    playable_mae = metrics.get("playable_mae")
    playable_bias = metrics.get("playable_bias")
    return GuardrailMetrics(
        xmins_mae=float(minutes.get("mae", float("inf"))),
        xp_bias=abs(float(metrics["bias"])),
        rank_correlation=float(spearman if spearman is not None else -1.0),
        captain_regret=float(cap_regret) if cap_regret is not None else None,
        playable_mae=float(playable_mae) if playable_mae is not None else None,
        playable_bias=abs(float(playable_bias)) if playable_bias is not None else None,
    )


def metrics_meet_guardrails(candidate: GuardrailMetrics, champion: GuardrailMetrics) -> bool:
    meets_xmins = candidate.xmins_mae <= champion.xmins_mae * (1.0 + GUARDRAIL_REL_TOL)
    meets_bias = candidate.xp_bias <= champion.xp_bias + BIAS_ABS_TOL
    meets_rank = candidate.rank_correlation >= champion.rank_correlation - SPEARMAN_ABS_TOL

    meets_captain = True
    if candidate.captain_regret is not None and champion.captain_regret is not None:
        meets_captain = candidate.captain_regret <= champion.captain_regret + CAPTAIN_REGRET_ABS_TOL

    meets_playable = True
    if candidate.playable_mae is not None and champion.playable_mae is not None:
        meets_playable = candidate.playable_mae <= champion.playable_mae * (1.0 + GUARDRAIL_REL_TOL)
    if candidate.playable_bias is not None and champion.playable_bias is not None:
        meets_playable = meets_playable and (candidate.playable_bias <= champion.playable_bias + BIAS_ABS_TOL)

    return meets_xmins and meets_bias and meets_rank and meets_captain and meets_playable


def compute_playable_pool_metrics(
    champion_df: pd.DataFrame,
    candidate_df: pd.DataFrame,
    *,
    target_column: str = "actual_points",
    xp_threshold: float = PLAYABLE_XP_THRESHOLD,
    minutes_threshold: float = PLAYABLE_MINUTES_THRESHOLD,
) -> tuple[dict[str, float], dict[str, float]]:
    """Compute MAE and bias over the playable pool (xp >= 2.0 or minutes >= 30)."""
    cols = ["gameweek", "player_id", "projected_points", target_column]
    if "actual_minutes" in champion_df.columns:
        cols.append("actual_minutes")
    champ_sub = champion_df[cols].rename(columns={"projected_points": "champ_xp"})
    cand_sub = candidate_df[["gameweek", "player_id", "projected_points"]].rename(
        columns={"projected_points": "cand_xp"}
    )
    merged = pd.merge(champ_sub, cand_sub, on=["gameweek", "player_id"], how="inner")
    if merged.empty:
        return {}, {}
    minutes = (
        merged["actual_minutes"]
        if "actual_minutes" in merged.columns
        else pd.Series(0.0, index=merged.index)
    )
    playable = (
        (merged["champ_xp"] >= xp_threshold)
        | (merged["cand_xp"] >= xp_threshold)
        | (minutes >= minutes_threshold)
    )
    subset = merged[playable]
    if subset.empty:
        return {}, {}
    champ_err = subset["champ_xp"] - subset[target_column]
    cand_err = subset["cand_xp"] - subset[target_column]
    champ_metrics = {"mae": float(champ_err.abs().mean()), "bias": float(champ_err.mean())}
    cand_metrics = {"mae": float(cand_err.abs().mean()), "bias": float(cand_err.mean())}
    return champ_metrics, cand_metrics


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
    cand_g = guardrail_metrics(combined_candidate)
    champ_g = guardrail_metrics(combined_champion)
    guardrails_passed = metrics_meet_guardrails(cand_g, champ_g)

    segment_deltas: dict[str, float] = {}
    segment_wins = 0
    for segment in _SEGMENT_NAMES:
        if segment not in champion_windows or segment not in candidate_windows:
            continue
        champ_seg_val = primary_metric_value(champion_windows[segment])
        cand_seg_val = primary_metric_value(candidate_windows[segment])
        delta_seg = champ_seg_val - cand_seg_val
        segment_deltas[segment] = delta_seg
        if delta_seg > 0:
            segment_wins += 1

    cold_start_ok = segment_deltas.get("cold_start", 0.0) >= -COLD_START_PARITY_TOL
    active_segments_ok = all(
        segment_deltas[s] >= -SEGMENT_REGRESSION_TOL
        for s in ("early_mid", "late")
        if s in segment_deltas
    )
    has_active_win = any(
        segment_deltas[s] > 0
        for s in ("early_mid", "late")
        if s in segment_deltas
    )
    segment_guardrails_passed = cold_start_ok and active_segments_ok and has_active_win

    reasons: list[str] = []
    effect_ok = combined_delta > 0 and combined_delta >= min_effect
    if combined_delta <= 0:
        reasons.append("combined primary metric did not improve")
    elif not effect_ok:
        reasons.append(f"combined improvement {combined_delta:.4f} below minimum effect {min_effect:.4f}")
    significant = bootstrap_p is None or bootstrap_p >= bootstrap_min_p
    if not significant:
        reasons.append(f"bootstrap P(delta>0) {bootstrap_p:.3f} below {bootstrap_min_p:.2f}")
    if not segment_guardrails_passed:
        if not cold_start_ok:
            reasons.append(
                f"cold start regressed ({segment_deltas['cold_start']:.3f} < -{COLD_START_PARITY_TOL:.2f})"
            )
        for s in ("early_mid", "late"):
            if s in segment_deltas and segment_deltas[s] < -SEGMENT_REGRESSION_TOL:
                reasons.append(
                    f"catastrophic regression in {s} segment ({segment_deltas[s]:.3f} < -{SEGMENT_REGRESSION_TOL:.2f})"
                )
        if not has_active_win:
            reasons.append("won 0 active in-season segments")
    if not guardrails_passed:
        reasons.append("failed one or more Champion guardrails")
        if (
            cand_g.captain_regret is not None
            and champ_g.captain_regret is not None
            and cand_g.captain_regret > champ_g.captain_regret + CAPTAIN_REGRET_ABS_TOL
        ):
            reasons.append(
                f"regressed Captaincy Regret guardrail "
                f"({cand_g.captain_regret:.3f} vs {champ_g.captain_regret:.3f} + {CAPTAIN_REGRET_ABS_TOL:.2f})"
            )
        if (
            cand_g.playable_mae is not None
            and champ_g.playable_mae is not None
            and cand_g.playable_mae > champ_g.playable_mae * (1.0 + GUARDRAIL_REL_TOL)
        ):
            reasons.append(
                f"regressed Playable Pool MAE guardrail "
                f"({cand_g.playable_mae:.4f} vs {champ_g.playable_mae:.4f})"
            )
        if (
            cand_g.playable_bias is not None
            and champ_g.playable_bias is not None
            and cand_g.playable_bias > champ_g.playable_bias + BIAS_ABS_TOL
        ):
            reasons.append(
                f"regressed Playable Pool Bias guardrail "
                f"({cand_g.playable_bias:.4f} vs {champ_g.playable_bias:.4f})"
            )
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

    passed = effect_ok and significant and segment_guardrails_passed and guardrails_passed
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
        segment_guardrails_passed=segment_guardrails_passed,
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
