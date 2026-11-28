"""Tests for fixture-grain Oracle Participation State and evidence forecast guards."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest

from backtesting.data_admission import require_input
from backtesting.forecast_adapter import assert_no_oracle_inputs, predict_issue
from backtesting.walkforward import WalkforwardConfig, inject_oracle_minutes, run_walkforward_backtest
from features.builder import EVENT_RATE_MAP
from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel
from models.ml_component_challenger import MLComponentChallengerModel
from models.participation_state_hybrid import ORACLE_STATE_COLUMNS, ParticipationStateHybridModel
from test_data_admission import catalog, request
from test_forecast_inputs import retain


def _base_feature_row(**overrides: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "player_id": 1,
        "position_id": 2,
        "club_id": 1,
        "opponent_id": 2,
        "is_home": True,
        "gameweek_id": 6,
        "fixture_id": 106,
        "difficulty": 3.0,
        "chance_of_playing": 100.0,
        "has_availability_snapshot": False,
        "is_immediate_next_gw": False,
        "p_dnp": 0.4,
        "p_start": 0.5,
        "p_sub_in": 0.1,
        "xmins_if_start": 80.0,
        "xmins_if_sub_in": 20.0,
        "p_60_if_start": 0.9,
        "p_60_if_sub_in": 0.05,
        "per90_xg": 0.15,
        "per90_xa": 0.10,
        "per90_threat": 10.0,
        "per90_creativity": 10.0,
        "per90_goals": 0.1,
        "per90_assists": 0.08,
        "per90_goals_conceded": 1.2,
        "per90_saves": 0.0,
        "per90_yellow_cards": 0.05,
        "per90_red_cards": 0.0,
        "per90_penalties_saved": 0.0,
        "per90_penalties_missed": 0.0,
        "per90_own_goals": 0.0,
        "per90_defensive_contribution": 5.0,
        "now_cost": 50.0,
    }
    row.update(overrides)
    return row


def test_inject_oracle_participation_state_all_cases_and_dgw() -> None:
    from backtesting.walkforward import inject_oracle_participation_state

    df_feat = pd.DataFrame([
        # 1: Start >=60
        {"player_id": 1, "gameweek_id": 6, "fixture_id": 106, "external_xmins": 55.0},
        # 2: Start <60 (early sub off / red card)
        {"player_id": 2, "gameweek_id": 6, "fixture_id": 106, "external_xmins": 55.0},
        # 3: Sub-in <60
        {"player_id": 3, "gameweek_id": 6, "fixture_id": 106, "external_xmins": 55.0},
        # 4: Sub-in >=60 (early injury replacement)
        {"player_id": 4, "gameweek_id": 6, "fixture_id": 106, "external_xmins": 55.0},
        # 5: DNP
        {"player_id": 5, "gameweek_id": 6, "fixture_id": 106, "external_xmins": 55.0},
        # 6: Blank GW (fixture_id < 0)
        {"player_id": 6, "gameweek_id": 6, "fixture_id": -1, "external_xmins": 55.0},
        # 7: DGW fixture A and fixture B
        {"player_id": 7, "gameweek_id": 6, "fixture_id": 106, "external_xmins": 55.0},
        {"player_id": 7, "gameweek_id": 6, "fixture_id": 206, "external_xmins": 55.0},
        # 8: Missing/NaN starts fallback
        {"player_id": 8, "gameweek_id": 6, "fixture_id": 106, "external_xmins": 55.0},
        {"player_id": 9, "gameweek_id": 6, "fixture_id": 106, "external_xmins": 55.0},
    ])
    df_perf = pd.DataFrame([
        {"player_id": 1, "gameweek_id": 6, "fixture_id": 106, "minutes": 90.0, "starts": 1.0},
        {"player_id": 2, "gameweek_id": 6, "fixture_id": 106, "minutes": 40.0, "starts": 1.0},
        {"player_id": 3, "gameweek_id": 6, "fixture_id": 106, "minutes": 20.0, "starts": 0.0},
        {"player_id": 4, "gameweek_id": 6, "fixture_id": 106, "minutes": 70.0, "starts": 0.0},
        {"player_id": 5, "gameweek_id": 6, "fixture_id": 106, "minutes": 0.0, "starts": 0.0},
        {"player_id": 7, "gameweek_id": 6, "fixture_id": 106, "minutes": 90.0, "starts": 1.0},
        {"player_id": 7, "gameweek_id": 6, "fixture_id": 206, "minutes": 15.0, "starts": 0.0},
        {"player_id": 8, "gameweek_id": 6, "fixture_id": 106, "minutes": 65.0, "starts": np.nan},
        {"player_id": 9, "gameweek_id": 6, "fixture_id": 106, "minutes": 30.0, "starts": np.nan},
    ])

    injected = inject_oracle_participation_state(df_feat, df_perf, target_gw=6)
    assert "external_xmins" not in injected.columns
    assert set(ORACLE_STATE_COLUMNS).issubset(injected.columns)
    assert injected.attrs.get("oracle_participation_state") is True

    by_key = injected.set_index(["player_id", "fixture_id"])
    assert tuple(by_key.loc[(1, 106), list(ORACLE_STATE_COLUMNS)]) == (1.0, 0.0, 0.0, 90.0, 1.0)
    assert tuple(by_key.loc[(2, 106), list(ORACLE_STATE_COLUMNS)]) == (1.0, 0.0, 0.0, 40.0, 0.0)
    assert tuple(by_key.loc[(3, 106), list(ORACLE_STATE_COLUMNS)]) == (0.0, 1.0, 0.0, 20.0, 0.0)
    assert tuple(by_key.loc[(4, 106), list(ORACLE_STATE_COLUMNS)]) == (0.0, 1.0, 0.0, 70.0, 1.0)
    assert tuple(by_key.loc[(5, 106), list(ORACLE_STATE_COLUMNS)]) == (0.0, 0.0, 1.0, 0.0, 0.0)
    assert tuple(by_key.loc[(6, -1), list(ORACLE_STATE_COLUMNS)]) == (0.0, 0.0, 1.0, 0.0, 0.0)
    # DGW preserves separate fixture grain
    assert tuple(by_key.loc[(7, 106), list(ORACLE_STATE_COLUMNS)]) == (1.0, 0.0, 0.0, 90.0, 1.0)
    assert tuple(by_key.loc[(7, 206), list(ORACLE_STATE_COLUMNS)]) == (0.0, 1.0, 0.0, 15.0, 0.0)
    # NaN starts fallback to minutes >= 60
    assert tuple(by_key.loc[(8, 106), list(ORACLE_STATE_COLUMNS)]) == (1.0, 0.0, 0.0, 65.0, 1.0)
    assert tuple(by_key.loc[(9, 106), list(ORACLE_STATE_COLUMNS)]) == (0.0, 1.0, 0.0, 30.0, 0.0)

    # Missing starts column entirely also falls back cleanly
    injected_no_starts = inject_oracle_minutes(df_feat, df_perf.drop(columns=["starts"]), target_gw=6)
    by_ns = injected_no_starts.set_index(["player_id", "fixture_id"])
    assert tuple(by_ns.loc[(2, 106), list(ORACLE_STATE_COLUMNS)]) == (0.0, 1.0, 0.0, 40.0, 0.0)
    assert tuple(by_ns.loc[(4, 106), list(ORACLE_STATE_COLUMNS)]) == (1.0, 0.0, 0.0, 70.0, 1.0)


def test_participation_state_model_bypasses_scale_and_overrides_on_oracle_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import models.participation_state_hybrid as psh

    def forbid_scale(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("scale_states_to_target must be bypassed under Oracle Participation State")

    monkeypatch.setattr(psh, "scale_states_to_target", forbid_scale)

    # Include ADR 0056 / 0010 immediate hard-DNP overrides and xmins_cap to verify bypass
    df = pd.DataFrame([
        _base_feature_row(
            player_id=1, position_id=2, is_immediate_next_gw=True, status="i", chance_of_playing=0.0, xmins_cap=10.0,
            oracle_p_start=1.0, oracle_p_sub_in=0.0, oracle_p_dnp=0.0, oracle_minutes=40.0, oracle_p_60=0.0,
        ),
        _base_feature_row(
            player_id=2, position_id=2, is_immediate_next_gw=True, status="s", chance_of_playing=0.0,
            oracle_p_start=0.0, oracle_p_sub_in=1.0, oracle_p_dnp=0.0, oracle_minutes=20.0, oracle_p_60=0.0,
        ),
        _base_feature_row(
            player_id=3, position_id=2, is_immediate_next_gw=True, status="u", chance_of_playing=0.0,
            oracle_p_start=0.0, oracle_p_sub_in=1.0, oracle_p_dnp=0.0, oracle_minutes=70.0, oracle_p_60=1.0,
        ),
        _base_feature_row(
            player_id=4, position_id=2,
            oracle_p_start=0.0, oracle_p_sub_in=0.0, oracle_p_dnp=1.0, oracle_minutes=0.0, oracle_p_60=0.0,
        ),
    ])

    preds = ParticipationStateHybridModel().predict(df, horizon=1).set_index("player_id")
    np.testing.assert_allclose(preds["projected_minutes"], [40.0, 20.0, 70.0, 0.0], atol=1e-6)
    np.testing.assert_allclose(preds["xp_minutes"], [1.0, 1.0, 2.0, 0.0], atol=1e-6)
    # Start <60 must have 0 clean sheet xP
    assert preds.loc[1, "xp_clean_sheet"] == pytest.approx(0.0, abs=1e-9)
    # Sub-in >=60 must receive positive clean sheet xP
    assert preds.loc[3, "xp_clean_sheet"] > 0.0
    assert preds.loc[4, "projected_points"] == pytest.approx(0.0, abs=1e-9)


def test_partial_oracle_columns_raises() -> None:
    df = pd.DataFrame([_base_feature_row(oracle_p_start=1.0, oracle_minutes=90.0)])
    with pytest.raises(ValueError, match="Oracle state columns"):
        ParticipationStateHybridModel().predict(df, horizon=1)


def test_ml_and_champion_models_exact_oracle_parity() -> None:
    from test_ml_panel_leakage import _create_synthetic_features, _create_synthetic_history

    history = _create_synthetic_history(n_gws=5)
    features = _create_synthetic_features(target_gw=6)
    n = len(features)
    # Mix all 5 cases across players
    mins = np.array([90.0, 40.0, 20.0, 70.0, 0.0, 90.0, 15.0, 80.0, 90.0, 0.0])[:n]
    starts = np.array([1.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 1.0, 1.0, 0.0])[:n]
    features["oracle_p_start"] = starts
    features["oracle_p_sub_in"] = np.where((starts == 0.0) & (mins > 0.0), 1.0, 0.0)
    features["oracle_p_dnp"] = np.where(mins <= 0.0, 1.0, 0.0)
    features["oracle_minutes"] = mins
    features["oracle_p_60"] = np.where(mins >= 60.0, 1.0, 0.0)
    features["is_immediate_next_gw"] = True
    features["status"] = "i"
    features["chance_of_playing"] = 0.0

    expected_xp_mins = np.where(mins >= 60.0, 2.0, np.where(mins > 0.0, 1.0, 0.0))

    for model in (DefXgShrinkChallengerModel(), MLComponentChallengerModel()):
        model.fit(history)
        proj = model.predict(features, horizon=1)
        np.testing.assert_allclose(proj["projected_minutes"].to_numpy(), mins, atol=1e-6)
        np.testing.assert_allclose(proj["xp_minutes"].to_numpy(), expected_xp_mins, atol=1e-6)


@pytest.mark.parametrize(
    "mutator",
    [
        lambda df: df.assign(external_xmins=90.0),
        lambda df: df.assign(oracle_minutes=90.0),
        lambda df: df.assign(
            oracle_p_start=1.0, oracle_p_sub_in=0.0, oracle_p_dnp=0.0, oracle_minutes=90.0, oracle_p_60=1.0
        ),
        lambda df: df.assign(actual_start=1.0),
        lambda df: df.assign(actual_minutes=90.0),
        lambda df: _with_attr(df, "oracle_participation_state", True),
        lambda df: _with_attr(df, "oracle_minutes", True),
    ],
)
def test_assert_no_oracle_inputs_rejects_all_oracle_surfaces(mutator: Any) -> None:
    df = mutator(pd.DataFrame([{"player_id": 1, "gameweek_id": 1}]))
    with pytest.raises(ValueError, match="prohibited in evidence forecasts"):
        assert_no_oracle_inputs(df)


def _with_attr(df: pd.DataFrame, key: str, value: Any) -> pd.DataFrame:
    out = df.copy()
    out.attrs[key] = value
    return out


def test_predict_issue_rejects_oracle_participation_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import backtesting.forecast_adapter as fa

    value = request()
    entries = catalog(value)
    origin = value["origins"][0]
    origin["season"] = "2024-25"
    origin["native_rules"] = "native-2024-25-v1"
    base = json.loads(entries[value["authority_digest"]])
    base.update({"version": 2, "season": "2024-25", "native_rules": origin["native_rules"]})
    event = {name: 0.0 for name, _ in EVENT_RATE_MAP}
    seed_row = {
        **event, "player_id": 1, "fixture_id": 99, "gameweek_id": 38,
        "kickoff_time": "2024-05-19T00:00:00Z", "minutes": 90, "total_points": 3,
        "starts": 1, "was_home": True, "opponent_club_id": 3,
    }
    source = {
        "version": 2, "url": "synthetic://" + "a" * 40, "revision": "a" * 40,
        "parser_version": "1", "seed_season": "2023-24", "seed_registry_complete": True,
        "published_at": "2025-01-01T10:00:00Z", "captured_at": "2025-01-01T11:00:00Z",
        "timestamp_uncertainty_seconds": 0, "seed_mapping": base["seed_mapping"],
        "tables": {
            "clubs": [{"id": n, "strength": 1000, "short_name": f"C{n}"} for n in (1, 2, 3)],
            "player_metadata": [{"id": n, "web_name": f"Player {n}"} for n in (1, 2)],
            "target_fixtures": [
                {"id": f["id"], "gameweek_id": f["gw"], "home_club_id": f["home_club"], "away_club_id": f["away_club"],
                 "team_h_difficulty": 3, "team_a_difficulty": 3}
                for f in origin["fixtures"]
            ],
            "history": [], "history_fixtures": [],
            "seed_players": [{"seed_key": f"s{n}", "id": n, "club_id": n, "position_id": n, "now_cost": 50} for n in (1, 2)],
            "seed_history": [seed_row],
            "seed_fixtures": [{"id": 99, "gameweek_id": 38, "home_club_id": 1, "away_club_id": 3, "finished": True, "finalized_at": "2024-05-20T00:00:00Z"}],
        },
    }
    source_digest = retain(entries, source)
    base["training_source_digests"] = [source_digest]
    value["authority_digest"] = retain(entries, base)
    for item in origin["sources"]:
        item["parent_manifest"] = value["authority_digest"]
    cap = require_input(value, entries, "2024-25", 1)
    authority = {
        "version": 2, "mode": "synthetic", "input_digest": cap.input_digest,
        "season": "2024-25", "gw": 1, "seed_identity": origin["seed_identity"],
        "source_digest": source_digest,
    }
    authority_digest = retain(entries, authority)

    real_build_features = fa.build_features

    def oracle_tainted_features(*args: Any, **kwargs: Any) -> pd.DataFrame:
        df = real_build_features(*args, **kwargs)
        df["oracle_minutes"] = 90.0
        return df

    monkeypatch.setattr(fa, "build_features", oracle_tainted_features)
    with pytest.raises(ValueError, match="prohibited in evidence forecasts"):
        predict_issue(cap, value, entries, authority_digest, tmp_path)


def test_walkforward_oracle_minutes_enforces_parity_and_dual_pool_archive_smoke(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archive_dir = Path("data/archive/2025-26/processed")
    if not (archive_dir / "player_performances.parquet").exists():
        pytest.skip("2025-26 archive not present")

    res = run_walkforward_backtest(
        WalkforwardConfig(
            model_name="def_xg_shrink_challenger",
            data_dir=archive_dir,
            start_gw=6,
            end_gw=7,
            oracle_minutes=True,
        )
    )
    assert res.metrics["oracle_minutes_enabled"] is True
    assert res.metrics["oracle_participation_state_enabled"] is True
    pools = res.metrics["oracle_event_pools"]
    assert set(pools) == {"all_players", "appeared"}
    assert pools["all_players"]["sample_count"] > pools["appeared"]["sample_count"] > 0
    assert "oracle_formation_xi_regret" in pools["appeared"]
    assert "mse_share" in pools["appeared"]["component_metrics"]["xp_goals"]

    # Verify parity assertion fails loudly if a model ignores oracle minutes
    import backtesting.walkforward as wf
    from models.base import BaseModel

    class BadModel(BaseModel):
        @property
        def name(self) -> str:
            return "bad_oracle_model"

        def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
            out = features_df[["player_id", "gameweek_id", "fixture_id"]].copy()
            out["projected_points"] = 1.0
            out["projected_minutes"] = 90.0  # ignores oracle_minutes=0.0
            out["xp_minutes"] = 2.0
            return out

    monkeypatch.setattr(wf, "get_model", lambda _name: BadModel())
    with pytest.raises(ValueError, match="Oracle Participation State parity"):
        run_walkforward_backtest(
            WalkforwardConfig(
                model_name="bad_oracle_model",
                data_dir=archive_dir,
                start_gw=6,
                end_gw=6,
                oracle_minutes=True,
            )
        )
