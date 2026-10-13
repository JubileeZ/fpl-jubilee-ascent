import pandas as pd
import pytest
from pathlib import Path

from features.builder import (
    build_features,
    load_xmins_override,
    resolve_operational_processed_dir,
)
from models.participation_state_hybrid import (
    ParticipationStateHybridModel,
    target_to_states,
)


def test_target_to_states_minutes_recovery():
    test_cases = [89.09, 85.0, 75.0, 50.0, 27.0, 10.0, 0.91, 0.0]
    for xmins in test_cases:
        p_start, p_sub, p_dnp, start_mins, sub_mins = target_to_states(xmins)
        assert 0.0 <= p_start <= 1.0
        assert 0.0 <= p_sub <= 1.0
        assert 0.0 <= p_dnp <= 1.0
        assert pytest.approx(p_start + p_sub + p_dnp, abs=1e-5) == 1.0
        recovered = p_start * start_mins + p_sub * sub_mins
        assert pytest.approx(recovered, abs=1e-2) == xmins


def test_load_xmins_override(tmp_path: Path):
    csv_file = tmp_path / "xmins.csv"
    csv_file.write_text(
        "Pos,ID,Name,7_xMins,8_xMins\n"
        "G,1,Raya,89.09,85.00\n"
        "F,411,Haaland,88.50,90.00\n",
        encoding="utf-8",
    )
    result = load_xmins_override(csv_file, [7, 8])
    assert result[(1, 7)] == 89.09
    assert result[(1, 8)] == 85.00
    assert result[(411, 7)] == 88.50
    assert result[(411, 8)] == 90.00


def test_build_features_attaches_external_xmins(tmp_path: Path):
    processed = resolve_operational_processed_dir(Path("."))
    csv_file = tmp_path / "xmins.csv"
    csv_file.write_text(
        "ID,Name,7_xMins\n"
        "411,Haaland,85.5\n",
        encoding="utf-8",
    )
    df = build_features(processed, 7, horizon=1, xmins_override=csv_file)
    assert "external_xmins" in df.columns
    haaland_row = df[df["player_id"] == 411]
    assert not haaland_row.empty
    assert haaland_row.iloc[0]["external_xmins"] == 85.5

    # Unlisted player receives 0.0 when override is active
    other_row = df[df["player_id"] != 411]
    assert not other_row.empty
    assert other_row.iloc[0]["external_xmins"] == 0.0


def test_participation_state_model_respects_external_xmins():
    model = ParticipationStateHybridModel()
    features = pd.DataFrame([
        {
            "player_id": 100,
            "gameweek_id": 7,
            "fixture_id": 1,
            "position_id": 4,
            "external_xmins": 80.0,
            "per90_xg": 0.5,
            "per90_xa": 0.2,
            "per90_goals_conceded": 1.0,
            "is_home": True,
        },
        {
            "player_id": 200,
            "gameweek_id": 7,
            "fixture_id": 1,
            "position_id": 4,
            "external_xmins": 0.0,
            "per90_xg": 0.5,
            "per90_xa": 0.2,
            "per90_goals_conceded": 1.0,
            "is_home": True,
        },
    ])
    preds = model.predict(features, horizon=1)
    p100 = preds[preds["player_id"] == 100].iloc[0]
    p200 = preds[preds["player_id"] == 200].iloc[0]

    assert pytest.approx(p100["projected_minutes"], abs=0.1) == 80.0
    assert p100["projected_points"] > 0.0

    assert pytest.approx(p200["projected_minutes"], abs=0.1) == 0.0
    assert p200["projected_points"] == 0.0


def test_generate_model_projections_with_xmins_override(tmp_path: Path):
    from commands.run_model import generate_model_projections

    csv_file = tmp_path / "xmins.csv"
    csv_file.write_text(
        "ID,Name,7_xMins\n"
        "411,Haaland,87.0\n",
        encoding="utf-8",
    )
    out_stem = "test_custom_mins"
    out_csv = generate_model_projections(
        model_name="champion",
        target_gw=7,
        horizon=1,
        xmins_override=csv_file,
        output_name=out_stem,
    )
    assert out_csv.exists()
    assert out_csv.name == f"{out_stem}.csv"
    df = pd.read_csv(out_csv)
    haaland = df[df["ID"] == 411]
    assert not haaland.empty
    assert pytest.approx(haaland.iloc[0]["7_xMins"], abs=0.1) == 87.0
    # Clean up test output file in data/
    out_csv.unlink(missing_ok=True)
