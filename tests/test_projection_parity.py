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
