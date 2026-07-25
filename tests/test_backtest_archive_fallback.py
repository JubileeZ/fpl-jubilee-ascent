import subprocess
import sys
from pathlib import Path

import pandas as pd

from commands.backtest import resolve_backtest_data_dir


def _write_backtest_tables(processed_dir: Path) -> None:
    processed_dir.mkdir(parents=True)
    pd.DataFrame([
        {
            "id": 1,
            "first_name": "A",
            "second_name": "B",
            "web_name": "AB",
            "club_id": 1,
            "position_id": 1,
            "now_cost": 50,
            "status": "a",
            "chance_of_playing_next_round": 100,
            "chance_of_playing_this_round": 100,
        },
    ]).to_parquet(processed_dir / "players.parquet", index=False)
    pd.DataFrame([
        {"id": 1, "name": "Arsenal", "short_name": "ARS", "strength": 4},
    ]).to_parquet(processed_dir / "clubs.parquet", index=False)
    pd.DataFrame([
        {
            "id": 10,
            "gameweek_id": 15,
            "home_club_id": 1,
            "away_club_id": 2,
            "team_h_difficulty": 3,
            "team_a_difficulty": 3,
        },
    ]).to_parquet(processed_dir / "fixtures.parquet", index=False)
    pd.DataFrame([
        {
            "player_id": 1,
            "fixture_id": 10,
            "gameweek_id": 15,
            "minutes": 90,
            "total_points": 6,
        },
    ]).to_parquet(processed_dir / "player_performances.parquet", index=False)


def test_backtest_cli_uses_latest_archive_when_active_history_is_missing(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    active_dir = data_root / "processed"
    active_dir.mkdir(parents=True)
    older_archive = data_root / "archive" / "2024-25" / "processed"
    older_archive.mkdir(parents=True)
    pd.DataFrame([{"player_id": 1}]).to_parquet(
        older_archive / "player_performances.parquet",
        index=False,
    )
    latest_archive = data_root / "archive" / "2025-26" / "processed"
    _write_backtest_tables(latest_archive)

    assert resolve_backtest_data_dir(active_dir) == latest_archive

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "commands.backtest",
            "linear_baseline",
            "--gw_range",
            "15-15",
            "--data_dir",
            str(active_dir),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "BACKTESTING REPORT: LINEAR_BASELINE" in result.stdout
    assert f"Data Directory  : {latest_archive.resolve()}" in result.stdout
