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
    # Peripheral defense decoupled: saves and defcon remain unscaled (neutral x1.0)
    assert float(out.loc[0, "per90_saves"]) == 3.0
    assert float(out.loc[0, "per90_defensive_contribution"]) == 8.0


def test_positional_prior_regularizes_returning_player_with_no_minutes() -> None:
    """Player with 0 minutes gets regularized positional share rather than 0.0."""
    fixtures = pd.DataFrame([
        {"id": 101, "home_club_id": 10, "away_club_id": 30, "gameweek_id": 1},
        {"id": 102, "home_club_id": 40, "away_club_id": 20, "gameweek_id": 1},
    ])
    rows = pd.DataFrame([
        {
            "player_id": 99,
            "club_id": 10,
            "fixture_id": 101,
            "gameweek_id": 1,
            "was_home": True,
            "minutes": 90,
            "expected_goals": 2.0,
            "expected_assists": 1.0,
            "expected_goals_conceded": 0.5,
        },
        {
            "player_id": 88,
            "club_id": 20,
            "fixture_id": 102,
            "gameweek_id": 1,
            "was_home": False,
            "minutes": 90,
            "expected_goals": 1.0,
            "expected_assists": 0.5,
            "expected_goals_conceded": 3.0,
        },
    ])
    # Player 1 is a FWD (pos 4), Player 2 is a DEF (pos 2). Neither has minutes in rows.
    feat = pd.DataFrame([
        {
            "player_id": 1,
            "club_id": 10,
            "opponent_id": 20,
            "position_id": 4,  # FWD
            "is_home": True,
            "gameweek_id": 2,
            "fixture_id": 201,
            "per90_xg": 0.60,
            "per90_xa": 0.20,
            "per90_goals_conceded": 1.0,
            "per90_saves": 0.0,
            "per90_defensive_contribution": 4.0,
            "penalties_order": 0.0,
        },
        {
            "player_id": 2,
            "club_id": 10,
            "opponent_id": 20,
            "position_id": 2,  # DEF
            "is_home": True,
            "gameweek_id": 2,
            "fixture_id": 201,
            "per90_xg": 0.05,
            "per90_xa": 0.05,
            "per90_goals_conceded": 1.0,
            "per90_saves": 0.0,
            "per90_defensive_contribution": 10.0,
            "penalties_order": 0.0,
        },
    ])
    out, applied = apply_matchup_share_overlay(feat, rows, fixtures, history_cutoff_gw=2)
    assert applied is True
    # FWD with 0 minutes gets FWD prior share (~0.26), boosting xG against weak opponent
    fwd_bump = float(out.loc[0, "per90_xg"]) - 0.60
    def_bump = float(out.loc[1, "per90_xg"]) - 0.05
    assert fwd_bump > 0.0
    assert def_bump > 0.0
    # Forward gets significantly higher share than defender from positional prior
    assert fwd_bump > def_bump * 4.0


def test_shrinkage_parameter_scales_delta_proportionally() -> None:
    fixtures = pd.DataFrame([
        {"id": 101, "home_club_id": 10, "away_club_id": 30, "gameweek_id": 1},
        {"id": 102, "home_club_id": 40, "away_club_id": 20, "gameweek_id": 1},
    ])
    rows = pd.DataFrame([
        {
            "player_id": 1,
            "club_id": 10,
            "fixture_id": 101,
            "gameweek_id": 1,
            "was_home": True,
            "minutes": 90,
            "expected_goals": 2.0,
            "expected_assists": 1.0,
            "expected_goals_conceded": 0.5,
        },
        {
            "player_id": 88,
            "club_id": 20,
            "fixture_id": 102,
            "gameweek_id": 1,
            "was_home": False,
            "minutes": 90,
            "expected_goals": 1.0,
            "expected_assists": 0.5,
            "expected_goals_conceded": 3.0,
        },
    ])
    feat = pd.DataFrame([
        {
            "player_id": 1,
            "club_id": 10,
            "opponent_id": 20,
            "position_id": 4,
            "is_home": True,
            "gameweek_id": 2,
            "fixture_id": 201,
            "per90_xg": 0.50,
            "per90_xa": 0.20,
            "per90_goals_conceded": 1.0,
            "per90_saves": 0.0,
            "per90_defensive_contribution": 4.0,
            "penalties_order": 0.0,
        }
    ])
    out_half, _ = apply_matchup_share_overlay(
        feat, rows, fixtures, history_cutoff_gw=2, shrink_att=0.20, shrink_def=0.20
    )
    out_full, _ = apply_matchup_share_overlay(
        feat, rows, fixtures, history_cutoff_gw=2, shrink_att=0.40, shrink_def=0.40
    )
    bump_half = float(out_half.loc[0, "per90_xg"]) - 0.50
    bump_full = float(out_full.loc[0, "per90_xg"]) - 0.50
    assert abs(bump_full - 2.0 * bump_half) < 1e-9


def _ratio_fixtures_and_hist() -> tuple[pd.DataFrame, pd.DataFrame]:
    fixtures = pd.DataFrame(
        [
            {"id": 101, "home_club_id": 10, "away_club_id": 30, "gameweek_id": 1},
            {"id": 102, "home_club_id": 40, "away_club_id": 20, "gameweek_id": 1},
        ]
    )
    rows = pd.DataFrame(
        [
            {
                "player_id": 1,
                "club_id": 10,
                "fixture_id": 101,
                "gameweek_id": 1,
                "was_home": True,
                "minutes": 90,
                "expected_goals": 1.5,
                "expected_assists": 0.5,
                "expected_goals_conceded": 1.0,
            },
            {
                # Weak-defence opponent: high xGC inflates the attack ratio.
                "player_id": 88,
                "club_id": 20,
                "fixture_id": 102,
                "gameweek_id": 1,
                "was_home": False,
                "minutes": 90,
                "expected_goals": 0.5,
                "expected_assists": 0.2,
                "expected_goals_conceded": 3.0,
            },
        ]
    )
    return fixtures, rows


def _ratio_feat(position_id: int) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "player_id": 7,
                "club_id": 10,
                "opponent_id": 20,
                "position_id": position_id,
                "is_home": True,
                "gameweek_id": 2,
                "fixture_id": 201,
                "per90_xg": 0.30,
                "per90_xa": 0.15,
                "per90_goals_conceded": 1.0,
                "per90_saves": 0.0,
                "per90_defensive_contribution": 6.0,
                "penalties_order": 0.0,
            }
        ]
    )


def test_attack_scale_ratio_moves_mid_fwd_with_opponent() -> None:
    fixtures, rows = _ratio_fixtures_and_hist()
    out, applied = apply_matchup_share_overlay(
        _ratio_feat(3), rows, fixtures, history_cutoff_gw=2, attack_scale="ratio"
    )
    assert applied is True
    mult = float(out.loc[0, "attack_multiplier"])
    assert 0.7 <= mult <= 1.4
    # Weak-defence opponent (xGC above league) scales attack up.
    assert mult > 1.0
    assert float(out.loc[0, "defence_multiplier"]) == 1.0


def test_attack_scale_ratio_leaves_def_gkp_neutral() -> None:
    fixtures, rows = _ratio_fixtures_and_hist()
    for position_id in (1, 2):
        out, applied = apply_matchup_share_overlay(
            _ratio_feat(position_id), rows, fixtures, history_cutoff_gw=2,
            attack_scale="ratio",
        )
        assert applied is True
        assert float(out.loc[0, "attack_multiplier"]) == 1.0


def test_attack_scale_rejects_unknown_mode() -> None:
    fixtures, rows = _ratio_fixtures_and_hist()
    try:
        apply_matchup_share_overlay(
            _ratio_feat(3), rows, fixtures, history_cutoff_gw=2,
            attack_scale="turbo",
        )
    except ValueError as exc:
        assert "attack_scale" in str(exc)
    else:
        raise AssertionError("expected ValueError for unknown attack_scale")


def _passthrough_processed(processed: Path) -> None:
    processed.mkdir()
    pd.DataFrame(
        [
            {
                "id": 1,
                "club_id": 1,
                "position_id": 3,
                "now_cost": 90,
                "chance_of_playing_next_round": 100.0,
                "penalties_order": 0,
            },
            {
                "id": 2,
                "club_id": 2,
                "position_id": 4,
                "now_cost": 90,
                "chance_of_playing_next_round": 100.0,
                "penalties_order": 0,
            },
        ]
    ).to_parquet(processed / "players.parquet", index=False)
    pd.DataFrame(
        [
            {"id": 1, "name": "A", "short_name": "A", "strength": 3},
            {"id": 2, "name": "B", "short_name": "B", "strength": 3},
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
                "expected_goals": 1.0,
                "expected_assists": 0.5,
                "expected_goals_conceded": 1.0,
            },
            {
                "player_id": 2,
                "gameweek_id": 1,
                "fixture_id": 10,
                "kickoff_time": "2026-08-01T12:00:00Z",
                "minutes": 90,
                "total_points": 2,
                "goals_scored": 0,
                "assists": 0,
                "was_home": False,
                "expected_goals": 0.5,
                "expected_assists": 0.2,
                "expected_goals_conceded": 3.0,
            },
        ]
    ).to_parquet(processed / "player_performances.parquet", index=False)


def test_build_features_matchup_variant_kwargs_reach_overlay(tmp_path: Path) -> None:
    """Explicit variant kwargs change overlay output; defaults stay production."""
    processed = tmp_path / "processed"
    _passthrough_processed(processed)
    table = write_role_table(tmp_path / "roles.csv", [1, 2])
    base_kwargs = dict(
        target_gw=2, horizon=1, use_archive_seed=False, **role_kwargs(table)
    )
    default = build_features(processed, **base_kwargs)
    row_default = default[
        (default["player_id"] == 1) & (default["fixture_id"] == 11)
    ].iloc[0]
    assert float(row_default["attack_multiplier"]) == 1.0

    boosted = build_features(processed, **base_kwargs, matchup_shrink_att=0.80)
    row_boosted = boosted[
        (boosted["player_id"] == 1) & (boosted["fixture_id"] == 11)
    ].iloc[0]
    assert float(row_boosted["per90_xg"]) > float(row_default["per90_xg"])

    ratio = build_features(processed, **base_kwargs, matchup_attack_scale="ratio")
    row_ratio = ratio[(ratio["player_id"] == 1) & (ratio["fixture_id"] == 11)].iloc[0]
    mult = float(row_ratio["attack_multiplier"])
    assert 0.7 <= mult <= 1.4
    assert mult > 1.0  # weak-defence opponent scales MID attack up


def _downside_fixtures_and_hist() -> tuple[pd.DataFrame, pd.DataFrame]:
    fixtures = pd.DataFrame(
        [
            {"id": 101, "home_club_id": 10, "away_club_id": 30, "gameweek_id": 1},
            {"id": 102, "home_club_id": 40, "away_club_id": 20, "gameweek_id": 1},
        ]
    )
    rows = pd.DataFrame(
        [
            {
                "player_id": 1,
                "club_id": 10,
                "fixture_id": 101,
                "gameweek_id": 1,
                "was_home": True,
                "minutes": 90,
                "expected_goals": 1.0,
                "expected_assists": 0.5,
                "expected_goals_conceded": 2.0,
            },
            {
                # Strong-defence opponent: low xGC pulls the downside ratio below 1.
                "player_id": 88,
                "club_id": 20,
                "fixture_id": 102,
                "gameweek_id": 1,
                "was_home": False,
                "minutes": 90,
                "expected_goals": 0.5,
                "expected_assists": 0.2,
                "expected_goals_conceded": 0.4,
            },
        ]
    )
    return fixtures, rows


def test_attack_scale_downside_never_inflates_weak_fixture() -> None:
    fixtures, rows = _ratio_fixtures_and_hist()
    out, applied = apply_matchup_share_overlay(
        _ratio_feat(3), rows, fixtures, history_cutoff_gw=2, attack_scale="downside"
    )
    assert applied is True
    # Weak-defence opponent: capped at 1.0, easy ceiling untouched.
    assert float(out.loc[0, "attack_multiplier"]) == 1.0
    assert float(out.loc[0, "defence_multiplier"]) == 1.0


def test_attack_scale_downside_reduces_strong_fixture() -> None:
    fixtures, rows = _downside_fixtures_and_hist()
    out, applied = apply_matchup_share_overlay(
        _ratio_feat(3), rows, fixtures, history_cutoff_gw=2, attack_scale="downside"
    )
    assert applied is True
    mult = float(out.loc[0, "attack_multiplier"])
    assert 0.7 <= mult < 1.0  # strong-defence opponent scales MID attack down


def test_attack_scale_downside_leaves_def_gkp_neutral() -> None:
    fixtures, rows = _downside_fixtures_and_hist()
    for position_id in (1, 2):
        out, applied = apply_matchup_share_overlay(
            _ratio_feat(position_id), rows, fixtures, history_cutoff_gw=2,
            attack_scale="downside",
        )
        assert applied is True
        assert float(out.loc[0, "attack_multiplier"]) == 1.0


