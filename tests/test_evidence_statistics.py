"""Unit tests for Phase 8 numerical and statistical protocol."""

import numpy as np
import pytest

from backtesting.evidence_statistics import (
    PairedGameweekScore,
    StatisticalProtocolConfig,
    assign_gameweek_segment,
    compute_season_summaries,
    evaluate_evidence_against_protocol,
    resample_paired_blocks,
    run_stored_score_bootstrap,
    simulate_bootstrap_calibration,
)
from backtesting.projection_guards import GuardOutput


def _make_paired_scores(
    season: str = "2024-25",
    gameweek_count: int = 38,
    mean_cand: float = 60.0,
    mean_champ: float = 58.0,
    noise_std: float = 1.0,
    seed: int = 42,
) -> list[PairedGameweekScore]:
    """Helper to generate reproducible paired gameweek scores."""
    rng = np.random.default_rng(seed)
    scores: list[PairedGameweekScore] = []
    for gw in range(1, gameweek_count + 1):
        noise = float(rng.normal(0.0, noise_std))
        cand_net = mean_cand + noise
        champ_net = mean_champ
        scores.append(
            PairedGameweekScore(
                season=season,
                gameweek=gw,
                candidate_net_points=cand_net,
                champion_net_points=champ_net,
                candidate_gross_points=cand_net,
                champion_gross_points=champ_net,
                candidate_hits_deducted=0,
                champion_hits_deducted=0,
                segment=assign_gameweek_segment(gw),
            )
        )
    return scores


def test_paired_score_properties_and_segments() -> None:
    """Verify PairedGameweekScore properties and segment mapping."""
    score = PairedGameweekScore(
        season="2024-25",
        gameweek=3,
        candidate_net_points=65.0,
        champion_net_points=60.0,
        candidate_gross_points=69.0,
        champion_gross_points=60.0,
        candidate_hits_deducted=4,
        champion_hits_deducted=0,
        segment=assign_gameweek_segment(3),
    )
    assert score.delta_net == 5.0
    assert score.delta_gross == 9.0
    assert score.delta_hits == 4
    assert score.segment == "cold_start"

    assert assign_gameweek_segment(1) == "cold_start"
    assert assign_gameweek_segment(4) == "cold_start"
    assert assign_gameweek_segment(5) == "early_mid"
    assert assign_gameweek_segment(19) == "early_mid"
    assert assign_gameweek_segment(20) == "late"
    assert assign_gameweek_segment(38) == "late"


def test_season_summaries_and_material_loss() -> None:
    """Verify seasonal aggregation and material harm limit detection."""
    scores_s1 = _make_paired_scores(season="2023-24", gameweek_count=38, mean_cand=50.0, mean_champ=50.5, noise_std=0.0)
    scores_s2 = _make_paired_scores(season="2024-25", gameweek_count=38, mean_cand=60.0, mean_champ=59.0, noise_std=0.0)

    # In 2023-24: net delta = 38 * -0.5 = -19.0. Material limit = 10.0 => violates!
    # In 2024-25: net delta = 38 * +1.0 = +38.0.
    summaries = compute_season_summaries(
        scores_s1 + scores_s2,
        season_material_loss_limit=10.0,
        segment_material_loss_limit=6.0,
    )
    assert len(summaries) == 2
    s1, s2 = summaries
    assert s1.season == "2023-24"
    assert s1.net_delta == -19.0
    assert s1.violates_material_loss is True

    assert s2.season == "2024-25"
    assert s2.net_delta == 38.0
    assert s2.violates_material_loss is False


def test_resample_paired_blocks_bounds_and_alignment() -> None:
    """Verify non-wrapping moving block bootstrap preserves length and pairing."""
    scores = _make_paired_scores(gameweek_count=38)
    rng = np.random.default_rng(123)

    resampled = resample_paired_blocks(scores, block_size=5, rng=rng)
    assert len(resampled) == 38
    # All resampled values must originate from the observed scores
    observed_deltas = {s.delta_net for s in scores}
    assert all(val in observed_deltas for val in resampled)


def test_stored_score_bootstrap_superiority() -> None:
    """Verify stored-score bootstrap detects clear superiority with positive lower bound."""
    scores = _make_paired_scores(gameweek_count=38, mean_cand=62.0, mean_champ=60.0, noise_std=0.5)
    config = StatisticalProtocolConfig(
        nominal_alpha=0.05,
        bootstrap_draws=2_000,
        bootstrap_block_size=5,
        family_error_control="none",
    )

    res = run_stored_score_bootstrap(scores, config, seed=42)
    assert res.point_estimate > 1.8
    assert res.confidence_interval[0] > 1.0  # Lower CI strictly positive
    assert res.p_value_superiority == 0.0


def test_family_wise_error_control_adjustments() -> None:
    """Verify Bonferroni and Holm error budget scaling across comparison family attempts."""
    config_bonf = StatisticalProtocolConfig(
        nominal_alpha=0.05,
        family_error_control="bonferroni",
        max_family_attempts=10,
        bootstrap_draws=100,
    )
    scores = _make_paired_scores(gameweek_count=10)
    res_bonf = run_stored_score_bootstrap(scores, config_bonf, attempt_number=1)
    assert res_bonf.adjusted_alpha == pytest.approx(0.005)

    config_holm = StatisticalProtocolConfig(
        nominal_alpha=0.05,
        family_error_control="holm",
        max_family_attempts=10,
        bootstrap_draws=100,
    )
    res_holm1 = run_stored_score_bootstrap(scores, config_holm, attempt_number=1)
    assert res_holm1.adjusted_alpha == pytest.approx(0.05 / 10)

    res_holm5 = run_stored_score_bootstrap(scores, config_holm, attempt_number=5)
    assert res_holm5.adjusted_alpha == pytest.approx(0.05 / 6)


def test_protocol_hash_determinism_and_sensitivity() -> None:
    """Verify protocol digest is deterministic and sensitive to configuration changes."""
    cfg1 = StatisticalProtocolConfig(nominal_alpha=0.05, season_material_loss_limit=10.0)
    cfg2 = StatisticalProtocolConfig(nominal_alpha=0.05, season_material_loss_limit=10.0)
    cfg3 = StatisticalProtocolConfig(nominal_alpha=0.01, season_material_loss_limit=10.0)

    h1 = cfg1.compute_hash()
    h2 = cfg2.compute_hash()
    h3 = cfg3.compute_hash()

    assert len(h1) == 64
    assert h1 == h2
    assert h1 != h3


def test_evidence_evaluation_pass_verdict() -> None:
    """Verify PASS verdict requires positive CI, confirmation season, green guards, and human approval."""
    scores = _make_paired_scores(gameweek_count=38, mean_cand=63.0, mean_champ=60.0, noise_std=0.5)
    config = StatisticalProtocolConfig(
        nominal_alpha=0.05,
        bootstrap_draws=1_000,
        family_error_control="none",
        approved_by_human=True,
    )
    guard = GuardOutput(
        metric_name="minutes_mae",
        passed=True,
        status="PASS",
        estimate=-0.5,
        margin=1.0,
        standard_error=0.1,
        ci_lower=-0.7,
        ci_upper=-0.3,
        coverage=1.0,
        sample_size=100,
        direction="lower_is_better",
        reason="Non-inferior",
    )

    eval_res = evaluate_evidence_against_protocol(
        scores,
        [guard],
        config,
        is_confirmation_available=True,
    )

    assert eval_res.verdict == "pass"
    assert eval_res.point_estimate > 2.5
    assert eval_res.confidence_interval[0] > 0.0
    assert eval_res.projection_guards_passed is True
    assert eval_res.material_loss_violated is False


def test_evidence_evaluation_unapproved_protocol_yields_inconclusive() -> None:
    """Verify unapproved protocol yields INCONCLUSIVE even with winning evidence."""
    scores = _make_paired_scores(gameweek_count=38, mean_cand=63.0, mean_champ=60.0, noise_std=0.5)
    config = StatisticalProtocolConfig(
        nominal_alpha=0.05,
        bootstrap_draws=1_000,
        family_error_control="none",
        approved_by_human=False,
    )
    eval_res = evaluate_evidence_against_protocol(
        scores,
        None,
        config,
        is_confirmation_available=True,
    )
    assert eval_res.verdict == "inconclusive"
    assert any("approved by human" in r for r in eval_res.reasons)


def test_evidence_evaluation_inconclusive_wide_uncertainty() -> None:
    """Verify positive point estimate with wide uncertainty containing zero yields INCONCLUSIVE."""
    # Mean cand is slightly higher (+0.1 pts/GW) but noise (std=2.0) ensures CI spans zero
    scores = _make_paired_scores(gameweek_count=38, mean_cand=60.1, mean_champ=60.0, noise_std=2.0, seed=42)
    config = StatisticalProtocolConfig(
        nominal_alpha=0.05,
        bootstrap_draws=1_000,
        family_error_control="none",
    )

    eval_res = evaluate_evidence_against_protocol(
        scores,
        None,
        config,
        is_confirmation_available=True,
    )

    assert eval_res.verdict == "inconclusive"
    assert any("Uncertainty contains zero" in r for r in eval_res.reasons)


def test_evidence_evaluation_inconclusive_development_only() -> None:
    """Verify strong positive gain yields INCONCLUSIVE when confirmation season is unavailable."""
    scores = _make_paired_scores(gameweek_count=38, mean_cand=65.0, mean_champ=60.0, noise_std=0.5)
    config = StatisticalProtocolConfig(
        nominal_alpha=0.05,
        bootstrap_draws=1_000,
        family_error_control="none",
    )

    eval_res = evaluate_evidence_against_protocol(
        scores,
        None,
        config,
        is_confirmation_available=False,
    )

    assert eval_res.verdict == "inconclusive"
    assert any("Confirmation season evidence not yet admitted" in r for r in eval_res.reasons)


def test_evidence_evaluation_fail_on_material_loss() -> None:
    """Verify FAIL verdict triggered when seasonal net loss exceeds material loss threshold."""
    scores = _make_paired_scores(gameweek_count=38, mean_cand=58.0, mean_champ=60.0, noise_std=0.0)
    config = StatisticalProtocolConfig(
        season_material_loss_limit=10.0,
        bootstrap_draws=500,
        family_error_control="none",
    )

    eval_res = evaluate_evidence_against_protocol(scores, None, config)
    assert eval_res.verdict == "fail"
    assert eval_res.material_loss_violated is True
    assert any("material limit" in r for r in eval_res.reasons)


def test_evidence_evaluation_fail_on_projection_guard() -> None:
    """Verify FAIL verdict triggered when required projection guard fails."""
    scores = _make_paired_scores(gameweek_count=38, mean_cand=65.0, mean_champ=60.0, noise_std=0.5)
    config = StatisticalProtocolConfig(bootstrap_draws=500, family_error_control="none")
    failed_guard = GuardOutput(
        metric_name="minutes_mae",
        passed=False,
        status="FAIL",
        estimate=2.5,
        margin=1.0,
        standard_error=0.2,
        ci_lower=2.1,
        ci_upper=2.9,
        coverage=1.0,
        sample_size=100,
        direction="lower_is_better",
        reason="Candidate playing time error significantly regressed",
    )

    eval_res = evaluate_evidence_against_protocol(
        scores,
        [failed_guard],
        config,
        is_confirmation_available=True,
    )
    assert eval_res.verdict == "fail"
    assert eval_res.projection_guards_passed is False
    assert any("playing time error significantly regressed" in r for r in eval_res.reasons)


def test_evidence_evaluation_invalid_on_empty_input() -> None:
    """Verify INVALID verdict when score data is empty."""
    config = StatisticalProtocolConfig()
    eval_res = evaluate_evidence_against_protocol([], None, config)
    assert eval_res.verdict == "invalid"
    assert any("empty" in r for r in eval_res.reasons)


def test_simulation_calibration_diagnostic() -> None:
    """Verify simulation calibration diagnostic computes empirical coverage."""
    config = StatisticalProtocolConfig(
        nominal_alpha=0.10,
        bootstrap_draws=200,
        bootstrap_block_size=4,
        family_error_control="none",
    )
    res = simulate_bootstrap_calibration(
        true_delta_mean=0.0,
        std_dev=2.0,
        autocorrelation=0.2,
        num_gameweeks=38,
        num_simulations=10,
        config=config,
        seed=101,
    )
    assert res["num_simulations"] == 10.0
    assert 0.0 <= res["empirical_coverage"] <= 1.0
    assert 0.0 <= res["empirical_rejection_rate"] <= 1.0
