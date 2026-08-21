"""Unit tests for Stage 2 Prior-Season Seed + destination GC overlay (ADR-0014)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd

_SPEC = importlib.util.spec_from_file_location(
    "build_expected_stats",
    Path("docs/archive/gw1-6-preseason-pipeline/02-expected-stats-gw1-5/build_expected_stats.py"),
)
_MOD = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(_MOD)


def test_destination_gc_map_home_away_and_league_avg() -> None:
    fixtures = pd.DataFrame([
        {"finished": True, "home_club_id": 1, "away_club_id": 2, "team_h_score": 2, "team_a_score": 0},
        {"finished": True, "home_club_id": 2, "away_club_id": 1, "team_h_score": 1, "team_a_score": 1},
        {"finished": False, "home_club_id": 1, "away_club_id": 2, "team_h_score": 9, "team_a_score": 9},
    ])
    clubs = pd.DataFrame({"id": [1, 2], "short_name": ["ARS", "MCI"]})
    gc_map, league_avg = _MOD._destination_gc_map(fixtures, clubs)
    # ARS: concede 0 home + 1 away → 0.5. MCI: concede 2 away + 1 home → 1.5.
    assert abs(gc_map["ARS"] - 0.5) < 1e-9
    assert abs(gc_map["MCI"] - 1.5) < 1e-9
    assert abs(league_avg - 1.0) < 1e-9


def test_promoted_club_uses_league_average() -> None:
    gc_map = {"ARS": 0.71, "LIV": 1.40}
    assert _MOD._lookup_destination_gc("HUL", gc_map, 1.375) == 1.375
    assert _MOD._lookup_destination_gc("ARS", gc_map, 1.375) == 0.71


def test_career_package_ignores_package_gc() -> None:
    rates, src, note = _MOD._career_attack(504, "DEF", Path("missing.json"))
    assert src == "career_individual"
    assert "gc" not in rates
    assert abs(rates["xg"] - 0.188) < 1e-9
    assert "Bundesliga" in note


def test_thin_career_sample_shrinks_toward_baseline() -> None:
    rates, _src, note = _MOD._career_attack(20, "MID", Path("missing.json"))
    weight = 153 / _MOD.MIN_USABLE_MINUTES
    expected_xg = weight * 0.690 + (1.0 - weight) * float(_MOD.POSITION_BASELINES["MID"]["xg"])
    assert abs(rates["xg"] - expected_xg) < 1e-9
    assert "thin-sample shrink" in note


def test_seed_defcon_fill_when_no_evidence() -> None:
    seed = {"defcon": 0.0, "has_defcon_evidence": 0.0}
    value, src = _MOD._fill_seed_defcon(seed, 504, "DEF")
    assert src == "defcon_external_fill"
    assert value == float(_MOD.EXTERNAL_RESEARCH_RATES[504]["defcon"])


def test_draft_on_fallback_raises() -> None:
    frame = pd.DataFrame(
        [
            {
                "web_name": "NewSigning",
                "player_id": 999,
                "position": "DEF",
                "club_short": "ARS",
                "expected_role": "Nailed Starter",
                "rate_source": "fallback_baseline+destination_gc",
            }
        ]
    )
    try:
        _MOD.raise_if_draft_on_fallback(frame)
    except SystemExit as exc:
        assert "NewSigning" in str(exc)
        assert "CAREER_INDIVIDUAL_RATES" in str(exc)
    else:
        raise AssertionError("expected SystemExit for Draft on fallback")


def test_rotation_on_fallback_does_not_raise() -> None:
    frame = pd.DataFrame(
        [
            {
                "web_name": "Bench",
                "player_id": 1,
                "position": "MID",
                "club_short": "HUL",
                "expected_role": "Rotation",
                "rate_source": "fallback_baseline+destination_gc",
            }
        ]
    )
    _MOD.raise_if_draft_on_fallback(frame)
