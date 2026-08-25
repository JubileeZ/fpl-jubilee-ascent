"""CLI for 2025-26 First-Half Transfer Plan Walk-Forward (ADR 0019)."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from clients.env_loader import configure_utf8_stdio, load_env

load_env()
configure_utf8_stdio()

from backtesting.strategy_policy import require_prior_season_seed
from backtesting.transfer_plan_walkforward import blocked_summary_rows, write_summary_csv

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = PROJECT_ROOT / "data" / "archive" / "2025-26" / "processed"
DEFAULT_SEED = PROJECT_ROOT / "data" / "archive" / "2024-25" / "processed"
DEFAULT_OUTPUT = PROJECT_ROOT / "docs" / "research" / "tp-walkforward-gw1-19-2025-26" / "tp_walkforward_summary.csv"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="First-Half Transfer Plan Walk-Forward (ADR 0019)")
    parser.add_argument("--data_dir", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--seed_dir", type=Path, default=DEFAULT_SEED)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        require_prior_season_seed(args.seed_dir)
    except FileNotFoundError as exc:
        detail = str(exc)
        write_summary_csv(args.output, blocked_summary_rows(detail))
        logger.error("%s", detail)
        return 1
    logger.error(
        "Prior-Season Seed is present at %s but the MILP walk-forward loop is not executed from this CLI yet. "
        "OAT arms are scored through backtesting.transfer_plan_walkforward with an injected solver.",
        args.seed_dir,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
