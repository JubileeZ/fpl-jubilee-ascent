"""Ownership Explorer Season Window and Score Mode slice behaviour."""

from projections.explorer_slice import (
    GameweekScore,
    aggregate_slice,
    build_explorer_slices,
    realized_gameweek_score,
    select_slice_gameweeks,
)


def test_first_half_all_projection_is_gw1_to_19() -> None:
    gws = select_slice_gameweeks(
        season_window="first_half",
        score_mode="all_projection",
        finished_gameweeks=set(),
    )
    assert gws == tuple(range(1, 20))


def test_second_half_and_full_season_windows() -> None:
    assert select_slice_gameweeks("second_half", "all_projection", set()) == tuple(range(20, 39))
    assert select_slice_gameweeks("full_season", "all_projection", set()) == tuple(range(1, 39))


def test_realized_hidden_when_no_finished_gameweek_in_window() -> None:
    assert select_slice_gameweeks("first_half", "realized_points", set()) is None
    assert select_slice_gameweeks("second_half", "realized_points", {1, 2, 10}) is None


def test_realized_is_finished_gameweeks_inside_window_only() -> None:
    gws = select_slice_gameweeks("first_half", "realized_points", {1, 2, 3, 20})
    assert gws == (1, 2, 3)


def test_remaining_excludes_finished_keeps_current_unfinished() -> None:
    gws = select_slice_gameweeks("first_half", "remaining_projection", {1, 2, 3})
    assert gws == tuple(range(4, 20))
    assert 4 in gws


def test_all_projection_ignores_finished_flags() -> None:
    gws = select_slice_gameweeks("first_half", "all_projection", {1, 2, 3})
    assert gws == tuple(range(1, 20))


def test_cameo_has_high_rate_per_90_and_low_per_gameweek() -> None:
    per_gw = {1: GameweekScore(points=10.0, minutes=20.0, xp_goals=8.0, xp_minutes=1.0)}
    metrics = aggregate_slice(per_gw, tuple(range(1, 20)))
    assert metrics.total == 10.0
    assert metrics.n_gameweeks == 19
    assert metrics.avg_minutes == 1.1
    assert metrics.rate_per_90 == 45.0
    assert metrics.per_gameweek == 0.5263
    assert metrics.xp_goals == 8.0
    assert metrics.xp_minutes == 1.0


def test_missing_gameweeks_count_as_zero_in_denominator() -> None:
    per_gw = {1: GameweekScore(points=6.0, minutes=90.0)}
    metrics = aggregate_slice(per_gw, (1, 2))
    assert metrics.total == 6.0
    assert metrics.minutes == 90.0
    assert metrics.avg_minutes == 45.0
    assert metrics.per_gameweek == 3.0
    assert metrics.rate_per_90 == 6.0


def test_realized_uses_official_points_and_scoring_matrix_components() -> None:
    score = realized_gameweek_score(
        [
            {
                "minutes": 90,
                "total_points": 8,
                "goals_scored": 0,
                "assists": 0,
                "clean_sheets": 1,
                "goals_conceded": 0,
                "saves": 0,
                "bonus": 0,
                "defensive_contribution": 12,
            }
        ],
        position_id=2,
    )
    assert score.points == 8.0
    assert score.minutes == 90.0
    assert score.xp_minutes == 2.0
    assert score.xp_clean_sheet == 4.0
    assert score.xp_defcon == 2.0
    assert score.xp_conceded == 0.0


def test_realized_defcon_below_threshold_is_zero() -> None:
    score = realized_gameweek_score(
        [{"minutes": 90, "total_points": 2, "defensive_contribution": 9}],
        position_id=2,
    )
    assert score.xp_defcon == 0.0
    assert score.xp_minutes == 2.0


def test_realized_sums_double_gameweek_fixtures() -> None:
    score = realized_gameweek_score(
        [
            {"minutes": 90, "total_points": 5, "goals_scored": 1},
            {"minutes": 90, "total_points": 6, "assists": 1},
        ],
        position_id=4,
    )
    assert score.points == 11.0
    assert score.minutes == 180.0
    assert score.xp_goals == 4.0
    assert score.xp_assists == 3.0
    assert score.xp_minutes == 4.0


def test_explorer_slices_hide_realized_and_keep_all_projection() -> None:
    projections = {
        gw: GameweekScore(points=2.0, minutes=90.0, xp_minutes=2.0) for gw in range(1, 7)
    }
    slices = build_explorer_slices(projections, {}, set())
    first = slices["first_half"]
    assert first["realized_points"] is None
    assert first["all_projection"]["n_gameweeks"] == 19
    assert first["all_projection"]["total"] == 12.0
    assert first["remaining_projection"]["n_gameweeks"] == 19
    assert slices["second_half"]["all_projection"]["total"] == 0.0
