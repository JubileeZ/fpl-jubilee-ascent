"""Measure Model Champion signed bias vs Realized Points (ADR 0033)."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from clients.env_loader import configure_utf8_stdio, load_env

load_env()
configure_utf8_stdio()

from backtesting.champion_bias import champion_bias_row, write_champion_bias_csv
from backtesting.walkforward import WalkforwardConfig, run_walkforward_backtest
from commands.backtest import resolve_backtest_data_dir, resolve_seed_processed_dir
from models.selection import DEFAULT_CONFIG_PATH, load_model_selection

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = (
    PROJECT_ROOT / "docs" / "research" / "champion-signed-bias-2025-26" / "champion_bias_summary.csv"
)


def _parse_gw_range(gw_range: str) -> tuple[int, int]:
    start_gw, end_gw = map(int, gw_range.split("-"))
    return start_gw, end_gw


def measure_window(
    *,
    model_name: str,
    data_dir: Path,
    start_gw: int,
    end_gw: int,
    seed_season: str | None,
) -> dict[str, object]:
    seed_processed_dir = resolve_seed_processed_dir(data_dir, model_name, seed_season)
    result = run_walkforward_backtest(
        WalkforwardConfig(
            model_name=model_name,
            data_dir=data_dir,
            start_gw=start_gw,
            end_gw=end_gw,
            seed_processed_dir=seed_processed_dir,
        )
    )
    season = data_dir.parent.name if data_dir.parent.name != "data" else ""
    return champion_bias_row(result, evaluation_season=season, seed_season=seed_season)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write Champion signed-bias companion CSV (ADR 0033).")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--gw_range", type=str, default="1-38")
    parser.add_argument("--data_dir", type=str, default="data/archive/2025-26/processed")
    parser.add_argument("--seed_season", type=str, default="2024-25")
    parser.add_argument("--sanity_data_dir", type=str, default="data/archive/2026-27/processed")
    parser.add_argument("--sanity_gw_range", type=str, default="1-3")
    parser.add_argument("--sanity_seed_season", type=str, default="2025-26")
    args = parser.parse_args(argv)

    selection = load_model_selection(args.config)
    start_gw, end_gw = _parse_gw_range(args.gw_range)
    data_dir = resolve_backtest_data_dir((PROJECT_ROOT / args.data_dir).resolve())
    rows = [
        measure_window(
            model_name=selection.champion,
            data_dir=data_dir,
            start_gw=start_gw,
            end_gw=end_gw,
            seed_season=args.seed_season,
        )
    ]
    sanity_dir = (PROJECT_ROOT / args.sanity_data_dir).resolve()
    if (sanity_dir / "player_performances.parquet").exists():
        sanity_start, sanity_end = _parse_gw_range(args.sanity_gw_range)
        rows.append(
            measure_window(
                model_name=selection.champion,
                data_dir=resolve_backtest_data_dir(sanity_dir),
                start_gw=sanity_start,
                end_gw=sanity_end,
                seed_season=args.sanity_seed_season,
            )
        )
    output = args.output if args.output.is_absolute() else PROJECT_ROOT / args.output
    write_champion_bias_csv(output, rows)
    for row in rows:
        logger.info(
            "Champion signed_bias=%s mae=%s season=%s gw=%s-%s n=%s",
            row["signed_bias"],
            row["mae"],
            row["evaluation_season"],
            row["gw_start"],
            row["gw_end"],
            row["sample_count"],
        )
    logger.info("Wrote %s", output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
