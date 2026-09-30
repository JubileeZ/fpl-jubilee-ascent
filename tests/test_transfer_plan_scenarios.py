import pandas as pd
import pytest

from solver.scenarios import (
    ARM_CONSERVATIVE,
    ARM_NO_HIT,
    ARM_OPTIMAL,
    annotate_plan_with_egs,
    apply_scenario_arm,
    feasible_scenario_arms,
    find_protected_one_match_missed_starters,
    find_unowned_flagged_players,
    rank_scenarios,
    scenario_arm_overrides,
)
from projections.expected_gw_score import PlayerGw


def test_optimal_allows_live_hits_without_start_pin() -> None:
    overrides = scenario_arm_overrides(ARM_OPTIMAL, start_gw=5, free_transfer_bank=0)
    assert "num_transfers" not in overrides
    assert "no_transfer_gws" not in overrides
    assert overrides["weekly_hit_limit"] == 1
    assert overrides["hit_cost"] == 4.0


def test_no_hit_forbids_hits_for_whole_horizon() -> None:
    overrides = scenario_arm_overrides(ARM_NO_HIT, start_gw=5, free_transfer_bank=2)
    assert "num_transfers" not in overrides
    assert "no_transfer_gws" not in overrides
    assert overrides["weekly_hit_limit"] == 0
    assert overrides["hit_cost"] == 4.0


def test_conservative_forbids_hits_and_applies_bans_locks() -> None:
    overrides = scenario_arm_overrides(ARM_CONSERVATIVE, start_gw=5, free_transfer_bank=2)
    assert "num_transfers" not in overrides
    assert "no_transfer_gws" not in overrides
    assert overrides["weekly_hit_limit"] == 0
    assert overrides["hit_cost"] == 4.0

    base = {"banned_next_gw": [5], "locked_next_gw": [8]}
    applied = apply_scenario_arm(
        base,
        ARM_CONSERVATIVE,
        start_gw=5,
        free_transfer_bank=2,
        banned_next_gw=[10, 11],
        locked_next_gw=[20],
    )
    assert applied["weekly_hit_limit"] == 0
    assert applied["banned_next_gw"] == [5, 10, 11]
    assert applied["locked_next_gw"] == [8, 20]


def test_both_arms_always_feasible() -> None:
    assert feasible_scenario_arms(0) == (ARM_OPTIMAL, ARM_NO_HIT, ARM_CONSERVATIVE)
    assert feasible_scenario_arms(1) == (ARM_OPTIMAL, ARM_NO_HIT, ARM_CONSERVATIVE)
    assert feasible_scenario_arms(5) == (ARM_OPTIMAL, ARM_NO_HIT, ARM_CONSERVATIVE)


def test_apply_scenario_arm_clears_conflicting_pins() -> None:
    base = {"num_transfers": 2, "no_transfer_gws": [9], "weekly_hit_limit": 99, "hit_cost": 8}
    optimal = apply_scenario_arm(base, ARM_OPTIMAL, start_gw=5, free_transfer_bank=2)
    assert "num_transfers" not in optimal
    assert "no_transfer_gws" not in optimal
    assert optimal["weekly_hit_limit"] == 1
    assert optimal["hit_cost"] == 4.0
    no_hit = apply_scenario_arm(base, ARM_NO_HIT, start_gw=5, free_transfer_bank=2)
    assert "num_transfers" not in no_hit
    assert "no_transfer_gws" not in no_hit
    assert no_hit["weekly_hit_limit"] == 0
    assert no_hit["hit_cost"] == 4.0


def test_find_unowned_flagged_players() -> None:
    players_df = pd.DataFrame([
        {"id": 1, "status": "a", "chance_of_playing_next_round": 100},  # unowned, fit
        {"id": 2, "status": "d", "chance_of_playing_next_round": 75},   # unowned, doubtful -> flagged
        {"id": 3, "status": "i", "chance_of_playing_next_round": 0},    # unowned, injured -> flagged
        {"id": 4, "status": "d", "chance_of_playing_next_round": 75},   # owned, doubtful -> ignored
    ])
    flagged = find_unowned_flagged_players(players_df, owned_ids=[4])
    assert flagged == [2, 3]


def test_find_protected_one_match_missed_starters() -> None:
    perf_df = pd.DataFrame([
        # Player 1: started GW1-4, missed GW5 -> protected
        {"player_id": 1, "gameweek_id": 1, "starts": 1, "minutes": 90},
        {"player_id": 1, "gameweek_id": 2, "starts": 1, "minutes": 85},
        {"player_id": 1, "gameweek_id": 3, "starts": 1, "minutes": 90},
        {"player_id": 1, "gameweek_id": 4, "starts": 1, "minutes": 90},
        {"player_id": 1, "gameweek_id": 5, "starts": 0, "minutes": 0},
        # Player 2: bench warmer (0 starts) -> not protected
        {"player_id": 2, "gameweek_id": 1, "starts": 0, "minutes": 10},
        {"player_id": 2, "gameweek_id": 2, "starts": 0, "minutes": 15},
        {"player_id": 2, "gameweek_id": 3, "starts": 0, "minutes": 0},
        # Player 3: played GW5 -> not missed
        {"player_id": 3, "gameweek_id": 4, "starts": 1, "minutes": 90},
        {"player_id": 3, "gameweek_id": 5, "starts": 1, "minutes": 90},
        # Player 4: missed GW4 and GW5 (multi-match absence) -> not protected
        {"player_id": 4, "gameweek_id": 1, "starts": 1, "minutes": 90},
        {"player_id": 4, "gameweek_id": 2, "starts": 1, "minutes": 90},
        {"player_id": 4, "gameweek_id": 3, "starts": 1, "minutes": 90},
        {"player_id": 4, "gameweek_id": 4, "starts": 0, "minutes": 0},
        {"player_id": 4, "gameweek_id": 5, "starts": 0, "minutes": 0},
    ])
    protected = find_protected_one_match_missed_starters(perf_df, owned_ids=[1, 2, 3, 4])
    assert protected == [1]


def test_unknown_arm_raises() -> None:
    with pytest.raises(ValueError, match="unknown"):
        scenario_arm_overrides("roll", start_gw=5, free_transfer_bank=1)


def test_rank_scenarios_uses_horizon_egs_not_solver_objective() -> None:
    ranked = rank_scenarios(
        [
            {
                "id": ARM_NO_HIT,
                "name": "No Hit",
                "horizon_egs": 100.0,
                "solver_objective": 400.0,
            },
            {
                "id": ARM_OPTIMAL,
                "name": "Optimal",
                "horizon_egs": 110.0,
                "solver_objective": 10.0,
            },
        ]
    )
    assert [row["id"] for row in ranked] == [ARM_OPTIMAL, ARM_NO_HIT]
    assert [row["rank"] for row in ranked] == [1, 2]


def test_rank_scenarios_ties_prefer_optimal() -> None:
    ranked = rank_scenarios(
        [
            {"id": ARM_NO_HIT, "name": "No Hit", "horizon_egs": 110.0},
            {"id": ARM_OPTIMAL, "name": "Optimal", "horizon_egs": 110.0},
        ]
    )
    assert [row["id"] for row in ranked] == [ARM_OPTIMAL, ARM_NO_HIT]


def test_annotate_plan_adds_expected_gw_score_and_auto_captain_alternatives() -> None:
    lineup = [1, 10, 11, 12, 13, 20, 21, 22, 23, 30, 31]
    players = {
        (1, 5): PlayerGw(1, 1, xp=2.0, p_appear=1.0),
        **{(pid, 5): PlayerGw(pid, 2, xp=2.0, p_appear=1.0) for pid in (10, 11, 12, 13)},
        **{(pid, 5): PlayerGw(pid, 3, xp=2.0, p_appear=1.0) for pid in (20, 21, 22, 23)},
        (30, 5): PlayerGw(30, 4, xp=9.0, p_appear=1.0),
        (31, 5): PlayerGw(31, 4, xp=2.0, p_appear=1.0),
    }
    plan = {
        "meta": {"solver_objective": 12.0, "next_gw": 5, "horizon": 1},
        "weeks": [
            {
                "gw": 5,
                "lineup_ids": lineup,
                "bench_ids": [],
                "captain_id": 30,
                "vice_id": 31,
                "hits": 1,
                "chip": None,
            }
        ],
    }
    annotated = annotate_plan_with_egs(plan, players, hit_cost=4.0)
    assert annotated["weeks"][0]["expected_gw_score"] == 34.0
    assert annotated["horizon_egs"] == 34.0
    assert annotated["auto_captain"]["auto_captain_id"] == 30
    assert annotated["auto_captain"]["auto_vice_id"] == 1
