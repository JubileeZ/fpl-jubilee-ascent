from pathlib import Path
from unittest.mock import Mock, patch

import pandas as pd
import pytest

from commands.run_model import main as run_model_main
from commands.solve import main as solve_main


def test_run_model_exposes_blend_thresholds(tmp_path: Path) -> None:
    processed = tmp_path / "data" / "processed"
    processed.mkdir(parents=True)
    pd.DataFrame([{"id": 8, "is_next": True, "finished": False}]).to_parquet(
        processed / "gameweeks.parquet",
        index=False,
    )
    pd.DataFrame().to_parquet(processed / "players.parquet", index=False)
    pd.DataFrame().to_parquet(processed / "clubs.parquet", index=False)
    model = Mock()
    model.predict.return_value = pd.DataFrame()

    with patch("commands.run_model.PROJECT_ROOT", tmp_path), \
        patch("commands.run_model.build_features", return_value=pd.DataFrame()) as build_features, \
        patch("commands.run_model.get_model", return_value=model), \
        patch("commands.run_model.export_projections"), \
        patch(
            "sys.argv",
            [
                "commands.run_model",
                "linear_baseline",
                "--horizon",
                "7",
                "--blend_start_appearances",
                "2",
                "--blend_full_appearances",
                "6",
            ],
        ):
        run_model_main()

    build_features.assert_called_once_with(
        processed,
        8,
        horizon=7,
        blend_start_appearances=2,
        blend_full_appearances=6,
        availability_overrides=tmp_path / "data" / "availability_overrides.csv",
    )


def test_solve_exposes_decay_and_hit_cost(tmp_path: Path) -> None:
    mock_prep_data = Mock(return_value={})
    with patch("commands.solve.PROJECT_ROOT", tmp_path), \
        patch("commands.solve.load_settings", return_value={"datasource": "linear_baseline", "horizon": 5}), \
        patch("commands.solve.prep_data", mock_prep_data), \
        patch("commands.solve.pad_solver_csv_horizon"), \
        patch("commands.solve.solve_multi_period_fpl", return_value=[]), \
        patch(
            "sys.argv",
            [
                "commands.solve",
                "--preseason",
                "--horizon",
                "7",
                "--decay_base",
                "0.8",
                "--hit_cost",
                "5",
            ],
        ):
        solve_main()

    options = mock_prep_data.call_args.args[1]
    assert options["horizon"] == 6
    assert options["decay_base"] == 0.8
    assert options["hit_cost"] == 5.0


def test_solve_rejects_unsupported_override(capsys) -> None:
    with patch("commands.solve.load_settings", return_value={"datasource": "linear_baseline", "horizon": 5}), \
        patch("sys.argv", ["commands.solve", "--preseason", "--not_a_solver_setting", "1"]), \
        pytest.raises(SystemExit):
        solve_main()

    assert "Unsupported solver option '--not_a_solver_setting'" in capsys.readouterr().err
