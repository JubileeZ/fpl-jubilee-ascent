"""Identity matching for Stage 1 lineup sources (Bruno G. vs B.Fernandes, Virgil)."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pandas as pd
import pytest


def _load_mod() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "refresh_expected_role",
        Path("docs/research/gw1-6-preseason-pipeline/01-expected-role-gw1-5/refresh_expected_role.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def role_mod() -> ModuleType:
    return _load_mod()


def test_bruno_fernandes_matches_b_fernandes_not_bruno_g(role_mod: ModuleType) -> None:
    m = role_mod.player_matches_source
    assert m("Bruno Fernandes", "B.Fernandes", "Bruno", "Borges Fernandes") is True
    assert m("Bruno Fernandes", "Bruno G.", "Bruno", "Guimarães Rodriguez Moura") is False
    assert m("B.Fernandes", "Fernandes", "Mateus", "Fernandes") is False
    assert m("Bruno Fernandes", "Fernandes", "Mateus", "Fernandes") is False


def test_bruno_g_matches_guimaraes_not_united_bruno(role_mod: ModuleType) -> None:
    m = role_mod.player_matches_source
    assert m("Bruno Guimaraes", "Bruno G.", "Bruno", "Guimarães Rodriguez Moura") is True
    assert m("Bruno G.", "Bruno G.", "Bruno", "Guimarães Rodriguez Moura") is True
    assert m("Bruno Guimaraes", "B.Fernandes", "Bruno", "Borges Fernandes") is False


def test_virgil_matches_van_dijk(role_mod: ModuleType) -> None:
    m = role_mod.player_matches_source
    assert m("Van Dijk", "Virgil", "Virgil", "van Dijk") is True
    assert m("Virgil van Dijk", "Virgil", "Virgil", "van Dijk") is True
    assert m("Van Dijk", "Virgil") is False  # web_name-only cannot see surname


def test_inject_does_not_move_bruno_g_to_mun(role_mod: ModuleType) -> None:
    players = pd.DataFrame(
        [
            {
                "id": 426,
                "web_name": "B.Fernandes",
                "first_name": "Bruno",
                "second_name": "Borges Fernandes",
                "club_id": 16,
                "position_id": 3,
            },
            {
                "id": 452,
                "web_name": "Bruno G.",
                "first_name": "Bruno",
                "second_name": "Guimarães Rodriguez Moura",
                "club_id": 17,
                "position_id": 3,
            },
        ]
    )
    clubs = pd.DataFrame(
        [
            {"id": 16, "short_name": "MUN", "name": "Man Utd"},
            {"id": 1, "short_name": "ARS", "name": "Arsenal"},
        ]
    )
    df = pd.DataFrame(
        [
            {
                "club": "Arsenal",
                "club_short": "ARS",
                "player_id": 452,
                "web_name": "Bruno G.",
                "position": "MID",
                "expected_role": "Nailed Starter",
                "p_start": 0.9,
                "p_sub_in": 0.05,
                "p_dnp": 0.05,
                "mins_if_start": 85,
                "mins_if_sub": 20,
                "confidence": "high",
                "conflict_rule": "unanimous_dual_source",
                "draft_eligible": True,
                "reason": "transfer",
                "sources": "overlay",
                "draft_availability": "eligible",
            },
            {
                "club": "Man Utd",
                "club_short": "MUN",
                "player_id": 426,
                "web_name": "B.Fernandes",
                "position": "MID",
                "expected_role": "Rotation",
                "p_start": 0.4,
                "p_sub_in": 0.25,
                "p_dnp": 0.35,
                "mins_if_start": 70,
                "mins_if_sub": 20,
                "confidence": "medium",
                "conflict_rule": "source_disagreement_or_single",
                "draft_eligible": False,
                "reason": "old",
                "sources": "overlay",
                "draft_availability": "not_role_eligible",
            },
        ]
    )
    ffs = {"MUN": ["Bruno Fernandes"], "ARS": []}
    out = role_mod.inject_missing_ffs_starters(df, ffs, {"MUN": ["Bruno Fernandes"]}, players, clubs)
    bruno_g = out.loc[out["player_id"] == 452].iloc[0]
    assert bruno_g["club_short"] == "ARS"
    bfer = out.loc[out["player_id"] == 426].iloc[0]
    assert bfer["club_short"] == "MUN"


def test_rebuild_assigns_united_bruno_to_b_fernandes(role_mod: ModuleType) -> None:
    players = pd.DataFrame(
        [
            {
                "id": 426,
                "web_name": "B.Fernandes",
                "first_name": "Bruno",
                "second_name": "Borges Fernandes",
                "club_id": 16,
            },
            {
                "id": 452,
                "web_name": "Bruno G.",
                "first_name": "Bruno",
                "second_name": "Guimarães Rodriguez Moura",
                "club_id": 1,
            },
            {
                "id": 356,
                "web_name": "Virgil",
                "first_name": "Virgil",
                "second_name": "van Dijk",
                "club_id": 14,
            },
        ]
    )
    df = pd.DataFrame(
        [
            {
                "player_id": 426,
                "web_name": "B.Fernandes",
                "club_short": "MUN",
                "expected_role": "Rotation",
                "p_start": 0.4,
                "p_sub_in": 0.25,
                "p_dnp": 0.35,
                "mins_if_start": 70,
                "mins_if_sub": 20,
                "draft_availability": "not_role_eligible",
            },
            {
                "player_id": 452,
                "web_name": "Bruno G.",
                "club_short": "ARS",
                "expected_role": "Rotation",
                "p_start": 0.4,
                "p_sub_in": 0.25,
                "p_dnp": 0.35,
                "mins_if_start": 70,
                "mins_if_sub": 20,
                "draft_availability": "not_role_eligible",
            },
            {
                "player_id": 356,
                "web_name": "Virgil",
                "club_short": "LIV",
                "expected_role": "Rotation",
                "p_start": 0.4,
                "p_sub_in": 0.25,
                "p_dnp": 0.35,
                "mins_if_start": 70,
                "mins_if_sub": 20,
                "draft_availability": "not_role_eligible",
            },
        ]
    )
    ffs = {
        "MUN": ["Bruno Fernandes"],
        "ARS": ["Bruno Guimaraes"],
        "LIV": ["Van Dijk"],
    }
    meerkat = {
        "MUN": ["Bruno Fernandes"],
        "ARS": ["Bruno Guimaraes"],
        "LIV": ["Van Dijk"],
    }
    out = role_mod.rebuild_roles_from_sources(df, ffs, meerkat, players=players)
    assert out.loc[out["player_id"] == 426, "expected_role"].iloc[0] == "Nailed Starter"
    assert out.loc[out["player_id"] == 452, "expected_role"].iloc[0] == "Nailed Starter"
    assert out.loc[out["player_id"] == 356, "expected_role"].iloc[0] == "Nailed Starter"
    assert out.loc[out["player_id"] == 452, "club_short"].iloc[0] == "ARS"
