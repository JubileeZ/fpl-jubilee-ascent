"""Matchup share overlay: this-season club xG history bumps Feature Contract rates."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from features.builder import build_features
from features.matchup_share import apply_matchup_share_overlay
from tests.expected_role_fixtures import role_kwargs, write_role_table


def _base_feat(**overrides: object) -> pd.DataFrame:
    row = {
        "player_id": 1,
        "club_id": 10,
        "opponent_id": 20,
        "is_home": True,
        "gameweek_id": 3,
        "fixture_id": 100,
        "per90_xg": 0.50,
        "per90_xa": 0.20,
        "per90_goals_conceded": 1.20,
        "per90_saves": 3.0,
        "per90_defensive_contribution": 8.0,
        "penalties_order": 0.0,
        "attack_multiplier": 1.5,
        "defence_multiplier": 1.4,
    }
    row.update(overrides)
    return pd.DataFrame([row])


def test_empty_history_leaves_rates_and_multipliers() -> None:
    feat = _base_feat()
    hist = pd.DataFrame(
        columns=[
            "player_id",
            "club_id",
            "fixture_id",
            "gameweek_id",
            "was_home",
            "minutes",
            "expected_goals",
            "expected_assists",
            "expected_goals_conceded",
        ]
    )
    fixtures = pd.DataFrame(
        columns=["id", "home_club_id", "away_club_id", "gameweek_id"]
    )
    out, applied = apply_matchup_share_overlay(feat, hist, fixtures, history_cutoff_gw=3)
    assert applied is False
    assert out.loc[0, "per90_xg"] == 0.50
    assert out.loc[0, "attack_multiplier"] == 1.5


def test_build_features_no_xg_history_keeps_club_strength_multipliers(
    tmp_path: Path,
) -> None:
    """No this-season xG → Matchup off → Club Strength multipliers."""
    processed = tmp_path / "processed"
    processed.mkdir()
    pd.DataFrame(
        [
            {
                "id": 1,
                "club_id": 1,
                "position_id": 4,
                "now_cost": 90,
                "chance_of_playing_next_round": 100.0,
            }
        ]
    ).to_parquet(processed / "players.parquet", index=False)
    pd.DataFrame(
        [
            {
                "id": 1,
                "name": "A",
                "short_name": "A",
                "strength": 3,
                "strength_attack_home": 1400,
                "strength_defence_home": 1200,
            },
            {
                "id": 2,
                "name": "B",
                "short_name": "B",
                "strength": 3,
                "strength_attack_away": 900,
                "strength_defence_away": 1100,
            },
        ]
    ).to_parquet(processed / "clubs.parquet", index=False)
    pd.DataFrame(
        [
            {
                "id": 10,
                "gameweek_id": 1,
                "home_club_id": 1,
                "away_club_id": 2,
                "team_h_difficulty": 2,
                "team_a_difficulty": 4,
                "finished": True,
            },
            {
                "id": 11,
                "gameweek_id": 2,
                "home_club_id": 1,
                "away_club_id": 2,
                "team_h_difficulty": 2,
                "team_a_difficulty": 4,
                "finished": False,
            },
        ]
    ).to_parquet(processed / "fixtures.parquet", index=False)
    pd.DataFrame(
        [
            {
                "player_id": 1,
                "gameweek_id": 1,
                "fixture_id": 10,
                "kickoff_time": "2026-08-01T12:00:00Z",
                "minutes": 90,
                "total_points": 5,
                "goals_scored": 1,
                "assists": 0,
                "was_home": True,
            }
        ]
    ).to_parquet(processed / "player_performances.parquet", index=False)
    table = write_role_table(tmp_path / "roles.csv", [1])
    feat = build_features(
        processed, target_gw=2, horizon=1, use_archive_seed=False, **role_kwargs(table)
    )
    row = feat[(feat["player_id"] == 1) & (feat["fixture_id"] == 11)].iloc[0]
    assert abs(float(row["attack_multiplier"]) - min(max(1400 / 1100, 0.4), 1.8)) < 1e-9
    assert abs(float(row["defence_multiplier"]) - min(max(900 / 1200, 0.4), 1.8)) < 1e-9


def test_build_features_with_xg_history_forces_neutral_multipliers(tmp_path: Path) -> None:
    """This-season Official xG history → Matchup on → multipliers ×1.0."""
    processed = tmp_path / "processed"
    processed.mkdir()
    pd.DataFrame(
        [
            {
                "id": 1,
                "club_id": 1,
                "position_id": 4,
                "now_cost": 90,
                "chance_of_playing_next_round": 100.0,
                "penalties_order": 0,
            }
        ]
    ).to_parquet(processed / "players.parquet", index=False)
    pd.DataFrame(
        [
            {
                "id": 1,
                "name": "A",
                "short_name": "A",
                "strength": 3,
                "strength_attack_home": 1400,
                "strength_defence_home": 1200,
            },
            {
                "id": 2,
                "name": "B",
                "short_name": "B",
                "strength": 3,
                "strength_attack_away": 900,
                "strength_defence_away": 1100,
            },
        ]
    ).to_parquet(processed / "clubs.parquet", index=False)
    pd.DataFrame(
        [
            {
                "id": 10,
                "gameweek_id": 1,
                "home_club_id": 1,
                "away_club_id": 2,
                "team_h_difficulty": 2,
                "team_a_difficulty": 4,
                "finished": True,
            },
            {
                "id": 11,
                "gameweek_id": 2,
                "home_club_id": 1,
                "away_club_id": 2,
                "team_h_difficulty": 2,
                "team_a_difficulty": 4,
                "finished": False,
            },
        ]
    ).to_parquet(processed / "fixtures.parquet", index=False)
    pd.DataFrame(
        [
            {
                "player_id": 1,
                "gameweek_id": 1,
                "fixture_id": 10,
                "kickoff_time": "2026-08-01T12:00:00Z",
                "minutes": 90,
                "total_points": 5,
                "goals_scored": 1,
                "assists": 0,
                "was_home": True,
                "expected_goals": 0.8,
                "expected_assists": 0.2,
                "expected_goals_conceded": 1.1,
            }
        ]
    ).to_parquet(processed / "player_performances.parquet", index=False)
    table = write_role_table(tmp_path / "roles.csv", [1])
    feat = build_features(
        processed, target_gw=2, horizon=1, use_archive_seed=False, **role_kwargs(table)
    )
    row = feat[(feat["player_id"] == 1) & (feat["fixture_id"] == 11)].iloc[0]
    assert float(row["attack_multiplier"]) == 1.0
    assert float(row["defence_multiplier"]) == 1.0


def test_history_applies_share_addon_and_forces_neutral_multipliers() -> None:
    rows: list[dict[str, object]] = []
    fixtures: list[dict[str, object]] = []
    for gw in range(1, 11):
        fid_home = 100 + gw
        fid_opp = 200 + gw
        fixtures.append(
            {"id": fid_home, "home_club_id": 10, "away_club_id": 30, "gameweek_id": gw}
        )
        fixtures.append(
            {"id": fid_opp, "home_club_id": 40, "away_club_id": 20, "gameweek_id": gw}
        )
        rows.extend(
            [
                {
                    "player_id": 1,
                    "club_id": 10,
                    "fixture_id": fid_home,
                    "gameweek_id": gw,
                    "was_home": True,
                    "minutes": 90,
                    "expected_goals": 1.0,
                    "expected_assists": 0.5,
                    "expected_goals_conceded": 1.0,
                },
                {
                    "player_id": 2,
                    "club_id": 10,
                    "fixture_id": fid_home,
                    "gameweek_id": gw,
                    "was_home": True,
                    "minutes": 90,
                    "expected_goals": 1.0,
                    "expected_assists": 0.5,
                    "expected_goals_conceded": 1.0,
                },
                {
                    "player_id": 3,
                    "club_id": 20,
                    "fixture_id": fid_opp,
                    "gameweek_id": gw,
                    "was_home": False,
                    "minutes": 90,
                    "expected_goals": 2.5,
                    "expected_assists": 0.0,
                    "expected_goals_conceded": 2.5,
                },
            ]
        )
    feat = _base_feat()
    out, applied = apply_matchup_share_overlay(
        feat, pd.DataFrame(rows), pd.DataFrame(fixtures), history_cutoff_gw=11
    )
    assert applied is True
    assert out.loc[0, "attack_multiplier"] == 1.0
    assert out.loc[0, "defence_multiplier"] == 1.0
    assert float(out.loc[0, "per90_xg"]) > 0.50
    assert float(out.loc[0, "per90_xa"]) > 0.20
    assert float(out.loc[0, "per90_goals_conceded"]) > 1.20
    assert float(out.loc[0, "per90_saves"]) > 3.0
