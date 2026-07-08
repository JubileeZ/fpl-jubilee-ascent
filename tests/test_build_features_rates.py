import pandas as pd
from pathlib import Path

from features.builder import build_features


def _write_processed(tmp_path: Path) -> Path:
    proc = tmp_path / "processed"
    proc.mkdir()

    pd.DataFrame([
        {"id": 1, "club_id": 1, "position_id": 4, "now_cost": 90,
         "chance_of_playing_next_round": 100.0},
        {"id": 2, "club_id": 1, "position_id": 4, "now_cost": 50,
         "chance_of_playing_next_round": 100.0},
    ]).to_parquet(proc / "players.parquet", index=False)

    pd.DataFrame([{"id": 1, "name": "Arsenal", "short_name": "ARS", "strength": 4}]).to_parquet(
        proc / "clubs.parquet", index=False
    )

    pd.DataFrame([
        {"id": 10, "gameweek_id": 3, "home_club_id": 1, "away_club_id": 2,
         "team_h_difficulty": 3, "team_a_difficulty": 3},
    ]).to_parquet(proc / "fixtures.parquet", index=False)

    # Player 1: GW1 1 goal in 90 min, GW2 1 assist in 90 min. Player 2: no history.
    pd.DataFrame([
        {"player_id": 1, "gameweek_id": 1, "minutes": 90, "total_points": 8,
         "goals_scored": 1, "assists": 0, "clean_sheets": 0, "goals_conceded": 0,
         "own_goals": 0, "penalties_saved": 0, "penalties_missed": 0,
         "yellow_cards": 0, "red_cards": 0, "saves": 0, "bonus": 0},
        {"player_id": 1, "gameweek_id": 2, "minutes": 90, "total_points": 3,
         "goals_scored": 0, "assists": 1, "clean_sheets": 0, "goals_conceded": 0,
         "own_goals": 0, "penalties_saved": 0, "penalties_missed": 0,
         "yellow_cards": 0, "red_cards": 0, "saves": 0, "bonus": 0},
    ]).to_parquet(proc / "player_performances.parquet", index=False)

    return proc


def test_build_features_emits_per90_rates_and_seed_flag(tmp_path):
    proc = _write_processed(tmp_path)
    df = build_features(proc, target_gw=3)

    p1 = df[df["player_id"] == 1].iloc[0]
    # 1 goal + 0 assists over 180 min -> 0.5 goals/90, 0.5 assists/90.
    assert p1["per90_goals"] == 0.5
    assert p1["per90_assists"] == 0.5
    assert bool(p1["has_prior_seed"]) is True

    p2 = df[df["player_id"] == 2].iloc[0]
    assert bool(p2["has_prior_seed"]) is True
    assert p2["per90_goals"] == 0.5
