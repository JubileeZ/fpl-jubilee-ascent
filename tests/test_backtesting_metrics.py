import pandas as pd
import pytest

from backtesting.metrics import evaluate_predictions


_LEDGER_COMPONENTS = (
    "xp_minutes",
    "xp_goals",
    "xp_assists",
    "xp_clean_sheet",
    "xp_conceded",
    "xp_saves",
    "xp_penalties_saved",
    "xp_penalties_missed",
    "xp_own_goals",
    "xp_yellow_cards",
    "xp_red_cards",
    "xp_defcon",
    "xp_bonus",
)


def test_metrics_report_bias_rank_counts_and_shortlist_quality():
    df_eval = pd.DataFrame([
        {"player_id": 1, "gameweek": 1, "projected_points": 10.0, "actual_points": 8.0, "actual_minutes": 90, "position_id": 3},
        {"player_id": 2, "gameweek": 1, "projected_points": 8.0, "actual_points": 10.0, "actual_minutes": 0, "position_id": 3},
        {"player_id": 3, "gameweek": 2, "projected_points": 4.0, "actual_points": 4.0, "actual_minutes": 45, "position_id": 4},
    ])

    metrics = evaluate_predictions(df_eval, top_k_values=(1,))

    assert metrics["sample_count"] == 3
    assert metrics["bias"] == 0.0
    assert metrics["valid_rank_gameweeks"] == 1
    assert metrics["undefined_rank_gameweeks"] == 1
    assert metrics["top_1_overlap"] == 0.5
    assert metrics["position_metrics"]["3"]["sample_count"] == 2.0
    assert set(metrics["minutes_band_metrics"]) == {"0", "1-59", "60+"}


def test_minutes_forecast_metrics_identify_zero_cameo_and_full_appearance_errors():
    df_eval = pd.DataFrame([
        {"player_id": 1, "gameweek": 1, "projected_points": 4.0, "actual_points": 0.0, "projected_minutes": 70.0, "actual_minutes": 0.0},
        {"player_id": 2, "gameweek": 1, "projected_points": 2.0, "actual_points": 1.0, "projected_minutes": 35.0, "actual_minutes": 30.0},
        {"player_id": 3, "gameweek": 1, "projected_points": 5.0, "actual_points": 6.0, "projected_minutes": 75.0, "actual_minutes": 90.0},
    ])

    metrics = evaluate_predictions(df_eval)
    minutes = metrics["minutes_forecast_metrics"]

    assert minutes["mean_projected"] == pytest.approx(60.0)
    assert minutes["mean_actual"] == pytest.approx(40.0)
    assert minutes["bias"] == pytest.approx(20.0)
    assert minutes["by_actual_band"]["0"]["mean_projected"] == pytest.approx(70.0)
    assert minutes["by_actual_band"]["1-59"]["mae"] == pytest.approx(5.0)
    assert minutes["by_actual_band"]["60+"]["bias"] == pytest.approx(-15.0)


def test_complete_component_ledgers_reconcile():
    row = {
        "player_id": 1,
        "gameweek": 1,
        **{component: 1.0 for component in _LEDGER_COMPONENTS},
        **{f"actual_{component}": 1.0 for component in _LEDGER_COMPONENTS},
    }
    row["projected_points"] = float(len(_LEDGER_COMPONENTS))
    row["actual_points"] = float(len(_LEDGER_COMPONENTS))

    metrics = evaluate_predictions(pd.DataFrame([row]))

    assert metrics["component_metrics"]["xp_saves"]["mae"] == 0.0
    assert metrics["component_metrics"]["xp_red_cards"]["bias"] == 0.0


def test_component_ledger_reconciliation_rejects_residuals():
    row = {
        "player_id": 1,
        "gameweek": 1,
        **{component: 0.0 for component in _LEDGER_COMPONENTS},
        **{f"actual_{component}": 0.0 for component in _LEDGER_COMPONENTS},
        "projected_points": 1.0,
        "actual_points": 0.0,
    }

    with pytest.raises(ValueError, match="Predicted component ledger"):
        evaluate_predictions(pd.DataFrame([row]))


def test_best_legal_xi_and_formation_stats() -> None:
    from backtesting.metrics import best_legal_xi, _formation_xi_stats, formation_xi_regret_by_gameweek

    # Create a full squad with 2 GKP, 5 DEF, 5 MID, 3 FWD (total 15 players)
    players = []
    # 2 GKPs
    players.append({"player_id": 1, "gameweek": 1, "position_id": 1, "projected_points": 5.0, "actual_points": 6.0})
    players.append({"player_id": 2, "gameweek": 1, "position_id": 1, "projected_points": 3.0, "actual_points": 2.0})
    # 5 DEFs
    for i in range(1, 6):
        players.append({"player_id": 10 + i, "gameweek": 1, "position_id": 2, "projected_points": 4.0 + i * 0.1, "actual_points": 3.0})
    # 5 MIDs
    for i in range(1, 6):
        players.append({"player_id": 20 + i, "gameweek": 1, "position_id": 3, "projected_points": 6.0 + i * 0.5, "actual_points": 5.0 + i * 1.0})
    # 3 FWDs
    for i in range(1, 4):
        players.append({"player_id": 30 + i, "gameweek": 1, "position_id": 4, "projected_points": 7.0 + i * 1.0, "actual_points": 4.0 + i * 2.0})

    df = pd.DataFrame(players)
    best_xi = best_legal_xi(df, "projected_points")
    assert len(best_xi) == 11
    # Check valid formation constraints: 1 GKP, 3-5 DEF, 2-5 MID, 1-3 FWD
    pos_counts = best_xi["position_id"].value_counts().to_dict()
    assert pos_counts[1] == 1
    assert 3 <= pos_counts[2] <= 5
    assert 2 <= pos_counts[3] <= 5
    assert 1 <= pos_counts[4] <= 3

    overlap, regret, cap_regret = _formation_xi_stats(df, target_column="actual_points")
    assert 0.0 <= overlap <= 1.0
    assert regret >= 0.0
    assert cap_regret >= 0.0

    gw_series = formation_xi_regret_by_gameweek(df, target_column="actual_points")
    assert len(gw_series) == 1
    assert gw_series.iloc[0] == regret


def test_select_legal_formation_xi_constraints_and_tie_breaking() -> None:
    from backtesting.metrics import select_legal_formation_xi

    # 20 players: 3 Arsenal (club 1) outfielders with top xP, premium costs
    players = [
        {"player_id": 1, "position_id": 1, "club_id": 2, "now_cost": 55.0, "projected_points": 5.5},
        {"player_id": 2, "position_id": 1, "club_id": 3, "now_cost": 50.0, "projected_points": 5.0},
        # Arsenal DEF
        {"player_id": 11, "position_id": 2, "club_id": 1, "now_cost": 62.0, "projected_points": 5.8},
        {"player_id": 12, "position_id": 2, "club_id": 1, "now_cost": 60.0, "projected_points": 5.7},
        # Other DEF
        {"player_id": 13, "position_id": 2, "club_id": 3, "now_cost": 72.0, "projected_points": 6.5},
        {"player_id": 14, "position_id": 2, "club_id": 4, "now_cost": 60.0, "projected_points": 5.2},
        {"player_id": 15, "position_id": 2, "club_id": 5, "now_cost": 47.0, "projected_points": 4.0},
        {"player_id": 16, "position_id": 2, "club_id": 6, "now_cost": 40.0, "projected_points": 3.2},
        # MIDs
        {"player_id": 21, "position_id": 3, "club_id": 1, "now_cost": 101.0, "projected_points": 7.5},  # 3rd Arsenal
        {"player_id": 22, "position_id": 3, "club_id": 7, "now_cost": 108.0, "projected_points": 8.0},
        {"player_id": 23, "position_id": 3, "club_id": 3, "now_cost": 126.0, "projected_points": 8.5},
        {"player_id": 24, "position_id": 3, "club_id": 8, "now_cost": 75.0, "projected_points": 6.2},
        {"player_id": 25, "position_id": 3, "club_id": 9, "now_cost": 54.0, "projected_points": 5.0},
        {"player_id": 26, "position_id": 3, "club_id": 5, "now_cost": 57.0, "projected_points": 5.0},
        # FWDs
        {"player_id": 31, "position_id": 4, "club_id": 4, "now_cost": 153.0, "projected_points": 9.5},
        {"player_id": 32, "position_id": 4, "club_id": 9, "now_cost": 91.0, "projected_points": 6.8},
        {"player_id": 33, "position_id": 4, "club_id": 10, "now_cost": 76.0, "projected_points": 5.9},
        {"player_id": 34, "position_id": 4, "club_id": 11, "now_cost": 63.0, "projected_points": 5.5},
        {"player_id": 35, "position_id": 4, "club_id": 6, "now_cost": 56.0, "projected_points": 4.5},
    ]
    df = pd.DataFrame(players)

    # 1. Constrained selection enforces <= 3 per club and <= £83.5m (835.0 units)
    xi = select_legal_formation_xi(df, "projected_points", budget_cap=835.0, max_per_club=3)
    assert len(xi) == 11
    assert xi["now_cost"].sum() <= 835.0
    club_counts = xi["club_id"].value_counts()
    assert (club_counts <= 3).all()

    # 2. Deterministic tie-breaking on tied xP (5.5): GKP 1 (£5.5m) vs GKP 2 (£5.0m)
    # Lower cost wins: GKP 2 selected, GKP 1 excluded
    df_gkp_tie = df.copy()
    df_gkp_tie.loc[df_gkp_tie["player_id"] == 2, "projected_points"] = 5.5
    xi_gkp = select_legal_formation_xi(df_gkp_tie, "projected_points", budget_cap=835.0, max_per_club=3)
    assert 2 in xi_gkp["player_id"].values
    assert 1 not in xi_gkp["player_id"].values

    # Test tie-break with identical cost: lower player_id wins (GKP 1 £5.0m vs GKP 2 £5.0m)
    df_gkp_tie.loc[df_gkp_tie["player_id"] == 1, "now_cost"] = 50.0
    xi_tie = select_legal_formation_xi(df_gkp_tie, "projected_points", budget_cap=835.0, max_per_club=3)
    assert 1 in xi_tie["player_id"].values  # ID 1 < ID 2
    assert 2 not in xi_tie["player_id"].values

    # Verify input row-order invariance
    df_shuffled = df.sample(frac=1.0, random_state=42)
    xi_shuffled = select_legal_formation_xi(df_shuffled, "projected_points", budget_cap=835.0, max_per_club=3)
    assert xi_shuffled["player_id"].tolist() == xi["player_id"].tolist()


def test_top_15_squad_selection_and_churn() -> None:
    from backtesting.metrics import select_top_15_squad, compute_top_15_squad_churn_by_gameweek

    # Create 2 gameweeks of 30 players
    base_players = []
    # 3 GKP
    for i in range(1, 4):
        base_players.append({"player_id": i, "position_id": 1, "club_id": i, "now_cost": 45.0 + i * 5.0, "projected_points": 4.0 + i * 0.5})
    # 10 DEF
    for i in range(1, 11):
        base_players.append({"player_id": 10 + i, "position_id": 2, "club_id": (i % 6) + 1, "now_cost": 45.0 + (i % 4) * 5.0, "projected_points": 4.5 + i * 0.3})
    # 10 MID
    for i in range(1, 11):
        base_players.append({"player_id": 20 + i, "position_id": 3, "club_id": (i % 6) + 1, "now_cost": 50.0 + (i % 5) * 10.0, "projected_points": 5.0 + i * 0.4})
    # 7 FWD
    for i in range(1, 8):
        base_players.append({"player_id": 30 + i, "position_id": 4, "club_id": (i % 6) + 1, "now_cost": 55.0 + (i % 4) * 15.0, "projected_points": 5.5 + i * 0.5})

    df_gw1 = pd.DataFrame(base_players)
    df_gw1["gameweek"] = 1

    squad1 = select_top_15_squad(df_gw1, "projected_points", squad_budget=1000.0, max_per_club=3)
    assert len(squad1) == 15
    assert squad1["now_cost"].sum() <= 1000.0
    pos_counts = squad1["position_id"].value_counts().to_dict()
    assert pos_counts[1] == 2
    assert pos_counts[2] == 5
    assert pos_counts[3] == 5
    assert pos_counts[4] == 3
    assert (squad1["club_id"].value_counts() <= 3).all()

    # GW2: Swap 2 players' projections to simulate turnover
    df_gw2 = df_gw1.copy()
    df_gw2["gameweek"] = 2
    # Boost player 11 (DEF) and lower player 20 (DEF)
    df_gw2.loc[df_gw2["player_id"] == 11, "projected_points"] = 12.0
    df_gw2.loc[df_gw2["player_id"] == 20, "projected_points"] = 1.0

    df_eval = pd.concat([df_gw1, df_gw2], ignore_index=True)
    churn = compute_top_15_squad_churn_by_gameweek(df_eval, "projected_points")
    assert len(churn) == 1
    assert 2 in churn.index
    assert churn.iloc[0] >= 0.0


