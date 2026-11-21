"""Sparse Champion confirmation calibration, vectorized parity, and certification harness (ADR 0070)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Literal, TypedDict

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
from backtesting.promotion_evidence import MANDATORY_GUARDS
from backtesting.season_rules import load_season_lifecycle

PROJECT_ROOT = Path(__file__).resolve().parents[1]

TUNING_SEED = 20101
CERTIFICATION_SEED = 20102
FALLBACK_ADVISORY_SEED = 20103
DEFAULT_NUM_SIMULATIONS = 20_000
DEFAULT_FPL_DELTA_SD_PER_GW = 4.0
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


class VectorizedEarlyHarmResult(TypedDict):
    triggered: np.ndarray
    statistical_triggered: np.ndarray
    gw1_4_floor_breached: np.ndarray
    cumulative_p_harm: np.ndarray
    segment_p_harms: dict[str, np.ndarray]


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
    is_primary_power: bool = False
    description: str = ""

    def __post_init__(self) -> None:
        if self.slate_size not in (1, 2):
            raise ValueError(f"slate_size must be 1 or 2, got {self.slate_size}")
        if len(self.finalist_effects_sd) != self.slate_size:
            raise ValueError("finalist_effects_sd length must equal slate_size")
        if self.gw1_4_effects_sd is not None and len(self.gw1_4_effects_sd) != self.slate_size:
            raise ValueError("gw1_4_effects_sd length must equal slate_size")
        if not 0.0 <= self.phi_ar < 1.0:
            raise ValueError("phi_ar must lie in [0, 1)")
        if not 0.0 <= self.rho_champ <= 1.0:
            raise ValueError("rho_champ must lie in [0, 1]")

    @property
    def null_indices(self) -> list[int]:
        return [
            j
            for j in range(self.slate_size)
            if self.finalist_effects_sd[j] == 0.0
            and (self.gw1_4_effects_sd is None or self.gw1_4_effects_sd[j] == 0.0)
        ]

    @property
    def improving_indices(self) -> list[int]:
        return [j for j in range(self.slate_size) if self.finalist_effects_sd[j] > 0.0]

    @property
    def harmful_indices(self) -> list[int]:
        return [
            j
            for j in range(self.slate_size)
            if self.finalist_effects_sd[j] < 0.0
            or (self.gw1_4_effects_sd is not None and self.gw1_4_effects_sd[j] < 0.0)
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
    """Return the preregistered certification scenario grid covering null, mixed-null, power, and harm."""
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
            description="Primary GW38 power + mixed-null (rank1=+0.40 SD, rank2=null, mild, guards GW15)",
            **mild,
        ),
        ScenarioSpec("m2_mixed_r1_null_r2_imp_mild_gw15", "mixed_null", 2, (0.0, 0.40), safeguards_pass_from_gw=15, description="M=2 mixed-null (rank1=null, rank2=+0.40 SD, mild, guards GW15)", **mild),
        ScenarioSpec("m2_mixed_r1_imp_r2_null_persistent_gw15", "mixed_null", 2, (0.40, 0.0), safeguards_pass_from_gw=15, description="M=2 mixed-null (rank1=+0.40 SD, rank2=null, persistent, guards GW15)", **persistent),
        ScenarioSpec("m2_mixed_r1_null_r2_imp_persistent_gw15", "mixed_null", 2, (0.0, 0.40), safeguards_pass_from_gw=15, description="M=2 mixed-null (rank1=null, rank2=+0.40 SD, persistent, guards GW15)", **persistent),
        ScenarioSpec("m2_mixed_r1_imp_r2_null_mild_gw30", "mixed_null", 2, (0.40, 0.0), safeguards_pass_from_gw=30, description="M=2 mixed-null (rank1=+0.40 SD, rank2=null, mild, guards GW30)", **mild),
        ScenarioSpec("m2_mixed_r1_null_r2_imp_mild_gw30", "mixed_null", 2, (0.0, 0.40), safeguards_pass_from_gw=30, description="M=2 mixed-null (rank1=null, rank2=+0.40 SD, mild, guards GW30)", **mild),
        # Additional power scenarios (+0.20, +0.60 marginal SD improvement)
        ScenarioSpec("m1_power_pos020_mild_gw15", "power", 1, (0.20,), safeguards_pass_from_gw=15, description="M=1 +0.20 SD power, mild, guards GW15", **mild),
        ScenarioSpec("m2_power_pos020_mixed_mild_gw15", "mixed_null", 2, (0.20, 0.0), safeguards_pass_from_gw=15, description="M=2 +0.20 SD + null, mild, guards GW15", **mild),
        ScenarioSpec("m1_power_pos060_mild_gw15", "power", 1, (0.60,), safeguards_pass_from_gw=15, description="M=1 +0.60 SD power, mild, guards GW15", **mild),
        ScenarioSpec("m2_power_pos060_mixed_mild_gw15", "mixed_null", 2, (0.60, 0.0), safeguards_pass_from_gw=15, description="M=2 +0.60 SD + null, mild, guards GW15", **mild),
        # Genuinely harmful scenarios (-0.40, -0.60, -0.80 SD & severe GW1-4 loss)
        ScenarioSpec("m1_harm_neg040_mild_gw15", "harmful", 1, (-0.40,), safeguards_pass_from_gw=15, description="M=1 -0.40 SD harmful, mild", **mild),
        ScenarioSpec("m1_harm_neg060_mild_gw15", "harmful", 1, (-0.60,), safeguards_pass_from_gw=15, description="M=1 -0.60 SD harmful, mild", **mild),
        ScenarioSpec("m1_harm_neg080_mild_gw15", "harmful", 1, (-0.80,), safeguards_pass_from_gw=15, description="M=1 -0.80 SD harmful, mild", **mild),
        ScenarioSpec("m1_harm_neg060_persistent_gw15", "harmful", 1, (-0.60,), safeguards_pass_from_gw=15, description="M=1 -0.60 SD harmful, persistent", **persistent),
        ScenarioSpec(
            "m1_harm_severe_gw1_4_mild_gw15",
            "harmful",
            1,
            (0.0,),
            gw1_4_effects_sd=(-2.50,),
            safeguards_pass_from_gw=15,
            description="M=1 severe GW1-4 collapse (-2.50 SD/GW = -40 pts E[GW1-4]), then neutral",
            **mild,
        ),
        ScenarioSpec("m2_harm_r1_neg060_r2_null_mild_gw15", "harmful", 2, (-0.60, 0.0), safeguards_pass_from_gw=15, description="M=2 rank1=-0.60 SD harmful + rank2=null, mild", **mild),
    )


def _evaluator_revisions() -> dict[str, str]:
    rel_paths = (
        "backtesting/evaluation_protocol.py",
        "backtesting/evidence_statistics.py",
        "backtesting/projection_guards.py",
        "backtesting/promotion_evidence.py",
        "backtesting/sparse_certification.py",
    )
    material = {rel: (PROJECT_ROOT / rel).read_bytes() for rel in rel_paths if (PROJECT_ROOT / rel).is_file()}
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
) -> dict[str, Any]:
    """Build immutable preregistration manifest with canonical SHA-256 digest."""
    if num_simulations < 10 or fpl_delta_sd_per_gw <= 0.0:
        raise ValueError("Invalid simulation run size or FPL SD scale")
    grid = build_preregistered_scenario_grid()
    body: dict[str, Any] = {
        "manifest_version": 1,
        "protocol_target_version": "v2.0",
        "authority_references": [
            "docs/adr/0070-weekly-planner-selection-and-champion-adoption.md",
            "docs/product/champion-adoption-implementation.md",
            "issues #195, #196, #201",
        ],
        "evaluator_revisions": _evaluator_revisions(),
        "simulator_config": {
            "num_gameweeks": 38,
            "registered_checkpoints": list(REGISTERED_CHECKPOINTS),
            "fpl_delta_sd_per_gw": float(fpl_delta_sd_per_gw),
            "fpl_scale_basis": (
                "Paired Candidate-Champion weekly net-points marginal SD calibrated at 4.0 pts/GW "
                "(matching smoke_gate_calibration.csv and test_evidence_statistics.py under ~18.56 pts/GW "
                "Champion dispersion from ADR 0069)."
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
                "Execute 1 predeclared advisory Early-Harm run on untouched fallback_seed=20103 ONLY if "
                "enforced statistical Early-Harm fails its <=5% false terminal exclusion upper-95 gate "
                "on seed=20102 while false full pass <=5% and primary GW38 power >=1/3 both hold."
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
        drift = np.full(num_gameweeks, float(spec.finalist_effects_sd[j]) * float(fpl_delta_sd_per_gw), dtype=float)
        if spec.gw1_4_effects_sd is not None:
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

    triggered = (stat_trig | gw1_4_breached) if statistical_mode == "enforced" else gw1_4_breached
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
            innov = rng.standard_t(df=5.0, size=length) * math.sqrt(3.0 / 5.0) * 4.0
            series = np.empty(length, dtype=float)
            x = float(innov[0])
            for t in range(length):
                x = phi * x + math.sqrt(1.0 - phi**2) * float(innov[t])
                series[t] = drift + x
            batch_rows.append(series)

        mat = np.vstack(batch_rows)
        vec_hac = vectorized_kendall_pw_hac_test(mat, alpha=alpha)
        vec_eh_enf = vectorized_early_harm_fallback(
            mat, gw1_4_material_loss_limit=36.0, statistical_mode="enforced"
        )
        vec_eh_adv = vectorized_early_harm_fallback(
            mat, gw1_4_material_loss_limit=36.0, statistical_mode="advisory"
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
                paired, gw1_4_material_loss_limit=36.0, statistical_mode="enforced"
            )
            s_eh_adv = evaluate_early_harm_fallback(
                paired, gw1_4_material_loss_limit=36.0, statistical_mode="advisory"
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
            else:
                excluded[:, j] |= breach_gw1_4

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
        int(np.sum(np.all(excluded[:, harmful_indices] | stat_harm_flagged[:, harmful_indices], axis=1)))
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


def tune_sparse_protocol(
    *,
    num_simulations: int = DEFAULT_NUM_SIMULATIONS,
    seed: int = TUNING_SEED,
    fpl_delta_sd_per_gw: float = DEFAULT_FPL_DELTA_SD_PER_GW,
    harm_alpha: float = EARLY_HARM_P_THRESHOLD,
) -> dict[str, Any]:
    """Calibrate M=1/M=2 superiority alphas and GW1-4 net-points floor strictly on seed=20101."""
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

    # 1. Calibrate GW1-4 material-loss limit in net FPL points across non-harmful scenarios
    non_harmful_mins: list[np.ndarray] = []
    for item in precomputed:
        good_idx = item["spec"].non_harmful_indices
        if good_idx:
            non_harmful_mins.append(np.min(item["gw1_4_sum"][:, good_idx], axis=1))

    target_gw1_4_upper = 0.020 if num_simulations >= 2000 else 0.015
    gw1_4_limit = 60.0
    for limit_half_pts in range(12, 241):  # 6.0 to 120.0 in 0.5 pt steps
        limit = limit_half_pts * 0.5
        worst_val = 0.0
        for arr in non_harmful_mins:
            k = int(np.sum(arr < -limit))
            bound = clopper_pearson_one_sided_95(k, num_simulations)
            metric = bound["upper_95"] if num_simulations >= 2000 else bound["rate"]
            worst_val = max(worst_val, float(metric))
        if worst_val <= target_gw1_4_upper:
            gw1_4_limit = limit
            break

    # 2. Calibrate OBF per-look superiority thresholds for M=1 and M=2 on seed=20101 ONLY,
    #    protecting worst-case FWER under advisory (which strictly upper-bounds enforced) while maximizing GW38 power.
    target_fwer_upper = 0.043 if num_simulations >= 2000 else 0.035
    calibrated_alphas: dict[str, dict[str, float]] = {}
    scale_factors: dict[int, float] = {}
    selected_weights: dict[int, tuple[float, float]] = {}

    # Precompute fast boolean/float arrays for instant bisection across (w15, w30)
    def _prep_fast_null(item: Mapping[str, Any]) -> dict[str, Any]:
        spec_i: ScenarioSpec = item["spec"]
        null_idx = spec_i.null_indices
        excl = item["gw1_4_sum"][:, null_idx] < -float(gw1_4_limit)
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
        ]
        fast_nulls = [_prep_fast_null(item) for item in null_items]
        power_items = [
            item
            for item in precomputed
            if item["spec"].slate_size == m_size
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

    summary_body = {
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

    return {
        **summary_body,
        "certification_digest": certification_digest,
        "statistical_protocol_hash": statistical_protocol_hash,
        "certified_protocol_config": certified_protocol_dict,
        "manifest": manifest,
        "parity_check": parity,
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

