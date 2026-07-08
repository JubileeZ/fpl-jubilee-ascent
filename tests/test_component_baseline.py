import pandas as pd

from models.component_baseline import ComponentBaseline


def _row(**overrides) -> dict:
    base = {
        "player_id": 1,
        "position_id": 4,  # F
        "gameweek_id": 10,
        "avg_mins_3gw": 90.0,
        "difficulty": 3.0,
        "chance_of_playing": 100.0,
        "has_prior_seed": True,
        "per90_goals": 0.0,
        "per90_assists": 0.0,
        "per90_clean_sheets": 0.0,
        "per90_goals_conceded": 0.0,
        "per90_saves": 0.0,
        "per90_bonus": 0.0,
        "per90_yellow_cards": 0.0,
        "per90_red_cards": 0.0,
        "per90_penalties_saved": 0.0,
        "per90_penalties_missed": 0.0,
        "per90_own_goals": 0.0,
    }
    base.update(overrides)
    return base


def test_forward_goal_reconstructs_to_eight():
    # 90 min (>=60) = 2 minutes points + 1 goal (F) = 6 -> 8 total.
    df = pd.DataFrame([_row(per90_goals=1.0)])
    out = ComponentBaseline().predict(df, horizon=1)
    assert len(out) == 1
    row = out.iloc[0]
    assert int(row["player_id"]) == 1
    assert int(row["gameweek_id"]) == 10
    assert row["projected_points"] == 8.0
    assert row["projected_minutes"] == 90.0


def test_appearance_prob_scales_minutes_and_events():
    # 50% availability halves expected minutes (90->45, <60 so 1 minute pt)
    # and halves the goal contribution (1 goal/90 over 45 min -> 0.5 goals -> 3 pts).
    df = pd.DataFrame([_row(per90_goals=1.0, chance_of_playing=50.0)])
    out = ComponentBaseline().predict(df, horizon=1)
    row = out.iloc[0]
    assert row["projected_minutes"] == 45.0
    # 1 minute pt (45 min played) + 3 goal pts (0.5 goals) = 4.0
    assert row["projected_points"] == 4.0


def test_difficulty_multiplier_scales_event_rates():
    # difficulty 2 -> multiplier max(0.2,(6-2)/3)=1.333; goals 6*1.333=8 + 2 mins = 10.
    # difficulty 5 -> multiplier max(0.2,(6-5)/3)=0.333; goals 6*0.333=2 + 2 mins = 4.
    easy = ComponentBaseline().predict(pd.DataFrame([_row(per90_goals=1.0, difficulty=2.0)]), horizon=1).iloc[0]
    hard = ComponentBaseline().predict(pd.DataFrame([_row(per90_goals=1.0, difficulty=5.0)]), horizon=1).iloc[0]
    assert easy["projected_points"] == 10.0
    assert hard["projected_points"] == 4.0


def test_no_prior_seed_projects_zero():
    df = pd.DataFrame([_row(per90_goals=1.0, has_prior_seed=False)])
    out = ComponentBaseline().predict(df, horizon=1)
    row = out.iloc[0]
    assert row["projected_points"] == 0.0
    assert row["projected_minutes"] == 0.0


def test_multiple_components_defender_clean_sheet():
    # Defender, 90 min, 1 clean sheet per 90 -> 4 clean sheet pts + 2 mins = 6.
    df = pd.DataFrame([_row(position_id=2, per90_clean_sheets=1.0)])
    out = ComponentBaseline().predict(df, horizon=1)
    assert out.iloc[0]["projected_points"] == 6.0


def test_goalkeeper_saves_contribute():
    # GK, 90 min, 3 saves/90 -> 1 save pt + 2 mins = 3.
    df = pd.DataFrame([_row(position_id=1, per90_saves=3.0)])
    out = ComponentBaseline().predict(df, horizon=1)
    assert out.iloc[0]["projected_points"] == 3.0


def test_negative_events_reduce_xp():
    # Forward, 90 min, 1 yellow/90 -> -1 + 2 mins = 1.
    df = pd.DataFrame([_row(per90_yellow_cards=1.0)])
    out = ComponentBaseline().predict(df, horizon=1)
    assert out.iloc[0]["projected_points"] == 1.0


def test_horizon_replicates_target_fixture_across_gws():
    df = pd.DataFrame([_row(per90_goals=1.0)])
    out = ComponentBaseline().predict(df, horizon=3)
    assert len(out) == 3
    assert list(out["gameweek_id"]) == [10, 11, 12]
    assert all(out["projected_points"] == 8.0)

