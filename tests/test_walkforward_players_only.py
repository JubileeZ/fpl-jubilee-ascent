from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

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


def test_backtest_cli_merges_cost_and_club_and_excludes_am(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from commands.backtest import main as backtest_main

    # 15 players + 1 AM (900) across 2 GWs so formation XI, captaincy, and churn are defined
    pids = list(range(1, 16)) + [900]
    pos = [1, 1, 2, 2, 2, 2, 2, 3, 3, 3, 3, 3, 4, 4, 4, 5]
    costs = [45] * 16
    clubs = [(i % 10) + 1 for i in range(16)]

    def _feat_gw(gw: int) -> pd.DataFrame:
        return pd.DataFrame({
            "player_id": pids,
            "position_id": pos,
            "now_cost": costs,
            "club_id": clubs,
            "gameweek_id": [gw] * len(pids),
            "fixture_id": [10 * gw] * len(pids),
        })

    class _RankedModel:
        name = "ranked"

        def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
            out = features_df[["player_id", "fixture_id", "gameweek_id"]].copy()
            out["projected_points"] = 20.0 - out["player_id"].astype(float) * 0.5
            out["projected_minutes"] = 90.0
            for component in LEDGER_COMPONENTS:
                if component == "xp_minutes":
                    out[component] = 2.0
                elif component == "xp_bonus":
                    out[component] = out["projected_points"] - 2.0
                else:
                    out[component] = 0.0
            return out

    perf_rows = []
    for gw in (1, 2):
        for pid in pids:
            pts = max(2, 17 - pid) if pid < 900 else 15
            perf_rows.append({
                "player_id": pid,
                "gameweek_id": gw,
                "fixture_id": 10 * gw,
                "minutes": 90 if pid < 900 else 0,
                "bonus": pts - 2 if pid < 900 else 15,
                "total_points": pts,
            })
    pd.DataFrame(perf_rows).to_parquet(tmp_path / "player_performances.parquet")

    with (
        patch("commands.backtest.build_features", side_effect=lambda *a, target_gw, **k: _feat_gw(target_gw)),
        patch("commands.backtest.get_model", return_value=_RankedModel()),
        patch("sys.argv", ["backtest.py", "ranked", "--gw_range", "1-2", "--data_dir", str(tmp_path)]),
    ):
        backtest_main()

    out = capsys.readouterr().out
    # 15 players * 2 GWs = 30 samples (AM player 900 excluded)
    assert "Sample Count    : 30" in out
    assert "Formation XI Regret" in out
    assert "Captaincy Regret" in out
    assert "Top-15 Squad Churn" in out




