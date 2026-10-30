"""Unit tests for substantive projection guards, component reconciliation, and staged diagnostics."""

import numpy as np
import pandas as pd
import pytest

from backtesting.projection_guards import (
    CANONICAL_METRICS,
    ComponentLedger,
    EvaluationHorizonConfig,
    MetricDirection,
    declare_component_applicability,
    diagnose_unconstrained_reversal,
    evaluate_composite_non_inferiority,
    evaluate_non_inferiority_guard,
    evaluate_oracle_minutes_mechanism,
    evaluate_prioritization_screen,
    extract_evaluation_population,
    reconcile_total_to_ledger,
)


def test_durable_metric_definitions_registry() -> None:
    """Verify durable canonical metric definitions (formula, units, direction, benchmark)."""
    assert "points_mse" in CANONICAL_METRICS
    assert "points_rmse" in CANONICAL_METRICS
    assert "points_bias" in CANONICAL_METRICS
    assert "minutes_mae" in CANONICAL_METRICS
    assert "goals_mse" in CANONICAL_METRICS
    assert "clean_sheets_brier" in CANONICAL_METRICS
    assert "goals_conceded_mse" in CANONICAL_METRICS
    assert "saves_mse" in CANONICAL_METRICS

    mse_def = CANONICAL_METRICS["points_mse"]
    assert mse_def.direction == "lower_is_better"
    assert mse_def.ideal_benchmark == 0.0
    assert mse_def.units == "points^2"
    assert "mean((xp - actual_points)^2)" in mse_def.formula

    bias_def = CANONICAL_METRICS["points_bias"]
    assert bias_def.direction == "zero_is_ideal"


def test_evaluation_horizon_config() -> None:
    """Verify standardized multi-period evaluation horizon leads and weights."""
    cfg = EvaluationHorizonConfig()
    assert cfg.leads == (1, 2, 3, 4, 5, 6)
    assert len(cfg.weights) == 6
    assert cfg.weights[0] == 1.0
    assert cfg.weights[1] == 0.84
    assert cfg.missingness_policy == "fail_closed"


def test_common_evaluation_population_invariance() -> None:
    """Verify common evaluation population mask invariance (playable pool and starters)."""
    df = pd.DataFrame([
        {"player_id": 1, "xmins": 90.0, "xp": 6.5, "now_cost": 85},
        {"player_id": 2, "xmins": 15.0, "xp": 1.2, "now_cost": 45},  # Non-playable
        {"player_id": 3, "xmins": 45.0, "xp": 3.0, "now_cost": 55},  # Playable by xmins >= 30
        {"player_id": 4, "xmins": 0.0, "xp": 0.5, "now_cost": 40},   # Non-playable
    ])

    playable = extract_evaluation_population(df, population="playable_pool", min_xmins=30.0, min_xp=2.0)
    assert set(playable["player_id"]) == {1, 3}

    # All players
    all_p = extract_evaluation_population(df, population="all_players")
    assert len(all_p) == 4


def test_season_component_applicability_declaration() -> None:
    """Verify season/component applicability distinguishes native rules and unavailable measurements."""
    decl_23 = declare_component_applicability("2023-24")
    assert decl_23.component_statuses["goals"] == "applicable"
    assert decl_23.component_statuses["clean_sheets"] == "applicable"
    assert decl_23.component_statuses["defensive_contributions"] == "inapplicable_season"
    assert "defensive_contributions" in decl_23.unsupported_components

    decl_25 = declare_component_applicability("2025-26")
    assert decl_25.component_statuses["defensive_contributions"] == "applicable"
    assert "defensive_contributions" in decl_25.required_components

    # Explicitly unavailable measurement in dataset
    available_subset = {"minutes", "goals", "assists", "clean_sheets"}
    decl_subset = declare_component_applicability("2024-25", available_measurements=available_subset)
    assert decl_subset.component_statuses["goals"] == "applicable"
    assert decl_subset.component_statuses["saves"] == "unavailable_measurement"


def test_ledger_reconciliation_exact_and_native_rules() -> None:
    """Verify that reconciling total points against native components succeeds under valid semantics."""
    # Midfielder playing 90 mins, scoring 0.5 goals, 0.2 assists, 0.3 clean sheets
    # Expected points: 2 (mins) + 0.5 * 5 (goals) + 0.2 * 3 (assists) + 0.3 * 1 (CS) = 2 + 2.5 + 0.6 + 0.3 = 5.4 pts
    ledger = ComponentLedger(
        minutes=90.0,
        goals=0.5,
        assists=0.2,
        clean_sheets=0.3,
    )
    res = reconcile_total_to_ledger(total_xp=5.4, components=ledger, position="M", season="2024-25")
    assert res.reconciled is True
    assert res.semantic_valid is True
    assert res.discrepancy <= 0.01

    # Verify GK defcon is 0 points under official rules
    gk_ledger = ComponentLedger(minutes=90.0, defensive_contributions=2.0)
    gk_res = reconcile_total_to_ledger(total_xp=2.0, components=gk_ledger, position="GK", season="2025-26")
    assert gk_res.reconciled is True
    assert gk_res.details["defensive_contributions_pts"] == 0.0


def test_fixture_with_reconciling_but_wrong_components_fails_guard() -> None:
    """Verify acceptance rule: fixture with reconciling but wrong components fails applicable guard."""
    # Model assigns 0 playing minutes, but projects 0.68 goals (0.68 * 5 = 3.4 pts) to hit 3.4 total points
    comps_impossible = ComponentLedger(
        minutes=0.0,
        goals=0.68,
    )
    res = reconcile_total_to_ledger(total_xp=3.4, components=comps_impossible, position="M", season="2024-25")
    # Even if total points match the arithmetic sum, semantic validity MUST fail!
    assert res.reconciled is True
    assert res.semantic_valid is False
    assert any("Zero playing minutes" in s for s in res.semantic_violations)

    # Negative expected goals
    comps_neg = ComponentLedger(
        minutes=90.0,
        goals=-0.2,
        clean_sheets=0.4,
    )
    res_neg = reconcile_total_to_ledger(total_xp=2.0, components=comps_neg, position="D", season="2024-25")
    assert res_neg.semantic_valid is False
    assert any("negative value" in s for s in res_neg.semantic_violations)


def test_oracle_minutes_mechanism_diagnostics() -> None:
    """Verify oracle-minutes mechanism evaluation is explicitly isolated and prohibited from accuracy claims."""
    rate_ledger = ComponentLedger(minutes=70.0, goals=0.7, assists=0.35)
    diag = evaluate_oracle_minutes_mechanism(
        player_id=10,
        actual_minutes=90.0,
        modeled_minutes=70.0,
        actual_points=8.0,
        modeled_xp=5.5,
        rate_components=rate_ledger,
        position="F",
        season="2024-25",
    )
    assert diag.diagnostic_only is True
    assert diag.is_accuracy_evidence is False
    assert diag.oracle_minutes_xp > diag.modeled_xp
    assert "strictly prohibited" in diag.disclaimer


def test_evaluate_non_inferiority_guard_with_meaningful_margin() -> None:
    """Verify non-inferiority evaluation reports structured estimates, margins, CI bounds, and coverage."""
    np.random.seed(42)
    # Candidate error slightly higher by 0.01, within meaningful margin of 0.05
    champ_errors = np.random.normal(loc=1.5, scale=0.3, size=200)
    cand_errors = champ_errors + np.random.normal(loc=0.01, scale=0.1, size=200)

    res = evaluate_non_inferiority_guard(
        cand_errors,
        champ_errors,
        metric_name="points_mae",
        meaningful_margin=0.05,
        alpha=0.05,
        direction="lower_is_better",
    )
    assert res.passed is True
    assert res.status == "PASS"
    assert res.margin == 0.05
    assert res.estimate < 0.05
    assert res.ci_upper is not None
    assert res.ci_upper <= 0.05
    assert res.coverage == 0.95
    assert res.sample_size == 200

    # Real deterioration: Candidate error higher by 0.10, exceeding margin of 0.05
    cand_bad = champ_errors + np.random.normal(loc=0.10, scale=0.1, size=200)
    res_bad = evaluate_non_inferiority_guard(
        cand_bad,
        champ_errors,
        metric_name="points_mae",
        meaningful_margin=0.05,
        alpha=0.05,
        direction="lower_is_better",
    )
    assert res_bad.passed is False
    assert res_bad.status == "FAIL"
    assert res_bad.ci_lower is not None
    assert res_bad.ci_lower > 0.05


def test_uncertainty_crossing_non_inferiority_margin_remains_inconclusive() -> None:
    diffs = np.array([0.03, 0.12, -0.06, 0.14, -0.03, 0.10, -0.08, 0.11, 0.02, -0.05])
    champ_small = np.ones(10) * 1.5
    cand_small = champ_small + diffs

    res = evaluate_non_inferiority_guard(
        cand_small,
        champ_small,
        metric_name="points_mae",
        meaningful_margin=0.05,
        alpha=0.05,
        direction="lower_is_better",
    )
    assert res.ci_lower is not None and res.ci_upper is not None
    assert res.ci_lower <= 0.05
    assert res.ci_upper > 0.05
    assert res.passed is False
    assert res.status == "INCONCLUSIVE"


def test_calibration_bias_equivalence_requires_both_ci_bounds_within_margin() -> None:
    """Verify that calibration bias equivalence requires both CI bounds to lie within [-margin, +margin]."""
    # Point estimate is small (0.01), but wide uncertainty [-0.08, 0.10] crosses margin 0.05
    diffs_wide = np.array([0.01, 0.09, -0.08, 0.10, -0.09, 0.08, -0.07, 0.09, 0.01, -0.04])
    champ = np.ones(10) * 5.0
    cand = champ + diffs_wide

    res_wide = evaluate_non_inferiority_guard(
        cand,
        champ,
        metric_name="points_bias",
        meaningful_margin=0.05,
        alpha=0.05,
        direction="zero_is_ideal",
    )
    assert res_wide.passed is False
    assert res_wide.status == "INCONCLUSIVE"
    assert res_wide.ci_lower is not None and res_wide.ci_upper is not None
    assert res_wide.ci_lower <= 0.05 < res_wide.ci_upper


@pytest.mark.parametrize("direction", ["lower_is_better", "higher_is_better", "zero_is_ideal"])
def test_large_opposing_errors_do_not_demonstrate_harm(direction: MetricDirection) -> None:
    result = evaluate_non_inferiority_guard(
        [0.0, 200.0], [100.0, 100.0], metric_name="paired_error", meaningful_margin=1.0, direction=direction
    )
    assert result.estimate == 0.0
    assert result.ci_lower is not None and result.ci_upper is not None
    assert result.ci_lower < -1.0 < 1.0 < result.ci_upper
    assert result.passed is False
    assert result.status == "INCONCLUSIVE"


@pytest.mark.parametrize("direction,delta", [("lower_is_better", 2.0), ("higher_is_better", -2.0), ("zero_is_ideal", 2.0), ("zero_is_ideal", -2.0)])
def test_interval_entirely_outside_harm_bound_demonstrates_harm(direction: MetricDirection, delta: float) -> None:
    result = evaluate_non_inferiority_guard(
        [10.0 + delta] * 3, [10.0] * 3, metric_name="paired_error", meaningful_margin=1.0, direction=direction
    )
    assert result.ci_lower == delta and result.ci_upper == delta
    assert result.passed is False
    assert result.status == "FAIL"
    assert "Demonstrated harm" in result.reason


@pytest.mark.parametrize("delta", [-100.0, 100.0])
def test_one_observation_cannot_estimate_uncertainty(delta: float) -> None:
    result = evaluate_non_inferiority_guard([delta], [0.0], metric_name="paired_error", meaningful_margin=1.0)
    assert result.estimate == delta
    assert result.sample_size == 1
    assert result.standard_error is None and result.ci_lower is None and result.ci_upper is None
    assert result.coverage == 0.0
    assert result.passed is False
    assert result.status == "INCONCLUSIVE"


def test_scientific_bounds_preserve_precision_at_margin() -> None:
    result = evaluate_non_inferiority_guard([0.05000001] * 3, [0.0] * 3, metric_name="paired_error", meaningful_margin=0.05)
    assert result.status == "FAIL"
    assert result.ci_lower is not None
    assert result.ci_lower > result.margin
    assert result.ci_lower == pytest.approx(0.05000001, abs=1e-12)


def test_composite_non_inferiority_does_not_impose_every_component_improvement() -> None:
    """Verify that composite non-inferiority passes when required components avoid demonstrated harm."""
    primary = evaluate_non_inferiority_guard(
        [1.0, 1.1, 0.9],
        [1.2, 1.3, 1.0],
        metric_name="points_mae",
        meaningful_margin=0.05,
    )
    # Component A improved
    comp_a = evaluate_non_inferiority_guard(
        [0.4, 0.4, 0.4],
        [0.5, 0.5, 0.5],
        metric_name="goals_mse",
        meaningful_margin=0.05,
    )
    # Component B slightly worse by 0.01, but well within approved non-inferiority margin 0.05
    comp_b = evaluate_non_inferiority_guard(
        [0.31, 0.31, 0.31],
        [0.30, 0.30, 0.30],
        metric_name="assists_mse",
        meaningful_margin=0.05,
    )
    passed, reason = evaluate_composite_non_inferiority(primary, [comp_a, comp_b])
    assert passed is True
    assert "passed" in reason


def test_series_index_alignment_in_guard() -> None:
    """Verify that evaluate_non_inferiority_guard aligns pandas Series on common index."""
    s_champ = pd.Series([1.5, 2.0, 2.5], index=[101, 102, 103])
    # Shuffled and offset indices
    s_cand = pd.Series([2.0, 1.5, 9.9], index=[102, 101, 999])

    res = evaluate_non_inferiority_guard(
        s_cand,
        s_champ,
        metric_name="points_mae",
        meaningful_margin=0.10,
    )
    # Aligns 101 and 102; drops 103 and 999
    assert res.sample_size == 2
    assert res.estimate == 0.0


def test_missing_required_evidence_fails_guard() -> None:
    """Verify that missing required evaluation samples returns MISSING_EVIDENCE and fails guard."""
    res = evaluate_non_inferiority_guard(
        [],
        [],
        metric_name="required_component_mae",
        meaningful_margin=0.05,
        required=True,
    )
    assert res.passed is False
    assert res.status == "MISSING_EVIDENCE"


def test_optional_prioritization_screen_separation() -> None:
    """Verify that deferred or unassessed screens do not declare a Dead Lever without full replay."""
    # Fast screen passes
    res_pass = evaluate_prioritization_screen(fast_metric_delta=0.15, threshold=0.0)
    assert res_pass.verdict == "PASS"

    # Fast screen deferred: does not declare Dead Lever
    res_defer = evaluate_prioritization_screen(fast_metric_delta=-0.08, threshold=0.0)
    assert res_defer.verdict == "DEFERRED"
    assert "not declared Dead Lever" in res_defer.reason

    # Mechanism cannot be assessed by fast screen: routes to full replay
    res_route = evaluate_prioritization_screen(fast_metric_delta=-0.05, can_assess_mechanism=False)
    assert res_route.verdict == "REQUIRES_FULL_REPLAY"


def test_diagnose_unconstrained_reversal() -> None:
    """Verify diagnostic report for substantial reversals across drivers."""
    # No reversal: both positive
    diag_none = diagnose_unconstrained_reversal(strategic_net_delta=1.5, unconstrained_net_delta=1.8)
    assert diag_none.has_reversal is False
    assert diag_none.reversal_category == "NONE"

    # Substantial reversal: positive in Unconstrained (+3.0) but negative in Strategic (-1.0)
    diag_rev = diagnose_unconstrained_reversal(
        strategic_net_delta=-1.0,
        unconstrained_net_delta=3.0,
        reversal_threshold=2.0,
        penalties_delta=2.5,
    )
    assert diag_rev.has_reversal is True
    assert diag_rev.reversal_category == "HIT_PENALTY"
    assert any("Strategic primary remains authoritative" in r for r in diag_rev.reasons)

    # Reversal driven by minutes floor
    diag_mins = diagnose_unconstrained_reversal(
        strategic_net_delta=-1.0,
        unconstrained_net_delta=3.0,
        reversal_threshold=2.0,
        minutes_floor_delta=2.0,
    )
    assert diag_mins.reversal_category == "MINUTES_FLOOR"
