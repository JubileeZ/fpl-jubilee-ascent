"""PROTOTYPE: Standalone Tier 1 Minutes Gate & Evaluator.

Validation prototype for Ticket #162 (Wayfinder Map #159):
1. Independent evaluation of Minutes Projection Models (M_mins) using ground truth minutes & starts.
2. Multiclass Participation Brier score over mutually exclusive states: (DNP, Start, Sub-in).
3. Starter discrimination (60+ minutes appearances): Non-parametric ROC-AUC, Precision, Recall, F1.
4. Active Player Pool conditioning: avoids dilution from unselected third goalkeepers and non-playing reserves.
5. Circular block bootstrap (P >= 0.60, L=3 GWs, B=20,000) for statistical significance.
6. Empirical verification of 4 gate scenarios:
   - Scenario A (Superior Rotation Model): PASS (MAE improved, Brier non-regressing, Recall preserved).
   - Scenario B (Starter Recall Leaker): FAIL (Excessive starter dropouts violating -0.005 tolerance).
   - Scenario C (Over-Confident Brier Degrader): FAIL (Miscalibrated probability distributions).
   - Scenario D (Inferior Minutes Model): FAIL (Negative MAE delta <= 0.0).

Run via:
    uv run python docs/research/decoupled-projection-architecture/prototype_minutes_gate.py
"""

from __future__ import annotations

from pathlib import Path
import sys

# Ensure repo root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import pandas as pd

from commands.evaluate_minutes import (
    compute_minutes_metrics,
    evaluate_minutes_gate,
)
from features.builder import build_features, history_before_target
from models import get_model


def run_scenario_tests() -> dict[str, bool]:
    """Verify Tier 1 Minutes Gate behavior across 4 synthetic validation scenarios."""
    print("=" * 76)
    print(" RUNNING TIER 1 MINUTES GATE SCENARIO TESTS")
    print("=" * 76)

    # Base ground truth fixtures (1000 simulated player-fixtures)
    np.random.seed(42)
    n = 1000

    # Ground truth: 40% starts (70-90 mins), 15% subs (10-30 mins), 45% DNP (0 mins)
    true_states = np.random.choice([0, 1, 2], size=n, p=[0.45, 0.40, 0.15])
    actual_dnp = (true_states == 0).astype(float)
    actual_start = (true_states == 1).astype(float)
    actual_sub = (true_states == 2).astype(float)

    actual_mins = np.zeros(n, dtype=float)
    for i in range(n):
        if true_states[i] == 1:
            actual_mins[i] = np.random.uniform(65.0, 90.0)
        elif true_states[i] == 2:
            actual_mins[i] = np.random.uniform(5.0, 30.0)
        else:
            actual_mins[i] = 0.0

    # Base Champion model predictions (noisy baseline)
    champ_p_start = np.clip(actual_start * 0.80 + np.random.uniform(0.0, 0.25, size=n), 0.0, 1.0)
    champ_p_sub = np.clip(actual_sub * 0.60 + np.random.uniform(0.0, 0.20, size=n), 0.0, 1.0)
    champ_p_dnp = np.clip(1.0 - champ_p_start - champ_p_sub, 0.0, 1.0)
    norm = champ_p_start + champ_p_sub + champ_p_dnp
    champ_p_start /= norm
    champ_p_sub /= norm
    champ_p_dnp /= norm

    champ_mins = champ_p_start * 80.0 + champ_p_sub * 20.0
    champ_p_60 = champ_p_start * 0.90 + champ_p_sub * 0.02

    df_base = pd.DataFrame({
        "actual_minutes": actual_mins,
        "actual_start": actual_start,
        "actual_sub_in": actual_sub,
        "actual_dnp": actual_dnp,
    })

    df_champ = df_base.copy()
    df_champ["projected_minutes"] = champ_mins
    df_champ["p_dnp"] = champ_p_dnp
    df_champ["p_start"] = champ_p_start
    df_champ["p_sub_in"] = champ_p_sub
    df_champ["p_60_plus"] = champ_p_60

    champ_metrics = compute_minutes_metrics(df_champ)

    scenarios_passed = {}

    # --- Scenario A: Superior Rotation Model ---
    df_cand_a = df_base.copy()
    cand_a_p_start = np.clip(actual_start * 0.92 + np.random.uniform(0.0, 0.12, size=n), 0.0, 1.0)
    cand_a_p_sub = np.clip(actual_sub * 0.75 + np.random.uniform(0.0, 0.15, size=n), 0.0, 1.0)
    cand_a_p_dnp = np.clip(1.0 - cand_a_p_start - cand_a_p_sub, 0.0, 1.0)
    norm_a = cand_a_p_start + cand_a_p_sub + cand_a_p_dnp
    df_cand_a["p_start"] = cand_a_p_start / norm_a
    df_cand_a["p_sub_in"] = cand_a_p_sub / norm_a
    df_cand_a["p_dnp"] = cand_a_p_dnp / norm_a
    df_cand_a["projected_minutes"] = df_cand_a["p_start"] * 82.0 + df_cand_a["p_sub_in"] * 20.0
    df_cand_a["p_60_plus"] = df_cand_a["p_start"] * 0.94 + df_cand_a["p_sub_in"] * 0.01

    cand_a_metrics = compute_minutes_metrics(df_cand_a)
    per_gw_deltas_a = [0.85, 0.72, 0.91, 0.60, 0.78] * 6  # 30 GWs
    verdict_a = evaluate_minutes_gate(cand_a_metrics, champ_metrics, per_gw_deltas_a)
    print(f"Scenario A (Superior Model):      Verdict={'PASS' if verdict_a.passed else 'FAIL'} | ΔMAE={verdict_a.delta_mae:+.3f} | BrierΔ={verdict_a.brier_delta:+.4f} | RecallΔ={verdict_a.recall_delta:+.4f}")
    scenarios_passed["Scenario A"] = verdict_a.passed is True

    # --- Scenario B: Starter Recall Leaker ---
    df_cand_b = df_cand_a.copy()
    # Suppress p_start for 10% of true starters (rotation false positives)
    starter_indices = np.where(actual_start == 1)[0]
    suppress_idx = starter_indices[:int(len(starter_indices) * 0.15)]
    cand_b_p_start = df_cand_b["p_start"].to_numpy().copy()
    cand_b_p_start[suppress_idx] = 0.20
    df_cand_b["p_start"] = cand_b_p_start
    df_cand_b["p_60_plus"] = df_cand_b["p_start"] * 0.90
    cand_b_metrics = compute_minutes_metrics(df_cand_b)
    verdict_b = evaluate_minutes_gate(cand_b_metrics, champ_metrics, per_gw_deltas_a)
    print(f"Scenario B (Starter Leaker):      Verdict={'PASS' if verdict_b.passed else 'FAIL'} | RecallΔ={verdict_b.recall_delta:+.4f} | Expected FAIL")
    scenarios_passed["Scenario B"] = (verdict_b.passed is False) and any("starter recall" in r for r in verdict_b.reasons)

    # --- Scenario C: Over-Confident Brier Degrader ---
    df_cand_c = df_cand_a.copy()
    # Scramble participation probabilities, degrading Brier calibration
    df_cand_c["p_dnp"] = np.random.uniform(0.1, 0.9, size=n)
    df_cand_c["p_start"] = np.random.uniform(0.1, 0.9, size=n)
    df_cand_c["p_sub_in"] = np.random.uniform(0.1, 0.9, size=n)
    norm_c = df_cand_c["p_dnp"] + df_cand_c["p_start"] + df_cand_c["p_sub_in"]
    df_cand_c["p_dnp"] /= norm_c
    df_cand_c["p_start"] /= norm_c
    df_cand_c["p_sub_in"] /= norm_c
    cand_c_metrics = compute_minutes_metrics(df_cand_c)
    verdict_c = evaluate_minutes_gate(cand_c_metrics, champ_metrics, per_gw_deltas_a)
    print(f"Scenario C (Brier Degrader):      Verdict={'PASS' if verdict_c.passed else 'FAIL'} | BrierΔ={verdict_c.brier_delta:+.4f} | Expected FAIL")
    scenarios_passed["Scenario C"] = (verdict_c.passed is False) and any("Brier score regresses" in r for r in verdict_c.reasons)

    # --- Scenario D: Inferior Minutes Model ---
    df_cand_d = df_champ.copy()
    # Add heavy uniform noise to projected minutes
    df_cand_d["projected_minutes"] += np.random.uniform(-25.0, 25.0, size=n)
    cand_d_metrics = compute_minutes_metrics(df_cand_d)
    per_gw_deltas_d = [-0.60, -0.45, -0.80, -0.55, -0.70] * 6
    verdict_d = evaluate_minutes_gate(cand_d_metrics, champ_metrics, per_gw_deltas_d)
    print(f"Scenario D (Inferior Model):      Verdict={'PASS' if verdict_d.passed else 'FAIL'} | ΔMAE={verdict_d.delta_mae:+.3f} | Expected FAIL")
    scenarios_passed["Scenario D"] = (verdict_d.passed is False) and any("MAE does not improve" in r for r in verdict_d.reasons)

    print("=" * 76 + "\n")
    return scenarios_passed


def run_live_data_benchmark() -> None:
    """Benchmark live Champion minutes on 2026/27 official processed data (GW1-5)."""
    data_dir = PROJECT_ROOT / "data" / "processed"
    perf_path = data_dir / "player_performances.parquet"
    if not perf_path.exists():
        print(f"Skipping live benchmark: {perf_path} not found.")
        return

    print("=" * 76)
    print(" BENCHMARKING CHAMPION MINUTES ON LIVE REPOSITORY DATA (GW1-5)")
    print("=" * 76)

    from backtesting.walkforward import load_gameweek_deadlines
    from commands.evaluate_minutes import (
        build_minutes_evaluation_frame,
        extract_minutes_prediction_frame,
    )

    df_perf = pd.read_parquet(perf_path)
    model = get_model("def_xg_shrink_challenger")
    deadlines = load_gameweek_deadlines(data_dir)

    eval_frames = []
    for gw in range(1, 6):
        deadline = deadlines.get(gw)
        df_feat = build_features(data_dir, gw, as_of_gw=gw, target_deadline=deadline)
        hist = history_before_target(
            df_perf,
            gw,
            deadline,
            require_kickoff_time=False,
        )
        model.fit(hist)
        preds = extract_minutes_prediction_frame(model, df_feat, horizon=1)
        eval_df = build_minutes_evaluation_frame(preds, df_perf, gw)
        eval_frames.append(eval_df)

    combined = pd.concat(eval_frames, ignore_index=True)
    metrics = compute_minutes_metrics(combined)

    print(f" Evaluated Gameweeks: GW1-5 ({metrics.sample_count} rows, {metrics.active_count} active)")
    print(f" Active Pool MAE:     {metrics.mae:.2f} mins")
    print(f" Active Pool RMSE:    {metrics.rmse:.2f} mins")
    print(f" Minutes Signed Bias: {metrics.bias:+.2f} mins")
    print(f" Brier Score:         {metrics.brier_score:.4f} (Start: {metrics.brier_start:.4f}, Sub: {metrics.brier_sub:.4f}, DNP: {metrics.brier_dnp:.4f})")
    print(f" Starter ROC-AUC:     {metrics.starter_auc:.4f}")
    print(f" Starter Recall 60+:  {metrics.starter_recall:.4f}")
    print(f" Starter Precision:   {metrics.starter_precision:.4f}")
    print("=" * 76 + "\n")


if __name__ == "__main__":
    results = run_scenario_tests()
    all_passed = all(results.values())
    if not all_passed:
        print("ERROR: One or more scenario tests failed!")
        sys.exit(1)
    run_live_data_benchmark()
