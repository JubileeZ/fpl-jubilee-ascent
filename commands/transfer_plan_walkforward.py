"""CLI for 2025-26 First-Half Transfer Plan Walk-Forward (ADR 0020)."""

from __future__ import annotations

import argparse
import logging
import shutil
import sys
import tempfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from clients.env_loader import configure_utf8_stdio, load_env

load_env()
configure_utf8_stdio()

from backtesting.strategy_policy import require_prior_season_seed
from backtesting.transfer_plan_walkforward import (
    OutcomesForWeek,
    SolveWeek,
    blocked_summary_rows,
    write_summary_csv,
)
from backtesting.walkforward_solve import (
    FIRST_HALF_LAST_GW,
    make_solve_week,
    outcomes_from_performances,
    run_first_half_ranking,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = PROJECT_ROOT / "data" / "archive" / "2025-26" / "processed"
DEFAULT_SEED = PROJECT_ROOT / "data" / "archive" / "2024-25" / "processed"
DEFAULT_OUTPUT = PROJECT_ROOT / "docs" / "research" / "tp-walkforward-gw1-19-2025-26" / "tp_walkforward_summary.csv"


def main(
    argv: list[str] | None = None,
    *,
    solve_week: SolveWeek | None = None,
    outcomes_for_week: OutcomesForWeek | None = None,
) -> int:
    parser = argparse.ArgumentParser(description="First-Half Transfer Plan Walk-Forward (ADR 0020)")
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
    work_dir: Path | None = None
    if solve_week is None:
        scratch = PROJECT_ROOT / ".tmp" / "agent"
        scratch.mkdir(parents=True, exist_ok=True)
        work_dir = Path(tempfile.mkdtemp(prefix="tp-wf-", dir=str(scratch)))
        solve_week = make_solve_week(
            processed_dir=args.data_dir,
            seed_dir=args.seed_dir,
            work_dir=work_dir,
        )
    resolved_outcomes = outcomes_for_week
    if resolved_outcomes is None:
        players = pd.read_parquet(args.data_dir / "players.parquet")
        performances = pd.read_parquet(args.data_dir / "player_performances.parquet")

        def archive_outcomes(gw: int):
            return outcomes_from_performances(performances, players, gw)

        resolved_outcomes = archive_outcomes
    try:
        rows = run_first_half_ranking(
            gameweeks=range(1, FIRST_HALF_LAST_GW + 1),
            solve_week=solve_week,
            outcomes_for_week=resolved_outcomes,
        )
    finally:
        if work_dir is not None:
            shutil.rmtree(work_dir, ignore_errors=True)
    write_summary_csv(args.output, rows)
    logger.info("Wrote %s", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
