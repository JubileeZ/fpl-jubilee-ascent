import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from backtesting.evaluation_protocol import (
    validate_bundle,
    validate_result,
    write_execution_manifest,
)


def bundle(tmp_path: Path) -> dict[str, Any]:
    slots: dict[str, dict[str, Any]] = {
        "source_admission": {
            "source_manifest_refs": ["source"],
            "admission_manifest_refs": ["admission"],
        },
        "forecasts": {"forecast_ids": ["forecast"]},
        "initial_state": {"state_ref": "initial"},
        "deadline_states_actions": {
            "deadline_records": [
                {
                    "deadline": 1,
                    "pre_state_ref": "before",
                    "post_state_ref": "after",
                    "actions_ref": "actions",
                }
            ]
        },
        "solver_certificate": {"certificate_refs": ["certificate"]},
        "scores": {"gross": 10, "hits": 0, "net": 10},
        "guard_metrics": {"metrics_ref": "guards"},
        "uncertainty": {"analysis_ref": "analysis"},
        "registry_references": {"registry_refs": ["registry"]},
        "human_decisions": {"decision_refs": ["decision"]},
    }
    files = {}
    for kind, slot in slots.items():
        content = json.dumps({"version": 1, **slot}).encode()
        path = tmp_path / f"{kind}.json"
        path.write_bytes(content)
        files[kind] = {"path": path.name, "sha256": hashlib.sha256(content).hexdigest()}
    return {"version": 1, "evidence_complete": True, "files": files}


def result() -> dict[str, Any]:
    return {
        "version": 1,
        "execution_status": "complete",
        "scientific_verdict": "pass",
        "reasons": [],
        "evidence_complete": True,
        "limitations": [],
        "started_at": "2026-01-01T00:00:00Z",
        "finished_at": "2026-01-01T01:00:00Z",
        "identity": {
            k: "a" * 64
            for k in (
                "model_source",
                "dirty_source",
                "parameters_training_seed",
                "input_manifests",
                "feature_scoring_code",
                "forecast_schema",
                "anchor",
                "rules_calendar",
                "solver",
                "evaluation_statistics",
                "protocol",
            )
        },
    }


def test_bundle_roundtrip_and_corruption(tmp_path: Path) -> None:
    manifest = bundle(tmp_path)
    validate_bundle(json.loads(json.dumps(manifest)), tmp_path)
    (tmp_path / "scores.json").write_text("changed", encoding="utf-8")
    with pytest.raises(ValueError):
        validate_bundle(manifest, tmp_path)
    del manifest["files"]["scores"]
    with pytest.raises(ValueError):
        validate_bundle(manifest, tmp_path)


def test_result_states_and_identity() -> None:
    value = result()
    validate_result(json.loads(json.dumps(value)))
    for status, verdict, complete in [
        ("partial", "inconclusive", False),
        ("complete", "invalid", False),
        ("complete", "inconclusive", True),
    ]:
        item = copy.deepcopy(value)
        item.update(
            execution_status=status,
            scientific_verdict=verdict,
            evidence_complete=complete,
            reasons=["synthetic"],
        )
        validate_result(item)
    for mutate in (
        {"version": 2},
        {"execution_status": "partial"},
        {"evidence_complete": False},
        {"identity": {}},
        {"scientific_verdict": "invalid"},
    ):
        item = copy.deepcopy(value)
        item.update(mutate)
        with pytest.raises(ValueError):
            validate_result(item)


def test_manifest_is_append_only(tmp_path: Path) -> None:
    manifest = {
        "version": 1,
        "kind": "implementation_verification",
        "attempt_id": "run-1",
        "status": "partial",
        "created_at": "2026-01-01T00:00:00Z",
        "result_digest": "a" * 64,
    }
    path = write_execution_manifest(tmp_path, manifest)
    assert json.loads(path.read_text(encoding="utf-8")) == manifest
    with pytest.raises(FileExistsError):
        write_execution_manifest(tmp_path, manifest)


def test_protocol_declaration_and_unknown_version() -> None:
    from backtesting.evaluation_protocol import validate_protocol

    protocol = {
        "version": 1,
        "windows": [
            {
                "season": "synthetic",
                "role": "development",
                "weight": None,
                "scored_deadlines": [1, 2],
            }
        ],
        "issue_cutoff": "deadline",
        "horizon": 6,
        "season_end_clipping": True,
        "native_rules": "rules-v1",
        "anchor": "one ownership anchor",
        "strategic_settings": "declared profile",
        "chip_calendar": "shared calendar",
        "quality_policy": "unapproved",
        "forecast_guards": "unapproved",
        "statistical_procedure": "unapproved",
        "approval_references": [],
    }
    validate_protocol(protocol)
    protocol["version"] = 2
    with pytest.raises(ValueError):
        validate_protocol(protocol)


def test_material_digest_binds_names_bytes_and_order() -> None:
    from backtesting.evaluation_protocol import material_digest

    assert material_digest({"a": b"1", "b": b"2"}) == material_digest(
        {"b": b"2", "a": b"1"}
    )
    assert material_digest({"a": b"1"}) != material_digest({"a": b"2"})
    assert material_digest({"a": b"1"}) != material_digest({"b": b"1"})
    with pytest.raises(ValueError):
        material_digest({})


def test_workflow_has_no_automatic_selection_write() -> None:
    workflow = Path(".github/workflows/evaluate_model_promotion.yml").read_text(
        encoding="utf-8"
    )
    assert "contents: read" in workflow
    assert "--apply" not in workflow
    assert "git push" not in workflow
    assert "git commit" not in workflow


@pytest.mark.parametrize("field", ["execution_status", "scientific_verdict"])
@pytest.mark.parametrize("bad", [[], {}])
def test_rejects_unhashable_result_enums(field: str, bad: Any) -> None:
    value = result()
    value[field] = bad
    with pytest.raises(ValueError):
        validate_result(value)


def test_rejects_mixed_material_keys() -> None:
    from backtesting.evaluation_protocol import material_digest

    with pytest.raises(ValueError):
        material_digest({"valid": b"a", 1: b"b"})  # type: ignore[dict-item]


def test_rejects_unhashable_manifest_enum(tmp_path: Path) -> None:
    manifest = {
        "version": 1,
        "kind": [],
        "attempt_id": "x",
        "status": "partial",
        "created_at": "2026-01-01T00:00:00Z",
        "result_digest": "a" * 64,
    }
    with pytest.raises(ValueError):
        write_execution_manifest(tmp_path, manifest)
    assert not (tmp_path / "x.json").exists()


def test_bundle_rejects_aliased_files_and_allows_pending_only_incomplete(
    tmp_path: Path,
) -> None:
    manifest = bundle(tmp_path)
    manifest["files"]["forecasts"] = manifest["files"]["source_admission"]
    with pytest.raises(ValueError):
        validate_bundle(manifest, tmp_path)
    manifest = bundle(tmp_path)
    content = json.dumps({"version": 1, "forecast_ids": None}).encode()
    (tmp_path / "forecasts.json").write_bytes(content)
    manifest["files"]["forecasts"]["sha256"] = hashlib.sha256(content).hexdigest()
    with pytest.raises(ValueError):
        validate_bundle(manifest, tmp_path)
    manifest["evidence_complete"] = False
    validate_bundle(manifest, tmp_path)


def test_bundle_accepts_large_integer_score(tmp_path: Path) -> None:
    manifest = bundle(tmp_path)
    content = json.dumps(
        {"version": 1, "gross": 10**1000, "hits": 0, "net": 10**1000}
    ).encode()
    (tmp_path / "scores.json").write_bytes(content)
    manifest["files"]["scores"]["sha256"] = hashlib.sha256(content).hexdigest()
    validate_bundle(manifest, tmp_path)
