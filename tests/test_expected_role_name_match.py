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
        Path("docs/archive/gw1-6-preseason-pipeline/01-expected-role-gw1-5/refresh_expected_role.py"),
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


def test_sync_clubs_from_api_moves_trafford_to_leeds(role_mod: ModuleType) -> None:
    players = pd.DataFrame(
        [
            {"id": 385, "web_name": "Trafford", "club_id": 13},
            {"id": 110, "web_name": "Rushworth", "club_id": 7},
        ]
    )
    clubs = pd.DataFrame(
        [
            {"id": 13, "short_name": "LEE", "name": "Leeds"},
            {"id": 7, "short_name": "COV", "name": "Coventry City"},
            {"id": 15, "short_name": "MCI", "name": "Man City"},
            {"id": 5, "short_name": "BHA", "name": "Brighton"},
        ]
    )
    df = pd.DataFrame(
        [
            {
                "player_id": 385,
                "web_name": "Trafford",
                "club_short": "MCI",
                "club": "Man City",
                "api_club_id": 15,
                "api_club_short": "MCI",
            },
            {
                "player_id": 110,
                "web_name": "Rushworth",
                "club_short": "BHA",
                "club": "Brighton",
                "api_club_id": 5,
                "api_club_short": "BHA",
            },
        ]
    )
    out = role_mod.sync_clubs_from_api(df, players, clubs)
    assert out.loc[out["player_id"] == 385, "club_short"].iloc[0] == "LEE"
    assert out.loc[out["player_id"] == 110, "club_short"].iloc[0] == "COV"


def test_single_token_source_matches_web_name_or_surname_not_middle(role_mod: ModuleType) -> None:
    m = role_mod.player_matches_source
    assert m("Nunes", "Matheus N.", "Matheus", "Nunes") is True
    assert m("Nunes", "Vitor Reis", "Vitor", "de Oliveira Nunes dos Reis") is False
    assert m("James", "James", "Reece", "James") is True
    assert m("James", "Trafford", "James", "Trafford") is False
    assert m("Trafford", "Trafford", "James", "Trafford") is True
    assert m("Gabriel", "Gabriel", "Gabriel", "dos Santos Magalhães") is True
    assert m("White", "White", "Benjamin", "White") is True
    assert m("Pope", "Pope", "Nick", "Pope") is True


def test_rebuild_nunes_does_not_regular_vitor_reis(role_mod: ModuleType) -> None:
    players = pd.DataFrame(
        [
            {
                "id": 389,
                "web_name": "Matheus N.",
                "first_name": "Matheus",
                "second_name": "Nunes",
                "club_id": 15,
            },
            {
                "id": 396,
                "web_name": "Vitor Reis",
                "first_name": "Vitor",
                "second_name": "de Oliveira Nunes dos Reis",
                "club_id": 15,
            },
        ]
    )
    df = pd.DataFrame(
        [
            {
                "player_id": 389,
                "web_name": "Matheus N.",
                "club_short": "MCI",
                "expected_role": "Rotation",
                "p_start": 0.4,
                "p_sub_in": 0.25,
                "p_dnp": 0.35,
                "mins_if_start": 70,
                "mins_if_sub": 20,
                "draft_availability": "not_role_eligible",
            },
            {
                "player_id": 396,
                "web_name": "Vitor Reis",
                "club_short": "MCI",
                "expected_role": "Regular Starter",
                "p_start": 0.75,
                "p_sub_in": 0.10,
                "p_dnp": 0.15,
                "mins_if_start": 80,
                "mins_if_sub": 20,
                "draft_availability": "eligible",
            },
        ]
    )
    out = role_mod.rebuild_roles_from_sources(
        df, {"MCI": []}, {"MCI": ["Nunes"]}, players=players
    )
    assert out.loc[out["player_id"] == 389, "expected_role"].iloc[0] == "Regular Starter"
    assert out.loc[out["player_id"] == 396, "expected_role"].iloc[0] == "Rotation"


def test_apply_transfer_floors_bruno_g_out_of_contention(role_mod: ModuleType) -> None:
    df = pd.DataFrame(
        [
            {
                "web_name": "Bruno G.",
                "club_short": "ARS",
                "club": "Arsenal",
                "expected_role": "Out of Contention",
                "p_start": 0.0,
                "p_sub_in": 0.05,
                "p_dnp": 0.95,
                "mins_if_start": 45,
                "mins_if_sub": 10,
                "draft_availability": "not_role_eligible",
                "availability_reason": "Transferred to Arsenal; vacated Newcastle midfield.",
                "reason": "old",
                "sources": "overlay",
                "confidence": "low",
                "conflict_rule": "",
                "draft_eligible": False,
            }
        ]
    )
    out = role_mod.apply_transfer_club_moves(df)
    row = out.iloc[0]
    assert row["club_short"] == "ARS"
    assert row["expected_role"] == "Rotation"
    assert float(row["p_start"]) == 0.40
    assert "vacat" not in str(row["availability_reason"]).lower()


def test_sync_clubs_floors_out_of_contention_on_move(role_mod: ModuleType) -> None:
    players = pd.DataFrame([{"id": 452, "web_name": "Bruno G.", "club_id": 1}])
    clubs = pd.DataFrame(
        [
            {"id": 1, "short_name": "ARS", "name": "Arsenal"},
            {"id": 17, "short_name": "NEW", "name": "Newcastle"},
        ]
    )
    df = pd.DataFrame(
        [
            {
                "player_id": 452,
                "web_name": "Bruno G.",
                "club_short": "NEW",
                "club": "Newcastle",
                "expected_role": "Out of Contention",
                "p_start": 0.0,
                "p_sub_in": 0.05,
                "p_dnp": 0.95,
                "mins_if_start": 45,
                "mins_if_sub": 10,
                "draft_availability": "not_role_eligible",
                "availability_reason": "Transferred to Arsenal; vacated Newcastle midfield.",
                "reason": "old",
                "sources": "overlay",
                "confidence": "low",
                "conflict_rule": "",
                "draft_eligible": False,
            }
        ]
    )
    out = role_mod.sync_clubs_from_api(df, players, clubs)
    row = out.iloc[0]
    assert row["club_short"] == "ARS"
    assert row["expected_role"] == "Rotation"
    assert row["availability_reason"] == ""


def test_inject_chelsea_james_does_not_move_trafford(role_mod: ModuleType) -> None:
    players = pd.DataFrame(
        [
            {
                "id": 142,
                "web_name": "James",
                "first_name": "Reece",
                "second_name": "James",
                "club_id": 6,
                "position_id": 2,
            },
            {
                "id": 385,
                "web_name": "Trafford",
                "first_name": "James",
                "second_name": "Trafford",
                "club_id": 13,
                "position_id": 1,
            },
        ]
    )
    clubs = pd.DataFrame(
        [
            {"id": 6, "short_name": "CHE", "name": "Chelsea"},
            {"id": 13, "short_name": "LEE", "name": "Leeds"},
        ]
    )
    df = pd.DataFrame(
        [
            {
                "club": "Leeds",
                "club_short": "LEE",
                "player_id": 385,
                "web_name": "Trafford",
                "position": "GKP",
                "expected_role": "Nailed Starter",
                "p_start": 0.9,
                "p_sub_in": 0.05,
                "p_dnp": 0.05,
                "mins_if_start": 85,
                "mins_if_sub": 20,
                "confidence": "high",
                "conflict_rule": "unanimous_dual_source",
                "draft_eligible": True,
                "reason": "lee",
                "sources": "overlay",
                "draft_availability": "eligible",
            }
        ]
    )
    out = role_mod.inject_missing_ffs_starters(
        df, {"CHE": ["James"]}, {"CHE": ["James"]}, players, clubs
    )
    trafford = out.loc[out["player_id"] == 385].iloc[0]
    assert trafford["club_short"] == "LEE"
    assert (out["player_id"] == 142).any()
    assert out.loc[out["player_id"] == 142, "club_short"].iloc[0] == "CHE"
