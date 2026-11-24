"""Cross-OS machine-adaptive CPU core detection and worker sizing helpers."""

from __future__ import annotations

import os
from pathlib import Path
import platform
import subprocess


def _read_int_sysctl(key: str) -> int | None:
    try:
        out = subprocess.check_output(
            ["sysctl", "-n", key],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        val = int(out)
        return val if val > 0 else None
    except Exception:
        return None


def _detect_macos_p_cores() -> int | None:
    if platform.system() != "Darwin":
        return None
    return _read_int_sysctl("hw.perflevel0.physicalcpu")


def _parse_linux_physical_cores(cpuinfo_text: str) -> int | None:
    pairs: set[tuple[str, str]] = set()
    phys_id: str | None = None
    core_id: str | None = None
    for line in cpuinfo_text.splitlines():
        stripped = line.strip()
        if not stripped:
            if phys_id is not None and core_id is not None:
                pairs.add((phys_id, core_id))
            phys_id = None
            core_id = None
            continue
        if ":" not in stripped:
            continue
        key, _, val = stripped.partition(":")
        key_s = key.strip().lower()
        val_s = val.strip()
        if key_s == "physical id":
            phys_id = val_s
        elif key_s == "core id":
            core_id = val_s
    if phys_id is not None and core_id is not None:
        pairs.add((phys_id, core_id))
    return len(pairs) if pairs else None


def _detect_linux_cgroup_quota_cores() -> int | None:
    # cgroup v2: /sys/fs/cgroup/cpu.max -> "<quota> <period>"
    v2_path = Path("/sys/fs/cgroup/cpu.max")
    if v2_path.is_file():
        try:
            parts = v2_path.read_text(encoding="utf-8").strip().split()
            if len(parts) >= 2 and parts[0] != "max":
                quota, period = int(parts[0]), int(parts[1])
                if quota > 0 and period > 0:
                    return max(1, (quota + period - 1) // period)
        except Exception:
            pass
    # cgroup v1 fallback
    q_path = Path("/sys/fs/cgroup/cpu/cpu.cfs_quota_us")
    p_path = Path("/sys/fs/cgroup/cpu/cpu.cfs_period_us")
    if q_path.is_file() and p_path.is_file():
        try:
            quota = int(q_path.read_text(encoding="utf-8").strip())
            period = int(p_path.read_text(encoding="utf-8").strip())
            if quota > 0 and period > 0:
                return max(1, (quota + period - 1) // period)
        except Exception:
            pass
    return None


def detect_physical_cores() -> int:
    """Detect usable physical (or Apple Silicon P-core / cgroup-clamped) CPU cores."""
    sys_name = platform.system()
    logical = os.cpu_count() or 1
    if sys_name == "Darwin":
        p_cores = _detect_macos_p_cores()
        if p_cores is not None:
            return max(1, p_cores)
        phys = _read_int_sysctl("hw.physicalcpu")
        return max(1, phys if phys is not None else logical)
    if sys_name == "Linux":
        cores: int | None = None
        cpuinfo_path = Path("/proc/cpuinfo")
        if cpuinfo_path.is_file():
            try:
                cores = _parse_linux_physical_cores(cpuinfo_path.read_text(encoding="utf-8"))
            except Exception:
                cores = None
        if cores is None:
            cores = logical
        try:
            affinity = len(os.sched_getaffinity(0))  # type: ignore[attr-defined]
            if affinity > 0:
                cores = min(cores, affinity)
        except (AttributeError, OSError):
            pass
        cgroup_cores = _detect_linux_cgroup_quota_cores()
        if cgroup_cores is not None:
            cores = min(cores, cgroup_cores)
        return max(1, cores)
    # Windows / other: halve logical count >= 4 to avoid SMT oversubscription.
    return max(1, logical // 2) if logical >= 4 else max(1, logical)


def recommended_pytest_workers() -> int:
    """Return physical-core-sized pytest-xdist worker count (capped at 16)."""
    return min(16, max(1, detect_physical_cores()))


def recommended_backtest_workers(*, heavy: bool = True) -> int:
    """Return worker count for multi-trajectory backtests or light forecast prep."""
    cores = detect_physical_cores()
    p_cores = _detect_macos_p_cores()
    if p_cores is not None and not heavy:
        logical = os.cpu_count() or p_cores
        return max(1, min(logical, p_cores + 2))
    if cores >= 8:
        return max(1, cores - 1 if heavy else cores)
    return max(1, cores)


def recommended_live_solver_threads(*, concurrent_arms: int = 1) -> int:
    """Return HiGHS thread count per live MILP arm without oversubscribing."""
    arms = max(1, int(concurrent_arms))
    return min(4, max(1, detect_physical_cores() // arms))
