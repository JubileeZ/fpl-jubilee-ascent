"""Dream Team budget, solver options, execute, and dashboard API (ADR 0028)."""

from __future__ import annotations

from pathlib import Path

from unittest.mock import patch

import pandas as pd
import pytest

from commands.dream_team import (
    GREENFIELD_BUDGET_M,
    dream_team_bank_tenths,
    dream_team_budget_m,
    dream_team_my_data,
    dream_team_options,
    execute_dream_team,
)


def _write_squad(processed_dir: Path) -> None:
    processed_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([
        {
            "id": 10, "code": 101, "first_name": "Erling", "second_name": "Haaland",
            "web_name": "Haaland", "club_id": 1, "position_id": 4, "now_cost": 150,
            "status": "a", "chance_of_playing_next_round": 100, "news": "",
            "total_points": 0, "minutes": 0, "starts": 0, "ict_index": "0",
            "influence": "0", "creativity": "0", "threat": "0",
            "expected_goals": "0", "expected_assists": "0", "selected_by_percent": 0,
        },
        {
            "id": 20, "code": 202, "first_name": "Bryan", "second_name": "Mbeumo",
            "web_name": "Mbeumo", "club_id": 2, "position_id": 3, "now_cost": 80,
            "status": "a", "chance_of_playing_next_round": 100, "news": "",
            "total_points": 0, "minutes": 0, "starts": 0, "ict_index": "0",
            "influence": "0", "creativity": "0", "threat": "0",
            "expected_goals": "0", "expected_assists": "0", "selected_by_percent": 0,
        },
    ]).to_parquet(processed_dir / "players.parquet")
    pd.DataFrame([
        {"entry_id": 1, "gameweek_id": 1, "player_id": 10, "lineup_index": 11,
         "multiplier": 1, "is_captain": False, "is_vice_captain": True,
         "purchase_price": 145, "selling_price": 146},
        {"entry_id": 1, "gameweek_id": 1, "player_id": 20, "lineup_index": 7,
         "multiplier": 2, "is_captain": True, "is_vice_captain": False,
         "purchase_price": 80, "selling_price": 80},
    ]).to_parquet(processed_dir / "user_picks.parquet")
    pd.DataFrame([
        {"entry_id": 1, "bank": 5, "value": 1000, "free_transfers": 2, "active_chip": None},
    ]).to_parquet(processed_dir / "user_state.parquet")


def test_dream_team_budget_is_itb_plus_selling_prices(tmp_path: Path) -> None:
    processed_dir = tmp_path / "processed"
    _write_squad(processed_dir)
    assert dream_team_budget_m(processed_dir) == 23.1
    assert dream_team_bank_tenths(processed_dir) == 231


def test_dream_team_budget_is_100_without_user_squad(tmp_path: Path) -> None:
    processed_dir = tmp_path / "processed"
    processed_dir.mkdir()
    assert dream_team_budget_m(processed_dir) == GREENFIELD_BUDGET_M
    assert dream_team_bank_tenths(processed_dir) == 1000


def test_dream_team_options_are_frozen_unconstrained_rebuild() -> None:
    options = dream_team_options("dual_vector_state_hybrid", target_gw=3, horizon=5)
    assert options["datasource"] == "dual_vector_state_hybrid"
    assert options["horizon"] == 5
    assert options["xmin_lb"] == 0
    assert options["keep_top_ev_percent"] == 100
    assert options["preseason"] is False
    assert options["no_trs_except_wc"] is True
    assert options["use_wc"] == [3]
    assert options["use_bb"] == []
    assert options["use_fh"] == []
    assert options["use_tc"] == []
    assert options["keep"] == []
    assert options["banned"] == []
    assert options["locked"] == []
    assert options["force_keep_gws"] == []
    assert options["force_ban_gws"] == []
    assert options["enabled_chip_windows"] == []
    assert options["chip_limits"]["wc"] == 1
    assert options["secs"] == 90


def test_dream_team_my_data_is_empty_picks_with_current_bank(tmp_path: Path) -> None:
    processed_dir = tmp_path / "processed"
    _write_squad(processed_dir)
    my_data = dream_team_my_data(processed_dir)
    assert my_data["picks"] == []
    assert my_data["chips"] == []
    assert my_data["transfers"]["bank"] == 231
    assert my_data["transfers"]["limit"] is None
    assert my_data["transfers"]["made"] == 0


def _mock_solution(player_ids: list[int], leftover: float) -> dict:
    rows = [
        {
            "id": pid, "week": 1, "name": f"P{pid}", "pos": "MID", "type": 3, "team": "MCI",
            "squad": 1, "lineup": 1 if i < 11 else 0, "bench": -1 if i < 11 else i - 11,
            "captain": 1 if i == 0 else 0, "vicecaptain": 1 if i == 1 else 0,
            "transfer_in": 1, "transfer_out": 0, "chip": "WC", "ft": 1, "transfer_count": 15,
            "xp_cont": 5.0, "xP": 5.0,
        }
        for i, pid in enumerate(player_ids)
    ]
    return {
        "picks": pd.DataFrame(rows),
        "total_xp": 50.0,
        "score": 48.0,
        "statistics": {1: {"itb": leftover, "ft": 1, "pt": 0, "nt": 15, "xP": 50.0, "obj": 48.0, "chip": "WC"}},
        "summary": "dream",
    }


def test_execute_dream_team_returns_week1_ids_and_skips_dashboard_json(tmp_path: Path) -> None:
    processed_dir = tmp_path / "processed"
    _write_squad(processed_dir)
    ids = list(range(1, 16))
    json_path = tmp_path / "dashboard" / "dashboard_data.json"
    json_path.parent.mkdir()
    with patch("commands.dream_team.pad_solver_csv_horizon"), patch(
        "commands.dream_team.prep_data", return_value={}
    ), patch(
        "commands.dream_team.solve_multi_period_fpl",
        return_value=[_mock_solution(ids, 0.4)],
    ):
        result = execute_dream_team(
            processed_dir,
            model_name="dual_vector_state_hybrid",
            target_gw=1,
            horizon=5,
        )
    assert result["player_ids"] == ids
    assert result["budget"] == 23.1
    assert result["leftover"] == 0.4
    assert result["model"] == "dual_vector_state_hybrid"
    assert result["horizon_start"] == 1
    assert result["horizon"] == 5
    assert not json_path.exists()


def test_run_dream_team_job_ok_and_error(monkeypatch: pytest.MonkeyPatch) -> None:
    from commands import dashboard as dash

    dash.reset_dream_team_state()
    monkeypatch.setattr(
        "commands.dashboard.execute_dream_team",
        lambda _processed, **_kwargs: {
            "player_ids": list(range(1, 16)),
            "budget": 100.0,
            "leftover": 1.5,
            "model": "dual_vector_state_hybrid",
            "horizon_start": 1,
            "horizon": 5,
        },
    )
    dash.run_dream_team_job(model_name="dual_vector_state_hybrid", target_gw=1, horizon=5)
    state = dash.dream_team_status()
    assert state["status"] == "ok"
    assert state["player_ids"] == list(range(1, 16))
    assert state["budget"] == 100.0
    assert state["leftover"] == 1.5

    dash.reset_dream_team_state()

    def boom(*_args: object, **_kwargs: object) -> dict:
        raise ValueError("solve failed")

    monkeypatch.setattr("commands.dashboard.execute_dream_team", boom)
    dash.run_dream_team_job(model_name="x", target_gw=1, horizon=5)
    err = dash.dream_team_status()
    assert err["status"] == "error"
    assert "solve failed" in str(err["error"])
    assert err.get("player_ids") in (None, [])


def test_handle_dashboard_api_dream_team_post_and_get(monkeypatch: pytest.MonkeyPatch) -> None:
    from commands import dashboard as dash

    dash.reset_dream_team_state()
    captured: dict[str, object] = {}

    def fake_start(**kwargs: object) -> dict[str, object]:
        captured.update(kwargs)
        return {"status": "running", "error": None, "detail": "Starting…"}

    monkeypatch.setattr(dash, "start_dream_team", fake_start)
    status, payload = dash.handle_dashboard_api(
        "POST",
        "/api/dream-team",
        {"model": "linear_baseline", "horizon_start": 2, "horizon_end": 6},
    )
    assert status == 202
    assert payload["status"] == "running"
    assert captured["model_name"] == "linear_baseline"
    assert captured["target_gw"] == 2
    assert captured["horizon"] == 5

    monkeypatch.setattr(
        dash,
        "dream_team_status",
        lambda: {"status": "ok", "player_ids": [9], "error": None, "detail": "done"},
    )
    get_status, get_payload = dash.handle_dashboard_api("GET", "/api/dream-team", None)
    assert get_status == 200
    assert get_payload["player_ids"] == [9]

