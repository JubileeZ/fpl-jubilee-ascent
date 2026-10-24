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


def test_walkforward_resolves_seed_season(tmp_path: Path) -> None:
    archive = tmp_path / "archive"
    archive_seed = archive / "2023-24" / "processed"
    archive_seed.mkdir(parents=True)
    (archive_seed / "players.parquet").touch()
    data_dir = archive / "2024-25" / "processed"
    data_dir.mkdir(parents=True)

    perf = pd.DataFrame({
        "player_id": [1, 1],
        "gameweek_id": [1, 2],
        "fixture_id": [10, 20],
        "minutes": [90, 90],
        "total_points": [2, 2],
    })
    perf.to_parquet(data_dir / "player_performances.parquet")

    captured_seed_dirs: list[Path | None] = []

    def fake_build_features(*args: object, **kwargs: object) -> pd.DataFrame:
        captured_seed_dirs.append(kwargs.get("seed_processed_dir"))  # type: ignore[arg-type]
        target_gw = int(str(kwargs.get("target_gw", 1)))
        return _features(target_gw)

    config = WalkforwardConfig(
        model_name="flat",
        data_dir=data_dir,
        start_gw=1,
        end_gw=2,
        seed_season="2023-24",
        eval_target="actual_points",
    )
    with (
        patch("backtesting.walkforward.build_features", side_effect=fake_build_features),
        patch("backtesting.walkforward.get_model", return_value=_FlatModel()),
    ):
        run_walkforward_backtest(config)

    assert len(captured_seed_dirs) == 2
    assert all(d == archive_seed for d in captured_seed_dirs)


def test_walkforward_raises_on_missing_seed_season(tmp_path: Path) -> None:
    import pytest

    data_dir = tmp_path / "archive" / "2024-25" / "processed"
    data_dir.mkdir(parents=True)
    perf = pd.DataFrame(
        {"player_id": [1], "gameweek_id": [1], "fixture_id": [10], "minutes": [90], "total_points": [2]}
    )
    perf.to_parquet(data_dir / "player_performances.parquet")
    config = WalkforwardConfig(
        model_name="flat",
        data_dir=data_dir,
        start_gw=1,
        end_gw=1,
        seed_season="nonexistent-season",
        eval_target="actual_points",
    )
    with (
        patch("backtesting.walkforward.get_model", return_value=_FlatModel()),
        pytest.raises(FileNotFoundError, match="Prior-season archive not found"),
    ):
        run_walkforward_backtest(config)



