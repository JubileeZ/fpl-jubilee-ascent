from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

from features.availability_snapshots import write_availability_snapshot
from features.builder import build_features, history_before_target


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
            "kickoff_time": "2026-07-25T12:00:00Z",
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


def test_feature_contract_does_not_trust_legacy_gameweek_labelled_snapshot(tmp_path):
    processed = _write_fixture_data(tmp_path)
    pd.DataFrame([
        {"player_id": 1, "snapshot_gameweek_id": 2, "chance_of_playing_next_round": 50.0},
    ]).to_parquet(processed / "player_snapshots.parquet", index=False)

    features = build_features(processed, target_gw=2, as_of_gw=2)

    assert features["chance_of_playing"].eq(100.0).all()


def _write_verified_snapshot(processed: Path, root: Path) -> datetime:
    deadline = datetime(2026, 8, 1, 12, tzinfo=UTC)
    package = write_availability_snapshot(
        root,
        "2026-27",
        2,
        deadline,
        deadline - timedelta(hours=1),
        pd.read_parquet(processed / "players.parquet"),
        pd.read_parquet(processed / "clubs.parquet"),
        pd.read_parquet(processed / "fixtures.parquet"),
    )
    assert package is not None
    return deadline


def test_point_in_time_features_require_verified_complete_snapshot(tmp_path):
    processed = _write_fixture_data(tmp_path)
    deadline = _write_verified_snapshot(processed, tmp_path / "snapshots")

    features = build_features(
        processed,
        target_gw=2,
        as_of_gw=2,
        availability_snapshot_root=tmp_path / "snapshots",
        season="2026-27",
        target_deadline=deadline,
        require_availability_snapshot=True,
    )

    assert features["has_availability_snapshot"].all()
    assert features["availability_snapshot_id"].notna().all()
    assert features["chance_of_playing"].eq(0.0).all()


def test_point_in_time_features_ignore_mutated_terminal_metadata(tmp_path):
    processed = _write_fixture_data(tmp_path)
    snapshot_root = tmp_path / "snapshots"
    deadline = _write_verified_snapshot(processed, snapshot_root)
    kwargs = {
        "target_gw": 2,
        "as_of_gw": 2,
        "availability_snapshot_root": snapshot_root,
        "season": "2026-27",
        "target_deadline": deadline,
        "require_availability_snapshot": True,
    }
    expected = build_features(processed, **kwargs)

    pd.DataFrame([
        {"id": 1, "club_id": 3, "position_id": 1, "now_cost": 1, "status": "u"},
    ]).to_parquet(processed / "players.parquet", index=False)
    pd.DataFrame([
        {"id": 1, "strength": 1},
        {"id": 2, "strength": 1},
        {"id": 3, "strength": 99},
    ]).to_parquet(processed / "clubs.parquet", index=False)
    pd.DataFrame([
        {"id": 99, "gameweek_id": 2, "home_club_id": 3, "away_club_id": 2, "team_h_difficulty": 5, "team_a_difficulty": 1},
    ]).to_parquet(processed / "fixtures.parquet", index=False)
    actual = build_features(processed, **kwargs)

    pd.testing.assert_frame_equal(expected, actual)


def test_point_in_time_features_reject_missing_snapshot(tmp_path):
    with pytest.raises(ValueError, match="Missing immutable availability snapshot"):
        build_features(
            _write_fixture_data(tmp_path),
            target_gw=2,
            as_of_gw=2,
            availability_snapshot_root=tmp_path / "snapshots",
            season="2026-27",
            target_deadline=datetime(2026, 8, 1, 12, tzinfo=UTC),
            require_availability_snapshot=True,
        )


def test_history_excludes_delayed_fixture_after_target_deadline(tmp_path):
    processed = _write_fixture_data(tmp_path)
    deadline = _write_verified_snapshot(processed, tmp_path / "snapshots")
    delayed = pd.read_parquet(processed / "player_performances.parquet").assign(
        kickoff_time="2026-08-02T12:00:00Z",
    )
    delayed.to_parquet(processed / "player_performances.parquet", index=False)

    features = build_features(
        processed,
        target_gw=2,
        as_of_gw=2,
        availability_snapshot_root=tmp_path / "snapshots",
        season="2026-27",
        target_deadline=deadline,
        require_availability_snapshot=True,
    )

    assert features["avg_points_3gw"].eq(0.0).all()


def test_point_in_time_features_reject_history_without_kickoff_time(tmp_path):
    processed = _write_fixture_data(tmp_path)
    deadline = _write_verified_snapshot(processed, tmp_path / "snapshots")
    performances = pd.read_parquet(processed / "player_performances.parquet").drop(columns="kickoff_time")
    performances.to_parquet(processed / "player_performances.parquet", index=False)

    with pytest.raises(ValueError, match="requires kickoff_time"):
        build_features(
            processed,
            target_gw=2,
            as_of_gw=2,
            availability_snapshot_root=tmp_path / "snapshots",
            season="2026-27",
            target_deadline=deadline,
            require_availability_snapshot=True,
        )


def test_history_filter_excludes_delayed_rows_for_model_fit():
    history = pd.DataFrame([
        {"gameweek_id": 1, "kickoff_time": "2026-08-01T11:00:00Z"},
        {"gameweek_id": 1, "kickoff_time": "2026-08-01T13:00:00Z"},
        {"gameweek_id": 2, "kickoff_time": "2026-08-01T10:00:00Z"},
    ])

    filtered = history_before_target(
        history,
        target_gw=2,
        target_deadline="2026-08-01T12:00:00Z",
        require_kickoff_time=True,
    )

    assert len(filtered) == 1
    assert filtered.iloc[0]["kickoff_time"] == "2026-08-01T11:00:00Z"
