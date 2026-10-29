"""Unit tests for transfer plan replay profiling engine."""

from pathlib import Path
from typing import Any

from backtesting.rolling_replay import SolverCertificate
from commands.profile_transfer_replay import (
    PREDEFINED_PROFILING_MANIFEST,
    ProbeExecutionRecord,
    ProfilingEnvelope,
    ProfilingProblem,
    compute_workload_projection,
    execute_profiling_experiment,
    get_environment_metadata,
    main,
)


def _make_certificate(**overrides: Any) -> SolverCertificate:
    """Helper to instantiate a valid SolverCertificate for tests."""
    defaults: dict[str, Any] = {
        "feasible": True,
        "objective": 80.0,
        "objective_bound": 80.0,
        "absolute_gap": 0.0,
        "relative_gap": 0.0,
        "termination_status": "OPTIMAL",
        "runtime_seconds": 0.01,
        "threads": 1,
        "seed": 42,
        "solver_version": "mock_highs",
        "quality_mode": "certified",
        "strategic_audit": {},
    }
    defaults.update(overrides)
    return SolverCertificate(**defaults)


def test_predefined_manifest_covers_archetypes() -> None:
    """Verify that the predefined manifest covers all required problem archetypes."""
    archetypes = {p.archetype for p in PREDEFINED_PROFILING_MANIFEST}
    assert "ordinary" in archetypes
    assert "constrained_budget" in archetypes
    assert "transfer_heavy" in archetypes
    assert "chip_enabled" in archetypes


def test_environment_metadata_capture() -> None:
    """Verify environment metadata returns valid system information."""
    meta = get_environment_metadata()
    assert meta.os != ""
    assert meta.python_version != ""
    assert meta.architecture != ""
    assert meta.highs_version != ""


def test_profiling_call_cap_and_unfinished_coverage_reporting() -> None:
    """Verify that execution stops strictly at max_optimizer_calls and reports unfinished coverage."""
    envelope = ProfilingEnvelope(max_optimizer_calls=2, time_limit_per_call_seconds=10.0)

    def simple_hook(p: ProfilingProblem, gap: float, limit: float) -> tuple[SolverCertificate, str]:
        return _make_certificate(), "action_test"

    report = execute_profiling_experiment(
        manifest=PREDEFINED_PROFILING_MANIFEST,
        envelope=envelope,
        solver_hook=simple_hook,
    )
    assert report.total_calls_executed == 2
    assert report.budget_exhausted is True
    assert report.workload_projection.sample_coverage_ratio == 0.25  # 2 of 8 planned probes
    assert report.workload_projection.unfinished_samples_count == 6


def test_paired_probe_quality_comparison() -> None:
    """Verify paired probes compare exact vs approximate targets and test action agreement."""
    def mock_hook(problem: ProfilingProblem, target_gap: float, time_limit: float) -> tuple[SolverCertificate, str]:
        runtime = 0.01 if target_gap > 0.0 else 0.04
        action = "tr:101" if target_gap == 0.0 else ("tr:102" if problem.archetype == "transfer_heavy" else "tr:101")
        cert = _make_certificate(
            objective_bound=80.0 + 80.0 * target_gap,
            absolute_gap=80.0 * target_gap,
            relative_gap=target_gap,
            runtime_seconds=runtime,
        )
        return cert, action

    report = execute_profiling_experiment(
        manifest=PREDEFINED_PROFILING_MANIFEST[:2],
        envelope=ProfilingEnvelope(max_optimizer_calls=10),
        solver_hook=mock_hook,
    )

    assert len(report.paired_comparisons) == 2
    for comp in report.paired_comparisons:
        assert comp.exact_gap == 0.0
        assert comp.approx_gap == 0.02
        assert comp.runtime_speedup_ratio > 1.0


def test_censored_timing_individual_reporting() -> None:
    """Verify that timeouts are marked censored and partitioned from complete timings."""
    def timed_out_hook(problem: ProfilingProblem, target_gap: float, time_limit: float) -> tuple[SolverCertificate, str]:
        cert = _make_certificate(
            feasible=False,
            objective=0.0,
            objective_bound=100.0,
            absolute_gap=100.0,
            relative_gap=1.0,
            termination_status="TIMEOUT",
            runtime_seconds=time_limit,
            quality_mode="time_capped",
        )
        return cert, "none"

    report = execute_profiling_experiment(
        manifest=PREDEFINED_PROFILING_MANIFEST[:1],
        envelope=ProfilingEnvelope(max_optimizer_calls=2, time_limit_per_call_seconds=5.0),
        solver_hook=timed_out_hook,
    )

    assert report.censored_calls_count == 2
    assert report.records[0].is_censored is True
    assert report.records[0].termination_status == "TIMEOUT"
    assert report.workload_projection.extrapolation_reliable is False


def test_workload_projection_from_measured_distribution() -> None:
    """Verify workload projection computes accurate season estimates and separates anchor from transfers."""
    records = [
        ProbeExecutionRecord(
            problem_id="p1",
            archetype="ordinary",
            protocol_id="eval-v1",
            source_id="synth",
            target_gap=0.0,
            actual_gap=0.0,
            actual_absolute_gap=0.0,
            objective=75.0,
            objective_bound=75.0,
            feasible=True,
            termination_status="OPTIMAL",
            is_censored=False,
            features_time_seconds=0.005,
            fitting_time_seconds=0.010,
            projection_time_seconds=0.005,
            assembly_time_seconds=0.01,
            solve_time_seconds=0.10,
            scoring_time_seconds=0.005,
            total_call_time_seconds=0.13,
            peak_memory_mb=120.0,
            first_action_digest="tr:1",
            cache_hit=False,
        ),
        ProbeExecutionRecord(
            problem_id="p2",
            archetype="constrained_budget",
            protocol_id="eval-v1",
            source_id="synth",
            target_gap=0.0,
            actual_gap=0.0,
            actual_absolute_gap=0.0,
            objective=70.0,
            objective_bound=70.0,
            feasible=True,
            termination_status="OPTIMAL",
            is_censored=False,
            features_time_seconds=0.005,
            fitting_time_seconds=0.010,
            projection_time_seconds=0.005,
            assembly_time_seconds=0.01,
            solve_time_seconds=0.20,
            scoring_time_seconds=0.005,
            total_call_time_seconds=0.23,
            peak_memory_mb=120.5,
            first_action_digest="tr:2",
            cache_hit=True,
        ),
    ]

    proj = compute_workload_projection(records, total_gameweeks=38, total_planned_probes=4, anchor_cost=0.08, gw1_lineup_cost=0.02)
    assert proj.sample_count == 2
    assert proj.planned_probes_count == 4
    assert proj.sample_coverage_ratio == 0.5
    assert proj.censored_rate == 0.0
    assert proj.feasible_rate == 1.0
    assert proj.transfer_jobs_count == 37
    assert proj.measured_anchor_cost_seconds == 0.08
    assert proj.measured_gw1_lineup_cost_seconds == 0.02
    assert len(proj.archetype_summaries) == 2


def test_cli_execution_and_report_saving(tmp_path: Path) -> None:
    """Verify that CLI module invocation runs cleanly and outputs report JSON."""
    out_file = tmp_path / "cli_report.json"
    ret = main(["--output", str(out_file), "--max-calls", "2", "--dry-run"])
    assert ret == 0
    assert out_file.is_file()
    text = out_file.read_text(encoding="utf-8")
    assert "workload_projection" in text
    assert "policy_recommendations" in text
