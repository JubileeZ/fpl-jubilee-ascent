import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from test_streamlit_planner import dataset
from dashboard.planner import Planner, PlanStore
from dashboard.planner_jobs import PlannerJobs
from dashboard.planner_service import PlannerPaths, make_solve_request


def test_player_details_sell_fill_and_reload(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    data_path = tmp_path / "dataset.json"
    data_path.write_text(json.dumps(dataset()), encoding="utf-8")
    monkeypatch.setenv("FPL_PLANNER_DATASET", str(data_path))
    monkeypatch.setenv("FPL_PLANNER_STORAGE", str(tmp_path / "storage"))
    monkeypatch.setenv("FPL_PLANNER_PROCESSED_DIR", str(tmp_path / "processed"))
    script = Path(__file__).resolve().parents[1] / "streamlit_app.py"
    app = AppTest.from_file(script, default_timeout=20).run()
    assert not app.exception
    app.button(key="player-7").click().run()
    assert any("Player 7" in heading.value for heading in app.subheader)
    app.button(key="sell-player").click().run()
    assert any("Add Defender" in button.label for button in app.button)
    app.button(key="vacancy-7").click().run()
    app.button(key="buy-16").click().run()
    assert not app.exception
    restored = AppTest.from_file(script, default_timeout=20).run()
    assert any("Player 16" in button.label for button in restored.button)
    assert not any("Player 7 ·" in button.label for button in restored.button)


def test_missing_data_explains_refresh_without_fake_players(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FPL_PLANNER_DATASET", str(tmp_path / "missing.json"))
    monkeypatch.setenv("FPL_PLANNER_STORAGE", str(tmp_path / "storage"))
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "streamlit_app.py", default_timeout=20).run()
    assert not app.exception
    assert any("Refresh" in message.value for message in app.info)
    assert not any(button.key and button.key.startswith("player-") for button in app.button)


def test_bench_captain_scenario_confirmation_and_horizon(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    data_path = tmp_path / "dataset.json"
    data = dataset()
    data["meta"]["transfer_plan_available_chips"] = [{"chip": "bb", "chip_set": 1, "gws": list(range(6, 12))}]
    data_path.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setenv("FPL_PLANNER_DATASET", str(data_path))
    monkeypatch.setenv("FPL_PLANNER_STORAGE", str(tmp_path / "storage"))
    monkeypatch.setenv("FPL_PLANNER_PROCESSED_DIR", str(tmp_path / "processed"))
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "streamlit_app.py", default_timeout=20).run()
    app.button(key="player-15").click().run()
    app.button(key="bench-player").click().run()
    assert app.session_state["planner"].week(6)["captain_id"] != 15
    app.button(key="bench-player").click().run()
    app.button(key="set-captain").click().run()
    assert app.session_state["planner"].week(6)["captain_id"] == 15
    app.selectbox(key="scenario-policy").set_value("no_hit").run()
    app.button(key="switch-scenario").click().run()
    app.button(key="cancel-reset").click().run()
    assert not app.exception
    assert app.session_state["planner"].state["scenario"] == "optimal"
    app.selectbox(key="scenario-policy").set_value("no_hit").run()
    app.button(key="switch-scenario").click().run()
    app.button(key="confirm-reset").click().run()
    assert not app.exception
    assert app.session_state["planner"].state["scenario"] == "no_hit"
    app.number_input(key="horizon-end").set_value(8).run()
    assert app.session_state["planner"].state["end"] == 8
    app.selectbox(key="chip-6").set_value("bb").run()
    assert app.session_state["planner"].week(6)["chip"] == "bb"
    assert not app.exception


def test_completed_solver_job_applies_after_browser_reopen(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    data_path = tmp_path / "dataset.json"
    data = dataset()
    data_path.write_text(json.dumps(data), encoding="utf-8")
    storage = tmp_path / "storage"
    paths = PlannerPaths(data_path, tmp_path / "processed", storage)
    planner = Planner(data)
    request = make_solve_request(planner, paths)
    plan = {"weeks": [{"gw": gw, "squad_ids": list(range(1, 16)), "buy": [], "sell": []} for gw in range(6, 12)]}
    jobs = PlannerJobs(storage / "jobs")
    job_id = jobs.start(request, lambda payload: {"plans": {"optimal": plan}, "errors": {}})
    jobs.wait(job_id, timeout=5)
    planner.state["job_id"] = job_id
    PlanStore(storage / "draft.json").save(planner.state)
    monkeypatch.setenv("FPL_PLANNER_DATASET", str(data_path))
    monkeypatch.setenv("FPL_PLANNER_STORAGE", str(storage))
    monkeypatch.setenv("FPL_PLANNER_PROCESSED_DIR", str(paths.processed))
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "streamlit_app.py", default_timeout=20).run()
    assert not app.exception
    assert app.session_state["planner"].recommendation_valid()
    assert any("Solver recommendation ready" in message.value for message in app.info)
