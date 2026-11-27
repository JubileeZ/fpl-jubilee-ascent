from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from features.builder import (
    attach_external_xmins,
    build_features,
    load_xmins_override,
    resolve_operational_processed_dir,
)
from models.participation_state_hybrid import (
    ParticipationStateHybridModel,
    scale_states_to_target,
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


@pytest.fixture(scope="module")
def baseline_champion_gw7() -> tuple[Path, pd.DataFrame, Any, pd.DataFrame]:
    from commands.run_model import load_fit_history
    from models import get_model, resolve_model_or_champion

    processed = resolve_operational_processed_dir(Path("."))
    df_feat_base = build_features(processed, 7, horizon=1)
    champ_name = resolve_model_or_champion("champion")
    model = get_model(champ_name)
    fit_hist = load_fit_history(processed, 7)
    if fit_hist is not None:
        model.fit(fit_hist)
    base_preds = model.predict(df_feat_base, horizon=1)
    return processed, df_feat_base, model, base_preds


def test_sparse_override_preserves_champion_for_unlisted_players(
    tmp_path: Path,
    baseline_champion_gw7: tuple[Path, pd.DataFrame, Any, pd.DataFrame],
) -> None:
    processed, _df_feat_base, model, base_preds = baseline_champion_gw7

    # Champion with sparse override on only 1 player (Haaland, 411)
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
        output_dir=tmp_path,
    )
    assert out_csv.exists()
    assert out_csv.parent == tmp_path
    assert out_csv.name == f"{out_stem}.csv"
    df = pd.read_csv(out_csv)
    haaland = df[df["ID"] == 411]
    assert not haaland.empty
    assert pytest.approx(haaland.iloc[0]["7_xMins"], abs=0.1) == 87.0


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


def test_scale_states_to_target_preserves_conditional_uncertainty() -> None:
    # (a) Scaling down reduces p_start & p_sub proportionally into p_dnp while keeping conditional start mins & p60
    pdnp, ps, psub, sm, subm, p60s, p60sub = scale_states_to_target(
        0.10, 0.70, 0.20, 76.0, 18.0, 0.80, 0.0, 38.0
    )
    assert sm == pytest.approx(76.0)
    assert subm == pytest.approx(18.0)
    assert p60s == pytest.approx(0.80)
    assert p60sub == pytest.approx(0.0)
    assert ps * sm + psub * subm == pytest.approx(38.0, abs=1e-4)
    assert pdnp + ps + psub == pytest.approx(1.0, abs=1e-6)
    assert psub > 0.0

    # (b) Moderate scaling up (68m -> 72m) moves p_dnp -> p_start while retaining non-zero sub uncertainty
    nat_pdnp, nat_ps, nat_psub = 0.20, 0.66, 0.14
    nat_sm, nat_subm = 80.0, 18.0
    u_pdnp, u_ps, u_psub, u_sm, u_subm, u_p60s, _ = scale_states_to_target(
        nat_pdnp, nat_ps, nat_psub, nat_sm, nat_subm, 0.88, 0.0, 72.0
    )
    assert u_ps < 0.90
    assert u_psub > 0.05
    assert u_sm == pytest.approx(nat_sm)
    assert u_p60s == pytest.approx(0.88)
    assert u_ps * u_sm + u_psub * u_subm == pytest.approx(72.0, abs=1e-4)
    assert u_pdnp + u_ps + u_psub == pytest.approx(1.0, abs=1e-6)

    # (c) Zero target collapses safely to DNP
    assert scale_states_to_target(0.2, 0.7, 0.1, 80.0, 18.0, 0.9, 0.0, 0.0) == (1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

    # (d) Near-zero native (< 5.0m) falls back to target_to_states
    fb = scale_states_to_target(0.98, 0.01, 0.01, 78.0, 18.0, 0.8, 0.0, 89.0)
    assert fb[1] * fb[3] + fb[2] * fb[4] == pytest.approx(89.0, abs=0.05)

    # (e) Minutes recovery sweep including full 90.0m and pure sub-in (start_mins=0.0) rows
    for tgt in (0.0, 10.0, 20.0, 45.0, 65.0, 72.0, 80.0, 89.0, 90.0):
        res = scale_states_to_target(0.15, 0.72, 0.13, 78.0, 18.0, 0.85, 0.0, tgt)
        assert 0.0 <= res[0] <= 1.0 and 0.0 <= res[1] <= 1.0 and 0.0 <= res[2] <= 1.0
        assert res[0] + res[1] + res[2] == pytest.approx(1.0, abs=1e-6)
        assert res[1] * res[3] + res[2] * res[4] == pytest.approx(tgt, abs=0.05)

    sub_only = scale_states_to_target(0.20, 0.0, 0.80, 0.0, 18.0, 0.0, 0.0, 65.0)
    assert sub_only[0] + sub_only[1] + sub_only[2] == pytest.approx(1.0, abs=1e-6)
    assert sub_only[1] * sub_only[3] + sub_only[2] * sub_only[4] == pytest.approx(65.0, abs=0.05)


def test_participation_state_model_override_scales_native_states_and_preserves_unlisted() -> None:
    model = ParticipationStateHybridModel()
    base_rows = pd.DataFrame([
        {
            "player_id": 100,
            "gameweek_id": 7,
            "fixture_id": 1,
            "position_id": 3,
            "p_dnp": 0.15,
            "p_start": 0.75,
            "p_sub_in": 0.10,
            "xmins_if_start": 76.0,
            "xmins_if_sub_in": 18.0,
            "p_60_if_start": 0.82,
            "p_60_if_sub_in": 0.0,
            "per90_xg": 0.4,
            "per90_xa": 0.3,
            "per90_goals_conceded": 1.1,
            "is_home": True,
        },
        {
            "player_id": 101,
            "gameweek_id": 7,
            "fixture_id": 2,
            "position_id": 2,
            "p_dnp": 0.08,
            "p_start": 0.88,
            "p_sub_in": 0.04,
            "xmins_if_start": 86.0,
            "xmins_if_sub_in": 15.0,
            "p_60_if_start": 0.94,
            "p_60_if_sub_in": 0.0,
            "per90_xg": 0.08,
            "per90_xa": 0.12,
            "per90_goals_conceded": 1.0,
            "is_home": True,
        },
    ])
    native_preds = model.predict(base_rows, horizon=1).set_index("player_id")

    over_rows = base_rows.copy()
    # Apply 75% doubtful factor on player 100, leave player 101 NaN
    target_100 = 0.57 * float(native_preds.loc[100, "projected_minutes"])
    over_rows["external_xmins"] = [target_100, float("nan")]
    over_preds = model.predict(over_rows, horizon=1).set_index("player_id")

    p100 = over_preds.loc[100]
    assert p100["projected_minutes"] == pytest.approx(target_100, abs=1e-4)
    assert p100["xmins_if_start"] == pytest.approx(76.0)
    assert p100["p_60_if_start"] == pytest.approx(0.82)
    assert p100["p_start"] < float(native_preds.loc[100, "p_start"])

    # Unlisted player 101 stays identical to native baseline (< 1e-9)
    p101 = over_preds.loc[101]
    n101 = native_preds.loc[101]
    assert abs(float(p101["projected_points"]) - float(n101["projected_points"])) < 1e-9
    assert abs(float(p101["projected_minutes"]) - float(n101["projected_minutes"])) < 1e-9


def test_attach_external_xmins_handles_dgw_bgw_clamps_and_non_mutation() -> None:
    df = pd.DataFrame([
        {"player_id": 1, "gameweek_id": 7, "fixture_id": 10},
        {"player_id": 1, "gameweek_id": 7, "fixture_id": 11},  # DGW splits 160 -> 80 per fixture
        {"player_id": 2, "gameweek_id": 7, "fixture_id": -1},  # Blank GW -> 0.0
        {"player_id": 3, "gameweek_id": 7, "fixture_id": 12},  # Listed > 90 -> clamped to 90.0
        {"player_id": 4, "gameweek_id": 7, "fixture_id": 13},  # Unlisted -> NaN
        {"player_id": 5, "gameweek_id": 7, "fixture_id": 14},  # Listed < 0 -> clamped to 0.0
        {"player_id": 6, "gameweek_id": 7, "fixture_id": 15},  # Listed NaN -> preserved as NaN
    ])
    df_orig = df.copy()
    out = attach_external_xmins(df, {(1, 7): 160.0, (2, 7): 80.0, (3, 7): 120.0, (5, 7): -15.0, (6, 7): float("nan")})
    assert "external_xmins" not in df_orig.columns
    assert "external_xmins" not in df.columns
    vals = list(out["external_xmins"])
    assert vals[0] == pytest.approx(80.0)
    assert vals[1] == pytest.approx(80.0)
    assert vals[2] == pytest.approx(0.0)
    assert vals[3] == pytest.approx(90.0)
    assert pd.isna(vals[4])
    assert vals[5] == pytest.approx(0.0)
    assert pd.isna(vals[6])

    # Empty map preserves native fallback without adding/overwriting external_xmins
    empty_out = attach_external_xmins(df, {})
    assert "external_xmins" not in empty_out.columns
    pd.testing.assert_frame_equal(empty_out, df)

    # Missing required columns returns copy safely without KeyError
    missing_cols = pd.DataFrame([{"player_id": 1}])
    missing_out = attach_external_xmins(missing_cols, {(1, 7): 50.0})
    assert "external_xmins" not in missing_out.columns
    pd.testing.assert_frame_equal(missing_out, missing_cols)

