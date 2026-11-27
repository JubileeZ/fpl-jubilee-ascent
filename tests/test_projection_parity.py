import json
from pathlib import Path

import pandas as pd
import pytest

from commands import export_dashboard
from features.season_archive import LIVE_SEASON, archive_processed_dir
from models.planner_selection import RemoteFreshnessResult
from models.selection import load_model_selection


@pytest.mark.parametrize("near_term", [True, False], ids=["near-term", "season"])
def test_dashboard_csv_parity(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, near_term: bool) -> None:
    """Verify exact parity between data/{model}.csv and data/dashboard_data.json for all unfinished GWs."""
    processed_dir = archive_processed_dir(LIVE_SEASON)
    monkeypatch.setattr(export_dashboard, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(export_dashboard, "resolve_operational_processed_dir", lambda _root: processed_dir)
    selection = load_model_selection()
    freshness = RemoteFreshnessResult(
        status="verified_current",
        local_champion=selection.champion,
        local_candidates=selection.candidates,
        local_podium_sealed=selection.podium_sealed,
        local_podium_frozen_season=selection.podium_frozen_season,
    )
    monkeypatch.setattr(export_dashboard, "check_remote_main_freshness", lambda *_args, **_kwargs: freshness)
    monkeypatch.setattr("models.planner_selection.sync_validation_evidence_readonly", lambda *_args, **_kwargs: False)
    if near_term:
        last_gw = min(export_dashboard.resolve_default_target_gw(processed_dir) + 1, export_dashboard.SEASON_END_GW)
        monkeypatch.setattr(export_dashboard, "SEASON_END_GW", last_gw)
    export_dashboard.run_dashboard_export(model_name=selection.champion, horizon=6)
    json_path = tmp_path / "data" / "dashboard_data.json"

    assert json_path.exists(), f"Failed to locate {json_path}"
    with open(json_path, encoding="utf-8") as f:
        dashboard_data = json.load(f)

    meta = dashboard_data.get("meta", {})
    assert meta.get("minutes_cascade") == {
        "mode": "internal_baseline",
        "profile": "SP_Soft_Shield_M1",
        "soft_curve_max_step": 5,
    }
    unfinished_gws = meta.get("unfinished_gameweeks", [])
    assert unfinished_gws, "No unfinished gameweeks found in dashboard_data.json metadata"

    json_players = {int(p["id"]): p for p in dashboard_data.get("players", [])}
    models_to_test = meta.get("models") or [selection.champion]

    for model_name in models_to_test:
        model_csv_path = tmp_path / "data" / f"{model_name}.csv"
        assert model_csv_path.exists()

        df_csv = pd.read_csv(model_csv_path)
        csv_player_ids = set(df_csv["ID"].astype(int))
        assert csv_player_ids == set(json_players.keys()), (
            f"Player set mismatch between {model_csv_path.name} and dashboard_data.json"
        )

        for _, row in df_csv.iterrows():
            pid = int(row["ID"])
            p_json = json_players[pid]
            # Use model-specific projections dict if comparison model, else primary
            model_sub = p_json.get("models", {}).get(model_name)
            projs = model_sub.get("projections", {}) if model_sub else p_json.get("projections", {})

            for gw in unfinished_gws:
                pts_col = f"{gw}_Pts"
                mins_col = f"{gw}_xMins"
                gw_key = f"gw{gw}"

                if pts_col in row and gw_key in projs:
                    csv_pts = float(row[pts_col])
                    json_pts = float(projs[gw_key]["total_xp"])
                    assert round(csv_pts, 2) == round(json_pts, 2), (
                        f"Point projection mismatch for {row['Name']} (ID {pid}) in GW{gw} for {model_name}: "
                        f"CSV={csv_pts:.2f}, JSON={json_pts:.2f}"
                    )

                if mins_col in row and gw_key in projs:
                    csv_mins = float(row[mins_col])
                    json_mins = float(projs[gw_key]["xmins"])
                    assert round(csv_mins, 1) == round(json_mins, 1), (
                        f"Minutes projection mismatch for {row['Name']} (ID {pid}) in GW{gw} for {model_name}: "
                        f"CSV={csv_mins:.1f}, JSON={json_mins:.1f}"
                    )


def test_dashboard_export_minutes_cascade_modes_tail_and_override_isolation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from features.internal_xmins import SOFT_UNKNOWN_CURVE
    from models.selection import ModelSelection, save_model_selection

    processed = tmp_path / "processed"
    processed.mkdir()
    pd.DataFrame([
        {"id": 1, "web_name": "GK1", "first_name": "G", "second_name": "One", "club_id": 1, "position_id": 1, "now_cost": 55, "status": "a", "chance_of_playing_next_round": 100.0, "news": "", "selected_by_percent": 10.0, "code": 1},
        {"id": 2, "web_name": "GK2", "first_name": "G", "second_name": "Two", "club_id": 1, "position_id": 1, "now_cost": 40, "status": "a", "chance_of_playing_next_round": 100.0, "news": "", "selected_by_percent": 1.0, "code": 2},
        {"id": 3, "web_name": "UnkInj", "first_name": "U", "second_name": "Inj", "club_id": 1, "position_id": 3, "now_cost": 70, "status": "i", "chance_of_playing_next_round": 0.0, "news": "Knee injury", "selected_by_percent": 5.0, "code": 3},
        {"id": 4, "web_name": "FitMid", "first_name": "F", "second_name": "Mid", "club_id": 1, "position_id": 3, "now_cost": 65, "status": "a", "chance_of_playing_next_round": 100.0, "news": "", "selected_by_percent": 15.0, "code": 4},
    ]).to_parquet(processed / "players.parquet", index=False)
    pd.DataFrame([
        {"id": 1, "name": "ClubA", "short_name": "CLA", "strength": 3, "strength_overall_home": 1100, "strength_overall_away": 1100, "strength_attack_home": 1100, "strength_attack_away": 1100, "strength_defence_home": 1100, "strength_defence_away": 1100},
        {"id": 2, "name": "ClubB", "short_name": "CLB", "strength": 3, "strength_overall_home": 1100, "strength_overall_away": 1100, "strength_attack_home": 1100, "strength_attack_away": 1100, "strength_defence_home": 1100, "strength_defence_away": 1100},
    ]).to_parquet(processed / "clubs.parquet", index=False)
    # GW1 finished; GW2 in-play (finished=False, is_next=False); GW3 transfer plan start (is_next=True) through GW10
    gw_rows = [{"id": 1, "name": "GW1", "finished": True, "is_next": False, "data_checked": True, "deadline_time": "2025-08-15T18:00:00Z"}]
    for gw in range(2, 11):
        gw_rows.append({
            "id": gw,
            "name": f"GW{gw}",
            "finished": False,
            "is_next": gw == 3,
            "data_checked": False,
            "deadline_time": f"2025-09-{gw:02d}T18:00:00Z",
        })
    pd.DataFrame(gw_rows).to_parquet(processed / "gameweeks.parquet", index=False)
    pd.DataFrame([
        {"id": gw, "gameweek_id": gw, "home_club_id": 1, "away_club_id": 2, "team_h_difficulty": 3, "team_a_difficulty": 3, "kickoff_time": f"2025-09-{gw:02d}T14:00:00Z", "finished": gw == 1}
        for gw in range(1, 11)
    ]).to_parquet(processed / "fixtures.parquet", index=False)
    pd.DataFrame([
        {"player_id": 1, "fixture_id": 1, "gameweek_id": 1, "club_id": 1, "opponent_club_id": 2, "was_home": True, "minutes": 90, "starts": 1, "total_points": 6, "goals_scored": 0, "assists": 0, "clean_sheets": 1, "goals_conceded": 0, "saves": 3, "bonus": 0, "bps": 24, "expected_goals": 0.0, "expected_assists": 0.0, "expected_goals_conceded": 0.8, "defensive_contribution": 0, "penalties_saved": 0, "penalties_missed": 0, "own_goals": 0, "yellow_cards": 0, "red_cards": 0, "threat": 0.0, "creativity": 0.0},
        {"player_id": 2, "fixture_id": 1, "gameweek_id": 1, "club_id": 1, "opponent_club_id": 2, "was_home": True, "minutes": 0, "starts": 0, "total_points": 0, "goals_scored": 0, "assists": 0, "clean_sheets": 0, "goals_conceded": 0, "saves": 0, "bonus": 0, "bps": 0, "expected_goals": 0.0, "expected_assists": 0.0, "expected_goals_conceded": 0.0, "defensive_contribution": 0, "penalties_saved": 0, "penalties_missed": 0, "own_goals": 0, "yellow_cards": 0, "red_cards": 0, "threat": 0.0, "creativity": 0.0},
        {"player_id": 3, "fixture_id": 1, "gameweek_id": 1, "club_id": 1, "opponent_club_id": 2, "was_home": True, "minutes": 85, "starts": 1, "total_points": 5, "goals_scored": 0, "assists": 1, "clean_sheets": 1, "goals_conceded": 0, "saves": 0, "bonus": 0, "bps": 20, "expected_goals": 0.2, "expected_assists": 0.3, "expected_goals_conceded": 0.8, "defensive_contribution": 4, "penalties_saved": 0, "penalties_missed": 0, "own_goals": 0, "yellow_cards": 0, "red_cards": 0, "threat": 15.0, "creativity": 20.0},
        {"player_id": 4, "fixture_id": 1, "gameweek_id": 1, "club_id": 1, "opponent_club_id": 2, "was_home": True, "minutes": 85, "starts": 1, "total_points": 5, "goals_scored": 0, "assists": 1, "clean_sheets": 1, "goals_conceded": 0, "saves": 0, "bonus": 0, "bps": 20, "expected_goals": 0.2, "expected_assists": 0.3, "expected_goals_conceded": 0.8, "defensive_contribution": 4, "penalties_saved": 0, "penalties_missed": 0, "own_goals": 0, "yellow_cards": 0, "red_cards": 0, "threat": 15.0, "creativity": 20.0},
    ]).to_parquet(processed / "player_performances.parquet", index=False)

    sel_path = tmp_path / "model_selection.json"
    save_model_selection(ModelSelection(champion="participation_state_hybrid", candidates=()), sel_path)

    # Decoy local override file that default dashboard export MUST ignore
    planner_dir = tmp_path / "data" / "planner"
    planner_dir.mkdir(parents=True)
    (planner_dir / "xmins_override.csv").write_text("ID,Name,3_xMins\n4,FitMid,12.0\n", encoding="utf-8")

    monkeypatch.setattr(export_dashboard, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(export_dashboard, "SEASON_END_GW", 10)
    monkeypatch.setattr(export_dashboard, "resolve_operational_processed_dir", lambda _r: processed)
    monkeypatch.setattr("models.selection.DEFAULT_CONFIG_PATH", sel_path)
    freshness = RemoteFreshnessResult("verified_current", "participation_state_hybrid", (), False, None)
    monkeypatch.setattr(export_dashboard, "check_remote_main_freshness", lambda *_a, **_kw: freshness)
    monkeypatch.setattr("models.planner_selection.sync_validation_evidence_readonly", lambda *_a, **_kw: False)

    # 1. Pure Layer 1 reference (minutes_cascade=False)
    off_json = export_dashboard.run_dashboard_export(
        model_name="participation_state_hybrid",
        horizon=6,
        config_path=sel_path,
        output_path=tmp_path / "off.json",
        minutes_cascade=False,
    )
    off_doc = json.loads(off_json.read_text(encoding="utf-8"))
    assert off_doc["meta"]["minutes_cascade"] == {"mode": "off", "profile": "layer1_native"}
    off_players = {int(p["id"]): p["projections"] for p in off_doc["players"]}

    # 2. Default export (minutes_cascade=True): SP_Soft_Shield_M1, ignores decoy override, step=0 at target_gw=3
    on_json = export_dashboard.run_dashboard_export(
        model_name="participation_state_hybrid",
        horizon=6,
        config_path=sel_path,
    )
    on_doc = json.loads(on_json.read_text(encoding="utf-8"))
    assert on_doc["meta"]["minutes_cascade"] == {
        "mode": "internal_baseline",
        "profile": "SP_Soft_Shield_M1",
        "soft_curve_max_step": 5,
    }
    on_players = {int(p["id"]): p["projections"] for p in on_doc["players"]}

    # Healthy outfielder (4) ignores decoy xmins_override.csv and preserves Layer 1
    assert on_players[4]["gw3"]["xmins"] == pytest.approx(off_players[4]["gw3"]["xmins"], abs=1e-6)
    # In-play GW2 (before transfer_plan_start=GW3) retains Layer 1
    assert on_players[1]["gw2"]["xmins"] == pytest.approx(off_players[1]["gw2"]["xmins"], abs=1e-6)
    # M1 GKP allocation active GW3..GW10
    assert on_players[1]["gw3"]["xmins"] == pytest.approx(89.0, abs=0.2)
    assert on_players[2]["gw3"]["xmins"] == pytest.approx(1.0, abs=0.2)
    assert on_players[1]["gw10"]["xmins"] == pytest.approx(89.0, abs=0.2)
    # Unknown-return 'i' (3): 0m at target_gw=3 (step=0), soft curve steps 1..5 (GW4..GW8), reverts to L1 at step>=6 (GW9..10)
    assert on_players[3]["gw3"]["xmins"] == 0.0
    for step in range(1, 6):
        gw = 3 + step
        expected = off_players[3][f"gw{gw}"]["xmins"] * SOFT_UNKNOWN_CURVE[step]
        assert on_players[3][f"gw{gw}"]["xmins"] == pytest.approx(expected, abs=0.1)
    assert on_players[3]["gw9"]["xmins"] == pytest.approx(off_players[3]["gw9"]["xmins"], abs=1e-6)
    assert on_players[3]["gw10"]["xmins"] == pytest.approx(off_players[3]["gw10"]["xmins"], abs=1e-6)

    # Exact ADR 0052 parity with data/participation_state_hybrid.csv
    df_csv = pd.read_csv(tmp_path / "data" / "participation_state_hybrid.csv").set_index("ID")
    for gw in range(2, 11):
        assert float(df_csv.loc[1, f"{gw}_xMins"]) == pytest.approx(on_players[1][f"gw{gw}"]["xmins"], abs=0.1)
        assert float(df_csv.loc[3, f"{gw}_Pts"]) == pytest.approx(on_players[3][f"gw{gw}"]["total_xp"], abs=0.01)

    # 3. Explicit external override path opt-in
    custom_csv = tmp_path / "custom_solio.csv"
    custom_csv.write_text("ID,Name,3_xMins\n4,FitMid,22.0\n", encoding="utf-8")
    ov_json = export_dashboard.run_dashboard_export(
        model_name="participation_state_hybrid",
        horizon=6,
        config_path=sel_path,
        output_path=tmp_path / "ov.json",
        xmins_override=custom_csv,
    )
    ov_doc = json.loads(ov_json.read_text(encoding="utf-8"))
    assert ov_doc["meta"]["minutes_cascade"]["mode"] == "external_override"
    ov_players = {int(p["id"]): p["projections"] for p in ov_doc["players"]}
    assert ov_players[4]["gw3"]["xmins"] == pytest.approx(22.0, abs=0.1)

