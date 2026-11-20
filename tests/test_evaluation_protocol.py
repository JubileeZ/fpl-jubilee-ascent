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


def _valid_v2_protocol() -> dict[str, Any]:
    return {
        "version": 2,
        "windows": [
            {
                "season": "2026-27",
                "role": "live",
                "weight": 1.0,
                "scored_deadlines": list(range(1, 39)),
            }
        ],
        "issue_cutoff": "deadline",
        "horizon": 6,
        "season_end_clipping": True,
        "native_rules": "native-2026-27-v1",
        "anchor": "neutral-gw1-opening-anchor",
        "strategic_settings": "adr0065-strategic",
        "chip_calendar": "shared-causal-calendar",
        "quality_policy": "certified-zero-gap",
        "forecast_guards": "s1-derived-15-guards",
        "statistical_procedure": "kendall-pw-hac-v2",
        "approval_references": ["ADR-0070-CERT"],
        "look_schedule": [15, 30, 38],
        "calibrated_superiority_alphas": {
            "1": {"15": 0.0004, "30": 0.008, "38": 0.032},
            "2": {"15": 0.0002, "30": 0.004, "38": 0.016},
        },
        "gw1_4_material_loss_limit": 36.0,
        "completed_segments": {
            "15": [[1, 4]],
            "30": [[1, 4], [5, 19]],
            "38": [[1, 4], [5, 19], [20, 38]],
        },
        "statistical_early_harm_mode": "advisory",
        "unused_alpha_policy": "discard",
        "expiry_rules": {
            "timezone": "UTC",
            "gw38_expiry_hours_after_last_kickoff": 360.0,
        },
        "certification_digest": "b" * 64,
        "statistical_protocol_hash": "c" * 64,
    }


def test_protocol_v2_adr0070_validation_and_rejections() -> None:
    from backtesting.evaluation_protocol import validate_protocol

    valid = _valid_v2_protocol()
    validate_protocol(valid)

    # Integer keys in completed_segments also accepted cleanly when non-colliding
    int_keys = copy.deepcopy(valid)
    int_keys["completed_segments"] = {15: [(1, 4)], 30: [(1, 4), (5, 19)], 38: [(1, 4), (5, 19), (20, 38)]}
    validate_protocol(int_keys)

    bad_cases: list[dict[str, Any]] = [
        {"version": 3},
        {"look_schedule": [15, 38, 30]},
        {"calibrated_superiority_alphas": {"1": {"15": 0.0004, "30": 0.008, "38": 0.032}}},
        {"calibrated_superiority_alphas": {"1": {"15": 0.0, "30": 0.008, "38": 0.032}, "2": {"15": 0.0002, "30": 0.004, "38": 0.016}}},
        {"gw1_4_material_loss_limit": -1.0},
        {"gw1_4_material_loss_limit": True},
        {"completed_segments": {"15": [[1, 5]], "30": [[1, 4], [5, 19]], "38": [[1, 4], [5, 19], [20, 38]]}},
        {"statistical_early_harm_mode": "disabled"},
        {"unused_alpha_policy": "reallocate"},
        {"expiry_rules": {"timezone": "America/New_York", "gw38_expiry_hours_after_last_kickoff": 360.0}},
        {"expiry_rules": {"timezone": "UTC", "gw38_expiry_hours_after_last_kickoff": 0.0}},
        {"certification_digest": "not-a-digest"},
        {"statistical_protocol_hash": "z" * 64},
    ]
    for mutation in bad_cases:
        broken = copy.deepcopy(valid)
        broken.update(mutation)
        with pytest.raises(ValueError):
            validate_protocol(broken)

    missing = copy.deepcopy(valid)
    missing.pop("certification_digest")
    with pytest.raises(ValueError):
        validate_protocol(missing)


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
