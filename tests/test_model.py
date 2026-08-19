import pandas as pd
from features.builder import build_features
from tests.expected_role_fixtures import role_kwargs, write_role_table
from models.linear_baseline import LinearBaseline
from projections.exporter import export_projections

def test_modeling_pipeline(tmp_path):
    processed_dir = tmp_path / "processed"
    processed_dir.mkdir()
    
    # 1. Create dummy Parquet files
    df_players = pd.DataFrame([
        {"id": 101, "first_name": "Bukayo", "second_name": "Saka", "web_name": "Saka", "club_id": 1, "position_id": 3, "now_cost": 100, "status": "a", "chance_of_playing_next_round": 100, "chance_of_playing_this_round": 100, "news": "", "news_added": None, "selected_by_percent": 35.0, "corners_and_indirect_freekicks_order": 1, "direct_freekicks_order": 1, "penalties_order": 1}
    ])
    df_players.to_parquet(processed_dir / "players.parquet")
    
    df_clubs = pd.DataFrame([
        {"id": 1, "name": "Arsenal", "short_name": "ARS", "strength": 4, "strength_overall_home": 1200, "strength_overall_away": 1250, "strength_attack_home": 1300, "strength_attack_away": 1350, "strength_defence_home": 1200, "strength_defence_away": 1250}
    ])
    df_clubs.to_parquet(processed_dir / "clubs.parquet")
    
    df_fixtures = pd.DataFrame([
        {"id": 10, "gameweek_id": 38, "kickoff_time": "2026-05-28T15:00:00Z", "home_club_id": 1, "away_club_id": 2, "finished": False, "started": False, "team_h_score": None, "team_a_score": None, "team_h_difficulty": 2, "team_a_difficulty": 5}
    ])
    df_fixtures.to_parquet(processed_dir / "fixtures.parquet")
    
    df_perf = pd.DataFrame([
        {"player_id": 101, "fixture_id": 1, "gameweek_id": 37, "opponent_club_id": 3, "was_home": True, "kickoff_time": "2026-05-21T15:00:00Z", "team_h_score": 2, "team_a_score": 0, "price": 100, "selected": 2000000, "transfers_balance": 1000, "transfers_in": 2000, "transfers_out": 1000, "minutes": 90, "total_points": 8}
    ])
    df_perf.to_parquet(processed_dir / "player_performances.parquet")
    
    # 2. Build features
    table = write_role_table(tmp_path / "roles.csv", [101])
    live_minutes = dict(
        blend_start_appearances=0,
        blend_full_appearances=1,
        **role_kwargs(table),
    )
    df_feat = build_features(processed_dir, target_gw=38, **live_minutes)
    assert len(df_feat) == 1
    assert df_feat.loc[0, "avg_points_3gw"] == 8.0
    assert df_feat.loc[0, "avg_mins_3gw"] == 90.0
    assert df_feat.loc[0, "difficulty"] == 2  # home perspective difficulty for Arsenal is 2
    
    # 3. Run model
    model = LinearBaseline()
    df_feat_horizon = build_features(processed_dir, target_gw=38, horizon=3, **live_minutes)
    df_proj = model.predict(df_feat_horizon, horizon=3)
    assert len(df_proj) == 3  # 3 weeks predictions for 1 player
    assert list(df_proj["gameweek_id"]) == [38, 39, 40]
    
    # 4. Export projections
    out_csv = tmp_path / "projections.csv"
    export_projections(df_proj, df_players, df_clubs, out_csv)
    assert out_csv.exists()
    
    df_csv = pd.read_csv(out_csv)
    assert len(df_csv) == 1
    assert "38_Pts" in df_csv.columns
    assert "38_xMins" in df_csv.columns
    
    # 5. Test auto-discovery
    from models import get_model
    discovered_model = get_model("linear_baseline")
    assert discovered_model.name == "linear_baseline"
    assert isinstance(discovered_model, LinearBaseline)

def test_run_model_gameweeks_negation(tmp_path):
    from unittest.mock import patch
    import commands.run_model
    from commands.run_model import main
    
    processed_dir = tmp_path / "data" / "processed"
    processed_dir.mkdir(parents=True)
    
    df_players = pd.DataFrame([
        {"id": 101, "first_name": "Bukayo", "second_name": "Saka", "web_name": "Saka", "club_id": 1, "position_id": 3, "now_cost": 100, "status": "a", "chance_of_playing_next_round": 100, "chance_of_playing_this_round": 100, "news": "", "news_added": None, "selected_by_percent": 35.0, "corners_and_indirect_freekicks_order": 1, "direct_freekicks_order": 1, "penalties_order": 1}
    ])
    df_players.to_parquet(processed_dir / "players.parquet")
    
    df_clubs = pd.DataFrame([
        {"id": 1, "name": "Arsenal", "short_name": "ARS", "strength": 4, "strength_overall_home": 1200, "strength_overall_away": 1250, "strength_attack_home": 1300, "strength_attack_away": 1350, "strength_defence_home": 1200, "strength_defence_away": 1250}
    ])
    df_clubs.to_parquet(processed_dir / "clubs.parquet")
    
    df_fixtures = pd.DataFrame([
        {"id": 10, "gameweek_id": 38, "kickoff_time": "2026-05-28T15:00:00Z", "home_club_id": 1, "away_club_id": 2, "finished": False, "started": False, "team_h_score": None, "team_a_score": None, "team_h_difficulty": 2, "team_a_difficulty": 5}
    ])
    df_fixtures.to_parquet(processed_dir / "fixtures.parquet")
    
    df_gw = pd.DataFrame([
        {"id": 37, "name": "GW 37", "deadline_time": "2026-05-21T15:00:00Z", "finished": True, "is_current": True, "is_next": False},
        {"id": 38, "name": "GW 38", "deadline_time": "2026-05-28T15:00:00Z", "finished": False, "is_current": False, "is_next": False}
    ])
    df_gw.to_parquet(processed_dir / "gameweeks.parquet")
    
    with patch.object(commands.run_model, "PROJECT_ROOT", tmp_path), \
         patch("sys.argv", ["commands.run_model", "linear_baseline", "--horizon", "1"]):
        with patch("commands.run_model.logger.warning") as mock_warn:
            main()
            mock_warn.assert_not_called()


def test_linear_model_xmins_cap_scales_points():
    df = pd.DataFrame(
        [
            {
                "player_id": 1,
                "gameweek_id": 1,
                "avg_points_3gw": 6.0,
                "avg_mins_3gw": 90.0,
                "difficulty": 3.0,
                "chance_of_playing": 100.0,
                "xmins_cap": 45.0,
            }
        ]
    )

    projection = LinearBaseline().predict(df, horizon=1).iloc[0]

    assert projection["projected_minutes"] == 45.0
    assert projection["projected_points"] == 3.0
