"""Trailing Start Window blends window posterior into Participation State."""

from pathlib import Path

import pandas as pd
import pytest

from features.builder import (
    _blend_state_summaries,
    _trailing_start_count,
    _trailing_start_window_rows,
    build_features,
)


def _club_rows(states: list[tuple[int, float, float]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"gameweek_id": gw, "minutes": minutes, "starts": starts}
            for gw, minutes, starts in states
        ]
    )


def test_trailing_start_count_breaks_on_sub_in() -> None:
    rows = _club_rows([(1, 0.0, 0.0), (2, 11.0, 0.0), (3, 90.0, 1.0), (4, 90.0, 1.0), (5, 90.0, 1.0)])
    assert _trailing_start_count(rows) == 3
    broken = _club_rows([(1, 90.0, 1.0), (2, 90.0, 1.0), (3, 90.0, 1.0), (4, 20.0, 0.0)])
    assert _trailing_start_count(broken) == 0


def test_trailing_start_window_rows_take_last_k_starts() -> None:
    rows = _club_rows([(1, 0.0, 0.0), (2, 11.0, 0.0), (3, 90.0, 1.0), (4, 90.0, 1.0), (5, 90.0, 1.0)])
    window = _trailing_start_window_rows(rows, 3)
    assert list(window["gameweek_id"]) == [3, 4, 5]
    assert _trailing_start_window_rows(rows, 4).empty


def test_blend_state_summaries_renormalizes_and_weights() -> None:
    window = {
        "p_dnp": 0.05,
        "p_start": 0.9,
        "p_sub_in": 0.05,
        "xmins_if_start": 90.0,
        "xmins_if_sub_in": 15.0,
        "p_60_if_start": 1.0,
        "p_60_if_sub_in": 0.0,
    }
    full = {
        "p_dnp": 0.25,
        "p_start": 0.55,
        "p_sub_in": 0.2,
        "xmins_if_start": 80.0,
        "xmins_if_sub_in": 12.0,
        "p_60_if_start": 0.9,
        "p_60_if_sub_in": 0.1,
        "state_observation_weight": 4.0,
    }
    blended = _blend_state_summaries(window, full, 0.9)
    assert blended["p_dnp"] + blended["p_start"] + blended["p_sub_in"] == pytest.approx(1.0)
    assert blended["p_start"] == pytest.approx(0.9 * 0.9 + 0.1 * 0.55)
    assert blended["xmins_if_start"] == pytest.approx(0.9 * 90.0 + 0.1 * 80.0)
    assert blended["trailing_start_window_active"] == 1.0


def _write_min_processed(path: Path) -> None:
    path.mkdir(parents=True)
    pd.DataFrame(
        [
            {
                "id": 1,
                "code": 100,
                "first_name": "A",
                "second_name": "Nail",
                "web_name": "Nail",
                "club_id": 1,
                "position_id": 2,
                "now_cost": 45,
                "status": "a",
                "chance_of_playing_next_round": None,
                "chance_of_playing_this_round": None,
                "news": "",
                "news_added": None,
                "selected_by_percent": 1.0,
            }
        ]
    ).to_parquet(path / "players.parquet")
    pd.DataFrame([{"id": 1, "name": "Club", "short_name": "CLB", "strength": 3}]).to_parquet(
        path / "clubs.parquet"
    )
    fixtures = []
    for gw in range(1, 6):
        fixtures.append(
            {
                "id": gw,
                "gameweek_id": gw,
                "home_club_id": 1,
                "away_club_id": 2,
                "team_h_difficulty": 3,
                "team_a_difficulty": 3,
                "finished": True,
                "kickoff_time": f"2025-08-{gw:02d}T14:00:00Z",
            }
        )
    fixtures.append(
        {
            "id": 6,
            "gameweek_id": 6,
            "home_club_id": 1,
            "away_club_id": 2,
            "team_h_difficulty": 3,
            "team_a_difficulty": 3,
            "finished": False,
            "kickoff_time": "2025-09-01T14:00:00Z",
        }
    )
    pd.DataFrame(fixtures).to_parquet(path / "fixtures.parquet")
    # GW1 DNP, GW2 sub, GW3-5 starts — Konsa-shaped tenure.
    rows = [
        {"player_id": 1, "fixture_id": 1, "gameweek_id": 1, "minutes": 0, "starts": 0, "was_home": True, "total_points": 0},
        {"player_id": 1, "fixture_id": 2, "gameweek_id": 2, "minutes": 11, "starts": 0, "was_home": True, "total_points": 1},
        {"player_id": 1, "fixture_id": 3, "gameweek_id": 3, "minutes": 90, "starts": 1, "was_home": True, "total_points": 6},
        {"player_id": 1, "fixture_id": 4, "gameweek_id": 4, "minutes": 90, "starts": 1, "was_home": True, "total_points": 6},
        {"player_id": 1, "fixture_id": 5, "gameweek_id": 5, "minutes": 90, "starts": 1, "was_home": True, "total_points": 6},
    ]
    for col in (
        "goals_scored", "assists", "clean_sheets", "goals_conceded", "own_goals",
        "penalties_saved", "penalties_missed", "yellow_cards", "red_cards", "saves",
        "bonus", "defensive_contribution", "expected_goals", "expected_assists",
        "threat", "creativity",
    ):
        for row in rows:
            row[col] = 0
    pd.DataFrame(rows).to_parquet(path / "player_performances.parquet")
    pd.DataFrame([{"id": gw, "deadline_time": f"2025-08-{gw:02d}T10:00:00Z"} for gw in range(1, 7)]).to_parquet(
        path / "gameweeks.parquet"
    )


def test_trailing_start_window_lifts_konsa_shaped_xmins(tmp_path: Path) -> None:
    processed = tmp_path / "processed"
    _write_min_processed(processed)
    baseline = build_features(
        processed,
        target_gw=6,
        horizon=1,
        use_archive_seed=False,
        history_before_gw=6,
        trailing_start_k=0,
    ).iloc[0]
    windowed = build_features(
        processed,
        target_gw=6,
        horizon=1,
        use_archive_seed=False,
        history_before_gw=6,
        trailing_start_k=3,
        trailing_start_weight=0.9,
    ).iloc[0]
    baseline_xmins = (
        float(baseline["p_start"]) * float(baseline["xmins_if_start"])
        + float(baseline["p_sub_in"]) * float(baseline["xmins_if_sub_in"])
    )
    window_xmins = (
        float(windowed["p_start"]) * float(windowed["xmins_if_start"])
        + float(windowed["p_sub_in"]) * float(windowed["xmins_if_sub_in"])
    )
    assert window_xmins > baseline_xmins + 10.0
    assert window_xmins >= 70.0
