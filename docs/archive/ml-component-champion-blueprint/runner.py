"""Reproducible Ablation & Evaluation Runner for ML Component Champion Blueprint.

Executes:
1. Tier 1 Minutes Gate Ablation -> tier1_minutes_ablation.csv
2. Tier 2 Oracle Event Gate Ablation -> tier2_oracle_event_ablation.csv
3. Greedy Stacking Synthesis
4. Tier 3 Dev and Confirmation Gate

Usage:
    uv run python docs/research/ml-component-champion-blueprint/runner.py --stage ablations
    uv run python docs/research/ml-component-champion-blueprint/runner.py --stage dev_gate
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
import sys
import time
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backtesting.metrics import evaluate_predictions, formation_xi_regret_by_gameweek
from backtesting.process_points import aggregate_process_points, blended_points
from backtesting.promotion import (
    compute_playable_pool_metrics,
)
from backtesting.walkforward import (
    LEDGER_COMPONENTS,
    PLAYER_POSITIONS,
    _build_actual_components,
    load_gameweek_deadlines,
)
from commands.evaluate_minutes import (
    build_minutes_evaluation_frame,
    compute_minutes_metrics,
    evaluate_minutes_gate,
    extract_minutes_prediction_frame,
)
import importlib.util

_oracle_gate_path = PROJECT_ROOT / "docs/research/decoupled-projection-architecture/prototype_oracle_gate.py"
_oracle_spec = importlib.util.spec_from_file_location("prototype_oracle_gate", _oracle_gate_path)
if _oracle_spec is None or _oracle_spec.loader is None:
    raise ImportError(f"Cannot load prototype_oracle_gate from {_oracle_gate_path}")
_oracle_mod = importlib.util.module_from_spec(_oracle_spec)
sys.modules["prototype_oracle_gate"] = _oracle_mod
_oracle_spec.loader.exec_module(_oracle_mod)
evaluate_oracle_event_gate = _oracle_mod.evaluate_oracle_event_gate
inject_oracle_minutes = _oracle_mod.inject_oracle_minutes
from features.builder import build_features, history_before_target
from features.contracts import assert_projection_contract
from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel
from models.ml_component_challenger import MLComponentChallengerModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ml_blueprint_runner")

RESEARCH_DIR = PROJECT_ROOT / "docs/research/ml-component-champion-blueprint"
DEV_DATA_DIR = PROJECT_ROOT / "data/archive/2025-26/processed"
CONFIRM_DATA_DIR = PROJECT_ROOT / "data/archive/2024-25/processed"


def precompute_season_frames(
    data_dir: Path,
    start_gw: int = 1,
    end_gw: int = 38,
) -> tuple[pd.DataFrame, list[tuple[int, pd.DataFrame, pd.DataFrame]]]:
    """Precompute and cache in memory (gw, df_feat, hist_before) across gameweeks."""
    perf_path = data_dir / "player_performances.parquet"
    if not perf_path.exists():
        raise FileNotFoundError(f"Missing player_performances.parquet in {data_dir}")

    df_perf = pd.read_parquet(perf_path)
    gameweek_deadlines = load_gameweek_deadlines(data_dir)

    cached_frames: list[tuple[int, pd.DataFrame, pd.DataFrame]] = []
    logger.info("Precomputing features for GW%d to GW%d from %s...", start_gw, end_gw, data_dir.parent.name)
    t0 = time.time()

    for gw in range(start_gw, end_gw + 1):
        deadline = gameweek_deadlines.get(gw)
        df_feat = build_features(data_dir, gw, as_of_gw=gw, target_deadline=deadline)
        if "position_id" in df_feat.columns:
            df_feat = df_feat[df_feat["position_id"].isin(PLAYER_POSITIONS)]
        hist_before = history_before_target(df_perf, gw, deadline, require_kickoff_time=False)
        cached_frames.append((gw, df_feat, hist_before))

    logger.info("Precomputed %d gameweek frames in %.2fs", len(cached_frames), time.time() - t0)
    return df_perf, cached_frames


def run_tier1_minutes_ablation(
    df_perf: pd.DataFrame,
    cached_frames: list[tuple[int, pd.DataFrame, pd.DataFrame]],
) -> pd.DataFrame:
    """Evaluate 3 M_mins heads standalone and stacked on 2025-26 via Tier 1 Minutes Gate."""
    logger.info("--- Starting Tier 1 Minutes Gate Ablations ---")
    champion = DefXgShrinkChallengerModel()

    # Precompute Champion Minutes Evaluation frames
    champ_eval_frames: list[pd.DataFrame] = []
    for gw, df_feat, hist in cached_frames:
        champion.fit(hist)
        champ_preds = extract_minutes_prediction_frame(champion, df_feat, horizon=1)
        champ_eval = build_minutes_evaluation_frame(champ_preds, df_perf, gw)
        champ_eval_frames.append(champ_eval)

    variants: dict[str, MLComponentChallengerModel] = {
        "mins_h1_ridge": MLComponentChallengerModel(
            enable_mins_h1=True, enable_mins_h2=False, enable_mins_h3=False,
            enable_goals=False, enable_assists=False, enable_defense=False, enable_bonus=False,
        ),
        "mins_h2_ridge": MLComponentChallengerModel(
            enable_mins_h1=False, enable_mins_h2=True, enable_mins_h3=False,
            enable_goals=False, enable_assists=False, enable_defense=False, enable_bonus=False,
        ),
        "mins_h3_ridge": MLComponentChallengerModel(
            enable_mins_h1=False, enable_mins_h2=False, enable_mins_h3=True,
            enable_goals=False, enable_assists=False, enable_defense=False, enable_bonus=False,
        ),
        "mins_all_ridge": MLComponentChallengerModel(
            enable_mins_h1=True, enable_mins_h2=True, enable_mins_h3=True,
            enable_goals=False, enable_assists=False, enable_defense=False, enable_bonus=False,
        ),
    }

    results: list[dict[str, Any]] = []

    for name, model in variants.items():
        logger.info("Evaluating Tier 1 variant: %s...", name)
        t0 = time.time()
        cand_eval_frames: list[pd.DataFrame] = []
        per_gw_deltas: list[float] = []

        for idx, (gw, df_feat, hist) in enumerate(cached_frames):
            model.fit(hist)
            cand_preds = extract_minutes_prediction_frame(model, df_feat, horizon=1)
            cand_eval = build_minutes_evaluation_frame(cand_preds, df_perf, gw)
            cand_eval_frames.append(cand_eval)

            champ_eval = champ_eval_frames[idx]
            active_mask = (
                (cand_eval["projected_minutes"] > 0)
                | (champ_eval["projected_minutes"] > 0)
                | (cand_eval["actual_minutes"] > 0)
            )
            if active_mask.any():
                c_mae = (cand_eval.loc[active_mask, "projected_minutes"] - cand_eval.loc[active_mask, "actual_minutes"]).abs().mean()
                ch_mae = (champ_eval.loc[active_mask, "projected_minutes"] - champ_eval.loc[active_mask, "actual_minutes"]).abs().mean()
                per_gw_deltas.append(ch_mae - c_mae)
            else:
                per_gw_deltas.append(0.0)

        df_cand_all = pd.concat(cand_eval_frames, ignore_index=True)
        df_champ_all = pd.concat(champ_eval_frames, ignore_index=True)

        c_m = compute_minutes_metrics(df_cand_all)
        ch_m = compute_minutes_metrics(df_champ_all)

        verdict = evaluate_minutes_gate(
            c_m,
            ch_m,
            per_gw_deltas=per_gw_deltas,
        )

        row = {
            "variant": name,
            "passed": verdict.passed,
            "delta_mae": round(verdict.delta_mae, 4),
            "cand_mae": round(c_m.mae, 4),
            "champ_mae": round(ch_m.mae, 4),
            "bootstrap_p": round(verdict.bootstrap_p, 4) if verdict.bootstrap_p is not None else None,
            "delta_brier": round(verdict.brier_delta, 5),
            "cand_brier": round(c_m.brier_score, 5),
            "champ_brier": round(ch_m.brier_score, 5),
            "delta_recall": round(verdict.recall_delta, 4),
            "cand_recall": round(c_m.starter_recall, 4),
            "champ_recall": round(ch_m.starter_recall, 4),
            "delta_auc": round(verdict.auc_delta, 4),
            "cand_auc": round(c_m.starter_auc, 4),
            "champ_auc": round(ch_m.starter_auc, 4),
            "cand_bias": round(c_m.bias, 4),
            "champ_bias": round(ch_m.bias, 4),
            "reasons": "; ".join(verdict.reasons) if verdict.reasons else "All criteria passed",
            "elapsed_s": round(time.time() - t0, 2),
        }
        logger.info(
            "%s: %s | Δ_MAE=%+.4f (boot P=%s) | Δ_Brier=%+.5f | Δ_Recall=%+.4f",
            name, "PASS" if verdict.passed else "FAIL", row["delta_mae"], row["bootstrap_p"],
            row["delta_brier"], row["delta_recall"],
        )
        results.append(row)

    out_df = pd.DataFrame(results)
    out_path = RESEARCH_DIR / "tier1_minutes_ablation.csv"
    out_df.to_csv(out_path, index=False)
    logger.info("Saved Tier 1 ablation results to %s", out_path)
    return out_df


def _run_oracle_eval_for_model(
    model: Any,
    df_perf: pd.DataFrame,
    cached_frames: list[tuple[int, pd.DataFrame, pd.DataFrame]],
) -> tuple[dict[str, Any], pd.DataFrame]:
    """Run walkforward prediction under Oracle Minutes and compute blended metrics."""
    all_results: list[pd.DataFrame] = []

    for gw, df_feat, hist in cached_frames:
        if hasattr(model, "fit"):
            model.fit(hist)

        # Inject oracle minutes
        df_oracle_feat = inject_oracle_minutes(df_feat, df_perf, target_gw=gw)
        df_proj = model.predict(df_oracle_feat, horizon=1)
        assert_projection_contract(df_proj)

        comp_cols = [c for c in LEDGER_COMPONENTS if c in df_proj.columns]
        proj_group_cols = ["projected_points", "projected_minutes"] + comp_cols
        df_proj_gw = (
            df_proj[df_proj["gameweek_id"] == gw]
            .groupby(["player_id", "gameweek_id"], as_index=False)[proj_group_cols]
            .sum()
        )

        gw_perf = _build_actual_components(df_perf[df_perf["gameweek_id"] == gw].copy(), df_feat)
        actual_group_cols = ["total_points", "minutes"] + [f"actual_{c}" for c in LEDGER_COMPONENTS if f"actual_{c}" in gw_perf.columns]
        df_actual_gw = (
            gw_perf.groupby(["player_id", "gameweek_id"], as_index=False)[actual_group_cols]
            .sum()
            .rename(columns={"total_points": "actual_points", "minutes": "actual_minutes"})
        )

        df_compare = df_proj_gw.merge(df_actual_gw, on=["player_id", "gameweek_id"], how="left")
        fill_cols = [c for c in df_compare.columns if c.startswith(("actual_", "xp_"))]
        df_compare[fill_cols] = df_compare[fill_cols].fillna(0.0)
        pos_map = df_feat[["player_id", "position_id"]].drop_duplicates("player_id")
        df_compare = df_compare.merge(pos_map, on="player_id", how="left")

        process_gw = aggregate_process_points(gw_perf)
        df_compare = df_compare.merge(process_gw, on=["player_id", "gameweek_id"], how="left")
        df_compare["process_points"] = df_compare["process_points"].fillna(0.0)
        df_compare["gameweek"] = gw
        all_results.append(df_compare)

    df_eval = pd.concat(all_results, ignore_index=True)
    df_eval["blended_points"] = blended_points(df_eval["actual_points"], df_eval["process_points"], weight=0.5)
    metrics = evaluate_predictions(df_eval, target_column="blended_points")
    metrics["oracle_formation_xi_regret"] = metrics.get("formation_xi_regret", 0.0)
    metrics["oracle_captain_regret"] = metrics.get("captain_regret", 0.0)
    return metrics, df_eval


def run_tier2_oracle_event_ablation(
    df_perf: pd.DataFrame,
    cached_frames: list[tuple[int, pd.DataFrame, pd.DataFrame]],
) -> pd.DataFrame:
    """Evaluate 4 M_events groups standalone and stacked under Oracle Minutes on 2025-26."""
    logger.info("--- Starting Tier 2 Oracle Event Gate Ablations ---")
    champion = DefXgShrinkChallengerModel()

    logger.info("Computing Champion Oracle reference metrics...")
    champ_metrics, champ_eval = _run_oracle_eval_for_model(champion, df_perf, cached_frames)
    champ_regrets = formation_xi_regret_by_gameweek(champ_eval, target_column="blended_points")

    variants: dict[str, MLComponentChallengerModel] = {
        "evt_goals_ridge": MLComponentChallengerModel(
            enable_mins_h1=False, enable_mins_h2=False, enable_mins_h3=False,
            enable_goals=True, enable_assists=False, enable_defense=False, enable_bonus=False,
        ),
        "evt_assists_loo": MLComponentChallengerModel(
            enable_mins_h1=False, enable_mins_h2=False, enable_mins_h3=False,
            enable_goals=False, enable_assists=True, enable_defense=False, enable_bonus=False,
        ),
        "evt_defense_multipliers": MLComponentChallengerModel(
            enable_mins_h1=False, enable_mins_h2=False, enable_mins_h3=False,
            enable_goals=False, enable_assists=False, enable_defense=True, enable_bonus=False,
        ),
        "evt_bonus_bps_ridge": MLComponentChallengerModel(
            enable_mins_h1=False, enable_mins_h2=False, enable_mins_h3=False,
            enable_goals=False, enable_assists=False, enable_defense=False, enable_bonus=True,
        ),
        "evt_stacked_events": MLComponentChallengerModel(
            enable_mins_h1=False, enable_mins_h2=False, enable_mins_h3=False,
            enable_goals=True, enable_assists=True, enable_defense=True, enable_bonus=True,
        ),
    }

    results: list[dict[str, Any]] = []

    for name, model in variants.items():
        logger.info("Evaluating Tier 2 Oracle variant: %s...", name)
        t0 = time.time()
        cand_metrics, cand_eval = _run_oracle_eval_for_model(model, df_perf, cached_frames)
        champ_m, cand_m = compute_playable_pool_metrics(champ_eval, cand_eval, target_column="blended_points")
        cand_playable_bias = float(cand_m["bias"])
        champ_playable_bias = float(champ_m["bias"])
        cand_regrets = formation_xi_regret_by_gameweek(cand_eval, target_column="blended_points")

        gws = sorted(set(champ_regrets.keys()) & set(cand_regrets.keys()))
        gw_deltas = [champ_regrets[g] - cand_regrets[g] for g in gws]

        verdict = evaluate_oracle_event_gate(
            champ_metrics,
            cand_metrics,
            gw_oracle_deltas=gw_deltas,
            champion_playable_bias=champ_playable_bias,
            candidate_playable_bias=cand_playable_bias,
        )

        row = {
            "variant": name,
            "passed": verdict.passed,
            "oracle_delta": round(verdict.oracle_delta, 4),
            "cand_oracle_regret": round(verdict.candidate_oracle_regret, 4),
            "champ_oracle_regret": round(verdict.champion_oracle_regret, 4),
            "bootstrap_p": round(verdict.bootstrap_p, 4) if verdict.bootstrap_p is not None else None,
            "cand_playable_bias": round(verdict.candidate_playable_bias, 4),
            "champ_playable_bias": round(verdict.champion_playable_bias, 4),
            "cand_captain_regret": round(verdict.candidate_captain_regret, 4),
            "champ_captain_regret": round(verdict.champion_captain_regret, 4),
            "reasons": "; ".join(verdict.reasons) if verdict.reasons else "All criteria passed",
            "elapsed_s": round(time.time() - t0, 2),
        }
        logger.info(
            "%s: %s | Δ_oracle=%+.4f (boot P=%s) | Playable Bias=%+.4f (champ=%+.4f) | Cap Regret=%.3f (champ=%.3f)",
            name, "PASS" if verdict.passed else "FAIL", row["oracle_delta"], row["bootstrap_p"],
            row["cand_playable_bias"], row["champ_playable_bias"],
            row["cand_captain_regret"], row["champ_captain_regret"],
        )
        results.append(row)

    out_df = pd.DataFrame(results)
    out_path = RESEARCH_DIR / "tier2_oracle_event_ablation.csv"
    out_df.to_csv(out_path, index=False)
    logger.info("Saved Tier 2 ablation results to %s", out_path)
    return out_df


def main() -> None:
    parser = argparse.ArgumentParser(description="Ablation and Gating Runner for ML Component Blueprint.")
    parser.add_argument(
        "--stage",
        choices=["ablations", "tier1", "tier2", "dev_gate"],
        default="ablations",
        help="Pipeline stage to execute",
    )
    parser.add_argument("--start_gw", type=int, default=1, help="Start gameweek (default: 1)")
    parser.add_argument("--end_gw", type=int, default=38, help="End gameweek (default: 38)")
    args = parser.parse_args()

    df_perf, cached_frames = precompute_season_frames(DEV_DATA_DIR, start_gw=args.start_gw, end_gw=args.end_gw)

    if args.stage in ("ablations", "tier1"):
        run_tier1_minutes_ablation(df_perf, cached_frames)

    if args.stage in ("ablations", "tier2"):
        run_tier2_oracle_event_ablation(df_perf, cached_frames)

    logger.info("Done executing stage: %s", args.stage)


if __name__ == "__main__":
    main()
