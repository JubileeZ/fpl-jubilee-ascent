from pathlib import Path

import pandas as pd
import pytest

from features.builder import build_features
from tests.expected_role_fixtures import role_kwargs, write_role_table


def _write_processed(tmp_path: Path) -> Path:
    processed = tmp_path / "processed"
    processed.mkdir()
    pd.DataFrame([
        {
            "id": 1,
            "club_id": 1,
            "position_id": 2,
            "now_cost": 60,
            "chance_of_playing_next_round": 100.0,
        },
    ]).to_parquet(processed / "players.parquet", index=False)
    pd.DataFrame([
        {"id": 1, "name": "Club A", "short_name": "A", "strength": 3},
        {"id": 2, "name": "Club B", "short_name": "B", "strength": 3},
        {"id": 3, "name": "Club C", "short_name": "C", "strength": 3},
    ]).to_parquet(processed / "clubs.parquet", index=False)
    pd.DataFrame([
        {"id": 101, "gameweek_id": 1, "home_club_id": 1, "away_club_id": 2, "team_h_difficulty": 3, "team_a_difficulty": 3},
        {"id": 102, "gameweek_id": 2, "home_club_id": 2, "away_club_id": 1, "team_h_difficulty": 3, "team_a_difficulty": 3},
        {"id": 103, "gameweek_id": 3, "home_club_id": 2, "away_club_id": 3, "team_h_difficulty": 3, "team_a_difficulty": 3},
        {"id": 104, "gameweek_id": 4, "home_club_id": 1, "away_club_id": 3, "team_h_difficulty": 3, "team_a_difficulty": 3},
        {"id": 105, "gameweek_id": 5, "home_club_id": 1, "away_club_id": 2, "team_h_difficulty": 3, "team_a_difficulty": 3},
    ]).to_parquet(processed / "fixtures.parquet", index=False)
    pd.DataFrame([
        {"player_id": 1, "fixture_id": 101, "gameweek_id": 1, "was_home": True, "minutes": 90, "starts": 1, "total_points": 6},
        {"player_id": 1, "fixture_id": 102, "gameweek_id": 2, "was_home": False, "minutes": 20, "starts": 0, "total_points": 1},
        {"player_id": 1, "fixture_id": 103, "gameweek_id": 3, "was_home": True, "minutes": 90, "starts": 1, "total_points": 6},
        {"player_id": 1, "fixture_id": 104, "gameweek_id": 4, "was_home": True, "minutes": 0, "starts": 0, "total_points": 0},
    ]).to_parquet(processed / "player_performances.parquet", index=False)
    return processed


def test_participation_features_use_current_club_fixture_tenure(tmp_path):
    processed = _write_processed(tmp_path)
    table = write_role_table(tmp_path / "roles.csv", [1])
    features = build_features(
        processed,
        target_gw=5,
        use_archive_seed=False,
        blend_start_appearances=0,
        blend_full_appearances=1,
        **role_kwargs(table),
    )
    player = features.iloc[0]

    assert player["state_observation_weight"] == pytest.approx(1.0 + 0.95**2 + 0.95**3)
    assert player["xmins_if_start"] == pytest.approx(90.0)
    assert player["xmins_if_sub_in"] == pytest.approx(20.0)
    assert player["p_60_if_start"] == pytest.approx(1.0)
    assert player["p_60_if_sub_in"] == pytest.approx(0.0)
    assert player["p_dnp"] + player["p_start"] + player["p_sub_in"] == pytest.approx(1.0)


def test_state_recency_parameter_increases_weight_of_older_current_club_starts(tmp_path):
    processed = _write_processed(tmp_path)
    table = write_role_table(tmp_path / "roles.csv", [1])
    lower_decay = build_features(
        processed,
        target_gw=5,
        use_archive_seed=False,
        state_recency_decay=0.85,
        blend_start_appearances=0,
        blend_full_appearances=1,
        **role_kwargs(table),
    ).iloc[0]
    selected_decay = build_features(
        processed,
        target_gw=5,
        use_archive_seed=False,
        state_recency_decay=0.95,
        blend_start_appearances=0,
        blend_full_appearances=1,
        **role_kwargs(table),
    ).iloc[0]

    assert selected_decay["state_observation_weight"] > lower_decay["state_observation_weight"]
    assert selected_decay["p_start"] > lower_decay["p_start"]


@pytest.mark.parametrize(
    ("state_recency_decay", "state_prior_strength", "message"),
    [
        (0.0, 4.0, "state_recency_decay"),
        (1.01, 4.0, "state_recency_decay"),
        (0.95, -1.0, "state_prior_strength"),
    ],
)
def test_state_feature_parameters_are_validated(
    tmp_path,
    state_recency_decay,
    state_prior_strength,
    message,
):
    with pytest.raises(ValueError, match=message):
        build_features(
            _write_processed(tmp_path),
            target_gw=5,
            use_archive_seed=False,
            state_recency_decay=state_recency_decay,
            state_prior_strength=state_prior_strength,
            **role_kwargs(write_role_table(tmp_path / "roles.csv", [1])),
        )
