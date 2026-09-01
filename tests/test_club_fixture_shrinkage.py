"""Feature Contract Club Fixture shrinkage (ADR 0022)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from features.builder import build_features
from tests.test_expected_role_prior import NAILED, _write_processed, _write_role_csv


def test_feature_contract_builds_when_expected_role_table_is_other_season(tmp_path: Path) -> None:
    processed = _write_processed(tmp_path)
    table = _write_role_csv(tmp_path / "roles.csv", [NAILED], season="2025-26")
    df = build_features(
        processed,
        target_gw=2,
        use_archive_seed=False,
        expected_role_table=table,
        expected_role_season="2026-27",
    )
    row = df[df["player_id"] == 1].iloc[0]
    assert row["p_dnp"] == pytest.approx(1.0 / 3.0)
    assert row["p_start"] == pytest.approx(1.0 / 3.0)
    assert row["xmins_if_start"] == pytest.approx(78.0)


def test_feature_contract_builds_when_expected_role_table_is_missing(tmp_path: Path) -> None:
    processed = _write_processed(tmp_path)
    df = build_features(
        processed,
        target_gw=2,
        use_archive_seed=False,
        expected_role_table=tmp_path / "missing-roles.csv",
        expected_role_season="2026-27",
    )
    assert df[df["player_id"] == 1].iloc[0]["p_start"] == pytest.approx(1.0 / 3.0)


def test_other_club_zero_minutes_are_not_current_club_dnp(tmp_path: Path) -> None:
    processed = tmp_path / "processed"
    processed.mkdir()
    pd.DataFrame(
        [{"id": 1, "club_id": 1, "position_id": 2, "now_cost": 60, "chance_of_playing_next_round": 100.0}]
    ).to_parquet(processed / "players.parquet", index=False)
    pd.DataFrame(
        [
            {"id": 1, "name": "Club A", "short_name": "A", "strength": 3},
            {"id": 2, "name": "Club B", "short_name": "B", "strength": 3},
        ]
    ).to_parquet(processed / "clubs.parquet", index=False)
    pd.DataFrame(
        [
            {
                "id": 101,
                "gameweek_id": 1,
                "home_club_id": 2,
                "away_club_id": 3,
                "team_h_difficulty": 3,
                "team_a_difficulty": 3,
            },
            {
                "id": 102,
                "gameweek_id": 2,
                "home_club_id": 1,
                "away_club_id": 2,
                "team_h_difficulty": 3,
                "team_a_difficulty": 3,
            },
        ]
    ).to_parquet(processed / "fixtures.parquet", index=False)
    pd.DataFrame(
        [
            {
                "player_id": 1,
                "fixture_id": 101,
                "gameweek_id": 1,
                "was_home": True,
                "minutes": 0,
                "starts": 0,
                "total_points": 0,
            }
        ]
    ).to_parquet(processed / "player_performances.parquet", index=False)
    row = build_features(processed, target_gw=2, use_archive_seed=False).iloc[0]
    assert row["p_dnp"] == pytest.approx(1.0 / 3.0)
    assert row["state_observation_weight"] == pytest.approx(0.0)


def test_event_rates_shrink_toward_prior_season_seed(tmp_path: Path) -> None:
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
                "chance_of_playing_next_round": 100.0,
            }
        ]
    ).to_parquet(processed / "players.parquet", index=False)
    pd.DataFrame([{"id": 1, "name": "A", "short_name": "A", "strength": 3}]).to_parquet(
        processed / "clubs.parquet", index=False
    )
    pd.DataFrame(
        [
            {
                "id": 1,
                "gameweek_id": 2,
                "home_club_id": 1,
                "away_club_id": 2,
                "team_h_difficulty": 3,
                "team_a_difficulty": 3,
            }
        ]
    ).to_parquet(processed / "fixtures.parquet", index=False)
    pd.DataFrame(
        [
            {
                "player_id": 1,
                "fixture_id": 1,
                "gameweek_id": 1,
                "was_home": True,
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
        ]
    ).to_parquet(processed / "player_performances.parquet", index=False)
    seed = tmp_path / "archive" / "2025-26" / "processed"
    seed.mkdir(parents=True)
    pd.DataFrame([{"id": 1, "code": 101, "position_id": 4, "now_cost": 90, "club_id": 1}]).to_parquet(
        seed / "players.parquet", index=False
    )
    pd.DataFrame(
        [
            {
                "player_id": 1,
                "fixture_id": gw,
                "gameweek_id": gw,
                "minutes": 100,
                "starts": 1,
                "total_points": 2,
                "goals_scored": 2,
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
    row = build_features(
        processed,
        target_gw=2,
        seed_processed_dir=seed,
        use_archive_seed=False,
    ).iloc[0]
    assert row["per90_goals"] == pytest.approx(1.44)


def test_eight_seed_fixtures_use_player_seed_not_position_price(tmp_path: Path) -> None:
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
            }
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
            }
        ]
    ).to_parquet(processed / "fixtures.parquet", index=False)
    pd.DataFrame(columns=["player_id", "gameweek_id", "minutes", "total_points"]).to_parquet(
        processed / "player_performances.parquet", index=False
    )
    seed = tmp_path / "archive" / "2024-25" / "processed"
    seed.mkdir(parents=True)
    pd.DataFrame(
        [
            {"id": 1, "code": 101, "position_id": 4, "now_cost": 90, "club_id": 1, "first_name": "A", "second_name": "One"},
            {"id": 3, "code": 103, "position_id": 4, "now_cost": 90, "club_id": 1, "first_name": "B", "second_name": "Two"},
        ]
    ).to_parquet(seed / "players.parquet", index=False)
    starter = {
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
    rows = [
        {"player_id": 1, "fixture_id": gw, "gameweek_id": gw, **starter}
        for gw in range(1, 9)
    ] + [
        {
            "player_id": 3,
            "fixture_id": 100 + gw,
            "gameweek_id": gw,
            **starter,
            "minutes": 0,
            "starts": 0,
        }
        for gw in range(1, 9)
    ]
    pd.DataFrame(rows).to_parquet(seed / "player_performances.parquet", index=False)
    row = build_features(
        processed,
        target_gw=1,
        seed_processed_dir=seed,
        use_archive_seed=False,
    ).iloc[0]
    assert row["p_start"] == pytest.approx(1.0)
    assert row["xmins_if_start"] == pytest.approx(90.0)
