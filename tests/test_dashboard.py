import json
from pathlib import Path
import pandas as pd

from commands.export_dashboard import build_dashboard_dataset, export_dashboard_data


def test_build_dashboard_dataset(tmp_path: Path):
    processed_dir = tmp_path / "data" / "processed"
    processed_dir.mkdir(parents=True)

    # 1. Create mock players parquet
    players_df = pd.DataFrame([
        {
            "id": 1,
            "code": 101,
            "first_name": "Erling",
            "second_name": "Haaland",
            "web_name": "Haaland",
            "club_id": 1,
            "position_id": 4,  # FWD
            "now_cost": 150,
            "status": "a",
            "chance_of_playing_next_round": 100,
            "news": "",
            "total_points": 200,
            "minutes": 1800,
            "starts": 20,
            "ict_index": "250.0",
            "influence": "100.0",
            "creativity": "50.0",
            "threat": "100.0",
            "expected_goals": "15.0",
            "expected_assists": "5.0",
        },
        {
            "id": 2,
            "code": 102,
            "first_name": "Mohamed",
            "second_name": "Salah",
            "web_name": "Salah",
            "club_id": 2,
            "position_id": 3,  # MID
            "now_cost": 125,
            "status": "a",
            "chance_of_playing_next_round": 100,
            "news": "",
            "total_points": 180,
            "minutes": 1620,
            "starts": 18,
            "ict_index": "220.0",
            "influence": "90.0",
            "creativity": "80.0",
            "threat": "50.0",
            "expected_goals": "12.0",
            "expected_assists": "8.0",
        },
    ])
    players_df.to_parquet(processed_dir / "players.parquet")

    # 2. Create mock clubs parquet
    clubs_df = pd.DataFrame([
        {"id": 1, "name": "Manchester City", "short_name": "MCI"},
        {"id": 2, "name": "Liverpool", "short_name": "LIV"},
    ])
    clubs_df.to_parquet(processed_dir / "clubs.parquet")

    # 3. Create mock gameweeks parquet
    gameweeks_df = pd.DataFrame([
        {"id": 1, "name": "Gameweek 1", "is_next": True, "finished": False},
        {"id": 2, "name": "Gameweek 2", "is_next": False, "finished": False},
    ])
    gameweeks_df.to_parquet(processed_dir / "gameweeks.parquet")

    # Mock predictions DataFrame
    predictions_df = pd.DataFrame([
        {
            "player_id": 1,
            "gameweek_id": 1,
            "projected_points": 7.5,
            "projected_minutes": 85.0,
            "xp_goals": 1.0,  # FWD goal = 4 pts
            "xp_assists": 0.5, # 1.5 pts
            "xp_clean_sheet": 0.0,
            "xp_defcon": 0.0,
            "xp_bonus": 1.0,
        },
        {
            "player_id": 2,
            "gameweek_id": 1,
            "projected_points": 8.0,
            "projected_minutes": 90.0,
            "xp_goals": 0.8,  # MID goal = 5 pts -> 4.0 pts
            "xp_assists": 0.6, # 1.8 pts
            "xp_clean_sheet": 0.4, # MID CS = 1 pt -> 0.4 pts
            "xp_defcon": 0.0,
            "xp_bonus": 1.2,
        },
    ])

    dataset = build_dashboard_dataset(
        processed_dir=processed_dir,
        predictions_df=predictions_df,
        target_gw=1,
        horizon=1,
    )

    assert "players" in dataset
    assert "meta" in dataset
    assert len(dataset["players"]) == 2

    haaland = next(p for p in dataset["players"] if p["id"] == 1)
    assert haaland["name"] == "Haaland"
    assert haaland["team"] == "MCI"
    assert haaland["price"] == 15.0
    assert haaland["pts_per_start"] == 10.0  # 200 / 20
    assert haaland["pts_per_90"] == 10.0     # (200 / 1800) * 90
    assert "projections" in haaland
    assert "gw1" in haaland["projections"]
    gw1 = haaland["projections"]["gw1"]
    assert gw1["xg_pts"] == 4.0  # 1.0 * 4
    assert gw1["xa_pts"] == 1.5  # 0.5 * 3
    assert gw1["total_xp"] == 7.5


def test_export_dashboard_data_writes_json(tmp_path: Path):
    output_path = tmp_path / "dashboard_data.json"
    dummy_data = {"meta": {"target_gw": 1}, "players": []}
    export_dashboard_data(dummy_data, output_path)

    assert output_path.exists()
    with open(output_path, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded["meta"]["target_gw"] == 1
