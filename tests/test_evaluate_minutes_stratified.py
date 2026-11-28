"""Tests for state-stratified and multi-horizon xMins evaluation (Track B / #251)."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pandas as pd
import pytest

from commands.evaluate_minutes import (
    MinutesMetrics,
    build_minutes_evaluation_frame,
    compute_minutes_metrics,
    compute_stratified_minutes_metrics,
    evaluate_minutes_from_eval_frames,
    extract_minutes_prediction_frame,
    run_minutes_walkforward_evaluation,
)
from models.base import BaseModel


def _build_stratified_eval_df() -> pd.DataFrame:
    # 4 players:
    # P1 (GKP): actual Start (90m), p_start=0.8 (>=0.5 -> TP), xmins_if_start=85, p_60_if_start=0.9
    # P2 (DEF): actual Start (45m), p_start=0.3 (<0.5 -> FN / Missed Starter), xmins_if_start=75, p_60_if_start=0.8
    # P3 (MID): actual Sub-in (20m), p_start=0.6 (>=0.5 -> FP / False Start), p_sub=0.3, xmins_if_sub_in=25
    # P4 (FWD): actual DNP (0m), p_start=0.1, p_sub=0.1, p_dnp=0.8, projected_minutes=10.0
    return pd.DataFrame([
        {
            "player_id": 1, "gameweek_id": 5, "fixture_id": 10, "position_id": 1,
            "projected_minutes": 70.0, "actual_minutes": 90.0,
            "p_start": 0.8, "p_sub_in": 0.1, "p_dnp": 0.1, "p_60_plus": 0.72,
            "xmins_if_start": 85.0, "xmins_if_sub_in": 15.0, "p_60_if_start": 0.9, "p_60_if_sub_in": 0.0,
            "actual_start": 1.0, "actual_sub_in": 0.0, "actual_dnp": 0.0,
        },
        {
            "player_id": 2, "gameweek_id": 5, "fixture_id": 10, "position_id": 2,
            "projected_minutes": 30.0, "actual_minutes": 45.0,
            "p_start": 0.3, "p_sub_in": 0.4, "p_dnp": 0.3, "p_60_plus": 0.24,
            "xmins_if_start": 75.0, "xmins_if_sub_in": 20.0, "p_60_if_start": 0.8, "p_60_if_sub_in": 0.0,
            "actual_start": 1.0, "actual_sub_in": 0.0, "actual_dnp": 0.0,
        },
        {
            "player_id": 3, "gameweek_id": 5, "fixture_id": 11, "position_id": 3,
            "projected_minutes": 50.0, "actual_minutes": 20.0,
            "p_start": 0.6, "p_sub_in": 0.3, "p_dnp": 0.1, "p_60_plus": 0.50,
            "xmins_if_start": 78.0, "xmins_if_sub_in": 25.0, "p_60_if_start": 0.85, "p_60_if_sub_in": 0.05,
            "actual_start": 0.0, "actual_sub_in": 1.0, "actual_dnp": 0.0,
        },
        {
            "player_id": 4, "gameweek_id": 5, "fixture_id": 11, "position_id": 4,
            "projected_minutes": 10.0, "actual_minutes": 0.0,
            "p_start": 0.1, "p_sub_in": 0.1, "p_dnp": 0.8, "p_60_plus": 0.05,
            "xmins_if_start": 78.0, "xmins_if_sub_in": 18.0, "p_60_if_start": 0.8, "p_60_if_sub_in": 0.0,
            "actual_start": 0.0, "actual_sub_in": 0.0, "actual_dnp": 1.0,
        },
    ])


def test_stratified_minutes_metrics_exact_calculations_and_positions() -> None:
    df = _build_stratified_eval_df()
    metrics = compute_minutes_metrics(df)
    strat = metrics.stratified
    assert strat == compute_stratified_minutes_metrics(df)

    # States calibration
    assert strat["states"]["start"]["sample_count"] == 2
    assert strat["states"]["start"]["actual_rate"] == pytest.approx(0.5)
    assert strat["states"]["start"]["mean_predicted_prob"] == pytest.approx(0.45)
    assert strat["states"]["start"]["calibration_error"] == pytest.approx(-0.05)
    assert strat["states"]["start"]["mean_prob_when_actual"] == pytest.approx(0.55)

    assert strat["states"]["sub_in"]["sample_count"] == 1
    assert strat["states"]["sub_in"]["mean_prob_when_actual"] == pytest.approx(0.3)
    assert strat["states"]["dnp"]["sample_count"] == 1
    assert strat["states"]["dnp"]["mean_prob_when_actual"] == pytest.approx(0.8)

    # False-Start % = FP / (TP + FP) = 1 / (1 + 1) = 0.5
    # Missed-Starter % = FN / (TP + FN) = 1 / (1 + 1) = 0.5
    assert strat["false_start_rate"] == pytest.approx(0.5)
    assert strat["missed_starter_rate"] == pytest.approx(0.5)

    # Conditional duration:
    # Start: P1 (85 - 90 = -5), P2 (75 - 45 = +30) -> MAE = 17.5, Bias = +12.5
    assert strat["conditional_duration"]["start"]["sample_count"] == 2
    assert strat["conditional_duration"]["start"]["mae"] == pytest.approx(17.5)
    assert strat["conditional_duration"]["start"]["bias"] == pytest.approx(12.5)
    # Sub-in: P3 (25 - 20 = +5)
    assert strat["conditional_duration"]["sub_in"]["sample_count"] == 1
    assert strat["conditional_duration"]["sub_in"]["mae"] == pytest.approx(5.0)
    # DNP: P4 (projected_minutes=10.0, p_dnp=0.8)
    assert strat["conditional_duration"]["dnp"]["sample_count"] == 1
    assert strat["conditional_duration"]["dnp"]["mae"] == pytest.approx(10.0)
    assert strat["conditional_duration"]["dnp"]["mean_p_dnp"] == pytest.approx(0.8)

    # p_60_if_start on actual_start == 1: P1 (0.9 vs 1.0), P2 (0.8 vs 0.0)
    p60 = strat["p_60_if_start"]
    assert p60["sample_count"] == 2
    assert p60["mean_predicted"] == pytest.approx(0.85)
    assert p60["actual_rate"] == pytest.approx(0.5)
    assert p60["brier"] == pytest.approx((0.1**2 + 0.8**2) / 2.0)

    # Position splits
    assert set(strat["by_position"]) == {"GKP", "DEF", "MID", "FWD"}
    assert strat["by_position"]["GKP"]["sample_count"] == 1
    assert strat["by_position"]["GKP"]["mae"] == pytest.approx(20.0)
    assert strat["by_position"]["DEF"]["missed_starter_rate"] == pytest.approx(1.0)
    assert strat["by_position"]["MID"]["false_start_rate"] == pytest.approx(1.0)

    # JSON serialization must never produce NaN/Infinity
    json.dumps(strat, allow_nan=False)


def test_stratified_edge_cases_and_backwards_compatibility() -> None:
    # Legacy 18-field MinutesMetrics constructor still works unchanged
    legacy = MinutesMetrics(
        sample_count=10, active_count=5, mae=10.0, rmse=12.0, bias=0.0,
        overall_mae=5.0, overall_rmse=8.0, overall_bias=0.0,
        brier_score=0.2, brier_start=0.1, brier_sub=0.05, brier_dnp=0.05,
        starter_auc=0.9, starter_precision=0.8, starter_recall=0.8, starter_f1=0.8,
        mean_projected=30.0, mean_actual=30.0,
    )
    assert legacy.stratified == {}

    # Edge case: zero predicted starters, zero sub-ins, no optional columns
    minimal = pd.DataFrame([
        {
            "projected_minutes": 0.0, "actual_minutes": 0.0,
            "p_dnp": 1.0, "p_start": 0.0, "p_sub_in": 0.0, "p_60_plus": 0.0,
            "actual_dnp": 1.0, "actual_start": 0.0, "actual_sub_in": 0.0,
        }
    ])
    strat = compute_minutes_metrics(minimal).stratified
    assert strat["false_start_rate"] is None
    assert strat["missed_starter_rate"] is None
    assert strat["conditional_duration"]["start"]["sample_count"] == 0
    assert strat["conditional_duration"]["sub_in"]["sample_count"] == 0
    assert strat["p_60_if_start"]["sample_count"] == 0
    assert strat["by_position"] == {}
    json.dumps(strat, allow_nan=False)

    # evaluate_minutes_from_eval_frames signature & behavior intact
    cand = pd.DataFrame({
        "player_id": [1, 2], "gameweek": [1, 1],
        "projected_minutes": [85.0, 0.0], "actual_minutes": [90.0, 0.0],
    })
    champ = pd.DataFrame({
        "player_id": [1, 2], "gameweek": [1, 1],
        "projected_minutes": [70.0, 0.0], "actual_minutes": [90.0, 0.0],
    })
    verdict = evaluate_minutes_from_eval_frames(champ, cand)
    assert verdict.horizon == 1
    assert verdict.delta_mae == pytest.approx(15.0)


def test_extract_and_build_minutes_frame_preserves_conditional_and_horizon_fields() -> None:
    class RichDummyModel(BaseModel):
        @property
        def name(self) -> str:
            return "rich_dummy"

        def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
            return pd.DataFrame({
                "player_id": [1, 1, 2],
                "gameweek_id": [5, 6, 5],
                "fixture_id": [10, 20, 10],
                "projected_minutes": [80.0, 75.0, 10.0],
                "p_dnp": [0.05, 0.10, 0.80],
                "p_start": [0.90, 0.85, 0.05],
                "p_sub_in": [0.05, 0.05, 0.15],
                "xmins_if_start": [85.0, 82.0, 78.0],
                "xmins_if_sub_in": [18.0, 18.0, 18.0],
                "p_60_if_start": [0.92, 0.88, 0.80],
                "p_60_if_sub_in": [0.02, 0.02, 0.01],
            })

    feat = pd.DataFrame({
        "player_id": [1, 1, 2],
        "gameweek_id": [5, 6, 5],
        "fixture_id": [10, 20, 10],
        "position_id": [2, 2, 3],
    })
    preds = extract_minutes_prediction_frame(RichDummyModel(), feat, horizon=2, issue_gw=5)
    assert {"xmins_if_start", "xmins_if_sub_in", "p_60_if_start", "p_60_if_sub_in", "position_id", "horizon_step"}.issubset(preds.columns)
    assert preds["horizon_step"].tolist() == [0, 1, 0]

    # build_minutes_evaluation_frame filters strictly to target_gw and handles starts==1 & minutes==0
    perf = pd.DataFrame([
        {"player_id": 1, "gameweek_id": 5, "fixture_id": 10, "minutes": 0.0, "starts": 1.0},
        {"player_id": 2, "gameweek_id": 5, "fixture_id": 10, "minutes": 25.0, "starts": 0.0},
        {"player_id": 1, "gameweek_id": 6, "fixture_id": 20, "minutes": 90.0, "starts": 1.0},
    ])
    gw5_eval = build_minutes_evaluation_frame(preds, perf, target_gw=5)
    assert len(gw5_eval) == 2
    assert set(gw5_eval["gameweek_id"]) == {5}
    p1 = gw5_eval[gw5_eval["player_id"] == 1].iloc[0]
    # starts==1 with minutes==0 must resolve to DNP, not Start
    assert (p1["actual_start"], p1["actual_sub_in"], p1["actual_dnp"]) == (0.0, 0.0, 1.0)


def _write_synthetic_processed_dir(data_dir: Path, n_gws: int = 5) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    clubs = pd.DataFrame([
        {"id": 1, "name": "ClubA", "short_name": "CA", "strength": 1100},
        {"id": 2, "name": "ClubB", "short_name": "CB", "strength": 1050},
    ])
    players = pd.DataFrame([
        {"id": 1, "web_name": "GK1", "club_id": 1, "position_id": 1, "now_cost": 50, "status": "a", "chance_of_playing_next_round": 100.0},
        {"id": 2, "web_name": "DEF1", "club_id": 1, "position_id": 2, "now_cost": 55, "status": "a", "chance_of_playing_next_round": 100.0},
        {"id": 3, "web_name": "MID1", "club_id": 2, "position_id": 3, "now_cost": 65, "status": "a", "chance_of_playing_next_round": 100.0},
        {"id": 4, "web_name": "FWD1", "club_id": 2, "position_id": 4, "now_cost": 75, "status": "a", "chance_of_playing_next_round": 100.0},
    ])
    gameweeks = pd.DataFrame([
        {"id": gw, "deadline_time": f"2025-08-{10 + gw:02d}T11:00:00Z", "finished": True}
        for gw in range(1, n_gws + 1)
    ])
    fixtures = pd.DataFrame([
        {
            "id": 100 + gw, "gameweek_id": gw, "home_club_id": 1, "away_club_id": 2,
            "team_h_difficulty": 3, "team_a_difficulty": 3,
            "finished": True, "finished_provisional": True,
            "kickoff_time": f"2025-08-{10 + gw:02d}T15:00:00Z",
        }
        for gw in range(1, n_gws + 1)
    ])
    perf_rows = []
    for gw in range(1, n_gws + 1):
        for pid, mins, starts in [(1, 90.0, 1.0), (2, 85.0, 1.0), (3, 20.0, 0.0), (4, 0.0, 0.0)]:
            club = 1 if pid in (1, 2) else 2
            opp = 2 if club == 1 else 1
            perf_rows.append({
                "player_id": pid,
                "gameweek_id": gw,
                "fixture_id": 100 + gw,
                "was_home": club == 1,
                "opponent_club_id": opp,
                "kickoff_time": f"2025-08-{10 + gw:02d}T15:00:00Z",
                "minutes": mins,
                "starts": starts,
                "total_points": 6 if mins >= 60 else (1 if mins > 0 else 0),
                "goals_scored": 0, "assists": 0, "clean_sheets": 1 if mins >= 60 else 0,
                "goals_conceded": 0, "saves": 2 if pid == 1 else 0,
                "penalties_saved": 0, "penalties_missed": 0, "own_goals": 0,
                "yellow_cards": 0, "red_cards": 0, "bonus": 0, "bps": 15,
                "expected_goals": 0.1, "expected_assists": 0.05, "expected_goals_conceded": 0.8,
                "threat": 10.0, "creativity": 10.0, "influence": 15.0,
                "defensive_contribution": 5.0,
            })
    clubs.to_parquet(data_dir / "clubs.parquet", index=False)
    players.to_parquet(data_dir / "players.parquet", index=False)
    gameweeks.to_parquet(data_dir / "gameweeks.parquet", index=False)
    fixtures.to_parquet(data_dir / "fixtures.parquet", index=False)
    pd.DataFrame(perf_rows).to_parquet(data_dir / "player_performances.parquet", index=False)


def test_multi_horizon_walkforward_and_cli_table_json(tmp_path: Path) -> None:
    data_dir = tmp_path / "processed"
    _write_synthetic_processed_dir(data_dir, n_gws=5)

    v1 = run_minutes_walkforward_evaluation(
        candidate_model_name="learned_start_challenger",
        champion_model_name="def_xg_shrink_challenger",
        data_dir=data_dir,
        start_gw=2,
        end_gw=5,
        horizon=1,
    )
    v4 = run_minutes_walkforward_evaluation(
        candidate_model_name="learned_start_challenger",
        champion_model_name="def_xg_shrink_challenger",
        data_dir=data_dir,
        start_gw=2,
        end_gw=5,
        horizon=4,
    )
    assert v4.horizon == 4
    assert list(v4.horizon_decay) == ["t+0", "t+1", "t+2", "t+3"]
    assert v4.delta_mae == pytest.approx(v1.delta_mae)
    assert v4.candidate_metrics.mae == pytest.approx(v1.candidate_metrics.mae)
    assert v4.horizon_decay["t+0"]["delta_mae"] == pytest.approx(v1.delta_mae)
    assert "stratified" in v4.horizon_decay["t+1"]["candidate"]

    # CLI JSON & Table invocation
    out_json = tmp_path / "eval.json"
    res_json = subprocess.run(
        [
            sys.executable, "-m", "commands.evaluate_minutes",
            "--model", "learned_start_challenger",
            "--champion", "def_xg_shrink_challenger",
            "--data-dir", str(data_dir),
            "--start-gw", "2", "--end-gw", "5",
            "--horizon", "3",
            "--format", "json",
            "--output-json", str(out_json),
        ],
        capture_output=True, text=True, check=True,
    )
    payload = json.loads(res_json.stdout)
    assert payload["horizon"] == 3
    assert set(payload["horizon_decay"]) == {"t+0", "t+1", "t+2"}
    assert "stratified" in payload["candidate"]
    assert out_json.exists()

    res_table = subprocess.run(
        [
            sys.executable, "-m", "commands.evaluate_minutes",
            "--model", "learned_start_challenger",
            "--champion", "def_xg_shrink_challenger",
            "--data-dir", str(data_dir),
            "--start-gw", "2", "--end-gw", "5",
            "--horizon", "3",
            "--format", "table",
        ],
        capture_output=True, text=True, check=True,
    )
    assert "State-Stratified" in res_table.stdout
    assert "Position Splits" in res_table.stdout
    assert "Multi-Horizon Decay" in res_table.stdout
