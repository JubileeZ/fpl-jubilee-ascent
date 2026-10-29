import json
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from backtesting.promotion import CONFIRMATION_BOOTSTRAP_MIN_P
from backtesting.walkforward import WalkforwardResult
from commands.evaluate_model_promotion import adopt_champion, evaluate_and_apply
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


def test_evaluate_and_apply_recommends_without_mutating_selection(tmp_path: Path) -> None:
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

    # Evaluation is read-only: Champion on disk is untouched
    assert load_model_selection(config_path).champion == "metrics_component_hybrid"
    assert "recommend_promotion" in updated.promotion_status
    assert comparisons[0].verdict.passed
    assert evidence_paths is not None


def test_adopt_champion_with_valid_bundle(tmp_path: Path) -> None:
    config_path = tmp_path / "model_selection.json"
    save_model_selection(
        ModelSelection(
            champion="former_champ",
            candidates=("new_candidate",),
        ),
        config_path,
    )

    bundle_path = tmp_path / "valid_bundle.json"
    bundle_data = {
        "scientific_verdict": "pass",
        "execution_status": "complete",
        "candidate_name": "new_candidate",
        "snapshot_backed": True,
    }
    bundle_path.write_text(json.dumps(bundle_data), encoding="utf-8")

    updated = adopt_champion(
        bundle_path=bundle_path,
        config_path=config_path,
        approval_ref="HUMAN-APPROVAL-20261029",
        expected_current_champion="former_champ",
    )

    assert updated.champion == "new_candidate"
    assert load_model_selection(config_path).champion == "new_candidate"


def test_adopt_champion_fails_on_inconclusive_or_failing_verdict(tmp_path: Path) -> None:
    config_path = tmp_path / "model_selection.json"
    save_model_selection(ModelSelection(champion="champ", candidates=("cand",)), config_path)

    bundle_path = tmp_path / "inconclusive_bundle.json"
    bundle_data = {
        "scientific_verdict": "inconclusive",
        "execution_status": "complete",
        "candidate_name": "cand",
    }
    bundle_path.write_text(json.dumps(bundle_data), encoding="utf-8")

    with pytest.raises(ValueError, match="scientific verdict is 'inconclusive', not 'pass'"):
        adopt_champion(
            bundle_path=bundle_path,
            config_path=config_path,
            approval_ref="APR-01",
        )


def test_adopt_champion_fails_on_missing_approval_or_mismatch(tmp_path: Path) -> None:
    config_path = tmp_path / "model_selection.json"
    save_model_selection(ModelSelection(champion="champ", candidates=("cand",)), config_path)

    bundle_path = tmp_path / "pass_bundle.json"
    bundle_data = {
        "scientific_verdict": "pass",
        "execution_status": "complete",
        "candidate_name": "cand",
    }
    bundle_path.write_text(json.dumps(bundle_data), encoding="utf-8")

    # Missing approval ref
    with pytest.raises(ValueError, match="missing required human approval reference"):
        adopt_champion(bundle_path=bundle_path, config_path=config_path, approval_ref="")

    # Expected champion mismatch
    with pytest.raises(ValueError, match="Current Champion mismatch"):
        adopt_champion(
            bundle_path=bundle_path,
            config_path=config_path,
            approval_ref="APR-01",
            expected_current_champion="different_champ",
        )


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

    # When data_dir is default / unspecified, confirmation defaults to 2023-24
    with patch("commands.evaluate_model_promotion.evaluate_and_apply") as mock_eval:
        mock_eval.return_value = (ModelSelection(champion="champ", candidates=()), [], None)
        main([
            "--config", str(config_path),
            "--confirmation",
        ])
        assert mock_eval.call_args.kwargs["seed_season"] == "2023-24"


def test_main_two_season_dispatches_to_two_season_evaluator(tmp_path: Path) -> None:
    from commands.evaluate_model_promotion import main

    config_path = tmp_path / "model_selection.json"
    save_model_selection(
        ModelSelection(
            champion="participation_state_hybrid",
            candidates=("metrics_component_hybrid",),
        ),
        config_path,
    )
    with patch("commands.evaluate_model_promotion.evaluate_and_apply_two_season") as mock_two:
        mock_two.return_value = (ModelSelection(champion="champ", candidates=()), [], None)
        main([
            "--config", str(config_path),
            "--two_season",
        ])
        assert mock_two.called
        assert mock_two.call_args.kwargs["conf_seed_season"] == "2023-24"
        assert mock_two.call_args.kwargs["dev_seed_season"] == "2024-25"




