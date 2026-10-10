import json
import threading
from pathlib import Path
from typing import Any

import pytest
from streamlit.testing.v1 import AppTest

from dashboard.planner import PlanStore, digest
from dashboard.planner_jobs import PlannerJobs
from dashboard.explorer import ExplorerSquad, compare_squads, player_slice, watchlist_rows
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


def test_dashboard_navigation_remembers_view_and_omits_transfer_planner(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    data_path = tmp_path / "dataset.json"
    data_path.write_text(json.dumps(dataset()), encoding="utf-8")
    monkeypatch.setenv("FPL_PLANNER_DATASET", str(data_path))
    monkeypatch.setenv("FPL_PLANNER_STORAGE", str(tmp_path / "storage"))
    monkeypatch.setenv("FPL_PLANNER_PROCESSED_DIR", str(tmp_path / "processed"))
    script = Path(__file__).resolve().parents[1] / "streamlit_app.py"
    app = AppTest.from_file(script, default_timeout=30).run()
    assert not app.exception
    assert app.radio(key="dashboard-page").value == "Explorer"
    assert "Transfer Planner" not in app.radio(key="dashboard-page").options
    for page in ("Research", "Model Methodology", "Explorer"):
        app.radio(key="dashboard-page").set_value(page).run()
        assert not app.exception
    app.radio(key="dashboard-page").set_value("Research").run()
    restored = AppTest.from_file(script, default_timeout=30).run()
    assert restored.radio(key="dashboard-page").value == "Research"


def test_explorer_watchlist_add_and_clear(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    data_path = tmp_path / "dataset.json"
    data_path.write_text(json.dumps(dataset()), encoding="utf-8")
    monkeypatch.setenv("FPL_PLANNER_DATASET", str(data_path))
    monkeypatch.setenv("FPL_PLANNER_STORAGE", str(tmp_path / "storage"))
    monkeypatch.setenv("FPL_PLANNER_PROCESSED_DIR", str(tmp_path / "processed"))
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "streamlit_app.py", default_timeout=30).run()
    assert not app.exception
    assert app.session_state.get("watchlist", []) == []
    app.selectbox(key="watchlist-add-select").set_value(7).run()
    app.button(key="watchlist-add-btn").click().run()
    assert not app.exception
    assert 7 in app.session_state["watchlist"]
    app.button(key="clear-watchlist").click().run()
    assert not app.exception
    assert app.session_state["watchlist"] == []


def test_explorer_player_details_and_watchlist_toggle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    data_path = tmp_path / "dataset.json"
    data_path.write_text(json.dumps(dataset()), encoding="utf-8")
    monkeypatch.setenv("FPL_PLANNER_DATASET", str(data_path))
    monkeypatch.setenv("FPL_PLANNER_STORAGE", str(tmp_path / "storage"))
    monkeypatch.setenv("FPL_PLANNER_PROCESSED_DIR", str(tmp_path / "processed"))
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "streamlit_app.py", default_timeout=30).run()
    assert not app.exception
    app.session_state["explorer-player"] = 7
    app.session_state["explorer-inspection"] = True
    app.run()
    assert not app.exception
    assert 7 not in app.session_state.get("watchlist", [])
    app.button(key="details-toggle-watchlist").click().run()
    assert 7 in app.session_state["watchlist"]
    app.button(key="details-toggle-watchlist").click().run()
    assert 7 not in app.session_state["watchlist"]


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


def test_explorer_preserves_missing_projection_and_component_values() -> None:
    player = dataset()["players"][0]
    player["projections"].pop("gw11")
    result = player_slice(player, "Champion", tuple(range(6, 12)))
    assert result["xP"] is None
    assert result["xMins / GW"] is None
    assert result["Projection"] == "Unavailable"
    player["projections"]["gw11"] = {"total_xp": 0, "xmins": 0}
    result = player_slice(player, "Champion", tuple(range(6, 12)))
    assert result["xP"] == 5
    assert result["xp_goals"] is None


def test_watchlist_rows_formatting() -> None:
    data = dataset()
    rows = watchlist_rows(data, "Champion", (6, 7), [1, 2])
    assert len(rows) == 2
    assert rows[0]["ID"] == 1
    assert rows[0]["Player"] == "Player 1"
    assert "GW6" in rows[0]
    assert "GW7" in rows[0]


def test_what_if_transfer_hits_apply_once_at_horizon_start() -> None:
    data = dataset()
    players = {player["id"]: player for player in data["players"]}
    squad = ExplorerSquad.from_dataset(data, "Champion", (6, 7))
    squad.replace(7, 16, players)
    free = compare_squads(data, "Champion", (6, 7), squad)
    data["meta"]["free_transfers"] = 0
    charged = compare_squads(data, "Champion", (6, 7), squad)
    assert charged[0]["What-If Expected"] == free[0]["What-If Expected"] - 4
    assert charged[1]["What-If Expected"] == free[1]["What-If Expected"]


def test_admin_key_gate_for_refresh(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    data_path = tmp_path / "dataset.json"
    data_path.write_text(json.dumps(dataset()), encoding="utf-8")
    monkeypatch.setenv("FPL_PLANNER_DATASET", str(data_path))
    monkeypatch.setenv("FPL_PLANNER_STORAGE", str(tmp_path / "storage"))
    monkeypatch.setenv("FPL_PLANNER_PROCESSED_DIR", str(tmp_path / "processed"))
    monkeypatch.setenv("ADMIN_KEY", "test-pass-123")
    script = Path(__file__).resolve().parents[1] / "streamlit_app.py"
    app = AppTest.from_file(script, default_timeout=30).run()
    assert not app.exception
    # Wrong key
    app.text_input(key="admin-key-input").set_value("wrong-key").run()
    assert any("Incorrect Admin Key" in msg.value for msg in app.error)
    # Correct key
    app.text_input(key="admin-key-input").set_value("test-pass-123").run()
    assert not app.error
    assert any(b.key == "btn-refresh-public" for b in app.button)


def test_explorer_player_dialog_and_close(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    data_path = tmp_path / "dataset.json"
    data_path.write_text(json.dumps(dataset()), encoding="utf-8")
    monkeypatch.setenv("FPL_PLANNER_DATASET", str(data_path))
    monkeypatch.setenv("FPL_PLANNER_STORAGE", str(tmp_path / "storage"))
    monkeypatch.setenv("FPL_PLANNER_PROCESSED_DIR", str(tmp_path / "processed"))
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "streamlit_app.py", default_timeout=30).run()
    app.session_state["explorer-player"] = 7
    app.session_state["explorer-inspection"] = True
    app.run()
    assert not app.exception
    assert len(app.get("dialog")) == 1
    app.button(key="close-explorer-details").click().run()
    assert not app.exception
    assert not app.get("dialog")
