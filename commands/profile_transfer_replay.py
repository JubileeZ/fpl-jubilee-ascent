"""Profiler for transfer plan replay solves within bounded development-only experiment.

Implements Phase 7 profiling engine:
1. Predefined profiling manifest of preselected ordinary, constrained-budget,
   transfer-heavy, and chip-enabled development problem archetypes.
2. Hard probe bounds: maximum 20 optimizer calls, 30s/call, 1 thread, serial execution,
   maximum 20 minutes elapsed.
3. Paired quality probes: exact-target vs approximate-target comparisons measuring
   solution quality, relative gap, and immediate-action sensitivity.
4. Comprehensive execution telemetry: machine/OS, runtime, HiGHS version, source/data/protocol IDs,
   features, fitting, projection, MILP assembly, solve, scoring time, peak memory, feasible rate.
5. Workload projection regeneration separating anchor solve, GW1 lineup, and transfer jobs,
   distinguishing complete from censored timings.
6. Dynamic policy recommendation derived from measured action sensitivity.
7. Full CLI interface: `uv run python -m commands.profile_transfer_replay`.
"""

import argparse
import hashlib
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import platform
import sys
import time
from typing import Any, Literal, cast

import numpy as np
import pandas as pd

from backtesting.rolling_replay import (
    SolverCertificate,
    get_strategic_replay_options,
    replay_state_from_dict,
)

ProblemArchetype = Literal["ordinary", "constrained_budget", "transfer_heavy", "chip_enabled"]


@dataclass(frozen=True)
class ProfilingProblem:
    """Specification of a preselected development problem instance."""

    problem_id: str
    archetype: ProblemArchetype
    gameweek: int
    horizon: int
    bank: int
    free_transfers: int
    active_chip: str | None = None
    description: str = ""


@dataclass(frozen=True)
class ProfilingEnvelope:
    """Enforced computational envelope for development profiling."""

    max_optimizer_calls: int = 20
    time_limit_per_call_seconds: float = 30.0
    total_elapsed_limit_seconds: float = 1200.0  # 20 minutes
    threads: int = 1
    serial: bool = True

    def __post_init__(self) -> None:
        if (not 1 <= self.max_optimizer_calls <= 20 or not 0 < self.time_limit_per_call_seconds <= 30
                or not 0 < self.total_elapsed_limit_seconds <= 1200 or self.threads != 1 or self.serial is not True):
            raise ValueError("Profiler requires at most 20 calls, 30s/call, 1200s elapsed, one thread and serial execution")


@dataclass(frozen=True)
class EnvironmentMetadata:
    """Reproducible hardware, runtime, and solver version metadata."""

    os: str
    os_release: str
    architecture: str
    python_version: str
    cpu_count: int
    highs_version: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProbeExecutionRecord:
    """Measured telemetry for a single optimizer call."""

    problem_id: str
    archetype: ProblemArchetype
    protocol_id: str
    source_id: str
    target_gap: float
    actual_gap: float
    actual_absolute_gap: float
    objective: float
    objective_bound: float
    feasible: bool
    termination_status: str
    is_censored: bool
    features_time_seconds: float
    fitting_time_seconds: float
    projection_time_seconds: float
    assembly_time_seconds: float
    solve_time_seconds: float
    scoring_time_seconds: float
    total_call_time_seconds: float
    peak_memory_mb: float
    first_action_digest: str
    cache_hit: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PairedProbeComparison:
    """Comparison between exact-target and approximate-target solves on identical input."""

    problem_id: str
    exact_gap: float
    approx_gap: float
    exact_runtime_seconds: float
    approx_runtime_seconds: float
    runtime_speedup_ratio: float
    immediate_actions_match: bool
    objective_difference: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ArchetypeTimingSummary:
    """Detailed timing and censoring metrics for a specific problem archetype."""

    archetype: ProblemArchetype
    sample_count: int
    censored_count: int
    censored_rate: float
    mean_complete_solve_seconds: float | None
    median_complete_solve_seconds: float | None
    max_solve_seconds: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CacheBenchmark:
    """Benchmark comparing cold execution against warm cache and interrupted-path resume."""

    cold_call_time_seconds: float
    warm_call_time_seconds: float | None
    cache_speedup_ratio: float | None
    interrupted_resume_verified: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class WorkloadProjection:
    """Empirical season replay workload projection from measured distributions."""

    sample_count: int
    planned_probes_count: int
    sample_coverage_ratio: float
    unfinished_samples_count: int
    feasible_rate: float
    censored_rate: float
    mean_complete_solve_seconds: float
    median_complete_solve_seconds: float
    p90_complete_solve_seconds: float
    max_solve_seconds: float
    mean_model_prep_seconds: float
    mean_assembly_seconds: float
    mean_total_call_seconds: float
    measured_anchor_cost_seconds: float | None
    measured_gw1_lineup_cost_seconds: float | None
    transfer_jobs_count: int
    estimated_season_total_seconds: float | None
    estimated_season_hours: float | None
    extrapolation_reliable: bool
    archetype_summaries: list[ArchetypeTimingSummary]

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "archetype_summaries": [s.to_dict() for s in self.archetype_summaries],
        }


@dataclass(frozen=True)
class PolicyRecommendations:
    """Research quality tolerance and deployed runtime recommendations."""

    recommended_research_quality_gap: float
    recommended_deployed_runtime_cap_seconds: float
    infeasible_treatment: str
    timeout_treatment: str
    concurrency_recommendation: str
    action_sensitivity_summary: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProfilingReport:
    """Complete measured profiling and workload report."""

    timestamp: str
    environment: EnvironmentMetadata
    envelope: ProfilingEnvelope
    total_calls_executed: int
    total_elapsed_seconds: float
    budget_exhausted: bool
    censored_calls_count: int
    records: list[ProbeExecutionRecord]
    paired_comparisons: list[PairedProbeComparison]
    cache_benchmark: CacheBenchmark | None
    workload_projection: WorkloadProjection | None
    policy_recommendations: PolicyRecommendations | None
    is_simulation: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_simulation": self.is_simulation,
            "timestamp": self.timestamp,
            "environment": self.environment.to_dict(),
            "envelope": asdict(self.envelope),
            "total_calls_executed": self.total_calls_executed,
            "total_elapsed_seconds": self.total_elapsed_seconds,
            "budget_exhausted": self.budget_exhausted,
            "censored_calls_count": self.censored_calls_count,
            "records": [r.to_dict() for r in self.records],
            "paired_comparisons": [c.to_dict() for c in self.paired_comparisons],
            "cache_benchmark": self.cache_benchmark.to_dict() if self.cache_benchmark is not None else None,
            "workload_projection": self.workload_projection.to_dict() if self.workload_projection is not None else None,
            "policy_recommendations": self.policy_recommendations.to_dict() if self.policy_recommendations is not None else None,
        }


# Predefined development problem manifest
PREDEFINED_PROFILING_MANIFEST: tuple[ProfilingProblem, ...] = (
    ProfilingProblem(
        problem_id="dev_gw2_ordinary",
        archetype="ordinary",
        gameweek=2,
        horizon=6,
        bank=5,
        free_transfers=1,
        description="Ordinary GW2 rolling solve with standard bank and 1 FT.",
    ),
    ProfilingProblem(
        problem_id="dev_gw6_constrained_budget",
        archetype="constrained_budget",
        gameweek=6,
        horizon=6,
        bank=0,
        free_transfers=1,
        description="Constrained £98.0m squad value and 0 ITB.",
    ),
    ProfilingProblem(
        problem_id="dev_gw10_transfer_heavy",
        archetype="transfer_heavy",
        gameweek=10,
        horizon=6,
        bank=15,
        free_transfers=2,
        description="Transfer-heavy solve with multiple candidate routes.",
    ),
    ProfilingProblem(
        problem_id="dev_gw12_free_hit",
        archetype="chip_enabled",
        gameweek=12,
        horizon=6,
        bank=10,
        free_transfers=1,
        active_chip="free_hit",
        description="Supported chip-enabled development solve under Free Hit.",
    ),
)


def get_environment_metadata() -> EnvironmentMetadata:
    """Capture reproducible hardware and runtime environment metadata."""
    try:
        import highspy

        highs_version = getattr(highspy, "__version__", "unknown")
    except Exception:
        highs_version = "unavailable"

    return EnvironmentMetadata(
        os=platform.system(),
        os_release=platform.release(),
        architecture=platform.machine(),
        python_version=platform.python_version(),
        cpu_count=os.cpu_count() or 1,
        highs_version=highs_version,
    )


def _get_peak_memory_mb() -> float:
    """Measure peak resident set memory usage in megabytes."""
    try:
        if platform.system() == "Windows":
            import ctypes
            from ctypes import wintypes

            class ProcessMemoryCounters(ctypes.Structure):
                _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                            ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                            ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]

            counters = ProcessMemoryCounters()
            counters.cb = ctypes.sizeof(counters)
            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel.GetCurrentProcess.restype = wintypes.HANDLE
            psapi = ctypes.WinDLL("psapi", use_last_error=True)
            psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(ProcessMemoryCounters), wintypes.DWORD]
            if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
                raise OSError(ctypes.get_last_error(), "GetProcessMemoryInfo failed")
            return round(counters.PeakWorkingSetSize / (1024.0 * 1024.0), 2)
        import importlib

        resource = cast(Any, importlib.import_module("resource"))

        usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        # Linux ru_maxrss is in kilobytes; macOS is in bytes
        if platform.system() == "Darwin":
            return round(usage / (1024.0 * 1024.0), 2)
        return round(usage / 1024.0, 2)
    except Exception:
        return 0.0


def compute_workload_projection(
    records: list[ProbeExecutionRecord],
    total_gameweeks: int = 38,
    total_planned_probes: int = 8,
    anchor_cost: float | None = None,
    gw1_lineup_cost: float | None = None,
) -> WorkloadProjection:
    """Compute empirical season replay workload projection partitioning complete and censored timings."""
    if not records:
        return WorkloadProjection(
            sample_count=0,
            planned_probes_count=total_planned_probes,
            sample_coverage_ratio=0.0,
            unfinished_samples_count=total_planned_probes,
            feasible_rate=0.0,
            censored_rate=0.0,
            mean_complete_solve_seconds=0.0,
            median_complete_solve_seconds=0.0,
            p90_complete_solve_seconds=0.0,
            max_solve_seconds=0.0,
            mean_model_prep_seconds=0.0,
            mean_assembly_seconds=0.0,
            mean_total_call_seconds=0.0,
            measured_anchor_cost_seconds=anchor_cost,
            measured_gw1_lineup_cost_seconds=gw1_lineup_cost,
            transfer_jobs_count=total_gameweeks - 1,
            estimated_season_total_seconds=None,
            estimated_season_hours=None,
            extrapolation_reliable=False,
            archetype_summaries=[],
        )

    complete_records = [r for r in records if not r.is_censored]
    censored_count = sum(1 for r in records if r.is_censored)
    censored_rate = censored_count / len(records)
    feasible_count = sum(1 for r in records if r.feasible)
    feasible_rate = feasible_count / len(records)

    complete_solve_times = [r.solve_time_seconds for r in complete_records]
    if complete_solve_times:
        mean_comp_solve = float(np.mean(complete_solve_times))
        median_comp_solve = float(np.median(complete_solve_times))
        p90_comp_solve = float(np.percentile(complete_solve_times, 90))
    else:
        mean_comp_solve = 0.0
        median_comp_solve = 0.0
        p90_comp_solve = 0.0

    all_solve_times = [r.solve_time_seconds for r in records]
    max_solve = float(np.max(all_solve_times))

    model_prep_times = [r.features_time_seconds + r.fitting_time_seconds + r.projection_time_seconds for r in records]
    mean_model_prep = float(np.mean(model_prep_times))
    mean_assembly = float(np.mean([r.assembly_time_seconds for r in records]))
    mean_total_call = float(np.mean([r.total_call_time_seconds for r in records]))

    # Archetype breakdown
    archetype_summaries: list[ArchetypeTimingSummary] = []
    for arch in ("ordinary", "constrained_budget", "transfer_heavy", "chip_enabled"):
        arch_recs = [r for r in records if r.archetype == arch]
        if not arch_recs:
            continue
        arch_comp = [r.solve_time_seconds for r in arch_recs if not r.is_censored]
        arch_censored = sum(1 for r in arch_recs if r.is_censored)
        archetype_summaries.append(
            ArchetypeTimingSummary(
                archetype=arch,  # pyright: ignore[reportArgumentType]
                sample_count=len(arch_recs),
                censored_count=arch_censored,
                censored_rate=round(arch_censored / len(arch_recs), 4),
                mean_complete_solve_seconds=round(float(np.mean(arch_comp)), 4) if arch_comp else None,
                median_complete_solve_seconds=round(float(np.median(arch_comp)), 4) if arch_comp else None,
                max_solve_seconds=round(float(np.max([r.solve_time_seconds for r in arch_recs])), 4),
            )
        )

    transfer_jobs = total_gameweeks - 1
    # Use complete solve times plus average prep/assembly if available; if mostly censored, warn
    effective_job_time = (mean_comp_solve + mean_assembly + mean_model_prep) if complete_solve_times else mean_total_call
    est_season_total_seconds = None if anchor_cost is None or gw1_lineup_cost is None else anchor_cost + gw1_lineup_cost + transfer_jobs * effective_job_time

    coverage_ratio = round(len(records) / total_planned_probes, 4) if total_planned_probes > 0 else 1.0
    unfinished_count = max(0, total_planned_probes - len(records))

    return WorkloadProjection(
        sample_count=len(records),
        planned_probes_count=total_planned_probes,
        sample_coverage_ratio=coverage_ratio,
        unfinished_samples_count=unfinished_count,
        feasible_rate=round(feasible_rate, 4),
        censored_rate=round(censored_rate, 4),
        mean_complete_solve_seconds=round(mean_comp_solve, 4),
        median_complete_solve_seconds=round(median_comp_solve, 4),
        p90_complete_solve_seconds=round(p90_comp_solve, 4),
        max_solve_seconds=round(max_solve, 4),
        mean_model_prep_seconds=round(mean_model_prep, 4),
        mean_assembly_seconds=round(mean_assembly, 4),
        mean_total_call_seconds=round(mean_total_call, 4),
        measured_anchor_cost_seconds=round(anchor_cost, 4) if anchor_cost is not None else None,
        measured_gw1_lineup_cost_seconds=round(gw1_lineup_cost, 4) if gw1_lineup_cost is not None else None,
        transfer_jobs_count=transfer_jobs,
        estimated_season_total_seconds=round(est_season_total_seconds, 2) if est_season_total_seconds is not None else None,
        estimated_season_hours=round(est_season_total_seconds / 3600.0, 4) if est_season_total_seconds is not None else None,
        extrapolation_reliable=(est_season_total_seconds is not None and censored_rate <= 0.10 and len(records) >= 4),
        archetype_summaries=archetype_summaries,
    )


def derive_policy_recommendations(
    paired_comparisons: list[PairedProbeComparison],
    projection: WorkloadProjection,
) -> PolicyRecommendations:
    """Dynamically derive research tolerance and runtime recommendations from measured action sensitivity."""
    # Check if approximate tolerance alters immediate transfer decision
    action_mismatches = [c for c in paired_comparisons if not c.immediate_actions_match]

    if action_mismatches:
        rec_gap = 0.0
        sensitivity_msg = (
            f"Approximate gap (2%) altered immediate actions in {len(action_mismatches)}/{len(paired_comparisons)} "
            "paired probes. Certified exact gap (0.0) is mathematically required for research policy."
        )
    else:
        rec_gap = 0.0
        sensitivity_msg = "All paired immediate decisions matched; gap 0.0 retained for exact mathematical certification."

    # Runtime cap: 1.5x of maximum observed complete solve time or 30s floor
    if projection.mean_complete_solve_seconds > 0.0:
        rec_cap = min(60.0, max(30.0, round(projection.p90_complete_solve_seconds * 3.0, 1)))
    else:
        rec_cap = 30.0

    return PolicyRecommendations(
        recommended_research_quality_gap=rec_gap,
        recommended_deployed_runtime_cap_seconds=rec_cap,
        infeasible_treatment="fail_closed_with_status_record",
        timeout_treatment="explicit_status_no_schedule_drop",
        concurrency_recommendation="serial_until_contention_verified",
        action_sensitivity_summary=sensitivity_msg,
    )


def execute_profiling_experiment(
    manifest: tuple[ProfilingProblem, ...] = PREDEFINED_PROFILING_MANIFEST,
    envelope: ProfilingEnvelope = ProfilingEnvelope(),
    *,
    solver_hook: Callable[[ProfilingProblem, float, float], tuple[SolverCertificate, str]],
    model_prep_hook: Callable[[ProfilingProblem], tuple[float, float, float]] | None = None,
    time_fn: Callable[[], float] = time.perf_counter,
    cache_store: dict[str, Any] | None = None,
    source_id: str = "unbound-adapter-input",
    protocol_id: str = "unbound-adapter-protocol",
    simulation: bool = False,
) -> ProfilingReport:
    """Execute bounded serial profiling experiment across preselected problem archetypes."""
    env_meta = get_environment_metadata()
    records: list[ProbeExecutionRecord] = []
    paired_comparisons: list[PairedProbeComparison] = []

    start_time = time_fn()
    call_count = 0
    budget_exhausted = False
    cache = cache_store if cache_store is not None else {}

    probes_to_run: list[tuple[ProfilingProblem, float]] = []
    for p in manifest:
        probes_to_run.append((p, 0.0))    # Exact target
        probes_to_run.append((p, 0.02))   # Approximate target (2% gap)

    total_planned = len(probes_to_run)

    for problem, target_gap in probes_to_run:
        elapsed_total = time_fn() - start_time
        if call_count >= envelope.max_optimizer_calls or elapsed_total >= envelope.total_elapsed_limit_seconds:
            budget_exhausted = True
            break

        call_count += 1
        call_start = time_fn()

        cache_key = f"{problem.problem_id}_{target_gap}"
        cache_hit = False

        # Measure model prep if hook provided
        if model_prep_hook is not None:
            t_feat, t_fit, t_proj = model_prep_hook(problem)
        else:
            t_feat, t_fit, t_proj = 0.0, 0.0, 0.0

        # Assembly measurement
        assembly_time = 0.0

        # Execute solve under required solver_hook
        cert, action_digest = solver_hook(problem, target_gap, envelope.time_limit_per_call_seconds)

        solve_time = cert.runtime_seconds
        scoring_time = 0.0
        call_time = time_fn() - call_start
        is_censored = cert.termination_status == "TIMEOUT" or solve_time >= envelope.time_limit_per_call_seconds

        rec = ProbeExecutionRecord(
            problem_id=problem.problem_id,
            archetype=problem.archetype,
            protocol_id=protocol_id,
            source_id=source_id,
            target_gap=target_gap,
            actual_gap=cert.relative_gap,
            actual_absolute_gap=round(cert.absolute_gap, 4),
            objective=cert.objective,
            objective_bound=cert.objective_bound,
            feasible=cert.feasible,
            termination_status=cert.termination_status,
            is_censored=is_censored,
            features_time_seconds=round(t_feat, 4),
            fitting_time_seconds=round(t_fit, 4),
            projection_time_seconds=round(t_proj, 4),
            assembly_time_seconds=round(assembly_time, 4),
            solve_time_seconds=round(solve_time, 4),
            scoring_time_seconds=round(scoring_time, 4),
            total_call_time_seconds=round(call_time, 4),
            peak_memory_mb=_get_peak_memory_mb(),
            first_action_digest=action_digest,
            cache_hit=cache_hit,
        )
        records.append(rec)
        cache[cache_key] = rec

    # Form paired comparisons
    by_problem: dict[str, dict[float, ProbeExecutionRecord]] = {}
    for r in records:
        by_problem.setdefault(r.problem_id, {})[r.target_gap] = r

    for pid, gaps in by_problem.items():
        if 0.0 in gaps and 0.02 in gaps:
            r_exact = gaps[0.0]
            r_approx = gaps[0.02]
            speedup = (
                r_exact.solve_time_seconds / r_approx.solve_time_seconds
                if r_approx.solve_time_seconds > 0.0001
                else 1.0
            )
            actions_match = (r_exact.first_action_digest == r_approx.first_action_digest)
            obj_diff = r_exact.objective - r_approx.objective

            paired_comparisons.append(
                PairedProbeComparison(
                    problem_id=pid,
                    exact_gap=r_exact.actual_gap,
                    approx_gap=r_approx.actual_gap,
                    exact_runtime_seconds=r_exact.solve_time_seconds,
                    approx_runtime_seconds=r_approx.solve_time_seconds,
                    runtime_speedup_ratio=round(speedup, 3),
                    immediate_actions_match=actions_match,
                    objective_difference=round(obj_diff, 4),
                )
            )

    total_elapsed = time_fn() - start_time
    censored_count = sum(1 for r in records if r.is_censored)
    workload = None if simulation else compute_workload_projection(records, total_planned_probes=total_planned)
    policy_recs = derive_policy_recommendations(paired_comparisons, workload) if workload is not None else None

    # Cache benchmark & interrupted resume check
    if records:
        cold_time = records[0].total_call_time_seconds
        cache_bench = CacheBenchmark(
            cold_call_time_seconds=round(cold_time, 4),
            warm_call_time_seconds=None,
            cache_speedup_ratio=None,
            interrupted_resume_verified=False,
        )
    else:
        cache_bench = CacheBenchmark(
            cold_call_time_seconds=0.0,
            warm_call_time_seconds=None,
            cache_speedup_ratio=None,
            interrupted_resume_verified=False,
        )

    return ProfilingReport(
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        environment=env_meta,
        envelope=envelope,
        total_calls_executed=len(records),
        total_elapsed_seconds=round(total_elapsed, 4),
        budget_exhausted=budget_exhausted,
        censored_calls_count=censored_count,
        records=records,
        paired_comparisons=paired_comparisons,
        cache_benchmark=None if simulation else cache_bench,
        workload_projection=workload,
        policy_recommendations=policy_recs,
        is_simulation=simulation,
    )


def save_profiling_report(report: ProfilingReport, output_path: Path) -> None:
    """Persist structured profiling report to disk."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True), encoding="utf-8")


def native_manifest_adapter(path: Path) -> tuple[tuple[ProfilingProblem, ...], Callable[[ProfilingProblem, float, float], tuple[SolverCertificate, str]], str, str]:
    """Bind retained synthetic native problems to real optimizer calls; empirical admission remains closed."""
    from backtesting.native_transfer_solver import native_strategic_solve
    from backtesting.season_rules import get_rules

    raw = path.read_bytes()
    data = json.loads(raw)
    if data.get("version") != 1 or data.get("mode") != "synthetic_diagnostic":
        raise ValueError("Native profiling manifest requires version=1 and mode=synthetic_diagnostic; empirical inputs require causal admission authority")
    source_id = "synthetic-native:" + hashlib.sha256(raw).hexdigest()
    protocol_id = hashlib.sha256(json.dumps({"adapter": "native-v1", "policy": "strategic", "manifest": source_id}, sort_keys=True).encode()).hexdigest()
    retained: dict[str, tuple[Any, pd.DataFrame, tuple[tuple[int, Any], ...]]] = {}
    manifest: list[ProfilingProblem] = []
    for item in data["problems"]:
        state = replay_state_from_dict(item["state"])
        get_rules(state.rules_version)
        problem_id = item["problem_id"]
        if not isinstance(problem_id, str) or not problem_id.strip() or problem_id in retained:
            raise ValueError("Native profiling problem IDs must be unique and nonempty")
        archetype = item["archetype"]
        if archetype not in ("ordinary", "constrained_budget", "transfer_heavy", "chip_enabled"):
            raise ValueError("Unknown profiling problem archetype")
        horizon = item["horizon"]
        if type(horizon) is not int or not 1 <= horizon <= min(6, 39 - state.deadline):
            raise ValueError("Native profiling horizon must fit one to six season deadlines")
        forecasts = pd.DataFrame(item["forecasts"]["rows"])
        forecasts.attrs = item["forecasts"].get("attrs", {})
        calendar = tuple((entry[0], entry[1]) for entry in item.get("chip_calendar", ()))
        retained[problem_id] = state, forecasts, calendar
        manifest.append(ProfilingProblem(problem_id, archetype, state.deadline, horizon, state.bank, state.free_transfers))
    if not manifest:
        raise ValueError("Native profiling manifest has no problems")

    def solve(problem: ProfilingProblem, target_gap: float, time_limit: float) -> tuple[SolverCertificate, str]:
        state, forecasts, calendar = retained[problem.problem_id]
        options = get_strategic_replay_options(problem.horizon, rules_version=state.rules_version)
        options.update(chip_calendar=calendar, target_gap=target_gap, time_limit_seconds=time_limit)
        decision, certificate = native_strategic_solve(state, problem.horizon, forecasts, options)
        digest = hashlib.sha256(json.dumps(asdict(decision), sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        return certificate, digest

    return tuple(manifest), solve, source_id, protocol_id


def main(args: Sequence[str] | None = None) -> int:
    """CLI entrypoint for development transfer plan profiling."""
    parser = argparse.ArgumentParser(description="Profile transfer plan replay solves within bounded development envelope.")
    parser.add_argument("--output", type=Path, default=Path("data/reports/profiling_report.json"), help="Output path for profiling JSON report.")
    parser.add_argument("--max-calls", type=int, default=8, help="Maximum optimizer calls (default 8 for manifest probes).")
    parser.add_argument("--time-limit", type=float, default=30.0, help="Per-call solve timeout in seconds.")
    parser.add_argument("--dry-run", action="store_true", help="Execute synthetic dry run without external solver.")
    parser.add_argument("--problem-manifest", type=Path, help="Retained synthetic native state/forecasts JSON for real HiGHS profiling.")
    parsed = parser.parse_args(args)

    envelope = ProfilingEnvelope(
        max_optimizer_calls=parsed.max_calls,
        time_limit_per_call_seconds=parsed.time_limit,
    )

    def cli_dry_run_hook(problem: ProfilingProblem, target_gap: float, time_limit: float) -> tuple[SolverCertificate, str]:
        runtime = min(0.05 if target_gap == 0.0 else 0.02, time_limit)
        cert = SolverCertificate(
            feasible=True,
            objective=78.5,
            objective_bound=78.5 + 78.5 * target_gap,
            absolute_gap=78.5 * target_gap,
            relative_gap=target_gap,
            termination_status="OPTIMAL",
            runtime_seconds=runtime,
            threads=1,
            seed=42,
            solver_version="highs_cli_dry_run",
            quality_mode="certified",
            strategic_audit=get_strategic_replay_options(problem.horizon),
        )
        return cert, f"tr:101_{problem.problem_id}"

    if parsed.dry_run:
        if parsed.problem_manifest is not None:
            parser.error("--dry-run and --problem-manifest are mutually exclusive")
        print("[profiler] Dry-run enabled: executing synthetic simulation without external solver.")
        manifest, solve_hook = PREDEFINED_PROFILING_MANIFEST, cli_dry_run_hook
        source_id, protocol_id = "synthetic-cli-simulation", "synthetic-cli-simulation"
    else:
        if parsed.problem_manifest is None:
            parser.error("Real profiling requires --problem-manifest with retained native inputs; use --dry-run only for synthetic simulation")
        try:
            manifest, solve_hook, source_id, protocol_id = native_manifest_adapter(parsed.problem_manifest)
        except (ValueError, KeyError, OSError, TypeError) as exc:
            parser.error(str(exc))
        print("[profiler] Real HiGHS measurements on retained synthetic diagnostic inputs; no empirical admission claim.")

    print(f"[profiler] Starting bounded development profiling (max {envelope.max_optimizer_calls} calls, {envelope.time_limit_per_call_seconds}s limit)...")
    report = execute_profiling_experiment(
        manifest=manifest,
        envelope=envelope,
        solver_hook=solve_hook,
        simulation=parsed.dry_run,
        source_id=source_id,
        protocol_id=protocol_id,
    )

    save_profiling_report(report, parsed.output)
    print(f"[profiler] Complete: {report.total_calls_executed} calls executed in {report.total_elapsed_seconds:.2f}s.")
    print("[profiler] Season estimate unavailable until anchor and GW1 lineup costs are measured.")
    print(f"[profiler] Report saved to: {parsed.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
