"""Historical Promotion Gate and live comparison helpers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
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

# Statistical gate (ADR 0046, 0049, 0062, 0064).
# Non-wrapping Moving Block Bootstrap (L=5, spanning 4-6 week fixture swings).
# Dev season: P >= 0.75; Confirmation season (warm-seeded): P >= 0.65; Pooled 2-Season Stratified: P >= 0.85 (ADR 0064).
MIN_EFFECT_SHARE = 0.0
BOOTSTRAP_MIN_P = 0.75
CONFIRMATION_BOOTSTRAP_MIN_P = 0.65
POOLED_BOOTSTRAP_MIN_P = 0.85
BOOTSTRAP_DRAWS = 20_000
BOOTSTRAP_BLOCK_GWS = 5
COMPONENT_SCREEN_MIN_P: float = 0.65
ORACLE_BIAS_REL_TOL: float = 0.02
ORACLE_BIAS_HARD_CAP: float = 0.20
GUARDRAIL_REL_TOL = 0.01
BIAS_ABS_TOL = 0.01
SPEARMAN_ABS_TOL = 0.005
CAPTAIN_REGRET_ABS_TOL = 0.15
PLAYABLE_XP_THRESHOLD = 2.0
PLAYABLE_MINUTES_THRESHOLD = 30.0

# Non-catastrophic sqrt(n_s)-calibrated segment loss guardrails (ADR 0062, ADR 0064)
# Standardized to uniform stringency z ~ -0.25 SE:
# cold_start (n=4):  -0.25 pts/GW (max -1.00 cumulative pt, z = -0.227 SE)
# early_mid  (n=15): -0.15 pts/GW (max -2.25 cumulative pts, z = -0.264 SE)
# late       (n=19): -0.13 pts/GW (max -2.47 cumulative pts, z = -0.258 SE)
COLD_START_PARITY_TOL: float = 0.25
SEGMENT_REGRESSION_TOL: float = 0.15
LATE_SEGMENT_REGRESSION_TOL: float = 0.13
CHURN_GUARDRAIL_TOL: float = 0.50

SEGMENT_REGRESSION_TOLERANCES: dict[str, float] = {
    "cold_start": COLD_START_PARITY_TOL,
    "early_mid": SEGMENT_REGRESSION_TOL,
    "late": LATE_SEGMENT_REGRESSION_TOL,
}


def segment_regression_tolerance(
    segment: str,
    *,
    tolerances: Mapping[str, float] | None = None,
) -> float:
    """Return sqrt(n_s)-calibrated regression floor for a seasonal segment."""
    lookup = tolerances if tolerances is not None else SEGMENT_REGRESSION_TOLERANCES
    return float(lookup.get(segment, SEGMENT_REGRESSION_TOL))


@dataclass(frozen=True)
class GuardrailMetrics:
    xmins_mae: float
    xp_bias: float
    rank_correlation: float
    captain_regret: float | None = None
    playable_mae: float | None = None
    playable_bias: float | None = None
    squad_churn: float | None = None


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
    active_guardrails_passed: bool = True


@dataclass(frozen=True)
class TwoSeasonGateVerdict:
    passed: bool
    dev_verdict: PromotionVerdict
    conf_verdict: PromotionVerdict
    pooled_bootstrap_p: float
    reasons: tuple[str, ...]


def moving_block_indices(
    n: int, block: int, draws: int, seed: int = 0
) -> np.ndarray:
    """Generate non-wrapping moving block bootstrap indices with shape (draws, k * size).

    Start indices are strictly restricted to 0 <= s <= n - size, ensuring all indices stay in
    [0, n-1] with zero circular wrapping (% n) and complete blocks of length size (ADR 0064).
    """
    if n <= 0:
        return np.empty((draws, 0), dtype=int)
    size = min(block, n)
    if size <= 0:
        return np.empty((draws, 0), dtype=int)
    rng = np.random.default_rng(seed)
    k = -(-n // size)
    num_starts = n - size + 1
    starts = rng.integers(0, num_starts, size=(draws, k))
    return (starts[:, :, None] + np.arange(size)).reshape(draws, -1)


def stratified_block_bootstrap_win_probability(
    strata_deltas: Sequence[Sequence[float]],
    *,
    draws: int = BOOTSTRAP_DRAWS,
    block: int = BOOTSTRAP_BLOCK_GWS,
    seed: int = 0,
) -> float:
    """Pooled multi-season stratified block bootstrap probability of positive mean delta.

    Draws non-wrapping moving blocks independently within each season's temporal stratum,
    preventing inter-season index mixing and modulo boundary artifacts, then evaluates
    the combined pooled sample mean across all strata (ADR 0064).
    """
    valid_strata: list[np.ndarray] = []
    for s in strata_deltas:
        arr = np.asarray(s, dtype=float)
        arr = arr[~np.isnan(arr)]
        if len(arr) > 0:
            valid_strata.append(arr)
    if not valid_strata:
        return 0.0

    strata_resamples: list[np.ndarray] = []
    for i, s_vals in enumerate(valid_strata):
        idx = moving_block_indices(len(s_vals), block, draws, seed=seed + i * 1000)
        if idx.shape[1] > 0:
            strata_resamples.append(s_vals[idx])

    if not strata_resamples:
        return 0.0
    pooled_matrix = np.concatenate(strata_resamples, axis=1)
    return float((pooled_matrix.mean(axis=1) > 0).mean())


pooled_block_bootstrap_win_probability = stratified_block_bootstrap_win_probability


def block_bootstrap_win_probability(
    deltas: Sequence[float],
    *,
    draws: int = BOOTSTRAP_DRAWS,
    block: int = BOOTSTRAP_BLOCK_GWS,
    seed: int = 0,
) -> float:
    """Share of non-wrapping moving block-bootstrap resamples with mean delta > 0.

    Eliminates circular modulo wrapping (% n) by restricting start indices to
    0 <= s <= n - L, and eliminates final-block truncation by evaluating complete
    blocks of length L (ADR 0064).
    """
    return stratified_block_bootstrap_win_probability(
        [deltas], draws=draws, block=block, seed=seed
    )


def _filter_active_gw_deltas(
    gw_deltas: Sequence[float] | None,
    *,
    active_gameweeks: Sequence[int] | None = None,
    active_gw_deltas: Sequence[float] | None = None,
    all_gameweeks: Sequence[int] | None = None,
) -> Sequence[float] | None:
    if active_gw_deltas is not None:
        return active_gw_deltas
    if active_gameweeks is None or gw_deltas is None:
        return gw_deltas
    if all_gameweeks is not None and len(all_gameweeks) == len(gw_deltas):
        mapping = dict(zip(all_gameweeks, gw_deltas))
        return [mapping[g] for g in active_gameweeks if g in mapping]
    min_gw = min(active_gameweeks, default=0)
    max_gw = max(active_gameweeks, default=0)
    n_deltas = len(gw_deltas)
    if min_gw >= 1 and max_gw <= n_deltas:
        if len(active_gameweeks) < n_deltas:
            return [gw_deltas[g - 1] for g in active_gameweeks if 1 <= g <= n_deltas]
    return gw_deltas


def evaluate_two_season_gate(
    dev_verdict: PromotionVerdict,
    conf_verdict: PromotionVerdict,
    *,
    dev_gw_deltas: Sequence[float],
    conf_gw_deltas: Sequence[float],
    dev_active_gameweeks: Sequence[int] | None = None,
    conf_active_gameweeks: Sequence[int] | None = None,
    dev_active_gw_deltas: Sequence[float] | None = None,
    conf_active_gw_deltas: Sequence[float] | None = None,
    dev_all_gameweeks: Sequence[int] | None = None,
    conf_all_gameweeks: Sequence[int] | None = None,
    dev_min_p: float = BOOTSTRAP_MIN_P,
    conf_min_p: float = CONFIRMATION_BOOTSTRAP_MIN_P,
    pooled_min_p: float = POOLED_BOOTSTRAP_MIN_P,
    seed: int = 0,
) -> TwoSeasonGateVerdict:
    """Evaluate full two-season promotion gate with pooled stratified bootstrap (ADR 0064)."""
    dev_resample = _filter_active_gw_deltas(
        dev_gw_deltas,
        active_gameweeks=dev_active_gameweeks,
        active_gw_deltas=dev_active_gw_deltas,
        all_gameweeks=dev_all_gameweeks,
    ) or ()
    conf_resample = _filter_active_gw_deltas(
        conf_gw_deltas,
        active_gameweeks=conf_active_gameweeks,
        active_gw_deltas=conf_active_gw_deltas,
        all_gameweeks=conf_all_gameweeks,
    ) or ()
    pooled_p = stratified_block_bootstrap_win_probability(
        [dev_resample, conf_resample], seed=seed
    )
    reasons: list[str] = []
    if not dev_verdict.passed:
        reasons.append(f"dev season failed: {', '.join(dev_verdict.reasons)}")
    elif dev_verdict.bootstrap_p is not None and dev_verdict.bootstrap_p < dev_min_p:
        reasons.append(
            f"dev bootstrap P {dev_verdict.bootstrap_p:.3f} below required {dev_min_p:.2f}"
        )
    if not conf_verdict.passed:
        reasons.append(f"confirmation season failed: {', '.join(conf_verdict.reasons)}")
    elif conf_verdict.bootstrap_p is not None and conf_verdict.bootstrap_p < conf_min_p:
        reasons.append(
            f"confirmation bootstrap P {conf_verdict.bootstrap_p:.3f} below required {conf_min_p:.2f}"
        )
    if pooled_p < pooled_min_p:
        reasons.append(
            f"pooled stratified bootstrap P(delta>0) {pooled_p:.3f} below required {pooled_min_p:.2f}"
        )
    passed = (
        dev_verdict.passed
        and conf_verdict.passed
        and (dev_verdict.bootstrap_p is None or dev_verdict.bootstrap_p >= dev_min_p)
        and (conf_verdict.bootstrap_p is None or conf_verdict.bootstrap_p >= conf_min_p)
        and (pooled_p >= pooled_min_p)
    )
    return TwoSeasonGateVerdict(
        passed=passed,
        dev_verdict=dev_verdict,
        conf_verdict=conf_verdict,
        pooled_bootstrap_p=pooled_p,
        reasons=tuple(reasons),
    )


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
    squad_churn = metrics.get("top_15_squad_churn")
    return GuardrailMetrics(
        xmins_mae=float(minutes.get("mae", float("inf"))),
        xp_bias=abs(float(metrics["bias"])),
        rank_correlation=float(spearman if spearman is not None else -1.0),
        captain_regret=float(cap_regret) if cap_regret is not None else None,
        playable_mae=float(playable_mae) if playable_mae is not None else None,
        playable_bias=abs(float(playable_bias)) if playable_bias is not None else None,
        squad_churn=float(squad_churn) if squad_churn is not None else None,
    )


def metrics_meet_guardrails(
    candidate: GuardrailMetrics,
    champion: GuardrailMetrics,
    *,
    check_churn: bool = True,
) -> bool:
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

    meets_churn = True
    if check_churn and candidate.squad_churn is not None and champion.squad_churn is not None:
        meets_churn = candidate.squad_churn <= champion.squad_churn + CHURN_GUARDRAIL_TOL

    return meets_xmins and meets_bias and meets_rank and meets_captain and meets_playable and meets_churn


def diagnose_guardrail_regressions(
    candidate: GuardrailMetrics,
    champion: GuardrailMetrics,
    *,
    window_label: str = "",
    check_churn: bool = True,
) -> list[str]:
    """Return diagnostic failure messages for guardrail metrics exceeding thresholds."""
    pfx = f"{window_label} " if window_label else ""
    reasons: list[str] = []
    if (
        candidate.xmins_mae is not None
        and champion.xmins_mae is not None
        and candidate.xmins_mae > champion.xmins_mae * (1.0 + GUARDRAIL_REL_TOL)
    ):
        reasons.append(
            f"regressed {pfx}xMins MAE guardrail ({candidate.xmins_mae:.4f} vs {champion.xmins_mae:.4f})"
        )
    if (
        candidate.xp_bias is not None
        and champion.xp_bias is not None
        and candidate.xp_bias > champion.xp_bias + BIAS_ABS_TOL
    ):
        reasons.append(
            f"regressed {pfx}XP Bias guardrail ({candidate.xp_bias:.4f} vs {champion.xp_bias:.4f} + {BIAS_ABS_TOL:.2f})"
        )
    if (
        candidate.rank_correlation is not None
        and champion.rank_correlation is not None
        and candidate.rank_correlation < champion.rank_correlation - SPEARMAN_ABS_TOL
    ):
        reasons.append(
            f"regressed {pfx}Rank Correlation guardrail "
            f"({candidate.rank_correlation:.4f} vs {champion.rank_correlation:.4f} - {SPEARMAN_ABS_TOL:.3f})"
        )
    if (
        candidate.captain_regret is not None
        and champion.captain_regret is not None
        and candidate.captain_regret > champion.captain_regret + CAPTAIN_REGRET_ABS_TOL
    ):
        reasons.append(
            f"regressed {pfx}Captaincy Regret guardrail "
            f"({candidate.captain_regret:.3f} vs {champion.captain_regret:.3f} + {CAPTAIN_REGRET_ABS_TOL:.2f})"
        )
    if (
        candidate.playable_mae is not None
        and champion.playable_mae is not None
        and candidate.playable_mae > champion.playable_mae * (1.0 + GUARDRAIL_REL_TOL)
    ):
        reasons.append(
            f"regressed {pfx}Playable Pool MAE guardrail ({candidate.playable_mae:.4f} vs {champion.playable_mae:.4f})"
        )
    if (
        candidate.playable_bias is not None
        and champion.playable_bias is not None
        and candidate.playable_bias > champion.playable_bias + BIAS_ABS_TOL
    ):
        reasons.append(
            f"regressed {pfx}Playable Pool Bias guardrail ({candidate.playable_bias:.4f} vs {champion.playable_bias:.4f})"
        )
    if (
        check_churn
        and candidate.squad_churn is not None
        and champion.squad_churn is not None
        and candidate.squad_churn > champion.squad_churn + CHURN_GUARDRAIL_TOL
    ):
        reasons.append(
            f"regressed {pfx}Squad Churn guardrail "
            f"({candidate.squad_churn:.2f} vs {champion.squad_churn:.2f} + {CHURN_GUARDRAIL_TOL:.2f})"
        )
    return reasons


def identify_active_gameweeks(
    champion_df: pd.DataFrame,
    candidate_df: pd.DataFrame,
    *,
    prediction_col: str = "projected_points",
    tol: float = 1e-6,
) -> list[int]:
    """Identify gameweeks where candidate predictions diverge from champion.

    G_active = {g : max_i |y_hat_cand_{i,g} - y_hat_champ_{i,g}| > tol}.
    Returns sorted list of active gameweek numbers.
    """
    cols = ["gameweek", "player_id", prediction_col]
    champ_sub = champion_df[cols].rename(columns={prediction_col: "champ_pred"})
    cand_sub = candidate_df[cols].rename(columns={prediction_col: "cand_pred"})
    merged = pd.merge(champ_sub, cand_sub, on=["gameweek", "player_id"], how="inner")
    if merged.empty:
        return []
    merged["diff"] = (merged["cand_pred"] - merged["champ_pred"]).abs()
    active_gws = [
        int(gw)
        for gw, max_diff in merged.groupby("gameweek")["diff"].max().items()
        if max_diff > tol
    ]
    return sorted(active_gws)


def compute_playable_pool_metrics(
    champion_df: pd.DataFrame,
    candidate_df: pd.DataFrame,
    *,
    target_column: str = "actual_points",
    xp_threshold: float = PLAYABLE_XP_THRESHOLD,
    minutes_threshold: float = PLAYABLE_MINUTES_THRESHOLD,
) -> tuple[dict[str, float], dict[str, float]]:
    """Compute MAE and bias over the model-independent exogenous playable pool.

    The playable pool mask is anchored strictly to exogenous criteria (champion xp >= 2.0
    or actual minutes >= 30). Candidate predictions are strictly excluded from mask
    construction to eliminate candidate-induced sample shifts and guarantee bit-for-bit
    identical evaluation sample sizes across all tested candidates (ADR 0064).
    """
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
    # Exogenous mask: depends only on Champion projection and observed minutes
    playable = (merged["champ_xp"] >= xp_threshold) | (minutes >= minutes_threshold)
    subset = merged[playable]
    if subset.empty:
        return {}, {}
    champ_err = subset["champ_xp"] - subset[target_column]
    cand_err = subset["cand_xp"] - subset[target_column]
    champ_metrics = {
        "mae": float(champ_err.abs().mean()),
        "bias": float(champ_err.mean()),
        "sample_count": int(len(subset)),
    }
    cand_metrics = {
        "mae": float(cand_err.abs().mean()),
        "bias": float(cand_err.mean()),
        "sample_count": int(len(subset)),
    }
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
    active_champion_metrics: dict[str, Any] | None = None,
    active_candidate_metrics: dict[str, Any] | None = None,
    active_gameweeks: Sequence[int] | None = None,
    active_gw_primary_deltas: Sequence[float] | None = None,
    all_gameweeks: Sequence[int] | None = None,
    segment_tolerances: Mapping[str, float] | None = None,
) -> PromotionVerdict:
    """Pass = combined delta > 0 and >= min effect, sqrt(n_s)-calibrated segment guardrails,
    Champion safety guardrails within tolerance, and (when per-GW deltas given) block-bootstrap
    P(delta > 0) >= bootstrap_min_p."""
    combined_champion = champion_windows["combined"]
    combined_candidate = candidate_windows["combined"]
    champion_primary = primary_metric_value(combined_champion)
    candidate_primary = primary_metric_value(combined_candidate)
    combined_delta = champion_primary - candidate_primary
    min_effect = MIN_EFFECT_SHARE * max(champion_primary, 0.0)

    # Restrict bootstrap resampling to active gameweeks to prevent dormant zero-error dilution (ADR 0064)
    resample_deltas = _filter_active_gw_deltas(
        gw_primary_deltas,
        active_gameweeks=active_gameweeks,
        active_gw_deltas=active_gw_primary_deltas,
        all_gameweeks=all_gameweeks,
    )

    bootstrap_p = (
        None if resample_deltas is None else block_bootstrap_win_probability(resample_deltas)
    )
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

    cold_tol = segment_regression_tolerance("cold_start", tolerances=segment_tolerances)
    cold_start_ok = segment_deltas.get("cold_start", 0.0) >= -cold_tol
    regressed_active_segments: list[tuple[str, float, float]] = []
    for s in ("early_mid", "late"):
        if s in segment_deltas:
            tol_s = segment_regression_tolerance(s, tolerances=segment_tolerances)
            if segment_deltas[s] < -tol_s:
                regressed_active_segments.append((s, segment_deltas[s], tol_s))
    active_segments_ok = not regressed_active_segments
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
                f"cold start regressed ({segment_deltas['cold_start']:.3f} < -{cold_tol:.2f})"
            )
        for s, delta_s, tol_s in regressed_active_segments:
            reasons.append(
                f"catastrophic regression in {s} segment ({delta_s:.3f} < -{tol_s:.2f})"
            )
        if not has_active_win:
            reasons.append("won 0 active in-season segments")
    if not guardrails_passed:
        reasons.append("failed one or more Champion guardrails")
        reasons.extend(diagnose_guardrail_regressions(cand_g, champ_g, window_label="", check_churn=True))

    active_cand_dict = active_candidate_metrics or candidate_windows.get("active")
    active_champ_dict = active_champion_metrics or champion_windows.get("active")
    active_guardrails_passed = True
    if active_cand_dict and active_champ_dict:
        active_cand_g = guardrail_metrics(active_cand_dict)
        active_champ_g = guardrail_metrics(active_champ_dict)
        active_guardrails_passed = metrics_meet_guardrails(active_cand_g, active_champ_g, check_churn=False)
        if not active_guardrails_passed:
            guardrails_passed = False
            reasons.append("failed one or more active-window Champion guardrails")
            reasons.extend(
                diagnose_guardrail_regressions(
                    active_cand_g, active_champ_g, window_label="active-window", check_churn=False
                )
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
        active_guardrails_passed=active_guardrails_passed,
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


@dataclass(frozen=True)
class OracleEventGateVerdict:
    passed: bool
    oracle_delta: float
    bootstrap_p: float | None
    candidate_playable_bias: float
    champion_playable_bias: float
    captain_regret_delta: float
    reasons: tuple[str, ...]


def evaluate_oracle_event_gate(
    champion_metrics: Mapping[str, Any],
    candidate_metrics: Mapping[str, Any],
    *,
    gw_deltas: Sequence[float] | None = None,
    active_gameweeks: Sequence[int] | None = None,
    all_gameweeks: Sequence[int] | None = None,
    champion_playable_bias: float | None = None,
    candidate_playable_bias: float | None = None,
    bootstrap_min_p: float = COMPONENT_SCREEN_MIN_P,
    bias_tol: float = ORACLE_BIAS_REL_TOL,
    bias_ceiling: float = ORACLE_BIAS_HARD_CAP,
    captain_regret_tol: float = CAPTAIN_REGRET_ABS_TOL,
) -> OracleEventGateVerdict:
    """Evaluate whether candidate event engine satisfies Tier 2 Oracle Event Gate.

    Conditions for Pass:
    1. Oracle Formation XI Regret improvement (oracle_delta = champ_regret - cand_regret > 0).
    2. Non-wrapping Moving Block Bootstrap P(oracle_delta > 0) >= bootstrap_min_p (when N >= 15 GWs).
    3. Playable Pool Signed Bias: |cand_bias| <= min(|champ_bias| + bias_tol, bias_ceiling).
    4. Captaincy Regret: cand_cap <= champ_cap + captain_regret_tol (0.15 pts/GW).
    """
    champ_regret = float(
        champion_metrics.get("oracle_formation_xi_regret")
        or champion_metrics.get("formation_xi_regret", 0.0)
    )
    cand_regret = float(
        candidate_metrics.get("oracle_formation_xi_regret")
        or candidate_metrics.get("formation_xi_regret", 0.0)
    )
    oracle_delta = champ_regret - cand_regret

    champ_cap = float(
        champion_metrics.get("oracle_captain_regret")
        or champion_metrics.get("captain_regret", 0.0)
    )
    cand_cap = float(
        candidate_metrics.get("oracle_captain_regret")
        or candidate_metrics.get("captain_regret", 0.0)
    )
    captain_regret_delta = cand_cap - champ_cap

    champ_bias = float(
        champion_playable_bias
        if champion_playable_bias is not None
        else champion_metrics.get("playable_bias", champion_metrics.get("bias", 0.0))
    )
    cand_bias = float(
        candidate_playable_bias
        if candidate_playable_bias is not None
        else candidate_metrics.get("playable_bias", candidate_metrics.get("bias", 0.0))
    )

    reasons: list[str] = []

    # 1. Delta check
    if oracle_delta <= 0.0:
        reasons.append(f"oracle formation XI regret did not improve ({oracle_delta:+.4f})")

    # 2. Bootstrap check
    resample_deltas = _filter_active_gw_deltas(
        gw_deltas,
        active_gameweeks=active_gameweeks,
        all_gameweeks=all_gameweeks,
    )
    bootstrap_p = None
    if resample_deltas is not None and len(resample_deltas) >= 15:
        bootstrap_p = block_bootstrap_win_probability(resample_deltas)
        if bootstrap_p < bootstrap_min_p:
            reasons.append(f"oracle bootstrap P {bootstrap_p:.3f} below required {bootstrap_min_p:.2f}")

    # 3. Playable pool signed bias
    bias_cap = min(abs(champ_bias) + bias_tol, bias_ceiling)
    if abs(cand_bias) > bias_cap:
        reasons.append(f"playable pool signed bias |{cand_bias:+.4f}| exceeded tolerance {bias_cap:.4f}")

    # 4. Captaincy regret tolerance
    if cand_cap > champ_cap + captain_regret_tol:
        reasons.append(f"captaincy regret regressed by {captain_regret_delta:+.4f} > {captain_regret_tol:+.4f}")

    passed = len(reasons) == 0
    return OracleEventGateVerdict(
        passed=passed,
        oracle_delta=oracle_delta,
        bootstrap_p=bootstrap_p,
        candidate_playable_bias=cand_bias,
        champion_playable_bias=champ_bias,
        captain_regret_delta=captain_regret_delta,
        reasons=tuple(reasons),
    )
