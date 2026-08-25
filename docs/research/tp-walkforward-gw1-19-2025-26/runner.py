"""Refresh 2025-26 First-Half Transfer Plan Walk-Forward companions (ADR 0019)."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from occupancy import write_occupancy_csv  # noqa: E402
from commands.transfer_plan_walkforward import main as walkforward_cli  # noqa: E402

ARCHIVE_2025 = ROOT / "data" / "archive" / "2025-26" / "processed"
OUTPUT_DIR = Path(__file__).resolve().parent


def main() -> int:
    occupancy_path = OUTPUT_DIR / "def_rotation_club_occupancy.csv"
    if ARCHIVE_2025.exists():
        clubs = pd.read_parquet(ARCHIVE_2025 / "clubs.parquet")
        fixtures = pd.read_parquet(ARCHIVE_2025 / "fixtures.parquet")
        write_occupancy_csv(occupancy_path, clubs, fixtures)
    summary_path = OUTPUT_DIR / "tp_walkforward_summary.csv"
    return walkforward_cli(["--output", str(summary_path)])


if __name__ == "__main__":
    raise SystemExit(main())
