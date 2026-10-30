"""Numerical and statistical evaluation protocol for model promotion.

Implements Phase 8 requirements:
1. Continuous net-score estimand under registered Strategic policy and neutral GW1 anchor.
2. Season-level and segment/state-level material-loss limits.
3. Paired calendar dependence and non-wrapping Moving Block Bootstrap (MBB) preserving serial autocorrelation.
4. Stored-score resampling without solver calls per bootstrap draw.
5. Fixed Bonferroni alpha allocation across registered attempts; bootstrap validity requires calibration.
6. Multi-season weighting and explicit Inconclusive vs demonstrated Fail vs Pass routes.
7. Integration with substantive projection guards (Phase 6).
8. Simulation calibration diagnostic for bootstrap coverage and empirical Type I error.
9. Concrete Q21 proposal with practical units, frozen protocol identity digest, and human approval barriers.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
import hashlib
import json
import math
from typing import TYPE_CHECKING, Any, Literal

import numpy as np

from backtesting.projection_guards import GuardOutput, classify_non_inferiority_interval

if TYPE_CHECKING:
    from backtesting.confirmation_registry import ConfirmationRegistry

ScientificVerdict = Literal["pass", "fail", "inconclusive", "invalid"]
FamilyErrorControl = Literal["bonferroni", "holm", "none"]


@dataclass(frozen=True)
class PairedGameweekScore:
    """Paired gameweek score record from rolling replays with identical calendar alignment."""

    season: str
    gameweek: int
    candidate_net_points: float
    champion_net_points: float
    candidate_gross_points: float
    champion_gross_points: float
    candidate_hits_deducted: int
    champion_hits_deducted: int
    is_chip_gameweek: bool = False
    segment: str = "early_mid"

    @property
    def delta_net(self) -> float:
        return float(self.candidate_net_points - self.champion_net_points)

    @property
    def delta_gross(self) -> float:
        return float(self.candidate_gross_points - self.champion_gross_points)

    @property
    def delta_hits(self) -> int:
        return int(self.candidate_hits_deducted - self.champion_hits_deducted)


@dataclass(frozen=True)
class SeasonScoreSummary:
    """Summary of paired performance for a single admitted season."""

    season: str
    gameweek_count: int
    candidate_total_net: float
    champion_total_net: float
    net_delta: float
    mean_net_delta_per_gw: float
    material_loss_limit: float
    violates_material_loss: bool
    segment_losses: dict[str, float] = field(default_factory=dict)
    violates_segment_loss: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BootstrapInferenceResult:
    """Result of stored-score block bootstrap inference on paired trajectories."""

    point_estimate: float
    confidence_interval: tuple[float, float]
    alpha: float
    adjusted_alpha: float
    p_value_superiority: float
    p_value_non_inferiority: float
    bootstrap_draws: int
    block_size: int
    standard_error: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "point_estimate": self.point_estimate,
            "confidence_interval": list(self.confidence_interval),
            "alpha": self.alpha,
            "adjusted_alpha": self.adjusted_alpha,
            "p_value_superiority": self.p_value_superiority,
            "p_value_non_inferiority": self.p_value_non_inferiority,
            "bootstrap_draws": self.bootstrap_draws,
            "block_size": self.block_size,
            "standard_error": self.standard_error,
        }


@dataclass(frozen=True)
class StatisticalProtocolConfig:
    """Concrete Q21 numerical and statistical protocol proposal with practical units."""

    protocol_version: str = "v1.0"
    nominal_alpha: float = 0.05
    bootstrap_draws: int = 10_000
    bootstrap_block_size: int = 5
    season_material_loss_limit: float = 10.0
    segment_material_loss_limit: float = 6.0
    non_inferiority_margin_per_gw: float = 0.05
    family_error_control: FamilyErrorControl = "bonferroni"
    max_family_attempts: int = 10
    season_weights: dict[str, float] = field(default_factory=dict)
    state_harm_checks_enabled: bool = True
    approved_by_human: bool = False
    approval_reference: str = "UNAPPROVED"
    required_projection_guards: tuple[str, ...] = ()
    development_season: str = "2025-26"
    confirmation_season: str = "2024-25"
    evidence_protocol_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def compute_hash(self) -> str:
        """Compute deterministic SHA256 digest of frozen protocol parameters."""
        canonical_data = {
            "protocol_version": self.protocol_version,
            "nominal_alpha": self.nominal_alpha,
            "bootstrap_draws": self.bootstrap_draws,
            "bootstrap_block_size": self.bootstrap_block_size,
            "season_material_loss_limit": self.season_material_loss_limit,
            "segment_material_loss_limit": self.segment_material_loss_limit,
            "non_inferiority_margin_per_gw": self.non_inferiority_margin_per_gw,
            "family_error_control": self.family_error_control,
            "max_family_attempts": self.max_family_attempts,
            "season_weights": dict(sorted(self.season_weights.items())),
            "state_harm_checks_enabled": self.state_harm_checks_enabled,
            "required_projection_guards": list(self.required_projection_guards),
            "development_season": self.development_season,
            "confirmation_season": self.confirmation_season,
            "evidence_protocol_hash": self.evidence_protocol_hash,
        }
        encoded = json.dumps(canonical_data, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class PromotionEvidenceEvaluation:
    """Synthesized promotion evidence verdict against the numerical protocol."""

    verdict: ScientificVerdict
    point_estimate: float
    confidence_interval: tuple[float, float]
    p_value: float
    adjusted_alpha: float
    season_summaries: list[SeasonScoreSummary]
    material_loss_violated: bool
    projection_guards_passed: bool
    projection_guard_failures: list[str]
    reasons: list[str]
    admitted_limitations: list[str]
    protocol_hash: str
    attempt_number: int
    is_confirmation_available: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict,
            "point_estimate": self.point_estimate,
            "confidence_interval": list(self.confidence_interval),
            "p_value": self.p_value,
            "adjusted_alpha": self.adjusted_alpha,
            "season_summaries": [s.to_dict() for s in self.season_summaries],
            "material_loss_violated": self.material_loss_violated,
            "projection_guards_passed": self.projection_guards_passed,
            "projection_guard_failures": self.projection_guard_failures,
            "reasons": self.reasons,
            "admitted_limitations": self.admitted_limitations,
            "protocol_hash": self.protocol_hash,
            "attempt_number": self.attempt_number,
            "is_confirmation_available": self.is_confirmation_available,
        }


def assign_gameweek_segment(gameweek: int) -> str:
    """Return canonical seasonal segment name for a given gameweek number."""
    if gameweek < 1 or gameweek > 38:
        raise ValueError(f"Gameweek {gameweek} out of valid season bounds [1, 38]")
    if gameweek <= 4:
        return "cold_start"
    if gameweek <= 19:
        return "early_mid"
    return "late"


def compute_season_summaries(
    paired_scores: Sequence[PairedGameweekScore],
    season_material_loss_limit: float,
    segment_material_loss_limit: float,
    *,
    state_harm_checks_enabled: bool = True,
) -> list[SeasonScoreSummary]:
    """Compute per-season performance totals and evaluate seasonal/segment harm limits."""
    by_season: dict[str, list[PairedGameweekScore]] = {}
    for score in paired_scores:
        by_season.setdefault(score.season, []).append(score)

    summaries: list[SeasonScoreSummary] = []
    for season, scores in sorted(by_season.items()):
        cand_total = sum(s.candidate_net_points for s in scores)
        champ_total = sum(s.champion_net_points for s in scores)
        net_delta = cand_total - champ_total
        gw_count = len(scores)
        mean_gw = net_delta / gw_count if gw_count > 0 else 0.0

        # Segment breakdown
        segment_deltas: dict[str, float] = {}
        for s in scores:
            segment = assign_gameweek_segment(s.gameweek)
            segment_deltas[segment] = segment_deltas.get(segment, 0.0) + s.delta_net
            if not isinstance(s.is_chip_gameweek, bool):
                raise ValueError("Chip gameweek flag must be an explicit boolean")
            if state_harm_checks_enabled and s.is_chip_gameweek:
                segment_deltas["chip"] = segment_deltas.get("chip", 0.0) + s.delta_net

        violates_season = net_delta < -season_material_loss_limit
        violates_segment = any(loss < -segment_material_loss_limit for loss in segment_deltas.values())

        summaries.append(
            SeasonScoreSummary(
                season=season,
                gameweek_count=gw_count,
                candidate_total_net=float(cand_total),
                champion_total_net=float(champ_total),
                net_delta=float(net_delta),
                mean_net_delta_per_gw=float(mean_gw),
                material_loss_limit=season_material_loss_limit,
                violates_material_loss=violates_season,
                segment_losses=segment_deltas,
                violates_segment_loss=violates_segment,
            )
        )
    return summaries


def resample_paired_blocks(
    season_scores: Sequence[PairedGameweekScore],
    block_size: int,
    rng: np.random.Generator,
) -> list[float]:
    """Non-wrapping Moving Block Bootstrap (MBB) resampling of paired gameweek differences.

    Resamples contiguous blocks of paired differences to preserve autocorrelation structure
    without wrapping around season boundaries or breaking candidate-champion pairing.
    """
    n = len(season_scores)
    if n == 0:
        return []
    if n <= block_size:
        # Fallback to independent sampling with replacement when sample is shorter than block size
        indices = rng.integers(0, n, size=n)
        return [season_scores[i].delta_net for i in indices]

    num_blocks = math.ceil(n / block_size)
    max_start = n - block_size
    sampled_deltas: list[float] = []

    for _ in range(num_blocks):
        start_idx = int(rng.integers(0, max_start + 1))
        for offset in range(block_size):
            sampled_deltas.append(season_scores[start_idx + offset].delta_net)
            if len(sampled_deltas) == n:
                break
        if len(sampled_deltas) == n:
            break

    return sampled_deltas


def compute_score_trace_hash(paired_scores: Sequence[PairedGameweekScore]) -> str:
    """Bind retained paired score values and their calendar keys to a registry entry."""
    payload = [asdict(score) for score in sorted(paired_scores, key=lambda score: (score.season, score.gameweek))]
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _adjusted_alpha(config: StatisticalProtocolConfig, attempt_number: int) -> float:
    if config.max_family_attempts < 1 or not 1 <= attempt_number <= config.max_family_attempts:
        raise ValueError("Attempt number exceeds the registered positive family attempt budget")
    if not 0.0 < config.nominal_alpha < 1.0:
        raise ValueError("Nominal alpha must lie strictly between zero and one")
    if config.family_error_control == "holm":
        raise ValueError("Holm requires a fixed family ordered by p-value; sequential attempt ranks are unsupported")
    if config.family_error_control == "bonferroni":
        return config.nominal_alpha / config.max_family_attempts
    if config.family_error_control == "none":
        return config.nominal_alpha
    raise ValueError(f"Unsupported family error control: {config.family_error_control}")


def run_stored_score_bootstrap(
    paired_scores: Sequence[PairedGameweekScore],
    config: StatisticalProtocolConfig,
    *,
    attempt_number: int = 1,
    seed: int = 42,
) -> BootstrapInferenceResult:
    """Run non-wrapping block bootstrap on stored scores without invoking the MILP solver."""
    adjusted_alpha = _adjusted_alpha(config, attempt_number)
    if config.bootstrap_draws < 1 or config.bootstrap_block_size < 1:
        raise ValueError("Bootstrap draws and block size must be positive")
    if not paired_scores:
        return BootstrapInferenceResult(
            point_estimate=0.0,
            confidence_interval=(0.0, 0.0),
            alpha=config.nominal_alpha,
            adjusted_alpha=adjusted_alpha,
            p_value_superiority=1.0,
            p_value_non_inferiority=1.0,
            bootstrap_draws=0,
            block_size=config.bootstrap_block_size,
            standard_error=0.0,
        )

    by_season: dict[str, list[PairedGameweekScore]] = {}
    for s in paired_scores:
        by_season.setdefault(s.season, []).append(s)

    total_weights = 0.0
    season_weights: dict[str, float] = {}
    for season in by_season:
        w = config.season_weights.get(season, float(len(by_season[season])))
        season_weights[season] = w
        total_weights += w

    if total_weights > 0:
        norm_weights = {s: w / total_weights for s, w in season_weights.items()}
    else:
        norm_weights = {s: 1.0 / len(by_season) for s in by_season}

    # Observed point estimate (weighted mean per GW)
    season_means = {s: float(np.mean([x.delta_net for x in scores])) for s, scores in by_season.items()}
    point_estimate = float(sum(season_means[s] * norm_weights[s] for s in by_season))

    rng = np.random.default_rng(seed)
    bootstrap_means = np.empty(config.bootstrap_draws, dtype=float)

    for b in range(config.bootstrap_draws):
        weighted_draw = 0.0
        for season, scores in by_season.items():
            resampled = resample_paired_blocks(scores, config.bootstrap_block_size, rng)
            season_mean = float(np.mean(resampled))
            weighted_draw += season_mean * norm_weights[season]
        bootstrap_means[b] = weighted_draw

    lower_pct = (adjusted_alpha / 2.0) * 100.0
    upper_pct = (1.0 - adjusted_alpha / 2.0) * 100.0
    ci_lower = float(np.percentile(bootstrap_means, lower_pct))
    ci_upper = float(np.percentile(bootstrap_means, upper_pct))
    std_error = float(np.std(bootstrap_means, ddof=1)) if config.bootstrap_draws > 1 else 0.0

    p_superiority = float(np.mean(bootstrap_means <= 0.0))
    p_non_inferiority = float(np.mean(bootstrap_means <= -config.non_inferiority_margin_per_gw))

    return BootstrapInferenceResult(
        point_estimate=point_estimate,
        confidence_interval=(ci_lower, ci_upper),
        alpha=config.nominal_alpha,
        adjusted_alpha=adjusted_alpha,
        p_value_superiority=p_superiority,
        p_value_non_inferiority=p_non_inferiority,
        bootstrap_draws=config.bootstrap_draws,
        block_size=config.bootstrap_block_size,
        standard_error=std_error,
    )


def evaluate_evidence_against_protocol(
    paired_scores: Sequence[PairedGameweekScore],
    projection_guards: Sequence[GuardOutput] | None,
    config: StatisticalProtocolConfig,
    *,
    attempt_number: int = 1,
    is_confirmation_available: bool = False,
    confirmation_registry: ConfirmationRegistry | None = None,
    confirmation_attempt_id: str | None = None,
    seed: int = 42,
) -> PromotionEvidenceEvaluation:
    """Evaluate retained scores with complete guards and registry-bound confirmation.

    The legacy confirmation boolean does not establish evidence admission. Bonferroni
    allocation controls multiplicity only insofar as the bootstrap intervals are calibrated.
    """
    protocol_hash = config.compute_hash()
    reasons: list[str] = []
    limitations: list[str] = []

    if not paired_scores:
        return PromotionEvidenceEvaluation(
            verdict="invalid",
            point_estimate=0.0,
            confidence_interval=(0.0, 0.0),
            p_value=1.0,
            adjusted_alpha=config.nominal_alpha,
            season_summaries=[],
            material_loss_violated=False,
            projection_guards_passed=False,
            projection_guard_failures=[],
            reasons=["Paired gameweek scores are empty or missing"],
            admitted_limitations=["Zero gameweeks evaluated"],
            protocol_hash=protocol_hash,
            attempt_number=attempt_number,
            is_confirmation_available=False,
        )

    season_summaries = compute_season_summaries(
        paired_scores,
        config.season_material_loss_limit,
        config.segment_material_loss_limit,
        state_harm_checks_enabled=config.state_harm_checks_enabled,
    )
    material_loss_violated = any(
        s.violates_material_loss or s.violates_segment_loss for s in season_summaries
    )

    if material_loss_violated:
        for s in season_summaries:
            if s.violates_material_loss:
                reasons.append(
                    f"Season {s.season} net loss of {abs(s.net_delta):.1f} pts exceeds material limit of {s.material_loss_limit:.1f} pts"
                )
            if s.violates_segment_loss:
                for seg, loss in s.segment_losses.items():
                    if loss < -config.segment_material_loss_limit:
                        reasons.append(
                            f"Season {s.season} segment '{seg}' loss of {abs(loss):.1f} pts exceeds segment limit of {config.segment_material_loss_limit:.1f} pts"
                        )

    guard_regressions: list[str] = []
    guard_missing_evidence: list[str] = []
    guard_uncertainty: list[str] = []
    required_guards = config.required_projection_guards
    if not required_guards or len(set(required_guards)) != len(required_guards) or any(not name.strip() for name in required_guards):
        guard_missing_evidence.append("Required projection guard inventory is missing or contains duplicate/empty names")
    guards = list(projection_guards or ())
    actual_guard_names = [guard.metric_name for guard in guards]
    if len(set(actual_guard_names)) != len(actual_guard_names):
        guard_missing_evidence.append("Projection guard evidence contains duplicate metric names")
    if set(actual_guard_names) != set(required_guards):
        guard_missing_evidence.append(
            f"Projection guard inventory mismatch: required {sorted(required_guards)}, supplied {sorted(actual_guard_names)}"
        )
    if not guards:
        guard_missing_evidence.append("Projection guards missing required evidence")
    for guard in guards:
        if guard.status not in ("PASS", "FAIL", "INCONCLUSIVE", "MISSING_EVIDENCE", "UNASSESSED"):
            guard_missing_evidence.append(f"Guard '{guard.metric_name}' has unknown status evidence: {guard.status}")
        elif guard.status in ("MISSING_EVIDENCE", "UNASSESSED"):
            guard_missing_evidence.append(f"Guard '{guard.metric_name}' missing required evidence: {guard.reason}")
        elif not isinstance(guard.passed, bool) or guard.passed != (guard.status == "PASS"):
            guard_missing_evidence.append(f"Guard '{guard.metric_name}' has inconsistent pass/status evidence")
        elif (
            guard.sample_size <= 0
            or not all(math.isfinite(value) for value in (guard.estimate, guard.margin))
            or guard.margin < 0.0
            or guard.direction not in ("lower_is_better", "higher_is_better", "zero_is_ideal")
        ):
            guard_missing_evidence.append(f"Guard '{guard.metric_name}' has incomplete or non-finite evidence")
        elif (
            guard.status == "INCONCLUSIVE"
            and guard.sample_size == 1
            and guard.standard_error is None
            and guard.ci_lower is None
            and guard.ci_upper is None
            and guard.coverage == 0.0
        ):
            guard_uncertainty.append(f"Guard '{guard.metric_name}' has insufficient observations to estimate uncertainty")
        elif (
            guard.sample_size < 2
            or guard.standard_error is None
            or guard.ci_lower is None
            or guard.ci_upper is None
            or not 0.0 < guard.coverage <= 1.0
            or not all(math.isfinite(value) for value in (guard.standard_error, guard.ci_lower, guard.ci_upper))
            or guard.standard_error < 0.0
            or guard.ci_lower > guard.ci_upper
        ):
            guard_missing_evidence.append(f"Guard '{guard.metric_name}' has incomplete or non-finite evidence")
        else:
            interval_status = classify_non_inferiority_interval(guard.ci_lower, guard.ci_upper, guard.margin, guard.direction)
            if interval_status == "INCONCLUSIVE" and not guard.passed:
                guard_uncertainty.append(f"Guard '{guard.metric_name}' non-inferiority remains uncertain: {guard.reason}")
            elif interval_status != guard.status:
                guard_missing_evidence.append(f"Guard '{guard.metric_name}' status contradicts its uncertainty bounds")
            elif interval_status == "FAIL":
                guard_regressions.append(f"Guard '{guard.metric_name}' failed: {guard.reason}")

    guards_passed = not guard_regressions and not guard_missing_evidence and not guard_uncertainty
    guard_failures = guard_regressions + guard_missing_evidence + guard_uncertainty
    if guard_missing_evidence:
        reasons.extend(guard_missing_evidence)
    if guard_regressions:
        reasons.extend(guard_regressions)
    if guard_uncertainty:
        reasons.extend(guard_uncertainty)

    confirmation_admitted = False
    if confirmation_registry is not None and confirmation_attempt_id is not None:
        registration = confirmation_registry.get_attempt(confirmation_attempt_id)
        confirmation_scores = [score for score in paired_scores if score.season == config.confirmation_season]
        completed_gws = [score.gameweek for score in confirmation_scores]
        if (
            registration is not None
            and registration.status in ("in_progress", "completed")
            and registration.execution_status == "complete"
            and registration.protocol_hash == protocol_hash
            and registration.attempt_number_in_family == attempt_number
            and registration.max_family_attempts == config.max_family_attempts
            and registration.requested_seasons == (config.confirmation_season,)
            and bool(completed_gws)
            and len(set(completed_gws)) == len(completed_gws)
            and set(completed_gws) == set(registration.registered_gameweeks) == set(registration.completed_gameweeks)
            and registration.score_trace_hash == compute_score_trace_hash(confirmation_scores)
        ):
            confirmation_admitted = True
    has_required_seasons = (
        config.development_season != config.confirmation_season
        and {score.season for score in paired_scores} == {config.development_season, config.confirmation_season}
    )
    if not confirmation_admitted:
        limitations.append("Confirmation unavailable: no matching registered complete score trace")
    if not has_required_seasons:
        limitations.append("Required development and confirmation seasons are incomplete")
    if config.family_error_control == "none":
        limitations.append("Unadjusted bootstrap diagnostic; no search-wide family error control")
    protocol_approved = config.approved_by_human and bool(config.approval_reference.strip()) and config.approval_reference != "UNAPPROVED"

    bootstrap_res = run_stored_score_bootstrap(
        paired_scores,
        config,
        attempt_number=attempt_number,
        seed=seed,
    )

    ci_lower, ci_upper = bootstrap_res.confidence_interval
    point_est = bootstrap_res.point_estimate
    p_val = bootstrap_res.p_value_superiority
    if ci_upper < 0.0:
        reasons.append(
            f"Candidate net-score interval below zero (upper CI {ci_upper:.3f} < 0.0 at alpha {bootstrap_res.adjusted_alpha:.4f})"
        )

    # Invalid criteria:
    # - Missing or unassessed required projection guard evidence (contract defect; does NOT lock dead lever)
    if guard_missing_evidence:
        verdict: ScientificVerdict = "invalid"

    # Fail criteria:
    # - Material loss limit violated in any season or segment
    # - Significant net loss (ci_upper < 0)
    # - Substantive projection guard regression
    elif protocol_approved and (material_loss_violated or ci_upper < 0.0 or bool(guard_regressions)):
        verdict = "fail"

    # Pass criteria:
    # - Protocol configuration approved by human
    # - Confirmation season available and complete
    # - Positive point estimate
    # - Statistically significant superiority (ci_lower > 0.0 or p_value <= adjusted_alpha)
    # - No material loss
    # - All projection guards passed
    elif (
        protocol_approved
        and confirmation_admitted
        and has_required_seasons
        and config.family_error_control == "bonferroni"
        and point_est > 0.0
        and ci_lower > 0.0
        and guards_passed
        and not material_loss_violated
    ):
        verdict = "pass"

    # Inconclusive criteria:
    # - Unapproved protocol configuration
    # - Point estimate is positive or non-inferior, but uncertainty is too wide (ci_lower <= 0.0)
    # - OR confirmation season is not yet available (development-only evidence)
    else:
        verdict = "inconclusive"
        if not protocol_approved:
            reasons.append(
                "Numerical protocol configuration has not been approved by human; candidate recommendation capability disabled pending protocol approval"
            )
            limitations.append("Protocol unapproved; human approval barrier active")
        if not confirmation_admitted:
            reasons.append(
                "Confirmation season evidence not yet admitted or available; candidate cannot pass on development-only evidence"
            )
            limitations.append("Development-only trajectory; awaiting registered fresh confirmation")
        if ci_lower <= 0.0 <= ci_upper:
            reasons.append(
                f"Uncertainty contains zero (CI [{ci_lower:.3f}, {ci_upper:.3f}] at alpha {bootstrap_res.adjusted_alpha:.4f}); advantage not statistically distinguished"
            )

    return PromotionEvidenceEvaluation(
        verdict=verdict,
        point_estimate=point_est,
        confidence_interval=(ci_lower, ci_upper),
        p_value=p_val,
        adjusted_alpha=bootstrap_res.adjusted_alpha,
        season_summaries=season_summaries,
        material_loss_violated=material_loss_violated,
        projection_guards_passed=guards_passed,
        projection_guard_failures=guard_failures,
        reasons=reasons,
        admitted_limitations=limitations,
        protocol_hash=protocol_hash,
        attempt_number=attempt_number,
        is_confirmation_available=confirmation_admitted,
    )


def simulate_bootstrap_calibration(
    true_delta_mean: float,
    std_dev: float,
    autocorrelation: float,
    num_gameweeks: int,
    num_simulations: int,
    config: StatisticalProtocolConfig,
    *,
    seed: int = 42,
) -> dict[str, float]:
    """Diagnostic harness evaluating empirical Type I error and coverage of the block bootstrap.

    Simulates paired score differences under an AR(1) process with specified true mean and autocorrelation.
    """
    rng = np.random.default_rng(seed)
    rejections_null = 0
    coverage_count = 0

    # White noise innovation scale to achieve target total std_dev under AR(1)
    # var(X) = var(e) / (1 - rho^2) => std(e) = std_dev * sqrt(1 - rho^2)
    rho = float(np.clip(autocorrelation, -0.99, 0.99))
    innov_std = std_dev * math.sqrt(max(1e-6, 1.0 - rho**2))

    for sim in range(num_simulations):
        deltas = np.empty(num_gameweeks, dtype=float)
        current = rng.normal(true_delta_mean, std_dev)
        for t in range(num_gameweeks):
            current = true_delta_mean + rho * (current - true_delta_mean) + rng.normal(0.0, innov_std)
            deltas[t] = current

        paired = [
            PairedGameweekScore(
                season="2024-25",
                gameweek=gw + 1,
                candidate_net_points=float(deltas[gw]),
                champion_net_points=0.0,
                candidate_gross_points=float(deltas[gw]),
                champion_gross_points=0.0,
                candidate_hits_deducted=0,
                champion_hits_deducted=0,
                segment=assign_gameweek_segment(gw + 1),
            )
            for gw in range(num_gameweeks)
        ]

        boot_res = run_stored_score_bootstrap(
            paired,
            config,
            attempt_number=1,
            seed=int(rng.integers(0, 1_000_000)),
        )

        ci_l, ci_u = boot_res.confidence_interval
        if ci_l <= true_delta_mean <= ci_u:
            coverage_count += 1
        if ci_l > 0.0:
            rejections_null += 1

    return {
        "num_simulations": float(num_simulations),
        "empirical_coverage": float(coverage_count / num_simulations),
        "empirical_rejection_rate": float(rejections_null / num_simulations),
        "nominal_alpha": float(config.nominal_alpha),
    }
