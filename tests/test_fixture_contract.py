from pathlib import Path

import pandas as pd

from features.builder import build_features


def _write_fixture_data(root: Path) -> Path:
    processed = root / "processed"
    processed.mkdir(parents=True)
    pd.DataFrame([
        {
            "id": 1,
            "club_id": 1,
            "position_id": 4,
            "now_cost": 90,
            "chance_of_playing_next_round": 0.0,
        },
    ]).to_parquet(processed / "players.parquet", index=False)
    pd.DataFrame([
        {
            "id": 1,
            "name": "Club A",
            "short_name": "A",
            "strength": 3,
            "strength_attack_home": 1400,
            "strength_defence_home": 1200,
        },
        {
            "id": 2,
            "name": "Club B",
            "short_name": "B",
            "strength": 3,
            "strength_attack_away": 900,
            "strength_defence_away": 1100,
        },
        {
            "id": 3,
            "name": "Club C",
            "short_name": "C",
            "strength": 3,
            "strength_attack_away": 1000,
            "strength_defence_away": 1000,
        },
    ]).to_parquet(processed / "clubs.parquet", index=False)
    pd.DataFrame([
        {
            "id": 10,
            "gameweek_id": 2,
            "home_club_id": 1,
            "away_club_id": 2,
            "team_h_difficulty": 2,
            "team_a_difficulty": 4,
        },
        {
            "id": 11,
            "gameweek_id": 2,
            "home_club_id": 1,
            "away_club_id": 3,
            "team_h_difficulty": 3,
            "team_a_difficulty": 3,
        },
    ]).to_parquet(processed / "fixtures.parquet", index=False)
    pd.DataFrame([
        {
            "player_id": 1,
            "gameweek_id": 1,
            "minutes": 90,
            "total_points": 5,
            "goals_scored": 1,
            "assists": 0,
        },
    ]).to_parquet(processed / "player_performances.parquet", index=False)
    return processed


def test_feature_contract_retains_fixture_rows_and_horizon(tmp_path):
    processed = _write_fixture_data(tmp_path)
    features = build_features(processed, target_gw=2, horizon=2, as_of_gw=2)

    target = features[features["player_id"] == 1]
    assert list(target[target["gameweek_id"] == 2]["fixture_id"]) == [10, 11]
    assert len(target[target["gameweek_id"] == 3]) == 1
    assert target["chance_of_playing"].eq(100.0).all()
    assert {"attack_multiplier", "defence_multiplier"}.issubset(features.columns)


def test_feature_contract_uses_as_of_availability_snapshot(tmp_path):
    processed = _write_fixture_data(tmp_path)
    pd.DataFrame([
        {"player_id": 1, "snapshot_gameweek_id": 2, "chance_of_playing_next_round": 50.0},
    ]).to_parquet(processed / "player_snapshots.parquet", index=False)

    features = build_features(processed, target_gw=2, as_of_gw=2)

    assert features["chance_of_playing"].eq(50.0).all()
