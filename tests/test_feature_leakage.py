from pathlib import Path

import pandas as pd

from features.builder import TERMINAL_PLAYER_COLUMNS
from tests.test_fixture_contract import _build, _write_fixture_data


def _with_gw1_history(root: Path) -> Path:
    processed = _write_fixture_data(root)
    fixtures = pd.read_parquet(processed / "fixtures.parquet")
    gw1 = {"id": 5, "gameweek_id": 1, "home_club_id": 1, "away_club_id": 2, "team_h_difficulty": 3, "team_a_difficulty": 3}
    pd.concat([pd.DataFrame([gw1]), fixtures]).assign(finished=lambda f: f["gameweek_id"].le(2)).to_parquet(
        processed / "fixtures.parquet", index=False
    )
    perf = pd.read_parquet(processed / "player_performances.parquet").assign(fixture_id=5, was_home=True, price=85)
    perf.to_parquet(processed / "player_performances.parquet", index=False)
    return processed


def test_as_of_features_without_snapshot_ignore_terminal_player_metadata(tmp_path: Path) -> None:
    processed = _with_gw1_history(tmp_path)
    expected = _build(processed, target_gw=2, as_of_gw=2)
    players = pd.read_parquet(processed / "players.parquet").assign(
        now_cost=140, club_id=3, status="i", penalties_order=1, total_points=250, goals_scored=30,
        expected_goals=25.0, selected_by_percent=60.0, chance_of_playing_next_round=0.0,
    )
    players.to_parquet(processed / "players.parquet", index=False)

    actual = _build(processed, target_gw=2, as_of_gw=2)

    pd.testing.assert_frame_equal(expected, actual)
    assert actual["now_cost"].eq(85).all()
    assert actual["club_id"].eq(1).all()
    assert not set(TERMINAL_PLAYER_COLUMNS) & set(actual.columns)


def test_as_of_features_exclude_target_gameweek_rows_without_deadline(tmp_path: Path) -> None:
    processed = _with_gw1_history(tmp_path)
    perf = pd.read_parquet(processed / "player_performances.parquet")
    future = perf.assign(gameweek_id=2, fixture_id=10, total_points=20, kickoff_time="2026-08-02T12:00:00Z")
    pd.concat([perf, future]).to_parquet(processed / "player_performances.parquet", index=False)

    features = _build(processed, target_gw=2, as_of_gw=2)

    assert features["avg_points_3gw"].eq(5.0).all()


def test_walkforward_fit_sees_strictly_prior_gameweeks_and_seed(tmp_path: Path, monkeypatch: object) -> None:
    from backtesting import walkforward as wf
    from backtesting.walkforward import WalkforwardConfig, run_walkforward_backtest
    from models.base import BaseModel

    seed_dir = _write_fixture_data(tmp_path / "seed")
    curr_dir = tmp_path / "curr"
    processed = _write_fixture_data(curr_dir)

    fixtures = pd.DataFrame([
        {"id": 101, "gameweek_id": 1, "home_club_id": 1, "away_club_id": 2, "team_h_difficulty": 3, "team_a_difficulty": 3, "kickoff_time": "2026-08-22T12:00:00Z", "finished": True},
        {"id": 102, "gameweek_id": 2, "home_club_id": 1, "away_club_id": 2, "team_h_difficulty": 3, "team_a_difficulty": 3, "kickoff_time": "2026-08-29T12:00:00Z", "finished": True},
        {"id": 103, "gameweek_id": 3, "home_club_id": 1, "away_club_id": 2, "team_h_difficulty": 3, "team_a_difficulty": 3, "kickoff_time": "2026-09-05T12:00:00Z", "finished": True},
    ])
    fixtures.to_parquet(processed / "fixtures.parquet", index=False)
    pd.DataFrame([
        {"id": 1, "deadline_time": "2026-08-21T17:30:00Z", "finished": True},
        {"id": 2, "deadline_time": "2026-08-28T17:30:00Z", "finished": True},
        {"id": 3, "deadline_time": "2026-09-04T17:30:00Z", "finished": True},
    ]).to_parquet(processed / "gameweeks.parquet", index=False)
    perf_rows = [
        {"player_id": 1, "fixture_id": 100 + gw, "gameweek_id": gw, "opponent_club_id": 2, "was_home": True,
         "kickoff_time": f"2026-08-{21 + gw}T12:00:00Z", "price": 85, "minutes": 90, "starts": 1,
         "total_points": 2, "goals_scored": 0, "assists": 0, "clean_sheets": 0, "goals_conceded": 0,
         "saves": 0, "penalties_saved": 0, "penalties_missed": 0, "own_goals": 0,
         "yellow_cards": 0, "red_cards": 0, "bonus": 0, "bps": 10, "influence": 1.0,
         "creativity": 1.0, "threat": 1.0, "ict_index": 3.0, "expected_goals": 0.1,
         "expected_assists": 0.1, "expected_goal_involvements": 0.2, "expected_goals_conceded": 0.5,
         "defensive_contribution": 0}
        for gw in (1, 2, 3)
    ]
    perf_rows[2]["kickoff_time"] = "2026-09-05T12:00:00Z"
    pd.DataFrame(perf_rows).to_parquet(processed / "player_performances.parquet", index=False)

    seen_fit_histories: list[list[int]] = []
    seen_seed_flags: list[tuple[int, bool]] = []

    class _SpyModel(BaseModel):
        name = "spy_isolation_model"

        def fit(self, df_history: pd.DataFrame) -> "_SpyModel":
            gws = sorted(int(g) for g in df_history["gameweek_id"].unique()) if not df_history.empty else []
            seen_fit_histories.append(gws)
            return self

        def predict(self, df_features: pd.DataFrame, horizon: int = 1) -> pd.DataFrame:
            gw = int(df_features["gameweek_id"].iloc[0])
            seen_seed_flags.append((gw, bool(df_features["has_seed"].all())))
            return pd.DataFrame([{
                "player_id": 1, "gameweek_id": gw, "projected_points": 2.0, "projected_minutes": 90.0,
                **{comp: (2.0 if comp == "xp_minutes" else 0.0) for comp in wf.LEDGER_COMPONENTS if comp != "xp_minutes"},
                "xp_minutes": 2.0,
            }])

    spy = _SpyModel()
    # Record target GW right before fit() using wrapped history_before_target or infer via iteration order
    orig_hbt = wf.history_before_target
    fit_gws_checked: list[tuple[int, list[int]]] = []

    def _wrapped_hbt(df_perf: pd.DataFrame, target_gw: int, target_deadline: object = None, require_snapshots: bool = False) -> pd.DataFrame:
        hist = orig_hbt(df_perf, target_gw, target_deadline, require_snapshots)
        gws = sorted(int(g) for g in hist["gameweek_id"].unique()) if not hist.empty else []
        fit_gws_checked.append((target_gw, gws))
        return hist

    monkeypatch.setattr(wf, "history_before_target", _wrapped_hbt)
    monkeypatch.setattr(wf, "get_model", lambda name, **kw: spy)
    run_walkforward_backtest(
        WalkforwardConfig(model_name="spy", data_dir=processed, start_gw=1, end_gw=3, seed_processed_dir=seed_dir, seed_season="2025-26")
    )

    assert fit_gws_checked == [(1, []), (2, [1]), (3, [1, 2])]
    assert seen_fit_histories == [[], [1], [1, 2]]
    assert all(all(g < target for g in gws) for target, gws in fit_gws_checked)
    assert seen_seed_flags == [(1, True), (2, True), (3, True)]
