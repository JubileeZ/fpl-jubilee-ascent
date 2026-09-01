import pandas as pd
import pytest

from features.builder import build_features
from tests.expected_role_fixtures import role_kwargs, write_role_table


def _write_current_processed(root):
    processed = root / "processed"
    processed.mkdir(parents=True)
    pd.DataFrame(
        [
            {"id": 1, "code": 101, "club_id": 1, "position_id": 4, "now_cost": 90, "chance_of_playing_next_round": None},
            {"id": 2, "code": 102, "club_id": 1, "position_id": 4, "now_cost": 90, "chance_of_playing_next_round": 100.0},
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
            {"id": 1, "code": 101, "position_id": 4, "now_cost": 90},
            {"id": 3, "code": 103, "position_id": 4, "now_cost": 90},
        ]
    ).to_parquet(archive / "players.parquet", index=False)
    # Player 1 prior: 16 goals in 800 mins (1.8/90). Player 3 prior: 0 goals in 800 mins.
    pd.DataFrame(
        [
            {
                "player_id": player_id,
                "gameweek_id": gameweek_id,
                "minutes": 100,
                "starts": 1,
                "goals_scored": goals_scored,
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
            for player_id, goals_scored in ((1, 2), (3, 0))
            for gameweek_id in range(1, 9)
        ]
    ).to_parquet(archive / "player_performances.parquet", index=False)


def test_new_player_uses_position_price_prior_not_zero(tmp_path):
    processed = _write_current_processed(tmp_path)
    _write_archive_seed(tmp_path)
    table = write_role_table(tmp_path / "roles.csv", [1])
    df = build_features(processed, target_gw=2, **role_kwargs(table))
    newcomer = df[df["player_id"] == 2].iloc[0]
    assert bool(newcomer["has_prior_seed"]) is False
    assert bool(newcomer["has_fallback_prior"]) is True
    assert bool(newcomer["has_seed"]) is True
    # Position/price prior = mean of {1.8, 0.0} = 0.9 goals/90.
    assert newcomer["per90_goals"] == 0.9
    assert newcomer["avg_mins_3gw"] > 0.0


def test_cold_start_uses_per_player_seed_and_prior_appearance_probability(tmp_path):
    processed = _write_current_processed(tmp_path)
    _write_archive_seed(tmp_path)
    table = write_role_table(tmp_path / "roles.csv", [1])
    df = build_features(processed, target_gw=2, **role_kwargs(table))
    player_one = df[df["player_id"] == 1].iloc[0]
    assert bool(player_one["has_prior_seed"]) is True
    assert player_one["per90_goals"] == pytest.approx(1.8)
    assert player_one["avg_mins_3gw"] == pytest.approx(100.0)
    assert player_one["chance_of_playing"] == pytest.approx(100.0)


def test_availability_override_does_not_cap_seeded_minutes(tmp_path):
    processed = _write_current_processed(tmp_path)
    _write_archive_seed(tmp_path)
    table = write_role_table(tmp_path / "roles.csv", [1])
    overrides = tmp_path / "availability_overrides.csv"
    overrides.write_text(
        "player_code,xmins_cap,source,expires_after_gw\n"
        "101,60,https://example.test/preseason,2\n",
        encoding="utf-8",
    )

    df = build_features(processed, target_gw=2, availability_overrides=overrides, **role_kwargs(table))

    assert pd.isna(df.loc[df["player_id"] == 1, "xmins_cap"].iloc[0])


def test_expired_availability_override_does_not_reject_projection(tmp_path):
    processed = _write_current_processed(tmp_path)
    _write_archive_seed(tmp_path)
    table = write_role_table(tmp_path / "roles.csv", [1])
    overrides = tmp_path / "availability_overrides.csv"
    overrides.write_text(
        "player_code,xmins_cap,source,expires_after_gw\n"
        "101,60,https://example.test/preseason,1\n",
        encoding="utf-8",
    )

    df = build_features(processed, target_gw=2, availability_overrides=overrides, **role_kwargs(table))
    assert pd.isna(df.loc[df["player_id"] == 1, "xmins_cap"].iloc[0])
