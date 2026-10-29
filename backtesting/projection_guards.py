"""Substantive projection guards, component reconciliation, and staged diagnostics.

Implements Phase 6 guardrails:
1. Invariant common evaluation population, units, horizon leads, and missingness policy.
   Candidate cannot choose its own evaluation mask.
2. Durable metric definitions (formula, units, direction, ideal benchmark) retaining
   squared-error metrics appropriate for conditional-mean point forecasts.
3. Predeclared season/component applicability distinguishing inapplicable native rules,
   unavailable measurements, and required-but-missing evidence.
4. Total-to-component ledger reconciliation under native season scoring, enforcing strict
   component semantics (e.g. zero-minute haul impossibility) and canonical vocabulary.
5. Substantive non-inferiority claims against approved margins and uncertainty procedures;
   returns structured estimates, margins, uncertainty, and coverage, not only booleans.
6. Separation of optional fast prioritization screens from final safeguards.
7. Bounded Unconstrained development diagnostic with separately reported reversal evidence.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Literal, cast

import numpy as np
import pandas as pd
from scipy import stats

from backtesting.season_rules import get_rules
from models.scoring_matrix import EventComponent, Position, event_points

EvaluationPopulation = Literal["all_players", "playable_pool", "starters_xi", "squad_15"]
MetricDirection = Literal["higher_is_better", "lower_is_better", "zero_is_ideal"]
ComponentStatus = Literal[
    "applicable",
    "inapplicable_season",
    "unavailable_measurement",
    "missing_required_evidence",
]


@dataclass(frozen=True)
class EvaluationHorizonConfig:
    """Standardized multi-period evaluation horizon configuration."""

    leads: tuple[int, ...] = (1, 2, 3, 4, 5, 6)
    weights: tuple[float, ...] = (1.0, 0.84, 0.7056, 0.5927, 0.4979, 0.4182)
    missingness_policy: Literal["fail_closed", "unassessed"] = "fail_closed"


@dataclass(frozen=True)
class MetricDefinition:
    """Durable specification of an evaluation metric."""

    name: str
    formula: str
    units: str
    direction: MetricDirection
    ideal_benchmark: float
    description: str


# Durable canonical metric definitions
CANONICAL_METRICS: dict[str, MetricDefinition] = {
    "points_mse": MetricDefinition(
        name="points_mse",
        formula="mean((xp - actual_points)^2)",
        units="points^2",
        direction="lower_is_better",
        ideal_benchmark=0.0,
        description="Mean squared error for conditional-mean total points forecast.",
    ),
    "points_rmse": MetricDefinition(
        name="points_rmse",
        formula="sqrt(mean((xp - actual_points)^2))",
        units="points",
        direction="lower_is_better",
        ideal_benchmark=0.0,
        description="Root mean squared error for conditional-mean total points forecast.",
    ),
    "points_mae": MetricDefinition(
        name="points_mae",
        formula="mean(|xp - actual_points|)",
        units="points",
        direction="lower_is_better",
        ideal_benchmark=0.0,
        description="Mean absolute error of total points forecast.",
    ),
    "points_bias": MetricDefinition(
        name="points_bias",
        formula="mean(xp - actual_points)",
        units="points",
        direction="zero_is_ideal",
        ideal_benchmark=0.0,
        description="Signed calibration bias of total points forecast.",
    ),
    "calibration_ratio": MetricDefinition(
        name="calibration_ratio",
        formula="mean(xp) / mean(actual_points)",
        units="ratio",
        direction="zero_is_ideal",
        ideal_benchmark=1.0,
        description="Ratio of projected points to realized points.",
    ),
    "minutes_mae": MetricDefinition(
        name="minutes_mae",
        formula="mean(|xmins - actual_minutes|)",
        units="minutes",
        direction="lower_is_better",
        ideal_benchmark=0.0,
        description="Mean absolute error of expected playing minutes.",
    ),
    "goals_mse": MetricDefinition(
        name="goals_mse",
        formula="mean((xg - actual_goals)^2)",
        units="goals^2",
        direction="lower_is_better",
        ideal_benchmark=0.0,
        description="Mean squared error for expected goals component.",
    ),
    "assists_mse": MetricDefinition(
        name="assists_mse",
        formula="mean((xa - actual_assists)^2)",
        units="assists^2",
        direction="lower_is_better",
        ideal_benchmark=0.0,
        description="Mean squared error for expected assists component.",
    ),
    "clean_sheets_brier": MetricDefinition(
        name="clean_sheets_brier",
        formula="mean((p_cs - actual_cs)^2)",
        units="probability^2",
        direction="lower_is_better",
        ideal_benchmark=0.0,
        description="Brier score for clean sheet probability forecast.",
    ),
    "goals_conceded_mse": MetricDefinition(
        name="goals_conceded_mse",
        formula="mean((xgc - actual_conceded)^2)",
        units="goals^2",
        direction="lower_is_better",
        ideal_benchmark=0.0,
        description="Mean squared error for expected goals conceded component.",
    ),
    "saves_mse": MetricDefinition(
        name="saves_mse",
        formula="mean((xsaves - actual_saves)^2)",
        units="saves^2",
        direction="lower_is_better",
        ideal_benchmark=0.0,
        description="Mean squared error for expected saves component.",
    ),
}


@dataclass(frozen=True)
class GuardOutput:
    """Detailed statistical guard evaluation output containing estimates, margins, and uncertainty."""

    metric_name: str
    passed: bool
    status: Literal["PASS", "FAIL", "UNASSESSED", "MISSING_EVIDENCE"]
    estimate: float
    margin: float
    standard_error: float
    ci_lower: float
    ci_upper: float
    coverage: float
    sample_size: int
    direction: MetricDirection
    reason: str


@dataclass(frozen=True)
class ComponentLedger:
    """Typed canonical event component projection container."""

    minutes: float
    goals: float = 0.0
    assists: float = 0.0
    clean_sheets: float = 0.0
    goals_conceded: float = 0.0
    saves: float = 0.0
    defensive_contributions: float = 0.0
    bonus: float = 0.0
    yellow_cards: float = 0.0
    red_cards: float = 0.0
    penalties_saved: float = 0.0
    penalties_missed: float = 0.0
    own_goals: float = 0.0

    def to_dict(self) -> dict[EventComponent, float]:
        return {
            "minutes": self.minutes,
            "goals": self.goals,
            "assists": self.assists,
            "clean_sheets": self.clean_sheets,
            "goals_conceded": self.goals_conceded,
            "saves": self.saves,
            "defensive_contributions": self.defensive_contributions,
            "bonus": self.bonus,
            "yellow_cards": self.yellow_cards,
            "red_cards": self.red_cards,
            "penalties_saved": self.penalties_saved,
            "penalties_missed": self.penalties_missed,
            "own_goals": self.own_goals,
        }


@dataclass(frozen=True)
class LedgerReconciliationResult:
    """Result of reconciling total projected points against native component ledger."""

    reconciled: bool
    total_xp: float
    ledger_sum_xp: float
    discrepancy: float
    semantic_valid: bool
    semantic_violations: tuple[str, ...]
    details: dict[str, float]


@dataclass(frozen=True)
class ComponentApplicabilityDeclaration:
    """Declared component status for a specific season and ruleset."""

    season: str
    rules_version: str
    component_statuses: dict[EventComponent, ComponentStatus]
    required_components: tuple[EventComponent, ...]
    unsupported_components: tuple[EventComponent, ...]


@dataclass(frozen=True)
class ScreenResult:
    """Result of an optional fast prioritization screen."""

    verdict: Literal["PASS", "DEFERRED", "REQUIRES_FULL_REPLAY"]
    fast_metric_delta: float
    mechanism_assessed: bool
    reason: str


@dataclass(frozen=True)
class OracleMinutesDiagnostic:
    """Diagnostic analyzing component rate skill isolated from playing time uncertainty."""

    player_id: int
    actual_minutes: float
    modeled_minutes: float
    actual_points: float
    modeled_xp: float
    oracle_minutes_xp: float
    diagnostic_only: bool = True
    is_accuracy_evidence: bool = False
    disclaimer: str = (
        "Oracle-minutes performance isolated for mechanistic diagnosis only; "
        "strictly prohibited from being counted as candidate promotion or accuracy evidence."
    )


@dataclass(frozen=True)
class ReversalDiagnostic:
    """Detailed diagnostic report investigating substantial Strategic vs Unconstrained reversals."""

    has_reversal: bool
    strategic_delta: float
    unconstrained_delta: float
    reversal_magnitude: float
    reversal_category: Literal[
        "NONE",
        "HIT_PENALTY",
        "MINUTES_FLOOR",
        "BENCH_COVER",
        "DEF_STACK",
        "CALENDAR_STATE",
        "SOLVER_QUALITY",
    ]
    reasons: tuple[str, ...]
    component_breakdown: dict[str, float] = field(default_factory=dict)


def declare_component_applicability(
    season: str,
    rules_version: str | None = None,
    available_measurements: set[str] | None = None,
) -> ComponentApplicabilityDeclaration:
    """Declare native scoring component applicability for an evaluation season."""
    eff_rules_version = rules_version if rules_version is not None else season
    rules = get_rules(eff_rules_version)

    base_components: list[EventComponent] = [
        "minutes",
        "goals",
        "assists",
        "clean_sheets",
        "goals_conceded",
        "saves",
        "bonus",
        "yellow_cards",
        "red_cards",
        "own_goals",
        "penalties_saved",
        "penalties_missed",
    ]

    statuses: dict[EventComponent, ComponentStatus] = {}
    for comp in base_components:
        if available_measurements is not None and comp not in available_measurements:
            statuses[comp] = "unavailable_measurement"
        else:
            statuses[comp] = "applicable"

    # Defensive contributions (defensive_contributions)
    if rules.defensive_contributions:
        if available_measurements is not None and "defensive_contributions" not in available_measurements:
            statuses["defensive_contributions"] = "unavailable_measurement"
        else:
            statuses["defensive_contributions"] = "applicable"
    else:
        statuses["defensive_contributions"] = "inapplicable_season"

    required = cast(tuple[EventComponent, ...], tuple(c for c, s in statuses.items() if s == "applicable"))
    unsupported = cast(tuple[EventComponent, ...], tuple(c for c, s in statuses.items() if s != "applicable"))

    return ComponentApplicabilityDeclaration(
        season=season,
        rules_version=rules.version,
        component_statuses=statuses,
        required_components=required,
        unsupported_components=unsupported,
    )


def extract_evaluation_population(
    df: pd.DataFrame,
    population: EvaluationPopulation = "playable_pool",
    *,
    min_xmins: float = 30.0,
    min_xp: float = 2.0,
) -> pd.DataFrame:
    """Filter DataFrame to an invariant common evaluation population. Candidate cannot alter this mask."""
    if df.empty:
        return df

    if population == "all_players":
        return df.copy()

    if population == "playable_pool":
        xmins_col = "xmins" if "xmins" in df.columns else "expected_minutes"
        xp_col = "xp" if "xp" in df.columns else "projected_points"

        cond = pd.Series(False, index=df.index)
        if xmins_col in df.columns:
            cond = cond | (df[xmins_col].fillna(0.0) >= min_xmins)
        if xp_col in df.columns:
            cond = cond | (df[xp_col].fillna(0.0) >= min_xp)
        if xmins_col not in df.columns and xp_col not in df.columns:
            cond = df["now_cost"] > 0 if "now_cost" in df.columns else pd.Series(True, index=df.index)

        return df.loc[cond].copy()

    if population in ("starters_xi", "squad_15"):
        col = "is_starter" if population == "starters_xi" else "is_squad"
        if col in df.columns:
            return df.loc[df[col].fillna(False).astype(bool)].copy()
        return df.copy()

    raise ValueError(f"Unknown evaluation population: {population}")


def reconcile_total_to_ledger(
    total_xp: float,
    components: ComponentLedger,
    position: Position,
    season: str = "2024-25",
    *,
    tol: float = 0.05,
) -> LedgerReconciliationResult:
    """Verify that total projected points match native scoring components and enforce semantic validity."""
    rules = get_rules(season)

    # 1. Semantic validity checks
    violations: list[str] = []

    if components.minutes < 0.0 or components.minutes > 95.0:
        violations.append(f"Expected minutes {components.minutes:.2f} out of legal bounds [0, 95]")

    # Non-negativity for count/rate events
    comp_dict = components.to_dict()
    for event_key, val in comp_dict.items():
        if val < -1e-6:
            violations.append(f"Component {event_key} has illegal negative value: {val:.4f}")

    # Appearance impossibility: 0 minutes cannot produce active match events
    if components.minutes <= 1e-4:
        active_events = [
            k
            for k in ("goals", "assists", "saves", "clean_sheets", "defensive_contributions")
            if comp_dict[k] > 1e-4  # pyright: ignore[reportArgumentType]
        ]
        if active_events:
            violations.append(f"Zero playing minutes cannot yield positive active event projections: {active_events}")

    # Clean sheet impossibility for forwards
    if position == "F" and components.clean_sheets > 0.05:
        violations.append("Forwards do not receive clean sheet points under official rules")

    # 2. Compute native component point contribution using canonical event_points
    ledger_sum = 0.0
    details: dict[str, float] = {}

    for comp_name, qty in comp_dict.items():
        pts = event_points(comp_name, position, qty, rules_version=rules.version)
        ledger_sum += pts
        details[f"{comp_name}_pts"] = round(pts, 4)

    diff = abs(total_xp - ledger_sum)
    reconciled = diff <= tol

    return LedgerReconciliationResult(
        reconciled=reconciled,
        total_xp=total_xp,
        ledger_sum_xp=round(ledger_sum, 4),
        discrepancy=round(diff, 4),
        semantic_valid=(len(violations) == 0),
        semantic_violations=tuple(violations),
        details=details,
    )


def evaluate_oracle_minutes_mechanism(
    player_id: int,
    actual_minutes: float,
    modeled_minutes: float,
    actual_points: float,
    modeled_xp: float,
    rate_components: ComponentLedger,
    position: Position,
    season: str = "2024-25",
) -> OracleMinutesDiagnostic:
    """Diagnose event rate modeling mechanisms by scaling rate projections by actual realized minutes.

    Mechanistic diagnostic only; strictly prohibited from promotion or accuracy claims.
    """
    scale = (actual_minutes / modeled_minutes) if modeled_minutes > 1e-4 else 0.0
    oracle_ledger = ComponentLedger(
        minutes=actual_minutes,
        goals=rate_components.goals * scale,
        assists=rate_components.assists * scale,
        clean_sheets=rate_components.clean_sheets if actual_minutes >= 60.0 else 0.0,
        goals_conceded=rate_components.goals_conceded * scale,
        saves=rate_components.saves * scale,
        defensive_contributions=rate_components.defensive_contributions * scale,
        bonus=rate_components.bonus * scale,
        yellow_cards=rate_components.yellow_cards * scale,
        red_cards=rate_components.red_cards * scale,
        penalties_saved=rate_components.penalties_saved * scale,
        penalties_missed=rate_components.penalties_missed * scale,
        own_goals=rate_components.own_goals * scale,
    )

    reconciled = reconcile_total_to_ledger(0.0, oracle_ledger, position, season)
    oracle_xp = reconciled.ledger_sum_xp

    return OracleMinutesDiagnostic(
        player_id=player_id,
        actual_minutes=actual_minutes,
        modeled_minutes=modeled_minutes,
        actual_points=actual_points,
        modeled_xp=modeled_xp,
        oracle_minutes_xp=oracle_xp,
        diagnostic_only=True,
        is_accuracy_evidence=False,
    )


def evaluate_non_inferiority_guard(
    candidate_errors: pd.Series | np.ndarray | Sequence[float],
    champion_errors: pd.Series | np.ndarray | Sequence[float],
    *,
    metric_name: str,
    meaningful_margin: float,
    alpha: float = 0.05,
    direction: MetricDirection = "lower_is_better",
    required: bool = True,
) -> GuardOutput:
    """Evaluate substantive non-inferiority against an approved meaningful margin with uncertainty.

    For error metrics (direction == 'lower_is_better'):
    Delta = mean(candidate) - mean(champion). Non-inferiority means Candidate is not worse than
    Champion by more than margin (Upper CI <= margin).

    For calibration bias (direction == 'zero_is_ideal'):
    Equivalence requires both CI bounds to lie within [-margin, +margin].

    Absence of statistically significant deterioration is insufficient proof of acceptable regression.
    """
    if isinstance(candidate_errors, pd.Series) and isinstance(champion_errors, pd.Series):
        aligned = pd.concat([candidate_errors.rename("cand"), champion_errors.rename("champ")], axis=1, join="inner").dropna()
        cand = aligned["cand"].to_numpy(dtype=float)
        champ = aligned["champ"].to_numpy(dtype=float)
    else:
        cand = np.asarray(candidate_errors, dtype=float)
        champ = np.asarray(champion_errors, dtype=float)
        if len(cand) != len(champ):
            raise ValueError(f"Unpaired candidate ({len(cand)}) and champion ({len(champ)}) evaluation samples")

    if len(cand) == 0 or len(champ) == 0:
        return GuardOutput(
            metric_name=metric_name,
            passed=False,
            status="MISSING_EVIDENCE" if required else "UNASSESSED",
            estimate=0.0,
            margin=meaningful_margin,
            standard_error=0.0,
            ci_lower=0.0,
            ci_upper=0.0,
            coverage=0.0,
            sample_size=0,
            direction=direction,
            reason="Missing or empty evaluation samples",
        )

    n = len(cand)
    paired_diff = cand - champ
    estimate = float(np.mean(paired_diff))
    se = float(stats.sem(paired_diff)) if n > 1 else 0.0

    z_crit = float(stats.norm.ppf(1.0 - alpha))
    margin = float(meaningful_margin)
    conf_pct = int(round((1.0 - alpha) * 100))

    if direction == "lower_is_better":
        ci_lower = float(estimate - z_crit * se)
        ci_upper = float(estimate + z_crit * se)
        passed = bool(ci_upper <= margin)
        reason = (
            f"Non-inferior: upper {conf_pct}% bound {ci_upper:.4f} <= margin {margin:.4f}"
            if passed
            else f"Failed non-inferiority: upper {conf_pct}% bound {ci_upper:.4f} exceeds margin {margin:.4f}"
        )
    elif direction == "higher_is_better":
        ci_lower = float(estimate - z_crit * se)
        ci_upper = float(estimate + z_crit * se)
        passed = bool(ci_lower >= -margin)
        reason = (
            f"Non-inferior: lower {conf_pct}% bound {ci_lower:.4f} >= -margin {-margin:.4f}"
            if passed
            else f"Failed non-inferiority: lower {conf_pct}% bound {ci_lower:.4f} lags beyond margin {-margin:.4f}"
        )
    else:  # zero_is_ideal (bias)
        z_two_sided = float(stats.norm.ppf(1.0 - alpha / 2.0))
        ci_lower = float(estimate - z_two_sided * se)
        ci_upper = float(estimate + z_two_sided * se)
        # Equivalence requires the entire two-sided CI to remain within [-margin, +margin]
        passed = bool(ci_lower >= -margin and ci_upper <= margin)
        reason = (
            f"Calibration equivalence verified: {conf_pct}% CI [{ci_lower:.4f}, {ci_upper:.4f}] within margin [{-margin:.4f}, {margin:.4f}]"
            if passed
            else f"Calibration equivalence failed: {conf_pct}% CI [{ci_lower:.4f}, {ci_upper:.4f}] exceeds margin [{-margin:.4f}, {margin:.4f}]"
        )

    status: Literal["PASS", "FAIL", "UNASSESSED", "MISSING_EVIDENCE"] = "PASS" if passed else "FAIL"

    return GuardOutput(
        metric_name=metric_name,
        passed=passed,
        status=status,
        estimate=round(estimate, 4),
        margin=round(margin, 4),
        standard_error=round(se, 4),
        ci_lower=round(ci_lower, 4),
        ci_upper=round(ci_upper, 4),
        coverage=1.0 - alpha,
        sample_size=n,
        direction=direction,
        reason=reason,
    )


def evaluate_composite_non_inferiority(
    primary_guard: GuardOutput,
    component_guards: Sequence[GuardOutput],
) -> tuple[bool, str]:
    """Evaluate multi-component non-inferiority without imposing every-component improvement.

    Acceptable when primary total performance is non-inferior and no required component
    shows demonstrated harm exceeding its meaningful margin.
    """
    if not primary_guard.passed:
        return False, f"Primary metric {primary_guard.metric_name} failed non-inferiority: {primary_guard.reason}"

    failed_components = [g for g in component_guards if not g.passed and g.status != "UNASSESSED"]
    if failed_components:
        failed_names = ", ".join(f"{g.metric_name} ({g.reason})" for g in failed_components)
        return False, f"Required component non-inferiority breached: {failed_names}"

    return True, "Primary and all required component non-inferiority guards passed."


def evaluate_prioritization_screen(
    fast_metric_delta: float,
    threshold: float = 0.0,
    can_assess_mechanism: bool = True,
) -> ScreenResult:
    """Evaluate an optional fast screen. Failed or deferred screen does not yield a Dead Lever."""
    if not can_assess_mechanism:
        return ScreenResult(
            verdict="REQUIRES_FULL_REPLAY",
            fast_metric_delta=fast_metric_delta,
            mechanism_assessed=False,
            reason="Fast screen cannot evaluate mechanism (e.g. transfer friction, multi-week state); route to full replay.",
        )

    if fast_metric_delta >= threshold:
        return ScreenResult(
            verdict="PASS",
            fast_metric_delta=fast_metric_delta,
            mechanism_assessed=True,
            reason=f"Fast screen passed with delta {fast_metric_delta:.4f} >= {threshold:.4f}",
        )

    return ScreenResult(
        verdict="DEFERRED",
        fast_metric_delta=fast_metric_delta,
        mechanism_assessed=True,
        reason=f"Fast screen deferred (delta {fast_metric_delta:.4f} < {threshold:.4f}); Candidate not declared Dead Lever without full replay.",
    )


def diagnose_unconstrained_reversal(
    strategic_net_delta: float,
    unconstrained_net_delta: float,
    *,
    reversal_threshold: float = 2.0,
    penalties_delta: float = 0.0,
    transfers_delta: float = 0.0,
    minutes_floor_delta: float = 0.0,
    bench_cover_delta: float = 0.0,
    def_stack_delta: float = 0.0,
    calendar_state_delta: float = 0.0,
    solver_quality_delta: float = 0.0,
) -> ReversalDiagnostic:
    """Predeclared diagnostic investigating substantial reversals between Strategic and Unconstrained arms.

    Investigates across forecasts, penalties, transfers, solver quality, and state/calendar interactions.
    Strategic primary cannot be selected or averaged away after outcomes.
    """
    diff = unconstrained_net_delta - strategic_net_delta
    has_reversal = (unconstrained_net_delta > 0.0 and strategic_net_delta < 0.0) or (diff >= reversal_threshold)

    if not has_reversal:
        return ReversalDiagnostic(
            has_reversal=False,
            strategic_delta=strategic_net_delta,
            unconstrained_delta=unconstrained_net_delta,
            reversal_magnitude=diff,
            reversal_category="NONE",
            reasons=("No substantial reversal between Strategic and Unconstrained arms.",),
        )

    reasons: list[str] = [
        f"Substantial policy reversal detected: Unconstrained delta = {unconstrained_net_delta:+.2f} pts vs Strategic delta = {strategic_net_delta:+.2f} pts (gap = {diff:.2f} pts)."
    ]

    breakdown: dict[str, float] = {
        "penalties_diff": penalties_delta,
        "transfers_diff": transfers_delta,
        "minutes_floor_diff": minutes_floor_delta,
        "bench_cover_diff": bench_cover_delta,
        "def_stack_diff": def_stack_delta,
        "calendar_state_diff": calendar_state_delta,
        "solver_quality_diff": solver_quality_delta,
    }

    # Determine dominant driver
    category: Literal[
        "NONE",
        "HIT_PENALTY",
        "MINUTES_FLOOR",
        "BENCH_COVER",
        "DEF_STACK",
        "CALENDAR_STATE",
        "SOLVER_QUALITY",
    ] = "NONE"

    if abs(penalties_delta) >= 1.5:
        category = "HIT_PENALTY"
        reasons.append(f"Reversal driven primarily by paid transfer hit penalties: delta penalty impact {penalties_delta:+.2f} pts.")
    elif abs(minutes_floor_delta) >= 1.5:
        category = "MINUTES_FLOOR"
        reasons.append(f"Reversal driven by starter xMins floor requirement: delta {minutes_floor_delta:+.2f} pts.")
    elif abs(bench_cover_delta) >= 1.5:
        category = "BENCH_COVER"
        reasons.append(f"Reversal driven by bench cover requirement: delta {bench_cover_delta:+.2f} pts.")
    elif abs(def_stack_delta) >= 1.5:
        category = "DEF_STACK"
        reasons.append(f"Reversal driven by defensive stack cap constraint: delta {def_stack_delta:+.2f} pts.")
    elif abs(solver_quality_delta) >= 1.5:
        category = "SOLVER_QUALITY"
        reasons.append(f"Reversal driven by solver quality / optimality gap differences: delta {solver_quality_delta:+.2f} pts.")
    else:
        category = "CALENDAR_STATE"
        reasons.append("Reversal driven by multi-period calendar and state dynamics.")

    reasons.append("Policy invariant: Strategic primary remains authoritative; Unconstrained results cannot override or be averaged into evaluation.")

    return ReversalDiagnostic(
        has_reversal=True,
        strategic_delta=strategic_net_delta,
        unconstrained_delta=unconstrained_net_delta,
        reversal_magnitude=round(diff, 3),
        reversal_category=category,
        reasons=tuple(reasons),
        component_breakdown=breakdown,
    )
