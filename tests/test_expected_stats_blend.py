"""Unit tests for Stage 2 dual-floor usable blend + Defcon fill."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "build_expected_stats",
    Path("docs/research/gw1-6-preseason-pipeline/02-expected-stats-gw1-5/build_expected_stats.py"),
)
_MOD = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(_MOD)


def _season(minutes: float, xg: float = 0.5, defcon: float = 5.0, has_defcon: bool = True) -> dict:
    return {
        "minutes": minutes,
        "xg": xg,
        "xa": 0.1,
        "defcon": defcon,
        "saves": 0.0,
        "gc": 1.2,
        "has_defcon_evidence": 1.0 if has_defcon else 0.0,
    }


def test_dual_floor_keeps_thin_year_in_older_mean_only() -> None:
    # Isak-like: thin 2025/26 (694) + strong older years
    usable = [
        ("2023/24", _season(2253, xg=0.40)),
        ("2024/25", _season(2758, xg=0.50)),
        ("2025/26", _season(694, xg=0.10)),
    ]
    rates, src, note = _MOD._blend_usable(usable, pid=0, pos="FWD")
    assert src == "fpl_recency_50_50"
    assert "2024/25" in note  # latest >=900
    assert "2025/26" in note  # thin year still in older mean
    # latest 0.50 * 0.5 + mean(0.40, 0.10)*0.5 = 0.25 + 0.125 = 0.375
    assert abs(rates["xg"] - 0.375) < 1e-9


def test_equal_weight_when_no_latest_eligible() -> None:
    usable = [
        ("2024/25", _season(600, xg=0.20)),
        ("2025/26", _season(700, xg=0.40)),
    ]
    rates, src, _note = _MOD._blend_usable(usable, pid=0, pos="MID")
    assert src == "fpl_equal_weight_thin_latest"
    assert abs(rates["xg"] - 0.30) < 1e-9


def test_defcon_fill_when_no_evidence() -> None:
    usable = [
        ("2024/25", _season(2000, xg=0.20, defcon=0.0, has_defcon=False)),
        ("2025/26", _season(2100, xg=0.30, defcon=0.0, has_defcon=False)),
    ]
    rates, src, note = _MOD._blend_usable(usable, pid=504, pos="DEF")
    # pid 504 has external defcon_cbit package
    assert "defcon_external_fill" in src or "defcon_external_fill" in note
    assert rates["defcon"] == float(_MOD.EXTERNAL_RESEARCH_RATES[504]["defcon"])
    assert abs(rates["xg"] - 0.25) < 1e-9
