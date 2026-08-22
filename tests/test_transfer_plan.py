import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pandas as pd

from commands.dashboard import ensure_solver_projection_csv, run_dashboard_transfer_plan
from commands.export_dashboard import load_transfer_plan, load_transfer_plan_document
from commands.solve import execute_transfer_plan, transfer_plan_options_for_dashboard
from projections.exporter import pad_solver_csv_horizon, solver_csv_covers_horizon, write_solver_projection_csvs
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


def test_load_settings_defaults_planning_horizon_to_five(tmp_path: Path, monkeypatch: Any) -> None:
    monkeypatch.setattr("solver.utils.DATA_DIR", tmp_path)
    assert DEFAULT_PLANNING_HORIZON == 5
    assert load_settings()["horizon"] == 5


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
    with patch("commands.solve.pad_solver_csv_horizon"), patch(
        "commands.solve.prep_data", return_value={}
    ), patch(
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
            horizon=5,
        )
    assert options["datasource"] == "participation_state_hybrid"
    assert options["horizon"] == 5
    assert options["use_wc"] == [4]
    assert options["use_bb"] == [1]
    assert options["enabled_chip_windows"] == []
    assert options["force_keep_gws"] == []


def test_dashboard_transfer_plan_options_include_keep_ban_and_enabled() -> None:
    with patch(
        "commands.solve.load_settings",
        return_value={"datasource": "linear_baseline", "horizon": 5, "decay_base": 0.85, "keep": []},
    ):
        options = transfer_plan_options_for_dashboard(
            {"use_wc": [], "use_bb": [], "use_fh": [], "use_tc": []},
            horizon=5,
            enabled_chips=[{"chip": "bb", "chip_set": 1}],
            force_keep=[{"player_id": 10, "gw": 1}],
            force_ban=[{"player_id": 20, "gw": 2}],
            target_gw=1,
        )
    assert options["force_keep_gws"] == [[10, 1]]
    assert options["force_ban_gws"] == [[20, 2]]
    assert options["enabled_chip_windows"][0]["chip"] == "bb"
    assert 10 in options["keep"]


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

    with patch("commands.dashboard.ensure_solver_projection_csv", return_value=tmp_path / "data" / "participation_state_hybrid.csv"), patch(
        "commands.dashboard.execute_transfer_plan", side_effect=fake_execute
    ):
        plan = run_dashboard_transfer_plan({
            "use_wc": [4],
            "use_bb": [3],
            "target_gw": 2,
            "horizon": 5,
            "enabled_chips": [{"chip": "fh", "chip_set": 1}],
            "force_keep": [{"player_id": 10, "gw": 2}],
            "force_ban": [{"player_id": 20, "gw": 3}],
        })
    assert captured["target_gw"] == 2
    assert captured["options"]["preseason"] is True
    assert captured["options"]["datasource"] == "participation_state_hybrid"
    assert captured["options"]["use_wc"] == [4]
    assert captured["options"]["use_bb"] == [3]
    assert captured["options"]["force_keep_gws"] == [[10, 2]]
    assert captured["options"]["force_ban_gws"] == [[20, 3]]
    assert captured["options"]["enabled_chip_windows"][0]["chip"] == "fh"
    assert 10 in captured["options"]["keep"]
    assert plan["meta"]["champion"] == "participation_state_hybrid"


def _player_meta() -> tuple[pd.DataFrame, pd.DataFrame]:
    players = pd.DataFrame([{
        "id": 10, "web_name": "Haaland", "club_id": 1, "position_id": 4, "now_cost": 140, "code": 123,
    }])
    clubs = pd.DataFrame([{"id": 1, "short_name": "MCI"}])
    return players, clubs


def test_solver_csv_covers_horizon_requires_every_milp_week(tmp_path: Path) -> None:
    csv_path = tmp_path / "participation_state_hybrid.csv"
    pd.DataFrame([{
        "ID": 10, "Name": "Haaland", "Pos": "F", "Price": 14.0, "Team": "MCI",
        "1_Pts": 8.0, "2_Pts": 7.0, "3_Pts": 6.0, "4_Pts": 5.0, "5_Pts": 4.0,
    }]).to_csv(csv_path, index=False)
    assert solver_csv_covers_horizon(csv_path, target_gw=1, horizon=5) is True
    assert solver_csv_covers_horizon(csv_path, target_gw=1, horizon=6) is False
    assert solver_csv_covers_horizon(tmp_path / "missing.csv", target_gw=1, horizon=6) is False


def test_pad_solver_csv_horizon_adds_missing_week_columns(tmp_path: Path) -> None:
    csv_path = tmp_path / "linear_baseline.csv"
    pd.DataFrame([{
        "ID": 10, "Name": "Haaland", "Pos": "F", "Price": 14.0, "Team": "MCI",
        "1_Pts": 8.0, "2_Pts": 7.0, "3_Pts": 6.0, "4_Pts": 5.0, "5_Pts": 4.0,
        "1_xMins": 90.0, "2_xMins": 90.0, "3_xMins": 90.0, "4_xMins": 90.0, "5_xMins": 90.0,
    }]).to_csv(csv_path, index=False)
    pad_solver_csv_horizon(csv_path, target_gw=1, horizon=6)
    loaded = pd.read_csv(csv_path)
    assert loaded.loc[0, "6_Pts"] == 0.0
    assert loaded.loc[0, "6_xMins"] == 0.0
    assert loaded.loc[0, "5_Pts"] == 4.0
    assert solver_csv_covers_horizon(csv_path, target_gw=1, horizon=6) is True


def test_write_solver_projection_csvs_includes_planning_horizon_weeks(tmp_path: Path) -> None:
    players, clubs = _player_meta()
    predictions = pd.DataFrame([
        {"player_id": 10, "gameweek_id": gw, "projected_points": 8.0, "projected_minutes": 90.0}
        for gw in range(1, 7)
    ])
    write_solver_projection_csvs(
        {"participation_state_hybrid": predictions},
        players,
        clubs,
        tmp_path,
    )
    csv_path = tmp_path / "participation_state_hybrid.csv"
    assert solver_csv_covers_horizon(csv_path, target_gw=1, horizon=6) is True
    cols = set(pd.read_csv(csv_path, nrows=0).columns)
    assert "6_Pts" in cols
    assert "6_xMins" in cols


def test_ensure_solver_projection_csv_rebuilds_when_sixth_week_missing(tmp_path: Path) -> None:
    processed = tmp_path / "processed"
    processed.mkdir()
    players, clubs = _player_meta()
    players.to_parquet(processed / "players.parquet")
    clubs.to_parquet(processed / "clubs.parquet")
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    pd.DataFrame([{
        "ID": 10, "Name": "Haaland", "Pos": "F", "Price": 14.0, "Team": "MCI",
        "1_Pts": 8.0, "2_Pts": 7.0, "3_Pts": 6.0, "4_Pts": 5.0, "5_Pts": 4.0,
    }]).to_csv(data_dir / "participation_state_hybrid.csv", index=False)

    class FakeModel:
        def predict(self, _features: pd.DataFrame, horizon: int) -> pd.DataFrame:
            return pd.DataFrame([
                {"player_id": 10, "gameweek_id": gw, "projected_points": 8.0, "projected_minutes": 90.0}
                for gw in range(1, horizon + 1)
            ])

    with patch("commands.dashboard.build_features", return_value=pd.DataFrame()), patch(
        "commands.dashboard.get_model", return_value=FakeModel()
    ):
        path = ensure_solver_projection_csv(
            "participation_state_hybrid", processed, target_gw=1, horizon=6, output_dir=data_dir
        )
    assert path == data_dir / "participation_state_hybrid.csv"
    assert solver_csv_covers_horizon(path, target_gw=1, horizon=6) is True


def test_run_dashboard_transfer_plan_ensures_csv_before_solve(tmp_path: Path, monkeypatch: Any) -> None:
    monkeypatch.setattr("commands.dashboard.PROJECT_ROOT", tmp_path)
    monkeypatch.setattr("commands.dashboard.SOLUTION_PATH", tmp_path / "data" / "solution.json")
    captured: dict[str, Any] = {}

    def fake_ensure(
        model_name: str,
        processed_dir: Path,
        target_gw: int,
        horizon: int,
        output_dir: Path,
    ) -> Path:
        captured["ensure"] = {
            "model_name": model_name,
            "processed_dir": processed_dir,
            "target_gw": target_gw,
            "horizon": horizon,
            "output_dir": output_dir,
        }
        return output_dir / f"{model_name}.csv"

    with patch("commands.dashboard.ensure_solver_projection_csv", side_effect=fake_ensure), patch(
        "commands.dashboard.execute_transfer_plan",
        return_value={"meta": {"champion": "participation_state_hybrid"}, "weeks": []},
    ):
        run_dashboard_transfer_plan({"horizon": 6, "target_gw": 1})
    assert captured["ensure"]["model_name"] == "participation_state_hybrid"
    assert captured["ensure"]["horizon"] == 5
    assert captured["ensure"]["target_gw"] == 1
    assert captured["ensure"]["output_dir"] == tmp_path / "data"


def test_load_transfer_plan_document_rejects_truncated_and_legacy(tmp_path: Path) -> None:
    truncated = tmp_path / "truncated.json"
    truncated.write_text(
        '{\n  "summary": "Mock recommended transfers and lineups",\n  "statistics": {},\n  "picks":  \n',
        encoding="utf-8",
    )
    assert load_transfer_plan_document(truncated) is None
    squad_ids, model_name, plan = load_transfer_plan(truncated)
    assert squad_ids == []
    assert model_name is None
    assert plan is None

    legacy = tmp_path / "legacy.json"
    legacy.write_text(
        json.dumps({"picks": [{"element": 10}], "model_name": "linear_baseline"}),
        encoding="utf-8",
    )
    assert load_transfer_plan_document(legacy) is None
    squad_ids, model_name, plan = load_transfer_plan(legacy)
    assert squad_ids == [10]
    assert model_name == "linear_baseline"
    assert plan is None
