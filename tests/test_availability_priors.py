"""Unit tests for research Draft Availability prior overlays."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "availability_priors",
    Path("docs/research/gw1-6-preseason-pipeline/availability_priors.py"),
)
_MOD = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(_MOD)
apply_availability_priors = _MOD.apply_availability_priors


def test_watch_haircut_gw1_to_5_only() -> None:
    p_start, p_sub, p_dnp = 0.90, 0.05, 0.05
    s, u, d = apply_availability_priors(p_start, p_sub, p_dnp, "watch", "", 3)
    assert s == 0.90 * 0.70
    assert u == 0.05
    assert abs(d - (0.05 + 0.90 * 0.30)) < 1e-9
    s6, u6, d6 = apply_availability_priors(p_start, p_sub, p_dnp, "watch", "", 6)
    assert (s6, u6, d6) == (0.90, 0.05, 0.05)


def test_exclude_gw1_5_zeros_through_gw5_not_gw6() -> None:
    s5, u5, d5 = apply_availability_priors(0.9, 0.05, 0.05, "exclude_gw1-5", "", 5)
    assert (s5, u5, d5) == (0.0, 0.0, 1.0)
    s6, u6, d6 = apply_availability_priors(0.9, 0.05, 0.05, "exclude_gw1-5", "", 6)
    assert (s6, u6, d6) == (0.9, 0.05, 0.05)


def test_exclude_gw1_only_gw1() -> None:
    s1, _, d1 = apply_availability_priors(0.75, 0.1, 0.15, "exclude_gw1", "", 1)
    assert (s1, d1) == (0.0, 1.0)
    s2, u2, d2 = apply_availability_priors(0.75, 0.1, 0.15, "exclude_gw1", "", 2)
    assert (s2, u2, d2) == (0.75, 0.1, 0.15)
