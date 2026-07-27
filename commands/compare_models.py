"""Read-only Comparison Slate scorecard."""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from clients.env_loader import configure_utf8_stdio, load_env

load_env()
configure_utf8_stdio()

from backtesting.model_evaluation import compare_to_reference
from backtesting.promotion import primary_metric_name, primary_metric_value
from backtesting.walkforward import WalkforwardConfig, run_walkforward_backtest
from commands.backtest import resolve_backtest_data_dir, resolve_seed_processed_dir
from models.selection import DEFAULT_CONFIG_PATH, load_model_selection

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _parse_gw_range(gw_range: str) -> tuple[int, int]:
    start_gw, end_gw = map(int, gw_range.split("-"))
    return start_gw, end_gw


def _git_commit() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _run_model(
  *,
  model_name: str,
  data_dir: Path,
  start_gw: int,
  end_gw: int,
  seed_season: str | None,
  snapshot_root: Path | None,
  snapshot_season: str | None,
  require_snapshots: bool,
) -> object:
    seed_processed_dir = resolve_seed_processed_dir(data_dir, model_name, seed_season)
    return run_walkforward_backtest(
        WalkforwardConfig(
            model_name=model_name,
            data_dir=data_dir,
            start_gw=start_gw,
            end_gw=end_gw,
            seed_processed_dir=seed_processed_dir,
            snapshot_root=snapshot_root,
            snapshot_season=snapshot_season,
            require_snapshots=require_snapshots,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare the Comparison Slate models on historical data.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--gw_range", type=str, default="1-38")
    parser.add_argument("--data_dir", type=str, default="data/processed")
    parser.add_argument("--seed_season", type=str, default=None)
    parser.add_argument("--snapshot_root", type=str, default=None)
    parser.add_argument("--season", type=str, default=None)
    parser.add_argument("--require_snapshots", action="store_true")
    args = parser.parse_args()

    selection = load_model_selection(args.config)
    start_gw, end_gw = _parse_gw_range(args.gw_range)
    data_dir = resolve_backtest_data_dir((PROJECT_ROOT / args.data_dir).resolve())
    snapshot_root = Path(args.snapshot_root).resolve() if args.snapshot_root else None
    snapshot_season = args.season or (data_dir.parent.name if data_dir.parent.name != "data" else None)

    champion_result = _run_model(
        model_name=selection.champion,
        data_dir=data_dir,
        start_gw=start_gw,
        end_gw=end_gw,
        seed_season=args.seed_season,
        snapshot_root=snapshot_root,
        snapshot_season=snapshot_season,
        require_snapshots=args.require_snapshots,
    )
    primary_name = primary_metric_name(champion_result.metrics)

    print("\n" + "=" * 72)
    print("COMPARISON SLATE SCORECARD")
    print("=" * 72)
    print(f"Champion        : {selection.champion}")
    print(f"Candidates      : {', '.join(selection.candidates) or 'none'}")
    print(f"Gameweek Range  : {start_gw}-{end_gw}")
    print(f"Data Directory  : {data_dir}")
    print(f"Primary Metric  : {primary_name}")
    print(f"Git Commit      : {_git_commit() or 'unknown'}")
    print("-" * 72)
    print(
        f"{'Model':<30} {'Primary':>10} {'xP MAE':>10} {'xMins MAE':>10} "
        f"{'Bias':>10} {'Spearman':>10} {'Gate':>8}"
    )
    print("-" * 72)

    champion_primary = primary_metric_value(champion_result.metrics)
    champion_minutes = champion_result.metrics.get("minutes_forecast_metrics") or {}
    champion_spearman = champion_result.metrics.get("spearman")
    print(
        f"{selection.champion:<30} "
        f"{champion_primary:>10.4f} "
        f"{champion_result.metrics['mae']:>10.4f} "
        f"{champion_minutes.get('mae', float('nan')):>10.4f} "
        f"{champion_result.metrics['bias']:>10.4f} "
        f"{(champion_spearman if champion_spearman is not None else float('nan')):>10.4f} "
        f"{'n/a':>8}"
    )

    for candidate in selection.candidates:
        candidate_result = _run_model(
            model_name=candidate,
            data_dir=data_dir,
            start_gw=start_gw,
            end_gw=end_gw,
            seed_season=args.seed_season,
            snapshot_root=snapshot_root,
            snapshot_season=snapshot_season,
            require_snapshots=args.require_snapshots,
        )
        verdict = compare_to_reference(champion_result, candidate_result)
        candidate_minutes = candidate_result.metrics.get("minutes_forecast_metrics") or {}
        candidate_spearman = candidate_result.metrics.get("spearman")
        gate = "pass" if verdict.passed else "fail"
        print(
            f"{candidate:<30} "
            f"{primary_metric_value(candidate_result.metrics):>10.4f} "
            f"{candidate_result.metrics['mae']:>10.4f} "
            f"{candidate_minutes.get('mae', float('nan')):>10.4f} "
            f"{candidate_result.metrics['bias']:>10.4f} "
            f"{(candidate_spearman if candidate_spearman is not None else float('nan')):>10.4f} "
            f"{gate:>8}"
        )
        if not verdict.passed and verdict.reasons:
            print(f"  reasons: {', '.join(verdict.reasons)}")
    print("=" * 72 + "\n")


if __name__ == "__main__":
    main()
