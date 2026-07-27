import pandas as pd
import pytest

from backtesting.promotion import (
    classify_live_lead,
    evaluate_historical_promotion_gate,
    guardrail_metrics,
    metrics_by_season_window,
    metrics_meet_guardrails,
    primary_metric_name,
    primary_metric_value,
)


def _metrics(
    *,
    mae: float,
    bias: float = 0.0,
    regret: float | None = 0.5,
    xmins_mae: float = 10.0,
    spearman: float = 0.4,
) -> dict:
    return {
        "mae": mae,
        "bias": bias,
        "spearman": spearman,
        "top_11_regret": regret,
        "minutes_forecast_metrics": {"mae": xmins_mae},
    }


def test_primary_metric_falls_back_to_xp_mae_without_rank_signal() -> None:
    metrics = _metrics(mae=2.0, regret=0.0)
    metrics["valid_rank_gameweeks"] = 0
    assert primary_metric_name(metrics) == "xp_mae"
    assert primary_metric_value(metrics) == 2.0


def test_guardrails_require_candidate_to_match_or_improve_champion() -> None:
    champion = guardrail_metrics(_metrics(mae=2.0, bias=1.0, xmins_mae=12.0, spearman=0.3))
    better = guardrail_metrics(_metrics(mae=1.5, bias=0.5, xmins_mae=10.0, spearman=0.4))
    worse = guardrail_metrics(_metrics(mae=1.5, bias=1.5, xmins_mae=10.0, spearman=0.4))

    assert metrics_meet_guardrails(better, champion)
    assert not metrics_meet_guardrails(worse, champion)


def test_historical_promotion_gate_passes_clear_winner() -> None:
    champion_windows = {
        "combined": _metrics(mae=2.0, regret=1.0),
        "cold_start": _metrics(mae=2.2, regret=1.1),
        "early_mid": _metrics(mae=2.1, regret=1.05),
        "late": _metrics(mae=2.0, regret=1.0),
    }
    candidate_windows = {
        "combined": _metrics(mae=1.5, regret=0.7, xmins_mae=9.0, spearman=0.5),
        "cold_start": _metrics(mae=1.4, regret=0.6),
        "early_mid": _metrics(mae=1.3, regret=0.65),
        "late": _metrics(mae=1.6, regret=0.9),
    }

    verdict = evaluate_historical_promotion_gate(champion_windows, candidate_windows)

    assert verdict.passed
    assert verdict.segment_wins >= 2
    assert verdict.guardrails_passed


def test_historical_promotion_gate_fails_without_segment_majority() -> None:
    champion_windows = {
        "combined": _metrics(mae=2.0, regret=1.0),
        "cold_start": _metrics(mae=2.0, regret=1.0),
        "early_mid": _metrics(mae=2.0, regret=1.0),
        "late": _metrics(mae=2.0, regret=1.0),
    }
    candidate_windows = {
        "combined": _metrics(mae=1.5, regret=0.7),
        "cold_start": _metrics(mae=1.4, regret=0.6),
        "early_mid": _metrics(mae=2.5, regret=1.2),
        "late": _metrics(mae=2.4, regret=1.1),
    }

    verdict = evaluate_historical_promotion_gate(champion_windows, candidate_windows)

    assert not verdict.passed
    assert "seasonal segments" in verdict.reasons[0]


def test_metrics_by_season_window_splits_gameweeks() -> None:
    df_eval = pd.DataFrame(
        [
            {"player_id": 1, "gameweek": 2, "projected_points": 5.0, "actual_points": 4.0},
            {"player_id": 2, "gameweek": 10, "projected_points": 6.0, "actual_points": 5.0},
            {"player_id": 3, "gameweek": 25, "projected_points": 7.0, "actual_points": 6.0},
        ]
    )

    windows = metrics_by_season_window(df_eval)

    assert set(windows) == {"combined", "cold_start", "early_mid", "late"}
    assert windows["cold_start"]["sample_count"] == 1
    assert windows["early_mid"]["sample_count"] == 1
    assert windows["late"]["sample_count"] == 1


@pytest.mark.parametrize(
    ("champion", "candidate", "expected"),
    [
        (1.0, 0.97, "unclear"),
        (1.0, 0.94, "meaningful"),
        (1.0, 1.06, "meaningful_loss"),
    ],
)
def test_classify_live_lead(champion: float, candidate: float, expected: str) -> None:
    assert classify_live_lead(champion, candidate) == expected
