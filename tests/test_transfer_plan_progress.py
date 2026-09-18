"""Progressive / parallel Transfer Plan Scenarios + stale after Refresh."""

from __future__ import annotations

import json
import threading
from pathlib import Path

import pandas as pd

from commands.transfer_plan_scenarios import (
    build_scenarios_payload,
    execute_transfer_plan_scenarios,
    mark_scenarios_stale,
    serial_arm_options,
)
from solver.scenarios import ARM_ONE_FT, ARM_OPTIMAL, ARM_ROLL


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
        {"entry_id": 1, "bank": 5, "value": 1000, "free_transfers": 1, "active_chip": None},
    ]).to_parquet(processed_dir / "user_state.parquet")


def test_serial_arm_options_force_single_thread_highs() -> None:
    opts = serial_arm_options({"parallel": "on", "threads": 8, "horizon": 3})
    assert opts["parallel"] == "off"
    assert opts["threads"] == 1
    assert opts["horizon"] == 3


def test_mark_scenarios_stale_keeps_cards(tmp_path: Path) -> None:
    path = tmp_path / "scenarios.json"
    payload = build_scenarios_payload(
        rows=[{
            "id": ARM_ROLL,
            "name": "Roll",
            "horizon_egs": 10.0,
            "solver_objective": 1.0,
            "plan": {"meta": {}, "weeks": []},
        }],
        arms=(ARM_ROLL, ARM_OPTIMAL),
        target_gw=5,
        horizon=1,
        free_transfers=0,
        status="ok",
        stale=False,
    )
    path.write_text(json.dumps(payload), encoding="utf-8")
    stale = mark_scenarios_stale(path)
    assert stale is not None
    assert stale["meta"]["stale"] is True
    assert stale["scenarios"][0]["id"] == ARM_ROLL
    reloaded = json.loads(path.read_text(encoding="utf-8"))
    assert reloaded["meta"]["stale"] is True


def test_execute_scenarios_progress_and_parallel_finish(tmp_path: Path) -> None:
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
    progress: list[dict] = []
    barrier = threading.Barrier(3)

    def fake_execute(options: dict, **kwargs: object) -> dict:
        assert options.get("parallel") == "off"
        assert options.get("threads") == 1
        barrier.wait(timeout=2.0)
        hits = 0 if options.get("no_transfer_gws") else (0 if options.get("num_transfers") == 1 else 1)
        return {
            "meta": {"solver_objective": 10.0, "next_gw": 5, "horizon": 1},
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

    scenarios_path = tmp_path / "scenarios.json"
    payload = execute_transfer_plan_scenarios(
        processed_dir=processed,
        target_gw=5,
        horizon=1,
        dataset=dataset,
        execute_plan=fake_execute,
        scenarios_path=scenarios_path,
        solution_path=tmp_path / "solution.json",
        on_progress=progress.append,
    )
    assert payload["meta"]["status"] == "ok"
    assert payload["meta"]["stale"] is False
    assert set(payload["meta"]["arms"]) == {ARM_ROLL, ARM_ONE_FT, ARM_OPTIMAL}
    assert payload["meta"]["pending_arms"] == []
    assert len(payload["scenarios"]) == 3
    assert any(p["meta"]["status"] == "running" for p in progress)
    assert progress[-1]["meta"]["status"] == "ok"
    disk = json.loads(scenarios_path.read_text(encoding="utf-8"))
    assert disk["meta"]["status"] == "ok"
