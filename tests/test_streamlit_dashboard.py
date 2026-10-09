import json
import threading
from pathlib import Path
from typing import Any

import pytest
from streamlit.testing.v1 import AppTest

from dashboard.planner import PlanStore, digest
from dashboard.planner_jobs import PlannerJobs
from dashboard.explorer import ExplorerSquad
from test_streamlit_planner import dataset


def test_saved_draft_rejects_stale_browser_write(tmp_path: Path) -> None:
    store = PlanStore(tmp_path / "draft.json")
    original: dict[str, Any] = {"revision": 1}
    store.save(original)
    expected = digest(original)
    store.save({"revision": 2}, expected_digest=expected)
    with pytest.raises(ValueError, match="Another browser"):
        store.save({"revision": 3}, expected_digest=expected)
    assert store.load() == {"revision": 2}


def test_dashboard_navigation_remembers_view_and_keeps_planner_draft(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    data_path = tmp_path / "dataset.json"
    data_path.write_text(json.dumps(dataset()), encoding="utf-8")
    monkeypatch.setenv("FPL_PLANNER_DATASET", str(data_path))
    monkeypatch.setenv("FPL_PLANNER_STORAGE", str(tmp_path / "storage"))
    monkeypatch.setenv("FPL_PLANNER_PROCESSED_DIR", str(tmp_path / "processed"))
    script = Path(__file__).resolve().parents[1] / "streamlit_app.py"
    app = AppTest.from_file(script, default_timeout=30).run()
    assert not app.exception
    assert app.radio(key="dashboard-page").value == "Transfer Planner"
    app.button(key="player-7").click().run()
    app.button(key="sell-player").click().run()
    for page in ("Explorer", "Research", "Model Methodology"):
        app.radio(key="dashboard-page").set_value(page).run()
        assert not app.exception
    restored = AppTest.from_file(script, default_timeout=30).run()
    assert restored.radio(key="dashboard-page").value == "Model Methodology"
    restored.radio(key="dashboard-page").set_value("Transfer Planner").run()
    assert restored.session_state["planner"].week(6)["vacancies"] == [7]


def test_explorer_what_if_does_not_change_saved_transfer_draft(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    data_path = tmp_path / "dataset.json"
    data_path.write_text(json.dumps(dataset()), encoding="utf-8")
    monkeypatch.setenv("FPL_PLANNER_DATASET", str(data_path))
    monkeypatch.setenv("FPL_PLANNER_STORAGE", str(tmp_path / "storage"))
    monkeypatch.setenv("FPL_PLANNER_PROCESSED_DIR", str(tmp_path / "processed"))
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "streamlit_app.py", default_timeout=30).run()
    before = app.session_state["planner"].snapshot()
    app.radio(key="dashboard-page").set_value("Explorer").run()
    app.selectbox(key="whatif-out").set_value(7).run()
    app.selectbox(key="whatif-in").set_value(16).run()
    app.button(key="whatif-replace").click().run()
    assert not app.exception
    assert 16 in app.session_state["explorer-squad"].ids
    assert app.session_state["planner"].snapshot() == before


def test_stale_browser_cannot_overwrite_newer_transfer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    data_path = tmp_path / "dataset.json"
    data_path.write_text(json.dumps(dataset()), encoding="utf-8")
    monkeypatch.setenv("FPL_PLANNER_DATASET", str(data_path))
    monkeypatch.setenv("FPL_PLANNER_STORAGE", str(tmp_path / "storage"))
    monkeypatch.setenv("FPL_PLANNER_PROCESSED_DIR", str(tmp_path / "processed"))
    script = Path(__file__).resolve().parents[1] / "streamlit_app.py"
    older = AppTest.from_file(script, default_timeout=30).run()
    newer = AppTest.from_file(script, default_timeout=30).run()
    newer.button(key="player-7").click().run()
    newer.button(key="sell-player").click().run()
    older.button(key="player-15").click().run()
    older.button(key="bench-player").click().run()
    saved = PlanStore(tmp_path / "storage/draft.json").load()
    assert saved is not None and saved["edits"]["6"] == [{"out": 7, "in": None}]
    assert not saved["overrides"]
    assert any("Another browser" in message.value for message in older.error)
    older.button(key="reload-draft").click().run()
    assert older.session_state["planner"].week(6)["vacancies"] == [7]
    assert not older.exception


def test_all_dashboard_job_kinds_share_one_exclusive_queue(tmp_path: Path) -> None:
    first, second = PlannerJobs(tmp_path), PlannerJobs(tmp_path)
    started, release = threading.Event(), threading.Event()

    def worker(request: dict[str, Any]) -> dict[str, Any]:
        started.set()
        assert release.wait(5)
        return {"kind": request["kind"]}

    job_id = first.start({"kind": "dream_team"}, worker)
    try:
        assert started.wait(5)
        assert second.active()["id"] == job_id
        for kind in ("refresh", "solve", "strategy"):
            with pytest.raises(ValueError, match="already running"):
                second.start({"kind": kind}, lambda request: request)
    finally:
        release.set()
        first.wait(job_id, 5)
    assert second.active() is None
    assert second.latest("dream_team")["result"]["kind"] == "dream_team"


def test_what_if_legal_swap_and_selling_price_preserve_saved_ownership() -> None:
    data = dataset()
    players = {player["id"]: player for player in data["players"]}
    squad = ExplorerSquad.from_dataset(data, "Champion", tuple(range(6, 12)))
    before = list(squad.lineup)
    with pytest.raises(ValueError, match="illegal"):
        squad.swap(15, 1, players)
    assert squad.lineup == before
    squad.swap(7, 4, players)
    assert 4 in squad.lineup and 7 in squad.bench_order
    squad.replace(7, 16, players)
    assert squad.bank(players, 2) == 1.5
    assert data["meta"]["owned_squad_ids"] == list(range(1, 16))
