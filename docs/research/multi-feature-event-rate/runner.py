"""Gate companion: face_value_challenger vs multi_feature_assist_challenger, 2025-26 GW1-38 (seed 2024-25).

    uv run python docs/research/multi-feature-event-rate/runner.py   (~10 min, 2 procs)

Writes candidate_gate_summary.csv beside this file. Dev season only; never 2026-27 GW6+ (sealed holdout).
"""

import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from backtesting.model_evaluation import compare_to_reference  # noqa: E402
from backtesting.promotion import metrics_by_season_window  # noqa: E402
from backtesting.walkforward import WalkforwardConfig, WalkforwardResult, run_walkforward_backtest  # noqa: E402

CHAMPION = "face_value_challenger"
CANDIDATE = "multi_feature_assist_challenger"
DATA, SEED = ROOT / "data/archive/2025-26/processed", ROOT / "data/archive/2024-25/processed"
SEGMENTS = ("cold_start", "early_mid", "late")


def run(model: str) -> tuple[str, WalkforwardResult]:
    config = WalkforwardConfig(model_name=model, data_dir=DATA, start_gw=1, end_gw=38, seed_processed_dir=SEED,
                               eval_target="blended_points")
    return model, run_walkforward_backtest(config)


def metrics(result: WalkforwardResult) -> dict[str, float]:
    blend = metrics_by_season_window(result.df_eval, target_column="blended_points")
    combined = blend["combined"]
    df = result.df_eval
    return {
        "regret": combined["top_11_regret"],
        **{f"{seg}_regret": blend[seg]["top_11_regret"] for seg in SEGMENTS if seg in blend},
        "blend_mae": combined["mae"],
        "realized_mae": metrics_by_season_window(df, target_column="actual_points")["combined"]["mae"],
        "process_mae": metrics_by_season_window(df, target_column="process_points")["combined"]["mae"],
        "abs_bias": abs(combined["bias"]),
        "spearman": combined["spearman"],
        "xmins_mae": combined["minutes_forecast_metrics"]["mae"],
        "xp_assists_mean": float(df["xp_assists"].mean()),
        "actual_assist_pts_mean": float(df["actual_xp_assists"].mean()),
        "assist_bias_realized": float((df["xp_assists"] - df["actual_xp_assists"]).mean()),
    }


if __name__ == "__main__":
    with ProcessPoolExecutor(2) as pool:
        results = dict(pool.map(run, (CHAMPION, CANDIDATE)))
    verdict = compare_to_reference(results[CHAMPION], results[CANDIDATE])
    rows = [
        {"season": "2025-26", "model": model, **metrics(results[model]), "gate_passed": verdict.passed,
         "combined_delta": verdict.combined_primary_delta, "min_effect": verdict.min_effect,
         "boot_p_gt0": verdict.bootstrap_p, "segment_wins": verdict.segment_wins,
         "guardrails_passed": verdict.guardrails_passed, "reasons": "; ".join(verdict.reasons)}
        for model in (CHAMPION, CANDIDATE)
    ]
    out = pd.DataFrame(rows)
    out.to_csv(Path(__file__).with_name("candidate_gate_summary.csv"), index=False)
    print(out.T.to_string())
