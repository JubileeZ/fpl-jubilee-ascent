import pandas as pd
import pytest
from pathlib import Path

from commands.export_dashboard import build_dashboard_dataset
from dashboard.explorer import player_slice


def test_underlying_actuals_calculation(tmp_path: Path):
    processed_dir = tmp_path / "data" / "processed"
    processed_dir.mkdir(parents=True)

    # 1. Mock players (1 FWD, 1 DEF, 1 MID, 1 GKP, 1 zero-min FWD)
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
            "total_points": 50,
            "minutes": 450,
            "starts": 5,
            "goals_scored": 6,
            "assists": 2,
            "clean_sheets": 2,
            "goals_conceded": 4,
            "saves": 0,
            "expected_goals": 5.50,
            "expected_assists": 1.50,
            "expected_goal_involvements": 7.00,
            "expected_goals_conceded": 4.20,
            "selected_by_percent": 60.0,
        },
        {
            "id": 2,
            "code": 102,
            "first_name": "Gabriel",
            "second_name": "Magalhaes",
            "web_name": "Gabriel",
            "club_id": 2,
            "position_id": 2,  # DEF
            "now_cost": 60,
            "status": "a",
            "total_points": 35,
            "minutes": 540,
            "starts": 6,
            "goals_scored": 1,
            "assists": 0,
            "clean_sheets": 3,
            "goals_conceded": 5,
            "saves": 0,
            "expected_goals": 0.80,
            "expected_assists": 0.20,
            "expected_goal_involvements": 1.00,
            "expected_goals_conceded": 4.80,
            "selected_by_percent": 25.0,
        },
        {
            "id": 3,
            "code": 103,
            "first_name": "David",
            "second_name": "Raya",
            "web_name": "Raya",
            "club_id": 2,
            "position_id": 1,  # GKP
            "now_cost": 55,
            "status": "a",
            "total_points": 30,
            "minutes": 540,
            "starts": 6,
            "goals_scored": 0,
            "assists": 0,
            "clean_sheets": 3,
            "goals_conceded": 5,
            "saves": 24,
            "expected_goals": 0.0,
            "expected_assists": 0.0,
            "expected_goal_involvements": 0.0,
            "expected_goals_conceded": 6.0,
            "selected_by_percent": 20.0,
        },
        {
            "id": 4,
            "code": 104,
            "first_name": "Zero",
            "second_name": "Minutes",
            "web_name": "ZeroMin",
            "club_id": 1,
            "position_id": 4,  # FWD
            "now_cost": 45,
            "status": "a",
            "total_points": 0,
            "minutes": 0,
            "starts": 0,
            "goals_scored": 0,
            "assists": 0,
            "clean_sheets": 0,
            "goals_conceded": 0,
            "saves": 0,
            "expected_goals": 0.0,
            "expected_assists": 0.0,
            "expected_goal_involvements": 0.0,
            "expected_goals_conceded": 0.0,
            "selected_by_percent": 0.1,
        },
    ])
    players_df.to_parquet(processed_dir / "players.parquet")

    # 2. Mock clubs
    clubs_df = pd.DataFrame([
        {"id": 1, "name": "Manchester City", "short_name": "MCI"},
        {"id": 2, "name": "Arsenal", "short_name": "ARS"},
    ])
    clubs_df.to_parquet(processed_dir / "clubs.parquet")

    # 3. Mock gameweeks
    gameweeks_df = pd.DataFrame([
        {"id": 1, "name": "Gameweek 1", "is_next": True, "finished": False},
    ])
    gameweeks_df.to_parquet(processed_dir / "gameweeks.parquet")

    # 4. Mock player_performances (finished past fixtures)
    # Gabriel: 6 matches. Defcon actions: [4, 10, 7, 11, 9, 5] -> 2 hits (>=10).
    # Haaland: 5 matches of 90 mins each. Defcon actions: [2, 1, 3, 2, 0] -> 0 hits (threshold 12 for FWD).
    # Raya: 6 matches. Saves: 4 per match (total 24). Defcon not applicable.
    perf_records = []
    # Haaland 5 fixtures
    for gw in range(1, 6):
        perf_records.append({
            "player_id": 1,
            "fixture_id": 100 + gw,
            "gameweek_id": gw,
            "opponent_club_id": 2,
            "was_home": True,
            "kickoff_time": "2026-09-01T15:00:00Z",
            "minutes": 90,
            "total_points": 10,
            "goals_scored": 1 if gw <= 4 else 2,
            "assists": 1 if gw <= 2 else 0,
            "clean_sheets": 1 if gw <= 2 else 0,
            "goals_conceded": 1,
            "saves": 0,
            "expected_goals": 1.10,
            "expected_assists": 0.30,
            "expected_goal_involvements": 1.40,
            "expected_goals_conceded": 0.84,
            "defensive_contribution": 2,
            "starts": 1,
        })
    # Gabriel 6 fixtures
    gabriel_defcons = [4, 10, 7, 11, 9, 5]
    for gw in range(1, 7):
        perf_records.append({
            "player_id": 2,
            "fixture_id": 200 + gw,
            "gameweek_id": gw,
            "opponent_club_id": 1,
            "was_home": False,
            "kickoff_time": "2026-09-01T15:00:00Z",
            "minutes": 90,
            "total_points": 6,
            "goals_scored": 1 if gw == 1 else 0,
            "assists": 0,
            "clean_sheets": 1 if gw % 2 == 1 else 0,
            "goals_conceded": 1 if gw % 2 == 0 else 0,
            "saves": 0,
            "expected_goals": 0.13,
            "expected_assists": 0.03,
            "expected_goal_involvements": 0.16,
            "expected_goals_conceded": 0.80,
            "defensive_contribution": gabriel_defcons[gw - 1],
            "starts": 1,
        })
    # Raya 6 fixtures
    for gw in range(1, 7):
        perf_records.append({
            "player_id": 3,
            "fixture_id": 200 + gw,
            "gameweek_id": gw,
            "opponent_club_id": 1,
            "was_home": False,
            "kickoff_time": "2026-09-01T15:00:00Z",
            "minutes": 90,
            "total_points": 5,
            "goals_scored": 0,
            "assists": 0,
            "clean_sheets": 1 if gw % 2 == 1 else 0,
            "goals_conceded": 1 if gw % 2 == 0 else 0,
            "saves": 4,
            "expected_goals": 0.0,
            "expected_assists": 0.0,
            "expected_goal_involvements": 0.0,
            "expected_goals_conceded": 1.0,
            "defensive_contribution": 0,
            "starts": 1,
        })
    # ZeroMin: 1 row with 0 minutes (DNP)
    perf_records.append({
        "player_id": 4,
        "fixture_id": 401,
        "gameweek_id": 1,
        "opponent_club_id": 2,
        "was_home": True,
        "kickoff_time": "2026-09-01T15:00:00Z",
        "minutes": 0,
        "total_points": 0,
        "goals_scored": 0,
        "assists": 0,
        "clean_sheets": 0,
        "goals_conceded": 0,
        "saves": 0,
        "expected_goals": 0.0,
        "expected_assists": 0.0,
        "expected_goal_involvements": 0.0,
        "expected_goals_conceded": 0.0,
        "defensive_contribution": 0,
        "starts": 0,
    })

    pd.DataFrame(perf_records).to_parquet(processed_dir / "player_performances.parquet")

    predictions_df = pd.DataFrame([
        {"player_id": pid, "gameweek_id": 1, "projected_points": 5.0, "projected_minutes": 90.0}
        for pid in [1, 2, 3, 4]
    ])

    dataset = build_dashboard_dataset(
        processed_dir=processed_dir,
        predictions_df=predictions_df,
        target_gw=1,
        horizon=1,
    )

    players = {p["id"]: p for p in dataset["players"]}

    # Verify Haaland
    h = players[1]
    assert h["apps"] == 5
    assert h["actual_starts"] == 5
    assert h["actual_minutes"] == 450
    assert h["actual_goals"] == 6
    assert h["actual_assists"] == 2
    assert h["actual_gi"] == 8
    assert h["actual_xg"] == 5.50
    assert h["actual_xa"] == 1.50
    assert h["actual_xgi"] == 7.00
    # 450 mins = 5.0 ninety-minute periods
    assert h["goals_per_90"] == round(6 / 5.0, 2)
    assert h["assists_per_90"] == round(2 / 5.0, 2)
    assert h["gi_per_90"] == round(8 / 5.0, 2)
    assert h["xg_per_90"] == round(5.50 / 5.0, 2)
    assert h["xa_per_90"] == round(1.50 / 5.0, 2)
    assert h["xgi_per_90"] == round(7.00 / 5.0, 2)
    # Per App (5 appearances)
    assert h["goals_per_app"] == round(6 / 5, 2)
    assert h["assists_per_app"] == round(2 / 5, 2)
    assert h["gi_per_app"] == round(8 / 5, 2)
    assert h["xg_per_app"] == round(5.50 / 5, 2)
    assert h["xa_per_app"] == round(1.50 / 5, 2)
    assert h["xgi_per_app"] == round(7.00 / 5, 2)
    # FWD Defcon: threshold 12, hits = 0
    assert h["defcon_hits"] == 0
    assert h["defcon_hit_rate"] == 0.0

    # Verify Gabriel (DEF)
    g = players[2]
    assert g["apps"] == 6
    assert g["actual_starts"] == 6
    assert g["actual_clean_sheets"] == 3
    assert g["cs_rate"] == round(3 / 6 * 100.0, 1)  # 50.0%
    assert g["actual_goals_conceded"] == 3
    # 540 mins = 6.0 nineties -> GC/90 = 3 / 6 = 0.5
    assert g["gc_per_90"] == round(3 / 6.0, 2)
    assert g["actual_xgc"] == round(0.80 * 6, 2)
    assert g["xgc_per_90"] == round((0.80 * 6) / 6.0, 2)
    # Defcon: 2 hits out of 6
    assert g["defcon_hits"] == 2
    assert g["defcon_hit_rate"] == round(2 / 6 * 100.0, 1)  # 33.3%

    # Verify Raya (GKP)
    r = players[3]
    assert r["apps"] == 6
    assert r["actual_saves"] == 24
    assert r["saves_per_90"] == round(24 / 6.0, 2)  # 4.0
    assert r["saves_per_app"] == round(24 / 6, 2)   # 4.0
    # GKP defcon not applicable -> None
    assert r["defcon_hits"] is None
    assert r["defcon_hit_rate"] is None

    # Verify Zero-minute player
    z = players[4]
    assert z["apps"] == 0
    assert z["actual_starts"] == 0
    assert z["actual_minutes"] == 0
    assert z["goals_per_90"] is None
    assert z["goals_per_app"] is None
    assert z["xgi_per_90"] is None
    assert z["xgi_per_app"] is None
    assert z["cs_rate"] is None
    assert z["defcon_hit_rate"] is None
    assert z["saves_per_90"] is None


def test_player_slice_underlying_fields(tmp_path: Path):
    player = {
        "id": 1,
        "name": "Haaland",
        "team": "MCI",
        "pos": "F",
        "pos_id": 4,
        "price": 15.0,
        "ownership_pct": 60.0,
        "apps": 5,
        "actual_starts": 5,
        "actual_minutes": 450,
        "actual_goals": 6,
        "actual_assists": 2,
        "actual_gi": 8,
        "actual_xg": 5.5,
        "actual_xa": 1.5,
        "actual_xgi": 7.0,
        "goals_per_90": 1.2,
        "assists_per_90": 0.4,
        "gi_per_90": 1.6,
        "xg_per_90": 1.1,
        "xa_per_90": 0.3,
        "xgi_per_90": 1.4,
        "goals_per_app": 1.2,
        "assists_per_app": 0.4,
        "gi_per_app": 1.6,
        "xg_per_app": 1.1,
        "xa_per_app": 0.3,
        "xgi_per_app": 1.4,
        "actual_clean_sheets": 2,
        "cs_rate": 40.0,
        "actual_goals_conceded": 4,
        "gc_per_90": 0.8,
        "actual_xgc": 4.2,
        "xgc_per_90": 0.84,
        "defcon_hits": 0,
        "defcon_hit_rate": 0.0,
        "actual_saves": None,
        "saves_per_90": None,
        "saves_per_app": None,
        "models": {
            "test_model": {
                "projections": {
                    "gw1": {"total_xp": 7.5, "xmins": 90.0, "xp_goals": 4.0, "xp_assists": 1.5}
                }
            }
        },
    }

    row = player_slice(player, "test_model", (1,))
    assert row["Apps"] == 5
    assert row["Starts"] == 5
    assert row["Actual Mins"] == 450
    assert row["Goals"] == 6
    assert row["Assists"] == 2
    assert row["GI"] == 8
    assert row["xG"] == 5.5
    assert row["xA"] == 1.5
    assert row["xGI"] == 7.0
    assert row["GI / 90"] == 1.6
    assert row["xGI / 90"] == 1.4
    assert row["GI / App"] == 1.6
    assert row["xGI / App"] == 1.4
    assert row["CS"] == 2
    assert row["CS %"] == 40.0
    assert row["GC"] == 4
    assert row["xGC"] == 4.2
    assert row["Defcon Hits"] == 0
    assert row["Defcon %"] == 0.0


def test_streamlit_explorer_underlying_presets_and_filter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import json
    from streamlit.testing.v1 import AppTest
    from test_streamlit_planner import dataset as base_dataset

    ds = base_dataset()
    p1 = ds["players"][0]
    p1["apps"] = 6
    p1["actual_starts"] = 6
    p1["actual_minutes"] = 540
    p1["actual_goals"] = 5
    p1["actual_assists"] = 2
    p1["actual_gi"] = 7
    p1["actual_xg"] = 4.5
    p1["actual_xa"] = 1.8
    p1["actual_xgi"] = 6.3
    p1["goals_per_90"] = 0.83
    p1["assists_per_90"] = 0.33
    p1["gi_per_90"] = 1.17
    p1["xg_per_90"] = 0.75
    p1["xa_per_90"] = 0.30
    p1["xgi_per_90"] = 1.05
    p1["actual_clean_sheets"] = 3
    p1["cs_rate"] = 50.0
    p1["actual_goals_conceded"] = 4
    p1["gc_per_90"] = 0.67
    p1["actual_xgc"] = 3.8
    p1["xgc_per_90"] = 0.63
    p1["defcon_hits"] = 2
    p1["defcon_hit_rate"] = 33.3

    p2 = ds["players"][1]
    p2["actual_minutes"] = 45

    data_path = tmp_path / "dataset.json"
    data_path.write_text(json.dumps(ds), encoding="utf-8")
    monkeypatch.setenv("FPL_PLANNER_DATASET", str(data_path))
    monkeypatch.setenv("FPL_PLANNER_STORAGE", str(tmp_path / "storage"))
    monkeypatch.setenv("FPL_PLANNER_PROCESSED_DIR", str(tmp_path / "processed"))

    script = Path(__file__).resolve().parents[1] / "streamlit_app.py"
    app = AppTest.from_file(script, default_timeout=30).run()
    assert not app.exception

    seg = app.segmented_control(key="explorer-table-preset")
    assert "Underlying Attack" in seg.options
    assert "Underlying Defence" in seg.options

    seg.set_value("Underlying Attack").run()
    assert not app.exception
    df_widget = app.dataframe(key="explorer-table")
    assert "Goals" in df_widget.value.columns
    assert "xGI" in df_widget.value.columns
    assert "GI / 90" in df_widget.value.columns

    seg.set_value("Underlying Defence").run()
    assert not app.exception
    df_widget = app.dataframe(key="explorer-table")
    assert "CS" in df_widget.value.columns
    assert "CS %" in df_widget.value.columns
    assert "Defcon Hits" in df_widget.value.columns
    assert "Defcon %" in df_widget.value.columns

    mins_slider = app.slider(key="explorer-actual-mins")
    assert mins_slider.value == 0
    mins_slider.set_value(90).run()
    assert not app.exception
