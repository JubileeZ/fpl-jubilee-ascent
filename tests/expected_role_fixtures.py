"""Shared Expected Role Table fixture for Feature Contract tests."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

NAILED_PRIOR = {
    "p_start": 0.90,
    "p_sub_in": 0.05,
    "p_dnp": 0.05,
    "mins_if_start": 85.0,
    "mins_if_sub": 20.0,
    "draft_availability": "eligible",
    "availability_override": "",
}


def write_role_table(
    path: Path,
    player_ids: list[int],
    season: str = "2026-27",
) -> Path:
    rows = [{"player_id": pid, "season": season, **NAILED_PRIOR} for pid in player_ids]
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def role_kwargs(path: Path, season: str = "2026-27") -> dict[str, Path | str]:
    return {"expected_role_table": path, "season": season}
