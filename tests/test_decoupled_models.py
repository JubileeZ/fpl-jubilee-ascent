"""Unit and integration tests for Decoupled Models and Tier 1 Minutes Gate.

Verifies:
1. Non-parametric ROC-AUC rank calculation and edge cases.
2. Multiclass Participation Brier score handling 3-way states (DNP, Start, Sub-in).
3. Active player pool conditioning and MAE/RMSE calculation.
4. Starter discrimination (60+ minutes) precision, recall, and F1.
5. Tier 1 Minutes Gate evaluation verdicts (pass, recall failure, brier regression, negative delta).
6. Extraction of standard minutes prediction frames from models.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from commands.evaluate_minutes import (
    MinutesGateVerdict,
    MinutesMetrics,
    compute_minutes_metrics,
    compute_roc_auc,
    evaluate_minutes_gate,
    extract_minutes_prediction_frame,
)
from models.base import BaseModel


# --- 1. ROC-AUC Tests ---

def test_compute_roc_auc_perfect() -> None:
    y_true = np.array([1, 1, 0, 0])
    y_score = np.array([0.9, 0.8, 0.2, 0.1])
    assert compute_roc_auc(y_true, y_score) == pytest.approx(1.0)


def test_compute_roc_auc_inverted() -> None:
    y_true = np.array([1, 1, 0, 0])
    y_score = np.array([0.1, 0.2, 0.8, 0.9])
    assert compute_roc_auc(y_true, y_score) == pytest.approx(0.0)


def test_compute_roc_auc_ties() -> None:
    y_true = np.array([1, 1, 0, 0])
    y_score = np.array([0.5, 0.5, 0.5, 0.5])
    assert compute_roc_auc(y_true, y_score) == pytest.approx(0.5)


def test_compute_roc_auc_single_class() -> None:
    y_true = np.array([1, 1, 1])
    y_score = np.array([0.9, 0.8, 0.7])
    assert compute_roc_auc(y_true, y_score) == pytest.approx(0.5)


# --- 2. Multiclass Brier Score & Minutes Metrics Tests ---

def test_brier_score_perfect_prediction() -> None:
    # 3 players: 1 DNP, 1 Start, 1 Sub
    df = pd.DataFrame({
        "projected_minutes": [0.0, 90.0, 20.0],
        "actual_minutes": [0.0, 90.0, 20.0],
        "p_dnp": [1.0, 0.0, 0.0],
        "p_start": [0.0, 1.0, 0.0],
        "p_sub_in": [0.0, 0.0, 1.0],
        "p_60_plus": [0.0, 1.0, 0.0],
        "actual_dnp": [1.0, 0.0, 0.0],
        "actual_start": [0.0, 1.0, 0.0],
        "actual_sub_in": [0.0, 0.0, 1.0],
    })
    metrics = compute_minutes_metrics(df)
    assert metrics.brier_score == pytest.approx(0.0)
    assert metrics.mae == pytest.approx(0.0)
    assert metrics.rmse == pytest.approx(0.0)
    assert metrics.bias == pytest.approx(0.0)
    assert metrics.starter_recall == pytest.approx(1.0)
    assert metrics.starter_precision == pytest.approx(1.0)
    assert metrics.starter_auc == pytest.approx(1.0)


def test_brier_score_uniform_prediction() -> None:
    # Uniform guess: (1/3, 1/3, 1/3)
    # Expected squared error per sample: (1 - 1/3)^2 + (0 - 1/3)^2 + (0 - 1/3)^2 = 4/9 + 1/9 + 1/9 = 6/9 = 2/3
    df = pd.DataFrame({
        "projected_minutes": [30.0],
        "actual_minutes": [90.0],
        "p_dnp": [1.0 / 3.0],
        "p_start": [1.0 / 3.0],
        "p_sub_in": [1.0 / 3.0],
        "p_60_plus": [0.33],
        "actual_dnp": [0.0],
        "actual_start": [1.0],
        "actual_sub_in": [0.0],
    })
    metrics = compute_minutes_metrics(df)
    assert metrics.brier_score == pytest.approx(2.0 / 3.0, abs=1e-4)


def test_brier_score_completely_inverted() -> None:
    # Completely wrong: predicts DNP=1.0 when actually Started
    df = pd.DataFrame({
        "projected_minutes": [0.0],
        "actual_minutes": [90.0],
        "p_dnp": [1.0],
        "p_start": [0.0],
        "p_sub_in": [0.0],
        "p_60_plus": [0.0],
        "actual_dnp": [0.0],
        "actual_start": [1.0],
        "actual_sub_in": [0.0],
    })
    metrics = compute_minutes_metrics(df)
    # (1 - 0)^2 + (0 - 1)^2 + (0 - 0)^2 = 2.0
    assert metrics.brier_score == pytest.approx(2.0)


def test_active_pool_filtering() -> None:
    # 2 active players, 1 unselected reserve (0 projected, 0 actual)
    df = pd.DataFrame({
        "projected_minutes": [80.0, 15.0, 0.0],
        "actual_minutes": [90.0, 0.0, 0.0],
        "p_dnp": [0.1, 0.8, 1.0],
        "p_start": [0.8, 0.0, 0.0],
        "p_sub_in": [0.1, 0.2, 0.0],
        "p_60_plus": [0.8, 0.0, 0.0],
        "actual_dnp": [0.0, 1.0, 1.0],
        "actual_start": [1.0, 0.0, 0.0],
        "actual_sub_in": [0.0, 0.0, 0.0],
    })
    metrics = compute_minutes_metrics(df)
    assert metrics.sample_count == 3
    assert metrics.active_count == 2
    # Active pool MAE = (|80-90| + |15-0|) / 2 = 25 / 2 = 12.5
    assert metrics.mae == pytest.approx(12.5)
    # Overall pool MAE = (10 + 15 + 0) / 3 = 25 / 3 = 8.333
    assert metrics.overall_mae == pytest.approx(25.0 / 3.0)


# --- 3. Tier 1 Minutes Gate Verdict Tests ---

def _sample_metrics(
    *,
    mae: float = 14.0,
    rmse: float = 22.0,
    bias: float = 0.5,
    brier: float = 0.3200,
    recall: float = 0.9200,
    auc: float = 0.9500,
) -> MinutesMetrics:
    return MinutesMetrics(
        sample_count=500,
        active_count=300,
        mae=mae,
        rmse=rmse,
        bias=bias,
        overall_mae=mae * 0.7,
        overall_rmse=rmse * 0.7,
        overall_bias=bias * 0.7,
        brier_score=brier,
        brier_start=brier * 0.5,
        brier_sub=brier * 0.2,
        brier_dnp=brier * 0.3,
        starter_auc=auc,
        starter_precision=0.88,
        starter_recall=recall,
        starter_f1=0.90,
        mean_projected=35.0,
        mean_actual=34.5,
    )


def test_minutes_gate_passes_superior_candidate() -> None:
    champ = _sample_metrics(mae=15.0, brier=0.3400, recall=0.9100)
    cand = _sample_metrics(mae=14.0, brier=0.3200, recall=0.9200)
    per_gw_deltas = [1.0] * 20

    verdict = evaluate_minutes_gate(cand, champ, per_gw_deltas)
    assert verdict.passed is True
    assert verdict.delta_mae == pytest.approx(1.0)
    assert verdict.bootstrap_p >= 0.60
    assert len(verdict.reasons) == 0


def test_minutes_gate_fails_negative_mae_delta() -> None:
    champ = _sample_metrics(mae=14.0)
    cand = _sample_metrics(mae=14.5)  # Worse MAE
    per_gw_deltas = [-0.5] * 20

    verdict = evaluate_minutes_gate(cand, champ, per_gw_deltas)
    assert verdict.passed is False
    assert any("does not improve" in r for r in verdict.reasons)


def test_minutes_gate_fails_starter_recall_regression() -> None:
    champ = _sample_metrics(mae=15.0, recall=0.9200)
    cand = _sample_metrics(mae=14.0, recall=0.9050)  # Drops recall by -0.015 > -0.005 tol
    per_gw_deltas = [1.0] * 20

    verdict = evaluate_minutes_gate(cand, champ, per_gw_deltas)
    assert verdict.passed is False
    assert any("starter recall regresses" in r for r in verdict.reasons)


def test_minutes_gate_fails_brier_regression() -> None:
    champ = _sample_metrics(mae=15.0, brier=0.3200)
    cand = _sample_metrics(mae=14.0, brier=0.3250)  # Degrades Brier by +0.005 > +0.002 tol
    per_gw_deltas = [1.0] * 20

    verdict = evaluate_minutes_gate(cand, champ, per_gw_deltas)
    assert verdict.passed is False
    assert any("Brier score regresses" in r for r in verdict.reasons)


def test_minutes_gate_fails_bias_guardrail() -> None:
    champ = _sample_metrics(mae=15.0, bias=0.20)
    cand = _sample_metrics(mae=14.0, bias=1.50)  # Bias 1.50 > 0.20 + 0.50 tol
    per_gw_deltas = [1.0] * 20

    verdict = evaluate_minutes_gate(cand, champ, per_gw_deltas)
    assert verdict.passed is False
    assert any("absolute bias" in r for r in verdict.reasons)


def test_minutes_gate_fails_nan_metrics() -> None:
    champ = _sample_metrics(mae=15.0)
    cand = _sample_metrics(mae=float("nan"))
    per_gw_deltas = [1.0] * 20

    verdict = evaluate_minutes_gate(cand, champ, per_gw_deltas)
    assert verdict.passed is False
    assert any("Candidate MAE does not improve" in r for r in verdict.reasons)


def test_active_pool_symmetric_mask() -> None:
    # Player 1: Cand projects 0, Champ projects 90, Actual 0
    # Player 2: Cand projects 80, Champ projects 80, Actual 80
    cand_eval = pd.DataFrame({
        "projected_minutes": [0.0, 80.0],
        "actual_minutes": [0.0, 80.0],
    })
    champ_eval = pd.DataFrame({
        "projected_minutes": [90.0, 80.0],
        "actual_minutes": [0.0, 80.0],
    })
    active_mask = (
        (cand_eval["projected_minutes"] > 0)
        | (champ_eval["projected_minutes"] > 0)
        | (cand_eval["actual_minutes"] > 0)
    )
    # Player 1 MUST be in the active mask despite candidate projecting 0 and actual being 0
    assert active_mask.iloc[0] is True or active_mask.iloc[0] == 1
    assert active_mask.sum() == 2


# --- 4. Model Prediction Frame Extraction Tests ---

def test_extract_minutes_prediction_frame() -> None:
    class DummyModel(BaseModel):
        @property
        def name(self) -> str:
            return "dummy"

        def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
            return pd.DataFrame({
                "player_id": [1, 2],
                "gameweek_id": [5, 5],
                "fixture_id": [10, 11],
                "projected_minutes": [85.0, 12.0],
                "p_dnp": [0.05, 0.80],
                "p_start": [0.90, 0.05],
                "p_sub_in": [0.05, 0.15],
                "p_60_if_start": [0.95, 0.10],
                "p_60_if_sub_in": [0.02, 0.00],
            })

    model = DummyModel()
    dummy_feat = pd.DataFrame({"player_id": [1, 2], "gameweek_id": [5, 5], "fixture_id": [10, 11]})
    out = extract_minutes_prediction_frame(model, dummy_feat, horizon=1)
    required = {
        "player_id", "gameweek_id", "fixture_id",
        "projected_minutes", "p_dnp", "p_start", "p_sub_in", "p_60_plus"
    }
    assert required.issubset(out.columns)
    assert len(out) == 2
    assert out.loc[0, "p_60_plus"] > 0.80
    assert out.loc[1, "p_60_plus"] < 0.10


def test_extract_minutes_prediction_frame_base_minutes_model() -> None:
    class DummyMinutesModel:
        @property
        def name(self) -> str:
            return "dummy_minutes"

        def predict_minutes(self, features_df: pd.DataFrame, horizon: int = 1) -> pd.DataFrame:
            return pd.DataFrame({
                "player_id": [101, 102],
                "gameweek_id": [6, 6],
                "projected_minutes": [90.0, 45.0],
                "p_dnp": [0.02, 0.10],
                "p_start": [0.95, 0.40],
                "p_sub_in": [0.03, 0.50],
                "p_60_plus": [0.92, 0.35],
            })

    model = DummyMinutesModel()
    dummy_feat = pd.DataFrame({"player_id": [101, 102], "gameweek_id": [6, 6], "fixture_id": [50, 51]})
    out = extract_minutes_prediction_frame(model, dummy_feat, horizon=1)
    assert out["fixture_id"].tolist() == [50, 51]
    assert out["projected_minutes"].tolist() == [90.0, 45.0]
    assert out["p_start"].tolist() == [0.95, 0.40]


def test_run_minutes_walkforward_evaluation_live_subset(tmp_path: Path) -> None:
    data_dir = Path("data/processed")
    if not (data_dir / "player_performances.parquet").exists():
        pytest.skip("Live processed data not present")

    from commands.evaluate_minutes import run_minutes_walkforward_evaluation
    verdict = run_minutes_walkforward_evaluation(
        candidate_model_name="def_xg_shrink_challenger",
        champion_model_name="learned_start_challenger",
        data_dir=data_dir,
        start_gw=5,
        end_gw=5,
    )
    assert isinstance(verdict, MinutesGateVerdict)
    assert verdict.candidate_metrics.sample_count > 0
    assert 0.0 <= verdict.candidate_metrics.brier_score <= 2.0
    assert 0.0 <= verdict.candidate_metrics.starter_auc <= 1.0
