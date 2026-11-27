"""Unit tests for modular internal xMins baseline engine."""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from features.internal_xmins import (
    SOFT_DOUBTFUL_CURVES,
    SOFT_SUSPENDED_N_CURVE,
    SOFT_UNKNOWN_CURVE,
    InternalXminsConfig,
    build_frozen_internal_minutes_baseline,
    build_soft_shield_layers,
    build_sparse_gkp_baseline,
    compute_internal_xmins_from_tables,
)


def _sample_tables() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    players = pd.DataFrame([
        # Club 1: 2 GKPs + 4 outfield
        {"id": 1, "web_name": "GK1", "club_id": 1, "position_id": 1, "now_cost": 55, "status": "a", "chance_of_playing_next_round": 100.0, "news": "", "code": 101},
        {"id": 2, "web_name": "GK2", "club_id": 1, "position_id": 1, "now_cost": 40, "status": "a", "chance_of_playing_next_round": 100.0, "news": "", "code": 102},
        {"id": 3, "web_name": "StarterA", "club_id": 1, "position_id": 2, "now_cost": 55, "status": "a", "chance_of_playing_next_round": 100.0, "news": "", "code": 103},
        {"id": 4, "web_name": "BenchSub", "club_id": 1, "position_id": 3, "now_cost": 45, "status": "a", "chance_of_playing_next_round": 100.0, "news": "", "code": 104},
        {"id": 5, "web_name": "InjuredMid", "club_id": 1, "position_id": 3, "now_cost": 70, "status": "i", "chance_of_playing_next_round": 0.0, "news": "Knee injury - Expected back 19 Oct", "code": 105},
        {"id": 6, "web_name": "SuspDef", "club_id": 1, "position_id": 2, "now_cost": 50, "status": "s", "chance_of_playing_next_round": 0.0, "news": "Suspended until 12 Oct", "code": 106},
        {"id": 7, "web_name": "DoubtFwd", "club_id": 1, "position_id": 4, "now_cost": 80, "status": "d", "chance_of_playing_next_round": 50.0, "news": "Knock - 50% chance of playing", "code": 107},
        {"id": 8, "web_name": "InjuredFringe", "club_id": 1, "position_id": 3, "now_cost": 50, "status": "i", "chance_of_playing_next_round": 0.0, "news": "Ankle injury - Expected back 12 Oct", "code": 108},
    ])
    fixtures = pd.DataFrame([
        {"id": 1, "gameweek_id": 1, "home_club_id": 1, "away_club_id": 2, "kickoff_time": "2025-08-16T14:00:00Z"},
        {"id": 2, "gameweek_id": 2, "home_club_id": 1, "away_club_id": 2, "kickoff_time": "2025-08-23T14:00:00Z"},
        {"id": 3, "gameweek_id": 3, "home_club_id": 1, "away_club_id": 2, "kickoff_time": "2025-08-30T14:00:00Z"},
        {"id": 4, "gameweek_id": 4, "home_club_id": 1, "away_club_id": 2, "kickoff_time": "2025-09-13T14:00:00Z"},
        {"id": 5, "gameweek_id": 5, "home_club_id": 1, "away_club_id": 2, "kickoff_time": "2025-09-20T14:00:00Z"},
        {"id": 6, "gameweek_id": 6, "home_club_id": 1, "away_club_id": 2, "kickoff_time": "2025-10-04T14:00:00Z"},
        {"id": 7, "gameweek_id": 7, "home_club_id": 1, "away_club_id": 2, "kickoff_time": "2025-10-12T14:00:00Z"},
        {"id": 8, "gameweek_id": 8, "home_club_id": 1, "away_club_id": 2, "kickoff_time": "2025-10-19T14:00:00Z"},
        {"id": 9, "gameweek_id": 9, "home_club_id": 1, "away_club_id": 2, "kickoff_time": "2025-10-26T14:00:00Z"},
        {"id": 10, "gameweek_id": 10, "home_club_id": 1, "away_club_id": 2, "kickoff_time": "2025-11-02T14:00:00Z"},
    ])
    perf_rows = []
    for gw in range(1, 7):
        # GK1 started 1..6; GK2 0m
        perf_rows.append({"player_id": 1, "fixture_id": gw, "gameweek_id": gw, "minutes": 90, "starts": 1})
        perf_rows.append({"player_id": 2, "fixture_id": gw, "gameweek_id": gw, "minutes": 0, "starts": 0})
        # StarterA started GW1..5 (85m), missed GW6 with 0m
        perf_rows.append({"player_id": 3, "fixture_id": gw, "gameweek_id": gw, "minutes": 85 if gw < 6 else 0, "starts": 1 if gw < 6 else 0})
        # BenchSub started GW1..4, came off bench GW5-6 (15m cameo -> fit benching)
        perf_rows.append({"player_id": 4, "fixture_id": gw, "gameweek_id": gw, "minutes": 80 if gw < 5 else 15, "starts": 1 if gw < 5 else 0})
        # InjuredMid started GW1..4 (80m), injured GW5..6
        perf_rows.append({"player_id": 5, "fixture_id": gw, "gameweek_id": gw, "minutes": 80 if gw < 5 else 0, "starts": 1 if gw < 5 else 0})
        # SuspDef started GW1..5 (88m)
        perf_rows.append({"player_id": 6, "fixture_id": gw, "gameweek_id": gw, "minutes": 88 if gw < 6 else 0, "starts": 1 if gw < 6 else 0})
        # DoubtFwd started GW1..6 (82m)
        perf_rows.append({"player_id": 7, "fixture_id": gw, "gameweek_id": gw, "minutes": 82, "starts": 1})
        # InjuredFringe: 0 starts, 5m cameo GW1
        perf_rows.append({"player_id": 8, "fixture_id": gw, "gameweek_id": gw, "minutes": 5 if gw == 1 else 0, "starts": 0})
    return players, fixtures, pd.DataFrame(perf_rows)


def test_zero_lookahead_leakage() -> None:
    players, fixtures, perfs = _sample_tables()
    native = {(pid, gw): 50.0 for pid in range(1, 9) for gw in range(7, 11)}
    res1 = compute_internal_xmins_from_tables(
        players, fixtures, perfs, 7, 4, native_mins_map=native, reference_date=date(2025, 10, 10)
    )
    future_noise = pd.DataFrame([
        {"player_id": 1, "fixture_id": 7, "gameweek_id": 7, "minutes": 0, "starts": 0},
        {"player_id": 2, "fixture_id": 7, "gameweek_id": 7, "minutes": 90, "starts": 1},
    ])
    res2 = compute_internal_xmins_from_tables(
        players, fixtures, pd.concat([perfs, future_noise], ignore_index=True),
        7, 4, native_mins_map=native, reference_date=date(2025, 10, 10),
    )
    assert res1 == res2


def test_m1_gkp_handover_and_doubtful_split() -> None:
    players, fixtures, perfs = _sample_tables()
    cfg = InternalXminsConfig(enable_gkp_role=True, enable_starter_recovery=False, enable_availability_ramp=True, enable_club_reconciliation=False)
    res = compute_internal_xmins_from_tables(players, fixtures, perfs, 7, 2, reference_date=date(2025, 10, 10), config=cfg)
    assert res[(1, 7)] == pytest.approx(89.0)
    assert res[(2, 7)] == pytest.approx(1.0)

    # Doubtful #1 (50% -> 0.27) splits minutes with #2
    p_doubt = players.copy()
    p_doubt.loc[p_doubt["id"] == 1, ["status", "chance_of_playing_next_round"]] = ["d", 50.0]
    res_d = compute_internal_xmins_from_tables(p_doubt, fixtures, perfs, 7, 1, reference_date=date(2025, 10, 10), config=cfg)
    assert res_d[(1, 7)] == pytest.approx(89.0 * 0.27)
    assert res_d[(2, 7)] > 50.0

    # Two-start available-rival handover promotes GK2
    p_swap = perfs.copy()
    p_swap.loc[(p_swap["player_id"] == 1) & (p_swap["gameweek_id"].isin([5, 6])), ["minutes", "starts"]] = [0, 0]
    p_swap.loc[(p_swap["player_id"] == 2) & (p_swap["gameweek_id"].isin([5, 6])), ["minutes", "starts"]] = [90, 1]
    res_sw = compute_internal_xmins_from_tables(players, fixtures, p_swap, 7, 1, reference_date=date(2025, 10, 10), config=cfg)
    assert res_sw[(2, 7)] == pytest.approx(89.0)
    assert res_sw[(1, 7)] == pytest.approx(1.0)


def test_m2_recovery_excludes_fit_bench_cameo() -> None:
    players, fixtures, perfs = _sample_tables()
    cfg = InternalXminsConfig(enable_gkp_role=False, enable_starter_recovery=True, enable_availability_ramp=False, enable_club_reconciliation=False)
    native = {(3, 7): 12.0, (4, 7): 15.0}
    res = compute_internal_xmins_from_tables(players, fixtures, perfs, 7, 1, native_mins_map=native, config=cfg)
    assert res[(3, 7)] == pytest.approx(85.0 * cfg.recovery_1gw_weight)
    assert res[(4, 7)] == pytest.approx(15.0)


def test_m3_availability_ramps_and_tenure_gate() -> None:
    players, fixtures, perfs = _sample_tables()
    cfg = InternalXminsConfig(enable_gkp_role=False, enable_starter_recovery=False, enable_availability_ramp=True, enable_club_reconciliation=False)
    native = {(pid, gw): 60.0 for pid in range(1, 9) for gw in range(7, 11)}
    native.update({(8, gw): 4.0 for gw in range(7, 11)})
    res = compute_internal_xmins_from_tables(players, fixtures, perfs, 7, 4, native_mins_map=native, reference_date=date(2025, 10, 10), config=cfg)

    # InjuredMid return_gw=8 (19 Oct): 0m GW7 -> 20m GW8 -> 65m GW9 -> 80m GW10
    assert res[(5, 7)] == pytest.approx(0.0)
    assert res[(5, 8)] == pytest.approx(20.0)
    assert res[(5, 9)] == pytest.approx(65.0)
    assert res[(5, 10)] == pytest.approx(80.0)

    # SuspDef return_gw=7 (12 Oct): immediate steady-state restoration
    assert res[(6, 7)] == pytest.approx(86.0)

    # DoubtFwd 50% scales at t=0 (0.27) and decays toward 1.0 over t=1,2
    assert res[(7, 7)] == pytest.approx(60.0 * 0.27)
    assert res[(7, 8)] > res[(7, 7)]

    # InjuredFringe has 0 starts -> post-return t=+2 stays near native 4.0m (not 70-80m)
    assert res[(8, 9)] == pytest.approx(4.0)


def test_m4_reconciliation_dgw_bgw_and_injury_guard() -> None:
    players, fixtures, perfs = _sample_tables()
    # Add Blank GW8 and Double GW9 for club 1
    fixtures_dgw = fixtures[fixtures["gameweek_id"] != 8].copy()
    fixtures_dgw = pd.concat([
        fixtures_dgw,
        pd.DataFrame([{"id": 99, "gameweek_id": 9, "home_club_id": 1, "away_club_id": 3, "kickoff_time": "2025-10-28T19:45:00Z"}]),
    ], ignore_index=True)
    # Give club 1 10 healthy starters + InjuredMid
    extra = [
        {"id": 100 + i, "web_name": f"Out{i}", "club_id": 1, "position_id": 2 if i < 4 else 3, "now_cost": 50, "status": "a", "chance_of_playing_next_round": 100.0, "news": "", "code": 200 + i}
        for i in range(8)
    ]
    p_all = pd.concat([players, pd.DataFrame(extra)], ignore_index=True)
    native = {(pid, gw): 65.0 for pid in p_all["id"] for gw in (7, 8, 9)}
    native.update({(5, gw): 0.0 for gw in (7, 8, 9)})
    cfg = InternalXminsConfig(enable_club_reconciliation=True)
    res = compute_internal_xmins_from_tables(
        p_all, fixtures_dgw, perfs, 7, 3, native_mins_map=native, reference_date=date(2025, 10, 10), config=cfg
    )
    assert res[(5, 7)] == 0.0  # Injured stays 0.0
    assert res[(3, 8)] == 0.0  # BGW8 is 0.0
    assert res[(3, 9)] > 120.0  # DGW9 sums two fixtures


def test_build_soft_shield_layers_all_statuses() -> None:
    players, fixtures, perfs = _sample_tables()
    extra = pd.DataFrame([
        {"id": 9, "web_name": "LeftClub", "club_id": 1, "position_id": 3, "now_cost": 55, "status": "u", "chance_of_playing_next_round": 0.0, "news": "Transferred", "code": 109},
        {"id": 10, "web_name": "LoanParent", "club_id": 1, "position_id": 2, "now_cost": 45, "status": "n", "chance_of_playing_next_round": 0.0, "news": "Ineligible to face parent club", "code": 110},
        {"id": 11, "web_name": "IneligOther", "club_id": 1, "position_id": 3, "now_cost": 50, "status": "n", "chance_of_playing_next_round": 0.0, "news": "Not available", "code": 111},
        {"id": 12, "web_name": "UnknownInj", "club_id": 1, "position_id": 3, "now_cost": 75, "status": "i", "chance_of_playing_next_round": 0.0, "news": "Knee injury - Unknown return date", "code": 112},
        {"id": 13, "web_name": "Doubt75", "club_id": 1, "position_id": 4, "now_cost": 70, "status": "d", "chance_of_playing_next_round": 75.0, "news": "Knock - 75% chance of playing", "code": 113},
    ])
    p_all = pd.concat([players, extra], ignore_index=True)
    # Give UnknownInj, LoanParent, IneligOther, Doubt75 native minutes of 80m
    native = {(pid, gw): 80.0 for pid in p_all["id"] for gw in range(7, 13)}
    native[(8, 7)] = native[(8, 8)] = native[(8, 9)] = native[(8, 10)] = 4.0

    # Extend fixtures through GW12 so t=0..5 exist
    more_fix = pd.DataFrame([
        {"id": 11, "gameweek_id": 11, "home_club_id": 1, "away_club_id": 2, "kickoff_time": "2025-11-09T14:00:00Z"},
        {"id": 12, "gameweek_id": 12, "home_club_id": 1, "away_club_id": 2, "kickoff_time": "2025-11-22T14:00:00Z"},
    ])
    fix_all = pd.concat([fixtures, more_fix], ignore_index=True)

    hard_guard, soft_curve, post_fallback = build_soft_shield_layers(
        p_all, fix_all, perfs, target_gw=7, horizon=6, native_mins_map=native, reference_date=date(2025, 10, 10)
    )

    # Healthy outfielder (3) absent from all 3 dicts
    for gw in range(7, 13):
        assert (3, gw) not in hard_guard
        assert (3, gw) not in soft_curve
        assert (3, gw) not in post_fallback

    # status='u' (9): 0.0 in hard_guard across entire horizon
    for gw in range(7, 13):
        assert hard_guard[(9, gw)] == 0.0

    # status='n' parent club (10): 0.0 in hard_guard at t=0 (GW7) only, omitted at t>=1
    assert hard_guard[(10, 7)] == 0.0
    for gw in range(8, 13):
        assert (10, gw) not in hard_guard
        assert (10, gw) not in soft_curve

    # status='n' non-parent-club (11): 0.0 in hard_guard at t=0, SOFT_SUSPENDED_N_CURVE at t=1..4 in soft_curve
    assert hard_guard[(11, 7)] == 0.0
    for step in range(1, 5):
        assert soft_curve[(11, 7 + step)] == pytest.approx(80.0 * SOFT_SUSPENDED_N_CURVE[step])
    assert (11, 12) not in soft_curve  # step 5 multiplier == 1.00 -> omitted

    # Unknown return date (12): 0.0 at t=0 in hard_guard, SOFT_UNKNOWN_CURVE at t=1..5 in soft_curve
    assert hard_guard[(12, 7)] == 0.0
    for step in range(1, 6):
        assert soft_curve[(12, 7 + step)] == pytest.approx(80.0 * SOFT_UNKNOWN_CURVE[step])

    # Known return_gw=8 Injury (5): 0.0 pre-return, 20m return, 65m return+1, baseline fallback return+2
    assert hard_guard[(5, 7)] == 0.0
    assert hard_guard[(5, 8)] == pytest.approx(20.0)
    assert hard_guard[(5, 9)] == pytest.approx(65.0)
    assert post_fallback[(5, 10)] >= 60.0

    # Suspension returning GW7 (6): baseline in post_fallback on GW7+
    assert post_fallback[(6, 7)] >= 60.0
    assert (6, 7) not in hard_guard

    # Doubtful 75% (13): SOFT_DOUBTFUL_CURVES[75] for steps with mult < 0.99, omitted at t>=3 (mult == 1.00)
    d75 = dict(SOFT_DOUBTFUL_CURVES)[75]
    assert soft_curve[(13, 7)] == pytest.approx(80.0 * d75[0])
    assert soft_curve[(13, 8)] == pytest.approx(80.0 * d75[1])
    assert soft_curve[(13, 9)] == pytest.approx(80.0 * d75[2])
    assert (13, 10) not in soft_curve


def test_build_sparse_gkp_baseline_and_zero_leakage() -> None:
    players, fixtures, perfs = _sample_tables()
    # Outfielders strictly excluded
    gk_only = build_sparse_gkp_baseline(players, fixtures, perfs, 7, 3)
    assert all(pid in {1, 2} for (pid, _gw) in gk_only)
    assert gk_only[(1, 7)] == pytest.approx(89.0)
    assert gk_only[(2, 7)] == pytest.approx(1.0)

    # Injured #1 (0.0 in soft_overrides) shifts 89.0 to #2
    gk_inj = build_sparse_gkp_baseline(players, fixtures, perfs, 7, 2, soft_overrides={(1, 7): 0.0})
    assert gk_inj[(1, 7)] == 0.0
    assert gk_inj[(2, 7)] == pytest.approx(89.0)

    # Doubtful #1 (0.32 * 89) shifts remaining to #2 cleanly
    gk_doubt = build_sparse_gkp_baseline(players, fixtures, perfs, 7, 1, soft_overrides={(1, 7): 89.0 * 0.32})
    assert gk_doubt[(1, 7)] == pytest.approx(89.0 * 0.32)
    assert gk_doubt[(2, 7)] == pytest.approx(90.0 - 89.0 * 0.32)

    # Double GW scales by n_fix and Blank GW gets 0.0 (or omitted cleanly)
    fix_dgw_bgw = fixtures[fixtures["gameweek_id"] != 8].copy()
    fix_dgw_bgw = pd.concat([
        fix_dgw_bgw,
        pd.DataFrame([{"id": 99, "gameweek_id": 9, "home_club_id": 1, "away_club_id": 3, "kickoff_time": "2025-10-28T19:45:00Z"}]),
    ], ignore_index=True)
    gk_dgw = build_sparse_gkp_baseline(players, fix_dgw_bgw, perfs, 7, 3)
    assert gk_dgw.get((1, 8), 0.0) == 0.0
    assert gk_dgw[(1, 9)] == pytest.approx(178.0)

    # Strict zero lookahead leakage on frozen combined baseline
    native = {(pid, gw): 60.0 for pid in players["id"] for gw in range(7, 11)}
    r1 = build_frozen_internal_minutes_baseline(
        players, fixtures, perfs, 7, 4, native_mins_map=native, reference_date=date(2025, 10, 10)
    )
    future_noise = pd.DataFrame([
        {"player_id": 1, "fixture_id": 7, "gameweek_id": 7, "minutes": 0, "starts": 0},
        {"player_id": 2, "fixture_id": 7, "gameweek_id": 7, "minutes": 90, "starts": 1},
    ])
    r2 = build_frozen_internal_minutes_baseline(
        players, fixtures, pd.concat([perfs, future_noise], ignore_index=True),
        7, 4, native_mins_map=native, reference_date=date(2025, 10, 10),
    )
    assert r1 == r2
    # Healthy outfielder (3) stays absent so Native Champion states stay untouched
    assert (3, 7) not in r1


def test_empty_columnless_fixtures_and_perfs_handled_safely() -> None:
    players, _, _ = _sample_tables()
    empty = pd.DataFrame()
    h, s, p = build_soft_shield_layers(players, empty, empty, 7, 2, reference_date=date(2025, 10, 10))
    assert h == {} and s == {} and p == {}
    assert build_sparse_gkp_baseline(players, empty, empty, 7, 2) == {}
    assert compute_internal_xmins_from_tables(players, empty, empty, 7, 2, reference_date=date(2025, 10, 10)) == {}
