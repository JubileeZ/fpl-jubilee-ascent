from pathlib import Path

import pandas as pd
import pytest

from features.builder import build_features


def test_seed_state_minutes_prior_does_not_need_expected_role_table(tmp_path: Path) -> None:
    processed = tmp_path / "processed"
    processed.mkdir()
    pd.DataFrame(
        [
            {
                "id": 1,
                "code": 101,
                "club_id": 1,
                "position_id": 4,
                "now_cost": 90,
                "first_name": "A",
                "second_name": "One",
                "chance_of_playing_next_round": None,
            },
        ]
    ).to_parquet(processed / "players.parquet", index=False)
    pd.DataFrame([{"id": 1, "name": "A", "short_name": "A", "strength": 3}]).to_parquet(
        processed / "clubs.parquet", index=False
    )
    pd.DataFrame(
        [
            {
                "id": 1,
                "gameweek_id": 1,
                "home_club_id": 1,
                "away_club_id": 2,
                "team_h_difficulty": 3,
                "team_a_difficulty": 3,
            },
        ]
    ).to_parquet(processed / "fixtures.parquet", index=False)
    pd.DataFrame(columns=["player_id", "gameweek_id", "minutes", "total_points"]).to_parquet(
        processed / "player_performances.parquet", index=False
    )

    seed = tmp_path / "archive" / "2024-25" / "processed"
    seed.mkdir(parents=True)
    pd.DataFrame(
        [{"id": 1, "code": 101, "position_id": 4, "now_cost": 90, "club_id": 1, "first_name": "A", "second_name": "One"}]
    ).to_parquet(seed / "players.parquet", index=False)
    pd.DataFrame(
        [
            {
                "player_id": 1,
                "fixture_id": gw,
                "gameweek_id": gw,
                "minutes": 90,
                "starts": 1,
                "total_points": 2,
                "goals_scored": 0,
                "assists": 0,
                "clean_sheets": 0,
                "goals_conceded": 0,
                "own_goals": 0,
                "penalties_saved": 0,
                "penalties_missed": 0,
                "yellow_cards": 0,
                "red_cards": 0,
                "saves": 0,
                "bonus": 0,
            }
            for gw in range(1, 9)
        ]
    ).to_parquet(seed / "player_performances.parquet", index=False)

    df = build_features(
        processed,
        target_gw=1,
        seed_processed_dir=seed,
        use_archive_seed=False,
        minutes_prior_source="seed_state",
    )
    row = df[df["player_id"] == 1].iloc[0]
    assert row["p_start_prior"] == pytest.approx(1.0)
    assert row["p_dnp_prior"] == pytest.approx(0.0)
    assert row["xmins_if_start"] == pytest.approx(90.0)
