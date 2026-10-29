"""Content-addressed synthetic forecast publication; no promotion authority."""

import hashlib
import json
import os
import platform
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from backtesting.data_admission import AdmittedInput, assess_origins, verify_input
from backtesting.forecast_adapter import predict_synthetic_issue
from backtesting.forecast_export import strict_solver_table, validate_components
from backtesting.forecast_inputs import validate_storage_path, verify_training_bundle
from backtesting.season_rules import get_rules


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _sha256_hex(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


_bytes = _canonical_json_bytes
_hash = _sha256_hex


def forecast_material(capability: AdmittedInput, request: dict[str, Any], catalog: dict[str, bytes], training_authority: str, model_name: str = "def_xg_shrink_challenger") -> dict[str, Any]:
    """Capture a conservative source closure, including dirty/generated Python bytes."""
    verify_input(capability, request, catalog)
    source = verify_training_bundle(capability, request, catalog, training_authority)
    origin = next(o for o in request["origins"] if o["season"] == capability.season and o["gw"] == capability.gw)
    authority = json.loads(catalog[request["authority_digest"]])
    report = next(r for r in assess_origins(request, catalog) if r["season"] == capability.season and r["gw"] == capability.gw)
    matches = [s for s in origin["sources"] if s["role"] == "input" and s["id"] == report["selected_source"]["input"]]
    if len(matches) != 1:
        raise ValueError("Ambiguous retained input source")
    input_source = matches[0]
    project = Path(__file__).resolve().parent.parent
    code: dict[str, str] = {}
    for directory in ("backtesting", "features", "models", "projections", "solver", "config"):
        root = project / directory
        if not root.is_dir() or not root.resolve().is_relative_to(project):
            raise ValueError("Source closure directory missing")
        for path in sorted(root.rglob("*.py")):
            resolved = path.resolve()
            if not resolved.is_relative_to(root.resolve()) or any(part in {"2026-27", ".git", ".agents"} for part in resolved.parts):
                raise ValueError("Unsealed source path")
            code[path.relative_to(project).as_posix()] = resolved.read_bytes().hex()
    for name in ("pyproject.toml", "uv.lock"):
        path = project / name
        if not path.is_file() or not path.resolve().is_relative_to(project):
            raise ValueError("Dependency lock missing")
        code[name] = path.read_bytes().hex()
    return {"version": 1, "mode": "synthetic_diagnostic", "issue": {k: origin[k] for k in ("season", "gw", "deadline", "target_gws", "universe", "players", "fixtures", "schedule", "native_rules", "seed_identity")}, "input_digest": capability.input_digest, "input_authority": {k: v for k, v in authority.items() if k != "source_manifests"}, "input_source": {k: (v.hex() if isinstance(v, bytes) else v) for k, v in input_source.items() if k != "parent_manifest"}, "training_authority": catalog[training_authority].hex(), "training_source": _canonical_json_bytes(source).hex(), "model": model_name, "model_parameters": {}, "fit_policy": "current-history-once", "seed_policy": "verified-prior-season", "schema": "synthetic-fixture-v1", "code": code, "python": sys.version, "platform": platform.platform()}


def _load_forecast_content(store: Path, forecast_id: str, material: dict[str, Any]) -> pd.DataFrame:
    if len(forecast_id) != 64 or any(c not in "0123456789abcdef" for c in forecast_id) or _sha256_hex(_canonical_json_bytes(material)) != forecast_id:
        raise ValueError("Forecast identity mismatch")
    directory = store / "forecasts" / forecast_id
    manifest = json.loads((directory / "manifest.json").read_bytes())
    if manifest.get("version") != 1 or manifest.get("forecast_id") != forecast_id or manifest.get("material_sha256") != forecast_id:
        raise ValueError("Invalid forecast manifest")
    material_bytes = (directory / "material.json").read_bytes()
    table = (directory / "forecast.csv").read_bytes()
    if material_bytes != _canonical_json_bytes(material) or _sha256_hex(table) != manifest.get("forecast_sha256"):
        raise ValueError("Forecast cache corruption")
    if "coverage_report_sha256" in manifest:
        report_file = directory / "coverage_report.json"
        if not report_file.exists() or _sha256_hex(report_file.read_bytes()) != manifest["coverage_report_sha256"]:
            raise ValueError("Coverage report missing or corrupt")
    if "generator_log_sha256" in manifest:
        log_file = directory / "generator_log.json"
        if not log_file.exists() or _sha256_hex(log_file.read_bytes()) != manifest["generator_log_sha256"]:
            raise ValueError("Generator log missing or corrupt")
    from io import BytesIO

    frame = pd.read_csv(BytesIO(table))
    if len(frame) != manifest.get("rows"):
        raise ValueError("Incomplete forecast cache")
    return frame


def load_forecast_verified(store: Path, forecast_id: str, capability: AdmittedInput, request: dict[str, Any], catalog: dict[str, bytes], training_authority: str, model_name: str | None = None) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Revalidate original admission, component coverage and retained source material on every load."""
    forecast_dir = store / "forecasts" / forecast_id
    if model_name is None and (forecast_dir / "material.json").exists():
        try:
            model_name = json.loads((forecast_dir / "material.json").read_bytes()).get("model", "def_xg_shrink_challenger")
        except Exception:
            model_name = "def_xg_shrink_challenger"
    if model_name is None:
        model_name = "def_xg_shrink_challenger"
    material = forecast_material(capability, request, catalog, training_authority, model_name)
    frame = _load_forecast_content(store, forecast_id, material)
    strict_solver_table(frame, capability, request, catalog)
    rules = get_rules(capability.season)
    validate_components(frame, rules.version)
    return frame, material


def generate_forecast(store: Path, capability: AdmittedInput, request: dict[str, Any], catalog: dict[str, bytes], training_authority: str, model_name: str = "def_xg_shrink_challenger") -> tuple[str, pd.DataFrame, bool]:
    """Append an attempt, verify a matching cache or publish a complete diagnostic table."""
    resolved = validate_storage_path(store)
    attempts, forecasts = resolved / "attempts", resolved / "forecasts"
    attempts.mkdir(parents=True, exist_ok=True)
    attempt = attempts / uuid.uuid4().hex
    attempt.mkdir()
    (attempt / "started.json").write_bytes(_canonical_json_bytes({"version": 1, "started_at": datetime.now(UTC).isoformat(), "season": capability.season, "issue": capability.gw, "model": model_name}))
    try:
        material = forecast_material(capability, request, catalog, training_authority, model_name)
        forecast_id = _sha256_hex(_canonical_json_bytes(material))
        forecasts.mkdir(parents=True, exist_ok=True)
        destination = forecasts / forecast_id
        rules = get_rules(capability.season)
        origin = next(o for o in request["origins"] if o["season"] == capability.season and o["gw"] == capability.gw)
        if destination.exists():
            frame = _load_forecast_content(resolved, forecast_id, material)
            strict_solver_table(frame, capability, request, catalog)
            validate_components(frame, rules.version)
            hit = True
        else:
            frame, meta = predict_synthetic_issue(capability, request, catalog, training_authority, resolved / "staging", model_name=model_name)
            table = frame.to_csv(index=False, float_format="%.17g", lineterminator="\n").encode()
            coverage_report = {
                "version": 1,
                "forecast_id": forecast_id,
                "season": capability.season,
                "issue_gw": capability.gw,
                "universe_size": len(origin["universe"]),
                "target_gws": origin["target_gws"],
                "rows": len(frame),
                "blanks": int((frame["fixture_id"] == -1).sum()),
                "fixtures": int((frame["fixture_id"] != -1).sum()),
            }
            generator_log = {
                "version": 1,
                "forecast_id": forecast_id,
                "model": model_name,
                "generation": meta,
                "completed_at": datetime.now(UTC).isoformat(),
            }
            rep_bytes = _canonical_json_bytes(coverage_report)
            log_bytes = _canonical_json_bytes(generator_log)
            manifest = {
                "version": 1,
                "forecast_id": forecast_id,
                "material_sha256": forecast_id,
                "forecast_sha256": _sha256_hex(table),
                "coverage_report_sha256": _sha256_hex(rep_bytes),
                "generator_log_sha256": _sha256_hex(log_bytes),
                "rows": len(frame),
                "mode": "synthetic_diagnostic",
                "generation": meta,
            }
            stage = forecasts / (".stage-" + uuid.uuid4().hex)
            stage.mkdir()
            (stage / "material.json").write_bytes(_canonical_json_bytes(material))
            (stage / "forecast.csv").write_bytes(table)
            (stage / "coverage_report.json").write_bytes(rep_bytes)
            (stage / "generator_log.json").write_bytes(log_bytes)
            (stage / "manifest.json").write_bytes(_canonical_json_bytes(manifest))
            try:
                os.rename(stage, destination)
            except FileExistsError:
                import shutil

                shutil.rmtree(stage)
                if (destination / "forecast.csv").read_bytes() != table:
                    raise ValueError("Concurrent forecast content mismatch")
            frame = _load_forecast_content(resolved, forecast_id, material)
            strict_solver_table(frame, capability, request, catalog)
            validate_components(frame, rules.version)
            hit = False
        (attempt / "complete.json").write_bytes(_canonical_json_bytes({"forecast_id": forecast_id, "cache_hit": hit, "completed_at": datetime.now(UTC).isoformat()}))
        return forecast_id, frame, hit
    except Exception as exc:
        (attempt / "failed.json").write_bytes(_canonical_json_bytes({"type": type(exc).__name__, "failed_at": datetime.now(UTC).isoformat()}))
        raise
