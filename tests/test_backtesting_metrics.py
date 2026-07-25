import pandas as pd

from backtesting.metrics import evaluate_predictions


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
