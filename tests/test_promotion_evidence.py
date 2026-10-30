"""Recommendation and adoption operate on reconstructed native replay evidence."""

from pathlib import Path
import json
import shutil
from dataclasses import replace

import pytest

from backtesting import promotion_evidence
from backtesting.promotion_evidence import evaluate_replay_evidence, verify_recommendation_bundle, write_recommendation_bundle
from commands.evaluate_model_promotion import adopt_champion
from models.selection import ModelSelection, load_model_selection, save_model_selection
from promotion_evidence_fixture import CANDIDATE, CHAMPION, build_evidence_fixture, save_material


@pytest.fixture(scope="module")
def retained_template(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return build_evidence_fixture(tmp_path_factory.mktemp("retained-promotion"))


@pytest.fixture
def retained_request(retained_template: Path, tmp_path: Path) -> Path:
    destination = tmp_path / "evidence"
    shutil.copytree(retained_template.parent, destination)
    return destination / "request.json"


def _selection(root: Path) -> Path:
    path = root / "selection.json"
    save_model_selection(ModelSelection(CHAMPION, (CANDIDATE,)), path)
    return path


def test_native_replay_outputs_reconstruct_and_synthetic_evidence_cannot_adopt(retained_request: Path) -> None:
    result = evaluate_replay_evidence(retained_request)
    assert result["scientific_verdict"] == "inconclusive"
    assert result["empirical_admission"] is False
    assert len(result["guards"]) == 15
    assert len(result["assessment"]["season_summaries"]) == 2
    bundle_path = retained_request.with_name("bundle.json")
    written = write_recommendation_bundle(retained_request, bundle_path)
    assert verify_recommendation_bundle(bundle_path, require_finalized=True) == written
    config_path = _selection(retained_request.parent)
    with pytest.raises(ValueError, match="empirical scientific pass"):
        adopt_champion(bundle_path, config_path=config_path, approval_ref="fixture-approval", expected_current_champion=CHAMPION, approved_bundle_hash=written["bundle_hash"])
    assert load_model_selection(config_path).champion == CHAMPION


@pytest.mark.parametrize("mutation", ["trace", "request", "bundle", "forecast", "guard_inventory", "live_readiness"])
def test_changed_retained_material_is_rejected(retained_request: Path, mutation: str) -> None:
    bundle_path = retained_request.with_name("bundle.json")
    write_recommendation_bundle(retained_request, bundle_path)
    request = json.loads(retained_request.read_bytes())
    if mutation == "bundle":
        bundle = json.loads(bundle_path.read_bytes())
        bundle["candidate_name"] = "foreign_candidate"
        bundle_path.write_text(json.dumps(bundle))
    elif mutation == "trace":
        path = retained_request.parent / request["replays"][0]["trace"]["path"]
        trace = json.loads(path.read_bytes())
        trace["records"][0]["net_points"] += 4
        path.write_text(json.dumps(trace))
    elif mutation == "forecast":
        issue = request["replays"][0]["issues"][0]
        path = retained_request.parent / issue["forecast_store"] / "forecasts" / issue["forecast_id"] / "forecast.csv"
        path.write_bytes(path.read_bytes() + b"tampered")
    elif mutation in {"guard_inventory", "live_readiness"}:
        slot = "protocol" if mutation == "guard_inventory" else "live_readiness"
        path = retained_request.parent / request[slot]["path"]
        material = json.loads(path.read_bytes())
        if mutation == "guard_inventory":
            material["guard_specs"].pop("points_mse")
        else:
            material["dry_run_captures"] = {}
        request[slot] = save_material(retained_request.parent, path.name, material)
        retained_request.write_text(json.dumps(request))
    else:
        request["former_champion"] = "stale_champion"
        retained_request.write_text(json.dumps(request))
    with pytest.raises(ValueError):
        verify_recommendation_bundle(bundle_path)


def test_missing_confirmation_comparator_rejected(retained_request: Path) -> None:
    request = json.loads(retained_request.read_bytes())
    request["replays"] = [entry for entry in request["replays"] if entry["season"] != "2024-25"]
    retained_request.write_text(json.dumps(request))
    with pytest.raises(ValueError, match="Missing development or confirmation"):
        evaluate_replay_evidence(retained_request)


def test_current_source_change_invalidates_request(retained_request: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(promotion_evidence, "current_model_source_hash", lambda: "f" * 64)
    with pytest.raises(ValueError, match="Frozen model source changed"):
        evaluate_replay_evidence(retained_request)


def test_rehashed_certificate_with_false_zero_gap_is_rejected(retained_request: Path) -> None:
    from backtesting.rolling_replay import _checkpoint_hash, record_from_dict, record_to_dict, UncertifiedSolveError

    request = json.loads(retained_request.read_bytes())
    entry = next(entry for entry in request["replays"] if entry["season"] == "2024-25" and entry["model_name"] == CANDIDATE)
    path = retained_request.parent / entry["trace"]["path"]
    trace = json.loads(path.read_bytes())
    record = record_from_dict(trace["records"][0])
    record = replace(record, certificate=replace(record.certificate, objective_bound=record.certificate.objective + 1.0, absolute_gap=1.0, relative_gap=0.0))
    record = replace(record, checkpoint_id=_checkpoint_hash(record))
    trace["records"][0] = record_to_dict(record)
    entry["trace"] = save_material(retained_request.parent, path.name, trace)
    retained_request.write_text(json.dumps(request))
    with pytest.raises(UncertifiedSolveError, match="relative gap contradicts"):
        evaluate_replay_evidence(retained_request)


def test_adoption_unit_contract_with_verified_boundary(retained_request: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Isolate the verified-boundary result; actual synthetic integration above must refuse adoption."""
    from commands import evaluate_model_promotion

    bundle_path = retained_request.with_name("bundle.json")
    written = {"candidate_name": CANDIDATE, "former_champion": CHAMPION, "scientific_verdict": "pass", "execution_status": "complete", "empirical_admission": True, "bundle_hash": "a" * 64, "protocol_hash": "b" * 64}
    monkeypatch.setattr(evaluate_model_promotion, "verify_recommendation_bundle", lambda *args, **kwargs: written)
    config_path = _selection(retained_request.parent)
    for kwargs, message in (
        ({"approved_bundle_hash": "0" * 64}, "different evidence bundle"),
        ({"candidate_name": "foreign"}, "Candidate override"),
        ({"expected_current_champion": "stale"}, "Current Champion mismatch"),
    ):
        options = {"config_path": config_path, "approval_ref": "fixture-human-approval", "expected_current_champion": CHAMPION, "approved_bundle_hash": written["bundle_hash"], **kwargs}
        with pytest.raises(ValueError, match=message):
            adopt_champion(bundle_path, **options)
    updated = adopt_champion(bundle_path, config_path=config_path, approval_ref="fixture-human-approval", expected_current_champion=CHAMPION, approved_bundle_hash=written["bundle_hash"])
    assert updated.champion == CANDIDATE
    assert load_model_selection(config_path) == updated
    receipt = json.loads(config_path.with_suffix(".adoption.json").read_bytes())
    assert receipt["bundle_hash"] == written["bundle_hash"]
    assert receipt["selection_before"]["champion"] == CHAMPION


def test_capture_cli_rejects_backdating_and_late_actual_clock(retained_request: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from commands import capture_live_evidence
    from backtesting.live_capture import LateCaptureError

    request_path = retained_request.with_name(f"capture-request-{CANDIDATE}.json")
    with pytest.raises(LateCaptureError):
        capture_live_evidence.capture_verified_issue(request_path, retained_request.parent / "late-capture")
    payload = json.loads(request_path.read_bytes())
    payload["capture_time_utc"] = "2025-01-01T11:00:00+00:00"
    request_path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="never a supplied timestamp"):
        capture_live_evidence.capture_verified_issue(request_path, retained_request.parent / "backdated-capture")


def test_solver_identity_includes_installed_binary_and_runtime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from importlib.machinery import ModuleSpec
    from importlib import util
    from backtesting.native_transfer_solver import native_strategic_solve
    from backtesting.rolling_replay import replay_solver_identity

    binary = tmp_path / "core.pyd"
    binary.write_bytes(b"fixture-installed-binary-v1")
    monkeypatch.setattr(util, "find_spec", lambda name: ModuleSpec(name, loader=None, origin=str(binary)))
    before = replay_solver_identity(native_strategic_solve)
    binary.write_bytes(b"fixture-installed-binary-v2")
    assert replay_solver_identity(native_strategic_solve) != before
