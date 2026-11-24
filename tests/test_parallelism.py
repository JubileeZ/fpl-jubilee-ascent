"""Tests for cross-OS machine-adaptive CPU core detection and worker sizing."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import solver.parallelism as par


def test_detect_macos_apple_silicon_p_cores() -> None:
    with (
        patch("solver.parallelism.platform.system", return_value="Darwin"),
        patch("solver.parallelism.subprocess.check_output", return_value="4\n"),
        patch("solver.parallelism.os.cpu_count", return_value=8),
    ):
        assert par.detect_physical_cores() == 4
        assert par.recommended_pytest_workers() == 4
        assert par.recommended_backtest_workers(heavy=True) == 4
        assert par.recommended_backtest_workers(heavy=False) == 6
        assert par.recommended_live_solver_threads(concurrent_arms=1) == 4
        assert par.recommended_live_solver_threads(concurrent_arms=3) == 1


def test_detect_macos_intel_physical_cores() -> None:
    def fake_sysctl(cmd: list[str], **_kwargs: object) -> str:
        if cmd[-1] == "hw.perflevel0.physicalcpu":
            raise RuntimeError("unknown oid")
        return "8\n"

    with (
        patch("solver.parallelism.platform.system", return_value="Darwin"),
        patch("solver.parallelism.subprocess.check_output", side_effect=fake_sysctl),
        patch("solver.parallelism.os.cpu_count", return_value=16),
    ):
        assert par.detect_physical_cores() == 8
        assert par.recommended_backtest_workers(heavy=True) == 7
        assert par.recommended_live_solver_threads(concurrent_arms=3) == 2


def test_detect_linux_physical_and_cgroup_clamp(tmp_path: Path) -> None:
    cpuinfo_blocks = []
    for core in range(12):
        for _smt in range(2):
            cpuinfo_blocks.append(f"physical id\t: 0\ncore id\t\t: {core}\n")
    cpuinfo_text = "\n".join(cpuinfo_blocks)

    assert par._parse_linux_physical_cores(cpuinfo_text) == 12

    with (
        patch("solver.parallelism.platform.system", return_value="Linux"),
        patch("solver.parallelism.Path.is_file", return_value=True),
        patch("solver.parallelism.Path.read_text", return_value=cpuinfo_text),
        patch("solver.parallelism._detect_linux_cgroup_quota_cores", return_value=None),
        patch("solver.parallelism.os.sched_getaffinity", return_value=set(range(24)), create=True),
        patch("solver.parallelism.os.cpu_count", return_value=24),
    ):
        assert par.detect_physical_cores() == 12
        assert par.recommended_pytest_workers() == 12
        assert par.recommended_backtest_workers(heavy=True) == 11
        assert par.recommended_live_solver_threads(concurrent_arms=1) == 4
        assert par.recommended_live_solver_threads(concurrent_arms=3) == 4

    with (
        patch("solver.parallelism.platform.system", return_value="Linux"),
        patch("solver.parallelism.Path.is_file", return_value=True),
        patch("solver.parallelism.Path.read_text", return_value=cpuinfo_text),
        patch("solver.parallelism._detect_linux_cgroup_quota_cores", return_value=4),
        patch("solver.parallelism.os.sched_getaffinity", return_value=set(range(4)), create=True),
        patch("solver.parallelism.os.cpu_count", return_value=4),
    ):
        assert par.detect_physical_cores() == 4
        assert par.recommended_pytest_workers() == 4


def test_detect_windows_smt_heuristic() -> None:
    with (
        patch("solver.parallelism.platform.system", return_value="Windows"),
        patch("solver.parallelism.os.cpu_count", return_value=16),
    ):
        assert par.detect_physical_cores() == 8
        assert par.recommended_pytest_workers() == 8
        assert par.recommended_live_solver_threads(concurrent_arms=3) == 2
