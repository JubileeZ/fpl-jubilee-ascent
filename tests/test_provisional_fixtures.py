"""Tests for provisional fixture ingestion, completed Club Fixture definition, and actuals."""

from pathlib import Path
import json
import pandas as pd

from features.processor import process_directory
from features.builder import _completed_performance_rows
from commands.export_dashboard import _load_player_actuals


def test_fixtures_processor_retains_finished_provisional(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"
    raw_dir.mkdir(parents=True)
    processed_dir.mkdir(parents=True)

    bootstrap = {
        "events": [{"id": 1, "name": "GW 1", "finished": False, "is_current": True, "is_next": False}],
        "elements": [{"id": 10, "code": 1001, "team": 1, "element_type": 4, "now_cost": 100, "web_name": "Striker"}],
        "teams": [{"id": 1, "name": "Team A", "short_name": "TMA"}, {"id": 2, "name": "Team B", "short_name": "TMB"}],
    }
    with open(raw_dir / "bootstrap_static.json", "w") as f:
        json.dump(bootstrap, f)

    fixtures = [
        {
            "id": 1,
            "event": 1,
            "team_h": 1,
            "team_a": 2,
            "started": True,
            "finished_provisional": True,
            "finished": False,
            "minutes": 90,
            "team_h_score": 2,
            "team_a_score": 1,
        },
        {
            "id": 2,
            "event": 1,
            "team_h": 2,
            "team_a": 1,
            "started": False,
            "finished_provisional": False,
            "finished": False,
            "minutes": 0,
        },
    ]
    with open(raw_dir / "fixtures_all.json", "w") as f:
        json.dump(fixtures, f)

    process_directory(raw_dir, processed_dir)

    fix_path = processed_dir / "fixtures.parquet"
    assert fix_path.exists()
    df_fix = pd.read_parquet(fix_path)
    assert "finished_provisional" in df_fix.columns
    row1 = df_fix[df_fix["id"] == 1].iloc[0]
    assert bool(row1["finished"]) is False
    assert bool(row1["finished_provisional"]) is True
    row2 = df_fix[df_fix["id"] == 2].iloc[0]
    assert bool(row2["finished_provisional"]) is False


def test_completed_performance_rows_includes_provisional() -> None:
    df_fixtures = pd.DataFrame([
        {"id": 101, "gameweek_id": 1, "finished": True, "finished_provisional": True},
        {"id": 102, "gameweek_id": 2, "finished": False, "finished_provisional": True},
        {"id": 103, "gameweek_id": 2, "finished": False, "finished_provisional": False},
    ])

    df_perf = pd.DataFrame([
        {"player_id": 1, "fixture_id": 101, "gameweek_id": 1, "minutes": 90},
        {"player_id": 1, "fixture_id": 102, "gameweek_id": 2, "minutes": 90},
        {"player_id": 2, "fixture_id": 103, "gameweek_id": 2, "minutes": 0},
    ])

    completed = _completed_performance_rows(df_perf, df_fixtures)
    assert len(completed) == 2
    assert set(completed["fixture_id"]) == {101, 102}


def test_completed_performance_rows_backward_compatible_without_provisional_col() -> None:
    df_fixtures = pd.DataFrame([
        {"id": 101, "gameweek_id": 1, "finished": True},
        {"id": 102, "gameweek_id": 2, "finished": False},
    ])

    df_perf = pd.DataFrame([
        {"player_id": 1, "fixture_id": 101, "gameweek_id": 1, "minutes": 90},
        {"player_id": 1, "fixture_id": 102, "gameweek_id": 2, "minutes": 90},
    ])

    completed = _completed_performance_rows(df_perf, df_fixtures)
    assert len(completed) == 1
    assert completed.iloc[0]["fixture_id"] == 101


def test_load_player_actuals_includes_provisionally_finished_fixture(tmp_path: Path) -> None:
    processed_dir = tmp_path / "processed"
    processed_dir.mkdir(parents=True)

    df_fixtures = pd.DataFrame([
        {"id": 201, "gameweek_id": 1, "finished": True, "finished_provisional": True},
        {"id": 202, "gameweek_id": 2, "finished": False, "finished_provisional": True},
        {"id": 203, "gameweek_id": 2, "finished": False, "finished_provisional": False},
    ])
    df_fixtures.to_parquet(processed_dir / "fixtures.parquet")

    df_perf = pd.DataFrame([
        {
            "player_id": 10,
            "fixture_id": 201,
            "gameweek_id": 1,
            "minutes": 90,
            "starts": 1,
            "goals_scored": 1,
            "assists": 0,
            "clean_sheets": 0,
            "goals_conceded": 1,
            "saves": 0,
            "expected_goals": 0.8,
            "expected_assists": 0.1,
            "expected_goals_conceded": 1.2,
        },
        {
            "player_id": 10,
            "fixture_id": 202,
            "gameweek_id": 2,
            "minutes": 90,
            "starts": 1,
            "goals_scored": 2,
            "assists": 1,
            "clean_sheets": 1,
            "goals_conceded": 0,
            "saves": 0,
            "expected_goals": 1.4,
            "expected_assists": 0.4,
            "expected_goals_conceded": 0.3,
        },
        {
            "player_id": 20,
            "fixture_id": 203,
            "gameweek_id": 2,
            "minutes": 0,
            "starts": 0,
            "goals_scored": 0,
            "assists": 0,
            "clean_sheets": 0,
            "goals_conceded": 0,
            "saves": 0,
            "expected_goals": 0.0,
            "expected_assists": 0.0,
            "expected_goals_conceded": 0.0,
        },
    ])
    df_perf.to_parquet(processed_dir / "player_performances.parquet")

    finished_gws = {1}
    actuals = _load_player_actuals(processed_dir, finished_gws)

    assert 10 in actuals
    p10 = actuals[10]
    assert p10["apps"] == 2
    assert p10["starts"] == 2
    assert p10["minutes"] == 180
    assert p10["goals"] == 3
    assert p10["assists"] == 1
    assert p10["cs"] == 1

    assert actuals.get(20, {}).get("apps", 0) == 0


def test_load_player_actuals_filters_prior_club_fixtures(tmp_path: Path) -> None:
    processed_dir = tmp_path / "processed"
    processed_dir.mkdir(parents=True)

    df_fixtures = pd.DataFrame([
        {"id": 301, "gameweek_id": 1, "home_club_id": 1, "away_club_id": 2, "finished": True, "finished_provisional": True},
        {"id": 302, "gameweek_id": 2, "home_club_id": 3, "away_club_id": 4, "finished": True, "finished_provisional": True},
    ])
    df_fixtures.to_parquet(processed_dir / "fixtures.parquet")

    df_perf = pd.DataFrame([
        {"player_id": 5, "fixture_id": 301, "gameweek_id": 1, "was_home": True, "minutes": 90, "starts": 1, "goals_scored": 1, "assists": 0, "clean_sheets": 0, "goals_conceded": 0, "saves": 0, "expected_goals": 0.5, "expected_assists": 0.0, "expected_goals_conceded": 0.5},
        {"player_id": 5, "fixture_id": 302, "gameweek_id": 2, "was_home": True, "minutes": 90, "starts": 1, "goals_scored": 2, "assists": 0, "clean_sheets": 0, "goals_conceded": 0, "saves": 0, "expected_goals": 1.0, "expected_assists": 0.0, "expected_goals_conceded": 0.5},
    ])
    df_perf.to_parquet(processed_dir / "player_performances.parquet")

    actuals_club3 = _load_player_actuals(processed_dir, finished_gws={1, 2}, player_clubs={5: 3})
    assert 5 in actuals_club3
    assert actuals_club3[5]["apps"] == 1
    assert actuals_club3[5]["goals"] == 2


def test_player_history_excludes_unplayed_provisional_fixture(tmp_path: Path) -> None:
    from dashboard.planner_service import PlannerPaths, player_history

    processed_dir = tmp_path / "processed"
    processed_dir.mkdir(parents=True)

    df_fixtures = pd.DataFrame([
        {"id": 401, "gameweek_id": 1, "finished": True, "finished_provisional": True},
        {"id": 402, "gameweek_id": 2, "finished": False, "finished_provisional": False},
    ])
    df_fixtures.to_parquet(processed_dir / "fixtures.parquet")

    df_perf = pd.DataFrame([
        {"player_id": 7, "fixture_id": 401, "gameweek_id": 1, "minutes": 90, "total_points": 8},
        {"player_id": 7, "fixture_id": 402, "gameweek_id": 2, "minutes": 0, "total_points": 0},
    ])
    df_perf.to_parquet(processed_dir / "player_performances.parquet")

    paths = PlannerPaths(
        dataset=tmp_path / "dataset.json",
        processed=processed_dir,
        storage=tmp_path / "storage",
    )
    records = player_history(paths, 7)
    assert len(records) == 1
    assert records[0]["gameweek_id"] == 1
    assert records[0]["total_points"] == 8


def test_build_features_supports_immediate_next_gw(tmp_path: Path) -> None:
    from features.builder import build_features

    processed_dir = tmp_path / "processed"
    processed_dir.mkdir(parents=True)

    pd.DataFrame([
        {"id": 1, "code": 11, "first_name": "Test", "second_name": "Player", "club_id": 1, "position_id": 3, "now_cost": 80, "status": "i", "chance_of_playing_next_round": 0.0}
    ]).to_parquet(processed_dir / "players.parquet")

    pd.DataFrame([
        {"id": 1, "name": "Team A", "short_name": "TMA", "strength": 3}
    ]).to_parquet(processed_dir / "clubs.parquet")

    pd.DataFrame([
        {"id": 501, "gameweek_id": 7, "home_club_id": 1, "away_club_id": 1, "finished": False, "finished_provisional": False, "team_h_difficulty": 3, "team_a_difficulty": 3},
        {"id": 502, "gameweek_id": 8, "home_club_id": 1, "away_club_id": 1, "finished": False, "finished_provisional": False, "team_h_difficulty": 3, "team_a_difficulty": 3},
    ]).to_parquet(processed_dir / "fixtures.parquet")

    pd.DataFrame(columns=["player_id", "fixture_id", "gameweek_id", "total_points", "minutes"]).to_parquet(
        processed_dir / "player_performances.parquet"
    )

    df_feat = build_features(
        processed_dir=processed_dir,
        target_gw=7,
        horizon=2,
        immediate_next_gw=8,
        use_archive_seed=False,
    )

    row_gw7 = df_feat[df_feat["gameweek_id"] == 7].iloc[0]
    row_gw8 = df_feat[df_feat["gameweek_id"] == 8].iloc[0]

    assert bool(row_gw7["is_immediate_next_gw"]) is False
    assert bool(row_gw8["is_immediate_next_gw"]) is True

