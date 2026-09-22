"""Transfer Plan Scenario arms and ranking (ADR 0042)."""

import pytest

from solver.scenarios import (
    ARM_NO_HIT,
    ARM_OPTIMAL,
    annotate_plan_with_egs,
    apply_scenario_arm,
    feasible_scenario_arms,
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


def test_both_arms_always_feasible() -> None:
    assert feasible_scenario_arms(0) == (ARM_OPTIMAL, ARM_NO_HIT)
    assert feasible_scenario_arms(1) == (ARM_OPTIMAL, ARM_NO_HIT)
    assert feasible_scenario_arms(5) == (ARM_OPTIMAL, ARM_NO_HIT)


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
