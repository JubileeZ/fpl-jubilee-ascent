import pandas as pd
import pytest

from backtesting.metrics import evaluate_predictions


_LEDGER_COMPONENTS = (
    "xp_minutes",
    "xp_goals",
    "xp_assists",
    "xp_clean_sheet",
    "xp_conceded",
    "xp_saves",
    "xp_penalties_saved",
    "xp_penalties_missed",
    "xp_own_goals",
    "xp_yellow_cards",
    "xp_red_cards",
    "xp_defcon",
    "xp_bonus",
)


def test_metrics_report_bias_rank_counts_and_shortlist_quality():
    df_eval = pd.DataFrame([
        {"player_id": 1, "gameweek": 1, "projected_points": 10.0, "actual_points": 8.0, "actual_minutes": 90, "position_id": 3},
        {"player_id": 2, "gameweek": 1, "projected_points": 8.0, "actual_points": 10.0, "actual_minutes": 0, "position_id": 3},
        {"player_id": 3, "gameweek": 2, "projected_points": 4.0, "actual_points": 4.0, "actual_minutes": 45, "position_id": 4},
    ])

    metrics = evaluate_predictions(df_eval, top_k_values=(1,))

    assert metrics["sample_count"] == 3
    assert metrics["bias"] == 0.0
    assert metrics["valid_rank_gameweeks"] == 1
    assert metrics["undefined_rank_gameweeks"] == 1
    assert metrics["top_1_overlap"] == 0.5
    assert metrics["position_metrics"]["3"]["sample_count"] == 2.0
    assert set(metrics["minutes_band_metrics"]) == {"0", "1-59", "60+"}


def test_minutes_forecast_metrics_identify_zero_cameo_and_full_appearance_errors():
    df_eval = pd.DataFrame([
        {"player_id": 1, "gameweek": 1, "projected_points": 4.0, "actual_points": 0.0, "projected_minutes": 70.0, "actual_minutes": 0.0},
        {"player_id": 2, "gameweek": 1, "projected_points": 2.0, "actual_points": 1.0, "projected_minutes": 35.0, "actual_minutes": 30.0},
        {"player_id": 3, "gameweek": 1, "projected_points": 5.0, "actual_points": 6.0, "projected_minutes": 75.0, "actual_minutes": 90.0},
    ])

    metrics = evaluate_predictions(df_eval)
    minutes = metrics["minutes_forecast_metrics"]

    assert minutes["mean_projected"] == pytest.approx(60.0)
    assert minutes["mean_actual"] == pytest.approx(40.0)
    assert minutes["bias"] == pytest.approx(20.0)
    assert minutes["by_actual_band"]["0"]["mean_projected"] == pytest.approx(70.0)
    assert minutes["by_actual_band"]["1-59"]["mae"] == pytest.approx(5.0)
    assert minutes["by_actual_band"]["60+"]["bias"] == pytest.approx(-15.0)


def test_complete_component_ledgers_reconcile():
    row = {
        "player_id": 1,
        "gameweek": 1,
        **{component: 1.0 for component in _LEDGER_COMPONENTS},
        **{f"actual_{component}": 1.0 for component in _LEDGER_COMPONENTS},
    }
    row["projected_points"] = float(len(_LEDGER_COMPONENTS))
    row["actual_points"] = float(len(_LEDGER_COMPONENTS))

    metrics = evaluate_predictions(pd.DataFrame([row]))

    assert metrics["component_metrics"]["xp_saves"]["mae"] == 0.0
    assert metrics["component_metrics"]["xp_red_cards"]["bias"] == 0.0


def test_component_ledger_reconciliation_rejects_residuals():
    row = {
        "player_id": 1,
        "gameweek": 1,
        **{component: 0.0 for component in _LEDGER_COMPONENTS},
        **{f"actual_{component}": 0.0 for component in _LEDGER_COMPONENTS},
        "projected_points": 1.0,
        "actual_points": 0.0,
    }

    with pytest.raises(ValueError, match="Predicted component ledger"):
        evaluate_predictions(pd.DataFrame([row]))
