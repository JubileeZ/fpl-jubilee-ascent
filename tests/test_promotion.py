import pandas as pd
import pytest

from backtesting.promotion import (
    BOOTSTRAP_MIN_P,
    CONFIRMATION_BOOTSTRAP_MIN_P,
    block_bootstrap_win_probability,
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


def _regret_metrics(*, mae: float, regret: float) -> dict:
    return {**_metrics(mae=mae, regret=regret), "valid_rank_gameweeks": 6}


def _clear_winner_windows() -> tuple[dict, dict]:
    champion = {name: _regret_metrics(mae=2.0, regret=10.0) for name in ("combined", "cold_start", "early_mid", "late")}
    candidate = {name: _regret_metrics(mae=1.9, regret=9.0) for name in ("combined", "cold_start", "early_mid", "late")}
    return champion, candidate


def test_gate_has_no_minimum_effect_beyond_improvement() -> None:
    champion, candidate = _clear_winner_windows()
    candidate["combined"] = _regret_metrics(mae=1.9, regret=9.95)

    small = evaluate_historical_promotion_gate(champion, candidate)
    candidate["combined"] = _regret_metrics(mae=1.9, regret=10.0)
    flat = evaluate_historical_promotion_gate(champion, candidate)

    assert small.passed
    assert small.min_effect == pytest.approx(0.0)
    assert not flat.passed
    assert "combined primary metric did not improve" in flat.reasons


def test_gate_requires_block_bootstrap_significance() -> None:
    champion, candidate = _clear_winner_windows()

    noisy = evaluate_historical_promotion_gate(champion, candidate, gw_primary_deltas=[5.0, -4.0, 3.0, -4.5, 1.5, -0.5])
    steady = evaluate_historical_promotion_gate(champion, candidate, gw_primary_deltas=[1.0, 0.5, 1.5, 0.8, 1.2, 1.0])

    assert not noisy.passed
    assert noisy.bootstrap_p is not None and noisy.bootstrap_p < BOOTSTRAP_MIN_P
    assert any("bootstrap" in reason for reason in noisy.reasons)
    assert steady.passed
    assert steady.bootstrap_p == 1.0


def test_both_seasons_accept_moderate_bootstrap_confidence() -> None:
    champion, candidate = _clear_winner_windows()
    deltas = [3.0, -1.0, 2.0, -1.5, 1.5, 0.5]

    dev = evaluate_historical_promotion_gate(champion, candidate, gw_primary_deltas=deltas)
    confirm = evaluate_historical_promotion_gate(
        champion, candidate, gw_primary_deltas=deltas, bootstrap_min_p=CONFIRMATION_BOOTSTRAP_MIN_P
    )

    assert BOOTSTRAP_MIN_P == CONFIRMATION_BOOTSTRAP_MIN_P == 0.60
    assert dev.bootstrap_p is not None and BOOTSTRAP_MIN_P <= dev.bootstrap_p < 0.95
    assert dev.passed
    assert confirm.passed


def test_guardrails_tolerate_noise_but_not_real_regression() -> None:
    champion = guardrail_metrics(_metrics(mae=2.0, bias=0.10, xmins_mae=14.0, spearman=0.69))
    within = guardrail_metrics(_metrics(mae=2.0, bias=0.105, xmins_mae=14.1, spearman=0.687))
    outside = guardrail_metrics(_metrics(mae=2.0, bias=0.10, xmins_mae=14.3, spearman=0.69))

    assert metrics_meet_guardrails(within, champion)
    assert not metrics_meet_guardrails(outside, champion)


def test_block_bootstrap_is_deterministic_and_bounded() -> None:
    deltas = [0.4, -0.2, 0.9, -1.1, 0.3, 0.6, -0.1]
    first = block_bootstrap_win_probability(deltas)

    assert first == block_bootstrap_win_probability(deltas)
    assert 0.0 < first < 1.0
    assert block_bootstrap_win_probability([]) == 0.0


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


def _blend_windows(*, champ_mae: float, cand_mae: float) -> tuple[dict, dict]:
    champion_windows = {
        "combined": _metrics(mae=champ_mae, regret=0.0),
        "cold_start": _metrics(mae=champ_mae, regret=0.0),
        "early_mid": _metrics(mae=champ_mae, regret=0.0),
        "late": _metrics(mae=champ_mae, regret=0.0),
    }
    candidate_windows = {
        "combined": _metrics(mae=cand_mae, regret=0.0),
        "cold_start": _metrics(mae=cand_mae, regret=0.0),
        "early_mid": _metrics(mae=cand_mae, regret=0.0),
        "late": _metrics(mae=cand_mae, regret=0.0),
    }
    return champion_windows, candidate_windows


def _reference_windows(
    *, champ_realized: float, cand_realized: float, champ_process: float, cand_process: float
) -> dict:
    return {
        "actual_points": (
            _metrics(mae=champ_realized, regret=0.0),
            _metrics(mae=cand_realized, regret=0.0),
        ),
        "process_points": (
            _metrics(mae=champ_process, regret=0.0),
            _metrics(mae=cand_process, regret=0.0),
        ),
    }


def test_blend_gate_passes_winner_holding_both_references() -> None:
    champion_windows, candidate_windows = _blend_windows(champ_mae=2.0, cand_mae=1.5)
    references = _reference_windows(
        champ_realized=2.0, cand_realized=1.8, champ_process=1.9, cand_process=1.7
    )
    verdict = evaluate_historical_promotion_gate(
        champion_windows,
        candidate_windows,
        eval_target="blended_points",
        reference_windows=references,
    )
    assert verdict.passed
    assert verdict.eval_target == "blended_points"
    assert verdict.guardrails_passed


def test_blend_gate_fails_when_realized_regresses() -> None:
    champion_windows, candidate_windows = _blend_windows(champ_mae=2.0, cand_mae=1.5)
    references = _reference_windows(
        champ_realized=2.0, cand_realized=2.4, champ_process=1.9, cand_process=1.7
    )
    verdict = evaluate_historical_promotion_gate(
        champion_windows,
        candidate_windows,
        eval_target="blended_points",
        reference_windows=references,
    )
    assert not verdict.passed
    assert not verdict.guardrails_passed
    assert any("Realized" in reason for reason in verdict.reasons)


def test_metrics_by_season_window_scores_blend_column() -> None:
    df_eval = pd.DataFrame(
        [
            {
                "player_id": 1,
                "gameweek": 10,
                "projected_points": 5.0,
                "actual_points": 9.0,
                "process_points": 3.0,
                "blended_points": 6.0,
            },
            {
                "player_id": 2,
                "gameweek": 10,
                "projected_points": 6.0,
                "actual_points": 5.0,
                "process_points": 5.0,
                "blended_points": 5.0,
            },
        ]
    )
    windows = metrics_by_season_window(df_eval, target_column="blended_points")
    # errors (5-6)=-1, (6-5)=1 → mae 1.0; realized mae would be 2.5
    assert abs(float(windows["combined"]["mae"]) - 1.0) < 1e-9
    assert windows["combined"]["eval_target"] == "blended_points"


def test_formation_xi_regret_prioritized_over_top_11() -> None:
    metrics = {
        "valid_rank_gameweeks": 10,
        "formation_xi_regret": 1.25,
        "top_11_regret": 2.50,
        "mae": 3.0,
    }
    assert primary_metric_name(metrics) == "decision_regret"
    assert primary_metric_value(metrics) == 1.25


def test_captaincy_guardrail_fails_when_exceeding_tolerance() -> None:
    from backtesting.promotion import CAPTAIN_REGRET_ABS_TOL

    champ_metrics = _metrics(mae=2.0, bias=0.1)
    champ_metrics["captain_regret"] = 1.0

    # Within tolerance (+0.15) passes
    cand_ok = _metrics(mae=1.8, bias=0.1)
    cand_ok["captain_regret"] = 1.0 + CAPTAIN_REGRET_ABS_TOL
    g_champ = guardrail_metrics(champ_metrics)
    g_ok = guardrail_metrics(cand_ok)
    assert metrics_meet_guardrails(g_ok, g_champ)

    # Beyond tolerance fails
    cand_fail = _metrics(mae=1.8, bias=0.1)
    cand_fail["captain_regret"] = 1.0 + CAPTAIN_REGRET_ABS_TOL + 0.05
    g_fail = guardrail_metrics(cand_fail)
    assert not metrics_meet_guardrails(g_fail, g_champ)


def test_playable_pool_metrics_and_guardrail() -> None:
    from backtesting.promotion import compute_playable_pool_metrics

    # 4 players:
    # 1: starter projected 5.0 vs actual 4.0 (playable by xp)
    # 2: reserve projected 1.0, 0 mins, actual 0.0 (not playable)
    # 3: sub projected 1.5, played 45 mins, actual 2.0 (playable by minutes)
    # 4: reserve projected 0.5, 0 mins, actual 0.0 (not playable)
    champ_df = pd.DataFrame(
        [
            {"player_id": 1, "gameweek": 1, "projected_points": 5.0, "actual_points": 4.0, "actual_minutes": 90},
            {"player_id": 2, "gameweek": 1, "projected_points": 1.0, "actual_points": 0.0, "actual_minutes": 0},
            {"player_id": 3, "gameweek": 1, "projected_points": 1.5, "actual_points": 2.0, "actual_minutes": 45},
            {"player_id": 4, "gameweek": 1, "projected_points": 0.5, "actual_points": 0.0, "actual_minutes": 0},
        ]
    )
    cand_df = pd.DataFrame(
        [
            {"player_id": 1, "gameweek": 1, "projected_points": 4.5, "actual_points": 4.0},
            {"player_id": 2, "gameweek": 1, "projected_points": 0.0, "actual_points": 0.0},
            {"player_id": 3, "gameweek": 1, "projected_points": 1.8, "actual_points": 2.0},
            {"player_id": 4, "gameweek": 1, "projected_points": 0.0, "actual_points": 0.0},
        ]
    )
    champ_m, cand_m = compute_playable_pool_metrics(champ_df, cand_df, target_column="actual_points")
    # Playable pool has only players 1 and 3 (2 players, not 4)
    # Champ errors: (5.0-4.0)=1.0, (1.5-2.0)=-0.5. MAE = 0.75, Bias = 0.25
    # Cand errors: (4.5-4.0)=0.5, (1.8-2.0)=-0.2. MAE = 0.35, Bias = 0.15
    assert abs(champ_m["mae"] - 0.75) < 1e-6
    assert abs(cand_m["mae"] - 0.35) < 1e-6
    assert abs(champ_m["bias"] - 0.25) < 1e-6
    assert abs(cand_m["bias"] - 0.15) < 1e-6

