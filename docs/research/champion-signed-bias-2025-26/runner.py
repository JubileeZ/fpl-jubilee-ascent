"""Refresh Champion signed-bias companion (ADR 0033)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from commands.measure_champion_bias import main as measure_cli  # noqa: E402

OUTPUT = Path(__file__).resolve().parent / "champion_bias_summary.csv"


def main() -> int:
    return measure_cli(["--output", str(OUTPUT)])


if __name__ == "__main__":
    raise SystemExit(main())
