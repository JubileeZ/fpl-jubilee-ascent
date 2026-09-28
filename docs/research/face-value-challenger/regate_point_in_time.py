import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from backtesting.model_evaluation import compare_to_reference  # noqa: E402
from backtesting.promotion import metrics_by_season_window  # noqa: E402
from backtesting.walkforward import WalkforwardConfig, run_walkforward_backtest  # noqa: E402

RUNS = {
    "2025-26": (ROOT / "data/archive/2025-26/processed", ROOT / "data/archive/2024-25/processed", 38),
    "2026-27": (ROOT / "data/archive/2026-27/processed", ROOT / "data/archive/2025-26/processed", 5),
}


def run(args: tuple[str, str]):
    model, season = args
    data_dir, seed, end = RUNS[season]
    return model, season, run_walkforward_backtest(
        WalkforwardConfig(model_name=model, data_dir=data_dir, start_gw=1, end_gw=end, seed_processed_dir=seed, eval_target="blended_points")
    )


if __name__ == "__main__":
    jobs = [(m, s) for m in ("hold_chase_challenger", "face_value_challenger") for s in RUNS]
    with ProcessPoolExecutor(4) as pool:
        results = {(m, s): r for m, s, r in pool.map(run, jobs)}
    out = {}
    for season in RUNS:
        ref, cand = results[("hold_chase_challenger", season)], results[("face_value_challenger", season)]
        v = compare_to_reference(ref, cand)
        wins = {}
        for name, res in (("hold_chase", ref), ("face_value", cand)):
            w = metrics_by_season_window(res.df_eval, target_column="blended_points")
            c = w["combined"]
            wins[name] = {
                "regret": c["top_11_regret"], "blend_mae": c["mae"], "abs_bias": abs(c["bias"]), "spearman": c["spearman"],
                "xmins_mae": c["minutes_forecast_metrics"]["mae"],
                **{f"{seg}_regret": w[seg]["top_11_regret"] for seg in ("cold_start", "early_mid", "late") if seg in w},
            }
        out[season] = {"passed": v.passed, "delta": v.combined_primary_delta, "min_effect": v.min_effect, "boot_p": v.bootstrap_p,
                       "segs": v.segment_wins, "guardrails": v.guardrails_passed, "reasons": list(v.reasons), "metrics": wins}
    print(json.dumps(out, indent=1))
    rows = [
        {"season": season, "model": model, **metrics, "gate_passed": v["passed"], "combined_delta": v["delta"],
         "min_effect": v["min_effect"], "boot_p_gt0": v["boot_p"], "segment_wins": v["segs"], "guardrails_passed": v["guardrails"]}
        for season, v in out.items()
        for model, metrics in v["metrics"].items()
    ]
    pd.DataFrame(rows).to_csv(Path(__file__).with_name("point_in_time_regate.csv"), index=False)
