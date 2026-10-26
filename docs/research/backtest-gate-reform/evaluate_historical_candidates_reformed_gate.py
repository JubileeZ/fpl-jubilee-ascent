"""Historical Candidate Re-evaluation under Reformed Gate (ADR 0064, Ticket #173).

Evaluates the 3 canonical cases from the quantitative audit brief:
1. adaptive_causal_challenger vs def_xg_shrink_challenger (Active Champion baseline)
2. bounded_causal_challenger vs adaptive_causal_challenger (GW10 clamp candidate)
3. apex_predator_challenger vs adaptive_causal_challenger (GW10 + congestion candidate)

Evaluates under:
- Dev Season: 2025-26 (seeded with 2024-25)
- Confirmation Season: 2024-25 (warm-seeded with 2023-24 archive)
- Constrained Legal Formation XI (£83.5m budget cap, max 3 per club, tie-breaking)
- Exogenous Playable Pool mask (Mins >= 30 or champ xP >= 2.0)
- Active-Window Guardrails (G_active) & Squad Churn (<= +0.50 players/GW)
- Non-wrapping Moving Block Bootstrap (L=5)
- sqrt(n_s)-scaled segment floors (cold_start >= -0.25, early_mid >= -0.15, late >= -0.13, active win >= 1)
- Pooled 2-Season Stratified Gate (Dev P >= 0.75, Conf P >= 0.65, Pooled P >= 0.85)

Results are cached to data/reports/walkforward_cache/{season}_{model}.parquet so subsequent
invocations run in sub-second time.
"""

from __future__ import annotations

import csv
import logging
import sys
import time
from dataclasses import dataclass
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

from backtesting.metrics import evaluate_predictions
from backtesting.model_evaluation import compare_two_season_gate
from backtesting.process_points import aggregate_process_points, blended_points
from backtesting.promotion import POOLED_BOOTSTRAP_MIN_P
from backtesting.walkforward import (
    LEDGER_COMPONENTS,
    PLAYER_POSITIONS,
    WalkforwardResult,
    _build_actual_components,
    load_gameweek_deadlines,
)
from features.builder import build_features, history_before_target
from models import get_model

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

CACHE_DIR = PROJECT_ROOT / "data" / "reports" / "walkforward_cache"
CANDIDATE_MODELS = (
    "def_xg_shrink_challenger",
    "adaptive_causal_challenger",
    "bounded_causal_challenger",
    "apex_predator_challenger",
)


@dataclass(frozen=True)
class CandidateReEvalResult:
    case_name: str
    candidate: str
    champion: str
    dev_passed: bool
    dev_delta: float
    dev_boot_p: float
    dev_segs: str
    dev_reasons: str
    conf_passed: bool
    conf_delta: float
    conf_boot_p: float
    conf_segs: str
    conf_reasons: str
    pooled_passed: bool
    pooled_boot_p: float
    final_verdict: str


def run_walkforward_for_model(
    season: str,
    seed_season: str,
    model_name: str,
    *,
    force: bool = False,
) -> WalkforwardResult:
    """Run full 38-GW walk-forward evaluation or load cached df_eval parquet."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / f"{season}_{model_name}.parquet"
    data_dir = PROJECT_ROOT / "data" / "archive" / season / "processed"

    if cache_file.exists() and not force:
        logger.info("Loading cached %s evaluation for season %s from %s", model_name, season, cache_file)
        df_eval = pd.read_parquet(cache_file)
        metrics = evaluate_predictions(df_eval, target_column="blended_points")
        return WalkforwardResult(
            model_name=model_name,
            data_dir=data_dir,
            start_gw=1,
            end_gw=38,
            metrics=metrics,
            df_eval=df_eval,
            snapshot_ids={},
            snapshot_backed=False,
        )

    logger.info("Running live walk-forward for %s on %s (seeded with %s)...", model_name, season, seed_season)
    t0 = time.time()
    seed_dir = PROJECT_ROOT / "data" / "archive" / seed_season / "processed"
    df_perf = pd.read_parquet(data_dir / "player_performances.parquet")
    deadlines = load_gameweek_deadlines(data_dir)
    model = get_model(model_name)
    results: list[pd.DataFrame] = []

    for gw in range(1, 39):
        df_feat = build_features(
            data_dir,
            target_gw=gw,
            horizon=1,
            seed_processed_dir=seed_dir,
            use_archive_seed=False,
            as_of_gw=gw,
            season=season,
            target_deadline=deadlines.get(gw),
        )
        if "position_id" in df_feat.columns:
            df_feat = df_feat[df_feat["position_id"].isin(PLAYER_POSITIONS)]

        hist = history_before_target(df_perf, gw, deadlines.get(gw), False)
        if hasattr(model, "fit"):
            model.fit(hist)

        df_proj = model.predict(df_feat, horizon=1)
        comp_cols = [c for c in LEDGER_COMPONENTS if c in df_proj.columns]
        proj_group_cols = ["projected_points", "projected_minutes"] + comp_cols
        df_proj_gw = (
            df_proj[df_proj["gameweek_id"] == gw]
            .groupby(["player_id", "gameweek_id"], as_index=False)[proj_group_cols]
            .sum()
        )

        gw_perf = _build_actual_components(df_perf[df_perf["gameweek_id"] == gw].copy(), df_feat)
        actual_group_cols = ["total_points", "minutes"] + [
            f"actual_{component}" for component in LEDGER_COMPONENTS
        ]
        actual_group_cols = [c for c in actual_group_cols if c in gw_perf.columns]
        df_actual_gw = (
            gw_perf.groupby(["player_id", "gameweek_id"], as_index=False)[actual_group_cols]
            .sum()
            .rename(columns={"total_points": "actual_points", "minutes": "actual_minutes"})
        )

        df_compare = df_proj_gw.merge(df_actual_gw, on=["player_id", "gameweek_id"], how="left")
        fill_cols = [c for c in df_compare.columns if c.startswith(("actual_", "xp_"))]
        df_compare[fill_cols] = df_compare[fill_cols].fillna(0.0)

        meta_cols = [c for c in ["player_id", "position_id", "now_cost", "club_id"] if c in df_feat.columns]
        player_meta = df_feat[meta_cols].drop_duplicates("player_id")
        df_compare = df_compare.merge(player_meta, on="player_id", how="left")

        process_gw = aggregate_process_points(gw_perf)
        df_compare = df_compare.merge(process_gw, on=["player_id", "gameweek_id"], how="left")
        df_compare["process_points"] = df_compare["process_points"].fillna(0.0)
        df_compare["gameweek"] = gw
        results.append(df_compare)

    df_eval = pd.concat(results, ignore_index=True)
    df_eval["blended_points"] = blended_points(
        df_eval["actual_points"], df_eval["process_points"], weight=0.5
    )
    df_eval.to_parquet(cache_file)
    logger.info("Saved %s evaluation to %s in %.1fs", model_name, cache_file, time.time() - t0)

    metrics = evaluate_predictions(df_eval, target_column="blended_points")
    return WalkforwardResult(
        model_name=model_name,
        data_dir=data_dir,
        start_gw=1,
        end_gw=38,
        metrics=metrics,
        df_eval=df_eval,
        snapshot_ids={},
        snapshot_backed=False,
    )


def run_historical_reevaluations(*, force: bool = False) -> list[CandidateReEvalResult]:
    """Execute evaluation for the 3 historical candidates under ADR 0064 criteria."""
    logger.info("Evaluating all historical models on 2025-26 and 2024-25 archives...")
    dev_results: dict[str, WalkforwardResult] = {}
    conf_results: dict[str, WalkforwardResult] = {}

    for model_name in CANDIDATE_MODELS:
        dev_results[model_name] = run_walkforward_for_model(
            "2025-26", "2024-25", model_name, force=force
        )
        conf_results[model_name] = run_walkforward_for_model(
            "2024-25", "2023-24", model_name, force=force
        )

    cases = [
        (
            "Case 1 (Incumbent vs Adaptive ML)",
            "adaptive_causal_challenger",
            "def_xg_shrink_challenger",
        ),
        (
            "Case 2 (GW10 Clamped ML)",
            "bounded_causal_challenger",
            "adaptive_causal_challenger",
        ),
        (
            "Case 3 (Composite ML + Congestion)",
            "apex_predator_challenger",
            "adaptive_causal_challenger",
        ),
    ]

    results: list[CandidateReEvalResult] = []

    for case_name, cand_name, champ_name in cases:
        dev_ref = dev_results[champ_name]
        dev_cand = dev_results[cand_name]
        conf_ref = conf_results[champ_name]
        conf_cand = conf_results[cand_name]

        verdict = compare_two_season_gate(dev_ref, dev_cand, conf_ref, conf_cand)
        v_dev = verdict.dev_verdict
        v_conf = verdict.conf_verdict

        if verdict.passed:
            final_status = "PROMOTED (ADR 0064 Full Pass)"
        elif v_dev.passed and not v_conf.passed:
            final_status = f"REJECTED (Confirmation season failed: {'; '.join(v_conf.reasons)})"
        elif not v_dev.passed:
            final_status = f"REJECTED (Dev season failed: {'; '.join(v_dev.reasons)})"
        else:
            final_status = f"REJECTED (Pooled stratified P={verdict.pooled_bootstrap_p:.3f} < {POOLED_BOOTSTRAP_MIN_P:.2f})"

        results.append(
            CandidateReEvalResult(
                case_name=case_name,
                candidate=cand_name,
                champion=champ_name,
                dev_passed=v_dev.passed,
                dev_delta=v_dev.combined_primary_delta,
                dev_boot_p=v_dev.bootstrap_p if v_dev.bootstrap_p is not None else 0.0,
                dev_segs=f"{v_dev.segment_wins}/3",
                dev_reasons="; ".join(v_dev.reasons) or "None (Clean Pass)",
                conf_passed=v_conf.passed,
                conf_delta=v_conf.combined_primary_delta,
                conf_boot_p=v_conf.bootstrap_p if v_conf.bootstrap_p is not None else 0.0,
                conf_segs=f"{v_conf.segment_wins}/3",
                conf_reasons="; ".join(v_conf.reasons) or "None (Clean Pass)",
                pooled_passed=verdict.passed,
                pooled_boot_p=verdict.pooled_bootstrap_p,
                final_verdict=final_status,
            )
        )

    return results


def write_summary_csv(results: list[CandidateReEvalResult], output_csv: Path) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "case_name",
            "candidate",
            "champion",
            "dev_passed",
            "dev_delta",
            "dev_boot_p",
            "dev_segs",
            "dev_reasons",
            "conf_passed",
            "conf_delta",
            "conf_boot_p",
            "conf_segs",
            "conf_reasons",
            "pooled_passed",
            "pooled_boot_p",
            "final_verdict",
        ])
        for r in results:
            writer.writerow([
                r.case_name,
                r.candidate,
                r.champion,
                r.dev_passed,
                f"{r.dev_delta:+.4f}",
                f"{r.dev_boot_p:.3f}",
                r.dev_segs,
                r.dev_reasons,
                r.conf_passed,
                f"{r.conf_delta:+.4f}",
                f"{r.conf_boot_p:.3f}",
                r.conf_segs,
                r.conf_reasons,
                r.pooled_passed,
                f"{r.pooled_boot_p:.3f}",
                r.final_verdict,
            ])


def main() -> None:
    force = "--force" in sys.argv
    results = run_historical_reevaluations(force=force)
    output_dir = Path(__file__).resolve().parent
    csv_path = output_dir / "historical_candidate_re_evaluation_summary.csv"
    write_summary_csv(results, csv_path)
    print(f"\nRe-evaluation complete. Wrote empirical summary to: {csv_path}")
    for r in results:
        print(f"\n[{r.case_name}] {r.candidate} vs {r.champion}")
        print(f"  Dev 2025-26   : {'PASS' if r.dev_passed else 'FAIL'} (delta {r.dev_delta:+.4f}, P={r.dev_boot_p:.3f}, segs {r.dev_segs})")
        if r.dev_reasons != "None (Clean Pass)":
            print(f"    reasons: {r.dev_reasons}")
        print(f"  Conf 2024-25  : {'PASS' if r.conf_passed else 'FAIL'} (delta {r.conf_delta:+.4f}, P={r.conf_boot_p:.3f}, segs {r.conf_segs})")
        if r.conf_reasons != "None (Clean Pass)":
            print(f"    reasons: {r.conf_reasons}")
        print(f"  Pooled Gate   : {'PASS' if r.pooled_passed else 'FAIL'} (Pooled P={r.pooled_boot_p:.3f} >= {POOLED_BOOTSTRAP_MIN_P:.2f})")
        print(f"  Final Verdict : {r.final_verdict}")


if __name__ == "__main__":
    main()
