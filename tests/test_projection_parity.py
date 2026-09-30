import json
import pandas as pd
import pytest

from commands.export_dashboard import (
    PROJECT_ROOT,
    resolve_operational_processed_dir,
    run_dashboard_export,
)
from models import get_default_model_name


def test_dashboard_csv_parity() -> None:
    """Verify exact parity between data/{model}.csv and data/dashboard_data.json for all unfinished GWs."""
    processed_dir = resolve_operational_processed_dir(PROJECT_ROOT)
    if not (processed_dir / "players.parquet").exists():
        pytest.skip("No operational processed data available")

    json_path = PROJECT_ROOT / "data" / "dashboard_data.json"
    champion_name = get_default_model_name()
    csv_path = PROJECT_ROOT / "data" / f"{champion_name}.csv"

    # If artifacts missing on clean run, generate them via canonical pipeline
    if not csv_path.exists() or not json_path.exists():
        run_dashboard_export(model_name=champion_name, horizon=6)

    assert json_path.exists(), f"Failed to locate {json_path}"
    with open(json_path, encoding="utf-8") as f:
        dashboard_data = json.load(f)

    meta = dashboard_data.get("meta", {})
    unfinished_gws = meta.get("unfinished_gameweeks", [])
    assert unfinished_gws, "No unfinished gameweeks found in dashboard_data.json metadata"

    json_players = {int(p["id"]): p for p in dashboard_data.get("players", [])}
    models_to_test = meta.get("models") or [champion_name]

    for model_name in models_to_test:
        model_csv_path = PROJECT_ROOT / "data" / f"{model_name}.csv"
        if not model_csv_path.exists():
            continue

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
