"""Legacy diagnostic routes cannot grant scientific or adoption authority."""

import json
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from backtesting.metrics import evaluate_predictions
from backtesting.promotion import CONFIRMATION_BOOTSTRAP_MIN_P
from backtesting.walkforward import WalkforwardResult
from commands.evaluate_model_promotion import adopt_champion, evaluate_and_apply, main
from models.selection import ModelSelection, load_model_selection, save_model_selection


def _result(model_name: str, *, worse: bool) -> WalkforwardResult:
    error = 2.0 if worse else 0.5
    frame = pd.DataFrame([{"player_id": pid, "gameweek": gw, "projected_points": 4.0 + error, "actual_points": 4.0, "process_points": 4.0, "blended_points": 4.0, "projected_minutes": 70.0, "actual_minutes": 60.0} for pid, gw in enumerate((2, 10, 25), 1)])
    return WalkforwardResult(model_name, Path("data"), 1, 38, evaluate_predictions(frame), frame, {}, False)


@pytest.mark.parametrize("candidate_worse", [False, True])
def test_legacy_proxy_result_never_recommends_or_mutates_selection(tmp_path: Path, candidate_worse: bool) -> None:
    config_path = tmp_path / "selection.json"
    selection = ModelSelection("metrics_component_hybrid", ("participation_state_hybrid",))
    save_model_selection(selection, config_path)
    with (
        patch("commands.evaluate_model_promotion._run_model", side_effect=lambda *, model_name, **kwargs: _result(model_name, worse=candidate_worse if model_name != selection.champion else True)),
        patch("commands.evaluate_model_promotion.EVIDENCE_DIR", tmp_path / "diagnostics"),
    ):
        updated, comparisons, evidence_paths = evaluate_and_apply(config_path=config_path, data_dir=tmp_path, start_gw=1, end_gw=38, seed_season=None, snapshot_root=None, snapshot_season="2025-26", require_snapshots=False, apply=True)
    assert updated == selection == load_model_selection(config_path)
    assert len(comparisons) == 1
    assert evidence_paths is not None
    payload = json.loads(evidence_paths[0].read_bytes())
    assert payload["scientific_verdict"] == "inconclusive"
    assert payload["execution_status"] == "not_run"
    assert payload["evidence_kind"] == "legacy_proxy_diagnostic"
    assert payload["comparisons"][0]["scientific_verdict"] == "inconclusive"
    with pytest.raises(ValueError, match="Unsupported verified recommendation"):
        adopt_champion(evidence_paths[0], config_path=config_path, approval_ref="human", expected_current_champion=selection.champion, approved_bundle_hash="0" * 64)


@pytest.mark.parametrize("status", [None, "partial", "complete"])
def test_plain_json_with_pass_fields_is_never_verified_evidence(tmp_path: Path, status: str | None) -> None:
    config_path = tmp_path / "selection.json"
    save_model_selection(ModelSelection("champ", ("cand",)), config_path)
    bundle = tmp_path / "bundle.json"
    bundle.write_text(json.dumps({"scientific_verdict": "pass", "execution_status": status, "candidate_name": "cand", "former_champion": "champ", "snapshot_backed": True}))
    with pytest.raises(ValueError, match="Unsupported verified recommendation"):
        adopt_champion(bundle, config_path=config_path, approval_ref="human", expected_current_champion="champ", approved_bundle_hash="a" * 64)
    assert load_model_selection(config_path).champion == "champ"


@pytest.mark.parametrize("options, expected", [
    ({}, "missing required human approval reference"),
    ({"approval_ref": "human"}, "explicit expected current Champion"),
    ({"approval_ref": "human", "expected_current_champion": "champ"}, "exact approved bundle hash"),
])
def test_adoption_requires_explicit_approval_and_exact_identity(tmp_path: Path, options: dict[str, str], expected: str) -> None:
    with pytest.raises(ValueError, match=expected):
        adopt_champion(tmp_path / "absent.json", approval_ref=options.get("approval_ref"), expected_current_champion=options.get("expected_current_champion"))


def test_confirmation_diagnostic_forwards_seed_and_legacy_bar(tmp_path: Path) -> None:
    selection = ModelSelection("champ", ())
    with patch("commands.evaluate_model_promotion.evaluate_and_apply", return_value=(selection, [], None)) as diagnostic:
        main(["--config", str(tmp_path / "selection.json"), "--confirmation"])
    assert diagnostic.call_args.kwargs["seed_season"] == "2023-24"
    assert diagnostic.call_args.kwargs["bootstrap_min_p"] == CONFIRMATION_BOOTSTRAP_MIN_P


def test_two_season_convenience_route_remains_diagnostic(tmp_path: Path) -> None:
    with patch("commands.evaluate_model_promotion.evaluate_and_apply_two_season", return_value=(ModelSelection("champ", ()), [], None)) as diagnostic:
        main(["--config", str(tmp_path / "selection.json"), "--confirmation_data_dir", str(tmp_path / "confirmation")])
    assert diagnostic.call_args.kwargs["dev_seed_season"] == "2024-25"
    assert diagnostic.call_args.kwargs["conf_seed_season"] == "2023-24"


def test_cli_verified_evidence_route_skips_legacy_backtests(tmp_path: Path) -> None:
    with (
        patch("commands.evaluate_model_promotion.write_recommendation_bundle", return_value={"scientific_verdict": "inconclusive", "bundle_hash": "a" * 64}) as evaluate,
        patch("commands.evaluate_model_promotion._run_model") as legacy,
    ):
        main(["--evidence_request", str(tmp_path / "request.json")])
    evaluate.assert_called_once_with(tmp_path / "request.json", tmp_path / "recommendation_bundle.json")
    legacy.assert_not_called()
