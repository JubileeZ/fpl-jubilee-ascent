from pathlib import Path

import pandas as pd

from backtesting.archive_static import bootstrap_from_processed, fixtures_from_processed


def test_bootstrap_from_processed_maps_ids(tmp_path: Path) -> None:
    processed = tmp_path / "processed"
    processed.mkdir()
    pd.DataFrame([{
        "id": 9, "code": 99, "first_name": "A", "second_name": "B", "web_name": "AB",
        "club_id": 2, "position_id": 3, "now_cost": 70,
    }]).to_parquet(processed / "players.parquet", index=False)
    pd.DataFrame([{"id": 2, "name": "Arsenal", "short_name": "ARS"}]).to_parquet(
        processed / "clubs.parquet", index=False
    )
    pd.DataFrame([{"id": 1, "is_next": True, "finished": False}]).to_parquet(
        processed / "gameweeks.parquet", index=False
    )
    pd.DataFrame([{
        "id": 10, "gameweek_id": 3, "home_club_id": 2, "away_club_id": 4,
    }]).to_parquet(processed / "fixtures.parquet", index=False)
    bootstrap = bootstrap_from_processed(processed)
    assert bootstrap["elements"][0]["id"] == 9
    assert bootstrap["elements"][0]["team"] == 2
    assert bootstrap["teams"][0]["short_name"] == "ARS"
    assert fixtures_from_processed(processed) == [{"event": 3, "team_h": 2, "team_a": 4}]
