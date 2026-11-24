import pandas as pd
import pytest
from pathlib import Path
from unittest.mock import patch
from commands.solve import build_my_data_from_parquet, main, validate_booked_chips
from solver.utils import load_settings

def test_build_my_data_from_parquet(tmp_path):
    # 1. Create mock processed tables
    df_picks = pd.DataFrame([
        {"player_id": 101, "purchase_price": 95, "selling_price": 98, "lineup_index": 1, "multiplier": 1, "is_captain": False, "is_vice_captain": False}
    ])
    df_picks.to_parquet(tmp_path / "user_picks.parquet")
    
    df_state = pd.DataFrame([
        {"entry_id": 12345, "bank": 15, "free_transfers": 2, "value": 1000, "active_chip": None}
    ])
    df_state.to_parquet(tmp_path / "user_state.parquet")
    
    df_players = pd.DataFrame([
        {"id": 101, "position_id": 3}
    ])
    df_players.to_parquet(tmp_path / "players.parquet")
    
    # 2. Build my_data dict
    my_data = build_my_data_from_parquet(tmp_path)
    
    assert my_data["team_id"] == 12345
    assert my_data["transfers"]["bank"] == 15
    assert my_data["transfers"]["limit"] == 2
    assert len(my_data["picks"]) == 1
    assert my_data["picks"][0]["element"] == 101
    assert my_data["picks"][0]["selling_price"] == 98
    assert my_data["picks"][0]["element_type"] == 3
    assert my_data["chips"] == []

def test_build_my_data_with_unlimited_transfers(tmp_path):
    # 1. Create mock processed tables
    df_picks = pd.DataFrame([
        {"player_id": 101, "purchase_price": 95, "selling_price": 98, "lineup_index": 1, "multiplier": 1, "is_captain": False, "is_vice_captain": False}
    ])
    df_picks.to_parquet(tmp_path / "user_picks.parquet")
    
    df_state = pd.DataFrame([
        {"entry_id": 12345, "bank": 15, "free_transfers": None, "value": 1000, "active_chip": None}
    ])
    df_state.to_parquet(tmp_path / "user_state.parquet")
    
    df_players = pd.DataFrame([
        {"id": 101, "position_id": 3}
    ])
    df_players.to_parquet(tmp_path / "players.parquet")
    
    # 2. Build my_data dict
    my_data = build_my_data_from_parquet(tmp_path)
    
    assert my_data["transfers"]["limit"] is None


def test_build_my_data_includes_active_user_chips(tmp_path: Path) -> None:
    pd.DataFrame([{
        "player_id": 101, "purchase_price": 95, "selling_price": 98,
        "lineup_index": 1, "multiplier": 1, "is_captain": False, "is_vice_captain": False,
    }]).to_parquet(tmp_path / "user_picks.parquet")
    pd.DataFrame([{
        "entry_id": 12345, "bank": 15, "free_transfers": 1, "value": 1000, "active_chip": "wildcard",
    }]).to_parquet(tmp_path / "user_state.parquet")
    pd.DataFrame([{"id": 101, "position_id": 3}]).to_parquet(tmp_path / "players.parquet")
    pd.DataFrame([{
        "chip": "wc", "name": "wildcard", "status": "active",
        "start_event": 1, "stop_event": 19, "number": 1, "chip_set": 1,
    }]).to_parquet(tmp_path / "user_chips.parquet")
    my_data = build_my_data_from_parquet(tmp_path)
    assert my_data["chips"][0]["name"] == "wildcard"
    assert my_data["chips"][0]["status_for_entry"] == "active"


def test_build_my_data_forwards_limit_and_made_for_chip_refunds(tmp_path: Path) -> None:
    pd.DataFrame([{
        "player_id": 101, "purchase_price": 95, "selling_price": 98,
        "lineup_index": 1, "multiplier": 1, "is_captain": False, "is_vice_captain": False,
    }]).to_parquet(tmp_path / "user_picks.parquet")
    pd.DataFrame([{
        "entry_id": 12345, "bank": 15, "free_transfers": 1,
        "free_transfers_limit": 2, "transfers_made": 1, "value": 1000, "active_chip": None,
    }]).to_parquet(tmp_path / "user_state.parquet")
    pd.DataFrame([{"id": 101, "position_id": 3}]).to_parquet(tmp_path / "players.parquet")
    my_data = build_my_data_from_parquet(tmp_path)
    assert my_data["transfers"]["limit"] == 2
    assert my_data["transfers"]["made"] == 1


def test_validate_booked_chips_accepts_one_chip_per_gameweek():
    validate_booked_chips(
        {"use_wc": [3], "use_bb": [4], "use_fh": [], "use_tc": []},
        next_gw=2,
        horizon=3,
    )


def test_validate_booked_chips_rejects_duplicate_chip():
    with pytest.raises(ValueError, match="booked more than once"):
        validate_booked_chips(
            {"use_wc": [3, 3], "use_bb": [], "use_fh": [], "use_tc": []},
            next_gw=2,
            horizon=3,
        )


def test_validate_booked_chips_rejects_conflict_and_out_of_horizon():
    with pytest.raises(ValueError, match="at most one chip"):
        validate_booked_chips(
            {"use_wc": [3], "use_bb": [3], "use_fh": [], "use_tc": []},
            next_gw=2,
            horizon=3,
        )
    with pytest.raises(ValueError, match="outside planning horizon"):
        validate_booked_chips(
            {"use_wc": [6], "use_bb": [], "use_fh": [], "use_tc": []},
            next_gw=2,
            horizon=3,
        )

def test_solve_cli_prints_summary(capsys):
    mock_settings = {"datasource": "linear_baseline", "horizon": 5, "preseason": True}
    mock_solutions = [{"summary": "Mock recommended transfers and lineups", "statistics": {}, "picks": pd.DataFrame()}]
    
    with patch("commands.solve.load_settings", return_value=mock_settings), \
         patch("commands.solve.prep_data", return_value={}), \
         patch("commands.solve.pad_solver_csv_horizon"), \
         patch("commands.solve.solve_multi_period_fpl", return_value=mock_solutions), \
         patch("sys.argv", ["commands.solve", "--preseason"]):
         
        main()
        
        captured = capsys.readouterr()
        assert "RECOMMENDED SQUAD & TRANSFER PLAN" in captured.out
        assert "Mock recommended transfers and lineups" in captured.out


def test_solve_cli_uses_champion_not_stale_settings_datasource() -> None:
    from models import get_default_model_name

    with patch("commands.solve.load_settings", return_value={"datasource": "linear_baseline", "horizon": 5, "preseason": True}), \
         patch("commands.solve.prep_data", return_value={}), \
         patch("commands.solve.pad_solver_csv_horizon") as pad_mock, \
         patch("commands.solve.solve_multi_period_fpl", return_value=[{"summary": "", "statistics": {}, "picks": pd.DataFrame()}]), \
         patch("sys.argv", ["commands.solve", "--preseason"]):
        main()
    assert pad_mock.call_args.args[0].name == f"{get_default_model_name()}.csv"


def test_load_settings_uses_champion_as_default(tmp_path, monkeypatch):
    from models import get_default_model_name

    monkeypatch.setattr("solver.utils.DATA_DIR", tmp_path)

    assert load_settings()["datasource"] == get_default_model_name()


def test_solve_cli_no_hit_flag_sets_weekly_hit_limit_zero() -> None:
    with patch("commands.solve.load_settings", return_value={"datasource": "linear_baseline", "horizon": 5, "preseason": True}), \
         patch("commands.solve.prep_data", return_value={}), \
         patch("commands.solve.pad_solver_csv_horizon"), \
         patch("commands.solve.solve_multi_period_fpl", return_value=[{"summary": "", "statistics": {}, "picks": pd.DataFrame()}]) as solve_mock, \
         patch("sys.argv", ["commands.solve", "--preseason", "--no_hit"]):
        main()
    options_passed = solve_mock.call_args.args[1]
    assert options_passed["weekly_hit_limit"] == 0


def test_solve_cli_hyphenated_no_hit_flag_sets_weekly_hit_limit_zero() -> None:
    with patch("commands.solve.load_settings", return_value={"datasource": "linear_baseline", "horizon": 5, "preseason": True}), \
         patch("commands.solve.prep_data", return_value={}), \
         patch("commands.solve.pad_solver_csv_horizon"), \
         patch("commands.solve.solve_multi_period_fpl", return_value=[{"summary": "", "statistics": {}, "picks": pd.DataFrame()}]) as solve_mock, \
         patch("sys.argv", ["commands.solve", "--preseason", "--no-hit"]):
        main()
    options_passed = solve_mock.call_args.args[1]
    assert options_passed["weekly_hit_limit"] == 0


def test_solve_cli_gap_zero_keeps_full_proof() -> None:
    seen: dict[str, object] = {}

    def _execute(options: dict[str, object], **_kwargs: object) -> dict[str, object]:
        seen["gap"] = options.get("gap")
        return {"meta": {}, "summary": ""}

    with patch("commands.solve.load_settings", return_value={"horizon": 6, "preseason": True}), \
         patch("commands.solve.execute_transfer_plan", side_effect=_execute), \
         patch("sys.argv", ["commands.solve", "--preseason", "--gap", "0"]):
        main()
    assert seen["gap"] == 0.0


def test_solve_cli_prints_solver_objective_note(capsys: pytest.CaptureFixture[str]) -> None:
    plan = {
        "meta": {"solver_objective_note": "Within 1% of the best Solver Objective."},
        "summary": "",
    }
    with patch("commands.solve.load_settings", return_value={"horizon": 6, "preseason": True}), \
         patch("commands.solve.execute_transfer_plan", return_value=plan), \
         patch("sys.argv", ["commands.solve", "--preseason"]):
        main()
    assert "Within 1% of the best Solver Objective." in capsys.readouterr().out


def test_solve_cli_champion_flag_uses_champion() -> None:
    from models import get_default_model_name

    with patch("commands.solve.load_settings", return_value={"datasource": "linear_baseline", "horizon": 5, "preseason": True}), \
         patch("commands.solve.prep_data", return_value={}), \
         patch("commands.solve.pad_solver_csv_horizon") as pad_mock, \
         patch("commands.solve.solve_multi_period_fpl", return_value=[{"summary": "", "statistics": {}, "picks": pd.DataFrame()}]), \
         patch("sys.argv", ["commands.solve", "--preseason", "--champion"]):
        main()
    assert pad_mock.call_args.args[0].name == f"{get_default_model_name()}.csv"


def test_solve_cli_model_champion_string_uses_champion() -> None:
    from models import get_default_model_name

    with patch("commands.solve.load_settings", return_value={"datasource": "linear_baseline", "horizon": 5, "preseason": True}), \
         patch("commands.solve.prep_data", return_value={}), \
         patch("commands.solve.pad_solver_csv_horizon") as pad_mock, \
         patch("commands.solve.solve_multi_period_fpl", return_value=[{"summary": "", "statistics": {}, "picks": pd.DataFrame()}]), \
         patch("sys.argv", ["commands.solve", "--preseason", "--model", "champion"]):
        main()
    assert pad_mock.call_args.args[0].name == f"{get_default_model_name()}.csv"


def test_solve_cli_defaults_to_single_arm_strategic_gap_zero(capsys: pytest.CaptureFixture[str]) -> None:
    plan = {
        "meta": {"solver_objective": 12.0},
        "summary": "Single plan summary (strategic, gap 0.0)",
    }
    with patch("commands.solve.load_settings", return_value={"datasource": "linear_baseline", "horizon": 5}), \
         patch("commands.solve.execute_transfer_plan", return_value=plan) as mock_single, \
         patch("sys.argv", ["commands.solve", "--target_gw", "6"]):
        main()
        mock_single.assert_called_once()
        options_passed = mock_single.call_args.args[0]
        assert options_passed["weekly_hit_limit"] == 1
        assert options_passed["strategic_options"]["starter_xmins_floor"] == 65.0
        assert options_passed["horizon_scale"] == pytest.approx(1.4437, rel=1e-3)
        assert "2" in options_passed["ft_value_list"]
        assert options_passed["gap"] == 0.0

    captured = capsys.readouterr().out
    assert "Single plan summary (strategic, gap 0.0)" in captured
    assert "TRANSFER PLAN SCENARIOS" not in captured


def test_solve_cli_no_hit_flag_forces_no_hit(capsys: pytest.CaptureFixture[str]) -> None:
    plan = {
        "meta": {"solver_objective": 12.0},
        "summary": "Single plan summary (no-hit, gap 0.0)",
    }
    with patch("commands.solve.load_settings", return_value={"datasource": "linear_baseline", "horizon": 5}), \
         patch("commands.solve.execute_transfer_plan", return_value=plan) as mock_single, \
         patch("sys.argv", ["commands.solve", "--no-hit", "--target_gw", "6"]):
        main()
        mock_single.assert_called_once()
        options_passed = mock_single.call_args.args[0]
        assert options_passed["weekly_hit_limit"] == 0
        assert options_passed.get("strategic_options") is None
        assert options_passed["gap"] == 0.0


def test_solve_cli_scenarios_flag_runs_3_arm_scenarios(capsys: pytest.CaptureFixture[str]) -> None:
    fake_scenarios_payload = {
        "meta": {"status": "ok", "arms": ["strategic", "unconstrained", "no_hit"], "data_digest": "abcdef12"},
        "scenarios": [
            {
                "id": "strategic",
                "name": "Strategic",
                "rank": 1,
                "horizon_egs": 38.5,
                "plan": {
                    "summary": "Haaland (C) GW6",
                    "weeks": [{"gw": 6, "hits": 0, "buy": [{"name": "Saka"}], "sell": [{"name": "Eze"}]}],
                },
            },
            {
                "id": "unconstrained",
                "name": "Unconstrained",
                "rank": 2,
                "horizon_egs": 37.0,
                "plan": {"summary": "", "weeks": [{"gw": 6, "hits": 0, "buy": [], "sell": []}]},
            },
            {
                "id": "no_hit",
                "name": "No Hit",
                "rank": 3,
                "horizon_egs": 36.2,
                "plan": {"summary": "", "weeks": [{"gw": 6, "hits": 0, "buy": [], "sell": []}]},
            },
        ],
    }

    with patch("commands.solve.load_settings", return_value={"datasource": "linear_baseline", "horizon": 5}), \
         patch("commands.transfer_plan_scenarios.execute_transfer_plan_scenarios", return_value=fake_scenarios_payload) as mock_scenarios, \
         patch("sys.argv", ["commands.solve", "--scenarios", "--target_gw", "6"]):
        main()
        mock_scenarios.assert_called_once()

    captured = capsys.readouterr().out
    assert "TRANSFER PLAN SCENARIOS (3 ARMS RANKED)" in captured
    assert "Rank 1: Strategic" in captured
    assert "Rank 2: Unconstrained" in captured
    assert "Rank 3: No Hit" in captured
    assert "Haaland (C) GW6" in captured


def test_solve_cli_single_flag_runs_single_plan(capsys: pytest.CaptureFixture[str]) -> None:
    plan = {
        "meta": {"solver_objective": 12.0},
        "summary": "Single plan summary",
    }
    with patch("commands.solve.load_settings", return_value={"datasource": "linear_baseline", "horizon": 5}), \
         patch("commands.solve.execute_transfer_plan", return_value=plan) as mock_single, \
         patch("sys.argv", ["commands.solve", "--single", "--target_gw", "6"]):
        main()
        mock_single.assert_called_once()

    captured = capsys.readouterr().out
    assert "Single plan summary" in captured
    assert "TRANSFER PLAN SCENARIOS" not in captured


def test_solve_cli_routes_default_to_provisional_active_and_champion_flag_switches_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from backtesting.portable_evidence import VerificationScorecard, write_scorecard
    from models.selection import ModelSelection, save_model_selection

    sel_path = tmp_path / "model_selection.json"
    save_model_selection(
        ModelSelection(
            champion="def_xg_shrink_challenger",
            candidates=("adaptive_causal_challenger",),
            provisional_active="adaptive_causal_challenger",
            podium_frozen_season="2026-27",
            podium_sealed=True,
        ),
        sel_path,
    )
    monkeypatch.setattr("models.selection.DEFAULT_CONFIG_PATH", sel_path)

    evidence_dir = tmp_path / "evidence"
    write_scorecard(
        evidence_dir,
        VerificationScorecard(
            season="2026-27",
            checkpoint_gw=15,
            slate_id="slate-2026-27",
            slate_sealed=True,
            confirmed_champion="def_xg_shrink_challenger",
            podium_order=("adaptive_causal_challenger",),
            provisional_active="adaptive_causal_challenger",
            serving_model_closure_hash="a" * 64,
            model_runtime_bindings={},
            evaluator_code_hash="b" * 64,
            producer_git_sha="c" * 40,
            settled_through_gw=15,
            gap_status="complete",
            first_blocked_gw=None,
            reason_codes=(),
            cumulative_net_points={
                "def_xg_shrink_challenger": 820.0,
                "adaptive_causal_challenger": 835.0,
            },
            weekly_leader="adaptive_causal_challenger",
            active_exclusions=(),
            generated_at="2026-11-20T12:00:00+00:00",
        ),
    )

    with (
        patch("commands.solve.load_settings", return_value={"datasource": "linear_baseline", "horizon": 5, "preseason": True}),
        patch("commands.solve.prep_data", return_value={}),
        patch("commands.solve.pad_solver_csv_horizon") as pad_mock,
        patch("commands.solve.solve_multi_period_fpl", return_value=[{"summary": "", "statistics": {}, "picks": pd.DataFrame()}]),
        patch("sys.argv", ["commands.solve", "--preseason", "--evidence-dir", str(evidence_dir)]),
    ):
        main()
    assert pad_mock.call_args.args[0].name == "adaptive_causal_challenger.csv"

    with (
        patch("commands.solve.load_settings", return_value={"datasource": "linear_baseline", "horizon": 5, "preseason": True}),
        patch("commands.solve.prep_data", return_value={}),
        patch("commands.solve.pad_solver_csv_horizon") as pad_mock_champ,
        patch("commands.solve.solve_multi_period_fpl", return_value=[{"summary": "", "statistics": {}, "picks": pd.DataFrame()}]),
        patch("sys.argv", ["commands.solve", "--preseason", "--champion", "--evidence-dir", str(evidence_dir)]),
    ):
        main()
    assert pad_mock_champ.call_args.args[0].name == "def_xg_shrink_challenger.csv"


def test_solve_cli_xmins_override_rerun_pins_prior_reviewed_base_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import json
    from backtesting.portable_evidence import VerificationScorecard, write_scorecard
    from models.selection import ModelSelection, save_model_selection

    sel_path = tmp_path / "model_selection.json"
    save_model_selection(
        ModelSelection(
            champion="def_xg_shrink_challenger",
            candidates=("adaptive_causal_challenger",),
            provisional_active=None,
            podium_frozen_season="2026-27",
            podium_sealed=True,
        ),
        sel_path,
    )
    monkeypatch.setattr("models.selection.DEFAULT_CONFIG_PATH", sel_path)
    monkeypatch.setattr("commands.solve.PROJECT_ROOT", tmp_path)
    proc_dir = tmp_path / "data" / "processed"
    proc_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {"id": gw, "finished": True, "data_checked": True, "is_next": False, "deadline_time": f"2026-11-{gw:02d}T11:00:00Z"}
            for gw in range(1, 16)
        ]
        + [{"id": 16, "finished": False, "data_checked": False, "is_next": True, "deadline_time": "2099-12-08T11:00:00Z"}]
    ).to_parquet(proc_dir / "gameweeks.parquet")
    evidence_dir = tmp_path / "evidence"
    # Initial solve at GW16: adaptive_causal_challenger leads (835 vs 820)
    write_scorecard(
        evidence_dir,
        VerificationScorecard(
            season="2026-27",
            checkpoint_gw=15,
            slate_id="slate-2026-27",
            slate_sealed=True,
            confirmed_champion="def_xg_shrink_challenger",
            podium_order=("adaptive_causal_challenger",),
            provisional_active=None,
            serving_model_closure_hash="a" * 64,
            model_runtime_bindings={},
            evaluator_code_hash="b" * 64,
            producer_git_sha="c" * 40,
            settled_through_gw=15,
            gap_status="complete",
            first_blocked_gw=None,
            reason_codes=(),
            cumulative_net_points={
                "def_xg_shrink_challenger": 820.0,
                "adaptive_causal_challenger": 835.0,
            },
            weekly_leader="adaptive_causal_challenger",
            active_exclusions=(),
            generated_at="2026-11-20T12:00:00+00:00",
        ),
    )
    override_csv = tmp_path / "xmins_override.csv"
    override_csv.write_text("ID,16_xMins\n1,90\n", encoding="utf-8")

    projected_models: list[str] = []

    def _fake_gen_proj(*, model_name: str, **_kwargs: object) -> None:
        projected_models.append(model_name)

    with (
        patch("commands.solve.load_settings", return_value={"horizon": 5, "preseason": True}),
        patch("commands.solve.prep_data", return_value={}),
        patch("commands.solve.pad_solver_csv_horizon"),
        patch("commands.solve.solve_multi_period_fpl", return_value=[{"summary": "", "statistics": {}, "picks": pd.DataFrame()}]),
        patch("commands.run_model.generate_model_projections", side_effect=_fake_gen_proj),
        patch(
            "sys.argv",
            [
                "commands.solve",
                "--preseason",
                "--target_gw",
                "16",
                "--evidence-dir",
                str(evidence_dir),
                "--xmins-override",
                str(override_csv),
            ],
        ),
    ):
        main()

    assert projected_models == ["adaptive_causal_challenger"]
    sol_data = json.loads((tmp_path / "data" / "solution.json").read_text(encoding="utf-8"))
    assert sol_data["meta"]["reviewed_base_model"] == "adaptive_causal_challenger"
    assert sol_data["meta"]["champion"] == "adaptive_causal_challenger_external_xmins"

    # Now scorecard flips to Champion leading (845 vs 835) before Step 6 rerun!
    write_scorecard(
        evidence_dir,
        VerificationScorecard(
            season="2026-27",
            checkpoint_gw=15,
            slate_id="slate-2026-27",
            slate_sealed=True,
            confirmed_champion="def_xg_shrink_challenger",
            podium_order=("adaptive_causal_challenger",),
            provisional_active=None,
            serving_model_closure_hash="a" * 64,
            model_runtime_bindings={},
            evaluator_code_hash="b" * 64,
            producer_git_sha="c" * 40,
            settled_through_gw=15,
            gap_status="complete",
            first_blocked_gw=None,
            reason_codes=(),
            cumulative_net_points={
                "def_xg_shrink_challenger": 845.0,
                "adaptive_causal_challenger": 835.0,
            },
            weekly_leader="def_xg_shrink_challenger",
            active_exclusions=(),
            generated_at="2026-11-20T12:05:00+00:00",
        ),
    )

    # 1. --xmins-override WITHOUT --rerun does NOT pin prior reviewed model -> switches to new scorecard leader
    projected_models.clear()
    with (
        patch("commands.solve.load_settings", return_value={"horizon": 5, "preseason": True}),
        patch("commands.solve.prep_data", return_value={}),
        patch("commands.solve.pad_solver_csv_horizon"),
        patch("commands.solve.solve_multi_period_fpl", return_value=[{"summary": "", "statistics": {}, "picks": pd.DataFrame()}]),
        patch("commands.run_model.generate_model_projections", side_effect=_fake_gen_proj),
        patch(
            "sys.argv",
            [
                "commands.solve",
                "--preseason",
                "--target_gw",
                "16",
                "--evidence-dir",
                str(evidence_dir),
                "--xmins-override",
                str(override_csv),
            ],
        ),
    ):
        main()

    assert projected_models == ["def_xg_shrink_challenger"]
    sol_fresh = json.loads((tmp_path / "data" / "solution.json").read_text(encoding="utf-8"))
    assert sol_fresh["meta"]["pinned_for_rerun"] is False

    # Restore prior GW16 solution from initial solve, then pass explicit --rerun -> stays pinned!
    (tmp_path / "data" / "solution.json").write_text(json.dumps(sol_data), encoding="utf-8")
    projected_models.clear()
    with (
        patch("commands.solve.load_settings", return_value={"horizon": 5, "preseason": True}),
        patch("commands.solve.prep_data", return_value={}),
        patch("commands.solve.pad_solver_csv_horizon"),
        patch("commands.solve.solve_multi_period_fpl", return_value=[{"summary": "", "statistics": {}, "picks": pd.DataFrame()}]),
        patch("commands.run_model.generate_model_projections", side_effect=_fake_gen_proj),
        patch(
            "sys.argv",
            [
                "commands.solve",
                "--preseason",
                "--target_gw",
                "16",
                "--evidence-dir",
                str(evidence_dir),
                "--xmins-override",
                str(override_csv),
                "--rerun",
            ],
        ),
    ):
        main()

    # Rerun stayed pinned to adaptive_causal_challenger!
    assert projected_models == ["adaptive_causal_challenger"]
    sol_rerun = json.loads((tmp_path / "data" / "solution.json").read_text(encoding="utf-8"))
    assert sol_rerun["meta"]["reviewed_base_model"] == "adaptive_causal_challenger"
    assert sol_rerun["meta"]["pinned_for_rerun"] is True


def test_build_my_data_from_parent_state_forwards_limit_and_made(tmp_path: Path) -> None:
    from commands.solve import build_my_data_from_parent_state

    pd.DataFrame([{"id": pid, "position_id": 3, "now_cost": 50} for pid in range(1, 16)]).to_parquet(
        tmp_path / "players.parquet"
    )
    parent = {
        "lineup": {"slots": {str(i): i for i in range(1, 16)}},
        "evaluation": {"bankRemaining": 1.2, "freeTransfersNext": 1, "freeTransfersLimit": 2, "transfersMade": 1},
    }
    my_data = build_my_data_from_parent_state(parent, tmp_path)
    assert my_data["transfers"]["limit"] == 2
    assert my_data["transfers"]["made"] == 1

    # Backward-compatible fallback when limit/made omitted
    legacy_parent = {
        "lineup": {"slots": {str(i): i for i in range(1, 16)}},
        "evaluation": {"bankRemaining": 1.2, "freeTransfersNext": 3},
    }
    legacy_data = build_my_data_from_parent_state(legacy_parent, tmp_path)
    assert legacy_data["transfers"]["limit"] == 3
    assert legacy_data["transfers"]["made"] == 0


