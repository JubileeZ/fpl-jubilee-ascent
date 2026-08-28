import json
from pathlib import Path
import pandas as pd

from commands.export_dashboard import (
    build_dashboard_dataset,
    export_dashboard_data,
    resolve_horizon_start,
)


def test_build_dashboard_dataset(tmp_path: Path):
    processed_dir = tmp_path / "data" / "processed"
    processed_dir.mkdir(parents=True)

    # 1. Create mock players parquet
    players_df = pd.DataFrame([
        {
            "id": 1,
            "code": 101,
            "first_name": "Erling",
            "second_name": "Haaland",
            "web_name": "Haaland",
            "club_id": 1,
            "position_id": 4,  # FWD
            "now_cost": 150,
            "status": "a",
            "chance_of_playing_next_round": 100,
            "news": "",
            "total_points": 200,
            "minutes": 1800,
            "starts": 20,
            "ict_index": "250.0",
            "influence": "100.0",
            "creativity": "50.0",
            "threat": "100.0",
            "expected_goals": "15.0",
            "expected_assists": "5.0",
            "selected_by_percent": 12.5,
        },
        {
            "id": 2,
            "code": 102,
            "first_name": "Mohamed",
            "second_name": "Salah",
            "web_name": "Salah",
            "club_id": 2,
            "position_id": 3,  # MID
            "now_cost": 125,
            "status": "a",
            "chance_of_playing_next_round": 100,
            "news": "",
            "total_points": 180,
            "minutes": 1620,
            "starts": 18,
            "ict_index": "220.0",
            "influence": "90.0",
            "creativity": "80.0",
            "threat": "50.0",
            "expected_goals": "12.0",
            "expected_assists": "8.0",
        },
    ])
    players_df.to_parquet(processed_dir / "players.parquet")

    # 2. Create mock clubs parquet
    clubs_df = pd.DataFrame([
        {"id": 1, "name": "Manchester City", "short_name": "MCI"},
        {"id": 2, "name": "Liverpool", "short_name": "LIV"},
    ])
    clubs_df.to_parquet(processed_dir / "clubs.parquet")

    # 3. Create mock gameweeks parquet
    gameweeks_df = pd.DataFrame([
        {"id": 1, "name": "Gameweek 1", "is_next": True, "finished": False},
        {"id": 2, "name": "Gameweek 2", "is_next": False, "finished": False},
    ])
    gameweeks_df.to_parquet(processed_dir / "gameweeks.parquet")

    # Mock predictions DataFrame
    predictions_df = pd.DataFrame([
        {
            "player_id": 1,
            "gameweek_id": 1,
            "projected_points": 7.5,
            "projected_minutes": 85.0,
            "xp_goals": 1.0,  # FWD goal = 4 pts
            "xp_assists": 0.5, # 1.5 pts
            "xp_clean_sheet": 0.0,
            "xp_defcon": 0.0,
            "xp_bonus": 1.0,
        },
        {
            "player_id": 2,
            "gameweek_id": 1,
            "projected_points": 8.0,
            "projected_minutes": 90.0,
            "xp_goals": 0.8,  # MID goal = 5 pts -> 4.0 pts
            "xp_assists": 0.6, # 1.8 pts
            "xp_clean_sheet": 0.4, # MID CS = 1 pt -> 0.4 pts
            "xp_defcon": 0.0,
            "xp_bonus": 1.2,
        },
    ])

    dataset = build_dashboard_dataset(
        processed_dir=processed_dir,
        predictions_df=predictions_df,
        target_gw=1,
        horizon=1,
    )

    assert "players" in dataset
    assert "meta" in dataset
    assert len(dataset["players"]) == 2

    haaland = next(p for p in dataset["players"] if p["id"] == 1)
    assert haaland["name"] == "Haaland"
    assert haaland["team"] == "MCI"
    assert haaland["price"] == 15.0
    assert haaland["pts_per_start"] == 10.0  # 200 / 20
    assert haaland["pts_per_90"] == 10.0     # (200 / 1800) * 90
    assert "projections" in haaland
    assert "gw1" in haaland["projections"]
    assert "models" in haaland
    gw1 = haaland["projections"]["gw1"]
    assert gw1["xg_pts"] == 4.0  # 1.0 * 4
    assert gw1["xa_pts"] == 1.5  # 0.5 * 3
    assert gw1["total_xp"] == 7.5
    assert haaland["ownership_pct"] == 12.5
    assert dataset["meta"]["planning_gw_ids"] == [1]
    slice_h = haaland["explorer"]["planning_horizon"]
    assert slice_h["n_gameweeks"] == 1
    assert slice_h["total"] == 7.5
    assert slice_h["xp_goals"] == 1.0
    assert any(c["chip"] == "wc" and c["chip_set"] == 1 for c in dataset["meta"]["available_chips"])


def test_explorer_full_season_includes_gws_outside_planning_horizon(tmp_path: Path) -> None:
    processed_dir = tmp_path / "data" / "processed"
    processed_dir.mkdir(parents=True)
    pd.DataFrame([{
        "id": 1, "code": 101, "first_name": "Erling", "second_name": "Haaland",
        "web_name": "Haaland", "club_id": 1, "position_id": 4, "now_cost": 150,
        "status": "a", "chance_of_playing_next_round": 100, "news": "",
        "total_points": 0, "minutes": 0, "starts": 0, "ict_index": "0",
        "influence": "0", "creativity": "0", "threat": "0",
        "expected_goals": "0", "expected_assists": "0", "selected_by_percent": 40.0,
    }]).to_parquet(processed_dir / "players.parquet")
    pd.DataFrame([{"id": 1, "name": "Manchester City", "short_name": "MCI"}]).to_parquet(
        processed_dir / "clubs.parquet"
    )
    pd.DataFrame([
        {"id": 1, "name": "Gameweek 1", "is_next": True, "finished": False},
        {"id": 2, "name": "Gameweek 2", "is_next": False, "finished": False},
    ]).to_parquet(processed_dir / "gameweeks.parquet")
    predictions = pd.DataFrame([
        {
            "player_id": 1, "gameweek_id": 1, "projected_points": 7.5, "projected_minutes": 85.0,
            "xp_goals": 1.0, "xp_assists": 0.5, "xp_clean_sheet": 0.0, "xp_defcon": 0.0,
            "xp_bonus": 1.0, "xp_minutes": 2.0, "xp_conceded": 0.0, "xp_saves": 0.0,
        },
        {
            "player_id": 1, "gameweek_id": 2, "projected_points": 3.0, "projected_minutes": 70.0,
            "xp_goals": 0.0, "xp_assists": 0.0, "xp_clean_sheet": 0.0, "xp_defcon": 0.0,
            "xp_bonus": 0.0, "xp_minutes": 2.0, "xp_conceded": 0.0, "xp_saves": 0.0,
        },
    ])
    dataset = build_dashboard_dataset(
        processed_dir=processed_dir,
        predictions_df=predictions,
        target_gw=1,
        horizon=1,
    )
    haaland = dataset["players"][0]
    assert dataset["meta"]["planning_gw_ids"] == [1]
    assert haaland["total_xp_horizon"] == 7.5
    assert haaland["explorer"]["planning_horizon"]["total"] == 7.5
    assert haaland["projections"]["gw2"]["total_xp"] == 3.0
    clamped = build_dashboard_dataset(
        processed_dir=processed_dir,
        predictions_df=predictions,
        target_gw=1,
        horizon=7,
    )
    assert clamped["meta"]["horizon"] == 6
    assert clamped["meta"]["planning_gw_ids"] == [1, 2, 3, 4, 5, 6]
    assert clamped["meta"]["horizon_start"] == 1
    assert clamped["meta"]["horizon_end"] == 6
    assert clamped["meta"]["unfinished_gameweeks"][:6] == [1, 2, 3, 4, 5, 6]


def test_realized_slice_appears_after_finished_gameweek(tmp_path: Path) -> None:
    processed_dir = tmp_path / "data" / "processed"
    processed_dir.mkdir(parents=True)
    pd.DataFrame([{
        "id": 1, "code": 101, "first_name": "Erling", "second_name": "Haaland",
        "web_name": "Haaland", "club_id": 1, "position_id": 4, "now_cost": 150,
        "status": "a", "chance_of_playing_next_round": 100, "news": "",
        "total_points": 8, "minutes": 90, "starts": 1, "ict_index": "0",
        "influence": "0", "creativity": "0", "threat": "0",
        "expected_goals": "0", "expected_assists": "0", "selected_by_percent": 40.0,
    }]).to_parquet(processed_dir / "players.parquet")
    pd.DataFrame([{"id": 1, "name": "Manchester City", "short_name": "MCI"}]).to_parquet(
        processed_dir / "clubs.parquet"
    )
    pd.DataFrame([
        {"id": 1, "name": "Gameweek 1", "is_next": False, "finished": True},
        {"id": 2, "name": "Gameweek 2", "is_next": True, "finished": False},
    ]).to_parquet(processed_dir / "gameweeks.parquet")
    pd.DataFrame([{
        "player_id": 1, "fixture_id": 10, "gameweek_id": 1, "minutes": 90, "total_points": 8,
        "goals_scored": 1, "assists": 0, "clean_sheets": 0, "goals_conceded": 2,
        "saves": 0, "bonus": 2, "defensive_contribution": 0,
    }]).to_parquet(processed_dir / "player_performances.parquet")
    predictions = pd.DataFrame([{
        "player_id": 1, "gameweek_id": 2, "projected_points": 6.0, "projected_minutes": 90.0,
        "xp_goals": 1.0, "xp_assists": 0.0, "xp_clean_sheet": 0.0, "xp_defcon": 0.0, "xp_bonus": 0.0,
    }])
    dataset = build_dashboard_dataset(
        processed_dir=processed_dir,
        predictions_df=predictions,
        target_gw=2,
        horizon=1,
    )
    slice_h = dataset["players"][0]["explorer"]["planning_horizon"]
    assert slice_h["total"] == 6.0
    assert slice_h["n_gameweeks"] == 1
    assert 1 not in dataset["meta"]["planning_gw_ids"]
    assert dataset["meta"]["planning_gw_ids"] == [2]
    assert dataset["meta"]["horizon_start"] == 2
    assert 1 not in dataset["meta"]["unfinished_gameweeks"]


def test_build_dashboard_dataset_multi_model(tmp_path: Path):
    processed_dir = tmp_path / "data" / "processed"
    processed_dir.mkdir(parents=True)

    players_df = pd.DataFrame([{
        "id": 1, "code": 101, "first_name": "Erling", "second_name": "Haaland",
        "web_name": "Haaland", "club_id": 1, "position_id": 4, "now_cost": 150,
        "status": "a", "chance_of_playing_next_round": 100, "news": "",
        "total_points": 100, "minutes": 900, "starts": 10, "ict_index": "100.0",
        "influence": "50.0", "creativity": "25.0", "threat": "50.0",
        "expected_goals": "8.0", "expected_assists": "2.0",
    }])
    players_df.to_parquet(processed_dir / "players.parquet")
    clubs_df = pd.DataFrame([{"id": 1, "name": "Manchester City", "short_name": "MCI"}])
    clubs_df.to_parquet(processed_dir / "clubs.parquet")
    gameweeks_df = pd.DataFrame([{"id": 1, "name": "Gameweek 1", "is_next": True, "finished": False}])
    gameweeks_df.to_parquet(processed_dir / "gameweeks.parquet")

    pred_m1 = pd.DataFrame([{
        "player_id": 1, "gameweek_id": 1, "projected_points": 7.5, "projected_minutes": 90.0,
        "xp_goals": 1.0, "xp_assists": 0.5, "xp_clean_sheet": 0.0, "xp_defcon": 0.0, "xp_bonus": 1.0,
    }])
    pred_m2 = pd.DataFrame([{
        "player_id": 1, "gameweek_id": 1, "projected_points": 5.0, "projected_minutes": 80.0,
        "xp_goals": 0.5, "xp_assists": 0.2, "xp_clean_sheet": 0.0, "xp_defcon": 0.0, "xp_bonus": 0.5,
    }])

    dataset = build_dashboard_dataset(
        processed_dir=processed_dir,
        predictions_df={"model_a": pred_m1, "model_b": pred_m2},
        target_gw=1,
        horizon=1,
        default_model_name="model_a",
    )

    assert dataset["meta"]["models"] == ["model_a", "model_b"]
    assert dataset["meta"]["default_model"] == "model_a"

    haaland = dataset["players"][0]
    assert "models" in haaland
    assert "model_a" in haaland["models"]
    assert "model_b" in haaland["models"]
    assert haaland["models"]["model_a"]["total_xp_horizon"] == 7.5
    assert haaland["models"]["model_b"]["total_xp_horizon"] == 5.0


def test_horizon_start_is_earliest_unfinished_not_is_next(tmp_path: Path) -> None:
    processed_dir = tmp_path / "data" / "processed"
    processed_dir.mkdir(parents=True)
    pd.DataFrame([{
        "id": 1, "code": 101, "first_name": "Erling", "second_name": "Haaland",
        "web_name": "Haaland", "club_id": 1, "position_id": 4, "now_cost": 150,
        "status": "a", "chance_of_playing_next_round": 100, "news": "",
        "total_points": 0, "minutes": 0, "starts": 0, "ict_index": "0",
        "influence": "0", "creativity": "0", "threat": "0",
        "expected_goals": "0", "expected_assists": "0", "selected_by_percent": 40.0,
    }]).to_parquet(processed_dir / "players.parquet")
    pd.DataFrame([{"id": 1, "name": "Manchester City", "short_name": "MCI"}]).to_parquet(
        processed_dir / "clubs.parquet"
    )
    pd.DataFrame([
        {"id": 1, "name": "Gameweek 1", "is_next": False, "finished": True},
        {"id": 2, "name": "Gameweek 2", "is_next": False, "finished": False},
        {"id": 3, "name": "Gameweek 3", "is_next": True, "finished": False},
    ]).to_parquet(processed_dir / "gameweeks.parquet")
    predictions = pd.DataFrame([
        {
            "player_id": 1, "gameweek_id": 2, "projected_points": 6.0, "projected_minutes": 90.0,
            "xp_goals": 1.0, "xp_assists": 0.0, "xp_clean_sheet": 0.0, "xp_defcon": 0.0, "xp_bonus": 0.0,
        },
        {
            "player_id": 1, "gameweek_id": 3, "projected_points": 5.0, "projected_minutes": 90.0,
            "xp_goals": 0.8, "xp_assists": 0.0, "xp_clean_sheet": 0.0, "xp_defcon": 0.0, "xp_bonus": 0.0,
        },
    ])
    assert resolve_horizon_start(processed_dir) == 2
    dataset = build_dashboard_dataset(
        processed_dir, predictions, target_gw=resolve_horizon_start(processed_dir), horizon=6
    )
    assert dataset["meta"]["horizon_start"] == 2
    assert dataset["meta"]["planning_gw_ids"] == [2, 3, 4, 5, 6, 7]
    assert dataset["meta"]["horizon_end"] == 7
    snapped = build_dashboard_dataset(processed_dir, predictions, target_gw=1, horizon=6)
    assert snapped["meta"]["horizon_start"] == 2
    kept = build_dashboard_dataset(processed_dir, predictions, target_gw=3, horizon=6)
    assert kept["meta"]["horizon_start"] == 3


def test_export_dashboard_data_writes_json(tmp_path: Path):
    output_path = tmp_path / "dashboard_data.json"
    dummy_data = {"meta": {"target_gw": 1}, "players": []}
    export_dashboard_data(dummy_data, output_path)

    assert output_path.exists()
    with open(output_path, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded["meta"]["target_gw"] == 1


def test_build_dashboard_dataset_omits_transfer_plan(tmp_path: Path) -> None:
    processed_dir = tmp_path / "data" / "processed"
    processed_dir.mkdir(parents=True)
    pd.DataFrame([{
        "id": 10, "code": 101, "first_name": "Erling", "second_name": "Haaland",
        "web_name": "Haaland", "club_id": 1, "position_id": 4, "now_cost": 150,
        "status": "a", "chance_of_playing_next_round": 100, "news": "",
        "total_points": 0, "minutes": 0, "starts": 0, "ict_index": "0",
        "influence": "0", "creativity": "0", "threat": "0",
        "expected_goals": "0", "expected_assists": "0", "selected_by_percent": 0,
    }]).to_parquet(processed_dir / "players.parquet")
    pd.DataFrame([{"id": 1, "name": "Manchester City", "short_name": "MCI"}]).to_parquet(
        processed_dir / "clubs.parquet"
    )
    pd.DataFrame([{"id": 1, "name": "Gameweek 1", "is_next": True, "finished": False}]).to_parquet(
        processed_dir / "gameweeks.parquet"
    )
    plan = {
        "meta": {"champion": "participation_state_hybrid", "horizon": 6, "next_gw": 1},
        "weeks": [{"gw": 1, "chip": "BB", "squad_ids": [10], "lineup_ids": [10], "bench_ids": [], "buy": [], "sell": []}],
        "summary": "",
    }
    sol_path = tmp_path / "solution.json"
    sol_path.write_text(json.dumps(plan), encoding="utf-8")
    predictions = pd.DataFrame([{
        "player_id": 10, "gameweek_id": 1, "projected_points": 8.0, "projected_minutes": 90.0,
        "xp_goals": 1.0, "xp_assists": 0.0, "xp_clean_sheet": 0.0, "xp_defcon": 0.0, "xp_bonus": 0.0,
    }])
    dataset = build_dashboard_dataset(
        processed_dir, predictions, target_gw=1, horizon=6, solution_path=sol_path
    )
    assert "transfer_plan" not in dataset
    assert "solution_model_name" not in dataset["meta"]
    assert "prefilled_squad_ids" not in dataset["meta"]


def test_build_dashboard_dataset_embeds_owned_squad_from_user_picks(tmp_path: Path) -> None:
    processed_dir = tmp_path / "data" / "processed"
    processed_dir.mkdir(parents=True)
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
            "web_name": "Mbeumo", "club_id": 1, "position_id": 3, "now_cost": 80,
            "status": "a", "chance_of_playing_next_round": 100, "news": "",
            "total_points": 0, "minutes": 0, "starts": 0, "ict_index": "0",
            "influence": "0", "creativity": "0", "threat": "0",
            "expected_goals": "0", "expected_assists": "0", "selected_by_percent": 0,
        },
    ]).to_parquet(processed_dir / "players.parquet")
    pd.DataFrame([{"id": 1, "name": "Manchester City", "short_name": "MCI"}]).to_parquet(
        processed_dir / "clubs.parquet"
    )
    pd.DataFrame([{"id": 1, "name": "Gameweek 1", "is_next": True, "finished": False}]).to_parquet(
        processed_dir / "gameweeks.parquet"
    )
    pd.DataFrame([
        {"entry_id": 1, "gameweek_id": 1, "player_id": 20, "lineup_index": 7,
         "multiplier": 2, "is_captain": True, "is_vice_captain": False},
        {"entry_id": 1, "gameweek_id": 1, "player_id": 10, "lineup_index": 1,
         "multiplier": 1, "is_captain": False, "is_vice_captain": True},
    ]).to_parquet(processed_dir / "user_picks.parquet")
    sol_path = tmp_path / "solution.json"
    sol_path.write_text(json.dumps({
        "meta": {"champion": "participation_state_hybrid"},
        "weeks": [{"gw": 1, "chip": None, "squad_ids": [99], "lineup_ids": [99], "bench_ids": [], "buy": [], "sell": []}],
    }), encoding="utf-8")
    predictions = pd.DataFrame([
        {"player_id": 10, "gameweek_id": 1, "projected_points": 8.0, "projected_minutes": 90.0,
         "xp_goals": 1.0, "xp_assists": 0.0, "xp_clean_sheet": 0.0, "xp_defcon": 0.0, "xp_bonus": 0.0},
        {"player_id": 20, "gameweek_id": 1, "projected_points": 6.0, "projected_minutes": 90.0,
         "xp_goals": 0.5, "xp_assists": 0.4, "xp_clean_sheet": 0.0, "xp_defcon": 0.0, "xp_bonus": 0.0},
    ])
    dataset = build_dashboard_dataset(
        processed_dir, predictions, target_gw=1, horizon=5, solution_path=sol_path
    )
    assert dataset["meta"]["owned_squad_ids"] == [10, 20]
    assert dataset["meta"]["owned_captain_id"] == 20
    assert dataset["meta"]["owned_vice_captain_id"] == 10
    assert "prefilled_squad_ids" not in dataset["meta"]


def test_ingest_live_data_passes_keep_roles_when_table_missing(monkeypatch) -> None:
    captured: list[list[str]] = []

    async def fake_main(argv=None) -> None:
        captured.append(list(argv or []))

    monkeypatch.setattr("commands.dashboard.table_season_status", lambda *_args, **_kwargs: "missing")
    monkeypatch.setattr("commands.refresh_data.main", fake_main)
    from commands.dashboard import ingest_live_data
    ingest_live_data("2026-27")
    assert captured[0][:2] == ["--season", "2026-27"]
    assert "--keep-roles" in captured[0]
    assert "--rebuild-roles" not in captured[0]


def test_ingest_live_data_skips_keep_roles_when_table_ok(monkeypatch) -> None:
    captured: list[list[str]] = []

    async def fake_main(argv=None) -> None:
        captured.append(list(argv or []))

    monkeypatch.setattr("commands.dashboard.table_season_status", lambda *_args, **_kwargs: "ok")
    monkeypatch.setattr("commands.refresh_data.main", fake_main)
    from commands.dashboard import ingest_live_data
    ingest_live_data("2026-27")
    assert "--keep-roles" not in captured[0]
    assert "--rebuild-roles" not in captured[0]


def test_run_refresh_job_ok_and_project_refuse(monkeypatch) -> None:
    from commands.dashboard import refresh_status, reset_refresh_state, run_refresh_job

    reset_refresh_state()
    monkeypatch.setattr("commands.dashboard.ingest_live_data", lambda: None)
    monkeypatch.setattr("commands.dashboard.run_dashboard_export", lambda **_kwargs: None)
    run_refresh_job()
    assert refresh_status()["status"] == "ok"

    reset_refresh_state()

    def boom(**_kwargs):
        raise ValueError("Expected Role Table missing")

    monkeypatch.setattr("commands.dashboard.run_dashboard_export", boom)
    run_refresh_job()
    assert refresh_status()["status"] == "error"
    assert "Expected Role Table" in str(refresh_status()["error"])

