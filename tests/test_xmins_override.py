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

    # Unlisted player receives NaN so they fall back to Native Champion
    other_row = df[df["player_id"] != 411]
    assert not other_row.empty
    assert pd.isna(other_row.iloc[0]["external_xmins"])


def test_load_xmins_override_omits_blank_cells(tmp_path: Path):
    csv_file = tmp_path / "xmins_blank.csv"
    csv_file.write_text(
        "ID,Name,7_xMins,8_xMins\n"
        "411,Haaland,85.5,\n"
        "12,Saka,0.0,60.0\n",
        encoding="utf-8",
    )
    result = load_xmins_override(csv_file, [7, 8])
    assert result[(411, 7)] == 85.5
    assert (411, 8) not in result
    assert result[(12, 7)] == 0.0
    assert result[(12, 8)] == 60.0


def test_sparse_override_preserves_champion_for_unlisted_players(tmp_path: Path):
    from models import get_model, resolve_model_or_champion
    from commands.run_model import load_fit_history

    processed = resolve_operational_processed_dir(Path("."))
    # 1. Baseline Champion without override
    df_feat_base = build_features(processed, 7, horizon=1)
    champ_name = resolve_model_or_champion("champion")
    model = get_model(champ_name)
    fit_hist = load_fit_history(processed, 7)
    if fit_hist is not None:
        model.fit(fit_hist)
    base_preds = model.predict(df_feat_base, horizon=1)

    # 2. Champion with sparse override on only 1 player (Haaland, 411)
    csv_file = tmp_path / "sparse_xmins.csv"
    csv_file.write_text(
        "ID,Name,7_xMins\n"
        "411,Haaland,33.0\n",
        encoding="utf-8",
    )
    df_feat_sparse = build_features(processed, 7, horizon=1, xmins_override=csv_file)
    sparse_preds = model.predict(df_feat_sparse, horizon=1)

    # Overridden player gets 33.0
    haaland_sparse = sparse_preds[sparse_preds["player_id"] == 411].iloc[0]
    assert pytest.approx(haaland_sparse["projected_minutes"], abs=0.5) == 33.0

    # Unlisted active players retain their baseline Champion minutes & points
    base_others = base_preds[base_preds["player_id"] != 411].sort_values("player_id")
    sparse_others = sparse_preds[sparse_preds["player_id"] != 411].sort_values("player_id")
    assert not base_others.empty
    # Sample top 10 players to verify parity
    top_base = base_others.head(10)
    top_sparse = sparse_others.head(10)
    for (_, b_row), (_, s_row) in zip(top_base.iterrows(), top_sparse.iterrows()):
        assert pytest.approx(b_row["projected_minutes"], abs=1e-3) == s_row["projected_minutes"]
        assert pytest.approx(b_row["projected_points"], abs=1e-3) == s_row["projected_points"]


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


def test_dgw_and_bgw_xmins_override_grain(tmp_path: Path):
    from projections.exporter import export_projections

    # Test that when external xmins is divided across 2 fixtures in a DGW,
    # export_projections sums them back to the gameweek total.
    pred_df = pd.DataFrame([
        # Player 100 has Double GW (fixtures 10 and 11 in GW20) with 45m each -> 90m total
        {"player_id": 100, "gameweek_id": 20, "fixture_id": 10, "projected_points": 4.5, "projected_minutes": 45.0},
        {"player_id": 100, "gameweek_id": 20, "fixture_id": 11, "projected_points": 4.5, "projected_minutes": 45.0},
        # Player 200 has Blank GW (fixture -1 in GW20) -> 0m
        {"player_id": 200, "gameweek_id": 20, "fixture_id": -1, "projected_points": 0.0, "projected_minutes": 0.0},
    ])
    players_df = pd.DataFrame([
        {"id": 100, "web_name": "DGW_Player", "position_id": 4, "now_cost": 80, "club_id": 1},
        {"id": 200, "web_name": "BGW_Player", "position_id": 3, "now_cost": 60, "club_id": 2},
    ])
    clubs_df = pd.DataFrame([
        {"id": 1, "short_name": "ARS"},
        {"id": 2, "short_name": "AVL"},
    ])
    out_csv = tmp_path / "projections_dgw.csv"
    export_projections(pred_df, players_df, clubs_df, out_csv)
    assert out_csv.exists()
    res = pd.read_csv(out_csv)
    p100 = res[res["ID"] == 100].iloc[0]
    p200 = res[res["ID"] == 200].iloc[0]
    assert p100["20_xMins"] == 90.0
    assert p100["20_Pts"] == 9.0
    assert p200["20_xMins"] == 0.0
    assert p200["20_Pts"] == 0.0
