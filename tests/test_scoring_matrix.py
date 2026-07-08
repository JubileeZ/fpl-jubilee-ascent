from models.scoring_matrix import event_points


def test_fwd_goal_worth_six():
    assert event_points("goals", "F", 1) == 6


def test_goal_points_per_position():
    assert event_points("goals", "M", 1) == 5
    assert event_points("goals", "D", 1) == 4
    assert event_points("goals", "GK", 1) == 4


def test_goal_points_scale_with_quantity():
    assert event_points("goals", "F", 2) == 12


def test_assist_worth_three_for_any_position():
    for pos in ("GK", "D", "M", "F"):
        assert event_points("assists", pos, 1) == 3


def test_clean_sheet_per_position():
    assert event_points("clean_sheets", "GK", 1) == 4
    assert event_points("clean_sheets", "D", 1) == 4
    assert event_points("clean_sheets", "M", 1) == 1
    assert event_points("clean_sheets", "F", 1) == 0


def test_minutes_under_sixty_worth_one():
    assert event_points("minutes", "F", 30) == 1
    assert event_points("minutes", "GK", 59) == 1


def test_minutes_sixty_or_more_worth_two():
    assert event_points("minutes", "M", 60) == 2
    assert event_points("minutes", "D", 90) == 2


def test_minutes_zero_worth_zero():
    assert event_points("minutes", "F", 0) == 0


def test_goals_conceded_gk_def_lose_one_per_two():
    assert event_points("goals_conceded", "GK", 2) == -1
    assert event_points("goals_conceded", "D", 4) == -2
    assert event_points("goals_conceded", "GK", 1) == 0


def test_goals_conceded_mid_fwd_unaffected():
    assert event_points("goals_conceded", "M", 6) == 0
    assert event_points("goals_conceded", "F", 4) == 0


def test_saves_gk_one_point_per_three():
    assert event_points("saves", "GK", 3) == 1
    assert event_points("saves", "GK", 6) == 2


def test_saves_non_gk_worth_zero():
    assert event_points("saves", "D", 9) == 0


def test_bonus_passes_through():
    assert event_points("bonus", "M", 0) == 0
    assert event_points("bonus", "F", 1) == 1
    assert event_points("bonus", "M", 3) == 3


def test_yellow_card_minus_one():
    assert event_points("yellow_cards", "D", 1) == -1
    assert event_points("yellow_cards", "M", 2) == -2


def test_red_card_minus_two():
    # ponytail: issue #77 specifies red=-2; official FPL is -3. Revisit if
    # reconstruction underfits red-card xP.
    assert event_points("red_cards", "F", 1) == -2


def test_penalties_saved_worth_five():
    assert event_points("penalties_saved", "GK", 1) == 5


def test_penalties_missed_minus_two():
    assert event_points("penalties_missed", "F", 1) == -2


def test_own_goal_minus_two():
    assert event_points("own_goals", "D", 1) == -2
    assert event_points("own_goals", "M", 2) == -4


def test_unknown_component_raises():
    import pytest
    with pytest.raises(ValueError):
        event_points("bogus", "F", 1)
