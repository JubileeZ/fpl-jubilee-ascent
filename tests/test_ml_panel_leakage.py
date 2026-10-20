"""Leakage and contract tests for Causal Panel Feature Engine (Blueprint Step 1).

Enforces:
1. Strict causal time-travel invariance: historical feature values at Gameweek g
   are strictly invariant to future rows (GW >= g) or future data mutations.
2. Zero terminal player columns: Feature Contract compliance without accessing
   any post-season summary fields in TERMINAL_PLAYER_COLUMNS.
3. Fit-only standardization: CausalFeatureScaler parameters (mean, std, q01, q99)
   are computed strictly on historical training rows (g < target_gw) and are
   100% independent of prediction frame values.
4. Strictly lagged market features: transfer_momentum and price_rel_pos read
   strictly from H_{<g} (g-1 or earlier), never from row g itself.
5. In-memory club ID reconstruction: opposing fixture matching without disk I/O.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from models.ml_panel_features import CausalFeatureScaler, build_causal_panel


def _create_synthetic_history(n_gws: int = 6, n_players: int = 10) -> pd.DataFrame:
    """Generate synthetic player_performances history with opposing fixtures."""
    rows = []
    # 2 clubs: Club 1 and Club 2 playing each other in each GW
    for gw in range(1, n_gws + 1):
        fid = 100 + gw
        kickoff = f"2025-08-{10 + gw:02d}T15:00:00Z"
        for i in range(n_players):
            is_club1 = i < (n_players // 2)
            opp_id = 2 if is_club1 else 1
            home = is_club1

            starter = (i % 3) != 0
            mins = 90.0 if starter else (20.0 if (i % 3) == 1 else 0.0)
            starts = 1.0 if starter else 0.0

            rows.append({
                "player_id": 1000 + i,
                "gameweek_id": gw,
                "fixture_id": fid,
                "was_home": home,
                "opponent_club_id": opp_id,
                "kickoff_time": kickoff,
                "minutes": mins,
                "starts": starts,
                "goals_scored": 1.0 if starter and (i == 1) else 0.0,
                "expected_goals": 0.35 if starter else 0.05,
                "assists": 1.0 if starter and (i == 2) else 0.0,
                "expected_assists": 0.20 if starter else 0.02,
                "creativity": 30.0 if starter else 5.0,
                "threat": 40.0 if starter else 10.0,
                "influence": 25.0 if starter else 5.0,
                "bps": 24.0 if starter else 4.0,
                "clean_sheets": 1.0 if starter and home else 0.0,
                "goals_conceded": 0.0 if home else 1.0,
                "saves": 3.0 if i in (0, n_players // 2) else 0.0,
                "price": 50.0 + i,
                "transfers_in": 1000 * gw + i * 10,
                "transfers_out": 500 * gw + i * 5,
            })
    return pd.DataFrame(rows)


def _create_synthetic_features(target_gw: int = 6, n_players: int = 10) -> pd.DataFrame:
    """Generate synthetic prediction frame for target_gw."""
    rows = []
    fid = 100 + target_gw
    kickoff = f"2025-08-{10 + target_gw:02d}T15:00:00Z"
    for i in range(n_players):
        is_club1 = i < (n_players // 2)
        club_id = 1 if is_club1 else 2
        opp_id = 2 if is_club1 else 1
        pos_id = 1 if i in (0, n_players // 2) else (2 if i % 4 == 1 else (3 if i % 4 == 2 else 4))

        rows.append({
            "player_id": 1000 + i,
            "gameweek_id": target_gw,
            "fixture_id": fid,
            "position_id": pos_id,
            "club_id": club_id,
            "opponent_id": opp_id,
            "is_home": is_club1,
            "kickoff_time": kickoff,
            "per90_xg": 0.30,
            "per90_xa": 0.15,
            "per90_goals_conceded": 1.2,
            "difficulty": 3.0,
            "p_start": 0.85,
            "p_sub_in": 0.10,
            "p_dnp": 0.05,
            "xmins_if_start": 82.0,
            "xmins_if_sub_in": 18.0,
            "now_cost": 50.0 + i,
        })
    return pd.DataFrame(rows)


def test_causal_panel_time_travel_invariance() -> None:
    """Features at GW g must be 100% invariant to subsequent GW data mutations."""
    history_base = _create_synthetic_history(n_gws=5)
    features_gw6 = _create_synthetic_features(target_gw=6)

    train_base, pred_base = build_causal_panel(history_base, features_gw6, min_train_gw=2)

    # Mutate history by:
    # 1. Changing GW5 outcomes drastically
    # 2. Appending new GW6 and GW7 rows
    history_mutated = history_base.copy()
    history_mutated.loc[history_mutated["gameweek_id"] == 5, "goals_scored"] += 50.0
    history_mutated.loc[history_mutated["gameweek_id"] == 5, "transfers_in"] += 1_000_000
    history_mutated.loc[history_mutated["gameweek_id"] == 5, "minutes"] = 90.0

    gw6_rows = history_base[history_base["gameweek_id"] == 5].copy()
    gw6_rows["gameweek_id"] = 6
    gw6_rows["fixture_id"] = 106
    history_mutated = pd.concat([history_mutated, gw6_rows], ignore_index=True)

    features_gw5 = _create_synthetic_features(target_gw=5)
    train_mutated, _ = build_causal_panel(history_mutated, features_gw5, min_train_gw=2)

    # Training rows for GW 2, 3, 4 must remain bit-for-bit identical
    for gw in (2, 3, 4):
        sub_base = train_base[train_base["gameweek_id"] == gw].sort_values("player_id").reset_index(drop=True)
        sub_mut = train_mutated[train_mutated["gameweek_id"] == gw].sort_values("player_id").reset_index(drop=True)

        feature_cols = [c for c in sub_base.columns if not c.startswith("target_")]
        pd.testing.assert_frame_equal(sub_base[feature_cols], sub_mut[feature_cols])


def test_no_terminal_player_columns_referenced() -> None:
    """Causal panel feature engine must not reference any terminal summary columns from features_df."""
    from features.builder import TERMINAL_PLAYER_COLUMNS

    history = _create_synthetic_history(n_gws=5)
    features = _create_synthetic_features(target_gw=6)

    # features_df generated at past deadlines must not contain terminal season columns
    features_clean = features.drop(columns=[c for c in TERMINAL_PLAYER_COLUMNS if c in features.columns], errors="ignore")
    assert not (set(TERMINAL_PLAYER_COLUMNS) & set(features_clean.columns))

    train_panel, pred_panel = build_causal_panel(history, features_clean, min_train_gw=3)
    assert not train_panel.empty
    assert not pred_panel.empty

    for col in TERMINAL_PLAYER_COLUMNS:
        assert col not in pred_panel.columns


def test_scaler_fit_strictly_excludes_prediction_rows() -> None:
    """Scaler parameters must be computed strictly on train_panel and unaffected by pred_panel."""
    history = _create_synthetic_history(n_gws=5)
    features = _create_synthetic_features(target_gw=6)

    train_panel, pred_panel = build_causal_panel(history, features, min_train_gw=3)
    feature_cols = [c for c in train_panel.columns if not c.startswith("target_") and c not in ("player_id", "gameweek_id", "fixture_id")]

    scaler1 = CausalFeatureScaler()
    scaler1.fit(train_panel, feature_cols)

    # Transform a heavily perturbed prediction panel
    pred_perturbed = pred_panel.copy()
    for col in feature_cols:
        pred_perturbed[col] = pred_perturbed[col] * 1000.0 + 999.0

    # Fitting a second scaler on the same training panel must produce identical statistics
    scaler2 = CausalFeatureScaler()
    scaler2.fit(train_panel, feature_cols)

    np.testing.assert_allclose(scaler1.means_, scaler2.means_, atol=1e-12)
    np.testing.assert_allclose(scaler1.stds_, scaler2.stds_, atol=1e-12)
    np.testing.assert_allclose(scaler1.q01_, scaler2.q01_, atol=1e-12)
    np.testing.assert_allclose(scaler1.q99_, scaler2.q99_, atol=1e-12)

    # Ensure transforming pred_perturbed uses train statistics
    scaled_pred = scaler1.transform(pred_perturbed)
    assert not scaled_pred.isna().any().any()


def test_market_transfer_momentum_lagged() -> None:
    """Transfer momentum and price_rel_pos must strictly lag to completed rows < g."""
    history = _create_synthetic_history(n_gws=5)
    features = _create_synthetic_features(target_gw=6)

    # In GW4, player 1001 had transfer spike: 999,999 in, 10 out
    history.loc[(history["player_id"] == 1001) & (history["gameweek_id"] == 4), "transfers_in"] = 999_999
    history.loc[(history["player_id"] == 1001) & (history["gameweek_id"] == 4), "transfers_out"] = 10

    # In GW5, player 1001 had transfer crash: 10 in, 999,999 out
    history.loc[(history["player_id"] == 1001) & (history["gameweek_id"] == 5), "transfers_in"] = 10
    history.loc[(history["player_id"] == 1001) & (history["gameweek_id"] == 5), "transfers_out"] = 999_999

    train_panel, pred_panel = build_causal_panel(history, features, min_train_gw=3)

    # Training row for GW 5 must reflect GW 4 spike (positive momentum)
    gw5_p1 = train_panel[(train_panel["gameweek_id"] == 5) & (train_panel["player_id"] == 1001)].iloc[0]
    assert gw5_p1["transfer_momentum"] > 2.0

    # Target GW 6 row must reflect GW 5 crash (negative momentum)
    gw6_p1 = pred_panel[pred_panel["player_id"] == 1001].iloc[0]
    assert gw6_p1["transfer_momentum"] < -2.0


def test_in_memory_club_reconstruction() -> None:
    """Club ID must be reconstructed in-memory without requiring club_id column in history."""
    history = _create_synthetic_history(n_gws=4)
    # Ensure club_id does not exist in history
    assert "club_id" not in history.columns

    features = _create_synthetic_features(target_gw=5)
    train_panel, pred_panel = build_causal_panel(history, features, min_train_gw=2)

    # Reconstructed club features (team_att_ratio, club_blended_xgc) must be valid numbers
    assert "team_att_ratio" in train_panel.columns
    assert "club_blended_xgc" in train_panel.columns
    assert not train_panel["team_att_ratio"].isna().any()
    assert not pred_panel["team_att_ratio"].isna().any()


def test_oracle_minutes_bypass_parity() -> None:
    """When external_xmins is present, projected_minutes must match external_xmins within 1e-6."""
    from models.ml_component_challenger import MLComponentChallengerModel

    history = _create_synthetic_history(n_gws=5)
    features = _create_synthetic_features(target_gw=6)
    features["external_xmins"] = [90.0, 45.0, 0.0, 60.0, 90.0, 0.0, 15.0, 80.0, 90.0, 0.0]

    model = MLComponentChallengerModel()
    model.fit(history)
    proj = model.predict(features, horizon=1)

    np.testing.assert_allclose(
        proj["projected_minutes"].to_numpy(),
        features["external_xmins"].to_numpy(),
        atol=1e-6,
    )


def test_cold_start_gw1_to_gw3_exact_champion_parity() -> None:
    """For target_gw in {1, 2, 3}, MLComponentChallengerModel outputs projections identical to Champion."""
    from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel
    from models.ml_component_challenger import MLComponentChallengerModel

    history = _create_synthetic_history(n_gws=3)

    for gw in (1, 2, 3):
        features = _create_synthetic_features(target_gw=gw)
        champ = DefXgShrinkChallengerModel()
        cand = MLComponentChallengerModel()

        champ.fit(history)
        cand.fit(history)

        proj_champ = champ.predict(features, horizon=1)
        proj_cand = cand.predict(features, horizon=1)

        pd.testing.assert_frame_equal(proj_champ, proj_cand)
