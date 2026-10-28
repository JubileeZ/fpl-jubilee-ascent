"""Face-value Challenger gate + lever ablation companion.

Writes ``face_value_gate_summary.csv`` beside this file: one row per (season, model) with
Historical Promotion Gate verdict vs ``hold_chase_challenger`` (Blended primary +
Realized/Process guardrails) and per-GW top-11 regret wins + bootstrap P(mean delta > 0).

    uv run python docs/research/face-value-challenger/runner.py
"""

from __future__ import annotations

import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from backtesting.metrics import _top_k_stats, evaluate_predictions  # noqa: E402
from backtesting.model_evaluation import compare_to_reference  # noqa: E402
from backtesting.promotion import metrics_by_season_window, primary_metric_value  # noqa: E402
from backtesting import walkforward  # noqa: E402
from backtesting.walkforward import WalkforwardConfig, WalkforwardResult, run_walkforward_backtest  # noqa: E402
from models import face_value_challenger as fv  # noqa: E402
from models.hold_chase_challenger import HoldChaseChallengerModel  # noqa: E402

OUT = Path(__file__).resolve().parent / "face_value_gate_summary.csv"
REFERENCE = "hold_chase_challenger"
SEASONS = {"2025-26": ("2024-25", 1, 38), "2026-27": ("2025-26", 1, 5)}


class FaceValueOnly(fv.FaceValueChallengerModel):
    """Ablation: lever 1 only (no finishing offset, no start shrink)."""

    @property
    def name(self) -> str:
        return "ablation_face_value_only"

    def fit(self, history_df: pd.DataFrame) -> None:
        self.goal_offsets, self.assist_offsets = {}, {}

    _state_probabilities = staticmethod(HoldChaseChallengerModel._state_probabilities)


class FaceValueStartShrink(fv.FaceValueChallengerModel):
    """Ablation: levers 1 + 3 (no finishing offset)."""

    @property
    def name(self) -> str:
        return "ablation_face_value_start_shrink"

    def fit(self, history_df: pd.DataFrame) -> None:
        self.goal_offsets, self.assist_offsets = {}, {}


ABLATIONS = {"ablation_face_value_only": FaceValueOnly, "ablation_face_value_start_shrink": FaceValueStartShrink}
MODELS = (REFERENCE, "ablation_face_value_only", "ablation_face_value_start_shrink", "face_value_challenger")
_catalog_get_model = walkforward.get_model
walkforward.get_model = lambda name: ABLATIONS[name]() if name in ABLATIONS else _catalog_get_model(name)


def _run(job: tuple[str, str]) -> tuple[str, str, WalkforwardResult]:
    season, model_name = job
    seed, start, end = SEASONS[season]
    config = WalkforwardConfig(
        model_name=model_name,
        data_dir=ROOT / "data" / "archive" / season / "processed",
        start_gw=start,
        end_gw=end,
        seed_processed_dir=ROOT / "data" / "archive" / seed / "processed",
        eval_target="blended_points",
    )
    return season, model_name, run_walkforward_backtest(config)


def _per_gw_regret(df: pd.DataFrame) -> pd.Series:
    return pd.Series(
        {gw: _top_k_stats(group, 11, target_column="blended_points")[1] for gw, group in df.groupby("gameweek")}
    )


def main() -> None:
    jobs = [(season, name) for season in SEASONS for name in MODELS]
    with ProcessPoolExecutor(max_workers=len(jobs)) as pool:
        results = {(season, name): res for season, name, res in pool.map(_run, jobs)}
    rows: list[dict[str, object]] = []
    for season in SEASONS:
        reference = results[(season, REFERENCE)]
        ref_regret = _per_gw_regret(reference.df_eval)
        for name in MODELS:
            res = results[(season, name)]
            windows = metrics_by_season_window(res.df_eval, target_column="blended_points")
            combined = windows["combined"]
            delta = ref_regret - _per_gw_regret(res.df_eval)
            boot = np.random.default_rng(0).choice(delta.to_numpy(), (20000, len(delta))).mean(axis=1)
            verdict = compare_to_reference(reference, res)
            rows.append({
                "season": season,
                "model": name,
                "gate_pass": bool(verdict.passed) if name != REFERENCE else None,
                "segment_wins": verdict.segment_wins if name != REFERENCE else None,
                "top_11_regret": primary_metric_value(combined),
                "combined_delta": verdict.combined_primary_delta,
                **{f"{seg}_regret": primary_metric_value(windows[seg]) for seg in ("cold_start", "early_mid", "late") if seg in windows},
                "blend_mae": combined["mae"],
                "abs_bias": abs(combined["bias"]),
                "spearman": combined["spearman"],
                "xmins_mae": combined["minutes_forecast_metrics"]["mae"],
                "realized_mae": evaluate_predictions(res.df_eval, target_column="actual_points")["mae"],
                "process_mae": evaluate_predictions(res.df_eval, target_column="process_points")["mae"],
                "gw_wins": int((delta > 0).sum()),
                "gw_losses": int((delta < 0).sum()),
                "boot_p_gt0": float((boot > 0).mean()) if name != REFERENCE else None,
                "reasons": "; ".join(verdict.reasons) if name != REFERENCE else "",
            })
    pd.DataFrame(rows).to_csv(OUT, index=False)
    print(pd.DataFrame(rows).to_string())


if __name__ == "__main__":
    main()
