import pandas as pd
import pytest
from pathlib import Path
from typing import Any
from unittest.mock import patch

from commands.solve import build_my_data_from_parent_state, main
from dashboard.planner import Planner
from dashboard.planner_service import PlannerPaths, solver_options
from solver.scenarios import (
    ARM_STRATEGIC,
    DEFAULT_STRATEGIC_OPTIONS,
    apply_scenario_arm,
)
from solver.solver import prep_data, solve_multi_period_fpl
from solver.transfer_plan import format_strategic_audit_lines, serialize_transfer_plan
from test_streamlit_planner import dataset


def test_format_strategic_audit_lines_clean_and_slacked() -> None:
    # 1. Clean audit (no slacks, passes all constraints)
    clean_audit = {
        "enabled": True,
        "parameters": {
            "hit_friction": 1.8,
            "effective_hit_cost": 5.8,
            "starter_xmins_floor": 65.0,
            "starter_xmins_penalty": 10.0,
            "bench_cover_min": 12,
            "bench_cover_xmins": 65.0,
            "bench_cover_penalty": 1.5,
            "def_stack_cap": 2,
            "def_stack_penalty": 1.2,
            "gk_transfer_friction": 1.5,
        },
        "total_hits": 0,
        "total_slack_penalty": 0.0,
        "sub_floor_starters": [],
        "bench_cover_shortfalls": [],
        "def_stack_breaches": [],
        "gk_transfers_penalized": [],
    }
    lines = format_strategic_audit_lines(clean_audit)
    assert any("STRATEGIC VARIANCE AUDIT" in line for line in lines)
    assert any("Starter xMins Floor: Passed" in line for line in lines)
    assert any("Net Strategic Variance Slack Penalties: 0.00 pts" in line for line in lines)

    # 2. Slacked audit (slacks incurred)
    slacked_audit = {
        "enabled": True,
        "parameters": {
            "hit_friction": 1.8,
            "effective_hit_cost": 5.8,
            "starter_xmins_floor": 65.0,
            "starter_xmins_penalty": 10.0,
            "bench_cover_min": 12,
            "bench_cover_xmins": 65.0,
            "bench_cover_penalty": 1.5,
            "def_stack_cap": 2,
            "def_stack_penalty": 1.2,
            "gk_transfer_friction": 1.5,
        },
        "total_hits": 1,
        "total_slack_penalty": 12.7,
        "sub_floor_starters": [{"gw": 6, "name": "Player 7", "xmins": 45.0}],
        "bench_cover_shortfalls": [{"gw": 6, "nailed_count": 11, "target": 12}],
        "def_stack_breaches": [{"gw": 6, "club": "Club 1", "count": 3, "cap": 2}],
        "gk_transfers_penalized": [{"gw": 6, "name": "GK 1"}],
    }
    slacked_lines = format_strategic_audit_lines(slacked_audit)
    joined = "\n".join(slacked_lines)
    assert "Net Strategic Variance Slack Penalties: 12.70 pts" in joined
    assert "GW6 Player 7 (45m)" in joined
    assert "GW6 (11/12)" in joined
    assert "GW6 Club 1 (3>2)" in joined
    assert "GW6 GK 1" in joined


def test_real_milp_strategic_audit_generated(tmp_path: Path) -> None:
    data = dataset()
    planner = Planner(data)
    planner.change_horizon(6, 6)
    processed = tmp_path / "processed"
    processed.mkdir()
    players = [{"id": row["id"], "position_id": row["pos_id"], "now_cost": 50} for row in data["players"]]
    pd.DataFrame(players).to_parquet(processed / "players.parquet")
    paths = PlannerPaths(tmp_path / "dataset.json", processed, tmp_path / "storage")
    options = solver_options(planner, paths)

    projection_path = tmp_path / "projections.csv"
    pd.DataFrame([
        {
            "ID": row["id"],
            "Name": row["name"],
            "Pos": row["pos"],
            "Price": row["price"],
            "Team": f"Club{row['team_id']}",
            "6_Pts": row["projections"]["gw6"]["total_xp"],
            "6_xMins": 90.0,
        }
        for row in data["players"]
    ]).to_csv(projection_path, index=False)

    bootstrap: dict[str, Any] = {
        "elements": [
            {
                "id": row["id"],
                "web_name": row["name"],
                "team": row["team_id"],
                "element_type": row["pos_id"],
                "now_cost": 50,
            }
            for row in data["players"]
        ],
        "teams": [{"id": club, "name": f"Club{club}", "short_name": f"C{club}"} for club in range(5)],
        "events": [{"id": 6, "is_next": True, "finished": False}],
        "element_types": [
            {"id": pos, "singular_name_short": label, "squad_min_play": low, "squad_max_play": high, "squad_select": count}
            for pos, label, low, high, count in [(1, "GKP", 1, 1, 2), (2, "DEF", 3, 5, 5), (3, "MID", 2, 5, 5), (4, "FWD", 1, 3, 3)]
        ],
    }
    options.update(
        fpl_bootstrap=bootstrap,
        fpl_fixtures=[],
        projections_path=str(projection_path),
        override_next_gw=6,
        xmin_lb=0,
        keep_top_ev_percent=100,
        secs=5,
        verbose=False,
    )
    # Apply strategic arm
    options = apply_scenario_arm(options, ARM_STRATEGIC)

    my_data = build_my_data_from_parent_state(options["parent_state"], processed)
    prepared = prep_data(my_data, options)
    solution = solve_multi_period_fpl(prepared, options)[0]

    assert "strategic_audit" in solution
    audit = solution["strategic_audit"]
    assert audit["enabled"] is True
    assert audit["parameters"]["starter_xmins_floor"] == 65.0
    assert audit["parameters"]["def_stack_cap"] == 2
    assert isinstance(audit["total_slack_penalty"], float)

    # Test serialization retains strategic_audit
    plan = serialize_transfer_plan(solution, champion="test_model", horizon=1, next_gw=6, decay_base=0.85)
    assert "strategic_audit" in plan["meta"]
    assert plan["meta"]["strategic_audit"] == audit


def test_solve_cli_arm_flags(capsys: pytest.CaptureFixture[str]) -> None:
    plan = {
        "meta": {"solver_objective": 12.0, "strategic_audit": {"total_slack_penalty": 0.0, "slacks": {}}},
        "summary": "CLI Plan",
    }
    # 1. Default arm is strategic
    with patch("commands.solve.load_settings", return_value={"datasource": "linear_baseline", "horizon": 5}), \
         patch("commands.solve.execute_transfer_plan", return_value=plan) as mock_exec, \
         patch("sys.argv", ["commands.solve", "--target_gw", "6"]):
        main()
        opts = mock_exec.call_args.args[0]
        assert opts["strategic_mode"] is True
        assert opts["weekly_hit_limit"] == 1
        assert opts["strategic_options"] == DEFAULT_STRATEGIC_OPTIONS

    # 2. Explicit arm unconstrained
    with patch("commands.solve.load_settings", return_value={"datasource": "linear_baseline", "horizon": 5}), \
         patch("commands.solve.execute_transfer_plan", return_value=plan) as mock_exec, \
         patch("sys.argv", ["commands.solve", "--arm", "unconstrained", "--target_gw", "6"]):
        main()
        opts = mock_exec.call_args.args[0]
        assert opts["strategic_mode"] is False
        assert opts["weekly_hit_limit"] == 1
        assert opts.get("strategic_options") is None

    # 3. Custom strategic parameter flags (both canonical and --strategic-* aliases, plus --arm no-hit)
    with patch("commands.solve.load_settings", return_value={"datasource": "linear_baseline", "horizon": 5}), \
         patch("commands.solve.execute_transfer_plan", return_value=plan) as mock_exec, \
         patch(
             "sys.argv",
             [
                 "commands.solve",
                 "--hit-friction", "3.5",
                 "--def-stack-cap", "1",
                 "--bench-cover-penalty", "2.0",
                 "--def-stack-penalty", "1.8",
                 "--target_gw", "6",
             ],
         ):
        main()
        opts = mock_exec.call_args.args[0]
        assert opts["strategic_mode"] is True
        assert opts["strategic_options"]["hit_friction"] == 3.5
        assert opts["strategic_options"]["def_stack_cap"] == 1
        assert opts["strategic_options"]["bench_cover_penalty"] == 2.0
        assert opts["strategic_options"]["def_stack_penalty"] == 1.8

    with patch("commands.solve.load_settings", return_value={"datasource": "linear_baseline", "horizon": 5}), \
         patch("commands.solve.execute_transfer_plan", return_value=plan) as mock_exec, \
         patch("sys.argv", ["commands.solve", "--arm", "no-hit", "--target_gw", "6"]):
        main()
        opts = mock_exec.call_args.args[0]
        assert opts["strategic_mode"] is False
        assert opts["weekly_hit_limit"] == 0


def test_milp_rules_1_to_5_and_waivers(tmp_path: Path) -> None:
    data = dataset()
    # Add an unowned GK (id=17) on Club 1 so GK transfer 1 -> 17 preserves position and club limits
    data["players"].append(
        {
            "id": 17,
            "name": "Player 17",
            "pos_id": 1,
            "pos": "G",
            "team_id": 1,
            "price": 5.0,
            "selling_price": 4.5,
            "projections": {"gw6": {"total_xp": 8.0, "xmins": 90.0, "p_appear": 1.0}},
        }
    )
    planner = Planner(data)
    planner.change_horizon(6, 6)
    processed = tmp_path / "processed"
    processed.mkdir()
    players = [{"id": row["id"], "position_id": row["pos_id"], "now_cost": 50} for row in data["players"]]
    pd.DataFrame(players).to_parquet(processed / "players.parquet")
    paths = PlannerPaths(tmp_path / "dataset.json", processed, tmp_path / "storage")
    base_options = solver_options(planner, paths)

    # Set up projections where:
    # - Owned players 8..15 have low xMins (45.0) so <12 nailed players exist (triggers Rule 2 & Rule 3)
    # - Owned GK1 (id=1, Club 1) and DEF6 (id=6, Club 1) have 20.0 pts so both start, breaching def_stack_cap=1 (Rule 4)
    # - Unowned GK17 (id=17, Club 1) has 8.0 pts vs GK1 (2.0 pts) for GK transfer tests (Rule 5)
    proj_rows = []
    for row in data["players"]:
        pid = int(row["id"])
        pts = float(row["projections"]["gw6"]["total_xp"])
        xmins = 45.0 if 8 <= pid <= 15 else 90.0
        if pid in (1, 6):
            pts = 20.0
            xmins = 90.0
        proj_rows.append(
            {
                "ID": pid,
                "Name": row["name"],
                "Pos": row["pos"],
                "Price": row["price"],
                "Team": f"Club{row['team_id']}",
                "6_Pts": pts,
                "6_xMins": xmins,
            }
        )
    projection_path = tmp_path / "projections_rules.csv"
    pd.DataFrame(proj_rows).to_csv(projection_path, index=False)

    bootstrap: dict[str, Any] = {
        "elements": [
            {
                "id": row["id"],
                "web_name": row["name"],
                "team": row["team_id"],
                "element_type": row["pos_id"],
                "now_cost": 50,
            }
            for row in data["players"]
        ],
        "teams": [{"id": club, "name": f"Club{club}", "short_name": f"C{club}"} for club in range(5)],
        "events": [{"id": 6, "is_next": True, "finished": False}],
        "element_types": [
            {"id": pos, "singular_name_short": label, "squad_min_play": low, "squad_max_play": high, "squad_select": count}
            for pos, label, low, high, count in [(1, "GKP", 1, 1, 2), (2, "DEF", 3, 5, 5), (3, "MID", 2, 5, 5), (4, "FWD", 1, 3, 3)]
        ],
    }
    base_options.update(
        fpl_bootstrap=bootstrap,
        fpl_fixtures=[],
        projections_path=str(projection_path),
        override_next_gw=6,
        xmin_lb=0,
        keep_top_ev_percent=100,
        secs=5,
        verbose=False,
    )
    my_data = build_my_data_from_parent_state(base_options["parent_state"], processed)

    # Solve Strategic arm with no transfers allowed and def_stack_cap=1 (crisis slacks on Rule 2, 3, 4 exercised)
    strat_opts = apply_scenario_arm(base_options, ARM_STRATEGIC, strategic_options={"def_stack_cap": 1})
    strat_opts["num_transfers"] = 0
    prepared = prep_data(my_data, strat_opts)
    strat_sol = solve_multi_period_fpl(prepared, strat_opts)[0]
    audit = strat_sol["strategic_audit"]
    assert audit["enabled"] is True
    assert len(audit["sub_floor_starters"]) > 0
    assert len(audit["bench_cover_shortfalls"]) == 1
    assert len(audit["def_stack_breaches"]) == 1
    assert audit["total_slack_penalty"] > 0.0

    # Rule 5: Book GK transfer (buy id=17, sell id=1) without chip -> penalized; with Wildcard -> waived!
    gk_normal_opts = apply_scenario_arm(base_options, ARM_STRATEGIC)
    gk_normal_opts["booked_transfers"] = [{"gw": 6, "transfer_in": 17, "transfer_out": 1}]
    gk_normal_sol = solve_multi_period_fpl(prep_data(my_data, gk_normal_opts), gk_normal_opts)[0]
    assert len(gk_normal_sol["strategic_audit"]["gk_transfers_penalized"]) == 1

    gk_wc_opts = apply_scenario_arm(base_options, ARM_STRATEGIC)
    gk_wc_opts["use_wc"] = [6]
    gk_wc_opts["force_keep_gws"] = [[17, 6]]
    gk_wc_sol = solve_multi_period_fpl(prep_data(my_data, gk_wc_opts), gk_wc_opts)[0]
    assert gk_wc_sol["strategic_audit"]["gk_transfers_penalized"] == []


def test_xmins_override_updates_egs_lookup_via_target_to_states(tmp_path: Path) -> None:
    from commands.transfer_plan_scenarios import execute_transfer_plan_scenarios

    p_dir = tmp_path / "processed"
    p_dir.mkdir()
    pd.DataFrame([{"id": 10, "status": "a"}]).to_parquet(p_dir / "players.parquet")
    pd.DataFrame([{"player_id": 10, "is_captain": True, "lineup_index": 11}]).to_parquet(p_dir / "user_picks.parquet")
    pd.DataFrame([{"free_transfers": 1, "bank": 0.0}]).to_parquet(p_dir / "user_state.parquet")

    ext_csv = tmp_path / "custom_ext.csv"
    pd.DataFrame([{"ID": 10, "Pos": "F", "5_Pts": 6.0, "5_xMins": 45.0}]).to_csv(ext_csv, index=False)

    def fake_solve(_options: dict, **_kwargs: object) -> dict:
        return {
            "meta": {"next_gw": 5, "horizon": 1},
            "weeks": [{"gw": 5, "lineup_ids": [10], "bench_ids": [], "captain_id": 10, "vice_id": 10, "hits": 0}],
        }

    with patch("commands.transfer_plan_scenarios.DATA_DIR", tmp_path):
        res = execute_transfer_plan_scenarios(
            processed_dir=p_dir,
            target_gw=5,
            horizon=1,
            dataset={"players": [{"id": 10, "pos": "F", "projections": {"gw5": {"total_xp": 6.0, "xmins": 90.0}}}]},
            execute_plan=fake_solve,
            scenarios_path=tmp_path / "scenarios.json",
            solution_path=tmp_path / "solution.json",
            datasource="custom_ext",
            xmins_override=ext_csv,
            force=True,
        )
    assert res["meta"]["status"] == "ok"
    assert len(res["scenarios"]) == 3
    # Captaincy doubles 6.0 -> 12.0 EGS
    assert res["scenarios"][0]["horizon_egs"] == pytest.approx(12.0)


def test_planner_update_and_reset_strategic_options_invalidates_recommendations() -> None:
    data = dataset()
    planner = Planner(data)
    snap = planner.snapshot()
    week_plan = {
        "meta": {"next_gw": 6, "horizon": 1},
        "weeks": [
            {
                "gw": gw,
                "squad_ids": list(range(1, 16)),
                "lineup_ids": [1, 3, 4, 5, 8, 9, 10, 11, 13, 14, 15],
                "bench_ids": [2, 6, 7, 12],
                "captain_id": 13,
                "vice_id": 14,
                "hits": 0,
                "buy": [],
                "sell": [],
            }
            for gw in range(planner.state["start"], planner.state["end"] + 1)
        ],
    }
    accepted = planner.accept_recommendations(
        {"strategic": week_plan, "unconstrained": week_plan, "no_hit": week_plan},
        snap,
        planner.data_digest,
    )
    assert accepted is True
    assert planner.recommendation_valid() is True
    assert planner.week(6)["needs_recalculation"] is False

    planner.update_strategic_options({"hit_friction": 3.2, "def_stack_cap": 1})
    assert planner.state["strategic_options"]["hit_friction"] == 3.2
    assert planner.state["strategic_options"]["def_stack_cap"] == 1
    assert planner.recommendation_valid() is False
    assert planner.week(6)["needs_recalculation"] is True

    planner.reset_strategic_options()
    assert planner.state["strategic_options"] == DEFAULT_STRATEGIC_OPTIONS
    assert planner.recommendation_valid() is True
    assert planner.week(6)["needs_recalculation"] is False


def test_solve_request_planner_service_runs_all_3_arms(tmp_path: Path) -> None:
    from dashboard.planner_service import make_solve_request, solve_request

    data = dataset()
    planner = Planner(data)
    processed = tmp_path / "processed"
    processed.mkdir()
    players = [{"id": row["id"], "position_id": row["pos_id"], "now_cost": 50} for row in data["players"]]
    pd.DataFrame(players).to_parquet(processed / "players.parquet")
    pd.DataFrame([{"player_id": 1, "gameweek_id": 1, "minutes": 90, "starts": 1}]).to_parquet(processed / "player_performances.parquet")
    pd.DataFrame([
        {
            "player_id": pid,
            "purchase_price": 50,
            "selling_price": 50,
            "lineup_index": i,
            "multiplier": 1,
            "is_captain": i == 1,
            "is_vice_captain": i == 2,
        }
        for i, pid in enumerate(range(1, 16), 1)
    ]).to_parquet(processed / "user_picks.parquet")
    pd.DataFrame([{"entry_id": 1, "bank": 10, "free_transfers": 1, "value": 1000, "active_chip": None}]).to_parquet(processed / "user_state.parquet")
    paths = PlannerPaths(tmp_path / "dataset.json", processed, tmp_path / "storage")
    req = make_solve_request(planner, paths)

    with patch("commands.solve.execute_transfer_plan", return_value={"weeks": [{"gw": 6}]}):
        result = solve_request(req, paths)
    assert set(result["plans"].keys()) == {"strategic", "unconstrained", "no_hit"}
    assert result["errors"] == {}
