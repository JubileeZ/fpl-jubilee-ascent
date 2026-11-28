"""Tests for pure point-in-time history M1 GKP solo prototype."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import ModuleType

import numpy as np
import pandas as pd

from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel

ROOT = Path(__file__).resolve().parents[1]
PROTOTYPE_PATH = ROOT / "docs/research/candidate-ideation/prototypes/m1_gkp_solo/prototypes.py"
SMOKE_PATH = ROOT / ".agents/skills/explore-candidate/smoke.py"


def _load_module(path: Path, name: str) -> ModuleType:
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _make_feature_row(
    player_id: int,
    club_id: int,
    position_id: int,
    gameweek_id: int,
    fixture_id: int,
    *,
    now_cost: float = 45.0,
    n_starts_historical: float = 0.0,
    p_start: float = 0.5,
    p_sub_in: float = 0.0,
    p_dnp: float = 0.5,
    xmins_if_start: float = 89.0,
    chance_of_playing: float = 100.0,
    is_immediate_next_gw: bool = False,
    has_availability_snapshot: bool = True,
) -> dict[str, object]:
    return {
        "player_id": player_id,
        "club_id": club_id,
        "position_id": position_id,
        "gameweek_id": gameweek_id,
        "fixture_id": fixture_id,
        "opponent_id": 99,
        "is_home": True,
        "difficulty": 3.0,
        "attack_multiplier": 1.0,
        "defence_multiplier": 1.0,
        "now_cost": now_cost,
        "n_starts_historical": n_starts_historical,
        "p_start": p_start,
        "p_sub_in": p_sub_in,
        "p_dnp": p_dnp,
        "p_start_prior": p_start,
        "p_sub_in_prior": p_sub_in,
        "p_dnp_prior": p_dnp,
        "xmins_if_start": xmins_if_start,
        "xmins_if_sub_in": 18.0,
        "p_60_if_start": 1.0,
        "p_60_if_sub_in": 0.0,
        "appearance_probability": p_start + p_sub_in,
        "avg_mins_3gw": xmins_if_start * p_start,
        "per90_xg": 0.25 if position_id >= 3 else 0.01,
        "per90_xa": 0.15 if position_id >= 3 else 0.01,
        "per90_goals": 0.20 if position_id >= 3 else 0.0,
        "per90_assists": 0.10 if position_id >= 3 else 0.0,
        "per90_clean_sheets": 0.35 if position_id <= 2 else 0.25,
        "per90_goals_conceded": 1.1,
        "per90_saves": 3.2 if position_id == 1 else 0.0,
        "per90_bonus": 0.2,
        "per90_defensive_contribution": 6.0 if position_id == 2 else 0.0,
        "per90_yellow_cards": 0.05,
        "per90_red_cards": 0.002,
        "per90_own_goals": 0.002,
        "per90_penalties_saved": 0.02 if position_id == 1 else 0.0,
        "per90_penalties_missed": 0.0,
        "per90_threat": 15.0 if position_id >= 3 else 1.0,
        "per90_creativity": 15.0 if position_id >= 3 else 1.0,
        "penalties_order": 0.0,
        "chance_of_playing": chance_of_playing,
        "status": "a",
        "is_immediate_next_gw": is_immediate_next_gw,
        "has_availability_snapshot": has_availability_snapshot,
        "native_rules_version": "2025-26",
    }


def _make_history(club1_starters_by_gw: list[tuple[int, int, int]]) -> pd.DataFrame:
    """Build two-sided club match history rows; each tuple = (gw, fixture_id, club1_gkp_starter_id)."""
    rows: list[dict[str, object]] = []
    for gw, fid, gk_pid in club1_starters_by_gw:
        for pid in (1, 2, 3):
            st = 1 if pid == gk_pid else 0
            mins = 90.0 if st == 1 else 0.0
            rows.append(
                {
                    "player_id": pid,
                    "fixture_id": fid,
                    "gameweek_id": gw,
                    "opponent_club_id": 20,
                    "was_home": True,
                    "minutes": mins,
                    "starts": st,
                    "goals_scored": 0,
                    "assists": 0,
                    "expected_goals": 0.0,
                    "expected_assists": 0.0,
                    "creativity": 0.0,
                }
            )
        rows.append(
            {
                "player_id": 901,
                "fixture_id": fid,
                "gameweek_id": gw,
                "opponent_club_id": 1,
                "was_home": False,
                "minutes": 90.0,
                "starts": 1,
                "goals_scored": 0,
                "assists": 0,
                "expected_goals": 0.0,
                "expected_assists": 0.0,
                "creativity": 0.0,
            }
        )
    return pd.DataFrame(rows)


def test_smoke_audit_only_passes() -> None:
    smoke = _load_module(SMOKE_PATH, "explore_candidate_smoke_test")
    proto = smoke.load_prototypes(PROTOTYPE_PATH)
    assert smoke.audit(PROTOTYPE_PATH, proto) == []


def test_causal_isolation_ignores_target_and_future_history() -> None:
    proto = _load_module(PROTOTYPE_PATH, "m1_gkp_solo_causal")
    cls = proto.PROTOTYPES["m1_gkp_solo"]

    past_hist = _make_history([(1, 101, 1), (2, 102, 1), (3, 103, 1)])
    leaky_hist = pd.concat(
        [
            past_hist,
            _make_history([(4, 104, 2), (5, 105, 2)]),
        ],
        ignore_index=True,
    )
    feat = pd.DataFrame(
        [
            _make_feature_row(1, 1, 1, 4, 104, now_cost=55.0, n_starts_historical=3.0),
            _make_feature_row(2, 1, 1, 4, 104, now_cost=45.0, n_starts_historical=0.0),
            _make_feature_row(3, 1, 1, 4, 104, now_cost=40.0, n_starts_historical=0.0),
        ]
    )

    t1 = proto._compute_pure_history_gkp_targets(
        feat, past_hist, 4, clear_starter_mins=89.0, backup_mins=1.0, handover_starts=2
    )
    t2 = proto._compute_pure_history_gkp_targets(
        feat, leaky_hist, 4, clear_starter_mins=89.0, backup_mins=1.0, handover_starts=2
    )
    assert t1 == t2 == {1: 89.0, 2: 1.0, 3: 0.0}

    m1 = cls()
    m1.fit(past_hist)
    p1 = m1.predict(feat, horizon=1)

    m2 = cls()
    m2.fit(leaky_hist)
    p2 = m2.predict(feat, horizon=1)

    assert np.allclose(p1["projected_minutes"], p2["projected_minutes"], atol=1e-6)
    assert np.isclose(p2.set_index("player_id").loc[1, "projected_minutes"], 89.0, atol=1e-6)


def test_outfielders_match_champion_and_discrete_gkp_allocation() -> None:
    proto = _load_module(PROTOTYPE_PATH, "m1_gkp_solo_inv")
    cls = proto.PROTOTYPES["m1_gkp_solo"]

    hist = _make_history([(1, 101, 1), (2, 102, 1)])
    feat = pd.DataFrame(
        [
            _make_feature_row(1, 1, 1, 3, 103, now_cost=55.0, n_starts_historical=2.0, p_start=0.80, p_dnp=0.20),
            _make_feature_row(2, 1, 1, 3, 103, now_cost=45.0, n_starts_historical=0.0, p_start=0.40, p_dnp=0.60),
            _make_feature_row(3, 1, 1, 3, 103, now_cost=40.0, n_starts_historical=0.0, p_start=0.20, p_dnp=0.80),
            _make_feature_row(10, 1, 2, 3, 103, now_cost=50.0, n_starts_historical=2.0, p_start=0.85, p_dnp=0.15),
            _make_feature_row(11, 1, 3, 3, 103, now_cost=75.0, n_starts_historical=2.0, p_start=0.90, p_dnp=0.10),
            _make_feature_row(12, 1, 4, 3, 103, now_cost=90.0, n_starts_historical=2.0, p_start=0.92, p_dnp=0.08),
            # Blank fixture row
            _make_feature_row(1, 1, 1, 4, -1, now_cost=55.0, n_starts_historical=2.0, p_start=0.80, p_dnp=0.20),
            # Double fixture rows in GW5
            _make_feature_row(1, 1, 1, 5, 105, now_cost=55.0, n_starts_historical=2.0, p_start=0.80, p_dnp=0.20),
            _make_feature_row(1, 1, 1, 5, 106, now_cost=55.0, n_starts_historical=2.0, p_start=0.80, p_dnp=0.20),
        ]
    )

    cand = cls()
    champ = DefXgShrinkChallengerModel()
    cand.fit(hist)
    champ.fit(hist)
    c_pred = cand.predict(feat, horizon=3)
    ch_pred = champ.predict(feat, horizon=3)

    # Outfielders completely invariant on minutes, states, and all non-bonus scoring components
    invariant_cols = [
        col for col in c_pred.columns if col not in {"xp_bonus", "projected_points"}
    ]
    c_out = c_pred[c_pred["player_id"].isin([10, 11, 12])][invariant_cols].reset_index(drop=True)
    ch_out = ch_pred[ch_pred["player_id"].isin([10, 11, 12])][invariant_cols].reset_index(drop=True)
    pd.testing.assert_frame_equal(c_out, ch_out)

    # Discrete GKP allocation: 89 / 1 / 0
    gw3 = c_pred[c_pred["gameweek_id"] == 3].set_index("player_id")
    assert np.isclose(gw3.loc[1, "projected_minutes"], 89.0, atol=1e-6)
    assert np.isclose(gw3.loc[2, "projected_minutes"], 1.0, atol=1e-6)
    assert np.isclose(gw3.loc[3, "projected_minutes"], 0.0, atol=1e-6)

    for pid in (1, 2, 3):
        p_sum = gw3.loc[pid, "p_dnp"] + gw3.loc[pid, "p_start"] + gw3.loc[pid, "p_sub_in"]
        assert np.isclose(p_sum, 1.0, atol=1e-9)
        assert 0.0 <= gw3.loc[pid, "p_60_if_start"] <= 1.0

    # BGW emits 0.0 mins and 0.0 pts
    bgw = c_pred[(c_pred["player_id"] == 1) & (c_pred["fixture_id"] == -1)].iloc[0]
    assert bgw["projected_minutes"] == 0.0
    assert bgw["projected_points"] == 0.0

    # DGW assigns 89m per fixture
    dgw = c_pred[(c_pred["player_id"] == 1) & (c_pred["gameweek_id"] == 5)]
    assert len(dgw) == 2
    assert np.allclose(dgw["projected_minutes"], 89.0, atol=1e-6)


def test_one_game_retention_and_two_start_handover() -> None:
    proto = _load_module(PROTOTYPE_PATH, "m1_gkp_solo_handover")
    cls = proto.PROTOTYPES["m1_gkp_solo"]

    # After 3 starts by pid=1 and 1 start by pid=2 (last1_missed=1): pid=1 stays #1 (89m).
    hist_1missed = _make_history([(1, 101, 1), (2, 102, 1), (3, 103, 1), (4, 104, 2)])
    feat_gw5 = pd.DataFrame(
        [
            _make_feature_row(1, 1, 1, 5, 105, now_cost=55.0, n_starts_historical=3.0),
            _make_feature_row(2, 1, 1, 5, 105, now_cost=45.0, n_starts_historical=1.0),
        ]
    )
    m_ret = cls()
    m_ret.fit(hist_1missed)
    p_ret = m_ret.predict(feat_gw5, horizon=1).set_index("player_id")
    assert np.isclose(p_ret.loc[1, "projected_minutes"], 89.0, atol=1e-6)
    assert np.isclose(p_ret.loc[2, "projected_minutes"], 1.0, atol=1e-6)

    # After pid=2 starts 2 consecutive matches (GW4, GW5): pid=2 takes over #1 (89m) cleanly.
    hist_handover = _make_history([(1, 101, 1), (2, 102, 1), (3, 103, 1), (4, 104, 2), (5, 105, 2)])
    feat_gw6 = pd.DataFrame(
        [
            _make_feature_row(1, 1, 1, 6, 106, now_cost=55.0, n_starts_historical=3.0),
            _make_feature_row(2, 1, 1, 6, 106, now_cost=45.0, n_starts_historical=2.0),
        ]
    )
    m_ho = cls()
    m_ho.fit(hist_handover)
    p_ho = m_ho.predict(feat_gw6, horizon=1).set_index("player_id")
    assert np.isclose(p_ho.loc[2, "projected_minutes"], 89.0, atol=1e-6)
    assert np.isclose(p_ho.loc[1, "projected_minutes"], 1.0, atol=1e-6)


def test_gw1_cold_start_and_hard_dnp_and_oracle_composition() -> None:
    proto = _load_module(PROTOTYPE_PATH, "m1_gkp_solo_gw1")
    cls = proto.PROTOTYPES["m1_gkp_solo"]

    empty_hist = _make_history([])
    feat_gw1 = pd.DataFrame(
        [
            _make_feature_row(1, 1, 1, 1, 101, now_cost=55.0, n_starts_historical=38.0),
            _make_feature_row(2, 1, 1, 1, 101, now_cost=45.0, n_starts_historical=31.0),
            _make_feature_row(3, 1, 1, 1, 101, now_cost=40.0, n_starts_historical=0.0),
        ]
    )
    m = cls()
    m.fit(empty_hist)
    p_gw1 = m.predict(feat_gw1, horizon=1).set_index("player_id")
    assert np.isclose(p_gw1.loc[1, "projected_minutes"], 89.0, atol=1e-6)
    assert np.isclose(p_gw1.loc[2, "projected_minutes"], 1.0, atol=1e-6)
    assert np.isclose(p_gw1.loc[3, "projected_minutes"], 0.0, atol=1e-6)

    # ADR 0010 hard DNP at immediate next GW zeroes #1 GKP without M1 fighting availability
    feat_dnp = feat_gw1.copy()
    feat_dnp.loc[feat_dnp["player_id"] == 1, "is_immediate_next_gw"] = True
    feat_dnp.loc[feat_dnp["player_id"] == 1, "chance_of_playing"] = 0.0
    p_dnp = m.predict(feat_dnp, horizon=1).set_index("player_id")
    assert np.isclose(p_dnp.loc[1, "projected_minutes"], 0.0, atol=1e-6)

    # Oracle Participation State columns bypass Layer 1 cleanly
    feat_oracle = feat_gw1.copy()
    feat_oracle["oracle_p_start"] = [0.0, 1.0, 0.0]
    feat_oracle["oracle_p_sub_in"] = [0.0, 0.0, 1.0]
    feat_oracle["oracle_p_dnp"] = [1.0, 0.0, 0.0]
    feat_oracle["oracle_minutes"] = [0.0, 90.0, 12.0]
    feat_oracle["oracle_p_60"] = [0.0, 1.0, 0.0]
    p_or = m.predict(feat_oracle, horizon=1).set_index("player_id")
    assert np.allclose(p_or["projected_minutes"], [0.0, 90.0, 12.0], atol=1e-6)
