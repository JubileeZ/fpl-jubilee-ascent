import pandas as pd
import pytest

from backtesting.promotion import (
    BOOTSTRAP_BLOCK_GWS,
    BOOTSTRAP_MIN_P,
    CONFIRMATION_BOOTSTRAP_MIN_P,
    POOLED_BOOTSTRAP_MIN_P,
    TwoSeasonGateVerdict,
    block_bootstrap_win_probability,
    classify_live_lead,
    compute_playable_pool_metrics,
    diagnose_guardrail_regressions,
    evaluate_historical_promotion_gate,
    evaluate_two_season_gate,
    guardrail_metrics,
    identify_active_gameweeks,
    metrics_by_season_window,
    metrics_meet_guardrails,
    pooled_block_bootstrap_win_probability,
    primary_metric_name,
    primary_metric_value,
    segment_regression_tolerance,
    stratified_block_bootstrap_win_probability,
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


def test_historical_promotion_gate_fails_on_catastrophic_segment_regression() -> None:
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
    assert any("catastrophic regression in early_mid" in r for r in verdict.reasons)
    assert any("won 0 active in-season segments" in r for r in verdict.reasons)


def test_historical_promotion_gate_tolerates_cold_start_parity_and_wins_late() -> None:
    champion_windows = {
        "combined": _metrics(mae=2.0, regret=1.0),
        "cold_start": _metrics(mae=2.0, regret=1.0),
        "early_mid": _metrics(mae=2.0, regret=1.0),
        "late": _metrics(mae=2.0, regret=1.0),
    }
    candidate_windows = {
        "combined": _metrics(mae=1.8, regret=0.8),
        "cold_start": _metrics(mae=2.0, regret=1.0),  # delta = 0.00 (fallback parity)
        "early_mid": _metrics(mae=2.0, regret=1.02),  # delta = -0.02 (>= -0.15)
        "late": _metrics(mae=1.5, regret=0.50),  # delta = +0.50 (active win)
    }

    verdict = evaluate_historical_promotion_gate(champion_windows, candidate_windows)

    assert verdict.passed
    assert verdict.segment_guardrails_passed
    assert verdict.segment_wins == 1


def test_historical_promotion_gate_tolerates_minor_cold_start_noise_within_sqrt_ns_floor() -> None:
    champion_windows = {
        "combined": _metrics(mae=2.0, regret=1.0),
        "cold_start": _metrics(mae=2.0, regret=1.0),
        "early_mid": _metrics(mae=2.0, regret=1.0),
        "late": _metrics(mae=2.0, regret=1.0),
    }
    candidate_windows = {
        "combined": _metrics(mae=1.8, regret=0.8),
        "cold_start": _metrics(mae=2.2, regret=1.20),  # delta = -0.20 (tolerated under -0.25 floor)
        "early_mid": _metrics(mae=1.7, regret=0.75),  # delta = +0.25 (active win)
        "late": _metrics(mae=1.7, regret=0.75),  # delta = +0.25 (active win)
    }

    verdict = evaluate_historical_promotion_gate(champion_windows, candidate_windows)

    assert verdict.passed
    assert verdict.segment_guardrails_passed
    assert verdict.segment_wins == 2


def test_historical_promotion_gate_fails_on_cold_start_regression() -> None:
    champion_windows = {
        "combined": _metrics(mae=2.0, regret=1.0),
        "cold_start": _metrics(mae=2.0, regret=1.0),
        "early_mid": _metrics(mae=2.0, regret=1.0),
        "late": _metrics(mae=2.0, regret=1.0),
    }
    candidate_windows = {
        "combined": _metrics(mae=1.8, regret=0.8),
        "cold_start": _metrics(mae=2.3, regret=1.30),  # delta = -0.30 (< -0.25)
        "early_mid": _metrics(mae=1.8, regret=0.90),
        "late": _metrics(mae=1.8, regret=0.90),
    }

    verdict = evaluate_historical_promotion_gate(champion_windows, candidate_windows)

    assert not verdict.passed
    assert not verdict.segment_guardrails_passed
    assert any("cold start regressed (-0.300 < -0.25)" in r for r in verdict.reasons)


def test_historical_promotion_gate_fails_on_tightened_late_segment_regression() -> None:
    champion_windows = {
        "combined": _metrics(mae=2.0, regret=1.0),
        "cold_start": _metrics(mae=2.0, regret=1.0),
        "early_mid": _metrics(mae=2.0, regret=1.0),
        "late": _metrics(mae=2.0, regret=1.0),
    }
    # -0.14 regression: passes in early_mid (tol 0.15), but fails in late (tightened tol 0.13)
    candidate_windows = {
        "combined": _metrics(mae=1.8, regret=0.8),
        "cold_start": _metrics(mae=1.9, regret=0.95),  # delta = +0.05
        "early_mid": _metrics(mae=1.6, regret=0.70),  # delta = +0.30 (active win)
        "late": _metrics(mae=2.14, regret=1.14),  # delta = -0.14 (< -0.13)
    }

    verdict = evaluate_historical_promotion_gate(champion_windows, candidate_windows)

    assert not verdict.passed
    assert not verdict.segment_guardrails_passed
    assert any("catastrophic regression in late segment (-0.140 < -0.13)" in r for r in verdict.reasons)


def test_segment_regression_tolerance_helper() -> None:
    assert segment_regression_tolerance("cold_start") == 0.25
    assert segment_regression_tolerance("early_mid") == 0.15
    assert segment_regression_tolerance("late") == 0.13
    assert segment_regression_tolerance("unknown_segment") == 0.15
    # Supports mapping lookup overrides
    assert segment_regression_tolerance("cold_start", tolerances={"cold_start": 0.10}) == 0.10


def test_historical_promotion_gate_supports_custom_segment_tolerances() -> None:
    champion_windows = {
        "combined": _metrics(mae=2.0, regret=1.0),
        "cold_start": _metrics(mae=2.0, regret=1.0),
        "early_mid": _metrics(mae=2.0, regret=1.0),
        "late": _metrics(mae=2.0, regret=1.0),
    }
    candidate_windows = {
        "combined": _metrics(mae=1.8, regret=0.8),
        "cold_start": _metrics(mae=2.2, regret=1.20),  # delta = -0.20
        "early_mid": _metrics(mae=1.6, regret=0.70),  # active win
        "late": _metrics(mae=1.8, regret=0.90),
    }

    # Stricter custom cold_start tolerance 0.10 -> should fail
    strict_verdict = evaluate_historical_promotion_gate(
        champion_windows,
        candidate_windows,
        segment_tolerances={"cold_start": 0.10, "early_mid": 0.15, "late": 0.13},
    )
    assert not strict_verdict.passed
    assert any("cold start regressed (-0.200 < -0.10)" in r for r in strict_verdict.reasons)


def test_historical_promotion_gate_fails_without_active_season_win() -> None:
    champion_windows = {
        "combined": _metrics(mae=2.0, regret=1.0),
        "cold_start": _metrics(mae=2.0, regret=1.0),
        "early_mid": _metrics(mae=2.0, regret=1.0),
        "late": _metrics(mae=2.0, regret=1.0),
    }
    candidate_windows = {
        "combined": _metrics(mae=1.8, regret=0.8),
        "cold_start": _metrics(mae=1.2, regret=0.50),  # won cold start (+0.50)
        "early_mid": _metrics(mae=2.05, regret=1.05),  # -0.05
        "late": _metrics(mae=2.05, regret=1.05),  # -0.05
    }

    verdict = evaluate_historical_promotion_gate(champion_windows, candidate_windows)

    assert not verdict.passed
    assert not verdict.segment_guardrails_passed
    assert any("won 0 active in-season segments" in r for r in verdict.reasons)


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
    deltas = [1.2, -0.8, 1.0, -1.2, 0.9, -0.4, 0.8, -0.6, 1.1, 0.5]

    dev = evaluate_historical_promotion_gate(champion, candidate, gw_primary_deltas=deltas)
    confirm = evaluate_historical_promotion_gate(
        champion, candidate, gw_primary_deltas=deltas, bootstrap_min_p=CONFIRMATION_BOOTSTRAP_MIN_P
    )

    assert BOOTSTRAP_MIN_P == 0.75
    assert CONFIRMATION_BOOTSTRAP_MIN_P == 0.65
    assert POOLED_BOOTSTRAP_MIN_P == 0.85
    assert BOOTSTRAP_BLOCK_GWS == 5
    assert dev.bootstrap_p is not None and BOOTSTRAP_MIN_P <= dev.bootstrap_p < 0.95
    assert dev.passed
    assert confirm.passed


def test_non_wrapping_block_bootstrap_never_wraps_around_gw38() -> None:
    """Verify that start indices are strictly bounded to 0 <= s <= n - L so no indices wrap."""
    import numpy as np

    n = 38
    block = 5
    size = min(block, n)
    k = -(-n // size)
    num_starts = n - size + 1
    starts = np.random.default_rng(42).integers(0, num_starts, size=(5000, k))
    idx = (starts[:, :, None] + np.arange(size)).reshape(5000, -1)

    assert starts.min() >= 0
    assert starts.max() <= n - block
    assert idx.min() >= 0
    assert idx.max() == n - 1  # Exactly 37 for n=38, never >= 38
    # Within every contiguous block of length 5, indices must be strictly increasing by 1
    blocks = idx.reshape(5000, k, block)
    diffs = np.diff(blocks, axis=2)
    assert np.all(diffs == 1)  # Never negative or wrapping around


def test_bootstrap_active_window_isolation_prevents_dormant_dilution() -> None:
    """Verify that when a candidate has dormant weeks, bootstrap isolates to active gameweeks."""
    champion, candidate = _clear_winner_windows()
    # 19 dormant weeks (zeros) + 19 active weeks (mean ~ +0.5)
    dormant_deltas = [0.0] * 19
    active_deltas = [0.8, 0.4, 0.9, -0.2, 0.7, 0.6, 0.3, -0.4, 0.8, 0.5, 0.4, 0.6, -0.1, 0.7, 0.5, 0.6, 0.2, 0.5, 0.7]
    full_deltas = dormant_deltas + active_deltas
    active_gws = list(range(20, 39))

    # Evaluate with active_gameweeks specified
    verdict = evaluate_historical_promotion_gate(
        champion,
        candidate,
        gw_primary_deltas=full_deltas,
        active_gameweeks=active_gws,
    )
    # Compare with standalone active bootstrap
    expected_p = block_bootstrap_win_probability(active_deltas)
    assert verdict.bootstrap_p == pytest.approx(expected_p, abs=1e-6)
    assert verdict.bootstrap_p >= BOOTSTRAP_MIN_P


def test_stratified_block_bootstrap_and_two_season_gate() -> None:
    """Verify pooled multi-season stratified bootstrap and evaluate_two_season_gate."""
    champion, candidate = _clear_winner_windows()

    dev_deltas = [1.2, -0.8, 1.0, -1.2, 0.9, -0.4, 0.8, -0.6, 1.1, 0.5]
    conf_deltas = [1.0, -0.5, 0.8, -0.9, 0.7, -0.3, 0.6, -0.4, 0.9, 0.4]

    dev_verdict = evaluate_historical_promotion_gate(
        champion, candidate, gw_primary_deltas=dev_deltas, bootstrap_min_p=BOOTSTRAP_MIN_P
    )
    conf_verdict = evaluate_historical_promotion_gate(
        champion, candidate, gw_primary_deltas=conf_deltas, bootstrap_min_p=CONFIRMATION_BOOTSTRAP_MIN_P
    )

    pooled_p = stratified_block_bootstrap_win_probability([dev_deltas, conf_deltas])
    alias_p = pooled_block_bootstrap_win_probability([dev_deltas, conf_deltas])
    assert pooled_p == alias_p
    assert pooled_p >= POOLED_BOOTSTRAP_MIN_P

    two_season_verdict = evaluate_two_season_gate(
        dev_verdict,
        conf_verdict,
        dev_gw_deltas=dev_deltas,
        conf_gw_deltas=conf_deltas,
    )
    assert isinstance(two_season_verdict, TwoSeasonGateVerdict)
    assert two_season_verdict.passed
    assert two_season_verdict.pooled_bootstrap_p == pooled_p
    assert len(two_season_verdict.reasons) == 0

    # Negative confirmation season fails two-season gate
    bad_conf_deltas = [-1.0, -0.8, -1.2, -0.5, -0.9, -0.4, -0.8, -0.6, -1.1, -0.5]
    bad_conf_verdict = evaluate_historical_promotion_gate(
        champion, candidate, gw_primary_deltas=bad_conf_deltas, bootstrap_min_p=CONFIRMATION_BOOTSTRAP_MIN_P
    )
    failing_two_season = evaluate_two_season_gate(
        dev_verdict,
        bad_conf_verdict,
        dev_gw_deltas=dev_deltas,
        conf_gw_deltas=bad_conf_deltas,
    )
    assert not failing_two_season.passed
    assert any("confirmation season failed" in r for r in failing_two_season.reasons)
    assert any("pooled stratified" in r for r in failing_two_season.reasons)


def test_evaluate_two_season_gate_filters_active_gameweeks() -> None:
    """Verify evaluate_two_season_gate isolates active gameweeks before pooled stratified bootstrap."""
    champion, candidate = _clear_winner_windows()
    dormant = [0.0] * 19
    dev_active = [0.8, 0.4, 0.9, -0.2, 0.7, 0.6, 0.3, -0.4, 0.8, 0.5, 0.4, 0.6, -0.1, 0.7, 0.5, 0.6, 0.2, 0.5, 0.7]
    conf_active = [0.7, 0.3, 0.8, -0.3, 0.6, 0.5, 0.2, -0.3, 0.7, 0.4, 0.3, 0.5, -0.2, 0.6, 0.4, 0.5, 0.3, 0.4, 0.6]
    dev_full = dormant + dev_active
    conf_full = dormant + conf_active
    active_gws = list(range(20, 39))

    dev_verdict = evaluate_historical_promotion_gate(
        champion, candidate, gw_primary_deltas=dev_full, active_gameweeks=active_gws
    )
    conf_verdict = evaluate_historical_promotion_gate(
        champion,
        candidate,
        gw_primary_deltas=conf_full,
        active_gameweeks=active_gws,
        bootstrap_min_p=CONFIRMATION_BOOTSTRAP_MIN_P,
    )

    two_season = evaluate_two_season_gate(
        dev_verdict,
        conf_verdict,
        dev_gw_deltas=dev_full,
        conf_gw_deltas=conf_full,
        dev_active_gameweeks=active_gws,
        conf_active_gameweeks=active_gws,
    )
    expected_pooled = stratified_block_bootstrap_win_probability([dev_active, conf_active])
    assert two_season.pooled_bootstrap_p == pytest.approx(expected_pooled, abs=1e-6)
    assert two_season.passed


def test_filter_active_gw_deltas_handles_offset_and_all_gameweeks() -> None:
    from backtesting.promotion import _filter_active_gw_deltas

    # Case 1: 1-indexed full season deltas (e.g. GW 1 to 6)
    deltas_full = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    active_gws = [2, 4]
    assert _filter_active_gw_deltas(deltas_full, active_gameweeks=active_gws) == [2.0, 4.0]

    # Case 2: Partial gameweek slice GW 10 to 15 (length 6) with all_gameweeks
    deltas_partial = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    all_gws = [10, 11, 12, 13, 14, 15]
    active_gws_partial = [12, 14]
    filtered_explicit = _filter_active_gw_deltas(
        deltas_partial, active_gameweeks=active_gws_partial, all_gameweeks=all_gws
    )
    assert filtered_explicit == [3.0, 5.0]

    # Case 3: Explicit active_gw_deltas takes priority
    explicit_active = [9.9]
    assert _filter_active_gw_deltas(
        deltas_partial, active_gameweeks=active_gws_partial, active_gw_deltas=explicit_active
    ) == [9.9]



def test_guardrails_tolerate_noise_but_not_real_regression() -> None:
    champion = guardrail_metrics(_metrics(mae=2.0, bias=0.10, xmins_mae=14.0, spearman=0.69))
    within = guardrail_metrics(_metrics(mae=2.0, bias=0.105, xmins_mae=14.1, spearman=0.687))
    outside = guardrail_metrics(_metrics(mae=2.0, bias=0.10, xmins_mae=14.3, spearman=0.69))

    assert metrics_meet_guardrails(within, champion)
    assert not metrics_meet_guardrails(outside, champion)


def test_block_bootstrap_is_deterministic_and_bounded() -> None:
    deltas = [-1.0, 0.5, 0.8, -0.2, -0.5, 0.4, 0.6, -0.8]
    first = block_bootstrap_win_probability(deltas)

    assert first == block_bootstrap_win_probability(deltas)
    assert 0.0 < first < 1.0
    assert block_bootstrap_win_probability([]) == 0.0
    assert block_bootstrap_win_probability([float("nan")]) == 0.0
    assert block_bootstrap_win_probability([1.0, float("nan"), 1.5, 0.8, -0.2, 0.5]) > 0.0
    assert stratified_block_bootstrap_win_probability([[float("nan")], []]) == 0.0


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


def test_squad_churn_guardrail() -> None:
    from backtesting.promotion import CHURN_GUARDRAIL_TOL

    champ_metrics = _metrics(mae=2.0, bias=0.1)
    champ_metrics["top_15_squad_churn"] = 1.20

    # Within tolerance (+0.50 players/GW) passes
    cand_ok = _metrics(mae=1.8, bias=0.1)
    cand_ok["top_15_squad_churn"] = 1.20 + CHURN_GUARDRAIL_TOL
    g_champ = guardrail_metrics(champ_metrics)
    g_ok = guardrail_metrics(cand_ok)
    assert metrics_meet_guardrails(g_ok, g_champ)

    # Beyond tolerance (> +0.50) fails
    cand_fail = _metrics(mae=1.8, bias=0.1)
    cand_fail["top_15_squad_churn"] = 1.20 + CHURN_GUARDRAIL_TOL + 0.10
    g_fail = guardrail_metrics(cand_fail)
    assert not metrics_meet_guardrails(g_fail, g_champ)


def test_playable_pool_exogeneity_invariance() -> None:
    """Verify Playable Pool mask is model-independent, row counts match bit-for-bit (ADR 0064)."""
    # 2 gameweeks, 4 players each
    champ_df = pd.DataFrame(
        [
            {"player_id": 1, "gameweek": 1, "projected_points": 5.0, "actual_points": 4.0, "actual_minutes": 90},
            {"player_id": 2, "gameweek": 1, "projected_points": 0.5, "actual_points": 0.0, "actual_minutes": 0},
            {"player_id": 3, "gameweek": 1, "projected_points": 1.0, "actual_points": 2.0, "actual_minutes": 45},
            {"player_id": 4, "gameweek": 1, "projected_points": 0.2, "actual_points": 0.0, "actual_minutes": 0},
            {"player_id": 1, "gameweek": 2, "projected_points": 5.5, "actual_points": 6.0, "actual_minutes": 90},
            {"player_id": 2, "gameweek": 2, "projected_points": 0.3, "actual_points": 0.0, "actual_minutes": 0},
            {"player_id": 3, "gameweek": 2, "projected_points": 2.5, "actual_points": 1.0, "actual_minutes": 60},
            {"player_id": 4, "gameweek": 2, "projected_points": 0.1, "actual_points": 0.0, "actual_minutes": 0},
        ]
    )
    # Candidate A: conservative 0.0 on reserve player 2
    cand_a_df = pd.DataFrame(
        [
            {"player_id": 1, "gameweek": 1, "projected_points": 4.5, "actual_points": 4.0},
            {"player_id": 2, "gameweek": 1, "projected_points": 0.0, "actual_points": 0.0},
            {"player_id": 3, "gameweek": 1, "projected_points": 1.2, "actual_points": 2.0},
            {"player_id": 4, "gameweek": 1, "projected_points": 0.0, "actual_points": 0.0},
            {"player_id": 1, "gameweek": 2, "projected_points": 5.0, "actual_points": 6.0},
            {"player_id": 2, "gameweek": 2, "projected_points": 0.0, "actual_points": 0.0},
            {"player_id": 3, "gameweek": 2, "projected_points": 2.2, "actual_points": 1.0},
            {"player_id": 4, "gameweek": 2, "projected_points": 0.0, "actual_points": 0.0},
        ]
    )
    # Candidate B: speculative 4.8 on reserve player 2 (0 mins) in both GWs
    cand_b_df = pd.DataFrame(
        [
            {"player_id": 1, "gameweek": 1, "projected_points": 4.5, "actual_points": 4.0},
            {"player_id": 2, "gameweek": 1, "projected_points": 4.8, "actual_points": 0.0},
            {"player_id": 3, "gameweek": 1, "projected_points": 1.2, "actual_points": 2.0},
            {"player_id": 4, "gameweek": 1, "projected_points": 0.0, "actual_points": 0.0},
            {"player_id": 1, "gameweek": 2, "projected_points": 5.0, "actual_points": 6.0},
            {"player_id": 2, "gameweek": 2, "projected_points": 4.8, "actual_points": 0.0},
            {"player_id": 3, "gameweek": 2, "projected_points": 2.2, "actual_points": 1.0},
            {"player_id": 4, "gameweek": 2, "projected_points": 0.0, "actual_points": 0.0},
        ]
    )

    champ_m_a, cand_m_a = compute_playable_pool_metrics(champ_df, cand_a_df, target_column="actual_points")
    champ_m_b, cand_m_b = compute_playable_pool_metrics(champ_df, cand_b_df, target_column="actual_points")

    # Row counts must be identical across all candidates and equal exactly 4 (players 1 and 3 in GW1 & GW2)
    assert champ_m_a["sample_count"] == 4
    assert champ_m_b["sample_count"] == 4
    assert cand_m_a["sample_count"] == 4
    assert cand_m_b["sample_count"] == 4

    # Champion playable metrics must be bit-for-bit identical regardless of Candidate B's speculative projection
    assert champ_m_a["mae"] == champ_m_b["mae"]
    assert champ_m_a["bias"] == champ_m_b["bias"]

    # Candidate metrics are also identical because player 2 is excluded by the exogenous mask
    assert cand_m_a["mae"] == cand_m_b["mae"]
    assert cand_m_a["bias"] == cand_m_b["bias"]


def test_identify_active_gameweeks() -> None:
    """Test identification of active gameweeks G_active where candidate diverges from champion."""
    champ_df = pd.DataFrame(
        [
            {"player_id": 1, "gameweek": 1, "projected_points": 3.0},
            {"player_id": 2, "gameweek": 1, "projected_points": 4.0},
            {"player_id": 1, "gameweek": 2, "projected_points": 3.0},
            {"player_id": 2, "gameweek": 2, "projected_points": 4.0},
            {"player_id": 1, "gameweek": 3, "projected_points": 3.0},
            {"player_id": 2, "gameweek": 3, "projected_points": 4.0},
        ]
    )
    # Candidate identical in GW1 & GW2, differs in GW3
    cand_df = pd.DataFrame(
        [
            {"player_id": 1, "gameweek": 1, "projected_points": 3.0},
            {"player_id": 2, "gameweek": 1, "projected_points": 4.0},
            {"player_id": 1, "gameweek": 2, "projected_points": 3.00000001},  # diff < 1e-6
            {"player_id": 2, "gameweek": 2, "projected_points": 4.0},
            {"player_id": 1, "gameweek": 3, "projected_points": 3.5},  # diff 0.5 > 1e-6
            {"player_id": 2, "gameweek": 3, "projected_points": 4.0},
        ]
    )

    active_gws = identify_active_gameweeks(champ_df, cand_df)
    assert active_gws == [3]


def test_active_window_guardrail_catches_dormant_fallback_dilution() -> None:
    """Verify dual-window guardrail catches regressions diluted across dormant fallback weeks."""
    champion_windows = {
        "combined": _metrics(mae=2.0, regret=1.0),
        "cold_start": _metrics(mae=2.0, regret=1.0),
        "early_mid": _metrics(mae=2.0, regret=1.0),
        "late": _metrics(mae=2.0, regret=1.0),
        "active": _metrics(mae=2.0, regret=1.0),
    }
    champion_windows["combined"]["captain_regret"] = 1.00
    champion_windows["active"]["captain_regret"] = 1.00

    # In full season combined: candidate captain regret is 1.125 (delta +0.125 <= 0.15 tolerance -> would pass full-season)
    # In active window: candidate captain regret is 1.250 (delta +0.250 > 0.15 tolerance -> must fail!)
    candidate_windows = {
        "combined": _metrics(mae=1.8, regret=0.90),
        "cold_start": _metrics(mae=2.0, regret=1.0),
        "early_mid": _metrics(mae=2.0, regret=1.0),
        "late": _metrics(mae=1.7, regret=0.85),
        "active": _metrics(mae=1.7, regret=0.85),
    }
    candidate_windows["combined"]["captain_regret"] = 1.125
    candidate_windows["active"]["captain_regret"] = 1.250

    verdict = evaluate_historical_promotion_gate(champion_windows, candidate_windows)
    assert not verdict.passed
    assert not verdict.guardrails_passed
    assert not verdict.active_guardrails_passed
    assert any("failed one or more active-window Champion guardrails" in r for r in verdict.reasons)
    assert any("regressed active-window Captaincy Regret guardrail" in r for r in verdict.reasons)


def test_active_window_guardrail_passes_when_active_window_improves() -> None:
    """Verify dual-window guardrail passes when active window improves."""
    champion_windows = {
        "combined": _metrics(mae=2.0, regret=1.0),
        "cold_start": _metrics(mae=2.0, regret=1.0),
        "early_mid": _metrics(mae=2.0, regret=1.0),
        "late": _metrics(mae=2.0, regret=1.0),
        "active": _metrics(mae=2.0, regret=1.0),
    }
    champion_windows["combined"]["captain_regret"] = 1.00
    champion_windows["active"]["captain_regret"] = 1.00

    candidate_windows = {
        "combined": _metrics(mae=1.8, regret=0.90),
        "cold_start": _metrics(mae=2.0, regret=1.0),
        "early_mid": _metrics(mae=2.0, regret=1.0),
        "late": _metrics(mae=1.7, regret=0.80),
        "active": _metrics(mae=1.7, regret=0.80),
    }
    candidate_windows["combined"]["captain_regret"] = 0.95
    candidate_windows["active"]["captain_regret"] = 0.95

    verdict = evaluate_historical_promotion_gate(champion_windows, candidate_windows)
    assert verdict.passed
    assert verdict.guardrails_passed
    assert verdict.active_guardrails_passed


def test_diagnose_guardrail_regressions_emits_clear_messages() -> None:
    """Verify diagnose_guardrail_regressions formats window-aware violation reasons."""
    champ = guardrail_metrics(_metrics(mae=2.0, bias=0.05, xmins_mae=10.0, spearman=0.5))
    cand_regressed = guardrail_metrics(_metrics(mae=2.0, bias=0.20, xmins_mae=12.0, spearman=0.3))

    reasons = diagnose_guardrail_regressions(cand_regressed, champ, window_label="active-window")
    assert any("regressed active-window xMins MAE guardrail" in r for r in reasons)
    assert any("regressed active-window XP Bias guardrail" in r for r in reasons)
    assert any("regressed active-window Rank Correlation guardrail" in r for r in reasons)


def test_evaluate_oracle_event_gate() -> None:
    from backtesting.promotion import evaluate_oracle_event_gate

    champ_metrics = {
        "oracle_formation_xi_regret": 15.0,
        "oracle_captain_regret": 4.0,
        "playable_bias": 0.05,
    }
    cand_metrics_pass = {
        "oracle_formation_xi_regret": 14.5,
        "oracle_captain_regret": 4.05,
        "playable_bias": 0.06,
    }
    # 20 GW deltas with consistent improvement
    gw_deltas_good = [0.5] * 20
    verdict_pass = evaluate_oracle_event_gate(champ_metrics, cand_metrics_pass, gw_deltas=gw_deltas_good)
    assert verdict_pass.passed
    assert verdict_pass.oracle_delta == pytest.approx(0.5)
    assert verdict_pass.bootstrap_p == pytest.approx(1.0)
    assert verdict_pass.reasons == ()

    # Fails when oracle regret did not improve
    cand_metrics_fail_delta = {
        "oracle_formation_xi_regret": 15.5,
        "oracle_captain_regret": 4.0,
        "playable_bias": 0.05,
    }
    verdict_fail_delta = evaluate_oracle_event_gate(champ_metrics, cand_metrics_fail_delta)
    assert not verdict_fail_delta.passed
    assert any("oracle formation XI regret did not improve" in r for r in verdict_fail_delta.reasons)

    # Fails when bias exceeds tolerance (|cand_bias| > min(|champ_bias| + 0.02, 0.20))
    cand_metrics_fail_bias = {
        "oracle_formation_xi_regret": 14.0,
        "oracle_captain_regret": 4.0,
        "playable_bias": 0.15,
    }
    verdict_fail_bias = evaluate_oracle_event_gate(champ_metrics, cand_metrics_fail_bias)
    assert not verdict_fail_bias.passed
    assert any("playable pool signed bias" in r for r in verdict_fail_bias.reasons)

    # Fails when captaincy regret regresses by > 0.15
    cand_metrics_fail_cap = {
        "oracle_formation_xi_regret": 14.0,
        "oracle_captain_regret": 4.30,
        "playable_bias": 0.05,
    }
    verdict_fail_cap = evaluate_oracle_event_gate(champ_metrics, cand_metrics_fail_cap)
    assert not verdict_fail_cap.passed
    assert any("captaincy regret regressed" in r for r in verdict_fail_cap.reasons)





