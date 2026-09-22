"""Export includes observed Δ£; no Differentials Ranking / EO payload."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from commands.export_dashboard import build_dashboard_dataset


def _minimal_processed(processed_dir: Path) -> None:
    processed_dir.mkdir(parents=True)
    pd.DataFrame([
        {
            "id": 1, "code": 1, "first_name": "A", "second_name": "One", "web_name": "One",
            "club_id": 1, "position_id": 3, "now_cost": 70, "status": "a",
            "chance_of_playing_next_round": 100, "news": "", "total_points": 10, "minutes": 90,
            "starts": 1, "ict_index": "0", "influence": "0", "creativity": "0", "threat": "0",
            "expected_goals": "0", "expected_assists": "0", "selected_by_percent": 5.0,
        },
        {
            "id": 2, "code": 2, "first_name": "B", "second_name": "Two", "web_name": "Two",
            "club_id": 1, "position_id": 4, "now_cost": 80, "status": "a",
            "chance_of_playing_next_round": 100, "news": "", "total_points": 10, "minutes": 90,
            "starts": 1, "ict_index": "0", "influence": "0", "creativity": "0", "threat": "0",
            "expected_goals": "0", "expected_assists": "0", "selected_by_percent": 2.0,
        },
    ]).to_parquet(processed_dir / "players.parquet")
    pd.DataFrame([{"id": 1, "name": "Arsenal", "short_name": "ARS"}]).to_parquet(
        processed_dir / "clubs.parquet"
    )
    pd.DataFrame([{"id": 1, "name": "Gameweek 1", "is_next": True, "finished": False}]).to_parquet(
        processed_dir / "gameweeks.parquet"
    )
    pd.DataFrame([{
        "id": 10, "gameweek_id": 1, "home_club_id": 1, "away_club_id": 1,
        "team_h_difficulty": 3, "team_a_difficulty": 3, "kickoff_time": None,
    }]).to_parquet(processed_dir / "fixtures.parquet")
    pd.DataFrame([
        {"player_id": 1, "element": 1, "position": 1, "is_captain": False, "is_vice_captain": False, "selling_price": 65},
    ]).to_parquet(processed_dir / "user_picks.parquet")
    pd.DataFrame([{"bank": 10, "transfers": 1}]).to_parquet(processed_dir / "user_state.parquet")


def test_export_price_delta_without_differentials(tmp_path: Path) -> None:
    processed = tmp_path / "processed"
    _minimal_processed(processed)
    history = pd.DataFrame([
        {"player_id": 1, "now_cost": 65, "gameweek_id": 1, "captured_at": "2026-09-01T00:00:00Z", "web_name": "One"},
        {"player_id": 2, "now_cost": 80, "gameweek_id": 1, "captured_at": "2026-09-01T00:00:00Z", "web_name": "Two"},
        {"player_id": 1, "now_cost": 70, "gameweek_id": 1, "captured_at": "2026-09-08T00:00:00Z", "web_name": "One"},
        {"player_id": 2, "now_cost": 80, "gameweek_id": 1, "captured_at": "2026-09-08T00:00:00Z", "web_name": "Two"},
    ])
    history.to_parquet(processed / "price_history.parquet", index=False)
    preds = pd.DataFrame([
        {"player_id": 1, "gameweek_id": 1, "projected_points": 4.0, "projected_minutes": 90.0,
         "xp_goals": 0, "xp_assists": 0, "xp_clean_sheet": 0, "xp_defcon": 0, "xp_bonus": 0, "p_dnp": 0},
        {"player_id": 2, "gameweek_id": 1, "projected_points": 9.0, "projected_minutes": 90.0,
         "xp_goals": 0, "xp_assists": 0, "xp_clean_sheet": 0, "xp_defcon": 0, "xp_bonus": 0, "p_dnp": 0},
    ])
    dataset = build_dashboard_dataset(processed, preds, target_gw=1, horizon=1)
    by_id = {p["id"]: p for p in dataset["players"]}
    assert by_id[1]["change_since_refresh"] == 0.5
    assert by_id[2]["change_since_refresh"] == 0.0
    assert "differentials_ranking" not in dataset
