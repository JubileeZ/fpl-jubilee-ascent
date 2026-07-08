import pandas as pd

from features.builder import build_features


def _write_current_processed(root):
    processed = root / "processed"
    processed.mkdir(parents=True)
    pd.DataFrame(
        [
            {"id": 1, "club_id": 1, "position_id": 4, "now_cost": 90, "chance_of_playing_next_round": 100.0},
            {"id": 2, "club_id": 1, "position_id": 4, "now_cost": 90, "chance_of_playing_next_round": 100.0},
        ]
    ).to_parquet(processed / "players.parquet", index=False)
    pd.DataFrame([{"id": 1, "name": "A", "short_name": "A", "strength": 3}]).to_parquet(
        processed / "clubs.parquet", index=False
    )
    pd.DataFrame(
        [{"id": 1, "gameweek_id": 2, "home_club_id": 1, "away_club_id": 2, "team_h_difficulty": 3, "team_a_difficulty": 3}]
    ).to_parquet(processed / "fixtures.parquet", index=False)
    # No current-season history yet.
    pd.DataFrame(columns=["player_id", "gameweek_id", "minutes", "total_points"]).to_parquet(
        processed / "player_performances.parquet", index=False
    )
    return processed


def _write_archive_seed(root):
    archive = root / "archive" / "2025-26" / "processed"
    archive.mkdir(parents=True)
    pd.DataFrame(
        [
            {"id": 1, "position_id": 4, "now_cost": 90},
            {"id": 3, "position_id": 4, "now_cost": 90},
        ]
    ).to_parquet(archive / "players.parquet", index=False)
    # Player 1 prior: 2 goals in 100 mins (1.8/90). Player 3 prior: 0 goals in 100 mins.
    pd.DataFrame(
        [
            {"player_id": 1, "gameweek_id": 1, "minutes": 100, "goals_scored": 2, "assists": 0, "clean_sheets": 0, "goals_conceded": 0, "own_goals": 0, "penalties_saved": 0, "penalties_missed": 0, "yellow_cards": 0, "red_cards": 0, "saves": 0, "bonus": 0},
            {"player_id": 3, "gameweek_id": 1, "minutes": 100, "goals_scored": 0, "assists": 0, "clean_sheets": 0, "goals_conceded": 0, "own_goals": 0, "penalties_saved": 0, "penalties_missed": 0, "yellow_cards": 0, "red_cards": 0, "saves": 0, "bonus": 0},
        ]
    ).to_parquet(archive / "player_performances.parquet", index=False)


def test_new_player_uses_position_price_prior_not_zero(tmp_path):
    processed = _write_current_processed(tmp_path)
    _write_archive_seed(tmp_path)
    df = build_features(processed, target_gw=2)
    newcomer = df[df["player_id"] == 2].iloc[0]
    assert bool(newcomer["has_prior_seed"]) is True
    # Position/price prior = mean of {1.8, 0.0} = 0.9 goals/90.
    assert newcomer["per90_goals"] == 0.9
    assert newcomer["avg_mins_3gw"] > 0.0


def test_cold_start_disables_per_player_seed_gw1_to_4(tmp_path):
    processed = _write_current_processed(tmp_path)
    _write_archive_seed(tmp_path)
    df = build_features(processed, target_gw=2)
    player_one = df[df["player_id"] == 1].iloc[0]
    # Cold-start guard should ignore player-specific 1.8/90 and use 0.9 prior.
    assert player_one["per90_goals"] == 0.9
