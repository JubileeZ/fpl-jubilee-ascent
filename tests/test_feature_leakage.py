from pathlib import Path

import pandas as pd

from features.builder import TERMINAL_PLAYER_COLUMNS
from tests.test_fixture_contract import _build, _write_fixture_data


def _with_gw1_history(root: Path) -> Path:
    processed = _write_fixture_data(root)
    fixtures = pd.read_parquet(processed / "fixtures.parquet")
    gw1 = {"id": 5, "gameweek_id": 1, "home_club_id": 1, "away_club_id": 2, "team_h_difficulty": 3, "team_a_difficulty": 3}
    pd.concat([pd.DataFrame([gw1]), fixtures]).assign(finished=lambda f: f["gameweek_id"].le(2)).to_parquet(
        processed / "fixtures.parquet", index=False
    )
    perf = pd.read_parquet(processed / "player_performances.parquet").assign(fixture_id=5, was_home=True, price=85)
    perf.to_parquet(processed / "player_performances.parquet", index=False)
    return processed


def test_as_of_features_without_snapshot_ignore_terminal_player_metadata(tmp_path: Path) -> None:
    processed = _with_gw1_history(tmp_path)
    expected = _build(processed, target_gw=2, as_of_gw=2)
    players = pd.read_parquet(processed / "players.parquet").assign(
        now_cost=140, club_id=3, status="i", penalties_order=1, total_points=250, goals_scored=30,
        expected_goals=25.0, selected_by_percent=60.0, chance_of_playing_next_round=0.0,
    )
    players.to_parquet(processed / "players.parquet", index=False)

    actual = _build(processed, target_gw=2, as_of_gw=2)

    pd.testing.assert_frame_equal(expected, actual)
    assert actual["now_cost"].eq(85).all()
    assert actual["club_id"].eq(1).all()
    assert not set(TERMINAL_PLAYER_COLUMNS) & set(actual.columns)


def test_as_of_features_exclude_target_gameweek_rows_without_deadline(tmp_path: Path) -> None:
    processed = _with_gw1_history(tmp_path)
    perf = pd.read_parquet(processed / "player_performances.parquet")
    future = perf.assign(gameweek_id=2, fixture_id=10, total_points=20, kickoff_time="2026-08-02T12:00:00Z")
    pd.concat([perf, future]).to_parquet(processed / "player_performances.parquet", index=False)

    features = _build(processed, target_gw=2, as_of_gw=2)

    assert features["avg_points_3gw"].eq(5.0).all()
