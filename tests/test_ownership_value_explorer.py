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
            "scenario": ["S1: example", "S5: example", "S13: example", "S13: example"],
            "phase": ["GW1-2 Pre-FH", "GW1-3 Pre-WC", "GW1-3 Pre-WC", "GW4-6 Post-WC"],
            "player_id": [1, 2, 2, 1],
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
    assert bool(alpha["in_wc4_core"]) is True
    assert bool(alpha["in_s13"]) is False
    assert bool(beta["in_s5"]) is True
    assert bool(beta["in_s13"]) is True
    assert bool(beta["in_wc4_core"]) is False
    assert bool(beta["in_user"]) is False


def test_html_includes_player_table_and_search(explorer_mod: ModuleType, tmp_path: Path) -> None:
    season = pd.DataFrame(
        [
            {
                "player_id": 356,
                "web_name": "Virgil",
                "club_short": "LIV",
                "position": "DEF",
                "expected_role": "Nailed Starter",
                "draft_availability": "eligible",
                "cost": 6.5,
                "ownership_pct": 16.3,
                "total_season_xp": 140.0,
                "total_season_xmins": 2945.0,
                "avg_xmins_season": 77.5,
                "xp_per_90_season": 4.3,
                "total_gw1_6_xp": 22.0,
                "total_gw1_6_xmins": 465.0,
                "avg_xmins_gw1_6": 77.5,
                "xp_per_90_gw1_6": 4.3,
                "n_gameweeks": 38,
            },
            {
                "player_id": 452,
                "web_name": "Bruno G.",
                "club_short": "ARS",
                "position": "MID",
                "expected_role": "Nailed Starter",
                "draft_availability": "eligible",
                "cost": 7.0,
                "ownership_pct": 8.2,
                "total_season_xp": 145.0,
                "total_season_xmins": 2945.0,
                "avg_xmins_season": 77.5,
                "xp_per_90_season": 4.4,
                "total_gw1_6_xp": 23.0,
                "total_gw1_6_xmins": 465.0,
                "avg_xmins_gw1_6": 77.5,
                "xp_per_90_gw1_6": 4.5,
                "n_gameweeks": 38,
            },
        ]
    )
    frame = explorer_mod.build_explorer_frame(season)
    path = tmp_path / "ownership_value_explorer.html"
    explorer_mod.write_explorer_html(frame, path)
    html = path.read_text(encoding="utf-8")
    assert 'id="player-search"' in html
    assert 'id="player-table"' in html
    assert '"web_name":"Virgil"' in html
    assert '"web_name":"Bruno G.","club_short":"ARS"' in html
    assert '"club_short":"MUN"' not in html


def test_role_csv_bruno_g_is_arsenal_not_united() -> None:
    roles = pd.read_csv(
        "data/research/gw1-6-preseason-pipeline/01-expected-role-gw1-5/expected-role-gw1-5.csv"
    )
    bruno_g = roles.loc[roles["web_name"] == "Bruno G."].iloc[0]
    assert bruno_g["club_short"] == "ARS"
    bfer = roles.loc[roles["web_name"] == "B.Fernandes"].iloc[0]
    assert bfer["club_short"] == "MUN"
    virgil = roles.loc[roles["web_name"] == "Virgil"].iloc[0]
    assert virgil["club_short"] == "LIV"
    assert virgil["expected_role"] == "Nailed Starter"


def test_explorer_metrics_identity() -> None:
    metrics = pd.read_csv("data/research/ownership-value-explorer/ownership_value_metrics.csv")
    bruno_g = metrics.loc[metrics["web_name"] == "Bruno G."].iloc[0]
    assert bruno_g["club_short"] == "ARS"
    bfer = metrics.loc[metrics["web_name"] == "B.Fernandes"].iloc[0]
    assert bfer["club_short"] == "MUN"
    assert bool(bfer["in_s13"]) is True
    virgil = metrics.loc[metrics["web_name"] == "Virgil"].iloc[0]
    assert float(virgil["avg_xmins_season"]) >= 45.0
    haaland = metrics.loc[metrics["web_name"] == "Haaland"].iloc[0]
    assert bool(haaland["in_s13"]) is True
    assert bool(haaland["in_wc4_core"]) is True
