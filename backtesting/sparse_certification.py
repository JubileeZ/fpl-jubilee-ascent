"""Sparse Champion confirmation calibration, vectorized parity, and certification harness (ADR 0070)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Literal, NotRequired, TypedDict

import numpy as np
from scipy import stats

from backtesting.evaluation_protocol import material_digest
from backtesting.evidence_statistics import (
    CONTIGUOUS_SEGMENT_BOUNDS,
    EARLY_HARM_MIN_GW,
    EARLY_HARM_P_THRESHOLD,
    OBF_ALPHA_SCHEDULE,
    PairedGameweekScore,
    StatisticalProtocolConfig,
    assign_gameweek_segment,
    evaluate_early_harm_fallback,
    run_kendall_pw_hac_test,
)
from backtesting.promotion_evidence import (
    MANDATORY_GUARDS,
    MILP_SEGMENT_REGRESSION_TOLERANCES,
    statistical_protocol_config_from_dict,
)
from backtesting.season_rules import load_season_lifecycle

PROJECT_ROOT = Path(__file__).resolve().parents[1]

TUNING_SEED = 21101
CERTIFICATION_SEED = 21102
FALLBACK_ADVISORY_SEED = 21103
DEFAULT_NUM_SIMULATIONS = 20_000
DEFAULT_FPL_DELTA_SD_PER_GW = 8.5
UPPER_STRESS_FPL_DELTA_SD_PER_GW = 11.0
DEFAULT_ADVISORY_GW1_4_LOSS_LIMIT = round(4.0 * float(MILP_SEGMENT_REGRESSION_TOLERANCES["cold_start"]), 1)
EMPIRICAL_GW_VARIANCE_PROFILE: tuple[float, ...] = (0.0, 0.0, 0.30, 0.75, *([1.0] * 34))
DEFAULT_SHOCK_GWS: tuple[int, ...] = (15, 19, 30, 34)
REGISTERED_CHECKPOINTS: tuple[int, ...] = (15, 30, 38)

MAX_FALSE_FULL_PASS_UPPER_95 = 0.05
MIN_PRIMARY_POWER_LOWER_95 = 1.0 / 3.0
MAX_FALSE_EXCLUSION_UPPER_95 = 0.05
PRIMARY_MAX_RETRIES = 0
FALLBACK_MAX_RETRIES = 1
DEFAULT_GW38_EXPIRY_HOURS = 24.0 + 14.0 * 24.0
DEFAULT_SPARSE_COMPLETED_SEGMENTS: dict[str, tuple[tuple[int, int], ...]] = {
    "15": ((1, 4),),
    "30": ((1, 4), (5, 19)),
    "38": ((1, 4), (5, 19), (20, 38)),
}
CERTIFICATION_SUMMARY_KEYS: tuple[str, ...] = (
    "manifest_digest",
    "parity_passed",
    "tuning",
    "primary_run",
    "fallback_run",
    "retries_used",
    "certified",
    "certified_mode",
    "certification_seed",
    "live_adoption_blocked",
)

ScenarioCategory = Literal["null", "mixed_null", "power", "harmful"]
DependenceRegime = Literal["mild", "persistent"]
InnovationDist = Literal["gaussian", "student_t5"]


class _RegimeParams(TypedDict):
    dependence_regime: DependenceRegime
    phi_ar: float
    rho_champ: float
    innovation_dist: InnovationDist
    shock_gws: tuple[int, ...]
    shock_multiplier: float
    gw_variance_profile: NotRequired[tuple[float, ...] | None]


class CertificationVerificationResult(TypedDict):
    passed: bool
    errors: list[str]
    drifted_files: list[str]
    certified: Any
    certified_mode: Any
    certification_digest: Any
    statistical_protocol_hash: Any
    manifest_digest_match: bool
    canonical_digest_match: bool
    evaluator_revisions_match: bool


class VectorizedEarlyHarmResult(TypedDict):
    triggered: np.ndarray
    statistical_triggered: np.ndarray
    gw1_4_floor_breached: np.ndarray
    cumulative_p_harm: np.ndarray
    segment_p_harms: dict[str, np.ndarray]


EVALUATOR_REVISION_PATHS: tuple[str, ...] = (
    "backtesting/evaluation_protocol.py",
    "backtesting/evidence_statistics.py",
    "backtesting/projection_guards.py",
    "backtesting/promotion_evidence.py",
    "backtesting/sparse_certification.py",
)


@dataclass(frozen=True)
class ScenarioSpec:
    """Preregistered synthetic 38-GW trajectory scenario definition."""

    scenario_id: str
    category: ScenarioCategory
    slate_size: int
    finalist_effects_sd: tuple[float, ...]
    dependence_regime: DependenceRegime
    phi_ar: float
    rho_champ: float
    innovation_dist: InnovationDist
    shock_gws: tuple[int, ...] = DEFAULT_SHOCK_GWS
    shock_multiplier: float = 1.5
    safeguards_pass_from_gw: int = 15
    gw1_4_effects_sd: tuple[float, ...] | None = None
    finalist_effects_pts_per_year: tuple[float, ...] | None = None
    gw1_4_effects_pts_total: tuple[float, ...] | None = None
    gw_variance_profile: tuple[float, ...] | None = None
    is_primary_power: bool = False
    description: str = ""

    def __post_init__(self) -> None:
        if self.slate_size not in (1, 2):
            raise ValueError(f"slate_size must be 1 or 2, got {self.slate_size}")
        if len(self.finalist_effects_sd) != self.slate_size:
            raise ValueError("finalist_effects_sd length must equal slate_size")
        if self.gw1_4_effects_sd is not None and len(self.gw1_4_effects_sd) != self.slate_size:
            raise ValueError("gw1_4_effects_sd length must equal slate_size")
        if self.finalist_effects_pts_per_year is not None:
            if len(self.finalist_effects_pts_per_year) != self.slate_size:
                raise ValueError("finalist_effects_pts_per_year length must equal slate_size")
            if any(val != 0.0 for val in self.finalist_effects_sd):
                raise ValueError("Cannot mix non-zero finalist_effects_sd with finalist_effects_pts_per_year")
        if self.gw1_4_effects_pts_total is not None:
            if len(self.gw1_4_effects_pts_total) != self.slate_size:
                raise ValueError("gw1_4_effects_pts_total length must equal slate_size")
            if self.gw1_4_effects_sd is not None:
                raise ValueError("Cannot specify both gw1_4_effects_sd and gw1_4_effects_pts_total")
        if self.gw_variance_profile is not None:
            if len(self.gw_variance_profile) != 38 or any(
                not math.isfinite(float(w)) or float(w) < 0.0 for w in self.gw_variance_profile
            ):
                raise ValueError("gw_variance_profile must be 38 finite nonnegative weights")
            if not any(float(w) > 0.0 for w in self.gw_variance_profile):
                raise ValueError("gw_variance_profile must include at least one positive weight")
        if not 0.0 <= self.phi_ar < 1.0:
            raise ValueError("phi_ar must lie in [0, 1)")
        if not 0.0 <= self.rho_champ <= 1.0:
            raise ValueError("rho_champ must lie in [0, 1]")

    def _effective_season_effects(self) -> tuple[float, ...]:
        return (
            self.finalist_effects_pts_per_year
            if self.finalist_effects_pts_per_year is not None
            else self.finalist_effects_sd
        )

    def _effective_gw1_4_effects(self) -> tuple[float, ...] | None:
        return (
            self.gw1_4_effects_pts_total
            if self.gw1_4_effects_pts_total is not None
            else self.gw1_4_effects_sd
        )

    @property
    def null_indices(self) -> list[int]:
        eff = self._effective_season_effects()
        gw1_4 = self._effective_gw1_4_effects()
        return [
            j
            for j in range(self.slate_size)
            if eff[j] == 0.0 and (gw1_4 is None or gw1_4[j] == 0.0)
        ]

    @property
    def improving_indices(self) -> list[int]:
        eff = self._effective_season_effects()
        return [j for j in range(self.slate_size) if eff[j] > 0.0]

    @property
    def harmful_indices(self) -> list[int]:
        eff = self._effective_season_effects()
        gw1_4 = self._effective_gw1_4_effects()
        return [
            j
            for j in range(self.slate_size)
            if eff[j] < 0.0 or (gw1_4 is not None and gw1_4[j] < 0.0)
        ]

    @property
    def non_harmful_indices(self) -> list[int]:
        harmful = set(self.harmful_indices)
        return [j for j in range(self.slate_size) if j not in harmful]


def compute_canonical_digest(payload: Any) -> str:
    """Compute canonical SHA-256 hex digest with sorted keys and strict finite JSON."""
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_preregistered_scenario_grid() -> tuple[ScenarioSpec, ...]:
    """Return the preregistered certification scenario grid covering null, mixed-null, standardized power, empirical fixed-pt diagnostics, and harm."""
    mild: _RegimeParams = {
        "dependence_regime": "mild",
        "phi_ar": 0.20,
        "rho_champ": 0.50,
        "innovation_dist": "gaussian",
        "shock_gws": DEFAULT_SHOCK_GWS,
        "shock_multiplier": 1.50,
    }
    persistent: _RegimeParams = {
        "dependence_regime": "persistent",
        "phi_ar": 0.55,
        "rho_champ": 0.50,
        "innovation_dist": "student_t5",
        "shock_gws": DEFAULT_SHOCK_GWS,
        "shock_multiplier": 2.00,
    }
    empirical_mild: _RegimeParams = {
        "dependence_regime": "mild",
        "phi_ar": 0.10,
        "rho_champ": 0.50,
        "innovation_dist": "gaussian",
        "shock_gws": DEFAULT_SHOCK_GWS,
        "shock_multiplier": 1.50,
        "gw_variance_profile": EMPIRICAL_GW_VARIANCE_PROFILE,
    }
    return (
        # M=1 all-null (mild & persistent, early GW15 vs late GW30 safeguards)
        ScenarioSpec("m1_null_mild_gw15", "null", 1, (0.0,), safeguards_pass_from_gw=15, description="M=1 all-null, mild, guards from GW15", **mild),
        ScenarioSpec("m1_null_mild_gw30", "null", 1, (0.0,), safeguards_pass_from_gw=30, description="M=1 all-null, mild, guards from GW30", **mild),
        ScenarioSpec("m1_null_persistent_gw15", "null", 1, (0.0,), safeguards_pass_from_gw=15, description="M=1 all-null, persistent Student-t(5), guards from GW15", **persistent),
        ScenarioSpec("m1_null_persistent_gw30", "null", 1, (0.0,), safeguards_pass_from_gw=30, description="M=1 all-null, persistent Student-t(5), guards from GW30", **persistent),
        # M=2 all-null (mild & persistent, early GW15 vs late GW30 safeguards)
        ScenarioSpec("m2_null_mild_gw15", "null", 2, (0.0, 0.0), safeguards_pass_from_gw=15, description="M=2 all-null, mild, guards from GW15", **mild),
        ScenarioSpec("m2_null_mild_gw30", "null", 2, (0.0, 0.0), safeguards_pass_from_gw=30, description="M=2 all-null, mild, guards from GW30", **mild),
        ScenarioSpec("m2_null_persistent_gw15", "null", 2, (0.0, 0.0), safeguards_pass_from_gw=15, description="M=2 all-null, persistent Student-t(5), guards from GW15", **persistent),
        ScenarioSpec("m2_null_persistent_gw30", "null", 2, (0.0, 0.0), safeguards_pass_from_gw=30, description="M=2 all-null, persistent Student-t(5), guards from GW30", **persistent),
        # M=2 mixed-null in BOTH rank orders under mild & persistent
        ScenarioSpec(
            "m2_mixed_r1_imp_r2_null_mild_gw15",
            "mixed_null",
            2,
            (0.40, 0.0),
            safeguards_pass_from_gw=15,
            is_primary_power=True,
            description="Standardized SNR benchmark GW38 power + mixed-null (rank1=+0.40 SD, rank2=null, mild, guards GW15)",
            **mild,
        ),
        ScenarioSpec("m2_mixed_r1_null_r2_imp_mild_gw15", "mixed_null", 2, (0.0, 0.40), safeguards_pass_from_gw=15, description="M=2 mixed-null (rank1=null, rank2=+0.40 SD SNR benchmark, mild, guards GW15)", **mild),
        ScenarioSpec("m2_mixed_r1_imp_r2_null_persistent_gw15", "mixed_null", 2, (0.40, 0.0), safeguards_pass_from_gw=15, description="M=2 mixed-null (rank1=+0.40 SD SNR benchmark, rank2=null, persistent, guards GW15)", **persistent),
        ScenarioSpec("m2_mixed_r1_null_r2_imp_persistent_gw15", "mixed_null", 2, (0.0, 0.40), safeguards_pass_from_gw=15, description="M=2 mixed-null (rank1=null, rank2=+0.40 SD SNR benchmark, persistent, guards GW15)", **persistent),
        ScenarioSpec("m2_mixed_r1_imp_r2_null_mild_gw30", "mixed_null", 2, (0.40, 0.0), safeguards_pass_from_gw=30, description="M=2 mixed-null (rank1=+0.40 SD SNR benchmark, rank2=null, mild, guards GW30)", **mild),
        ScenarioSpec("m2_mixed_r1_null_r2_imp_mild_gw30", "mixed_null", 2, (0.0, 0.40), safeguards_pass_from_gw=30, description="M=2 mixed-null (rank1=null, rank2=+0.40 SD SNR benchmark, mild, guards GW30)", **mild),
        # Additional standardized SNR power scenarios (+0.20, +0.60 SD)
        ScenarioSpec("m1_power_pos020_mild_gw15", "power", 1, (0.20,), safeguards_pass_from_gw=15, description="M=1 +0.20 SD standardized SNR power, mild, guards GW15", **mild),
        ScenarioSpec("m2_power_pos020_mixed_mild_gw15", "mixed_null", 2, (0.20, 0.0), safeguards_pass_from_gw=15, description="M=2 +0.20 SD standardized SNR + null, mild, guards GW15", **mild),
        ScenarioSpec("m1_power_pos060_mild_gw15", "power", 1, (0.60,), safeguards_pass_from_gw=15, description="M=1 +0.60 SD standardized SNR power, mild, guards GW15", **mild),
        ScenarioSpec("m2_power_pos060_mixed_mild_gw15", "mixed_null", 2, (0.60, 0.0), safeguards_pass_from_gw=15, description="M=2 +0.60 SD standardized SNR + null, mild, guards GW15", **mild),
        # Genuinely harmful scenarios (-0.40, -0.60, -0.80 SD & decoupled -40 pt GW1-4 collapse)
        ScenarioSpec("m1_harm_neg040_mild_gw15", "harmful", 1, (-0.40,), safeguards_pass_from_gw=15, description="M=1 -0.40 SD harmful, mild", **mild),
        ScenarioSpec("m1_harm_neg060_mild_gw15", "harmful", 1, (-0.60,), safeguards_pass_from_gw=15, description="M=1 -0.60 SD harmful, mild", **mild),
        ScenarioSpec("m1_harm_neg080_mild_gw15", "harmful", 1, (-0.80,), safeguards_pass_from_gw=15, description="M=1 -0.80 SD harmful, mild", **mild),
        ScenarioSpec("m1_harm_neg060_persistent_gw15", "harmful", 1, (-0.60,), safeguards_pass_from_gw=15, description="M=1 -0.60 SD harmful, persistent", **persistent),
        ScenarioSpec(
            "m1_harm_severe_gw1_4_mild_gw15",
            "harmful",
            1,
            (0.0,),
            gw1_4_effects_pts_total=(-40.0,),
            safeguards_pass_from_gw=15,
            description="M=1 severe GW1-4 collapse (-40 pts total E[GW1-4]), then neutral",
            **mild,
        ),
        ScenarioSpec("m2_harm_r1_neg060_r2_null_mild_gw15", "harmful", 2, (-0.60, 0.0), safeguards_pass_from_gw=15, description="M=2 rank1=-0.60 SD harmful + rank2=null, mild", **mild),
        # Decoupled fixed-FPL-points/year empirical rolling-MILP scenarios (locked-GW1/GW2 ramp, phi=0.10)
        ScenarioSpec("m1_empirical_pos40_pts_yr", "power", 1, (0.0,), finalist_effects_pts_per_year=(40.0,), safeguards_pass_from_gw=15, description="M=1 empirical +40 pts/yr (locked GW1/2, phi=0.10)", **empirical_mild),
        ScenarioSpec("m1_empirical_pos60_pts_yr", "power", 1, (0.0,), finalist_effects_pts_per_year=(60.0,), safeguards_pass_from_gw=15, description="M=1 empirical +60 pts/yr (locked GW1/2, phi=0.10)", **empirical_mild),
        ScenarioSpec("m1_empirical_pos80_pts_yr", "power", 1, (0.0,), finalist_effects_pts_per_year=(80.0,), safeguards_pass_from_gw=15, description="M=1 empirical +80 pts/yr (locked GW1/2, phi=0.10)", **empirical_mild),
        ScenarioSpec("m2_empirical_pos60_mixed_pts_yr", "mixed_null", 2, (0.0, 0.0), finalist_effects_pts_per_year=(60.0, 0.0), safeguards_pass_from_gw=15, description="M=2 empirical +60 pts/yr + null (locked GW1/2, phi=0.10)", **empirical_mild),
        ScenarioSpec("m1_empirical_neg40_pts_yr", "harmful", 1, (0.0,), finalist_effects_pts_per_year=(-40.0,), safeguards_pass_from_gw=15, description="M=1 empirical -40 pts/yr harmful (locked GW1/2, phi=0.10)", **empirical_mild),
        ScenarioSpec("m1_empirical_neg80_pts_yr", "harmful", 1, (0.0,), finalist_effects_pts_per_year=(-80.0,), safeguards_pass_from_gw=15, description="M=1 empirical -80 pts/yr harmful (locked GW1/2, phi=0.10)", **empirical_mild),
    )


def _evaluator_revisions(project_root: Path | None = None) -> dict[str, str]:
    root = project_root or PROJECT_ROOT
    material = {rel: (root / rel).read_bytes() for rel in EVALUATOR_REVISION_PATHS if (root / rel).is_file()}
    file_hashes = {rel: hashlib.sha256(raw).hexdigest() for rel, raw in sorted(material.items())}
    return {
        **file_hashes,
        "closure_digest": material_digest(material),
    }


def build_preregistration_manifest(
    *,
    num_simulations: int = DEFAULT_NUM_SIMULATIONS,
    fpl_delta_sd_per_gw: float = DEFAULT_FPL_DELTA_SD_PER_GW,
    tuning_seed: int = TUNING_SEED,
    certification_seed: int = CERTIFICATION_SEED,
    fallback_seed: int = FALLBACK_ADVISORY_SEED,
    project_root: Path | None = None,
) -> dict[str, Any]:
    """Build immutable preregistration manifest with canonical SHA-256 digest."""
    if num_simulations < 10 or fpl_delta_sd_per_gw <= 0.0:
        raise ValueError("Invalid simulation run size or FPL SD scale")
    grid = build_preregistered_scenario_grid()
    body: dict[str, Any] = {
        "manifest_version": 2,
        "protocol_target_version": "v2.0",
        "authority_references": [
            "docs/adr/0070-weekly-planner-selection-and-champion-adoption.md",
            "docs/adr/0071-certified-solver-budget-and-milp-qualification-calibration.md",
            "docs/product/champion-adoption-implementation.md",
            "issues #195, #196, #201, #211",
        ],
        "evaluator_revisions": _evaluator_revisions(project_root=project_root),
        "simulator_config": {
            "num_gameweeks": 38,
            "registered_checkpoints": list(REGISTERED_CHECKPOINTS),
            "fpl_delta_sd_per_gw": float(fpl_delta_sd_per_gw),
            "upper_stress_fpl_delta_sd_per_gw": float(UPPER_STRESS_FPL_DELTA_SD_PER_GW),
            "empirical_gw_variance_profile": list(EMPIRICAL_GW_VARIANCE_PROFILE),
            "advisory_gw1_4_loss_limit": float(DEFAULT_ADVISORY_GW1_4_LOSS_LIMIT),
            "fpl_scale_basis": (
                f"Pooled empirical non-zero 6-GW rolling-MILP weekly net-points SD calibrated at "
                f"{DEFAULT_FPL_DELTA_SD_PER_GW:.1f} pts/GW (EXT-01_1..EXT-05_1 S-1/S-2 active pool; "
                f"{UPPER_STRESS_FPL_DELTA_SD_PER_GW:.1f} pts/GW upper stress) with locked-GW1/GW2 empirical "
                f"variance ramp. Per 2026-11-22 ADR 0070 amendment, gw1_4_material_loss_limit="
                f"{DEFAULT_ADVISORY_GW1_4_LOSS_LIMIT:.1f} (ADR 0071 cold_start 4*8.9) is advisory-only in "
                "advisory mode, making calibrated superiority thresholds 100% scale-free; fixed-pts/yr "
                "empirical power scenarios decouple effect sizes from fpl_delta_sd_per_gw."
            ),
            "shock_gws": list(DEFAULT_SHOCK_GWS),
            "early_harm_min_gw": EARLY_HARM_MIN_GW,
            "early_harm_p_threshold": EARLY_HARM_P_THRESHOLD,
            "completed_segments_by_checkpoint": {
                "15": [[1, 4]],
                "30": [[1, 4], [5, 19]],
                "38": [[1, 4], [5, 19], [20, 38]],
            },
            "unused_alpha_policy": "discard",
            "gw38_expiry_hours_after_last_kickoff": DEFAULT_GW38_EXPIRY_HOURS,
        },
        "tuning_seed": tuning_seed,
        "certification_seed": certification_seed,
        "fallback_seed": fallback_seed,
        "num_simulations": num_simulations,
        "retry_budget": {
            "primary_max_retries": PRIMARY_MAX_RETRIES,
            "fallback_max_retries": FALLBACK_MAX_RETRIES,
            "fallback_trigger_rule": (
                f"Execute 1 predeclared advisory Early-Harm run on untouched fallback_seed={fallback_seed} ONLY if "
                f"enforced statistical Early-Harm fails its <=5% false terminal exclusion upper-95 gate "
                f"on seed={certification_seed} while false full pass <=5% and primary GW38 power >=1/3 both hold."
            ),
        },
        "acceptance_rules": {
            "confidence_method": "one_sided_95_clopper_pearson_exact_binomial",
            "max_false_full_pass_upper_95": MAX_FALSE_FULL_PASS_UPPER_95,
            "min_primary_gw38_power_lower_95": MIN_PRIMARY_POWER_LOWER_95,
            "max_statistical_false_exclusion_upper_95": MAX_FALSE_EXCLUSION_UPPER_95,
        },
        "scenario_grid": [asdict(spec) for spec in grid],
    }
    return {**body, "manifest_digest": compute_canonical_digest(body)}


def clopper_pearson_one_sided_95(k: int, n: int) -> dict[str, Any]:
    """Exact one-sided 95% Clopper-Pearson binomial confidence bounds and exact event counts."""
    if n <= 0 or not 0 <= k <= n:
        raise ValueError(f"Invalid binomial counts k={k}, n={n}")
    lower_95 = 0.0 if k == 0 else float(stats.beta.ppf(0.05, k, n - k + 1))
    upper_95 = 1.0 if k == n else float(stats.beta.ppf(0.95, k + 1, n - k))
    return {
        "k": int(k),
        "n": int(n),
        "rate": float(k / n),
        "lower_95": lower_95,
        "upper_95": upper_95,
    }


def _draw_unit_ar1_with_shocks(
    rng: np.random.Generator,
    num_simulations: int,
    *,
    num_gameweeks: int,
    phi_ar: float,
    innovation_dist: InnovationDist,
    shock_gws: Sequence[int],
    shock_multiplier: float,
) -> np.ndarray:
    """Generate stationary AR(1) paths normalized to season-average unit marginal variance."""
    burn = 50
    total_steps = burn + num_gameweeks
    if innovation_dist == "gaussian":
        eps = rng.standard_normal((num_simulations, total_steps))
    elif innovation_dist == "student_t5":
        # Student-t(df=5) has variance 5 / (5 - 2) = 5 / 3 -> scale by sqrt(3/5) for unit variance
        eps = rng.standard_t(df=5.0, size=(num_simulations, total_steps)) * math.sqrt(3.0 / 5.0)
    else:
        raise ValueError(f"Unsupported innovation_dist: {innovation_dist}")

    shock_set = set(shock_gws)
    scale_vec = np.ones(total_steps, dtype=float)
    for t in range(num_gameweeks):
        if (t + 1) in shock_set:
            scale_vec[burn + t] = float(shock_multiplier)
    eps *= scale_vec[None, :]

    innov_scale = math.sqrt(max(1e-12, 1.0 - phi_ar**2))
    out = np.empty((num_simulations, num_gameweeks), dtype=float)
    x = eps[:, 0].copy()
    for step in range(1, total_steps):
        x = phi_ar * x + innov_scale * eps[:, step]
        if step >= burn:
            out[:, step - burn] = x

    # Theoretical marginal variance across GWs so RMS marginal SD equals 1.0 exactly
    var_t = np.empty(num_gameweeks, dtype=float)
    v = 1.0
    for t in range(num_gameweeks):
        s_t = float(shock_multiplier) if (t + 1) in shock_set else 1.0
        v = (phi_ar**2) * v + (1.0 - phi_ar**2) * (s_t**2)
        var_t[t] = v
    rms_sd = math.sqrt(float(np.mean(var_t)))
    return out / rms_sd


def generate_synthetic_paths(
    spec: ScenarioSpec,
    *,
    num_simulations: int,
    seed: int,
    fpl_delta_sd_per_gw: float = DEFAULT_FPL_DELTA_SD_PER_GW,
    num_gameweeks: int = 38,
) -> np.ndarray:
    """Generate deterministic (num_simulations, slate_size, 38) net FPL point differentials."""
    if spec.gw_variance_profile is not None and num_gameweeks != len(spec.gw_variance_profile):
        raise ValueError("gw_variance_profile length must match num_gameweeks")
    profile = (
        np.asarray(spec.gw_variance_profile, dtype=float)
        if spec.gw_variance_profile is not None
        else None
    )
    rng = np.random.default_rng(seed)
    shared = _draw_unit_ar1_with_shocks(
        rng,
        num_simulations,
        num_gameweeks=num_gameweeks,
        phi_ar=spec.phi_ar,
        innovation_dist=spec.innovation_dist,
        shock_gws=spec.shock_gws,
        shock_multiplier=spec.shock_multiplier,
    )
    sqrt_rho = math.sqrt(spec.rho_champ)
    sqrt_idio = math.sqrt(max(0.0, 1.0 - spec.rho_champ))
    paths = np.empty((num_simulations, spec.slate_size, num_gameweeks), dtype=float)

    for j in range(spec.slate_size):
        idio = _draw_unit_ar1_with_shocks(
            rng,
            num_simulations,
            num_gameweeks=num_gameweeks,
            phi_ar=spec.phi_ar,
            innovation_dist=spec.innovation_dist,
            shock_gws=spec.shock_gws,
            shock_multiplier=spec.shock_multiplier,
        )
        noise = (sqrt_rho * shared + sqrt_idio * idio) * float(fpl_delta_sd_per_gw)
        if profile is not None:
            noise = noise * profile[None, :]
        if spec.finalist_effects_pts_per_year is not None:
            total_effect = float(spec.finalist_effects_pts_per_year[j])
            if profile is not None:
                active = profile > 0.0
                active_count = int(np.sum(active))
                drift = np.where(active, total_effect / float(active_count), 0.0)
            else:
                drift = np.full(num_gameweeks, total_effect / float(num_gameweeks), dtype=float)
        else:
            drift = np.full(num_gameweeks, float(spec.finalist_effects_sd[j]) * float(fpl_delta_sd_per_gw), dtype=float)
        if spec.gw1_4_effects_pts_total is not None:
            if profile is not None:
                active_1_4 = profile[:4] > 0.0
                active_1_4_count = int(np.sum(active_1_4))
                if active_1_4_count == 0:
                    raise ValueError("Cannot distribute gw1_4_effects_pts_total when GW1..4 profile is all zeros")
                drift[:4] = np.where(active_1_4, float(spec.gw1_4_effects_pts_total[j]) / float(active_1_4_count), 0.0)
            else:
                drift[:4] = float(spec.gw1_4_effects_pts_total[j]) / 4.0
        elif spec.gw1_4_effects_sd is not None:
            drift[:4] = float(spec.gw1_4_effects_sd[j]) * float(fpl_delta_sd_per_gw)
        paths[:, j, :] = noise + drift[None, :]
    return paths


def _bartlett_lrv_vec(series: np.ndarray, bandwidth: int, *, adj: int = 1) -> np.ndarray:
    nv = series.shape[1]
    if nv == 0:
        return np.zeros(series.shape[0], dtype=float)
    div = float(max(nv - adj, 1))
    total = np.einsum("ij,ij->i", series, series) / div
    for k in range(1, min(bandwidth, nv - 1) + 1):
        weight = 1.0 - float(k) / float(bandwidth + 1)
        cov = np.einsum("ij,ij->i", series[:, k:], series[:, :-k]) / div
        total += 2.0 * weight * cov
    return np.maximum(0.0, total)


def _one_sided_lower_bound(mean: np.ndarray, se: np.ndarray, df: np.ndarray, alpha: float) -> np.ndarray:
    lower = mean.copy()
    regular = se > 1e-12
    if np.any(regular):
        t_crit = stats.t.ppf(1.0 - alpha, df=df[regular])
        lower[regular] = mean[regular] - t_crit * se[regular]
    is_zero = (~regular) & (np.abs(mean) <= 1e-12)
    lower[is_zero] = 0.0
    return lower


def vectorized_kendall_pw_hac_test(
    deltas_2d: np.ndarray,
    *,
    alpha: float = 0.05,
) -> dict[str, np.ndarray]:
    """Vectorized Kendall-PW + Bartlett HAC Student-t test matching scalar run_kendall_pw_hac_test."""
    if not 0.0 < alpha < 1.0:
        raise ValueError("Alpha must lie strictly between 0 and 1")
    arr = np.asarray(deltas_2d, dtype=float)
    if arr.ndim != 2:
        raise ValueError("deltas_2d must have shape (batch, n)")
    batch, n = arr.shape
    if n < 2 or not np.isfinite(arr).all():
        raise ValueError("Vectorized Kendall-PW HAC test requires at least two finite observations")

    mean = np.mean(arr, axis=1)
    e = arr - mean[:, None]
    denom = np.einsum("ij,ij->i", e[:, :-1], e[:, :-1])
    num = np.einsum("ij,ij->i", e[:, 1:], e[:, :-1])
    safe_denom = np.where(denom > 1e-12, denom, 1.0)
    r1 = np.where(denom > 1e-12, num / safe_denom, 0.0)
    phi_raw = (float(n) * r1 + 1.0) / float(n - 3) if n > 3 else r1
    phi = np.clip(phi_raw, 0.0, 0.92)

    bandwidth = max(1, min(n - 2, int(math.floor(float(n) ** (1.0 / 3.0))))) if n >= 3 else 0
    lrv_bartlett = _bartlett_lrv_vec(e, bandwidth, adj=1)
    u = e[:, 1:] - phi[:, None] * e[:, :-1]
    if u.shape[1] >= 2:
        lrv_u = _bartlett_lrv_vec(u, bandwidth, adj=1)
    else:
        lrv_u = np.einsum("ij,ij->i", u, u)
    lrv_pw = lrv_u / ((1.0 - phi) ** 2)
    lrv = np.maximum(lrv_pw, lrv_bartlett)

    var_e = np.var(e, axis=1, ddof=1)
    vif = np.where(var_e > 1e-12, np.maximum(1.0, lrv / np.maximum(var_e, 1e-12)), 1.0)
    n_eff = np.maximum(min(float(n), 5.0 if n >= 6 else float(n)), float(n) / vif)
    df = np.maximum(1.0, n_eff - 1.0)
    se = np.sqrt(lrv / float(n))

    t_stat = np.empty(batch, dtype=float)
    p_sup = np.empty(batch, dtype=float)
    p_harm = np.empty(batch, dtype=float)

    regular = se > 1e-12
    if np.any(regular):
        t_reg = mean[regular] / se[regular]
        df_reg = df[regular]
        t_stat[regular] = t_reg
        p_sup[regular] = stats.t.sf(t_reg, df=df_reg)
        p_harm[regular] = stats.t.cdf(t_reg, df=df_reg)

    degen = ~regular
    if np.any(degen):
        m_deg = mean[degen]
        is_zero = np.abs(m_deg) <= 1e-12
        is_pos = m_deg > 1e-12
        t_stat[degen] = np.where(is_zero, 0.0, np.where(is_pos, np.inf, -np.inf))
        p_sup[degen] = np.where(is_zero, 1.0, np.where(is_pos, 0.0, 1.0))
        p_harm[degen] = np.where(is_zero, 1.0, np.where(is_pos, 1.0, 0.0))
    lower = _one_sided_lower_bound(mean, se, df, alpha)

    return {
        "point_estimate": mean,
        "standard_error": se,
        "t_statistic": t_stat,
        "df": df,
        "n_eff": n_eff,
        "phi_hat": phi,
        "lrv_pw": lrv_pw,
        "lrv_bartlett": lrv_bartlett,
        "lrv": lrv,
        "one_sided_lower": lower,
        "p_value_superiority": p_sup,
        "p_value_harm": p_harm,
    }


def vectorized_early_harm_fallback(
    prefix_2d: np.ndarray,
    *,
    min_gw: int = EARLY_HARM_MIN_GW,
    harm_alpha: float = EARLY_HARM_P_THRESHOLD,
    gw1_4_material_loss_limit: float | None = None,
    statistical_mode: Literal["enforced", "advisory"] = "enforced",
) -> VectorizedEarlyHarmResult:
    """Vectorized Early-Harm + completed-segment + GW1-4 floor evaluation matching scalar fallback."""
    arr = np.asarray(prefix_2d, dtype=float)
    batch, n = arr.shape

    gw1_4_breached = np.zeros(batch, dtype=bool)
    if gw1_4_material_loss_limit is not None and n >= 4:
        gw1_4_sum = np.sum(arr[:, :4], axis=1)
        gw1_4_breached = gw1_4_sum < -float(gw1_4_material_loss_limit)

    stat_trig = np.zeros(batch, dtype=bool)
    cum_p_harm = np.full(batch, np.nan, dtype=float)
    seg_p_harms: dict[str, np.ndarray] = {}

    if n >= min_gw:
        cum = vectorized_kendall_pw_hac_test(arr, alpha=harm_alpha)
        cum_p_harm = cum["p_value_harm"]
        stat_trig |= cum_p_harm <= harm_alpha
        for seg_name, (lo, hi) in CONTIGUOUS_SEGMENT_BOUNDS.items():
            seg_len = hi - lo + 1
            if seg_len < min_gw or n < hi:
                continue
            seg_res = vectorized_kendall_pw_hac_test(arr[:, lo - 1 : hi], alpha=harm_alpha)
            seg_p_harms[seg_name] = seg_res["p_value_harm"]
            stat_trig |= seg_res["p_value_harm"] <= harm_alpha

    triggered = (stat_trig | gw1_4_breached) if statistical_mode == "enforced" else np.zeros(batch, dtype=bool)
    return {
        "triggered": triggered,
        "statistical_triggered": stat_trig,
        "gw1_4_floor_breached": gw1_4_breached,
        "cumulative_p_harm": cum_p_harm,
        "segment_p_harms": seg_p_harms,
    }


def _to_paired_scores(deltas: np.ndarray) -> list[PairedGameweekScore]:
    return [
        PairedGameweekScore(
            season="2026-27",
            gameweek=gw,
            candidate_net_points=60.0 + float(deltas[gw - 1]),
            champion_net_points=60.0,
            candidate_gross_points=60.0 + float(deltas[gw - 1]),
            champion_gross_points=60.0,
            candidate_hits_deducted=0,
            champion_hits_deducted=0,
            segment=assign_gameweek_segment(gw),
        )
        for gw in range(1, len(deltas) + 1)
    ]


def verify_vectorized_vs_scalar_parity(
    *,
    num_prefixes: int = 520,
    seed: int = 999,
) -> dict[str, Any]:
    """Compare vectorized Kendall-PW HAC & Early-Harm outputs against scalar evaluators across >=500 prefixes."""
    if num_prefixes < 500:
        raise ValueError("Parity check requires >= 500 sampled prefixes")
    rng = np.random.default_rng(seed)
    lengths = (2, 4, 6, 15, 19, 30, 38)
    per_length = max(1, (num_prefixes // len(lengths)) + 1)

    max_diff = 0.0
    total_checked = 0
    agreements = 0
    edge_cases_checked = 0

    hac_fields = (
        "point_estimate",
        "standard_error",
        "t_statistic",
        "df",
        "n_eff",
        "phi_hat",
        "lrv_pw",
        "lrv_bartlett",
        "lrv",
        "one_sided_lower",
        "p_value_superiority",
        "p_value_harm",
    )

    for length in lengths:
        alpha = OBF_ALPHA_SCHEDULE.get(length, 0.025)
        batch_rows: list[np.ndarray] = []
        # Deterministic edge cases first
        batch_rows.append(np.zeros(length, dtype=float))
        batch_rows.append(np.full(length, 2.0, dtype=float))
        batch_rows.append(np.full(length, -2.0, dtype=float))
        batch_rows.append(np.full(length, 1e-13, dtype=float))
        batch_rows.append(np.array([3.0 if i % 2 == 0 else -1.0 for i in range(length)], dtype=float))
        batch_rows.append(np.array([-10.0 if i < 4 else 0.5 for i in range(length)], dtype=float))
        batch_rows.append(np.array([20.0 if i < 4 else -10.0 for i in range(length)], dtype=float))
        batch_rows.append(np.linspace(-3.0, 3.0, length, dtype=float))  # strong positive phi (~0.92 clip test)
        num_edge = len(batch_rows)
        edge_cases_checked += num_edge

        while len(batch_rows) < per_length:
            phi = 0.55 if len(batch_rows) % 2 == 0 else 0.20
            drift = float(rng.choice([-0.8, 0.0, 0.4, 1.2]))
            innov = rng.standard_t(df=5.0, size=length) * math.sqrt(3.0 / 5.0) * DEFAULT_FPL_DELTA_SD_PER_GW
            series = np.empty(length, dtype=float)
            x = float(innov[0])
            for t in range(length):
                x = phi * x + math.sqrt(1.0 - phi**2) * float(innov[t])
                series[t] = drift + x
            batch_rows.append(series)

        mat = np.vstack(batch_rows)
        vec_hac = vectorized_kendall_pw_hac_test(mat, alpha=alpha)
        vec_eh_enf = vectorized_early_harm_fallback(
            mat, gw1_4_material_loss_limit=DEFAULT_ADVISORY_GW1_4_LOSS_LIMIT, statistical_mode="enforced"
        )
        vec_eh_adv = vectorized_early_harm_fallback(
            mat, gw1_4_material_loss_limit=DEFAULT_ADVISORY_GW1_4_LOSS_LIMIT, statistical_mode="advisory"
        )

        for idx in range(mat.shape[0]):
            row = mat[idx]
            scalar_hac = run_kendall_pw_hac_test(row.tolist(), alpha=alpha)
            for field_name in hac_fields:
                v_val = float(vec_hac[field_name][idx])
                s_val = float(getattr(scalar_hac, field_name))
                if math.isinf(s_val) or math.isinf(v_val):
                    assert s_val == v_val
                else:
                    max_diff = max(max_diff, abs(v_val - s_val))

            paired = _to_paired_scores(row)
            s_eh_enf = evaluate_early_harm_fallback(
                paired, gw1_4_material_loss_limit=DEFAULT_ADVISORY_GW1_4_LOSS_LIMIT, statistical_mode="enforced"
            )
            s_eh_adv = evaluate_early_harm_fallback(
                paired, gw1_4_material_loss_limit=DEFAULT_ADVISORY_GW1_4_LOSS_LIMIT, statistical_mode="advisory"
            )

            vec_sup = bool(
                vec_hac["point_estimate"][idx] > 0.0
                and vec_hac["one_sided_lower"][idx] > 0.0
                and vec_hac["p_value_superiority"][idx] <= alpha
            )
            scal_sup = bool(
                scalar_hac.point_estimate > 0.0
                and scalar_hac.one_sided_lower > 0.0
                and scalar_hac.p_value_superiority <= alpha
            )

            if length >= EARLY_HARM_MIN_GW:
                max_diff = max(
                    max_diff,
                    abs(float(vec_eh_enf["cumulative_p_harm"][idx]) - float(s_eh_enf.cumulative_p_harm or 0.0)),
                )
                for seg_name, seg_p in s_eh_enf.segment_p_harms.items():
                    max_diff = max(
                        max_diff,
                        abs(float(vec_eh_enf["segment_p_harms"][seg_name][idx]) - float(seg_p)),
                    )

            agree = (
                vec_sup == scal_sup
                and bool(vec_eh_enf["triggered"][idx]) == s_eh_enf.triggered
                and bool(vec_eh_enf["statistical_triggered"][idx]) == s_eh_enf.statistical_triggered
                and bool(vec_eh_enf["gw1_4_floor_breached"][idx]) == s_eh_enf.gw1_4_floor_breached
                and bool(vec_eh_adv["triggered"][idx]) == s_eh_adv.triggered
                and bool(vec_eh_adv["gw1_4_floor_breached"][idx]) == s_eh_adv.gw1_4_floor_breached
            )
            if agree:
                agreements += 1
            total_checked += 1

    agreement_rate = float(agreements / total_checked)
    passed = max_diff <= 1e-10 and agreement_rate == 1.0
    return {
        "num_prefixes_checked": total_checked,
        "edge_cases_checked": edge_cases_checked,
        "max_abs_numeric_diff": max_diff,
        "binary_agreement_rate": agreement_rate,
        "tolerance": 1e-10,
        "passed": passed,
    }


def _scenario_seed(base_seed: int, scenario_index: int) -> int:
    return int(np.random.SeedSequence([base_seed, scenario_index]).generate_state(1)[0])


def _precompute_scenario_stats(
    spec: ScenarioSpec,
    paths: np.ndarray,
    *,
    harm_alpha: float = EARLY_HARM_P_THRESHOLD,
) -> dict[str, Any]:
    """Precompute scale-free HAC & harm stats per look once for fast evaluation and calibration."""
    num_sims, slate_size, _ = paths.shape
    gw1_4_sum = np.sum(paths[:, :, :4], axis=2)
    cum_delta: dict[int, np.ndarray] = {}
    cum_hac: dict[int, list[dict[str, np.ndarray]]] = {}
    cum_p_harm: dict[int, np.ndarray] = {}
    for gw in REGISTERED_CHECKPOINTS:
        cum_delta[gw] = np.sum(paths[:, :, :gw], axis=2)
        hac_list = [vectorized_kendall_pw_hac_test(paths[:, j, :gw], alpha=0.05) for j in range(slate_size)]
        cum_hac[gw] = hac_list
        cum_p_harm[gw] = np.column_stack([hac_list[j]["p_value_harm"] for j in range(slate_size)])

    early_mid_p_harm = np.column_stack(
        [vectorized_kendall_pw_hac_test(paths[:, j, 4:19], alpha=harm_alpha)["p_value_harm"] for j in range(slate_size)]
    )
    late_p_harm = np.column_stack(
        [vectorized_kendall_pw_hac_test(paths[:, j, 19:38], alpha=harm_alpha)["p_value_harm"] for j in range(slate_size)]
    )
    return {
        "spec": spec,
        "num_simulations": num_sims,
        "gw1_4_sum": gw1_4_sum,
        "cum_delta": cum_delta,
        "cum_hac": cum_hac,
        "cum_p_harm": cum_p_harm,
        "early_mid_p_harm": early_mid_p_harm,
        "late_p_harm": late_p_harm,
    }


def _simulate_from_precomputed(
    pre: Mapping[str, Any],
    *,
    calibrated_superiority_alphas: Mapping[str, Mapping[str, float]],
    gw1_4_material_loss_limit: float,
    statistical_early_harm_mode: Literal["enforced", "advisory"],
    harm_alpha: float = EARLY_HARM_P_THRESHOLD,
    exact_lower_check: bool = True,
) -> dict[str, Any]:
    spec: ScenarioSpec = pre["spec"]
    n_sims: int = pre["num_simulations"]
    m_count = spec.slate_size
    alphas_for_m = calibrated_superiority_alphas[str(m_count)]
    gw1_4_sum: np.ndarray = pre["gw1_4_sum"]

    excluded = np.zeros((n_sims, m_count), dtype=bool)
    stat_harm_flagged = np.zeros((n_sims, m_count), dtype=bool)
    gw1_4_flagged = np.zeros((n_sims, m_count), dtype=bool)
    ever_full_pass = np.zeros((n_sims, m_count), dtype=bool)
    slate_confirmed = np.zeros(n_sims, dtype=bool)
    confirmed_winner = np.full(n_sims, -1, dtype=int)
    confirmed_gw = np.zeros(n_sims, dtype=int)

    for gw in REGISTERED_CHECKPOINTS:
        alpha_g = float(alphas_for_m[str(gw)])
        cum_delta_g: np.ndarray = pre["cum_delta"][gw]
        cum_p_harm_g: np.ndarray = pre["cum_p_harm"][gw]
        hac_list_g: list[dict[str, np.ndarray]] = pre["cum_hac"][gw]

        pass_now = np.zeros((n_sims, m_count), dtype=bool)
        guards_pass_now = gw >= spec.safeguards_pass_from_gw

        for j in range(m_count):
            breach_gw1_4 = gw1_4_sum[:, j] < -float(gw1_4_material_loss_limit)
            gw1_4_flagged[:, j] |= breach_gw1_4
            stat_flag_now = cum_p_harm_g[:, j] <= harm_alpha
            if gw >= 30:
                stat_flag_now = stat_flag_now | (pre["early_mid_p_harm"][:, j] <= harm_alpha)
            if gw >= 38:
                stat_flag_now = stat_flag_now | (pre["late_p_harm"][:, j] <= harm_alpha)
            stat_harm_flagged[:, j] |= (~excluded[:, j]) & stat_flag_now

            if statistical_early_harm_mode == "enforced":
                excluded[:, j] |= breach_gw1_4 | stat_flag_now

            if guards_pass_now:
                hac_j = hac_list_g[j]
                mean_j = hac_j["point_estimate"]
                se_j = hac_j["standard_error"]
                df_j = hac_j["df"]
                p_sup_j = hac_j["p_value_superiority"]
                if exact_lower_check:
                    lower_j = _one_sided_lower_bound(mean_j, se_j, df_j, alpha_g)
                    sup_j = (mean_j > 0.0) & (lower_j > 0.0) & (p_sup_j <= alpha_g)
                else:
                    sup_j = (mean_j > 0.0) & np.where(se_j > 1e-12, p_sup_j < alpha_g, p_sup_j <= alpha_g)
                pass_now[:, j] = (~excluded[:, j]) & sup_j
                ever_full_pass[:, j] |= pass_now[:, j]

        if guards_pass_now:
            unconfirmed = ~slate_confirmed
            if m_count == 1:
                newly = unconfirmed & pass_now[:, 0]
                confirmed_winner[newly] = 0
                confirmed_gw[newly] = gw
                slate_confirmed |= newly
            else:
                both = unconfirmed & pass_now[:, 0] & pass_now[:, 1]
                only0 = unconfirmed & pass_now[:, 0] & (~pass_now[:, 1])
                only1 = unconfirmed & pass_now[:, 1] & (~pass_now[:, 0])
                win_both_0 = both & (cum_delta_g[:, 0] >= cum_delta_g[:, 1])
                win_both_1 = both & (cum_delta_g[:, 1] > cum_delta_g[:, 0])
                win0 = only0 | win_both_0
                win1 = only1 | win_both_1
                confirmed_winner[win0] = 0
                confirmed_winner[win1] = 1
                confirmed_gw[win0 | win1] = gw
                slate_confirmed |= win0 | win1

    null_indices = spec.null_indices
    improving_indices = spec.improving_indices
    harmful_indices = spec.harmful_indices
    non_harmful_indices = spec.non_harmful_indices

    false_slate_k = int(np.sum(np.isin(confirmed_winner, null_indices))) if null_indices else 0
    false_ever_k = int(np.sum(np.any(ever_full_pass[:, null_indices], axis=1))) if null_indices else 0

    correct_k = int(np.sum(np.isin(confirmed_winner, improving_indices))) if improving_indices else 0
    gw15_k = int(np.sum(np.isin(confirmed_winner, improving_indices) & (confirmed_gw == 15))) if improving_indices else 0
    gw30_k = int(np.sum(np.isin(confirmed_winner, improving_indices) & (confirmed_gw == 30))) if improving_indices else 0
    gw38_k = int(np.sum(np.isin(confirmed_winner, improving_indices) & (confirmed_gw == 38))) if improving_indices else 0

    term_false_excl_k = int(np.sum(np.any(excluded[:, non_harmful_indices], axis=1))) if non_harmful_indices else 0
    stat_false_flag_k = int(np.sum(np.any(stat_harm_flagged[:, non_harmful_indices], axis=1))) if non_harmful_indices else 0
    gw1_4_false_excl_k = int(np.sum(np.any(gw1_4_flagged[:, non_harmful_indices], axis=1))) if non_harmful_indices else 0

    harm_term_k = int(np.sum(np.all(excluded[:, harmful_indices], axis=1))) if harmful_indices else 0
    harm_stat_k = int(np.sum(np.all(stat_harm_flagged[:, harmful_indices], axis=1))) if harmful_indices else 0
    harm_gw1_4_k = int(np.sum(np.all(gw1_4_flagged[:, harmful_indices], axis=1))) if harmful_indices else 0
    harm_any_k = (
        int(
            np.sum(
                np.all(
                    excluded[:, harmful_indices]
                    | stat_harm_flagged[:, harmful_indices]
                    | gw1_4_flagged[:, harmful_indices],
                    axis=1,
                )
            )
        )
        if harmful_indices
        else 0
    )

    return {
        "scenario_id": spec.scenario_id,
        "category": spec.category,
        "slate_size": m_count,
        "dependence_regime": spec.dependence_regime,
        "safeguards_pass_from_gw": spec.safeguards_pass_from_gw,
        "is_primary_power": spec.is_primary_power,
        "has_null_finalist": bool(null_indices),
        "has_improving_finalist": bool(improving_indices),
        "has_non_harmful_finalist": bool(non_harmful_indices),
        "has_harmful_finalist": bool(harmful_indices),
        "false_slate_pass": clopper_pearson_one_sided_95(false_slate_k, n_sims),
        "false_null_ever_pass": clopper_pearson_one_sided_95(false_ever_k, n_sims),
        "correct_confirmation_by_gw38": clopper_pearson_one_sided_95(correct_k, n_sims),
        "confirm_gw15": clopper_pearson_one_sided_95(gw15_k, n_sims),
        "confirm_gw30": clopper_pearson_one_sided_95(gw30_k, n_sims),
        "confirm_gw38": clopper_pearson_one_sided_95(gw38_k, n_sims),
        "terminal_false_exclusion": clopper_pearson_one_sided_95(term_false_excl_k, n_sims),
        "statistical_false_exclusion_flag": clopper_pearson_one_sided_95(stat_false_flag_k, n_sims),
        "gw1_4_false_exclusion": clopper_pearson_one_sided_95(gw1_4_false_excl_k, n_sims),
        "harmful_terminal_exclusion": clopper_pearson_one_sided_95(harm_term_k, n_sims),
        "harmful_statistical_flag": clopper_pearson_one_sided_95(harm_stat_k, n_sims),
        "harmful_gw1_4_exclusion": clopper_pearson_one_sided_95(harm_gw1_4_k, n_sims),
        "harmful_any_detected": clopper_pearson_one_sided_95(harm_any_k, n_sims),
    }


def evaluate_scenario_vectorized(
    spec: ScenarioSpec,
    *,
    num_simulations: int,
    seed: int,
    calibrated_superiority_alphas: Mapping[str, Mapping[str, float]],
    gw1_4_material_loss_limit: float,
    statistical_early_harm_mode: Literal["enforced", "advisory"] = "enforced",
    fpl_delta_sd_per_gw: float = DEFAULT_FPL_DELTA_SD_PER_GW,
    harm_alpha: float = EARLY_HARM_P_THRESHOLD,
) -> dict[str, Any]:
    """Generate and evaluate one preregistered synthetic scenario using the vectorized evaluator."""
    paths = generate_synthetic_paths(
        spec,
        num_simulations=num_simulations,
        seed=seed,
        fpl_delta_sd_per_gw=fpl_delta_sd_per_gw,
    )
    pre = _precompute_scenario_stats(spec, paths, harm_alpha=harm_alpha)
    return _simulate_from_precomputed(
        pre,
        calibrated_superiority_alphas=calibrated_superiority_alphas,
        gw1_4_material_loss_limit=gw1_4_material_loss_limit,
        statistical_early_harm_mode=statistical_early_harm_mode,
        harm_alpha=harm_alpha,
        exact_lower_check=True,
    )


def _weighted_alphas_for_m(slate_size: int, scale: float, w15: float = 1.0, w30: float = 1.0) -> dict[str, float]:
    return {
        "15": round(float(OBF_ALPHA_SCHEDULE[15] / float(slate_size)) * float(scale) * float(w15), 8),
        "30": round(float(OBF_ALPHA_SCHEDULE[30] / float(slate_size)) * float(scale) * float(w30), 8),
        "38": round(float(OBF_ALPHA_SCHEDULE[38] / float(slate_size)) * float(scale), 8),
    }


def tune_enforced_gw1_4_limit(
    non_harmful_mins: Sequence[np.ndarray],
    *,
    num_simulations: int,
    fpl_delta_sd_per_gw: float,
) -> float:
    """Fail-closed grid search for an enforced GW1-4 net-points limit across non-harmful paths."""
    target_gw1_4_upper = 0.020 if num_simulations >= 2000 else 0.015
    max_half_pts = max(240, int(math.ceil(24.0 * float(fpl_delta_sd_per_gw))))
    for limit_half_pts in range(12, max_half_pts + 1):
        limit = limit_half_pts * 0.5
        worst_val = 0.0
        for arr in non_harmful_mins:
            k = int(np.sum(arr < -limit))
            bound = clopper_pearson_one_sided_95(k, num_simulations)
            metric = bound["upper_95"] if num_simulations >= 2000 else bound["rate"]
            worst_val = max(worst_val, float(metric))
        if worst_val <= target_gw1_4_upper:
            return float(limit)
    raise RuntimeError(
        f"Failed to find enforced gw1_4_material_loss_limit <= {target_gw1_4_upper:.3f} "
        f"within [6.0, {max_half_pts * 0.5:.1f}] at fpl_delta_sd_per_gw={fpl_delta_sd_per_gw}"
    )


def tune_sparse_protocol(
    *,
    num_simulations: int = DEFAULT_NUM_SIMULATIONS,
    seed: int = TUNING_SEED,
    fpl_delta_sd_per_gw: float = DEFAULT_FPL_DELTA_SD_PER_GW,
    harm_alpha: float = EARLY_HARM_P_THRESHOLD,
) -> dict[str, Any]:
    """Calibrate scale-free M=1/M=2 superiority alphas strictly on the preregistered tuning seed."""
    grid = build_preregistered_scenario_grid()
    precomputed: list[dict[str, Any]] = []
    for idx, spec in enumerate(grid):
        paths = generate_synthetic_paths(
            spec,
            num_simulations=num_simulations,
            seed=_scenario_seed(seed, idx),
            fpl_delta_sd_per_gw=fpl_delta_sd_per_gw,
        )
        precomputed.append(_precompute_scenario_stats(spec, paths, harm_alpha=harm_alpha))

    # 1. Align advisory GW1-4 threshold to ADR 0071 cold_start (-8.9 pts/GW * 4 = 35.6 pts)
    gw1_4_limit = float(DEFAULT_ADVISORY_GW1_4_LOSS_LIMIT)

    # 2. Calibrate OBF per-look superiority thresholds for M=1 and M=2 on tuning_seed ONLY,
    #    purely scale-free without borrowing exclusion rate from gw1_4_limit.
    target_fwer_upper = 0.043 if num_simulations >= 2000 else 0.035
    calibrated_alphas: dict[str, dict[str, float]] = {}
    scale_factors: dict[int, float] = {}
    selected_weights: dict[int, tuple[float, float]] = {}

    def _prep_fast_null(item: Mapping[str, Any]) -> dict[str, Any]:
        spec_i: ScenarioSpec = item["spec"]
        null_idx = spec_i.null_indices
        excl = np.zeros((num_simulations, len(null_idx)), dtype=bool)
        p_sups: dict[int, np.ndarray] = {}
        for gw in REGISTERED_CHECKPOINTS:
            if gw < spec_i.safeguards_pass_from_gw:
                p_sups[gw] = np.ones((num_simulations, len(null_idx)), dtype=float)
            else:
                cols = []
                for j in null_idx:
                    hac_j = item["cum_hac"][gw][j]
                    pos_j = hac_j["point_estimate"] > 0.0
                    p_j = np.where(pos_j, hac_j["p_value_superiority"], 1.0)
                    cols.append(p_j)
                p_sups[gw] = np.column_stack(cols)
        return {"excl": excl, "p15": p_sups[15], "p30": p_sups[30], "p38": p_sups[38]}

    for m_size in (1, 2):
        null_items = [
            item
            for item in precomputed
            if item["spec"].slate_size == m_size
            and item["spec"].category in ("null", "mixed_null")
            and item["spec"].null_indices
        ]
        fast_nulls = [_prep_fast_null(item) for item in null_items]
        power_items = [
            item
            for item in precomputed
            if item["spec"].slate_size == m_size
            and item["spec"].finalist_effects_pts_per_year is None
            and (item["spec"].is_primary_power if m_size == 2 else item["spec"].category == "power")
        ]
        best_tuple: tuple[float, float, float, float, dict[str, float]] | None = None
        for w15 in (0.05, 0.1, 0.25, 0.5, 1.0):
            for w30 in (0.25, 0.5, 0.75, 1.0):
                base_sum = w15 * OBF_ALPHA_SCHEDULE[15] + w30 * OBF_ALPHA_SCHEDULE[30] + OBF_ALPHA_SCHEDULE[38]
                if not (w15 * OBF_ALPHA_SCHEDULE[15] < w30 * OBF_ALPHA_SCHEDULE[30] < OBF_ALPHA_SCHEDULE[38]):
                    continue
                max_budget_scale = 0.05 / base_sum
                lo, hi = 0.01, max_budget_scale
                best_scale = lo
                for _ in range(24):
                    mid = 0.5 * (lo + hi)
                    a15 = (OBF_ALPHA_SCHEDULE[15] / float(m_size)) * mid * w15
                    a30 = (OBF_ALPHA_SCHEDULE[30] / float(m_size)) * mid * w30
                    a38 = (OBF_ALPHA_SCHEDULE[38] / float(m_size)) * mid
                    worst_metric = 0.0
                    for fn in fast_nulls:
                        hit = (~fn["excl"]) & ((fn["p15"] < a15) | (fn["p30"] < a30) | (fn["p38"] < a38))
                        k = int(np.sum(np.any(hit, axis=1)))
                        bound = clopper_pearson_one_sided_95(k, num_simulations)
                        stat_key = "upper_95" if num_simulations >= 2000 else "rate"
                        worst_metric = max(worst_metric, float(bound[stat_key]))
                        if worst_metric > target_fwer_upper:
                            break
                    if worst_metric <= target_fwer_upper:
                        best_scale = mid
                        lo = mid
                    else:
                        hi = mid
                safe_scale = max(0.01, math.floor(best_scale * 10_000.0) / 10_000.0)
                final_m = _weighted_alphas_for_m(m_size, safe_scale, w15, w30)
                cand_alphas = {"1": final_m, "2": final_m}
                power_score = 0.0
                for item in power_items:
                    res_p = _simulate_from_precomputed(
                        item,
                        calibrated_superiority_alphas=cand_alphas,
                        gw1_4_material_loss_limit=gw1_4_limit,
                        statistical_early_harm_mode="advisory",
                        harm_alpha=harm_alpha,
                        exact_lower_check=False,
                    )
                    power_score += float(res_p["correct_confirmation_by_gw38"]["rate"])
                power_score /= max(1, len(power_items))
                candidate = (power_score, w30, w15, safe_scale, final_m)
                if best_tuple is None or candidate[:3] > best_tuple[:3]:
                    best_tuple = candidate

        assert best_tuple is not None
        scale_factors[m_size] = best_tuple[3]
        selected_weights[m_size] = (best_tuple[2], best_tuple[1])
        calibrated_alphas[str(m_size)] = best_tuple[4]

    return {
        "tuning_seed": seed,
        "num_simulations": num_simulations,
        "fpl_delta_sd_per_gw": float(fpl_delta_sd_per_gw),
        "gw1_4_material_loss_limit": float(gw1_4_limit),
        "gw1_4_limit_basis": "advisory_adr0071_cold_start_4x8.9",
        "calibrated_superiority_alphas": calibrated_alphas,
        "m1_scale_factor": scale_factors[1],
        "m2_scale_factor": scale_factors[2],
        "m1_look_weights": {"15": selected_weights[1][0], "30": selected_weights[1][1], "38": 1.0},
        "m2_look_weights": {"15": selected_weights[2][0], "30": selected_weights[2][1], "38": 1.0},
    }


def run_certification_suite(
    *,
    num_simulations: int,
    seed: int,
    calibrated_superiority_alphas: Mapping[str, Mapping[str, float]],
    gw1_4_material_loss_limit: float,
    statistical_early_harm_mode: Literal["enforced", "advisory"],
    fpl_delta_sd_per_gw: float = DEFAULT_FPL_DELTA_SD_PER_GW,
    harm_alpha: float = EARLY_HARM_P_THRESHOLD,
) -> dict[str, Any]:
    """Run all preregistered scenarios on one fixed seed and evaluate exact 95% acceptance gates."""
    grid = build_preregistered_scenario_grid()
    scenarios: list[dict[str, Any]] = []
    for idx, spec in enumerate(grid):
        scenarios.append(
            evaluate_scenario_vectorized(
                spec,
                num_simulations=num_simulations,
                seed=_scenario_seed(seed, idx),
                calibrated_superiority_alphas=calibrated_superiority_alphas,
                gw1_4_material_loss_limit=gw1_4_material_loss_limit,
                statistical_early_harm_mode=statistical_early_harm_mode,
                fpl_delta_sd_per_gw=fpl_delta_sd_per_gw,
                harm_alpha=harm_alpha,
            )
        )

    null_scenarios = [s for s in scenarios if s["has_null_finalist"]]
    false_pass_worst = max(
        (max(s["false_null_ever_pass"]["upper_95"], s["false_slate_pass"]["upper_95"]) for s in null_scenarios),
        default=0.0,
    )
    false_full_pass_ok = bool(null_scenarios) and false_pass_worst <= MAX_FALSE_FULL_PASS_UPPER_95

    primary_scenarios = [s for s in scenarios if s["is_primary_power"]]
    if len(primary_scenarios) != 1:
        raise ValueError("Expected exactly one primary GW38 power scenario in grid")
    primary_power_lower = float(primary_scenarios[0]["correct_confirmation_by_gw38"]["lower_95"])
    primary_gw38_power_ok = primary_power_lower >= MIN_PRIMARY_POWER_LOWER_95

    non_harmful_scenarios = [s for s in scenarios if s["has_non_harmful_finalist"]]
    stat_excl_worst = max(
        (s["statistical_false_exclusion_flag"]["upper_95"] for s in non_harmful_scenarios),
        default=0.0,
    )
    term_excl_worst = max(
        (s["terminal_false_exclusion"]["upper_95"] for s in non_harmful_scenarios),
        default=0.0,
    )
    statistical_false_exclusion_ok = stat_excl_worst <= MAX_FALSE_EXCLUSION_UPPER_95
    terminal_false_exclusion_ok = term_excl_worst <= MAX_FALSE_EXCLUSION_UPPER_95
    all_passed = false_full_pass_ok and primary_gw38_power_ok and terminal_false_exclusion_ok

    return {
        "seed": seed,
        "statistical_early_harm_mode": statistical_early_harm_mode,
        "num_simulations": num_simulations,
        "scenarios": scenarios,
        "gates": {
            "false_full_pass_ok": false_full_pass_ok,
            "worst_false_full_pass_upper_95": false_pass_worst,
            "primary_gw38_power_ok": primary_gw38_power_ok,
            "primary_gw38_power_lower_95": primary_power_lower,
            "statistical_false_exclusion_ok": statistical_false_exclusion_ok,
            "worst_statistical_false_exclusion_upper_95": stat_excl_worst,
            "terminal_false_exclusion_ok": terminal_false_exclusion_ok,
            "worst_terminal_false_exclusion_upper_95": term_excl_worst,
            "all_passed": all_passed,
        },
    }


def _simulate_locked_ar1_paths(
    rng: np.random.Generator,
    num_simulations: int,
    *,
    num_gameweeks: int,
    sigma_gw: float,
    effect_pts_total: float,
    profile: np.ndarray,
    shock_gws: tuple[int, ...],
) -> np.ndarray:
    shared = _draw_unit_ar1_with_shocks(
        rng,
        num_simulations,
        num_gameweeks=num_gameweeks,
        phi_ar=0.10,
        innovation_dist="gaussian",
        shock_gws=shock_gws,
        shock_multiplier=1.50,
    )
    ind = _draw_unit_ar1_with_shocks(
        rng,
        num_simulations,
        num_gameweeks=num_gameweeks,
        phi_ar=0.10,
        innovation_dist="gaussian",
        shock_gws=shock_gws,
        shock_multiplier=1.50,
    )
    noise = math.sqrt(0.5) * (shared + ind) * float(sigma_gw) * profile[None, :]
    active = profile > 0.0
    drift = np.where(active, float(effect_pts_total) / float(np.sum(active)), 0.0)
    return noise + drift[None, :]


def _superiority_pass_mask(paths: np.ndarray, alpha: float) -> np.ndarray:
    hac = vectorized_kendall_pw_hac_test(paths, alpha=alpha)
    return (
        (hac["point_estimate"] > 0.0)
        & (hac["one_sided_lower"] > 0.0)
        & (hac["p_value_superiority"] <= alpha)
    )


def compute_empirical_power_diagnostics(
    *,
    calibrated_superiority_alphas: Mapping[str, Mapping[str, float]],
    seed: int,
    num_simulations: int = DEFAULT_NUM_SIMULATIONS,
) -> dict[str, Any]:
    """Evaluate 1-season (38 GW) and 2-season carryover (76 GW) confirmation power at fixed FPL pts/yr."""
    profile_38 = np.asarray(EMPIRICAL_GW_VARIANCE_PROFILE, dtype=float)
    profile_76 = np.concatenate([profile_38, profile_38])
    shocks_38 = DEFAULT_SHOCK_GWS
    shocks_76 = (*DEFAULT_SHOCK_GWS, *(gw + 38 for gw in DEFAULT_SHOCK_GWS))

    rows: list[dict[str, Any]] = []
    diag_idx = 0
    for slate_size in (1, 2):
        alphas_m = calibrated_superiority_alphas[str(slate_size)]
        a15 = float(alphas_m["15"])
        a30 = float(alphas_m["30"])
        a38 = float(alphas_m["38"])
        for sigma_gw in (DEFAULT_FPL_DELTA_SD_PER_GW, UPPER_STRESS_FPL_DELTA_SD_PER_GW):
            for eff_pts in (40.0, 60.0, 80.0):
                diag_idx += 1
                sub_seed = int(np.random.SeedSequence([seed, 9001, diag_idx]).generate_state(1)[0])
                rng = np.random.default_rng(sub_seed)

                # 1-season 38-GW empirical trajectory (locked GW1/GW2, phi=0.10, Gaussian)
                p_1 = _simulate_locked_ar1_paths(
                    rng,
                    num_simulations,
                    num_gameweeks=38,
                    sigma_gw=float(sigma_gw),
                    effect_pts_total=float(eff_pts),
                    profile=profile_38,
                    shock_gws=shocks_38,
                )
                hits_by_gw = {
                    gw: _superiority_pass_mask(p_1[:, :gw], alpha_g)
                    for gw, alpha_g in ((15, a15), (30, a30), (38, a38))
                }
                cum_seq_38 = hits_by_gw[15] | hits_by_gw[30] | hits_by_gw[38]

                # 2-season 76-GW carryover diagnostic evaluated at final a38 budget
                p_2 = _simulate_locked_ar1_paths(
                    rng,
                    num_simulations,
                    num_gameweeks=76,
                    sigma_gw=float(sigma_gw),
                    effect_pts_total=2.0 * float(eff_pts),
                    profile=profile_76,
                    shock_gws=shocks_76,
                )
                hit_76 = _superiority_pass_mask(p_2, a38)

                rows.append(
                    {
                        "slate_size": slate_size,
                        "sigma_gw": float(sigma_gw),
                        "effect_pts_per_year": float(eff_pts),
                        "gw15_power": float(np.mean(hits_by_gw[15])),
                        "gw30_power": float(np.mean(hits_by_gw[30])),
                        "single_season_gw38_power": float(np.mean(cum_seq_38)),
                        "two_season_76gw_power": float(np.mean(hit_76)),
                    }
                )

    return {
        "dgp": "empirical_locked_gw1_2_phi010_gaussian",
        "seed": int(seed),
        "num_simulations": int(num_simulations),
        "gw_variance_profile": list(EMPIRICAL_GW_VARIANCE_PROFILE),
        "rows": rows,
    }


def certify_sparse_confirmation(
    *,
    num_simulations: int = DEFAULT_NUM_SIMULATIONS,
    fpl_delta_sd_per_gw: float = DEFAULT_FPL_DELTA_SD_PER_GW,
    tuning_seed: int = TUNING_SEED,
    certification_seed: int = CERTIFICATION_SEED,
    fallback_seed: int = FALLBACK_ADVISORY_SEED,
) -> dict[str, Any]:
    """Execute full preregistered sparse confirmation calibration, parity check, and held-out certification."""
    manifest = build_preregistration_manifest(
        num_simulations=num_simulations,
        fpl_delta_sd_per_gw=fpl_delta_sd_per_gw,
        tuning_seed=tuning_seed,
        certification_seed=certification_seed,
        fallback_seed=fallback_seed,
    )
    parity = verify_vectorized_vs_scalar_parity(num_prefixes=520, seed=999)
    if not parity["passed"]:
        raise RuntimeError(f"Vectorized vs scalar parity failed: {parity}")

    tuning = tune_sparse_protocol(
        num_simulations=num_simulations,
        seed=tuning_seed,
        fpl_delta_sd_per_gw=fpl_delta_sd_per_gw,
    )
    alphas = tuning["calibrated_superiority_alphas"]
    gw1_4_limit = float(tuning["gw1_4_material_loss_limit"])

    primary_run = run_certification_suite(
        num_simulations=num_simulations,
        seed=certification_seed,
        calibrated_superiority_alphas=alphas,
        gw1_4_material_loss_limit=gw1_4_limit,
        statistical_early_harm_mode="enforced",
        fpl_delta_sd_per_gw=fpl_delta_sd_per_gw,
    )
    p_gates = primary_run["gates"]

    fallback_run: dict[str, Any] | None = None
    retries_used = 0
    certified_mode: Literal["enforced", "advisory"] | None = None
    active_seed: int | None = None

    if p_gates["all_passed"]:
        certified = True
        certified_mode = "enforced"
        active_seed = certification_seed
    elif (
        p_gates["false_full_pass_ok"]
        and p_gates["primary_gw38_power_ok"]
        and not p_gates["statistical_false_exclusion_ok"]
    ):
        retries_used = 1
        fallback_run = run_certification_suite(
            num_simulations=num_simulations,
            seed=fallback_seed,
            calibrated_superiority_alphas=alphas,
            gw1_4_material_loss_limit=gw1_4_limit,
            statistical_early_harm_mode="advisory",
            fpl_delta_sd_per_gw=fpl_delta_sd_per_gw,
        )
        f_gates = fallback_run["gates"]
        certified = bool(
            f_gates["false_full_pass_ok"]
            and f_gates["primary_gw38_power_ok"]
            and f_gates["terminal_false_exclusion_ok"]
        )
        if certified:
            certified_mode = "advisory"
            active_seed = fallback_seed
    else:
        certified = False

    certified_protocol_dict: dict[str, Any] | None = None
    statistical_protocol_hash: str | None = None
    certification_digest: str | None = None

    summary_raw = {
        "manifest_digest": manifest["manifest_digest"],
        "parity_passed": parity["passed"],
        "tuning": tuning,
        "primary_run": primary_run,
        "fallback_run": fallback_run,
        "retries_used": retries_used,
        "certified": certified,
        "certified_mode": certified_mode,
        "certification_seed": active_seed,
        "live_adoption_blocked": not certified,
    }
    summary_body = {k: summary_raw[k] for k in CERTIFICATION_SUMMARY_KEYS}
    certification_digest = compute_canonical_digest(summary_body)

    if certified and certified_mode is not None:
        cfg = build_certified_protocol_config(
            calibrated_superiority_alphas=alphas,
            gw1_4_material_loss_limit=gw1_4_limit,
            statistical_early_harm_mode=certified_mode,
            certification_digest=certification_digest,
        )
        certified_protocol_dict = cfg.to_dict()
        statistical_protocol_hash = cfg.compute_hash()

    empirical_power_diagnostics = (
        compute_empirical_power_diagnostics(
            calibrated_superiority_alphas=alphas,
            seed=active_seed,
            num_simulations=num_simulations,
        )
        if certified and active_seed is not None
        else None
    )

    return {
        **summary_body,
        "certification_digest": certification_digest,
        "statistical_protocol_hash": statistical_protocol_hash,
        "certified_protocol_config": certified_protocol_dict,
        "manifest": manifest,
        "parity_check": parity,
        "empirical_power_diagnostics": empirical_power_diagnostics,
    }


def build_certified_protocol_config(
    *,
    calibrated_superiority_alphas: dict[str, dict[str, float]],
    gw1_4_material_loss_limit: float,
    statistical_early_harm_mode: Literal["enforced", "advisory"],
    certification_digest: str,
    development_season: str | None = None,
    confirmation_season: str | None = None,
) -> StatisticalProtocolConfig:
    """Build certified ADR 0070 v2.0 StatisticalProtocolConfig aligned with the Annual Firewall."""
    lifecycle = load_season_lifecycle()
    dev_season = development_season or lifecycle.season_for_role("development")
    conf_season = confirmation_season or lifecycle.season_for_role("active_validation")
    return StatisticalProtocolConfig(
        protocol_version="v2.0",
        inference_method="kendall_pw_hac_t",
        development_season=dev_season,
        confirmation_season=conf_season,
        required_projection_guards=tuple(sorted(MANDATORY_GUARDS)),
        confirmation_checkpoints=REGISTERED_CHECKPOINTS,
        calibrated_superiority_alphas=calibrated_superiority_alphas,
        gw1_4_material_loss_limit=gw1_4_material_loss_limit,
        statistical_early_harm_mode=statistical_early_harm_mode,
        statistical_early_harm_alpha=EARLY_HARM_P_THRESHOLD,
        availability_skip_unused_alpha=True,
        gw38_expiry_hours_after_last_kickoff=DEFAULT_GW38_EXPIRY_HOURS,
        certification_digest=certification_digest,
        completed_segments=DEFAULT_SPARSE_COMPLETED_SEGMENTS,
    )


def verify_certification_artifacts(
    cert_dir: Path,
    *,
    expected_digest: str | None = None,
    project_root: Path | None = None,
    check_evaluator_revisions: bool = True,
) -> CertificationVerificationResult:
    """Fail-closed verifier for sparse confirmation artifacts, canonical digests, and evaluator drift."""
    cert_path = cert_dir / "certification_result.json"
    manifest_path = cert_dir / "preregistration_manifest.json"
    errors: list[str] = []
    drifted_files: list[str] = []

    if not cert_path.is_file():
        errors.append(f"Missing certification artifact: {cert_path}")
        return {
            "passed": False,
            "errors": errors,
            "drifted_files": drifted_files,
            "certified": None,
            "certified_mode": None,
            "certification_digest": None,
            "statistical_protocol_hash": None,
            "manifest_digest_match": False,
            "canonical_digest_match": False,
            "evaluator_revisions_match": False,
        }

    cert_data = json.loads(cert_path.read_bytes())
    manifest_digest_match = False
    canonical_digest_match = False
    evaluator_revisions_match = not check_evaluator_revisions

    if not manifest_path.is_file():
        errors.append(f"Missing preregistration manifest: {manifest_path}")
        manifest: dict[str, Any] | None = None
    else:
        manifest = json.loads(manifest_path.read_bytes())
        manifest_body = {k: v for k, v in manifest.items() if k != "manifest_digest"}
        computed_manifest_digest = compute_canonical_digest(manifest_body)
        manifest_digest_match = (
            manifest.get("manifest_digest") == computed_manifest_digest
            and cert_data.get("manifest_digest") == computed_manifest_digest
        )
        if not manifest_digest_match:
            errors.append("Preregistration manifest_digest mismatch")

    if all(k in cert_data for k in CERTIFICATION_SUMMARY_KEYS):
        summary_body = {k: cert_data[k] for k in CERTIFICATION_SUMMARY_KEYS}
        computed_cert_digest = compute_canonical_digest(summary_body)
        canonical_digest_match = cert_data.get("certification_digest") == computed_cert_digest
        if not canonical_digest_match:
            errors.append("Canonical certification_digest mismatch")
    else:
        missing_keys = [k for k in CERTIFICATION_SUMMARY_KEYS if k not in cert_data]
        errors.append(f"Certification artifact missing canonical summary keys: {missing_keys}")

    if cert_data.get("certified") is not True:
        errors.append("Certification artifact is not certified=True")
    if cert_data.get("certified_mode") not in ("enforced", "advisory"):
        errors.append(f"Unsupported certified_mode: {cert_data.get('certified_mode')!r}")
    if cert_data.get("parity_passed") is not True:
        errors.append("Certification parity_passed is not True")
    if cert_data.get("live_adoption_blocked") is not False:
        errors.append("Certification live_adoption_blocked is not False")

    c_cfg = cert_data.get("certified_protocol_config")
    if not isinstance(c_cfg, dict) or c_cfg.get("certification_digest") != cert_data.get("certification_digest"):
        errors.append("certified_protocol_config missing or certification_digest mismatch")
    else:
        try:
            rebuilt = statistical_protocol_config_from_dict(c_cfg)
            if rebuilt.compute_hash() != cert_data.get("statistical_protocol_hash"):
                errors.append("statistical_protocol_hash mismatch against certified_protocol_config")
            tuning_block = cert_data.get("tuning")
            cert_mode = cert_data.get("certified_mode")
            cert_digest = cert_data.get("certification_digest")
            if (
                cert_data.get("certified") is True
                and cert_mode in ("enforced", "advisory")
                and isinstance(tuning_block, dict)
                and isinstance(cert_digest, str)
            ):
                expected_cfg = build_certified_protocol_config(
                    calibrated_superiority_alphas=tuning_block["calibrated_superiority_alphas"],
                    gw1_4_material_loss_limit=float(tuning_block["gw1_4_material_loss_limit"]),
                    statistical_early_harm_mode=cert_mode,
                    certification_digest=cert_digest,
                )
                if (
                    rebuilt != expected_cfg
                    or compute_canonical_digest(c_cfg) != compute_canonical_digest(expected_cfg.to_dict())
                ):
                    errors.append("certified_protocol_config mismatch against certified tuning/mode parameters")
        except Exception as exc:
            errors.append(f"Invalid certified_protocol_config: {exc}")

    if expected_digest is not None and cert_data.get("certification_digest") != expected_digest:
        errors.append(
            f"certification_digest {cert_data.get('certification_digest')!r} != expected {expected_digest!r}"
        )

    if check_evaluator_revisions and manifest is not None:
        eval_root = project_root or PROJECT_ROOT
        recorded = manifest.get("evaluator_revisions")
        missing_eval = [rel for rel in EVALUATOR_REVISION_PATHS if not (eval_root / rel).is_file()]
        if missing_eval:
            evaluator_revisions_match = False
            drifted_files.extend(missing_eval)
            errors.append(f"Missing evaluator source files under {eval_root}: {missing_eval}")
        elif not isinstance(recorded, dict):
            evaluator_revisions_match = False
            errors.append("Manifest missing evaluator_revisions mapping")
        else:
            live_revs = _evaluator_revisions(project_root=eval_root)
            for key, expected_hash in live_revs.items():
                if recorded.get(key) != expected_hash:
                    drifted_files.append(key)
            extra_keys = [k for k in recorded if k not in live_revs]
            drifted_files.extend(extra_keys)
            evaluator_revisions_match = len(drifted_files) == 0
            if not evaluator_revisions_match:
                errors.append(f"Evaluator revisions drifted since preregistration: {drifted_files}")

    return {
        "passed": len(errors) == 0,
        "errors": errors,
        "drifted_files": drifted_files,
        "certified": cert_data.get("certified"),
        "certified_mode": cert_data.get("certified_mode"),
        "certification_digest": cert_data.get("certification_digest"),
        "statistical_protocol_hash": cert_data.get("statistical_protocol_hash"),
        "manifest_digest_match": manifest_digest_match,
        "canonical_digest_match": canonical_digest_match,
        "evaluator_revisions_match": evaluator_revisions_match,
    }

