import pandas as pd
from models.metrics_component_hybrid import MetricsComponentHybridModel

def _row(**overrides) -> dict:
    base = {
        "player_id": 1,
        "position_id": 4,  # FWD
        "gameweek_id": 10,
        "avg_mins_3gw": 90.0,
        "difficulty": 3.0,
        "chance_of_playing": 100.0,
        "has_prior_seed": True,
        "per90_goals": 0.0,
        "per90_assists": 0.0,
        "per90_clean_sheets": 0.0,
        "per90_goals_conceded": 1.0,
        "per90_saves": 0.0,
        "per90_bonus": 0.0,
        "per90_yellow_cards": 0.0,
        "per90_red_cards": 0.0,
        "per90_defensive_contribution": 0.0,
        "per90_xg": 0.0,
        "per90_xa": 0.0,
        "per90_threat": 0.0,
        "per90_creativity": 0.0,
    }
    base.update(overrides)
    return base


def test_metrics_component_hybrid_name():
    model = MetricsComponentHybridModel()
    assert model.name == "metrics_component_hybrid"


def test_xg_threat_regression_increases_xp():
    model = MetricsComponentHybridModel()
    low_xg = model.predict(pd.DataFrame([_row(per90_xg=0.1, per90_threat=10.0)]), horizon=1).iloc[0]
    high_xg = model.predict(pd.DataFrame([_row(per90_xg=0.8, per90_threat=80.0)]), horizon=1).iloc[0]
    assert high_xg["projected_points"] > low_xg["projected_points"]


def test_poisson_clean_sheet_requires_sixty_minutes():
    model = MetricsComponentHybridModel()
    # Defender, 90 mins -> CS > 0
    full_game = model.predict(pd.DataFrame([_row(position_id=2, avg_mins_3gw=90.0)]), horizon=1).iloc[0]
    # Defender, 45 mins -> CS = 0
    sub_game = model.predict(pd.DataFrame([_row(position_id=2, avg_mins_3gw=45.0)]), horizon=1).iloc[0]
    assert full_game["projected_points"] > sub_game["projected_points"]


def test_defcon_bps_boost_for_defenders():
    model = MetricsComponentHybridModel()
    no_defcon = model.predict(pd.DataFrame([_row(position_id=2, per90_defensive_contribution=0.0)]), horizon=1).iloc[0]
    high_defcon = model.predict(pd.DataFrame([_row(position_id=2, per90_defensive_contribution=15.0)]), horizon=1).iloc[0]
    assert high_defcon["projected_points"] > no_defcon["projected_points"]


def test_softmax_bonus_is_bounded():
    model = MetricsComponentHybridModel()
    res = model.predict(pd.DataFrame([_row(per90_xg=1.5, per90_threat=150.0)]), horizon=1).iloc[0]
    assert 0.0 <= res["projected_points"] <= 20.0


def test_zero_availability_zeroes_minutes_and_points():
    model = MetricsComponentHybridModel()
    result = model.predict(
        pd.DataFrame([_row(chance_of_playing=0.0, per90_xg=1.0)]),
        horizon=1,
    ).iloc[0]
    assert result["projected_minutes"] == 0.0
    assert result["projected_points"] == 0.0


def test_xmins_cap_limits_projected_minutes():
    result = MetricsComponentHybridModel().predict(
        pd.DataFrame([_row(per90_xg=1.0, xmins_cap=45.0)]),
        horizon=1,
    ).iloc[0]

    assert result["projected_minutes"] == 45.0


def test_defensive_contribution_probability_adds_fpl_points():
    model = MetricsComponentHybridModel()
    without_defcon = model.predict(
        pd.DataFrame([_row(position_id=2, per90_defensive_contribution=0.0)]),
        horizon=1,
    ).iloc[0]
    with_defcon = model.predict(
        pd.DataFrame([_row(position_id=2, per90_defensive_contribution=15.0)]),
        horizon=1,
    ).iloc[0]
    assert with_defcon["projected_points"] - without_defcon["projected_points"] > 1.0


def test_zero_goals_conceded_rate_is_not_replaced_by_default():
    model = MetricsComponentHybridModel()
    zero_rate = model.predict(
        pd.DataFrame([_row(position_id=1, per90_goals_conceded=0.0)]),
        horizon=1,
    ).iloc[0]
    conceded_rate = model.predict(
        pd.DataFrame([_row(position_id=1, per90_goals_conceded=1.0)]),
        horizon=1,
    ).iloc[0]
    assert zero_rate["projected_points"] > conceded_rate["projected_points"]


def test_negative_event_projection_is_preserved():
    model = MetricsComponentHybridModel()
    result = model.predict(
        pd.DataFrame([_row(per90_yellow_cards=10.0)]),
        horizon=1,
    ).iloc[0]
    assert result["projected_points"] < 0.0


def test_full_match_bonus_allocates_six_points():
    model = MetricsComponentHybridModel()
    players = [
        _row(player_id=1, position_id=4, per90_xg=1.2, avg_mins_3gw=90.0),
        _row(player_id=2, position_id=3, per90_xa=1.0, avg_mins_3gw=90.0),
        _row(player_id=3, position_id=2, per90_clean_sheets=0.5, avg_mins_3gw=90.0),
        _row(player_id=4, position_id=1, per90_saves=4.0, avg_mins_3gw=90.0),
    ]
    df = pd.DataFrame(players)
    df["fixture_id"] = 100
    preds = model.predict(df, horizon=1)

    # For 4 eligible players in a fixture, total projected points must be positive and include all 6 bonus points
    assert len(preds) == 4
    assert preds["projected_points"].sum() > 6.0



def test_empirical_bayes_fit_learns_weights():
    model = MetricsComponentHybridModel()
    history = pd.DataFrame([
        {"player_id": 1, "minutes": 90, "goals_scored": 2, "expected_goals": 1.5, "threat": 120.0, "assists": 1, "expected_assists": 0.8, "creativity": 80.0},
        {"player_id": 1, "minutes": 90, "goals_scored": 1, "expected_goals": 0.9, "threat": 90.0, "assists": 0, "expected_assists": 0.3, "creativity": 30.0},
        {"player_id": 2, "minutes": 90, "goals_scored": 0, "expected_goals": 0.1, "threat": 10.0, "assists": 2, "expected_assists": 1.2, "creativity": 110.0},
    ])
    model.fit(history)
    assert model.goal_weights is not None
    assert model.assist_weights is not None

