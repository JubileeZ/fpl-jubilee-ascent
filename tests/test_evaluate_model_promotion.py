from pathlib import Path
from unittest.mock import patch

import pandas as pd

from backtesting.promotion import CONFIRMATION_BOOTSTRAP_MIN_P
from backtesting.walkforward import WalkforwardResult
from commands.evaluate_model_promotion import evaluate_and_apply
from models.selection import ModelSelection, load_model_selection, save_model_selection


def _result(model_name: str, *, worse: bool) -> WalkforwardResult:
    error = 2.0 if worse else 0.5
    df_eval = pd.DataFrame(
        [
            {
                "player_id": 1,
                "gameweek": 2,
                "projected_points": 4.0 + error,
                "actual_points": 4.0,
                "process_points": 4.0,
                "blended_points": 4.0,
                "projected_minutes": 70.0,
                "actual_minutes": 60.0,
            },
            {
                "player_id": 2,
                "gameweek": 10,
                "projected_points": 5.0 + error,
                "actual_points": 5.0,
                "process_points": 5.0,
                "blended_points": 5.0,
                "projected_minutes": 70.0,
                "actual_minutes": 60.0,
            },
            {
                "player_id": 3,
                "gameweek": 25,
                "projected_points": 6.0 + error,
                "actual_points": 6.0,
                "process_points": 6.0,
                "blended_points": 6.0,
                "projected_minutes": 70.0,
                "actual_minutes": 60.0,
            },
        ]
    )
    from backtesting.metrics import evaluate_predictions

    metrics = evaluate_predictions(df_eval)
    return WalkforwardResult(
        model_name=model_name,
        data_dir=Path("data"),
        start_gw=1,
        end_gw=38,
        metrics=metrics,
        df_eval=df_eval,
        snapshot_ids={},
        snapshot_backed=False,
    )


def test_evaluate_and_apply_promotes_clear_candidate(tmp_path: Path) -> None:
    config_path = tmp_path / "model_selection.json"
    save_model_selection(
        ModelSelection(
            champion="metrics_component_hybrid",
            candidates=("participation_state_hybrid",),
        ),
        config_path,
    )
    data_dir = tmp_path / "processed"
    data_dir.mkdir()

    def fake_run_model(*, model_name: str, **kwargs):
        return _result(model_name, worse=model_name == "metrics_component_hybrid")

    with patch("commands.evaluate_model_promotion._run_model", side_effect=fake_run_model):
        updated, comparisons, evidence_paths = evaluate_and_apply(
            config_path=config_path,
            data_dir=data_dir,
            start_gw=1,
            end_gw=38,
            seed_season=None,
            snapshot_root=None,
            snapshot_season="2025-26",
            require_snapshots=False,
            apply=True,
        )

    assert updated.champion == "participation_state_hybrid"
    assert comparisons[0].verdict.passed
    assert evidence_paths is not None
    assert load_model_selection(config_path).champion == "participation_state_hybrid"


def test_evaluate_and_apply_forwards_confirmation_bootstrap_bar(tmp_path: Path) -> None:
    config_path = tmp_path / "model_selection.json"
    save_model_selection(ModelSelection(champion="metrics_component_hybrid", candidates=("participation_state_hybrid",)), config_path)
    data_dir = tmp_path / "processed"
    data_dir.mkdir()

    with (
        patch("commands.evaluate_model_promotion._run_model", side_effect=lambda *, model_name, **kwargs: _result(model_name, worse=False)),
        patch("commands.evaluate_model_promotion.compare_to_reference") as gate,
    ):
        evaluate_and_apply(
            config_path=config_path,
            data_dir=data_dir,
            start_gw=1,
            end_gw=38,
            seed_season=None,
            snapshot_root=None,
            snapshot_season="2024-25",
            require_snapshots=False,
            apply=False,
            bootstrap_min_p=CONFIRMATION_BOOTSTRAP_MIN_P,
        )

    assert gate.call_args.kwargs["bootstrap_min_p"] == CONFIRMATION_BOOTSTRAP_MIN_P


def test_evaluate_and_apply_leaves_config_when_gate_fails(tmp_path: Path) -> None:
    config_path = tmp_path / "model_selection.json"
    save_model_selection(
        ModelSelection(
            champion="participation_state_hybrid",
            candidates=("metrics_component_hybrid",),
        ),
        config_path,
    )
    data_dir = tmp_path / "processed"
    data_dir.mkdir()

    with patch(
        "commands.evaluate_model_promotion._run_model",
        side_effect=lambda *, model_name, **kwargs: _result(model_name, worse=True),
    ):
        updated, comparisons, evidence_paths = evaluate_and_apply(
            config_path=config_path,
            data_dir=data_dir,
            start_gw=1,
            end_gw=38,
            seed_season=None,
            snapshot_root=None,
            snapshot_season="2025-26",
            require_snapshots=False,
            apply=True,
        )

    assert updated.champion == "participation_state_hybrid"
    assert not comparisons[0].verdict.passed
    assert evidence_paths is not None
    assert load_model_selection(config_path).champion == "participation_state_hybrid"


def test_main_confirmation_defaults_seed_season_to_2023_24(tmp_path: Path) -> None:
    from commands.evaluate_model_promotion import main

    config_path = tmp_path / "model_selection.json"
    save_model_selection(
        ModelSelection(
            champion="participation_state_hybrid",
            candidates=("metrics_component_hybrid",),
        ),
        config_path,
    )
    data_dir = tmp_path / "archive" / "2024-25" / "processed"
    data_dir.mkdir(parents=True)

    with patch("commands.evaluate_model_promotion.evaluate_and_apply") as mock_eval:
        mock_eval.return_value = (ModelSelection(champion="champ", candidates=()), [], None)
        main([
            "--config", str(config_path),
            "--data_dir", str(data_dir),
            "--confirmation",
        ])
        assert mock_eval.call_args.kwargs["seed_season"] == "2023-24"

    with patch("commands.evaluate_model_promotion.evaluate_and_apply") as mock_eval:
        mock_eval.return_value = (ModelSelection(champion="champ", candidates=()), [], None)
        main([
            "--config", str(config_path),
            "--data_dir", str(data_dir),
            "--confirmation",
            "--seed_season", "2022-23",
        ])
        assert mock_eval.call_args.kwargs["seed_season"] == "2022-23"

    data_dir_2526 = tmp_path / "archive" / "2025-26" / "processed"
    data_dir_2526.mkdir(parents=True)
    with patch("commands.evaluate_model_promotion.evaluate_and_apply") as mock_eval:
        mock_eval.return_value = (ModelSelection(champion="champ", candidates=()), [], None)
        main([
            "--config", str(config_path),
            "--data_dir", str(data_dir_2526),
            "--confirmation",
        ])
        assert mock_eval.call_args.kwargs["seed_season"] is None



