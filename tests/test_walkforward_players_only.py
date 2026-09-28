from pathlib import Path
from unittest.mock import patch

import pandas as pd

from backtesting.walkforward import LEDGER_COMPONENTS, WalkforwardConfig, run_walkforward_backtest


class _FlatModel:
    name = "flat"

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        out = features_df[["player_id", "fixture_id", "gameweek_id"]].copy()
        out["projected_points"], out["projected_minutes"] = 2.0, 90.0
        for component in LEDGER_COMPONENTS:
            out[component] = 2.0 if component == "xp_minutes" else 0.0
        return out


def _features(target_gw: int) -> pd.DataFrame:
    return pd.DataFrame({
        "player_id": [1, 2, 900],
        "position_id": [3, 4, 5],
        "gameweek_id": [target_gw] * 3,
        "fixture_id": [10 * target_gw] * 3,
    })


def test_walkforward_excludes_assistant_manager_elements(tmp_path: Path) -> None:
    perf = pd.DataFrame({
        "player_id": [1, 2, 900, 1, 2, 900],
        "gameweek_id": [1, 1, 1, 2, 2, 2],
        "fixture_id": [10, 10, 10, 20, 20, 20],
        "minutes": [90, 90, 0, 90, 90, 0],
        "total_points": [2, 2, 9, 2, 2, 8],
    })
    perf.to_parquet(tmp_path / "player_performances.parquet")
    config = WalkforwardConfig(model_name="flat", data_dir=tmp_path, start_gw=1, end_gw=2, eval_target="actual_points")
    with (
        patch("backtesting.walkforward.build_features", side_effect=lambda *a, target_gw, **k: _features(target_gw)),
        patch("backtesting.walkforward.get_model", return_value=_FlatModel()),
    ):
        result = run_walkforward_backtest(config)
    assert set(result.df_eval["player_id"]) == {1, 2}
