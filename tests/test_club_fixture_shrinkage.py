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


def test_this_season_evidence_ignores_prior_season_player_event_rates(tmp_path: Path) -> None:
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
    assert row["per90_goals"] == pytest.approx(0.0)
    assert row["seed_source"] == "position_price_prior"
    assert bool(row["has_prior_seed"]) is False


def test_global_this_season_evidence_drops_other_players_last_season_minutes(tmp_path: Path) -> None:
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
                "chance_of_playing_next_round": 100.0,
            },
            {
                "id": 2,
                "code": 102,
                "club_id": 1,
                "position_id": 4,
                "now_cost": 90,
                "first_name": "B",
                "second_name": "Two",
                "chance_of_playing_next_round": 100.0,
            },
        ]
    ).to_parquet(processed / "players.parquet", index=False)
    pd.DataFrame([{"id": 1, "name": "A", "short_name": "A", "strength": 3}]).to_parquet(
        processed / "clubs.parquet", index=False
    )
    pd.DataFrame(
        [
            {
                "id": 101,
                "gameweek_id": 1,
                "home_club_id": 1,
                "away_club_id": 2,
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
    pd.DataFrame(
        [
            {
                "id": 1,
                "code": 101,
                "position_id": 4,
                "now_cost": 90,
                "club_id": 1,
                "first_name": "A",
                "second_name": "One",
            },
            {
                "id": 2,
                "code": 102,
                "position_id": 4,
                "now_cost": 90,
                "club_id": 1,
                "first_name": "B",
                "second_name": "Two",
            },
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
    pd.DataFrame(
        [
            {"player_id": pid, "fixture_id": gw, "gameweek_id": gw, **starter}
            for pid in (1, 2)
            for gw in range(1, 9)
        ]
    ).to_parquet(seed / "player_performances.parquet", index=False)
    row = build_features(
        processed,
        target_gw=2,
        seed_processed_dir=seed,
        use_archive_seed=False,
    )
    unused = row[row["player_id"] == 2].iloc[0]
    assert unused["p_dnp"] == pytest.approx(1.0)
    assert bool(unused["has_prior_seed"]) is False


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


def _write_finished_minutes_tables(
    processed: Path,
    *,
    fixtures: list[dict[str, object]],
    performances: list[dict[str, object]],
) -> None:
    pd.DataFrame(
        [
            {
                "id": 1,
                "club_id": 1,
                "position_id": 4,
                "now_cost": 77,
                "chance_of_playing_next_round": 100.0,
            }
        ]
    ).to_parquet(processed / "players.parquet", index=False)
    pd.DataFrame([{"id": 1, "name": "A", "short_name": "A", "strength": 3}]).to_parquet(
        processed / "clubs.parquet", index=False
    )
    pd.DataFrame(fixtures).to_parquet(processed / "fixtures.parquet", index=False)
    pd.DataFrame(performances).to_parquet(processed / "player_performances.parquet", index=False)


def test_unfinished_zero_minutes_are_not_recorded_dnp(tmp_path: Path) -> None:
    processed = tmp_path / "processed"
    processed.mkdir()
    _write_finished_minutes_tables(
        processed,
        fixtures=[
            {
                "id": 101,
                "gameweek_id": 1,
                "home_club_id": 1,
                "away_club_id": 2,
                "team_h_difficulty": 3,
                "team_a_difficulty": 3,
                "finished": True,
            },
            {
                "id": 102,
                "gameweek_id": 2,
                "home_club_id": 1,
                "away_club_id": 2,
                "team_h_difficulty": 3,
                "team_a_difficulty": 3,
                "finished": True,
            },
            {
                "id": 103,
                "gameweek_id": 3,
                "home_club_id": 1,
                "away_club_id": 2,
                "team_h_difficulty": 3,
                "team_a_difficulty": 3,
                "finished": False,
            },
        ],
        performances=[
            {
                "player_id": 1,
                "fixture_id": 101,
                "gameweek_id": 1,
                "was_home": True,
                "minutes": 90,
                "starts": 1,
                "total_points": 2,
            },
            {
                "player_id": 1,
                "fixture_id": 102,
                "gameweek_id": 2,
                "was_home": True,
                "minutes": 90,
                "starts": 1,
                "total_points": 2,
            },
            {
                "player_id": 1,
                "fixture_id": 103,
                "gameweek_id": 3,
                "was_home": True,
                "minutes": 0,
                "starts": 0,
                "total_points": 0,
            },
        ],
    )
    row = build_features(processed, target_gw=4, use_archive_seed=False).iloc[0]
    assert row["dnp_observation_weight"] == pytest.approx(0.0)
    assert row["start_observation_weight"] == pytest.approx(1.95)
    assert row["p_start"] == pytest.approx(1.0)


def test_unfinished_only_history_is_not_this_season_evidence(tmp_path: Path) -> None:
    processed = tmp_path / "processed"
    processed.mkdir()
    _write_finished_minutes_tables(
        processed,
        fixtures=[
            {
                "id": 101,
                "gameweek_id": 1,
                "home_club_id": 1,
                "away_club_id": 2,
                "team_h_difficulty": 3,
                "team_a_difficulty": 3,
                "finished": False,
            }
        ],
        performances=[
            {
                "player_id": 1,
                "fixture_id": 101,
                "gameweek_id": 1,
                "was_home": True,
                "minutes": 0,
                "starts": 0,
                "total_points": 0,
            }
        ],
    )
    row = build_features(processed, target_gw=2, use_archive_seed=False).iloc[0]
    assert row["state_observation_weight"] == pytest.approx(0.0)
    assert row["p_start"] == pytest.approx(1.0 / 3.0)
    assert row["p_dnp"] == pytest.approx(1.0 / 3.0)


def test_full_season_window_uses_finished_starts_before_gw1_target(tmp_path: Path) -> None:
    processed = tmp_path / "processed"
    processed.mkdir()
    _write_finished_minutes_tables(
        processed,
        fixtures=[
            {
                "id": 101,
                "gameweek_id": 1,
                "home_club_id": 1,
                "away_club_id": 2,
                "team_h_difficulty": 3,
                "team_a_difficulty": 3,
                "finished": True,
            },
            {
                "id": 102,
                "gameweek_id": 2,
                "home_club_id": 1,
                "away_club_id": 2,
                "team_h_difficulty": 3,
                "team_a_difficulty": 3,
                "finished": True,
            },
        ],
        performances=[
            {
                "player_id": 1,
                "fixture_id": 101,
                "gameweek_id": 1,
                "was_home": True,
                "minutes": 90,
                "starts": 1,
                "total_points": 2,
            },
            {
                "player_id": 1,
                "fixture_id": 102,
                "gameweek_id": 2,
                "was_home": True,
                "minutes": 90,
                "starts": 1,
                "total_points": 2,
            },
        ],
    )
    row = build_features(
        processed,
        target_gw=1,
        horizon=38,
        use_archive_seed=False,
        history_before_gw=39,
    ).iloc[0]
    assert row["start_observation_weight"] == pytest.approx(1.95)
    assert row["p_start"] == pytest.approx(1.0)


def _write_seed_season(root: Path, season: str, minutes: int, starts: int) -> None:
    seed = root / "archive" / season / "processed"
    seed.mkdir(parents=True)
    pd.DataFrame(
        [{"id": 1, "code": 101, "position_id": 4, "now_cost": 77, "club_id": 1, "first_name": "A", "second_name": "One"}]
    ).to_parquet(seed / "players.parquet", index=False)
    starter = {
        "minutes": minutes,
        "starts": starts,
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
    pd.DataFrame(
        [{"player_id": 1, "fixture_id": gw, "gameweek_id": gw, **starter} for gw in range(1, 9)]
    ).to_parquet(seed / "player_performances.parquet", index=False)


def test_prior_season_seed_skips_live_season_archive(tmp_path: Path) -> None:
    processed = tmp_path / "processed"
    processed.mkdir()
    pd.DataFrame(
        [
            {
                "id": 1,
                "code": 101,
                "club_id": 1,
                "position_id": 4,
                "now_cost": 77,
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
    _write_seed_season(tmp_path, "2025-26", minutes=90, starts=1)
    _write_seed_season(tmp_path, "2026-27", minutes=0, starts=0)
    row = build_features(processed, target_gw=1).iloc[0]
    assert row["p_start"] == pytest.approx(1.0)
    assert row["seed_source"] == "player_prior"


def test_prior_season_seed_from_archive_season_processed_dir(tmp_path: Path) -> None:
    processed = tmp_path / "archive" / "2026-27" / "processed"
    processed.mkdir(parents=True)
    pd.DataFrame(
        [
            {
                "id": 1,
                "code": 101,
                "club_id": 1,
                "position_id": 4,
                "now_cost": 77,
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
    _write_seed_season(tmp_path, "2025-26", minutes=90, starts=1)
    row = build_features(processed, target_gw=1).iloc[0]
    assert row["p_start"] == pytest.approx(1.0)
    assert row["seed_source"] == "player_prior"


def test_two_finished_starts_use_strength_one_state_prior(tmp_path: Path) -> None:
    processed = tmp_path / "processed"
    processed.mkdir()
    pd.DataFrame(
        [
            {
                "id": 1,
                "club_id": 1,
                "position_id": 4,
                "now_cost": 77,
                "chance_of_playing_next_round": 100.0,
            },
            {
                "id": 2,
                "club_id": 1,
                "position_id": 4,
                "now_cost": 77,
                "chance_of_playing_next_round": 100.0,
            },
        ]
    ).to_parquet(processed / "players.parquet", index=False)
    pd.DataFrame([{"id": 1, "name": "A", "short_name": "A", "strength": 3}]).to_parquet(
        processed / "clubs.parquet", index=False
    )
    pd.DataFrame(
        [
            {
                "id": 101,
                "gameweek_id": 1,
                "home_club_id": 1,
                "away_club_id": 2,
                "team_h_difficulty": 3,
                "team_a_difficulty": 3,
                "finished": True,
            },
            {
                "id": 102,
                "gameweek_id": 2,
                "home_club_id": 1,
                "away_club_id": 2,
                "team_h_difficulty": 3,
                "team_a_difficulty": 3,
                "finished": True,
            },
            {
                "id": 103,
                "gameweek_id": 3,
                "home_club_id": 1,
                "away_club_id": 2,
                "team_h_difficulty": 3,
                "team_a_difficulty": 3,
                "finished": False,
            },
        ]
    ).to_parquet(processed / "fixtures.parquet", index=False)
    pd.DataFrame(
        [
            {
                "player_id": 1,
                "fixture_id": fid,
                "gameweek_id": gw,
                "was_home": True,
                "minutes": 90,
                "starts": 1,
                "total_points": 2,
            }
            for gw, fid in ((1, 101), (2, 102))
        ]
        + [
            {
                "player_id": 2,
                "fixture_id": fid,
                "gameweek_id": gw,
                "was_home": True,
                "minutes": 0,
                "starts": 0,
                "total_points": 0,
            }
            for gw, fid in ((1, 101), (2, 102))
        ]
        + [
            {
                "player_id": 1,
                "fixture_id": 103,
                "gameweek_id": 3,
                "was_home": True,
                "minutes": 0,
                "starts": 0,
                "total_points": 0,
            }
        ]
    ).to_parquet(processed / "player_performances.parquet", index=False)
    row = build_features(processed, target_gw=4, use_archive_seed=False)
    starter = row[row["player_id"] == 1].iloc[0]
    assert starter["dnp_observation_weight"] == pytest.approx(0.0)
    assert starter["p_start"] == pytest.approx(0.8305, abs=0.001)
