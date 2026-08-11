"""Unit tests for ownership value explorer (season schema)."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pandas as pd
import pytest


def _load_mod() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "ownership_value_explorer",
        Path("docs/research/ownership-value-explorer/plot_ownership_value_explorer.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def explorer_mod() -> ModuleType:
    return _load_mod()


def test_build_explorer_frame_season_overlays(explorer_mod: ModuleType) -> None:
    season = pd.DataFrame(
        [
            {
                "player_id": 1,
                "web_name": "Alpha",
                "club_short": "ARS",
                "position": "MID",
                "expected_role": "Nailed Starter",
                "draft_availability": "eligible",
                "cost": 8.0,
                "ownership_pct": 12.5,
                "total_season_xp": 160.0,
                "total_season_xmins": 3000.0,
                "avg_xmins_season": 78.9,
                "xp_per_90_season": 4.8,
                "total_gw1_6_xp": 24.0,
                "total_gw1_6_xmins": 540.0,
                "avg_xmins_gw1_6": 90.0,
                "xp_per_90_gw1_6": 4.0,
                "n_gameweeks": 38,
            },
            {
                "player_id": 2,
                "web_name": "Beta",
                "club_short": "CHE",
                "position": "FWD",
                "expected_role": "Rotation Option",
                "draft_availability": "eligible",
                "cost": 5.5,
                "ownership_pct": 0.4,
                "total_season_xp": 40.0,
                "total_season_xmins": 400.0,
                "avg_xmins_season": 10.5,
                "xp_per_90_season": 9.0,
                "total_gw1_6_xp": 6.0,
                "total_gw1_6_xmins": 60.0,
                "avg_xmins_gw1_6": 10.0,
                "xp_per_90_gw1_6": 9.0,
                "n_gameweeks": 38,
            },
        ]
    )
    simulation = pd.DataFrame(
        {
            "scenario": ["S1: example", "S5: example"],
            "phase": ["GW1-2 Pre-FH", "GW1-3 Pre-WC"],
            "player_id": [1, 2],
        }
    )
    user_picks = pd.DataFrame({"player_id": [1]})

    frame = explorer_mod.build_explorer_frame(season, simulation=simulation, user_picks=user_picks)
    assert len(frame) == 2
    alpha = frame.loc[frame["player_id"] == 1].iloc[0]
    beta = frame.loc[frame["player_id"] == 2].iloc[0]
    assert float(alpha["xp_per_90_season"]) == 4.8
    assert float(alpha["ownership_pct"]) == 12.5
    assert bool(alpha["in_s1"]) is True
    assert bool(alpha["in_user"]) is True
    assert bool(beta["in_s5"]) is True
    assert bool(beta["in_user"]) is False
