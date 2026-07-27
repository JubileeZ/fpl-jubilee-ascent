import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

from commands.backtest import resolve_seed_processed_dir
from features.availability_snapshots import write_availability_snapshot

def test_backtest_cli_run(tmp_path):
    data_dir = tmp_path / "processed"
    data_dir.mkdir()
    
    # 1. Create dummy Parquet files
    df_players = pd.DataFrame([
        {"id": 1, "first_name": "A", "second_name": "B", "web_name": "AB", "club_id": 1, "position_id": 1, "now_cost": 50, "status": "a", "chance_of_playing_next_round": 100, "chance_of_playing_this_round": 100, "news": "", "news_added": None, "selected_by_percent": 10.0, "corners_and_indirect_freekicks_order": None, "direct_freekicks_order": None, "penalties_order": None},
        {"id": 2, "first_name": "C", "second_name": "D", "web_name": "CD", "club_id": 1, "position_id": 1, "now_cost": 45, "status": "a", "chance_of_playing_next_round": 100, "chance_of_playing_this_round": 100, "news": "", "news_added": None, "selected_by_percent": 5.0, "corners_and_indirect_freekicks_order": None, "direct_freekicks_order": None, "penalties_order": None}
    ])
    df_players.to_parquet(data_dir / "players.parquet")
    
    df_clubs = pd.DataFrame([
        {"id": 1, "name": "Arsenal", "short_name": "ARS", "strength": 4, "strength_overall_home": 1200, "strength_overall_away": 1250, "strength_attack_home": 1300, "strength_attack_away": 1350, "strength_defence_home": 1200, "strength_defence_away": 1250}
    ])
    df_clubs.to_parquet(data_dir / "clubs.parquet")
    
    df_fixtures = pd.DataFrame([
        {"id": 10, "gameweek_id": 15, "kickoff_time": "2026-05-28T15:00:00Z", "home_club_id": 1, "away_club_id": 2, "finished": True, "started": True, "team_h_score": 1, "team_a_score": 1, "team_h_difficulty": 3, "team_a_difficulty": 3}
    ])
    df_fixtures.to_parquet(data_dir / "fixtures.parquet")
    
    df_perf = pd.DataFrame([
        {"player_id": 1, "fixture_id": 10, "gameweek_id": 15, "opponent_club_id": 2, "was_home": True, "kickoff_time": "2026-05-28T15:00:00Z", "team_h_score": 1, "team_a_score": 1, "price": 50, "selected": 10000, "transfers_balance": 0, "transfers_in": 0, "transfers_out": 0, "minutes": 90, "total_points": 6},
        {"player_id": 2, "fixture_id": 10, "gameweek_id": 15, "opponent_club_id": 2, "was_home": True, "kickoff_time": "2026-05-28T15:00:00Z", "team_h_score": 1, "team_a_score": 1, "price": 45, "selected": 5000, "transfers_balance": 0, "transfers_in": 0, "transfers_out": 0, "minutes": 90, "total_points": 2}
    ])
    df_perf.to_parquet(data_dir / "player_performances.parquet")
    
    cmd = [
        sys.executable, "-m", "commands.backtest", "linear_baseline",
        "--gw_range", "15-15",
        "--data_dir", str(data_dir)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0
    assert "BACKTESTING REPORT: LINEAR_BASELINE" in res.stdout
    assert "Points MAE" in res.stdout
    assert "Points RMSE" in res.stdout


def test_seed_based_backtest_rejects_its_evaluation_season(tmp_path):
    evaluation_dir = tmp_path / "data" / "archive" / "2025-26" / "processed"

    with pytest.raises(ValueError, match="both evaluation data and Prior-Season Seed"):
        resolve_seed_processed_dir(evaluation_dir, "metrics_component_hybrid", "2025-26")


def test_seed_based_backtest_rejects_later_seed_season(tmp_path: Path):
    evaluation_dir = tmp_path / "data" / "archive" / "2025-26" / "processed"

    with pytest.raises(ValueError, match="must precede evaluation season"):
        resolve_seed_processed_dir(evaluation_dir, "metrics_component_hybrid", "2026-27")


def test_point_in_time_backtest_requires_and_reports_snapshot(tmp_path: Path):
    data_dir = tmp_path / "processed"
    data_dir.mkdir()
    players = pd.DataFrame([
        {"id": 1, "club_id": 1, "position_id": 3, "now_cost": 60, "status": "a", "chance_of_playing_next_round": 100},
    ])
    clubs = pd.DataFrame([
        {"id": 1, "strength": 3},
        {"id": 2, "strength": 3},
    ])
    fixtures = pd.DataFrame([
        {
            "id": 10,
            "gameweek_id": 2,
            "kickoff_time": "2026-08-01T15:00:00Z",
            "home_club_id": 1,
            "away_club_id": 2,
            "team_h_difficulty": 3,
            "team_a_difficulty": 3,
        },
    ])
    players.to_parquet(data_dir / "players.parquet", index=False)
    clubs.to_parquet(data_dir / "clubs.parquet", index=False)
    fixtures.to_parquet(data_dir / "fixtures.parquet", index=False)
    pd.DataFrame([
        {"id": 1, "deadline_time": "2026-08-01T12:00:00Z"},
        {"id": 2, "deadline_time": "2026-08-08T12:00:00Z"},
    ]).to_parquet(data_dir / "gameweeks.parquet", index=False)
    pd.DataFrame([
        {
            "player_id": 1,
            "fixture_id": 10,
            "gameweek_id": 2,
            "kickoff_time": "2026-08-01T15:00:00Z",
            "minutes": 90,
            "total_points": 2,
        },
    ]).to_parquet(data_dir / "player_performances.parquet", index=False)
    deadline = datetime(2026, 8, 8, 12, tzinfo=UTC)
    snapshot_root = tmp_path / "snapshots"
    package = write_availability_snapshot(
        snapshot_root,
        "2026-27",
        2,
        deadline,
        deadline - timedelta(hours=1),
        players,
        clubs,
        fixtures,
    )
    assert package is not None

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "commands.backtest",
            "linear_baseline",
            "--gw_range",
            "2-2",
            "--data_dir",
            str(data_dir),
            "--snapshot_root",
            str(snapshot_root),
            "--season",
            "2026-27",
            "--require_snapshots",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Snapshots       : GW2=2026-27-GW2-" in result.stdout
