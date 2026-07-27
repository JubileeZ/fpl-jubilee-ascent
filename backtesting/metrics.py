"""Decision-aware metrics for player/gameweek projection backtests."""

from collections.abc import Iterable

import numpy as np
import pandas as pd


_MINUTE_BAND_LABELS = ("0", "1-59", "60+")
_LEDGER_COMPONENTS = (
    "xp_minutes",
    "xp_goals",
    "xp_assists",
    "xp_clean_sheet",
    "xp_conceded",
    "xp_saves",
    "xp_penalties_saved",
    "xp_penalties_missed",
    "xp_own_goals",
    "xp_yellow_cards",
    "xp_red_cards",
    "xp_defcon",
    "xp_bonus",
)


def _top_k_stats(group: pd.DataFrame, k: int) -> tuple[float, float]:
    count = min(k, len(group))
    if count == 0:
        return 0.0, 0.0
    predicted = group.nlargest(count, "projected_points")
    actual = group.nlargest(count, "actual_points")
    predicted_ids = set(predicted["player_id"])
    actual_ids = set(actual["player_id"])
    overlap = len(predicted_ids & actual_ids) / count
    regret = float(actual["actual_points"].sum() - predicted["actual_points"].sum())
    return overlap, regret


def _minute_bands(minutes: pd.Series) -> pd.Categorical:
    return pd.cut(
        minutes,
        bins=[-0.1, 0.0, 59.999, float("inf")],
        labels=_MINUTE_BAND_LABELS,
    )


def _validate_component_ledger(df_eval: pd.DataFrame) -> None:
    """Reject predictions or actuals that do not reconcile to total points."""
    predicted_columns = [component for component in _LEDGER_COMPONENTS if component in df_eval.columns]
    actual_columns = [f"actual_{component}" for component in _LEDGER_COMPONENTS if f"actual_{component}" in df_eval.columns]
    complete_ledger = (
        len(predicted_columns) == len(_LEDGER_COMPONENTS)
        and len(actual_columns) == len(_LEDGER_COMPONENTS)
    )
    if complete_ledger:
        predicted_residual = df_eval["projected_points"] - df_eval[predicted_columns].sum(axis=1)
        if not np.allclose(predicted_residual, 0.0, atol=1e-9):
            raise ValueError("Predicted component ledger does not reconcile to projected_points")
        actual_residual = df_eval["actual_points"] - df_eval[actual_columns].sum(axis=1)
        if not np.allclose(actual_residual, 0.0, atol=1e-9):
            raise ValueError("Actual component ledger does not reconcile to actual_points")


def evaluate_predictions(
    df_eval: pd.DataFrame,
    top_k_values: Iterable[int] = (11, 15),
) -> dict[str, object]:
    """Calculate forecast, ranking, and shortlist metrics.

    ``df_eval`` must already be at one row per player/gameweek. Missing actual
    rows should be represented as zero points before calling this function.
    """
    required = {"player_id", "gameweek", "projected_points", "actual_points"}
    missing = required.difference(df_eval.columns)
    if missing:
        raise ValueError(f"Missing evaluation columns: {sorted(missing)}")
    if df_eval.empty:
        raise ValueError("Cannot evaluate an empty prediction frame")

    _validate_component_ledger(df_eval)
    errors = df_eval["projected_points"] - df_eval["actual_points"]
    correlations: list[float] = []
    undefined_rank_gameweeks = 0
    for _, group in df_eval.groupby("gameweek"):
        if len(group) < 2:
            undefined_rank_gameweeks += 1
            continue
        correlation = group["projected_points"].corr(group["actual_points"], method="spearman")
        if pd.isna(correlation):
            undefined_rank_gameweeks += 1
        else:
            correlations.append(float(correlation))

    position_metrics: dict[str, dict[str, float]] = {}
    if "position_id" in df_eval.columns:
        for position_id, group in df_eval.groupby("position_id"):
            position_errors = group["projected_points"] - group["actual_points"]
            position_metrics[str(position_id)] = {
                "sample_count": float(len(group)),
                "mae": float(position_errors.abs().mean()),
                "bias": float(position_errors.mean()),
            }

    minutes_band_metrics: dict[str, dict[str, float]] = {}
    if "actual_minutes" in df_eval.columns:
        bands = _minute_bands(df_eval["actual_minutes"])
        for band, group in df_eval.groupby(bands, observed=True):
            band_errors = group["projected_points"] - group["actual_points"]
            minutes_band_metrics[str(band)] = {
                "sample_count": float(len(group)),
                "mae": float(band_errors.abs().mean()),
                "bias": float(band_errors.mean()),
            }

    minutes_forecast_metrics: dict[str, object] = {}
    if {"projected_minutes", "actual_minutes"}.issubset(df_eval.columns):
        minute_errors = df_eval["projected_minutes"] - df_eval["actual_minutes"]
        by_actual_band: dict[str, dict[str, float]] = {}
        for band, group in df_eval.groupby(_minute_bands(df_eval["actual_minutes"]), observed=True):
            band_errors = group["projected_minutes"] - group["actual_minutes"]
            by_actual_band[str(band)] = {
                "sample_count": float(len(group)),
                "mean_projected": float(group["projected_minutes"].mean()),
                "mean_actual": float(group["actual_minutes"].mean()),
                "mae": float(band_errors.abs().mean()),
                "bias": float(band_errors.mean()),
            }
        minutes_forecast_metrics = {
            "mean_projected": float(df_eval["projected_minutes"].mean()),
            "mean_actual": float(df_eval["actual_minutes"].mean()),
            "mae": float(minute_errors.abs().mean()),
            "bias": float(minute_errors.mean()),
            "rmse": float(np.sqrt(np.mean(minute_errors**2))),
            "by_actual_band": by_actual_band,
        }

    component_metrics: dict[str, dict[str, float]] = {}
    component_keys = list(_LEDGER_COMPONENTS)
    for comp in component_keys:
        act_col = f"actual_{comp}"
        if comp in df_eval.columns and act_col in df_eval.columns:
            comp_errors = df_eval[comp] - df_eval[act_col]
            component_metrics[comp] = {
                "mean_projected": float(df_eval[comp].mean()),
                "mean_actual": float(df_eval[act_col].mean()),
                "mae": float(comp_errors.abs().mean()),
                "bias": float(comp_errors.mean()),
                "rmse": float(np.sqrt(np.mean(comp_errors**2))),
            }

    metrics: dict[str, object] = {
        "sample_count": int(len(df_eval)),
        "mae": float(errors.abs().mean()),
        "rmse": float(np.sqrt(np.mean(errors**2))),
        "bias": float(errors.mean()),
        "spearman": float(np.mean(correlations)) if correlations else None,
        "valid_rank_gameweeks": len(correlations),
        "undefined_rank_gameweeks": undefined_rank_gameweeks,
        "samples_by_gameweek": {
            int(gameweek): int(len(group))
            for gameweek, group in df_eval.groupby("gameweek")
        },
        "position_metrics": position_metrics,
        "minutes_band_metrics": minutes_band_metrics,
        "minutes_forecast_metrics": minutes_forecast_metrics,
        "component_metrics": component_metrics,
    }

    for k in top_k_values:
        overlaps: list[float] = []
        regrets: list[float] = []
        for _, group in df_eval.groupby("gameweek"):
            overlap, regret = _top_k_stats(group, k)
            if len(group) > 0:
                overlaps.append(overlap)
                regrets.append(regret)
        metrics[f"top_{k}_overlap"] = float(np.mean(overlaps)) if overlaps else None
        metrics[f"top_{k}_regret"] = float(np.mean(regrets)) if regrets else None

    return metrics
