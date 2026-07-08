import subprocess
import sys
import pandas as pd

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
