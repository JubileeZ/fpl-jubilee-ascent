"""Standalone Tier 1 Minutes Gate CLI and evaluation engine.

Evaluates standalone Minutes Projection Models (M_mins) or monolithic models
against ground truth match minutes and participation status from player_performances.parquet.

Metrics:
1. Minutes Error: MAE and RMSE on active players (xmins > 0 or actual > 0).
2. Multiclass Participation Brier Score across (p_dnp, p_start, p_sub_in).
3. Starter Discrimination: ROC-AUC, Precision, Recall on 60+ minute appearances.
4. Tier 1 Minutes Gate:
   - Δ_MAE > 0.0 mins (Candidate improves on active pool MAE).
   - Block bootstrap P(Δ_MAE > 0) >= 0.60 (B=20,000 draws, block L=3 GWs).
   - Non-regressing Brier score: Brier_cand <= Brier_champ + 0.002.
   - Starter Recall tolerance: Recall_cand >= Recall_champ - 0.005.
   - Absolute Bias guardrail: |Bias_cand| <= |Bias_champ| + 0.50 mins.
   - Starter ROC-AUC tolerance: AUC_cand >= AUC_champ - 0.010.

Usage:
    uv run python -m commands.evaluate_minutes --model <cand> --champion <champ> --data-dir data/processed
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import logging
from pathlib import Path
import sys
from typing import Any, Sequence

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backtesting.promotion import (
    BOOTSTRAP_BLOCK_GWS,
    BOOTSTRAP_DRAWS,
    BOOTSTRAP_MIN_P,
    block_bootstrap_win_probability,
)
from backtesting.walkforward import load_gameweek_deadlines
from clients.env_loader import configure_utf8_stdio, load_env
from features.builder import build_features, history_before_target
from models import get_model
from models.selection import load_model_selection

logger = logging.getLogger(__name__)

# Constants for Tier 1 Minutes Gate
MINUTES_BRIER_REL_TOL = 0.002
MINUTES_RECALL_TOL = 0.005
MINUTES_BIAS_ABS_TOL = 0.50
MINUTES_AUC_TOL = 0.010


@dataclass(frozen=True)
class MinutesMetrics:
    """Statistical evaluation metrics for minutes and participation predictions."""

    sample_count: int
    active_count: int
    # Active pool metrics (projected > 0 or actual > 0)
    mae: float
    rmse: float
    bias: float
    # Overall pool metrics
    overall_mae: float
    overall_rmse: float
    overall_bias: float
    # Multiclass Brier score across (p_dnp, p_start, p_sub_in)
    brier_score: float
    brier_start: float
    brier_sub: float
    brier_dnp: float
    # Starter discrimination (60+ minutes)
    starter_auc: float
    starter_precision: float
    starter_recall: float
    starter_f1: float
    # Mean predictions
    mean_projected: float
    mean_actual: float


@dataclass(frozen=True)
class MinutesGateVerdict:
    """Verdict for standalone Tier 1 Minutes Gate evaluation."""

    passed: bool
    reasons: tuple[str, ...]
    delta_mae: float
    bootstrap_p: float
    brier_delta: float
    recall_delta: float
    auc_delta: float
    candidate_metrics: MinutesMetrics
    champion_metrics: MinutesMetrics

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "reasons": list(self.reasons),
            "delta_mae": self.delta_mae,
            "bootstrap_p": self.bootstrap_p,
            "brier_delta": self.brier_delta,
            "recall_delta": self.recall_delta,
            "auc_delta": self.auc_delta,
            "candidate": asdict(self.candidate_metrics),
            "champion": asdict(self.champion_metrics),
        }


def compute_roc_auc(y_true: np.ndarray, y_score: np.ndarray) -> float:
    """Compute non-parametric ROC-AUC via Mann-Whitney U rank statistic."""
    y_true_raw = np.asarray(y_true)
    y_score_raw = np.asarray(y_score)
    valid = ~pd.isna(y_true_raw) & ~pd.isna(y_score_raw)
    if not np.any(valid):
        return 0.5

    y_true = y_true_raw[valid].astype(bool)
    y_score = y_score_raw[valid].astype(float)

    n_pos = int(np.sum(y_true))
    n_neg = int(len(y_true) - n_pos)

    if n_pos == 0 or n_neg == 0:
        return 0.5

    # Ranks (1-based), handling ties with average rank
    order = np.argsort(y_score)
    ranks = np.empty_like(order, dtype=float)
    ranks[order] = np.arange(1, len(y_score) + 1)

    # Resolve tied scores
    sorted_scores = y_score[order]
    tie_starts = np.where(np.diff(sorted_scores) == 0)[0]
    if len(tie_starts) > 0:
        i = 0
        while i < len(sorted_scores):
            j = i
            while j < len(sorted_scores) and sorted_scores[j] == sorted_scores[i]:
                j += 1
            if j > i + 1:
                ranks[order[i:j]] = (i + 1 + j) / 2.0
            i = j

    rank_sum_pos = float(np.sum(ranks[y_true]))
    u_stat = rank_sum_pos - (n_pos * (n_pos + 1)) / 2.0
    return float(u_stat / (n_pos * n_neg))


def compute_minutes_metrics(df_eval: pd.DataFrame) -> MinutesMetrics:
    """Calculate comprehensive minutes and participation metrics on an evaluation DataFrame.

    Required columns:
        'projected_minutes', 'actual_minutes',
        'p_dnp', 'p_start', 'p_sub_in', 'p_60_plus',
        'actual_start', 'actual_sub_in', 'actual_dnp'
    """
    n = len(df_eval)
    if n == 0:
        raise ValueError("Cannot compute metrics on empty evaluation DataFrame")

    # Active pool filter: player was projected to play (>0) OR actually played (>0)
    active_mask = (df_eval["projected_minutes"] > 0) | (df_eval["actual_minutes"] > 0)
    df_active = df_eval[active_mask] if active_mask.any() else df_eval

    # Active errors
    act_err = df_active["projected_minutes"] - df_active["actual_minutes"]
    mae = float(act_err.abs().mean())
    rmse = float(np.sqrt(np.mean(act_err**2)))
    bias = float(act_err.mean())

    # Overall errors
    all_err = df_eval["projected_minutes"] - df_eval["actual_minutes"]
    overall_mae = float(all_err.abs().mean())
    overall_rmse = float(np.sqrt(np.mean(all_err**2)))
    overall_bias = float(all_err.mean())

    # Multiclass Brier score across participation states
    # Normalize probabilities defensively to guarantee partition of unity (sum=1.0)
    p_dnp = df_eval["p_dnp"].fillna(0.0).clip(lower=0.0)
    p_start = df_eval["p_start"].fillna(0.0).clip(lower=0.0)
    p_sub = df_eval["p_sub_in"].fillna(0.0).clip(lower=0.0)
    p_sum = p_dnp + p_start + p_sub

    zero_mask = p_sum <= 1e-9
    p_dnp = p_dnp.where(~zero_mask, 1.0)
    p_sum = p_sum.where(~zero_mask, 1.0)

    p_dnp = p_dnp / p_sum
    p_start = p_start / p_sum
    p_sub = p_sub / p_sum

    brier_start = float(np.mean((p_start - df_eval["actual_start"]) ** 2))
    brier_sub = float(np.mean((p_sub - df_eval["actual_sub_in"]) ** 2))
    brier_dnp = float(np.mean((p_dnp - df_eval["actual_dnp"]) ** 2))
    brier_score = brier_start + brier_sub + brier_dnp

    # Starter discrimination (60+ minutes)
    y_60 = (df_eval["actual_minutes"] >= 60).to_numpy()
    p_60 = df_eval["p_60_plus"].to_numpy()

    starter_auc = compute_roc_auc(y_60, p_60)

    # Classification at 0.5 threshold
    pred_60 = p_60 >= 0.5
    tp = int(np.sum(pred_60 & y_60))
    fp = int(np.sum(pred_60 & ~y_60))
    fn = int(np.sum(~pred_60 & y_60))

    precision = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
    recall = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
    f1 = float(2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    return MinutesMetrics(
        sample_count=n,
        active_count=int(active_mask.sum()),
        mae=mae,
        rmse=rmse,
        bias=bias,
        overall_mae=overall_mae,
        overall_rmse=overall_rmse,
        overall_bias=overall_bias,
        brier_score=brier_score,
        brier_start=brier_start,
        brier_sub=brier_sub,
        brier_dnp=brier_dnp,
        starter_auc=starter_auc,
        starter_precision=precision,
        starter_recall=recall,
        starter_f1=f1,
        mean_projected=float(df_eval["projected_minutes"].mean()),
        mean_actual=float(df_eval["actual_minutes"].mean()),
    )


def evaluate_minutes_gate(
    candidate_metrics: MinutesMetrics,
    champion_metrics: MinutesMetrics,
    per_gw_deltas: Sequence[float],
) -> MinutesGateVerdict:
    """Evaluate candidate minutes predictions against champion under the Tier 1 Minutes Gate."""
    reasons: list[str] = []

    # 1. Primary MAE improvement (Δ_MAE = Champion MAE - Candidate MAE)
    delta_mae = champion_metrics.mae - candidate_metrics.mae
    if np.isnan(delta_mae) or delta_mae <= 0.0:
        reasons.append(
            f"Candidate MAE does not improve on Champion ({candidate_metrics.mae:.3f} vs {champion_metrics.mae:.3f}, delta: {delta_mae:+.3f})"
        )

    # 2. Block bootstrap significance P(Δ_MAE > 0) >= 0.60
    bootstrap_p = block_bootstrap_win_probability(
        per_gw_deltas, draws=BOOTSTRAP_DRAWS, block=BOOTSTRAP_BLOCK_GWS
    )
    if np.isnan(bootstrap_p) or bootstrap_p < BOOTSTRAP_MIN_P:
        reasons.append(
            f"Bootstrap win probability {bootstrap_p:.3f} below required threshold {BOOTSTRAP_MIN_P:.2f}"
        )

    # 3. Multiclass Brier score non-regression
    brier_delta = candidate_metrics.brier_score - champion_metrics.brier_score
    if np.isnan(brier_delta) or brier_delta > MINUTES_BRIER_REL_TOL:
        reasons.append(
            f"Candidate Brier score regresses by {brier_delta:+.4f} (allowed tolerance +{MINUTES_BRIER_REL_TOL})"
        )

    # 4. Starter Recall tolerance (60+ minutes)
    recall_delta = candidate_metrics.starter_recall - champion_metrics.starter_recall
    if np.isnan(recall_delta) or recall_delta < -MINUTES_RECALL_TOL:
        reasons.append(
            f"Candidate starter recall regresses by {recall_delta:+.4f} (allowed tolerance -{MINUTES_RECALL_TOL})"
        )

    # 5. Absolute Bias guardrail
    cand_abs_bias = abs(candidate_metrics.bias)
    champ_abs_bias = abs(champion_metrics.bias)
    if np.isnan(cand_abs_bias) or np.isnan(champ_abs_bias) or cand_abs_bias > champ_abs_bias + MINUTES_BIAS_ABS_TOL:
        reasons.append(
            f"Candidate absolute bias |{candidate_metrics.bias:+.2f}| exceeds Champion |{champion_metrics.bias:+.2f}| + {MINUTES_BIAS_ABS_TOL:.2f}"
        )

    # 6. Starter ROC-AUC tolerance
    auc_delta = candidate_metrics.starter_auc - champion_metrics.starter_auc
    if np.isnan(auc_delta) or auc_delta < -MINUTES_AUC_TOL:
        reasons.append(
            f"Candidate starter AUC regresses by {auc_delta:+.4f} (allowed tolerance -{MINUTES_AUC_TOL})"
        )

    passed = len(reasons) == 0
    return MinutesGateVerdict(
        passed=passed,
        reasons=tuple(reasons),
        delta_mae=float(delta_mae),
        bootstrap_p=float(bootstrap_p),
        brier_delta=float(brier_delta),
        recall_delta=float(recall_delta),
        auc_delta=float(auc_delta),
        candidate_metrics=candidate_metrics,
        champion_metrics=champion_metrics,
    )


def extract_minutes_prediction_frame(
    model: Any,
    features_df: pd.DataFrame,
    horizon: int = 1,
) -> pd.DataFrame:
    """Extract standard minutes and participation columns from model predictions.

    Guarantees the presence of:
        'player_id', 'gameweek_id', 'fixture_id', 'projected_minutes',
        'p_dnp', 'p_start', 'p_sub_in', 'p_60_plus'
    """
    if hasattr(model, "predict_minutes"):
        preds = model.predict_minutes(features_df, horizon=horizon)
    else:
        preds = model.predict(features_df, horizon=horizon)

    out = pd.DataFrame()
    out["player_id"] = preds["player_id"].to_numpy().astype(int)
    out["gameweek_id"] = preds["gameweek_id"].to_numpy().astype(int)
    if "fixture_id" in preds.columns:
        out["fixture_id"] = preds["fixture_id"].to_numpy().astype(int)
    elif "fixture_id" in features_df.columns:
        out["fixture_id"] = features_df["fixture_id"].to_numpy().astype(int)
    else:
        out["fixture_id"] = 0

    out["projected_minutes"] = preds["projected_minutes"].to_numpy().astype(float)

    # Participation probabilities
    if {"p_dnp", "p_start", "p_sub_in"}.issubset(preds.columns):
        out["p_dnp"] = preds["p_dnp"].to_numpy().astype(float)
        out["p_start"] = preds["p_start"].to_numpy().astype(float)
        out["p_sub_in"] = preds["p_sub_in"].to_numpy().astype(float)
    else:
        # Fallback heuristic for models without explicit participation states
        p_start = np.clip(out["projected_minutes"] / 80.0, 0.0, 0.95)
        p_sub = np.clip((out["projected_minutes"] - 40.0) / 40.0, 0.0, 0.3)
        p_dnp = np.clip(1.0 - p_start - p_sub, 0.0, 1.0)
        norm = p_start + p_sub + p_dnp
        out["p_start"] = p_start / norm
        out["p_sub_in"] = p_sub / norm
        out["p_dnp"] = p_dnp / norm

    # P(60+ minutes)
    if "p_60_plus" in preds.columns:
        out["p_60_plus"] = preds["p_60_plus"].to_numpy().astype(float)
    elif {"p_60_if_start", "p_60_if_sub_in"}.issubset(preds.columns):
        p_60_start = preds["p_60_if_start"].fillna(0.0).to_numpy()
        p_60_sub = preds["p_60_if_sub_in"].fillna(0.0).to_numpy()
        out["p_60_plus"] = (
            out["p_start"].to_numpy() * p_60_start
            + out["p_sub_in"].to_numpy() * p_60_sub
        ).astype(float)
    else:
        # Logistic approximation around 60 minutes
        out["p_60_plus"] = 1.0 / (1.0 + np.exp(-(out["projected_minutes"] - 50.0) / 10.0))

    return out


def build_minutes_evaluation_frame(
    preds_df: pd.DataFrame,
    df_perf: pd.DataFrame,
    target_gw: int,
) -> pd.DataFrame:
    """Merge predictions with actual performances for target gameweek with ground truth participation."""
    gw_perf = df_perf[df_perf["gameweek_id"] == target_gw].copy()

    # Ground truth participation states
    has_starts = "starts" in gw_perf.columns
    if has_starts:
        actual_start = (gw_perf["starts"] == 1).astype(float)
        actual_sub_in = ((gw_perf["starts"] == 0) & (gw_perf["minutes"] > 0)).astype(float)
        actual_dnp = ((gw_perf["starts"] == 0) & (gw_perf["minutes"] == 0)).astype(float)
    else:
        # Fallback when starts column unavailable
        actual_start = (gw_perf["minutes"] >= 60).astype(float)
        actual_sub_in = ((gw_perf["minutes"] > 0) & (gw_perf["minutes"] < 60)).astype(float)
        actual_dnp = (gw_perf["minutes"] == 0).astype(float)

    perf_cols = gw_perf[["player_id", "gameweek_id", "fixture_id", "minutes"]].copy()
    perf_cols["actual_start"] = actual_start
    perf_cols["actual_sub_in"] = actual_sub_in
    perf_cols["actual_dnp"] = actual_dnp
    perf_cols = perf_cols.rename(columns={"minutes": "actual_minutes"})

    merged = preds_df.merge(
        perf_cols,
        on=["player_id", "gameweek_id", "fixture_id"],
        how="left",
    )

    merged["actual_minutes"] = merged["actual_minutes"].fillna(0.0).astype(float)
    merged["actual_start"] = merged["actual_start"].fillna(0.0).astype(float)
    merged["actual_sub_in"] = merged["actual_sub_in"].fillna(0.0).astype(float)
    merged["actual_dnp"] = merged["actual_dnp"].fillna(1.0).astype(float)

    return merged


def run_minutes_walkforward_evaluation(
    *,
    candidate_model_name: str,
    champion_model_name: str,
    data_dir: Path,
    start_gw: int | None = None,
    end_gw: int | None = None,
) -> MinutesGateVerdict:
    """Execute walk-forward minutes evaluation comparing candidate to champion across gameweeks."""
    perf_path = data_dir / "player_performances.parquet"
    if not perf_path.exists():
        raise FileNotFoundError(f"Missing player_performances.parquet in {data_dir}")

    df_perf = pd.read_parquet(perf_path)
    completed_gws = sorted(df_perf["gameweek_id"].dropna().unique().astype(int).tolist())
    if not completed_gws:
        raise ValueError(f"No completed gameweeks found in {perf_path}")

    first_gw = completed_gws[0] if start_gw is None else max(start_gw, completed_gws[0])
    last_gw = completed_gws[-1] if end_gw is None else min(end_gw, completed_gws[-1])
    target_gws = [gw for gw in completed_gws if first_gw <= gw <= last_gw]

    cand_model = get_model(candidate_model_name)
    champ_model = get_model(champion_model_name)

    cand_frames: list[pd.DataFrame] = []
    champ_frames: list[pd.DataFrame] = []
    per_gw_deltas: list[float] = []

    gameweek_deadlines = load_gameweek_deadlines(data_dir)

    for gw in target_gws:
        deadline = gameweek_deadlines.get(gw)
        df_feat = build_features(data_dir, gw, as_of_gw=gw, target_deadline=deadline)
        hist_before = history_before_target(
            df_perf,
            gw,
            deadline,
            require_kickoff_time=False,
        )

        cand_model.fit(hist_before)
        champ_model.fit(hist_before)

        cand_preds = extract_minutes_prediction_frame(cand_model, df_feat, horizon=1)
        champ_preds = extract_minutes_prediction_frame(champ_model, df_feat, horizon=1)

        cand_eval = build_minutes_evaluation_frame(cand_preds, df_perf, gw)
        champ_eval = build_minutes_evaluation_frame(champ_preds, df_perf, gw)

        cand_frames.append(cand_eval)
        champ_frames.append(champ_eval)

        # Symmetric active pool: player was projected by candidate OR projected by champion OR actually played
        active_mask = (
            (cand_eval["projected_minutes"] > 0)
            | (champ_eval["projected_minutes"] > 0)
            | (cand_eval["actual_minutes"] > 0)
        )
        if not active_mask.any():
            per_gw_deltas.append(0.0)
            continue

        c_mae = (
            cand_eval.loc[active_mask, "projected_minutes"]
            - cand_eval.loc[active_mask, "actual_minutes"]
        ).abs().mean()
        ch_mae = (
            champ_eval.loc[active_mask, "projected_minutes"]
            - champ_eval.loc[active_mask, "actual_minutes"]
        ).abs().mean()
        per_gw_deltas.append(float(ch_mae - c_mae))

    full_cand = pd.concat(cand_frames, ignore_index=True)
    full_champ = pd.concat(champ_frames, ignore_index=True)

    cand_metrics = compute_minutes_metrics(full_cand)
    champ_metrics = compute_minutes_metrics(full_champ)

    return evaluate_minutes_gate(cand_metrics, champ_metrics, per_gw_deltas)


def main() -> None:
    load_env()
    configure_utf8_stdio()

    parser = argparse.ArgumentParser(
        description="Standalone Tier 1 Minutes Gate evaluation for Minutes Projection Models."
    )
    parser.add_argument("--model", required=True, help="Candidate model identifier or class name")
    parser.add_argument("--champion", default=None, help="Champion model identifier (default: active Champion)")
    parser.add_argument("--data-dir", default="data/processed", help="Path to processed data directory")
    parser.add_argument("--start-gw", type=int, default=None, help="Starting gameweek for evaluation")
    parser.add_argument("--end-gw", type=int, default=None, help="Ending gameweek for evaluation")
    parser.add_argument("--output-json", default=None, help="Path to write structured JSON evaluation output")
    parser.add_argument("--format", choices=["table", "json"], default="table", help="Console output format")

    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    if not data_dir.is_absolute():
        data_dir = PROJECT_ROOT / data_dir

    champ_name = args.champion
    if not champ_name:
        selection = load_model_selection()
        champ_name = selection.champion

    logger.info(
        "Evaluating Standalone Minutes Gate: %s (Cand) vs %s (Champ) on %s",
        args.model,
        champ_name,
        data_dir,
    )

    verdict = run_minutes_walkforward_evaluation(
        candidate_model_name=args.model,
        champion_model_name=champ_name,
        data_dir=data_dir,
        start_gw=args.start_gw,
        end_gw=args.end_gw,
    )

    result_dict = verdict.to_dict()

    if args.output_json:
        out_path = Path(args.output_json)
        if not out_path.is_absolute():
            out_path = PROJECT_ROOT / out_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result_dict, f, indent=2)
        logger.info("Saved evaluation JSON to %s", out_path)

    if args.format == "json":
        print(json.dumps(result_dict, indent=2))
        return

    # Table format
    print("\n" + "=" * 76)
    print(f" STANDALONE TIER 1 MINUTES GATE: {args.model} vs {champ_name}")
    print("=" * 76)
    print(f" Gate Verdict: {'PASS' if verdict.passed else 'FAIL'}")
    print(f" Bootstrap Win Prob: {verdict.bootstrap_p:.3f} (Required: >= {BOOTSTRAP_MIN_P:.2f})")
    print(f" Active Pool MAE:    Cand {verdict.candidate_metrics.mae:.3f} | Champ {verdict.champion_metrics.mae:.3f} | Δ {verdict.delta_mae:+.3f} mins")
    print(f" Active Pool RMSE:   Cand {verdict.candidate_metrics.rmse:.3f} | Champ {verdict.champion_metrics.rmse:.3f}")
    print(f" Minutes Bias:       Cand {verdict.candidate_metrics.bias:+.3f} | Champ {verdict.champion_metrics.bias:+.3f}")
    print(f" Brier Score:        Cand {verdict.candidate_metrics.brier_score:.4f} | Champ {verdict.champion_metrics.brier_score:.4f} | Δ {verdict.brier_delta:+.4f}")
    print(f" Starter Recall 60+: Cand {verdict.candidate_metrics.starter_recall:.4f} | Champ {verdict.champion_metrics.starter_recall:.4f} | Δ {verdict.recall_delta:+.4f}")
    print(f" Starter ROC-AUC:    Cand {verdict.candidate_metrics.starter_auc:.4f} | Champ {verdict.champion_metrics.starter_auc:.4f} | Δ {verdict.auc_delta:+.4f}")

    if verdict.reasons:
        print("\n Failure Reasons:")
        for r in verdict.reasons:
            print(f"  - {r}")
    print("=" * 76 + "\n")


if __name__ == "__main__":
    main()
