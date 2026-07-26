import pandas as pd
from models.metrics_component_hybrid import MetricsComponentHybridModel
from backtesting.metrics import evaluate_predictions


def test_predict_exports_all_event_components():
    model = MetricsComponentHybridModel()
    features = pd.DataFrame([{
        "player_id": 1,
        "position_id": 2,  # DEF
        "gameweek_id": 1,
        "fixture_id": 10,
        "avg_mins_3gw": 90.0,
        "difficulty": 3.0,
        "chance_of_playing": 100.0,
        "per90_goals": 0.1,
        "per90_assists": 0.05,
        "per90_clean_sheets": 0.4,
        "per90_goals_conceded": 1.0,
        "per90_defensive_contribution": 12.0,
    }])
    df_proj = model.predict(features, horizon=1)

    expected_cols = {
        "projected_points", "projected_minutes",
        "xp_minutes", "xp_goals", "xp_assists",
        "xp_clean_sheet", "xp_conceded", "xp_defcon", "xp_bonus"
    }
    assert expected_cols.issubset(df_proj.columns)
    assert df_proj["xp_minutes"].iloc[0] > 0
    assert df_proj["xp_clean_sheet"].iloc[0] > 0


def test_evaluate_predictions_computes_component_metrics():
    df_eval = pd.DataFrame([
        {
            "player_id": 1,
            "gameweek": 1,
            "projected_points": 5.0,
            "actual_points": 4.0,
            "xp_minutes": 2.0,
            "actual_xp_minutes": 2.0,
            "xp_goals": 1.5,
            "actual_xp_goals": 0.0,
            "xp_assists": 0.5,
            "actual_xp_assists": 0.0,
            "xp_clean_sheet": 1.0,
            "actual_xp_clean_sheet": 2.0,
            "xp_conceded": -0.5,
            "actual_xp_conceded": 0.0,
            "xp_defcon": 0.3,
            "actual_xp_defcon": 0.0,
            "xp_bonus": 0.2,
            "actual_xp_bonus": 0.0,
        }
    ])
    metrics = evaluate_predictions(df_eval)

    assert "component_metrics" in metrics
    cm = metrics["component_metrics"]
    assert "xp_minutes" in cm
    assert cm["xp_minutes"]["bias"] == 0.0
    assert cm["xp_goals"]["bias"] == 1.5
    assert cm["xp_clean_sheet"]["bias"] == -1.0
