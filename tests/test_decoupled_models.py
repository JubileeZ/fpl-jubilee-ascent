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


# --- 5. Ticket #165: Composite Model Architecture & Parity Tests ---

def _load_prototype_decoupled():
    import importlib.util
    import sys
    path = Path("docs/research/decoupled-projection-architecture/prototype_decoupled.py")
    spec = importlib.util.spec_from_file_location("prototype_decoupled", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["prototype_decoupled"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_composite_projection_model_satisfies_contract() -> None:
    mod = _load_prototype_decoupled()
    from features.contracts import assert_projection_contract

    df_feat = pd.DataFrame({
        "player_id": [1, 2, 3],
        "gameweek_id": [6, 6, 6],
        "fixture_id": [10, 11, 12],
        "position_id": [2, 3, 4],
        "club_id": [1, 2, 3],
        "opponent_id": [4, 5, 6],
        "is_home": [True, False, True],
        "per90_xg": [0.10, 0.40, 0.60],
        "per90_xa": [0.05, 0.30, 0.15],
        "per90_goals_conceded": [1.1, 1.3, 1.2],
        "difficulty": [2.0, 3.0, 4.0],
        "p_start": [0.90, 0.85, 0.95],
        "p_sub_in": [0.05, 0.10, 0.05],
        "p_dnp": [0.05, 0.05, 0.00],
        "xmins_if_start": [85.0, 75.0, 90.0],
        "xmins_if_sub_in": [15.0, 20.0, 15.0],
    })

    composite = mod.resolve_composite_spec("composite:learned_start:def_xg_shrink")
    res = composite.predict(df_feat, horizon=1)

    assert_projection_contract(res)
    assert len(res) == 3
    components = [c for c in res.columns if c.startswith("xp_")]
    assert len(components) == 13
    assert (res["projected_points"] - res[components].sum(axis=1)).abs().max() < 1e-9


def test_states_from_external_minutes_deterministic() -> None:
    mod = _load_prototype_decoupled()
    composite_cls = mod.CompositeProjectionModel

    df_feat = pd.DataFrame({
        "player_id": [10, 20, 30, 40],
        "gameweek_id": [7, 7, 7, 7],
        "fixture_id": [101, 102, 103, 104],
        "external_xmins": [90.0, 0.0, 45.0, np.nan],
    })

    states1 = composite_cls._states_from_external_minutes(df_feat, horizon=1)
    states2 = composite_cls._states_from_external_minutes(df_feat, horizon=1)

    pd.testing.assert_frame_equal(states1.frame, states2.frame)

    p10 = states1.frame.loc[states1.frame["player_id"] == 10].iloc[0]
    assert p10["p_start"] > 0.95
    assert p10["p_dnp"] < 0.05
    assert p10["p_sub_in"] == pytest.approx(0.0)
    assert p10["projected_minutes"] == pytest.approx(90.0)
    assert p10["p_60_plus"] == pytest.approx(0.99)

    p20 = states1.frame.loc[states1.frame["player_id"] == 20].iloc[0]
    assert p20["p_dnp"] == pytest.approx(1.0)
    assert p20["p_start"] == pytest.approx(0.0)
    assert p20["p_sub_in"] == pytest.approx(0.0)
    assert p20["projected_minutes"] == pytest.approx(0.0)
    assert p20["p_60_plus"] == pytest.approx(0.0)

    p30 = states1.frame.loc[states1.frame["player_id"] == 30].iloc[0]
    assert p30["p_start"] > 0.0
    assert p30["p_sub_in"] > 0.0
    assert p30["projected_minutes"] == pytest.approx(45.0)

    p40 = states1.frame.loc[states1.frame["player_id"] == 40].iloc[0]
    assert p40["p_dnp"] == pytest.approx(1.0)
    assert p40["projected_minutes"] == pytest.approx(0.0)


def test_bit_for_bit_parity_with_native_champion() -> None:
    data_dir = Path("data/processed")
    if not (data_dir / "player_performances.parquet").exists():
        pytest.skip("Live processed data not present")

    mod = _load_prototype_decoupled()
    from features.builder import build_features, resolve_operational_processed_dir
    from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel

    processed_dir = resolve_operational_processed_dir(Path("."))
    df_feat = build_features(processed_dir, target_gw=6, horizon=1)
    df_perf = pd.read_parquet(processed_dir / "player_performances.parquet")

    native = DefXgShrinkChallengerModel()
    native.fit(df_perf)
    res_native = native.predict(df_feat, horizon=1)

    composite = mod.resolve_composite_spec("composite:learned_start:def_xg_shrink")
    composite.fit(df_perf)
    res_comp = composite.predict(df_feat, horizon=1)

    assert len(res_native) == len(res_comp)
    components = [c for c in res_native.columns if c.startswith("xp_")] + ["projected_minutes", "projected_points"]
    for col in components:
        np.testing.assert_allclose(
            res_comp[col].to_numpy(),
            res_native[col].to_numpy(),
            atol=1e-12,
            rtol=1e-12,
            err_msg=f"Bit-for-bit parity mismatch in column '{col}'",
        )


# --- 6. Ticket #161 / #165: Oracle Event Gate Tests ---

def _load_prototype_oracle_gate():
    import importlib.util
    import sys
    path = Path("docs/research/decoupled-projection-architecture/prototype_oracle_gate.py")
    spec = importlib.util.spec_from_file_location("prototype_oracle_gate", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["prototype_oracle_gate"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_evaluate_oracle_event_gate_scenarios() -> None:
    mod = _load_prototype_oracle_gate()
    eval_gate = mod.evaluate_oracle_event_gate

    base_champ = {
        "oracle_formation_xi_regret": 63.96,
        "oracle_captain_regret": 2.79,
        "playable_bias": -0.2442,
    }

    cand_a = {
        "oracle_formation_xi_regret": 63.51,
        "oracle_captain_regret": 2.74,
        "playable_bias": -0.2342,
    }
    verdict_a = eval_gate(base_champ, cand_a)
    assert verdict_a.passed is True
    assert verdict_a.oracle_delta == pytest.approx(0.45)
    assert len(verdict_a.reasons) == 0

    cand_b = {
        "oracle_formation_xi_regret": 63.30,
        "oracle_captain_regret": 2.80,
        "playable_bias": -0.3242,
    }
    verdict_b = eval_gate(base_champ, cand_b)
    assert verdict_b.passed is False
    assert any("playable bias" in r for r in verdict_b.reasons)

    cand_c = {
        "oracle_formation_xi_regret": 63.50,
        "oracle_captain_regret": 3.04,
        "playable_bias": -0.2400,
    }
    verdict_c = eval_gate(base_champ, cand_c)
    assert verdict_c.passed is False
    assert any("Captaincy Regret" in r for r in verdict_c.reasons)

    cand_d = {
        "oracle_formation_xi_regret": 64.26,
        "oracle_captain_regret": 2.75,
        "playable_bias": -0.2400,
    }
    verdict_d = eval_gate(base_champ, cand_d)
    assert verdict_d.passed is False
    assert any("Regret did not improve" in r for r in verdict_d.reasons)


# --- 7. Ticket #164: LOO Teammate Finishing & Shot-Volume GK Saves Tests ---

def _load_prototype_event_challenger():
    import importlib.util
    import sys
    path = Path("docs/research/decoupled-projection-architecture/prototype_event_challenger.py")
    spec = importlib.util.spec_from_file_location("prototype_event_challenger", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["prototype_event_challenger"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_loo_finishing_multipliers_centering_and_clipping() -> None:
    mod = _load_prototype_event_challenger()
    compute_loo = mod.compute_loo_finishing_multipliers
    config = mod.EventCalibrationConfig()

    # Synthetic match history: Club 1 (clinical, G > xG), Club 2 (wasteful, G < xG)
    rows = []
    # Club 1: 5 matches, player 101 has 6 goals from 2.0 xG; player 102 has 1 goal from 1.0 xG
    for gw in range(1, 6):
        rows.append({"player_id": 101, "club_id": 1, "gameweek_id": gw, "fixture_id": gw, "minutes": 90.0, "goals_scored": 1.2, "expected_goals": 0.4, "threat": 40.0, "saves": 0.0})
        rows.append({"player_id": 102, "club_id": 1, "gameweek_id": gw, "fixture_id": gw, "minutes": 90.0, "goals_scored": 0.2, "expected_goals": 0.2, "threat": 20.0, "saves": 0.0})
        # Club 2: 5 matches, player 201 has 0 goals from 2.0 xG; player 202 has 0 goals from 1.0 xG
        rows.append({"player_id": 201, "club_id": 2, "gameweek_id": gw, "fixture_id": 100 + gw, "minutes": 90.0, "goals_scored": 0.0, "expected_goals": 0.4, "threat": 30.0, "saves": 0.0})
        rows.append({"player_id": 202, "club_id": 2, "gameweek_id": gw, "fixture_id": 100 + gw, "minutes": 90.0, "goals_scored": 0.0, "expected_goals": 0.2, "threat": 15.0, "saves": 0.0})

    hist = pd.DataFrame(rows)
    active_clubs = {101: 1, 102: 1, 201: 2, 202: 2}

    mults = compute_loo(hist, target_gw=6, active_player_clubs=active_clubs, config=config)

    # 1. Pool centering: mean multiplier on pool should be close to 1.00
    mean_val = np.mean(list(mults.values()))
    assert 0.98 <= mean_val <= 1.02

    # 2. Hard clipping bounds [0.88, 1.15]
    for val in mults.values():
        assert 0.88 <= val <= 1.15

    # 3. Teammate of high-conversion scorer (player 102) has higher multiplier than player in wasteful team (player 202)
    assert mults[102] > mults[202]


def test_loo_finishing_multipliers_strictly_leave_one_out() -> None:
    mod = _load_prototype_event_challenger()
    compute_loo = mod.compute_loo_finishing_multipliers
    config = mod.EventCalibrationConfig()

    rows = []
    for gw in range(1, 6):
        rows.append({"player_id": 1, "club_id": 10, "gameweek_id": gw, "fixture_id": gw, "minutes": 90.0, "goals_scored": 1.0, "expected_goals": 1.0, "threat": 30.0, "saves": 0.0})
        rows.append({"player_id": 2, "club_id": 10, "gameweek_id": gw, "fixture_id": gw, "minutes": 90.0, "goals_scored": 1.0, "expected_goals": 1.0, "threat": 30.0, "saves": 0.0})

    hist_base = pd.DataFrame(rows)
    active_clubs = {1: 10, 2: 10}

    mults_base = compute_loo(hist_base, target_gw=6, active_player_clubs=active_clubs, config=config)
    assert mults_base[1] == pytest.approx(1.0, abs=1e-3)
    assert mults_base[2] == pytest.approx(1.0, abs=1e-3)

    # Surge player 1 goals: player 1 scores 10 extra goals
    hist_surge = hist_base.copy()
    hist_surge.loc[hist_surge["player_id"] == 1, "goals_scored"] += 2.0

    mults_surge = compute_loo(hist_surge, target_gw=6, active_player_clubs=active_clubs, config=config)

    # Player 2 (teammate) should receive an assist conversion boost
    assert mults_surge[2] > mults_base[2]
    # Player 1 should NOT be boosted by their own goals (uncentered raw is 1.0, and centered ratio drops relative to teammate)
    assert mults_surge[1] <= mults_base[1]


def test_loo_finishing_multipliers_cold_start() -> None:
    mod = _load_prototype_event_challenger()
    compute_loo = mod.compute_loo_finishing_multipliers
    config = mod.EventCalibrationConfig(min_fixtures=3)

    # Only 2 completed fixtures
    rows = []
    for gw in range(1, 3):
        rows.append({"player_id": 1, "club_id": 10, "gameweek_id": gw, "fixture_id": gw, "minutes": 90.0, "goals_scored": 5.0, "expected_goals": 0.5, "threat": 30.0, "saves": 0.0})
        rows.append({"player_id": 2, "club_id": 10, "gameweek_id": gw, "fixture_id": gw, "minutes": 90.0, "goals_scored": 0.0, "expected_goals": 0.5, "threat": 30.0, "saves": 0.0})

    hist = pd.DataFrame(rows)
    active_clubs = {1: 10, 2: 10}

    mults = compute_loo(hist, target_gw=3, active_player_clubs=active_clubs, config=config)
    assert mults[1] == pytest.approx(1.0)
    assert mults[2] == pytest.approx(1.0)


def test_opponent_save_multipliers() -> None:
    mod = _load_prototype_event_challenger()
    compute_saves = mod.compute_opponent_save_multipliers
    config = mod.EventCalibrationConfig()

    rows = []
    # Club 1: Perimeter shooting (very high threat, low xG -> low danger)
    # Club 2: Clinical/penetrative (normal threat, high xG -> high danger)
    for gw in range(1, 6):
        rows.append({"player_id": 1, "club_id": 1, "gameweek_id": gw, "fixture_id": gw, "minutes": 90.0, "goals_scored": 1.0, "expected_goals": 1.0, "threat": 300.0, "saves": 0.0})
        rows.append({"player_id": 2, "club_id": 2, "gameweek_id": gw, "fixture_id": 100 + gw, "minutes": 90.0, "goals_scored": 2.0, "expected_goals": 2.5, "threat": 80.0, "saves": 0.0})

    hist = pd.DataFrame(rows)
    save_mults = compute_saves(hist, target_gw=6, config=config)

    # Club 1 should have a higher save multiplier (rewards GK facing high threat / low danger)
    assert save_mults[1] > save_mults[2]
    # Bound check
    assert 0.70 <= save_mults[1] <= 1.45
    assert 0.70 <= save_mults[2] <= 1.45
