"""Dashboard Transfer Plan Surface API."""

from pathlib import Path
import json

import pandas as pd
import pytest

from commands.transfer_plan_scenarios import UserSquadRequired, execute_transfer_plan_scenarios
from solver.scenarios import ARM_OPTIMAL, ARM_ROLL


def _squad(processed_dir: Path) -> None:
    processed_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{
        "id": 10, "code": 101, "first_name": "Erling", "second_name": "Haaland",
        "web_name": "Haaland", "club_id": 1, "position_id": 4, "now_cost": 150,
        "status": "a", "chance_of_playing_next_round": 100, "news": "",
        "total_points": 0, "minutes": 0, "starts": 0, "ict_index": "0",
        "influence": "0", "creativity": "0", "threat": "0",
        "expected_goals": "0", "expected_assists": "0", "selected_by_percent": 0,
    }]).to_parquet(processed_dir / "players.parquet")
    pd.DataFrame([
        {"entry_id": 1, "gameweek_id": 1, "player_id": 10, "lineup_index": 11,
         "multiplier": 1, "is_captain": True, "is_vice_captain": False,
         "purchase_price": 145, "selling_price": 146},
    ]).to_parquet(processed_dir / "user_picks.parquet")
    pd.DataFrame([
        {"entry_id": 1, "bank": 5, "value": 1000, "free_transfers": 0, "active_chip": None},
    ]).to_parquet(processed_dir / "user_state.parquet")


def test_execute_scenarios_requires_user_squad(tmp_path: Path) -> None:
    processed = tmp_path / "processed"
    processed.mkdir()
    with pytest.raises(UserSquadRequired):
        execute_transfer_plan_scenarios(
            processed_dir=processed,
            target_gw=5,
            horizon=1,
            dataset={"players": []},
            scenarios_path=tmp_path / "scenarios.json",
            solution_path=tmp_path / "solution.json",
        )


def test_execute_scenarios_ranks_feasible_arms(tmp_path: Path) -> None:
    processed = tmp_path / "processed"
    _squad(processed)
    dataset = {
        "players": [{
            "id": 10,
            "pos": "F",
            "pos_id": 4,
            "projections": {"gw5": {"total_xp": 8.0, "xmins": 90.0, "p_appear": 1.0}},
        }]
    }

    def fake_execute(options: dict, **kwargs: object) -> dict:
        hits = 0 if options.get("no_transfer_gws") else 1
        return {
            "meta": {"solver_objective": 10.0 if hits else 9.0, "next_gw": 5, "horizon": 1},
            "weeks": [{
                "gw": 5,
                "lineup_ids": [10],
                "bench_ids": [],
                "captain_id": 10,
                "vice_id": 10,
                "hits": hits,
                "chip": None,
            }],
        }

    payload = execute_transfer_plan_scenarios(
        processed_dir=processed,
        target_gw=5,
        horizon=1,
        dataset=dataset,
        execute_plan=fake_execute,
        scenarios_path=tmp_path / "scenarios.json",
        solution_path=tmp_path / "solution.json",
    )
    ids = [row["id"] for row in payload["scenarios"]]
    assert ARM_ROLL in ids
    assert ARM_OPTIMAL in ids
    assert "one_ft" not in ids
    assert payload["scenarios"][0]["rank"] == 1
    assert (tmp_path / "scenarios.json").exists()
    assert (tmp_path / "solution.json").exists()


def test_handle_dashboard_api_transfer_plan(monkeypatch: pytest.MonkeyPatch) -> None:
    from commands import dashboard as dash

    dash.reset_transfer_plan_state()
    captured: dict[str, object] = {}

    def fake_start(**kwargs: object) -> tuple[int, dict[str, object]]:
        captured.update(kwargs)
        return 202, {"status": "running", "error": None, "detail": "Starting…"}

    monkeypatch.setattr(dash, "start_transfer_plan", fake_start)
    monkeypatch.setattr(dash, "_transfer_plan_args", lambda _body: (5, 6, {"use_wc": []}, []))
    status, payload = dash.handle_dashboard_api("POST", "/api/transfer-plan", {"horizon": 6})
    assert status == 202
    assert captured["target_gw"] == 5
    assert captured["horizon"] == 6
    get_status, get_payload = dash.handle_dashboard_api("GET", "/api/transfer-plan", None)
    assert get_status == 200
    assert "status" in get_payload


def test_refresh_marks_scenarios_stale_without_deleting(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from commands import dashboard as dash
    from commands.transfer_plan_scenarios import build_scenarios_payload, write_scenarios_payload
    from solver.scenarios import ARM_ROLL

    path = tmp_path / "transfer_plan_scenarios.json"
    write_scenarios_payload(
        path,
        build_scenarios_payload(
            rows=[{
                "id": ARM_ROLL,
                "name": "Roll",
                "horizon_egs": 1.0,
                "solver_objective": 1.0,
                "plan": {"meta": {}, "weeks": []},
            }],
            arms=(ARM_ROLL,),
            target_gw=1,
            horizon=1,
            free_transfers=0,
            status="ok",
        ),
    )
    monkeypatch.setattr(dash, "SCENARIOS_PATH", path)
    monkeypatch.setattr("commands.transfer_plan_scenarios.SCENARIOS_PATH", path)
    # mark_scenarios_stale imports path arg — run_refresh uses dash.SCENARIOS_PATH
    monkeypatch.setattr(dash, "ingest_live_data", lambda: None)
    monkeypatch.setattr(dash, "run_dashboard_export", lambda **_k: None)
    dash.reset_refresh_state()
    dash.reset_dream_team_state()
    dash.reset_transfer_plan_state()
    dash.run_refresh_job(model_name="linear_baseline", horizon=1, model_names=["linear_baseline"])
    assert path.exists()
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["meta"]["stale"] is True
    assert dash.transfer_plan_status()["payload"]["meta"]["stale"] is True


def test_refresh_conflicts_with_running_transfer_plan() -> None:
    from commands import dashboard as dash

    dash.reset_refresh_state()
    dash.reset_dream_team_state()
    dash.reset_transfer_plan_state()
    dash._set_plan_state(status="running", detail="Solving…")
    status, payload = dash.handle_dashboard_api("POST", "/api/refresh", {"model": "linear_baseline"})
    assert status == 409
    assert "Transfer Plan" in str(payload["error"])
    dash.reset_transfer_plan_state()


def test_transfer_plan_conflicts_with_running_refresh() -> None:
    from commands import dashboard as dash

    dash.reset_refresh_state()
    dash.reset_dream_team_state()
    dash.reset_transfer_plan_state()
    dash._set_refresh_state(status="running", detail="Ingesting…")
    status, payload = dash.handle_dashboard_api("POST", "/api/transfer-plan", {"horizon": 6})
    assert status == 409
    assert "Refresh" in str(payload["error"])
    dash.reset_refresh_state()


def test_execute_scenarios_rejects_spent_booked_chip(tmp_path: Path) -> None:
    processed = tmp_path / "processed"
    _squad(processed)
    pd.DataFrame([
        {"chip": "wildcard", "status": "played", "chip_set": 1},
        {"chip": "bboost", "status": "available", "chip_set": 1},
        {"chip": "freehit", "status": "available", "chip_set": 1},
        {"chip": "3xc", "status": "available", "chip_set": 1},
    ]).to_parquet(processed / "user_chips.parquet")
    with pytest.raises(ValueError, match="not an Available Chip"):
        execute_transfer_plan_scenarios(
            processed_dir=processed,
            target_gw=5,
            horizon=1,
            dataset={"players": []},
            booked_chips={"use_wc": [5], "use_bb": [], "use_fh": [], "use_tc": []},
            execute_plan=lambda *_a, **_k: {"meta": {}, "weeks": []},
            scenarios_path=tmp_path / "scenarios.json",
            solution_path=tmp_path / "solution.json",
        )
