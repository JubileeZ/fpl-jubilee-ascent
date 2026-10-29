"""Versioned, fail-closed contracts for future evaluation evidence."""

import hashlib
import json
import math
import re
from datetime import datetime
from pathlib import Path
from typing import Any

IDENTITY_FIELDS = frozenset(
    {
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
    }
)
BUNDLE_FIELDS = frozenset(
    {
        "source_admission",
        "forecasts",
        "initial_state",
        "deadline_states_actions",
        "solver_certificate",
        "scores",
        "guard_metrics",
        "uncertainty",
        "registry_references",
        "human_decisions",
    }
)

SLOT_FIELDS: dict[str, frozenset[str]] = {
    "source_admission": frozenset({"source_manifest_refs", "admission_manifest_refs"}),
    "forecasts": frozenset({"forecast_ids"}),
    "initial_state": frozenset({"state_ref"}),
    "deadline_states_actions": frozenset({"deadline_records"}),
    "solver_certificate": frozenset({"certificate_refs"}),
    "scores": frozenset({"gross", "hits", "net"}),
    "guard_metrics": frozenset({"metrics_ref"}),
    "uncertainty": frozenset({"analysis_ref"}),
    "registry_references": frozenset({"registry_refs"}),
    "human_decisions": frozenset({"decision_refs"}),
}

EXECUTION_STATUSES = frozenset({"not_run", "partial", "censored", "complete"})
VERDICTS = frozenset({"pass", "fail", "inconclusive", "invalid"})


def _object(value: Any, fields: frozenset[str]) -> None:
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError(f"Expected fields: {sorted(fields)}")


def _version(value: Any) -> None:
    if type(value) is not int or value != 1:
        raise ValueError("Unsupported version")


def _digest(value: Any) -> None:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError("Expected lowercase SHA256 digest")


def _timestamp(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("Expected timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Invalid timestamp") from exc
    if parsed.utcoffset() is None:
        raise ValueError("Timestamp must include timezone")
    return parsed


def _strings(value: Any) -> None:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise ValueError("Expected list of nonempty strings")


def validate_result(result: dict[str, Any]) -> None:
    _object(
        result,
        frozenset(
            {
                "version",
                "execution_status",
                "scientific_verdict",
                "reasons",
                "evidence_complete",
                "limitations",
                "started_at",
                "finished_at",
                "identity",
            }
        ),
    )
    _version(result["version"])
    if (
        not isinstance(result["execution_status"], str)
        or result["execution_status"] not in EXECUTION_STATUSES
        or not isinstance(result["scientific_verdict"], str)
        or result["scientific_verdict"] not in VERDICTS
    ):
        raise ValueError("Invalid execution status or scientific verdict")
    if type(result["evidence_complete"]) is not bool:
        raise ValueError("Evidence completeness must be boolean")
    _strings(result["reasons"])
    _strings(result["limitations"])
    if result["scientific_verdict"] != "pass" and not result["reasons"]:
        raise ValueError("Non-pass verdict requires reasons")
    if result["scientific_verdict"] in {"pass", "fail"} and (
        result["execution_status"] != "complete" or not result["evidence_complete"]
    ):
        raise ValueError(
            "Pass and demonstrated fail require complete execution and evidence"
        )
    if result["scientific_verdict"] == "invalid" and result["evidence_complete"]:
        raise ValueError("Invalid evidence cannot be complete")
    if _timestamp(result["finished_at"]) < _timestamp(result["started_at"]):
        raise ValueError("Finish precedes start")
    _object(result["identity"], IDENTITY_FIELDS)
    for digest in result["identity"].values():
        _digest(digest)


def validate_bundle(bundle: dict[str, Any], root: Path) -> None:
    _object(bundle, frozenset({"version", "evidence_complete", "files"}))
    if type(bundle["evidence_complete"]) is not bool:
        raise ValueError("Evidence completeness must be boolean")
    _version(bundle["version"])
    _object(bundle["files"], BUNDLE_FIELDS)
    base = root.resolve()
    seen: set[Path] = set()
    for kind, entry in bundle["files"].items():
        _object(entry, frozenset({"path", "sha256"}))
        _digest(entry["sha256"])
        if not isinstance(entry["path"], str) or not entry["path"]:
            raise ValueError("Missing evidence path")
        path = Path(entry["path"])
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("Evidence path must be relative to bundle")
        resolved = (base / path).resolve()
        if not resolved.is_relative_to(base) or not resolved.is_file():
            raise ValueError("Missing or outside evidence file")
        if resolved in seen:
            raise ValueError("Evidence slots must use distinct files")
        seen.add(resolved)
        content = resolved.read_bytes()
        if hashlib.sha256(content).hexdigest() != entry["sha256"]:
            raise ValueError("Evidence checksum mismatch")
        try:
            slot = json.loads(content)
        except (ValueError, UnicodeDecodeError) as exc:
            raise ValueError("Invalid evidence JSON") from exc
        _object(slot, SLOT_FIELDS[kind] | {"version"})
        _version(slot["version"])
        for field in SLOT_FIELDS[kind]:
            value = slot[field]
            if value is None and not bundle["evidence_complete"]:
                continue
            if kind == "scores":
                if type(value) not in (int, float) or (
                    type(value) is float and not math.isfinite(value)
                ):
                    raise ValueError("Score must be finite")
            elif field == "deadline_records":
                if not isinstance(value, list) or not value:
                    raise ValueError("Missing deadline records")
                for record in value:
                    _object(
                        record,
                        frozenset(
                            {
                                "deadline",
                                "pre_state_ref",
                                "post_state_ref",
                                "actions_ref",
                            }
                        ),
                    )
                    if (
                        type(record["deadline"]) is not int
                        or not 1 <= record["deadline"] <= 38
                    ):
                        raise ValueError("Invalid deadline")
                    for key in ("pre_state_ref", "post_state_ref", "actions_ref"):
                        if not isinstance(record[key], str) or not record[key].strip():
                            raise ValueError("Missing deadline reference")
            elif field.endswith("_refs") or field == "forecast_ids":
                _strings(value)
                if not value:
                    raise ValueError("Evidence list cannot be empty")
            elif not isinstance(value, str) or not value.strip():
                raise ValueError("Missing evidence reference")


def write_execution_manifest(directory: Path, manifest: dict[str, Any]) -> Path:
    _object(
        manifest,
        frozenset(
            {"version", "kind", "attempt_id", "status", "created_at", "result_digest"}
        ),
    )
    _version(manifest["version"])
    if (
        not isinstance(manifest["kind"], str)
        or manifest["kind"] not in {"calibration", "implementation_verification"}
        or not isinstance(manifest["status"], str)
        or manifest["status"] not in EXECUTION_STATUSES
    ):
        raise ValueError("Invalid manifest kind or status")
    attempt = manifest["attempt_id"]
    if not isinstance(attempt, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", attempt):
        raise ValueError("Invalid attempt ID")
    _timestamp(manifest["created_at"])
    _digest(manifest["result_digest"])
    payload = (
        json.dumps(
            manifest, sort_keys=True, indent=2, allow_nan=False, ensure_ascii=True
        )
        + "\n"
    )
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{attempt}.json"
    with path.open("x", encoding="utf-8", newline="\n") as output:
        output.write(payload)
    return path


def validate_protocol(protocol: dict[str, Any]) -> None:
    """Validate the declaration; approval and admissibility remain separate decisions."""
    fields = frozenset(
        {
            "version",
            "windows",
            "issue_cutoff",
            "horizon",
            "season_end_clipping",
            "native_rules",
            "anchor",
            "strategic_settings",
            "chip_calendar",
            "quality_policy",
            "forecast_guards",
            "statistical_procedure",
            "approval_references",
        }
    )
    _object(protocol, fields)
    _version(protocol["version"])
    if protocol["horizon"] != 6 or protocol["season_end_clipping"] is not True:
        raise ValueError("Expected six-GW horizon with season-end clipping")
    if not isinstance(protocol["windows"], list) or not protocol["windows"]:
        raise ValueError("Expected declared windows")
    for window in protocol["windows"]:
        _object(window, frozenset({"season", "role", "weight", "scored_deadlines"}))
        if (
            not isinstance(window["season"], str)
            or not window["season"].strip()
            or not isinstance(window["role"], str)
            or window["role"] not in {"development", "confirmation", "live"}
        ):
            raise ValueError("Invalid season or role")
        weight = window["weight"]
        if weight is not None and (
            type(weight) not in (int, float) or not 0 < weight <= 1
        ):
            raise ValueError("Weight must be positive or unapproved")
        deadlines = window["scored_deadlines"]
        if (
            not isinstance(deadlines, list)
            or not deadlines
            or any(type(gw) is not int or not 1 <= gw <= 38 for gw in deadlines)
            or sorted(set(deadlines)) != deadlines
        ):
            raise ValueError("Invalid scored deadlines")
    for name in fields - {
        "version",
        "windows",
        "horizon",
        "season_end_clipping",
        "approval_references",
    }:
        if not isinstance(protocol[name], str) or not protocol[name].strip():
            raise ValueError(f"Missing {name} declaration")
    _strings(protocol["approval_references"])


def material_digest(material: dict[str, bytes]) -> str:
    """Hash named material using sorted names and length-prefixed raw bytes."""
    if (
        not isinstance(material, dict)
        or not material
        or any(
            not isinstance(k, str) or not k or not isinstance(v, bytes)
            for k, v in material.items()
        )
    ):
        raise ValueError("Material requires nonempty names and bytes")
    digest = hashlib.sha256(b"evaluation-material-v1\0")
    for name in sorted(material):
        encoded = name.encode("utf-8")
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)
        digest.update(len(material[name]).to_bytes(8, "big"))
        digest.update(material[name])
    return digest.hexdigest()
