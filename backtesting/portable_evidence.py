"""Portable, path-safe checkpoint evidence primitives (#193, #198)."""

from __future__ import annotations

import ast
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass, replace
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import posixpath
import re
import subprocess
import tarfile
from tempfile import TemporaryDirectory
import tomllib
from typing import Any, Literal, TypeVar

from backtesting.season_rules import load_season_lifecycle
from models.selection import load_model_selection

PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_DRIVE_RE = re.compile(r"^[A-Za-z]:")
_FORBIDDEN_SEGMENTS = frozenset({"archive", ".git", ".agents"})
_MODELING_PACKAGES = frozenset({"highspy", "numpy", "pandas", "pyarrow", "scipy"})
_LOCAL_PACKAGES = frozenset({"models", "features", "projections", "backtesting", "solver", "clients"})
_RUNTIME_SEED_FILES = (
    "backtesting/native_transfer_solver.py",
    "backtesting/replay_state.py",
    "backtesting/season_rules.py",
    "backtesting/forecast_adapter.py",
    "backtesting/forecast_export.py",
    "config/season_lifecycle.json",
)
_EVALUATOR_EXCLUDED_SEGMENTS = frozenset({"dashboard", "tests", ".git", ".agents", "__pycache__"})

T = TypeVar("T")


class TamperedLedgerError(ValueError):
    """Raised when an append-only ledger or scorecard fails integrity verification."""


def _canonical_json_bytes(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _validate_sha256_hex(value: Any, label: str = "sha256") -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise ValueError(f"Invalid {label}: expected lowercase 64-char hex digest")
    return value


def validate_relative_posix_path(path_str: str) -> str:
    """Normalize and enforce a strict relative POSIX path with no traversal or forbidden segments."""
    if not isinstance(path_str, str) or not path_str or path_str != path_str.strip():
        raise ValueError(f"Invalid relative POSIX path: {path_str!r}")
    if "\x00" in path_str or "\\" in path_str or path_str.startswith("/") or _DRIVE_RE.match(path_str):
        raise ValueError(f"Path must be relative POSIX without drive letters or backslashes: {path_str!r}")
    raw_parts = path_str.split("/")
    if any(part == ".." for part in raw_parts):
        raise ValueError(f"Path traversal '..' forbidden: {path_str!r}")
    if any(part in _FORBIDDEN_SEGMENTS for part in raw_parts):
        raise ValueError(f"Forbidden path segment in {path_str!r}")
    normalized = posixpath.normpath(path_str)
    if normalized in ("", ".") or normalized.startswith("/") or normalized.startswith(".."):
        raise ValueError(f"Normalized path invalid: {path_str!r}")
    norm_parts = normalized.split("/")
    if any(part in ("", ".", "..") or part in _FORBIDDEN_SEGMENTS for part in norm_parts):
        raise ValueError(f"Invalid path segment after normalization: {path_str!r}")
    return normalized


def _ensure_no_symlink_components(root: Path, rel_posix: str) -> Path:
    root_resolved = root.resolve()
    cur = root_resolved
    for part in rel_posix.split("/"):
        cur = cur / part
        if cur.is_symlink():
            raise ValueError(f"Symlink path component forbidden inside evidence root: {rel_posix}")
    resolved = cur.resolve()
    if not resolved.is_relative_to(root_resolved):
        raise ValueError(f"Path escapes confined root: {rel_posix}")
    return resolved


class BlobStore:
    """Content-addressed `blobs/<sha256>` store strictly confined to ``root``."""

    def __init__(self, root: Path | str) -> None:
        raw_root = Path(root)
        self.root = load_season_lifecycle().assert_unsealed_storage_path(
            raw_root, error_message="Protected blob store root"
        )
        self.blobs_dir = self.root / "blobs"

    def relpath(self, digest: str) -> str:
        clean = _validate_sha256_hex(digest, "blob_sha256")
        return f"blobs/{clean}"

    def _resolve_blob_ref(self, digest_or_relpath: str) -> tuple[str, Path]:
        if _SHA256_RE.fullmatch(digest_or_relpath):
            digest = digest_or_relpath
            rel = f"blobs/{digest}"
        else:
            rel = validate_relative_posix_path(digest_or_relpath)
            parts = rel.split("/")
            if len(parts) != 2 or parts[0] != "blobs":
                raise ValueError(f"Blob reference must resolve under blobs/<sha256>: {digest_or_relpath!r}")
            digest = _validate_sha256_hex(parts[1], "blob_sha256")
        if self.blobs_dir.is_symlink():
            raise ValueError("Symlinked blobs directory forbidden")
        resolved = _ensure_no_symlink_components(self.root, rel)
        return digest, resolved

    def exists(self, digest: str) -> bool:
        _, target = self._resolve_blob_ref(digest)
        return target.is_file()

    def write_bytes(self, data: bytes) -> str:
        if not isinstance(data, bytes):
            raise TypeError("BlobStore.write_bytes requires bytes")
        digest = _sha256_bytes(data)
        self.blobs_dir.mkdir(parents=True, exist_ok=True)
        _, dest = self._resolve_blob_ref(digest)
        if dest.exists():
            if not dest.is_file() or _sha256_bytes(dest.read_bytes()) != digest:
                raise ValueError(f"Corrupt existing blob for {digest}")
            return digest
        stage = self.blobs_dir / f".stage-{digest[:12]}-{os.getpid()}"
        try:
            stage.write_bytes(data)
            os.replace(stage, dest)
        finally:
            stage.unlink(missing_ok=True)
        return digest

    def write_canonical_json(self, obj: Any) -> dict[str, str]:
        raw = _canonical_json_bytes(obj)
        digest = self.write_bytes(raw)
        return {"path": self.relpath(digest), "sha256": digest}

    def read_bytes(self, digest_or_relpath: str, *, expected_sha256: str | None = None) -> bytes:
        digest, target = self._resolve_blob_ref(digest_or_relpath)
        if expected_sha256 is not None and _validate_sha256_hex(expected_sha256, "expected_sha256") != digest:
            raise ValueError(f"Blob digest mismatch: expected {expected_sha256}, ref points to {digest}")
        if not target.is_file():
            raise ValueError(f"Missing blob file: blobs/{digest}")
        raw = target.read_bytes()
        actual = _sha256_bytes(raw)
        if actual != digest:
            raise ValueError(f"Blob checksum mismatch for blobs/{digest}: got {actual}")
        return raw

    def verify(self, digest_or_relpath: str, *, expected_sha256: str | None = None) -> str:
        self.read_bytes(digest_or_relpath, expected_sha256=expected_sha256)
        digest, _ = self._resolve_blob_ref(digest_or_relpath)
        return digest


@dataclass(frozen=True)
class ModelRuntimeIdentity:
    """Exact runtime binding for a registered model."""

    model_name: str
    module_name: str
    class_qualname: str
    module_relpath: str
    module_sha256: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class ServingModelClosure:
    """Transitive serving/finalist runtime closure independent of UI/Candidate Search."""

    serving_model_closure_hash: str
    model_runtime_bindings: dict[str, dict[str, str]]
    closure_files: dict[str, str]
    package_pins: dict[str, Any]
    evaluator_code_hash: str
    producer_git_sha: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _discover_models_in_root(root: Path) -> dict[str, tuple[str, str, str]]:
    """Discover unique model_name -> (module_name, class_qualname, module_relpath) in ``root/models``."""
    models_dir = root / "models"
    if not models_dir.is_dir():
        raise ValueError(f"Models directory missing under {root}")
    found: dict[str, tuple[str, str, str]] = {}
    for file in sorted(models_dir.glob("*.py")):
        if file.name in ("__init__.py", "base.py"):
            continue
        tree = ast.parse(file.read_text(encoding="utf-8"), filename=str(file))
        mod_name = f"models.{file.stem}"
        rel_path = f"models/{file.name}"
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            for stmt in node.body:
                if isinstance(stmt, ast.FunctionDef) and stmt.name == "name":
                    for body_stmt in stmt.body:
                        if (
                            isinstance(body_stmt, ast.Return)
                            and isinstance(body_stmt.value, ast.Constant)
                            and isinstance(body_stmt.value.value, str)
                        ):
                            m_name = body_stmt.value.value
                            if m_name in found:
                                raise ValueError(f"Duplicate model name '{m_name}' in {rel_path}")
                            found[m_name] = (mod_name, node.name, rel_path)
    return found


def resolve_model_runtime_identity(model_name: str, project_root: Path | None = None) -> ModelRuntimeIdentity:
    """Resolve exact ``(module_name, class_qualname)`` binding for ``model_name`` in ``models/``."""
    if not isinstance(model_name, str) or not model_name.strip():
        raise ValueError("Model name must be a non-empty string")
    root = (project_root or PROJECT_ROOT).resolve()

    if root == PROJECT_ROOT:
        from models import _iter_registered_models

        discovered = _discover_models_in_root(root)
        matches = [m for m in _iter_registered_models() if m.name == model_name]
        if len(matches) != 1 or model_name not in discovered:
            raise ValueError(f"Model '{model_name}' not uniquely registered in models/")
        inst = matches[0]
        cls = type(inst)
        mod_name = cls.__module__
        qualname = cls.__qualname__
        if not mod_name.startswith("models.") or mod_name in ("models.base", "models"):
            raise ValueError(f"Invalid model module binding for '{model_name}': {mod_name}")
        rel_path = f"{mod_name.replace('.', '/')}.py"
        if discovered[model_name][:2] != (mod_name, qualname):
            raise ValueError(f"Runtime binding mismatch for '{model_name}'")
    else:
        discovered = _discover_models_in_root(root)
        if model_name not in discovered:
            raise ValueError(f"Model '{model_name}' not found under {root / 'models'}")
        mod_name, qualname, rel_path = discovered[model_name]

    mod_file = (root / rel_path).resolve()
    if not mod_file.is_file() or not mod_file.is_relative_to(root):
        raise ValueError(f"Model module file missing or outside root: {rel_path}")
    return ModelRuntimeIdentity(
        model_name=model_name,
        module_name=mod_name,
        class_qualname=qualname,
        module_relpath=rel_path,
        module_sha256=_sha256_bytes(mod_file.read_bytes()),
    )


def _resolve_local_module(root: Path, current_rel: str, module_name: str | None, level: int) -> list[str]:
    """Resolve an AST import target to relative POSIX `.py` paths inside ``root``."""
    candidates: list[str] = []
    if level > 0:
        cur_parts = current_rel.split("/")[:-1]
        if level - 1 > len(cur_parts):
            return []
        base_parts = cur_parts[: len(cur_parts) - (level - 1)]
        full_mod = ".".join([*base_parts, *(module_name.split(".") if module_name else [])])
    elif module_name:
        full_mod = module_name
    else:
        return []

    parts = [p for p in full_mod.split(".") if p]
    if not parts or parts[0] not in _LOCAL_PACKAGES:
        return []
    mod_file = root / Path(*parts).with_suffix(".py")
    pkg_init = root / Path(*parts) / "__init__.py"
    if mod_file.is_file():
        candidates.append(mod_file.relative_to(root).as_posix())
    if pkg_init.is_file():
        candidates.append(pkg_init.relative_to(root).as_posix())
    return candidates


def _parse_modeling_lock_pins(root: Path) -> dict[str, Any]:
    lock_path = root / "uv.lock"
    if not lock_path.is_file():
        raise ValueError(f"Dependency lock uv.lock missing under {root}")
    lock_data = tomllib.loads(lock_path.read_text(encoding="utf-8"))
    pins: dict[str, Any] = {}
    for pkg in lock_data.get("package", ()):
        name = pkg.get("name")
        if name in _MODELING_PACKAGES:
            entry: dict[str, Any] = {
                "name": str(name),
                "version": str(pkg.get("version", "")),
            }
            if "sdist" in pkg:
                entry["sdist"] = pkg["sdist"]
            if "wheels" in pkg:
                entry["wheels"] = pkg["wheels"]
            pins[str(name)] = entry
    missing = sorted(_MODELING_PACKAGES - set(pins))
    if missing:
        raise ValueError(f"Required modeling package pin(s) missing from uv.lock: {missing}")
    return {name: pins[name] for name in sorted(pins)}


def compute_evaluator_code_hash(project_root: Path | None = None) -> str:
    """Compute separate SHA-256 hash of promotion/evaluator modules excluding UI & Candidate Search."""
    root = (project_root or PROJECT_ROOT).resolve()
    material: dict[str, str] = {}
    bt_dir = root / "backtesting"
    if bt_dir.is_dir():
        for path in sorted(bt_dir.rglob("*.py")):
            rel = path.relative_to(root).as_posix()
            if not any(seg in _EVALUATOR_EXCLUDED_SEGMENTS for seg in rel.split("/")):
                material[rel] = _sha256_bytes(path.read_bytes())
    for rel in ("commands/evaluate_model_promotion.py", "commands/produce_validation_evidence.py", "pyproject.toml"):
        p = root / rel
        if p.is_file():
            material[rel] = _sha256_bytes(p.read_bytes())
    return _sha256_bytes(_canonical_json_bytes(material))


def get_producer_git_sha(project_root: Path | None = None) -> str:
    """Return current HEAD commit SHA in ``project_root`` or ``'unknown'`` when unavailable."""
    root = (project_root or PROJECT_ROOT).resolve()
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True, stderr=subprocess.DEVNULL
        ).strip()
        return out or "unknown"
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return "unknown"


def compute_serving_model_closure(
    model_names: Sequence[str],
    project_root: Path | None = None,
) -> ServingModelClosure:
    """Compute transitive AST closure for ``model_names`` plus core runtime & modeling uv.lock pins."""
    root = (project_root or PROJECT_ROOT).resolve()
    ordered_models = tuple(dict.fromkeys(model_names))
    bindings: dict[str, dict[str, str]] = {}
    seed_py: list[str] = []

    for name in ordered_models:
        ident = resolve_model_runtime_identity(name, project_root=root)
        bindings[name] = ident.to_dict()
        seed_py.append(ident.module_relpath)

    for folder in ("features", "projections"):
        fdir = root / folder
        if not fdir.is_dir():
            raise ValueError(f"Required runtime directory missing: {folder}")
        for py in sorted(fdir.rglob("*.py")):
            seed_py.append(py.relative_to(root).as_posix())

    closure_files: dict[str, str] = {}
    for rel in _RUNTIME_SEED_FILES:
        target = (root / rel).resolve()
        if not target.is_file() or not target.is_relative_to(root):
            raise ValueError(f"Required runtime closure file missing: {rel}")
        if rel.endswith(".py"):
            seed_py.append(rel)
        else:
            closure_files[rel] = _sha256_bytes(target.read_bytes())

    visited: set[str] = set()
    queue = list(dict.fromkeys(seed_py))
    while queue:
        rel = queue.pop(0)
        if rel in visited:
            continue
        parts = rel.split("/")
        if rel == "config/model_selection.json" or parts[0] in ("dashboard", "tests", ".git", ".agents", "data"):
            continue
        file_path = (root / rel).resolve()
        if not file_path.is_file() or not file_path.is_relative_to(root):
            continue
        visited.add(rel)
        raw = file_path.read_bytes()
        closure_files[rel] = _sha256_bytes(raw)
        if not rel.endswith(".py"):
            continue
        tree = ast.parse(raw.decode("utf-8"), filename=str(file_path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    for target_rel in _resolve_local_module(root, rel, alias.name, 0):
                        if target_rel not in visited:
                            queue.append(target_rel)
            elif isinstance(node, ast.ImportFrom):
                base_targets = _resolve_local_module(root, rel, node.module, node.level)
                for target_rel in base_targets:
                    if target_rel not in visited:
                        queue.append(target_rel)
                if node.module:
                    for alias in node.names:
                        sub_mod = f"{node.module}.{alias.name}"
                        for target_rel in _resolve_local_module(root, rel, sub_mod, node.level):
                            if target_rel not in visited:
                                queue.append(target_rel)

    sorted_files = {k: closure_files[k] for k in sorted(closure_files)}
    package_pins = _parse_modeling_lock_pins(root)
    closure_payload = {
        "version": 1,
        "model_runtime_bindings": {k: bindings[k] for k in sorted(bindings)},
        "files": sorted_files,
        "packages": package_pins,
    }
    closure_hash = _sha256_bytes(_canonical_json_bytes(closure_payload))
    return ServingModelClosure(
        serving_model_closure_hash=closure_hash,
        model_runtime_bindings=bindings,
        closure_files=sorted_files,
        package_pins=package_pins,
        evaluator_code_hash=compute_evaluator_code_hash(root),
        producer_git_sha=get_producer_git_sha(root),
    )


def _compute_chain_record_hash(payload_without_hash: Mapping[str, Any]) -> str:
    return _sha256_bytes(_canonical_json_bytes(payload_without_hash))


def _load_chained_jsonl(
    ledger_file: Path,
    from_dict_fn: Callable[[dict[str, Any]], T],
    hash_payload_fn: Callable[[T], dict[str, Any]],
) -> list[T]:
    if not ledger_file.is_file():
        return []
    records: list[T] = []
    with ledger_file.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            raw = line.strip()
            if not raw:
                continue
            try:
                data = json.loads(raw)
                rec = from_dict_fn(data)
                expected_hash = _compute_chain_record_hash(hash_payload_fn(rec))
                actual_hash = getattr(rec, "record_hash")
                actual_prev = getattr(rec, "prev_record_hash")
                expected_prev = getattr(records[-1], "record_hash") if records else ("0" * 64)
            except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
                raise TamperedLedgerError(f"Corrupt ledger record at line {line_no}: {exc}") from exc
            if actual_hash != expected_hash:
                raise TamperedLedgerError(f"Ledger record hash mismatch at line {line_no}")
            if actual_prev != expected_prev:
                raise TamperedLedgerError(
                    f"Ledger chain break at line {line_no}: expected prev '{expected_prev}', got '{actual_prev}'"
                )
            records.append(rec)
    return records


def _append_chained_jsonl(ledger_file: Path, record_dict: Mapping[str, Any]) -> None:
    ledger_file.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record_dict, sort_keys=True, allow_nan=False) + "\n"
    with ledger_file.open("a", encoding="utf-8") as handle:
        handle.write(line)
        handle.flush()
        os.fsync(handle.fileno())


@dataclass(frozen=True)
class ExclusionRecord:
    """Append-only SHA-256 hash-chained finalist exclusion entry."""

    slate_id: str
    season: str
    candidate_name: str
    checkpoint_gw: int
    reason_code: str
    details: str
    recorded_at: str
    evidence_hash: str | None = None
    prev_record_hash: str = "0" * 64
    record_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def hash_payload(self) -> dict[str, Any]:
        data = self.to_dict()
        data.pop("record_hash", None)
        return data

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ExclusionRecord":
        return cls(
            slate_id=str(data["slate_id"]),
            season=str(data["season"]),
            candidate_name=str(data["candidate_name"]),
            checkpoint_gw=int(data["checkpoint_gw"]),
            reason_code=str(data["reason_code"]),
            details=str(data["details"]),
            recorded_at=str(data["recorded_at"]),
            evidence_hash=data.get("evidence_hash"),
            prev_record_hash=str(data["prev_record_hash"]),
            record_hash=str(data["record_hash"]),
        )


class ExclusionLedger:
    """Append-only SHA-256 hash-chained ledger tracking finalist exclusions (`exclusions.jsonl`)."""

    def __init__(self, ledger_file: Path | str) -> None:
        self.ledger_file = Path(ledger_file)

    def load_all_records(self) -> list[ExclusionRecord]:
        return _load_chained_jsonl(
            self.ledger_file,
            ExclusionRecord.from_dict,
            ExclusionRecord.hash_payload,
        )

    def verify_integrity(self) -> bool:
        self.load_all_records()
        return True

    def is_excluded(
        self,
        candidate_name: str,
        *,
        slate_id: str | None = None,
        season: str | None = None,
        up_to_gw: int | None = None,
    ) -> bool:
        return candidate_name in self.excluded_candidates(slate_id=slate_id, season=season, up_to_gw=up_to_gw)

    def is_candidate_excluded(
        self,
        candidate_name: str,
        *,
        slate_id: str | None,
        season: str | None,
        up_to_gw: int | None = None,
    ) -> bool:
        """Check whether candidate is excluded on this slate/season or globally across the season."""
        if self.is_excluded(candidate_name, slate_id=slate_id, season=season, up_to_gw=up_to_gw):
            return True
        if slate_id is not None:
            return self.is_excluded(candidate_name, season=season, up_to_gw=up_to_gw)
        return False

    def excluded_candidates(
        self,
        *,
        slate_id: str | None = None,
        season: str | None = None,
        up_to_gw: int | None = None,
    ) -> set[str]:
        return {
            rec.candidate_name
            for rec in self.load_all_records()
            if (slate_id is None or rec.slate_id == slate_id)
            and (season is None or rec.season == season)
            and (up_to_gw is None or rec.checkpoint_gw <= up_to_gw)
        }

    def record_exclusion(
        self,
        *,
        slate_id: str,
        season: str,
        candidate_name: str,
        checkpoint_gw: int,
        reason_code: str,
        details: str,
        recorded_at: str | None = None,
        evidence_hash: str | None = None,
    ) -> ExclusionRecord:
        if not slate_id.strip() or not candidate_name.strip() or not reason_code.strip():
            raise ValueError("Exclusion requires non-empty slate_id, candidate_name, and reason_code")
        if type(checkpoint_gw) is not int or not 1 <= checkpoint_gw <= 38:
            raise ValueError(f"Invalid exclusion checkpoint_gw: {checkpoint_gw}")
        existing = self.load_all_records()
        for rec in existing:
            if rec.slate_id == slate_id and rec.season == season and rec.candidate_name == candidate_name:
                return rec
        prev_hash = existing[-1].record_hash if existing else ("0" * 64)
        from datetime import UTC, datetime

        ts = recorded_at or datetime.now(UTC).isoformat()
        draft = ExclusionRecord(
            slate_id=slate_id,
            season=season,
            candidate_name=candidate_name,
            checkpoint_gw=checkpoint_gw,
            reason_code=reason_code,
            details=details,
            recorded_at=ts,
            evidence_hash=evidence_hash,
            prev_record_hash=prev_hash,
            record_hash="",
        )
        final = replace(draft, record_hash=_compute_chain_record_hash(draft.hash_payload()))
        _append_chained_jsonl(self.ledger_file, final.to_dict())
        return final


AdoptionDisposition = Literal["requested", "approved", "rejected", "expired", "adopted", "invalidated"]


@dataclass(frozen=True)
class AdoptionRecord:
    """Append-only SHA-256 hash-chained human adoption disposition entry."""

    request_id: str
    slate_id: str
    season: str
    checkpoint_gw: int
    candidate_name: str
    expected_champion: str
    bundle_hash: str
    disposition: AdoptionDisposition
    actor: str
    recorded_at: str
    approval_ref: str | None = None
    reason: str = ""
    prev_record_hash: str = "0" * 64
    record_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def hash_payload(self) -> dict[str, Any]:
        data = self.to_dict()
        data.pop("record_hash", None)
        return data

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "AdoptionRecord":
        return cls(
            request_id=str(data["request_id"]),
            slate_id=str(data["slate_id"]),
            season=str(data["season"]),
            checkpoint_gw=int(data["checkpoint_gw"]),
            candidate_name=str(data["candidate_name"]),
            expected_champion=str(data["expected_champion"]),
            bundle_hash=str(data["bundle_hash"]),
            disposition=data["disposition"],
            actor=str(data["actor"]),
            recorded_at=str(data["recorded_at"]),
            approval_ref=data.get("approval_ref"),
            reason=str(data.get("reason", "")),
            prev_record_hash=str(data["prev_record_hash"]),
            record_hash=str(data["record_hash"]),
        )


class AdoptionLedger:
    """Append-only SHA-256 hash-chained human disposition ledger (`adoption_ledger.jsonl`)."""

    def __init__(self, ledger_file: Path | str) -> None:
        self.ledger_file = Path(ledger_file)

    def load_all_records(self) -> list[AdoptionRecord]:
        return _load_chained_jsonl(
            self.ledger_file,
            AdoptionRecord.from_dict,
            AdoptionRecord.hash_payload,
        )

    def verify_integrity(self) -> bool:
        self.load_all_records()
        return True

    def latest_for_request(self, request_id: str) -> AdoptionRecord | None:
        matches = [r for r in self.load_all_records() if r.request_id == request_id]
        return matches[-1] if matches else None

    def latest_for_bundle(self, bundle_hash: str) -> AdoptionRecord | None:
        matches = [r for r in self.load_all_records() if r.bundle_hash == bundle_hash]
        return matches[-1] if matches else None

    def record_disposition(
        self,
        *,
        request_id: str,
        slate_id: str,
        season: str,
        checkpoint_gw: int,
        candidate_name: str,
        expected_champion: str,
        bundle_hash: str,
        disposition: AdoptionDisposition,
        actor: str,
        approval_ref: str | None = None,
        reason: str = "",
        recorded_at: str | None = None,
    ) -> AdoptionRecord:
        _validate_sha256_hex(bundle_hash, "bundle_hash")
        if not request_id.strip() or not slate_id.strip() or not actor.strip():
            raise ValueError("Adoption record requires non-empty request_id, slate_id, and actor")
        existing = self.load_all_records()
        prev_hash = existing[-1].record_hash if existing else ("0" * 64)
        from datetime import UTC, datetime

        ts = recorded_at or datetime.now(UTC).isoformat()
        draft = AdoptionRecord(
            request_id=request_id,
            slate_id=slate_id,
            season=season,
            checkpoint_gw=checkpoint_gw,
            candidate_name=candidate_name,
            expected_champion=expected_champion,
            bundle_hash=bundle_hash,
            disposition=disposition,
            actor=actor,
            recorded_at=ts,
            approval_ref=approval_ref,
            reason=reason,
            prev_record_hash=prev_hash,
            record_hash="",
        )
        final = replace(draft, record_hash=_compute_chain_record_hash(draft.hash_payload()))
        _append_chained_jsonl(self.ledger_file, final.to_dict())
        return final


def _normalize_chain_record(rec: Any) -> dict[str, Any]:
    if isinstance(rec, Mapping):
        return dict(rec)
    to_dict_fn = getattr(rec, "to_dict", None)
    if callable(to_dict_fn):
        return dict(to_dict_fn())  # type: ignore[arg-type]
    raise TypeError(f"Unsupported ledger record type: {type(rec)!r}")


def _verify_record_self_hash(raw_rec: Any, rec_dict: dict[str, Any], idx: int) -> None:
    compute_fn = getattr(raw_rec, "compute_record_hash", None)
    if callable(compute_fn):
        if str(compute_fn()) != rec_dict.get("record_hash"):
            raise ValueError(f"Canonical ledger record_hash mismatch at index {idx}")
        return
    hash_payload_fn = getattr(raw_rec, "hash_payload", None)
    if callable(hash_payload_fn):
        if _compute_chain_record_hash(hash_payload_fn()) != rec_dict.get("record_hash"):  # type: ignore[arg-type]
            raise ValueError(f"Canonical ledger record_hash mismatch at index {idx}")


def verify_chain_extends(
    prefix_records: Sequence[Any],
    canonical_records: Sequence[Any],
) -> bool:
    """Verify ``canonical_records`` preserves exact SHA-256 hash-chained ``prefix_records`` and extends cleanly."""
    prefix = [_normalize_chain_record(r) for r in prefix_records]
    canonical = [_normalize_chain_record(r) for r in canonical_records]
    if len(canonical) < len(prefix):
        raise ValueError("Canonical ledger is shorter than snapshot prefix")
    expected_prev = "0" * 64
    for idx, (raw_rec, rec) in enumerate(zip(canonical_records, canonical, strict=True)):
        if rec.get("prev_record_hash") != expected_prev:
            raise ValueError(f"Canonical ledger hash chain break at index {idx}")
        expected_prev = str(rec.get("record_hash", ""))
        if not _SHA256_RE.fullmatch(expected_prev):
            raise ValueError(f"Invalid record_hash at index {idx}")
        _verify_record_self_hash(raw_rec, rec, idx)
    for idx, p_rec in enumerate(prefix):
        if _canonical_json_bytes(p_rec) != _canonical_json_bytes(canonical[idx]):
            raise ValueError(f"Canonical ledger diverges from snapshot prefix at index {idx}")
    return True


GapStatus = Literal["complete", "transient_gap", "permanent_gap"]


@dataclass(frozen=True)
class VerificationScorecard:
    """Immutable self-hashed per-GW scorecard (`scorecards/gw<NN>.json` + `latest_scorecard.json`)."""

    season: str
    checkpoint_gw: int
    slate_id: str
    slate_sealed: bool
    confirmed_champion: str
    podium_order: tuple[str, ...]
    provisional_active: str | None
    serving_model_closure_hash: str
    model_runtime_bindings: dict[str, dict[str, str]]
    evaluator_code_hash: str
    producer_git_sha: str
    settled_through_gw: int
    gap_status: GapStatus
    first_blocked_gw: int | None
    reason_codes: tuple[str, ...]
    cumulative_net_points: dict[str, float]
    weekly_leader: str | None
    active_exclusions: tuple[str, ...]
    generated_at: str
    checkpoint_action: str | None = None
    bundle_hash: str | None = None
    schema_version: int = 1
    scorecard_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "season": self.season,
            "checkpoint_gw": self.checkpoint_gw,
            "slate_id": self.slate_id,
            "slate_sealed": self.slate_sealed,
            "confirmed_champion": self.confirmed_champion,
            "podium_order": list(self.podium_order),
            "provisional_active": self.provisional_active,
            "serving_model_closure_hash": self.serving_model_closure_hash,
            "model_runtime_bindings": self.model_runtime_bindings,
            "evaluator_code_hash": self.evaluator_code_hash,
            "producer_git_sha": self.producer_git_sha,
            "settled_through_gw": self.settled_through_gw,
            "gap_status": self.gap_status,
            "first_blocked_gw": self.first_blocked_gw,
            "reason_codes": list(self.reason_codes),
            "cumulative_net_points": dict(self.cumulative_net_points),
            "weekly_leader": self.weekly_leader,
            "active_exclusions": list(self.active_exclusions),
            "checkpoint_action": self.checkpoint_action,
            "bundle_hash": self.bundle_hash,
            "generated_at": self.generated_at,
            "scorecard_hash": self.scorecard_hash,
        }

    def compute_hash(self) -> str:
        payload = self.to_dict()
        payload.pop("scorecard_hash", None)
        return _sha256_bytes(_canonical_json_bytes(payload))

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "VerificationScorecard":
        return cls(
            schema_version=int(data.get("schema_version", 1)),
            season=str(data["season"]),
            checkpoint_gw=int(data["checkpoint_gw"]),
            slate_id=str(data["slate_id"]),
            slate_sealed=bool(data["slate_sealed"]),
            confirmed_champion=str(data["confirmed_champion"]),
            podium_order=tuple(str(x) for x in data.get("podium_order", ())),
            provisional_active=data.get("provisional_active"),
            serving_model_closure_hash=str(data["serving_model_closure_hash"]),
            model_runtime_bindings={
                str(k): {str(sk): str(sv) for sk, sv in v.items()}
                for k, v in dict(data.get("model_runtime_bindings", {})).items()
            },
            evaluator_code_hash=str(data["evaluator_code_hash"]),
            producer_git_sha=str(data["producer_git_sha"]),
            settled_through_gw=int(data["settled_through_gw"]),
            gap_status=data["gap_status"],
            first_blocked_gw=data.get("first_blocked_gw"),
            reason_codes=tuple(str(x) for x in data.get("reason_codes", ())),
            cumulative_net_points={str(k): float(v) for k, v in dict(data.get("cumulative_net_points", {})).items()},
            weekly_leader=data.get("weekly_leader"),
            active_exclusions=tuple(str(x) for x in data.get("active_exclusions", ())),
            checkpoint_action=data.get("checkpoint_action"),
            bundle_hash=data.get("bundle_hash"),
            generated_at=str(data["generated_at"]),
            scorecard_hash=str(data.get("scorecard_hash", "")),
        )


def write_scorecard(root: Path | str, scorecard: VerificationScorecard) -> tuple[Path, Path]:
    """Write self-hashed ``scorecards/gw<NN>.json`` and ``latest_scorecard.json`` atomically."""
    base = load_season_lifecycle().assert_unsealed_storage_path(Path(root), error_message="Protected scorecard root")
    signed = replace(scorecard, scorecard_hash=scorecard.compute_hash())
    raw = json.dumps(signed.to_dict(), indent=2, sort_keys=True, allow_nan=False).encode("utf-8") + b"\n"
    sc_dir = base / "scorecards"
    sc_dir.mkdir(parents=True, exist_ok=True)
    gw_path = sc_dir / f"gw{signed.checkpoint_gw:02d}.json"
    latest_path = base / "latest_scorecard.json"
    for dest in (gw_path, latest_path):
        tmp = dest.with_suffix(".tmp")
        tmp.write_bytes(raw)
        os.replace(tmp, dest)
    return gw_path, latest_path


def load_and_verify_scorecard(path: Path | str) -> VerificationScorecard:
    """Load and verify self-hashed ``VerificationScorecard``."""
    target = Path(path)
    data = json.loads(target.read_bytes())
    sc = VerificationScorecard.from_dict(data)
    if not sc.scorecard_hash or sc.scorecard_hash != sc.compute_hash():
        raise TamperedLedgerError(f"VerificationScorecard hash mismatch in {target}")
    return sc


def _verify_bundle_in_dir(bundle_path: Path, *, require_finalized: bool = True) -> dict[str, Any]:
    from backtesting.promotion_evidence import verify_checkpoint_recommendation_bundle

    return verify_checkpoint_recommendation_bundle(bundle_path, require_finalized=require_finalized)


def _collect_snapshot_files(
    root: Path,
    bundle_rel: str,
    bundle: Mapping[str, Any],
    request: Mapping[str, Any],
    exclusions_path: Path | None,
) -> dict[str, bytes]:
    """Collect frozen relative-POSIX byte copies for an immutable checkpoint snapshot."""
    collected: dict[str, bytes] = {}

    def _add_file(rel_raw: Any, *, required: bool = True) -> None:
        if rel_raw is None:
            if required:
                raise ValueError("Missing required snapshot file reference")
            return
        rel = validate_relative_posix_path(str(rel_raw))
        target = _ensure_no_symlink_components(root, rel)
        if not target.is_file():
            if required:
                raise ValueError(f"Missing snapshot member: {rel}")
            return
        collected[rel] = target.read_bytes()

    def _add_admission_context(ref: Mapping[str, Any]) -> None:
        ref_rel = validate_relative_posix_path(str(ref["path"]))
        _add_file(ref_rel)
        ctx = json.loads(collected[ref_rel].decode("utf-8"))
        for val in ctx.get("catalog", {}).values():
            if isinstance(val, Mapping):
                sha = val.get("sha256") or val.get("blob_sha256")
                blob_rel = val.get("path") or (f"blobs/{sha}" if sha else None)
                if blob_rel:
                    _add_file(blob_rel)

    _add_file(bundle_rel)
    _add_file(bundle["request_path"])
    _add_file(request["selection_path"])
    _add_file(request["protocol"]["path"])
    _add_file(request["parameters"]["path"])
    _add_file(request["registry_path"])

    if exclusions_path is not None:
        ep = Path(exclusions_path).resolve()
        if not ep.is_file():
            raise ValueError(f"Explicit exclusions_path not found: {exclusions_path}")
        ExclusionLedger(ep).verify_integrity()
        collected["exclusions.jsonl"] = ep.read_bytes()
    else:
        default_excl = root / "exclusions.jsonl"
        if default_excl.is_file():
            _add_file("exclusions.jsonl")
            ExclusionLedger(default_excl).verify_integrity()
        else:
            collected["exclusions.jsonl"] = b""

    if isinstance(request.get("s1_guard_baseline"), Mapping):
        _add_file(request["s1_guard_baseline"]["path"])

    for dev_ref in request.get("development_selections", {}).values():
        if isinstance(dev_ref, Mapping) and "path" in dev_ref:
            _add_file(dev_ref["path"])

    for g_src in request.get("guard_outcome_sources", ()):
        if isinstance(g_src, Mapping) and isinstance(g_src.get("admission"), Mapping):
            _add_admission_context(g_src["admission"])

    for replay in request.get("replays", ()):
        if isinstance(replay.get("anchor"), Mapping):
            _add_file(replay["anchor"]["path"])
        if isinstance(replay.get("trace"), Mapping):
            _add_file(replay["trace"]["path"])
        for issue in replay.get("issues", ()):
            if isinstance(issue.get("admission"), Mapping):
                _add_admission_context(issue["admission"])
            fstore = issue.get("forecast_store")
            fid = issue.get("forecast_id")
            if isinstance(fstore, str) and isinstance(fid, str):
                store_rel = validate_relative_posix_path(fstore)
                _validate_sha256_hex(fid, "forecast_id")
                fdir_rel = f"{store_rel}/forecasts/{fid}"
                fdir = _ensure_no_symlink_components(root, fdir_rel)
                if not fdir.is_dir():
                    raise ValueError(f"Missing forecast cache directory: {fdir_rel}")
                for item in sorted(fdir.iterdir()):
                    if item.is_symlink():
                        raise ValueError(f"Symlink forbidden in forecast cache: {item}")
                    if item.is_file():
                        _add_file(f"{fdir_rel}/{item.name}")

    return {k: collected[k] for k in sorted(collected)}


def pack_checkpoint_snapshot(
    bundle_path: Path | str,
    *,
    output_dir: Path | str | None = None,
    exclusions_path: Path | str | None = None,
    project_root: Path | str | None = None,
) -> dict[str, Any]:
    """Package frozen byte-copies of a finalized passing checkpoint into a deterministic tar.gz snapshot."""
    bpath = Path(bundle_path).resolve()
    root = bpath.parent
    bundle_rel = validate_relative_posix_path(bpath.name)
    bundle = _verify_bundle_in_dir(bpath, require_finalized=True)
    if (
        bundle.get("scientific_verdict") != "pass"
        or bundle.get("execution_status") != "complete"
        or bundle.get("empirical_admission") is not True
    ):
        raise ValueError("Immutable checkpoint snapshot requires a finalized empirical scientific pass")

    request = json.loads((root / validate_relative_posix_path(bundle["request_path"])).read_bytes())
    selection = load_model_selection(root / validate_relative_posix_path(request["selection_path"]))
    season = selection.podium_frozen_season
    if not season:
        raise ValueError("Checkpoint snapshot requires frozen active validation season in selection.json")
    checkpoint_gw = int(bundle["checkpoint_gw"])
    bundle_hash = _validate_sha256_hex(bundle["bundle_hash"], "bundle_hash")

    closure = compute_serving_model_closure(
        [selection.champion, *selection.candidates],
        project_root=Path(project_root) if project_root is not None else None,
    )
    if bundle.get("serving_model_closure_hash") and bundle["serving_model_closure_hash"] != closure.serving_model_closure_hash:
        raise ValueError("Bundle serving_model_closure_hash differs from current runtime closure")
    if bundle.get("model_runtime_bindings") and bundle["model_runtime_bindings"] != closure.model_runtime_bindings:
        raise ValueError("Bundle model_runtime_bindings differ from current runtime bindings")

    files = _collect_snapshot_files(
        root,
        bundle_rel,
        bundle,
        request,
        Path(exclusions_path) if exclusions_path is not None else None,
    )
    dest_dir = Path(output_dir).resolve() if output_dir is not None else root
    dest_dir = load_season_lifecycle().assert_unsealed_storage_path(dest_dir, error_message="Protected snapshot output")
    dest_dir.mkdir(parents=True, exist_ok=True)
    stem = f"checkpoint-{season}-gw{checkpoint_gw:02d}-{bundle_hash[:12]}"
    archive_path = dest_dir / f"{stem}.tar.gz"
    manifest_path = dest_dir / f"{stem}.manifest.json"

    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as gz:
        with tarfile.open(fileobj=gz, mode="w", format=tarfile.USTAR_FORMAT) as tf:
            for rel, raw in sorted(files.items()):
                info = tarfile.TarInfo(name=rel)
                info.size = len(raw)
                info.mode = 0o644
                info.mtime = 0
                info.uid = 0
                info.gid = 0
                info.uname = ""
                info.gname = ""
                tf.addfile(info, io.BytesIO(raw))
    archive_bytes = buf.getvalue()
    archive_sha256 = _sha256_bytes(archive_bytes)
    tmp_tar = archive_path.with_suffix(".tar.gz.tmp")
    tmp_tar.write_bytes(archive_bytes)
    os.replace(tmp_tar, archive_path)

    from backtesting.confirmation_registry import ConfirmationRegistry

    reg_records = ConfirmationRegistry(root / validate_relative_posix_path(request["registry_path"])).load_all_records()
    excl_tmp = root / "exclusions.jsonl"
    if exclusions_path is not None:
        excl_records = ExclusionLedger(Path(exclusions_path)).load_all_records()
    elif excl_tmp.is_file():
        excl_records = ExclusionLedger(excl_tmp).load_all_records()
    else:
        excl_records = []

    manifest = {
        "schema_version": 1,
        "archive_name": archive_path.name,
        "archive_sha256": archive_sha256,
        "season": season,
        "checkpoint_gw": checkpoint_gw,
        "bundle_relpath": bundle_rel,
        "bundle_hash": bundle_hash,
        "expected_champion": selection.champion,
        "recommended_champion": bundle.get("recommended_champion") or bundle.get("candidate_name"),
        "serving_model_closure_hash": closure.serving_model_closure_hash,
        "model_runtime_bindings": closure.model_runtime_bindings,
        "evaluator_code_hash": closure.evaluator_code_hash,
        "producer_git_sha": closure.producer_git_sha,
        "registry_head_hash": reg_records[-1].record_hash if reg_records else ("0" * 64),
        "exclusions_head_hash": excl_records[-1].record_hash if excl_records else ("0" * 64),
        "files": {rel: _sha256_bytes(raw) for rel, raw in sorted(files.items())},
    }
    tmp_man = manifest_path.with_suffix(".manifest.tmp")
    tmp_man.write_bytes(json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False).encode("utf-8") + b"\n")
    os.replace(tmp_man, manifest_path)

    return {
        "archive_path": str(archive_path),
        "manifest_path": str(manifest_path),
        "archive_sha256": archive_sha256,
        "bundle_hash": bundle_hash,
        "manifest": manifest,
    }


def verify_checkpoint_snapshot_archive(
    archive_path: Path | str,
    *,
    expected_archive_sha256: str | None = None,
    manifest_path: Path | str | None = None,
    expected_champion: str | None = None,
    canonical_registry_path: Path | str | None = None,
    canonical_exclusions_path: Path | str | None = None,
    project_root: Path | str | None = None,
) -> dict[str, Any]:
    """Verify snapshot digest, safely extract to an isolated directory, and offline-verify bundle & chains."""
    apath = Path(archive_path).resolve()
    if not apath.is_file():
        raise ValueError(f"Snapshot archive not found: {apath}")
    raw_archive = apath.read_bytes()
    actual_archive_sha256 = _sha256_bytes(raw_archive)

    manifest: dict[str, Any] | None = None
    if manifest_path is not None:
        mpath = Path(manifest_path).resolve()
        loaded_manifest = json.loads(mpath.read_bytes())
        if not isinstance(loaded_manifest, dict):
            raise ValueError("Snapshot manifest must be a JSON object")
        manifest = loaded_manifest
        expected_from_manifest = manifest.get("archive_sha256")
        if _validate_sha256_hex(expected_from_manifest, "manifest.archive_sha256") != actual_archive_sha256:
            raise ValueError("Snapshot archive_sha256 mismatch against manifest")
    if expected_archive_sha256 is not None:
        if _validate_sha256_hex(expected_archive_sha256, "expected_archive_sha256") != actual_archive_sha256:
            raise ValueError("Snapshot archive_sha256 mismatch against expected digest")
    if manifest is None and expected_archive_sha256 is None:
        raise ValueError("Snapshot verification requires manifest_path or expected_archive_sha256")

    with TemporaryDirectory(prefix="chk-verify-") as tmpdir:
        extract_root = Path(tmpdir).resolve()
        extracted_files: dict[str, str] = {}
        with tarfile.open(fileobj=io.BytesIO(raw_archive), mode="r:gz") as tf:
            for member in tf.getmembers():
                if member.issym() or member.islnk():
                    raise ValueError(f"Symlink/hardlink forbidden in checkpoint snapshot: {member.name!r}")
                if member.isdir():
                    continue
                if not member.isreg():
                    raise ValueError(f"Non-regular archive member forbidden: {member.name!r}")
                rel = validate_relative_posix_path(member.name)
                dest = _ensure_no_symlink_components(extract_root, rel)
                dest.parent.mkdir(parents=True, exist_ok=True)
                extracted = tf.extractfile(member)
                if extracted is None:
                    raise ValueError(f"Failed reading archive member: {rel}")
                data = extracted.read()
                dest.write_bytes(data)
                extracted_files[rel] = _sha256_bytes(data)

        if manifest is not None and manifest.get("files") != extracted_files:
            raise ValueError("Snapshot manifest file inventory or checksums mismatch")

        bundle_rel = validate_relative_posix_path(
            str(manifest["bundle_relpath"]) if manifest and manifest.get("bundle_relpath") else "bundle.json"
        )
        bundle_file = _ensure_no_symlink_components(extract_root, bundle_rel)
        if not bundle_file.is_file():
            raise ValueError(f"Bundle missing from snapshot archive: {bundle_rel}")

        bundle = _verify_bundle_in_dir(bundle_file, require_finalized=True)
        if (
            bundle.get("scientific_verdict") != "pass"
            or bundle.get("execution_status") != "complete"
            or bundle.get("empirical_admission") is not True
        ):
            raise ValueError("Snapshot bundle is not a finalized empirical scientific pass")
        if manifest is not None and bundle.get("bundle_hash") != manifest.get("bundle_hash"):
            raise ValueError("Snapshot bundle_hash differs from manifest")

        request = json.loads((_ensure_no_symlink_components(extract_root, validate_relative_posix_path(bundle["request_path"]))).read_bytes())
        selection = load_model_selection(
            _ensure_no_symlink_components(extract_root, validate_relative_posix_path(request["selection_path"]))
        )
        expected_champ = expected_champion or (manifest.get("expected_champion") if manifest else None)
        if expected_champ is not None and (
            bundle.get("former_champion") != expected_champ or selection.champion != expected_champ
        ):
            raise ValueError(f"Expected Champion '{expected_champ}' mismatch")

        closure = compute_serving_model_closure(
            [selection.champion, *selection.candidates],
            project_root=Path(project_root) if project_root is not None else None,
        )
        if bundle.get("serving_model_closure_hash") != closure.serving_model_closure_hash:
            raise ValueError("Snapshot serving_model_closure_hash mismatch")
        if bundle.get("model_runtime_bindings") != closure.model_runtime_bindings:
            raise ValueError("Snapshot model_runtime_bindings mismatch")
        if manifest is not None:
            if manifest.get("serving_model_closure_hash") != closure.serving_model_closure_hash:
                raise ValueError("Manifest serving_model_closure_hash mismatch")
            if manifest.get("model_runtime_bindings") != closure.model_runtime_bindings:
                raise ValueError("Manifest model_runtime_bindings mismatch")

        from backtesting.confirmation_registry import ConfirmationRegistry

        snap_reg_path = _ensure_no_symlink_components(
            extract_root, validate_relative_posix_path(request["registry_path"])
        )
        snap_reg_records = ConfirmationRegistry(snap_reg_path).load_all_records()
        if canonical_registry_path is not None:
            canon_reg = ConfirmationRegistry(canonical_registry_path)
            canon_reg_records = canon_reg.load_all_records()
            verify_chain_extends(snap_reg_records, canon_reg_records)
            attempt_id = bundle.get("confirmation_attempt_id")
            if attempt_id:
                latest_canon = canon_reg.get_attempt(str(attempt_id))
                if latest_canon is None or latest_canon.status in ("withdrawn", "invalidated"):
                    raise ValueError(f"Canonical registry invalidated or withdrew attempt '{attempt_id}'")

        snap_excl_path = _ensure_no_symlink_components(extract_root, "exclusions.jsonl")
        snap_excl_records = ExclusionLedger(snap_excl_path).load_all_records()
        if canonical_exclusions_path is not None:
            canon_excl = ExclusionLedger(canonical_exclusions_path)
            canon_excl_records = canon_excl.load_all_records()
            verify_chain_extends(snap_excl_records, canon_excl_records)
            target_cand = str(bundle.get("recommended_champion") or bundle.get("candidate_name"))
            season = selection.podium_frozen_season
            if any(
                rec.candidate_name == target_cand and (season is None or rec.season == season)
                for rec in canon_excl_records
            ):
                raise ValueError(f"Candidate '{target_cand}' was subsequently excluded in canonical ExclusionLedger")

    return {
        "archive_sha256": actual_archive_sha256,
        "bundle": bundle,
        "serving_model_closure_hash": closure.serving_model_closure_hash,
        "model_runtime_bindings": closure.model_runtime_bindings,
        "snapshot_files": sorted(extracted_files),
    }
