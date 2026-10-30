"""Unit tests for Phase 8 numerical and statistical protocol."""

from dataclasses import asdict, replace
from pathlib import Path

import numpy as np
import pytest

from backtesting.evidence_statistics import (
    PairedGameweekScore,
    StatisticalProtocolConfig,
    assign_gameweek_segment,
    compute_season_summaries,
    compute_score_trace_hash,
    evaluate_evidence_against_protocol,
    resample_paired_blocks,
    run_stored_score_bootstrap,
    simulate_bootstrap_calibration,
)
from backtesting.projection_guards import GuardOutput, evaluate_non_inferiority_guard
from backtesting.confirmation_registry import ConfirmationRegistry


def _passing_guard(metric_name: str = "minutes_mae") -> GuardOutput:
    return GuardOutput(
        metric_name=metric_name,
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


def _register_confirmation(
    tmp_path: Path,
    scores: list[PairedGameweekScore],
    config: StatisticalProtocolConfig,
) -> tuple[ConfirmationRegistry, str]:
    registry = ConfirmationRegistry(tmp_path / "registry.jsonl")
    confirmation_scores = [score for score in scores if score.season == config.confirmation_season]
    registration = registry.register_finalist(
        candidate_name="synthetic_candidate",
        champion_name="synthetic_champion",
        mechanism_family="synthetic_family",
        model_source_hash="a" * 64,
        parameters_hash="b" * 64,
        dev_selection_record_ref="synthetic-development-record",
        protocol_hash=config.compute_hash(),
        registered_gameweeks=tuple(score.gameweek for score in confirmation_scores),
        requested_seasons=(config.confirmation_season,),
        max_family_attempts=config.max_family_attempts,
    )
    registry.transition_attempt_status(
        registration.attempt_id,
        "in_progress",
        execution_status="complete",
        completed_gameweeks=registration.registered_gameweeks,
        score_trace_hash=compute_score_trace_hash(confirmation_scores),
    )
    return registry, registration.attempt_id


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
    """Every registered sequential attempt spends the same Bonferroni budget."""
    config_bonf = StatisticalProtocolConfig(
        nominal_alpha=0.05,
        family_error_control="bonferroni",
        max_family_attempts=10,
        bootstrap_draws=100,
    )
    scores = _make_paired_scores(gameweek_count=10)
    res_bonf = run_stored_score_bootstrap(scores, config_bonf, attempt_number=1)
    assert res_bonf.adjusted_alpha == pytest.approx(0.005)

    res_last = run_stored_score_bootstrap(scores, config_bonf, attempt_number=10)
    assert res_last.adjusted_alpha == pytest.approx(0.005)


@pytest.mark.parametrize("attempt_number", [0, 11])
def test_attempt_outside_family_budget_is_rejected(attempt_number: int) -> None:
    config = StatisticalProtocolConfig(bootstrap_draws=100, max_family_attempts=10)
    with pytest.raises(ValueError, match="family attempt budget"):
        run_stored_score_bootstrap(_make_paired_scores(), config, attempt_number=attempt_number)


@pytest.mark.parametrize("attempt_number", [1, 5, 10])
def test_sequential_holm_is_not_pvalue_ranked_inference(attempt_number: int) -> None:
    config = StatisticalProtocolConfig(bootstrap_draws=100, family_error_control="holm")
    with pytest.raises(ValueError, match="fixed family ordered by p-value"):
        run_stored_score_bootstrap(_make_paired_scores(), config, attempt_number=attempt_number)


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


def test_evidence_evaluation_pass_verdict(tmp_path: Path) -> None:
    """Verify PASS verdict requires positive CI, confirmation season, green guards, and human approval."""
    scores = _make_paired_scores(season="2025-26", mean_cand=63.0, mean_champ=60.0, noise_std=0.5)
    scores += _make_paired_scores(season="2024-25", mean_cand=63.0, mean_champ=60.0, noise_std=0.5)
    config = StatisticalProtocolConfig(
        nominal_alpha=0.05,
        bootstrap_draws=1_000,
        family_error_control="bonferroni",
        approved_by_human=True,
        approval_reference="SYNTHETIC-PROTOCOL-APPROVAL",
        required_projection_guards=("minutes_mae",),
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

    registry, attempt_id = _register_confirmation(tmp_path, scores, config)
    eval_res = evaluate_evidence_against_protocol(
        scores,
        [guard],
        config,
        is_confirmation_available=True,
        confirmation_registry=registry,
        confirmation_attempt_id=attempt_id,
    )

    assert eval_res.verdict == "pass"
    assert eval_res.point_estimate > 2.5
    assert eval_res.confidence_interval[0] > 0.0
    assert eval_res.projection_guards_passed is True
    assert eval_res.material_loss_violated is False
    assert eval_res.is_confirmation_available is True


def test_evidence_evaluation_unapproved_protocol_yields_inconclusive() -> None:
    """Verify unapproved protocol yields INCONCLUSIVE even with winning evidence."""
    scores = _make_paired_scores(gameweek_count=38, mean_cand=63.0, mean_champ=60.0, noise_std=0.5)
    config = StatisticalProtocolConfig(
        nominal_alpha=0.05,
        bootstrap_draws=1_000,
        family_error_control="none",
        approved_by_human=False,
        required_projection_guards=("minutes_mae",),
    )
    eval_res = evaluate_evidence_against_protocol(
        scores,
        [_passing_guard()],
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
        required_projection_guards=("minutes_mae",),
    )

    eval_res = evaluate_evidence_against_protocol(
        scores,
        [_passing_guard()],
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
        required_projection_guards=("minutes_mae",),
    )

    eval_res = evaluate_evidence_against_protocol(
        scores,
        [_passing_guard()],
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
        required_projection_guards=("minutes_mae",),
        approved_by_human=True,
        approval_reference="SYNTHETIC-PROTOCOL-APPROVAL",
    )

    eval_res = evaluate_evidence_against_protocol(scores, [_passing_guard()], config)
    assert eval_res.verdict == "fail"
    assert eval_res.material_loss_violated is True
    assert any("material limit" in r for r in eval_res.reasons)


def test_evidence_evaluation_fail_on_projection_guard() -> None:
    """Verify FAIL verdict triggered when required projection guard fails."""
    scores = _make_paired_scores(gameweek_count=38, mean_cand=65.0, mean_champ=60.0, noise_std=0.5)
    config = StatisticalProtocolConfig(
        bootstrap_draws=500,
        family_error_control="none",
        required_projection_guards=("minutes_mae",),
        approved_by_human=True,
        approval_reference="SYNTHETIC-PROTOCOL-APPROVAL",
    )
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


def test_evidence_evaluation_invalid_on_missing_guard_evidence() -> None:
    """Verify INVALID verdict when required projection guard is missing evidence (does not lock dead lever)."""
    scores = _make_paired_scores(gameweek_count=38, mean_cand=65.0, mean_champ=60.0, noise_std=0.5)
    config = StatisticalProtocolConfig(bootstrap_draws=500, family_error_control="none", required_projection_guards=("minutes_mae",))
    missing_guard = GuardOutput(
        metric_name="minutes_mae",
        passed=False,
        status="MISSING_EVIDENCE",
        estimate=0.0,
        margin=1.0,
        standard_error=0.0,
        ci_lower=0.0,
        ci_upper=0.0,
        coverage=0.0,
        sample_size=0,
        direction="lower_is_better",
        reason="No minutes projection column found in output",
    )

    eval_res = evaluate_evidence_against_protocol(
        scores,
        [missing_guard],
        config,
        is_confirmation_available=True,
    )
    assert eval_res.verdict == "invalid"
    assert eval_res.projection_guards_passed is False
    assert any("missing required evidence" in r for r in eval_res.reasons)


def test_evidence_evaluation_invalid_on_empty_input() -> None:
    """Verify INVALID verdict when score data is empty."""
    config = StatisticalProtocolConfig()
    eval_res = evaluate_evidence_against_protocol([], None, config)
    assert eval_res.verdict == "invalid"
    assert any("empty" in r for r in eval_res.reasons)


@pytest.mark.parametrize("guards", [None, []])
def test_absent_guard_outputs_cannot_be_a_vacuous_pass(guards: list[GuardOutput] | None) -> None:
    config = StatisticalProtocolConfig(
        bootstrap_draws=100,
        approved_by_human=True,
        approval_reference="SYNTHETIC-APPROVAL",
        required_projection_guards=("minutes_mae",),
    )
    result = evaluate_evidence_against_protocol(_make_paired_scores(noise_std=0.0), guards, config, is_confirmation_available=True)
    assert result.verdict == "invalid"
    assert result.projection_guards_passed is False
    assert any("missing required evidence" in reason for reason in result.reasons)


@pytest.mark.parametrize("required", [(), ("minutes_mae", "points_mse")])
def test_guard_inventory_must_be_declared_and_completely_supplied(required: tuple[str, ...]) -> None:
    config = StatisticalProtocolConfig(bootstrap_draws=100, required_projection_guards=required)
    result = evaluate_evidence_against_protocol(_make_paired_scores(), [_passing_guard()], config)
    assert result.verdict == "invalid"
    assert result.projection_guards_passed is False
    assert any("inventory" in reason for reason in result.reasons)


@pytest.mark.parametrize(
    "guards",
    [
        [_passing_guard(), _passing_guard()],
        [replace(_passing_guard(), status="UNASSESSED")],
        [replace(_passing_guard(), sample_size=0)],
        [replace(_passing_guard(), estimate=float("nan"))],
    ],
)
def test_duplicate_or_unassessed_guard_outputs_are_invalid(guards: list[GuardOutput]) -> None:
    config = StatisticalProtocolConfig(bootstrap_draws=100, required_projection_guards=("minutes_mae",))
    result = evaluate_evidence_against_protocol(_make_paired_scores(), guards, config)
    assert result.verdict == "invalid"
    assert result.projection_guards_passed is False


@pytest.mark.parametrize(
    "guard",
    [
        replace(_passing_guard(), passed=False, status="FAIL", estimate=float("nan")),
        replace(_passing_guard(), passed=False, status="FAIL", standard_error=float("nan")),
        replace(_passing_guard(), passed=False, status="FAIL", ci_lower=float("nan")),
        replace(_passing_guard(), passed=False, status="FAIL", ci_upper=float("nan")),
        replace(_passing_guard(), passed=False, status="FAIL", coverage=0.0),
        replace(_passing_guard(), passed=False, status="FAIL", sample_size=0),
        replace(_passing_guard(), passed=False, status="PASS"),
        replace(_passing_guard(), passed=True, status="FAIL"),
        GuardOutput(**{**asdict(_passing_guard()), "passed": False, "status": "UNKNOWN"}),
    ],
)
def test_malformed_failed_guard_evidence_is_invalid(guard: GuardOutput) -> None:
    config = StatisticalProtocolConfig(
        bootstrap_draws=100,
        required_projection_guards=("minutes_mae",),
        approved_by_human=False,
    )
    result = evaluate_evidence_against_protocol(_make_paired_scores(noise_std=0.0), [guard], config)
    assert result.verdict == "invalid"
    assert result.projection_guards_passed is False
    assert result.projection_guard_failures


def test_complete_failed_guard_still_demonstrates_substantive_regression() -> None:
    guard = replace(
        _passing_guard(),
        passed=False,
        status="FAIL",
        estimate=2.5,
        ci_lower=2.3,
        ci_upper=2.7,
        reason="Measured regression exceeds the approved margin",
    )
    config = StatisticalProtocolConfig(
        bootstrap_draws=100,
        required_projection_guards=("minutes_mae",),
        approved_by_human=True,
        approval_reference="SYNTHETIC-PROTOCOL-APPROVAL",
    )
    result = evaluate_evidence_against_protocol(_make_paired_scores(noise_std=0.0), [guard], config)
    assert result.verdict == "fail"
    assert result.projection_guard_failures == ["Guard 'minutes_mae' failed: Measured regression exceeds the approved margin"]


@pytest.mark.parametrize("harm", ["material_loss", "guard", "negative_bootstrap"])
@pytest.mark.parametrize("approved", [False, True])
def test_scientific_harm_requires_approved_numeric_limits(harm: str, approved: bool) -> None:
    config = StatisticalProtocolConfig(
        bootstrap_draws=100,
        required_projection_guards=("minutes_mae",),
        approved_by_human=approved,
        approval_reference="SYNTHETIC-PROTOCOL-APPROVAL" if approved else "UNAPPROVED",
    )
    candidate_points = {"material_loss": 58.0, "guard": 62.0, "negative_bootstrap": 59.9}[harm]
    scores = _make_paired_scores(mean_cand=candidate_points, mean_champ=60.0, noise_std=0.0)
    guard = _passing_guard()
    if harm == "guard":
        guard = replace(guard, passed=False, status="FAIL", estimate=2.5, ci_lower=2.3, ci_upper=2.7)
    result = evaluate_evidence_against_protocol(scores, [guard], config)
    assert result.verdict == ("fail" if approved else "inconclusive")
    assert result.point_estimate == pytest.approx(candidate_points - 60.0)
    if harm == "material_loss":
        assert result.material_loss_violated is True
        assert any("material limit" in reason for reason in result.reasons)
    elif harm == "guard":
        assert result.projection_guards_passed is False
        assert result.projection_guard_failures
    else:
        assert result.material_loss_violated is False
        assert result.confidence_interval[1] < 0.0
        assert any("interval below zero" in reason for reason in result.reasons)
        assert not any("Uncertainty contains zero" in reason for reason in result.reasons)
    if not approved:
        assert "Protocol unapproved; human approval barrier active" in result.admitted_limitations
        assert any("not been approved by human" in reason for reason in result.reasons)


@pytest.mark.parametrize("claim", [False, True])
def test_confirmation_boolean_cannot_admit_unregistered_evidence(claim: bool) -> None:
    config = StatisticalProtocolConfig(
        bootstrap_draws=100,
        approved_by_human=True,
        approval_reference="SYNTHETIC-APPROVAL",
        required_projection_guards=("minutes_mae",),
    )
    scores = _make_paired_scores(season="2025-26", noise_std=0.0) + _make_paired_scores(noise_std=0.0)
    result = evaluate_evidence_against_protocol(scores, [_passing_guard()], config, is_confirmation_available=claim)
    assert result.confidence_interval[0] > 0.0
    assert result.verdict == "inconclusive"
    assert result.is_confirmation_available is False
    assert any("Confirmation season evidence" in reason for reason in result.reasons)


def test_changed_confirmation_scores_are_not_bound_to_the_registered_run(tmp_path: Path) -> None:
    config = StatisticalProtocolConfig(
        bootstrap_draws=100,
        approved_by_human=True,
        approval_reference="SYNTHETIC-APPROVAL",
        required_projection_guards=("minutes_mae",),
    )
    scores = _make_paired_scores(season="2025-26", noise_std=0.0) + _make_paired_scores(noise_std=0.0)
    registry, attempt_id = _register_confirmation(tmp_path, scores, config)
    altered = [replace(score, candidate_net_points=score.candidate_net_points + 1.0) for score in scores]
    result = evaluate_evidence_against_protocol(
        altered, [_passing_guard()], config, confirmation_registry=registry, confirmation_attempt_id=attempt_id
    )
    assert result.verdict == "inconclusive"
    assert result.is_confirmation_available is False


def test_registered_confirmation_alone_cannot_replace_development_evidence(tmp_path: Path) -> None:
    config = StatisticalProtocolConfig(
        bootstrap_draws=100,
        approved_by_human=True,
        approval_reference="SYNTHETIC-APPROVAL",
        required_projection_guards=("minutes_mae",),
    )
    scores = _make_paired_scores(noise_std=0.0)
    registry, attempt_id = _register_confirmation(tmp_path, scores, config)
    result = evaluate_evidence_against_protocol(
        scores, [_passing_guard()], config, confirmation_registry=registry, confirmation_attempt_id=attempt_id
    )
    assert result.is_confirmation_available is True
    assert result.verdict == "inconclusive"
    assert "Required development and confirmation seasons are incomplete" in result.admitted_limitations


def test_unadjusted_diagnostic_cannot_produce_a_final_pass(tmp_path: Path) -> None:
    config = StatisticalProtocolConfig(
        bootstrap_draws=100,
        approved_by_human=True,
        approval_reference="SYNTHETIC-APPROVAL",
        required_projection_guards=("minutes_mae",),
        family_error_control="none",
    )
    scores = _make_paired_scores(season="2025-26", noise_std=0.0) + _make_paired_scores(noise_std=0.0)
    registry, attempt_id = _register_confirmation(tmp_path, scores, config)
    result = evaluate_evidence_against_protocol(
        scores, [_passing_guard()], config, confirmation_registry=registry, confirmation_attempt_id=attempt_id
    )
    assert result.confidence_interval[0] > 0.0
    assert result.is_confirmation_available is True
    assert result.verdict == "inconclusive"
    assert any("no search-wide family error control" in limitation for limitation in result.admitted_limitations)


def test_guard_inventory_and_semantics_are_part_of_frozen_protocol_identity() -> None:
    config = StatisticalProtocolConfig(required_projection_guards=("minutes_mae",), evidence_protocol_hash="a" * 64)
    assert config.compute_hash() != replace(config, required_projection_guards=("minutes_mae", "points_mse")).compute_hash()
    assert config.compute_hash() != replace(config, evidence_protocol_hash="b" * 64).compute_hash()


def test_score_trace_digest_binds_values_and_not_input_order() -> None:
    scores = _make_paired_scores(gameweek_count=2)
    assert compute_score_trace_hash(scores) == compute_score_trace_hash(list(reversed(scores)))
    changed = [replace(scores[0], candidate_net_points=scores[0].candidate_net_points + 1.0), scores[1]]
    assert compute_score_trace_hash(changed) != compute_score_trace_hash(scores)


@pytest.mark.parametrize("evidence", ["wide_interval", "one_observation", "legacy_failed_label"])
def test_uncertain_guard_prevents_pass_without_declaring_harm(tmp_path: Path, evidence: str) -> None:
    config = StatisticalProtocolConfig(
        bootstrap_draws=100,
        approved_by_human=True,
        approval_reference="SYNTHETIC-APPROVAL",
        required_projection_guards=("minutes_mae",),
    )
    scores = _make_paired_scores(season="2025-26", noise_std=0.0) + _make_paired_scores(noise_std=0.0)
    registry, attempt_id = _register_confirmation(tmp_path, scores, config)
    candidate, champion = ([100.0], [0.0]) if evidence == "one_observation" else ([0.0, 200.0], [100.0, 100.0])
    guard = evaluate_non_inferiority_guard(candidate, champion, metric_name="minutes_mae", meaningful_margin=1.0)
    if evidence == "legacy_failed_label":
        guard = replace(guard, status="FAIL")
    result = evaluate_evidence_against_protocol(
        scores, [guard], config, confirmation_registry=registry, confirmation_attempt_id=attempt_id
    )
    assert result.is_confirmation_available is True
    assert result.confidence_interval[0] > 0.0
    assert result.verdict == "inconclusive"
    assert result.projection_guards_passed is False
    assert any("uncertain" in reason or "uncertainty" in reason for reason in result.reasons)


def test_default_segment_label_cannot_hide_late_season_harm() -> None:
    scores = [
        PairedGameweekScore("synthetic", 5, 70.0, 60.0, 70.0, 60.0, 0, 0),
        PairedGameweekScore("synthetic", 20, 50.0, 60.0, 50.0, 60.0, 0, 0),
    ]
    assert all(score.segment == "early_mid" for score in scores)
    summary = compute_season_summaries(scores, season_material_loss_limit=10.0, segment_material_loss_limit=6.0)[0]
    assert summary.net_delta == 0.0
    assert summary.violates_material_loss is False
    assert summary.segment_losses == {"early_mid": 10.0, "late": -10.0}
    assert summary.violates_segment_loss is True
    config = StatisticalProtocolConfig(
        bootstrap_draws=100,
        approved_by_human=True,
        approval_reference="SYNTHETIC-APPROVAL",
        required_projection_guards=("minutes_mae",),
    )
    result = evaluate_evidence_against_protocol(scores, [_passing_guard()], config)
    assert result.verdict == "fail"
    assert any("segment 'late'" in reason for reason in result.reasons)


def test_chip_harm_is_checked_separately_from_offsetting_nonchip_gameweeks() -> None:
    scores = [
        PairedGameweekScore("synthetic", 5, 53.0, 60.0, 53.0, 60.0, 0, 0, is_chip_gameweek=True),
        PairedGameweekScore("synthetic", 6, 67.0, 60.0, 67.0, 60.0, 0, 0),
    ]
    checked = compute_season_summaries(scores, season_material_loss_limit=10.0, segment_material_loss_limit=6.0)[0]
    assert checked.net_delta == 0.0
    assert checked.segment_losses == {"early_mid": 0.0, "chip": -7.0}
    assert checked.violates_segment_loss is True
    disabled = compute_season_summaries(
        scores, season_material_loss_limit=10.0, segment_material_loss_limit=6.0, state_harm_checks_enabled=False
    )[0]
    assert disabled.segment_losses == {"early_mid": 0.0}
    assert disabled.violates_segment_loss is False


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
