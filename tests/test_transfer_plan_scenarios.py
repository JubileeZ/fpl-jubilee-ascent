import pandas as pd
import pytest

from pathlib import Path
from solver.scenarios import (
    ARM_NO_HIT,
    ARM_STRATEGIC,
    ARM_UNCONSTRAINED,
    DEFAULT_STRATEGIC_OPTIONS,
    annotate_plan_with_egs,
    apply_scenario_arm,
    compute_scenarios_digest,
    feasible_scenario_arms,
    rank_scenarios,
    scenario_arm_overrides,
)
from projections.expected_gw_score import PlayerGw


def test_unconstrained_allows_live_hits_without_start_pin() -> None:
    overrides = scenario_arm_overrides(ARM_UNCONSTRAINED, start_gw=5, free_transfer_bank=0)
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


def test_strategic_applies_variance_defaults_and_hit_hurdle() -> None:
    overrides = scenario_arm_overrides(ARM_STRATEGIC, start_gw=5, free_transfer_bank=2)
    assert "num_transfers" not in overrides
    assert "no_transfer_gws" not in overrides
    assert overrides["weekly_hit_limit"] == 1
    assert overrides["hit_cost"] == 4.0
    assert overrides["strategic_options"] == DEFAULT_STRATEGIC_OPTIONS

    base = {"weekly_hit_limit": 0}
    applied = apply_scenario_arm(
        base,
        ARM_STRATEGIC,
        start_gw=5,
        free_transfer_bank=2,
        strategic_options={"hit_friction": 3.0},
    )
    assert applied["weekly_hit_limit"] == 1
    assert applied["strategic_options"]["hit_friction"] == 3.0
    assert applied["strategic_options"]["starter_xmins_floor"] == 65.0


def test_both_arms_always_feasible() -> None:
    assert feasible_scenario_arms(0) == (ARM_STRATEGIC, ARM_UNCONSTRAINED, ARM_NO_HIT)
    assert feasible_scenario_arms(1) == (ARM_STRATEGIC, ARM_UNCONSTRAINED, ARM_NO_HIT)
    assert feasible_scenario_arms(5) == (ARM_STRATEGIC, ARM_UNCONSTRAINED, ARM_NO_HIT)


def test_apply_scenario_arm_clears_conflicting_pins() -> None:
    base = {"num_transfers": 2, "no_transfer_gws": [9], "weekly_hit_limit": 99, "hit_cost": 8}
    unconstrained = apply_scenario_arm(base, ARM_UNCONSTRAINED, start_gw=5, free_transfer_bank=2)
    assert "num_transfers" not in unconstrained
    assert "no_transfer_gws" not in unconstrained
    assert unconstrained["weekly_hit_limit"] == 1
    assert unconstrained["hit_cost"] == 4.0
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
                "id": ARM_STRATEGIC,
                "name": "Strategic",
                "horizon_egs": 110.0,
                "solver_objective": 10.0,
            },
        ]
    )
    assert [row["id"] for row in ranked] == [ARM_STRATEGIC, ARM_NO_HIT]
    assert [row["rank"] for row in ranked] == [1, 2]


def test_rank_scenarios_ties_prefer_strategic() -> None:
    ranked = rank_scenarios(
        [
            {"id": ARM_NO_HIT, "name": "No Hit", "horizon_egs": 110.0},
            {"id": ARM_STRATEGIC, "name": "Strategic", "horizon_egs": 110.0},
        ]
    )
    assert [row["id"] for row in ranked] == [ARM_STRATEGIC, ARM_NO_HIT]


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


def test_compute_scenarios_digest_sensitivity(tmp_path: Path) -> None:
    p_dir = tmp_path / "processed"
    p_dir.mkdir()
    (p_dir / "players.parquet").write_bytes(b"players_v1")
    (p_dir / "user_picks.parquet").write_bytes(b"picks_v1")
    (p_dir / "user_state.parquet").write_bytes(b"state_v1")

    d1 = compute_scenarios_digest(
        processed_dir=p_dir,
        target_gw=5,
        horizon=6,
        champion="linear_baseline",
        booked_chips={"use_wc": [6]},
        gap=0.0,
    )
    # Same inputs -> identical digest
    d2 = compute_scenarios_digest(
        processed_dir=p_dir,
        target_gw=5,
        horizon=6,
        champion="linear_baseline",
        booked_chips={"use_wc": [6]},
        gap=0.0,
    )
    assert d1 == d2

    # Change parquet file -> changed digest
    (p_dir / "user_picks.parquet").write_bytes(b"picks_v2")
    d3 = compute_scenarios_digest(
        processed_dir=p_dir,
        target_gw=5,
        horizon=6,
        champion="linear_baseline",
        booked_chips={"use_wc": [6]},
        gap=0.0,
    )
    assert d1 != d3

    # Change gap -> changed digest
    d4 = compute_scenarios_digest(
        processed_dir=p_dir,
        target_gw=5,
        horizon=6,
        champion="linear_baseline",
        booked_chips={"use_wc": [6]},
        gap=0.01,
    )
    assert d3 != d4


def test_execute_transfer_plan_scenarios_reuses_cache(tmp_path: Path) -> None:
    from commands.transfer_plan_scenarios import execute_transfer_plan_scenarios
    p_dir = tmp_path / "processed"
    p_dir.mkdir()
    pd.DataFrame([{"id": 10, "status": "a"}]).to_parquet(p_dir / "players.parquet")
    pd.DataFrame([{"player_id": 10, "is_captain": True, "lineup_index": 11}]).to_parquet(p_dir / "user_picks.parquet")
    pd.DataFrame([{"free_transfers": 1, "bank": 0.0}]).to_parquet(p_dir / "user_state.parquet")

    scenarios_json = tmp_path / "scenarios.json"
    solution_json = tmp_path / "solution.json"

    call_count = 0

    def fake_solve(_options: dict, **_kwargs: object) -> dict:
        nonlocal call_count
        call_count += 1
        return {
            "meta": {"next_gw": 5, "horizon": 1},
            "weeks": [{"gw": 5, "lineup_ids": [10], "bench_ids": [], "hits": 0}],
        }

    # First call: runs solver (3 arms)
    res1 = execute_transfer_plan_scenarios(
        processed_dir=p_dir,
        target_gw=5,
        horizon=1,
        dataset={"players": [{"id": 10, "pos": "F", "projections": {"gw5": {"total_xp": 5.0, "xmins": 90.0}}}]},
        execute_plan=fake_solve,
        scenarios_path=scenarios_json,
        solution_path=solution_json,
    )
    assert call_count == 3
    assert res1["meta"]["status"] == "ok"
    assert res1["meta"]["data_digest"] is not None

    # Second call without changes: reuses cache without calling execute_plan!
    res2 = execute_transfer_plan_scenarios(
        processed_dir=p_dir,
        target_gw=5,
        horizon=1,
        dataset={"players": [{"id": 10, "pos": "F", "projections": {"gw5": {"total_xp": 5.0, "xmins": 90.0}}}]},
        execute_plan=fake_solve,
        scenarios_path=scenarios_json,
        solution_path=solution_json,
    )
    assert call_count == 3  # unchanged!
    assert res2["meta"]["data_digest"] == res1["meta"]["data_digest"]

    # Third call with force=True: re-runs solver
    execute_transfer_plan_scenarios(
        processed_dir=p_dir,
        target_gw=5,
        horizon=1,
        dataset={"players": [{"id": 10, "pos": "F", "projections": {"gw5": {"total_xp": 5.0, "xmins": 90.0}}}]},
        execute_plan=fake_solve,
        scenarios_path=scenarios_json,
        solution_path=solution_json,
        force=True,
    )
    assert call_count == 6
