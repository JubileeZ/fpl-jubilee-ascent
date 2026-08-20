import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pandas as pd

from commands.dashboard import run_dashboard_transfer_plan
from commands.solve import execute_transfer_plan, transfer_plan_options_for_dashboard
from solver.transfer_plan import serialize_transfer_plan
from solver.utils import DEFAULT_PLANNING_HORIZON, load_settings


def _picks() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "id": 10, "week": 1, "name": "Haaland", "pos": "FWD", "type": 4, "team": "MCI",
                "squad": 1, "lineup": 1, "bench": -1, "captain": 1, "vicecaptain": 0,
                "transfer_in": 0, "transfer_out": 0, "chip": "BB", "ft": 1, "transfer_count": 0,
                "xp_cont": 8.0, "xP": 8.0,
            },
            {
                "id": 20, "week": 1, "name": "Salah", "pos": "MID", "type": 3, "team": "LIV",
                "squad": 1, "lineup": 0, "bench": 0, "captain": 0, "vicecaptain": 1,
                "transfer_in": 0, "transfer_out": 0, "chip": "BB", "ft": 1, "transfer_count": 0,
                "xp_cont": 0.0, "xP": 6.0,
            },
            {
                "id": 10, "week": 2, "name": "Haaland", "pos": "FWD", "type": 4, "team": "MCI",
                "squad": 0, "lineup": 0, "bench": -1, "captain": 0, "vicecaptain": 0,
                "transfer_in": 0, "transfer_out": 1, "chip": "", "ft": 1, "transfer_count": 1,
                "xp_cont": 0.0, "xP": 8.0,
            },
            {
                "id": 30, "week": 2, "name": "Watkins", "pos": "FWD", "type": 4, "team": "AVL",
                "squad": 1, "lineup": 1, "bench": -1, "captain": 1, "vicecaptain": 0,
                "transfer_in": 1, "transfer_out": 0, "chip": "", "ft": 1, "transfer_count": 1,
                "xp_cont": 7.0, "xP": 7.0,
            },
            {
                "id": 20, "week": 2, "name": "Salah", "pos": "MID", "type": 3, "team": "LIV",
                "squad": 1, "lineup": 0, "bench": 0, "captain": 0, "vicecaptain": 1,
                "transfer_in": 0, "transfer_out": 0, "chip": "", "ft": 1, "transfer_count": 1,
                "xp_cont": 0.0, "xP": 6.0,
            },
        ]
    )


def test_serialize_transfer_plan_is_json_safe_and_lists_weekly_moves() -> None:
    solution = {
        "picks": _picks(),
        "total_xp": 15.0,
        "score": 14.2,
        "statistics": {
            1: {"itb": 0.5, "ft": 1, "pt": 0, "nt": 0, "xP": 8.0, "obj": 8.0, "chip": "BB"},
            2: {"itb": 1.0, "ft": 1, "pt": 0, "nt": 1, "xP": 7.0, "obj": 6.0, "chip": None},
        },
        "summary": "GW plan",
    }
    plan = serialize_transfer_plan(
        solution,
        champion="participation_state_hybrid",
        horizon=6,
        next_gw=1,
        decay_base=0.85,
        booked_chips={"use_bb": [1], "use_wc": [], "use_fh": [], "use_tc": []},
    )
    dumped = json.dumps(plan)
    loaded = json.loads(dumped)
    assert loaded["meta"]["champion"] == "participation_state_hybrid"
    assert loaded["meta"]["horizon"] == 6
    assert loaded["meta"]["next_gw"] == 1
    assert loaded["meta"]["decay_base"] == 0.85
    assert loaded["meta"]["solver_objective"] == 14.2
    assert loaded["meta"]["total_xp"] == 15.0
    assert loaded["meta"]["booked_chips"]["use_bb"] == [1]
    assert loaded["weeks"][0]["gw"] == 1
    assert loaded["weeks"][0]["chip"] == "BB"
    assert loaded["weeks"][0]["xp"] == 8.0
    assert loaded["weeks"][0]["objective"] == 8.0
    assert loaded["weeks"][0]["squad_ids"] == [10, 20]
    assert loaded["weeks"][0]["lineup_ids"] == [10]
    assert loaded["weeks"][0]["bench_ids"] == [20]
    assert loaded["weeks"][0]["captain_id"] == 10
    assert loaded["weeks"][0]["vice_id"] == 20
    assert loaded["weeks"][0]["buy"] == []
    assert loaded["weeks"][0]["sell"] == []
    assert loaded["weeks"][1]["buy"] == [{"id": 30, "name": "Watkins"}]
    assert loaded["weeks"][1]["sell"] == [{"id": 10, "name": "Haaland"}]
    assert loaded["weeks"][1]["chip"] is None
    assert "model" not in dumped


def test_load_settings_defaults_planning_horizon_to_six(tmp_path: Path, monkeypatch: Any) -> None:
    monkeypatch.setattr("solver.utils.DATA_DIR", tmp_path)
    assert DEFAULT_PLANNING_HORIZON == 6
    assert load_settings()["horizon"] == 6


def test_execute_transfer_plan_writes_json_safe_plan(tmp_path: Path) -> None:
    solution = {
        "picks": _picks(),
        "total_xp": 15.0,
        "score": 14.2,
        "statistics": {
            1: {"itb": 0.5, "ft": 1, "pt": 0, "nt": 0, "xP": 8.0, "obj": 8.0, "chip": "BB"},
            2: {"itb": 1.0, "ft": 1, "pt": 0, "nt": 1, "xP": 7.0, "obj": 6.0, "chip": None},
        },
        "summary": "GW plan",
    }
    sol_path = tmp_path / "solution.json"
    options = {
        "datasource": "linear_baseline",
        "horizon": 6,
        "preseason": True,
        "decay_base": 0.85,
        "use_bb": [1],
        "use_wc": [],
        "use_fh": [],
        "use_tc": [],
    }
    with patch("commands.solve.prep_data", return_value={}), patch(
        "commands.solve.solve_multi_period_fpl", return_value=[solution]
    ):
        plan = execute_transfer_plan(
            options, processed_dir=tmp_path, target_gw=1, solution_path=sol_path
        )
    loaded = json.loads(sol_path.read_text(encoding="utf-8"))
    assert loaded["weeks"][1]["buy"][0]["name"] == "Watkins"
    assert loaded["meta"]["champion"] == "linear_baseline"
    assert plan["weeks"][0]["chip"] == "BB"


def test_dashboard_transfer_plan_options_force_champion() -> None:
    with patch(
        "commands.solve.load_settings",
        return_value={"datasource": "linear_baseline", "horizon": 5, "decay_base": 0.85},
    ):
        options = transfer_plan_options_for_dashboard(
            {"use_wc": [4], "use_bb": [1], "use_fh": [], "use_tc": []},
            horizon=6,
        )
    assert options["datasource"] == "participation_state_hybrid"
    assert options["horizon"] == 6
    assert options["use_wc"] == [4]
    assert options["use_bb"] == [1]


def test_run_dashboard_transfer_plan_passes_booked_chips_and_preseason(tmp_path: Path, monkeypatch: Any) -> None:
    monkeypatch.setattr("commands.dashboard.PROJECT_ROOT", tmp_path)
    monkeypatch.setattr("commands.dashboard.SOLUTION_PATH", tmp_path / "data" / "solution.json")
    captured: dict[str, Any] = {}

    def fake_execute(
        options: dict[str, object],
        *,
        processed_dir: Path,
        target_gw: int,
        solution_path: Path,
    ) -> dict[str, Any]:
        captured["options"] = options
        captured["target_gw"] = target_gw
        captured["solution_path"] = solution_path
        return {"meta": {"champion": options["datasource"]}, "weeks": []}

    with patch("commands.dashboard.execute_transfer_plan", side_effect=fake_execute):
        plan = run_dashboard_transfer_plan({"use_wc": [4], "use_bb": [1], "target_gw": 2, "horizon": 6})
    assert captured["target_gw"] == 2
    assert captured["options"]["preseason"] is True
    assert captured["options"]["datasource"] == "participation_state_hybrid"
    assert captured["options"]["use_wc"] == [4]
    assert plan["meta"]["champion"] == "participation_state_hybrid"
