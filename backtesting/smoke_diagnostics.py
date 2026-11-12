"""Retained, versioned Development Screen evidence without promotion authority."""

from __future__ import annotations

import csv
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import platform
import tempfile
from typing import Any

import numpy as np
import pandas as pd

from backtesting.metrics import formation_xi_regret_by_gameweek
from backtesting.promotion import OracleEventGateVerdict, compute_playable_pool_metrics, evaluate_oracle_event_gate
from backtesting.walkforward import WalkforwardResult

SCHEMA_VERSION = 2
SUMMARY_FIELDS: tuple[str, ...] = (
    "schema_version", "date", "season", "data_season", "lane", "variant", "champion", "gw_range",
    "run_id", "stage", "terminal", "participation_mode", "scoring_context", "eval_target", "seed_season",
    "pass", "combined_delta", "min_effect", "segs", "boot_p_gt0", "guardrails_passed", "reasons", "source",
    "evidence_kind", "scientific_verdict", "execution_status", "promotion_execution_status", "dead_lever_authority",
    "evidence_path", "evidence_sha256",
)


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def digest(value: Any) -> str:
    return hashlib.sha256(_json_bytes(value)).hexdigest()


def file_digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def versioned_output(path: Path) -> Path:
    return path if path.stem.endswith(".v2") else path.with_stem(path.stem + ".v2")


def input_identity(root: Path, data_dir: Path, seed_dir: Path | None, prototype: Path | None) -> dict[str, Any]:
    paths = [path for directory in ("backtesting", "clients", "commands", "features", "models", "projections", "solver", "docs/research") for path in (root / directory).rglob("*.py")]
    paths += [root / ".agents/skills/explore-candidate/smoke.py", root / "pyproject.toml", root / "uv.lock", root / "config/model_selection.json"]
    if prototype is not None:
        paths.extend(prototype.parent.rglob("*.py"))
    sources = {str(path.resolve().relative_to(root.resolve())) if path.resolve().is_relative_to(root.resolve()) else str(path.resolve()): file_digest(path) for path in sorted(set(paths)) if path.is_file()}
    inputs: dict[str, dict[str, str]] = {}
    for label, directory in (("season", data_dir), ("seed", seed_dir)):
        if directory is None:
            continue
        inputs[label] = {name: file_digest(directory / name) for name in ("players.parquet", "player_performances.parquet", "fixtures.parquet", "clubs.parquet", "gameweeks.parquet")}
    return {
        "sources": sources, "inputs": inputs, "python": platform.python_version(),
        "packages": {name: version(name) for name in ("pandas", "numpy", "pyarrow", "scipy", "highspy")},
        "parameters": {}, "construction": "default no-argument model constructors; source-bound defaults",
    }


def paired_playable_metrics(reference: pd.DataFrame, candidate: pd.DataFrame, target: str) -> tuple[dict[str, float], dict[str, float]]:
    keys = ["gameweek", "player_id"]
    required = [*keys, "projected_points", "actual_minutes", target]
    for frame in (reference, candidate):
        if any(column not in frame for column in required) or frame.empty or frame.duplicated(keys).any():
            raise ValueError("Diagnostic evidence requires unique, nonempty paired player/gameweek frames")
        if not np.isfinite(frame[required].to_numpy(dtype=float)).all():
            raise ValueError("Diagnostic frame contains non-finite required values")
    ref = reference.sort_values(keys).reset_index(drop=True)
    cand = candidate.sort_values(keys).reset_index(drop=True)
    if not ref[keys].equals(cand[keys]) or not np.array_equal(ref[[target, "actual_minutes"]].to_numpy(), cand[[target, "actual_minutes"]].to_numpy()):
        raise ValueError("Diagnostic populations and observed targets must match exactly")
    champion_pool, candidate_pool = compute_playable_pool_metrics(ref, cand, target_column=target)
    if not champion_pool or not candidate_pool or champion_pool["sample_count"] != candidate_pool["sample_count"]:
        raise ValueError("Common playable-pool evidence is empty or inconsistent")
    if not np.isfinite([champion_pool["bias"], candidate_pool["bias"]]).all():
        raise ValueError("Common playable-pool evidence is non-finite")
    return champion_pool, candidate_pool


def paired_weekly_regret(reference: pd.DataFrame, candidate: pd.DataFrame, target: str) -> pd.DataFrame:
    paired_playable_metrics(reference, candidate, target)
    champion_regret = formation_xi_regret_by_gameweek(reference, target_column=target)
    candidate_regret = formation_xi_regret_by_gameweek(candidate, target_column=target)
    if not champion_regret.index.equals(candidate_regret.index):
        raise ValueError("Paired weekly regrets require identical calendars")
    return pd.DataFrame({"gameweek": champion_regret.index, "champion_regret": champion_regret.to_numpy(),
                         "candidate_regret": candidate_regret.to_numpy(), "delta": (champion_regret - candidate_regret).to_numpy()})


def oracle_event_screen(reference: WalkforwardResult, candidate: WalkforwardResult, *, target: str) -> tuple[OracleEventGateVerdict, pd.DataFrame]:
    champion_pool, candidate_pool = paired_playable_metrics(reference.df_eval, candidate.df_eval, target)
    weekly = paired_weekly_regret(reference.df_eval, candidate.df_eval, target)
    verdict = evaluate_oracle_event_gate(
        reference.metrics, candidate.metrics, gw_deltas=weekly["delta"].tolist(), all_gameweeks=weekly["gameweek"].tolist(),
        champion_playable_bias=champion_pool["bias"], candidate_playable_bias=candidate_pool["bias"],
    )
    return verdict, weekly


class DiagnosticStore:
    def __init__(self, output: Path) -> None:
        self.output = versioned_output(output)
        self.evidence_root = self.output.parent / (self.output.stem + ".evidence")

    def rows(self) -> list[dict[str, str]]:
        if not self.output.exists():
            return []
        with self.output.open(newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != list(SUMMARY_FIELDS):
                raise ValueError("Diagnostic schema differs; preserve existing output and select a new v2 file")
            return list(reader)

    def record(
        self, identity: dict[str, Any], summary: dict[str, Any], *, reference: pd.DataFrame | None = None,
        candidate: pd.DataFrame | None = None, weekly: pd.DataFrame | None = None,
    ) -> dict[str, str]:
        row: dict[str, Any] = {
            **summary, "schema_version": SCHEMA_VERSION, "run_id": digest(identity),
            "evidence_kind": "development_screen_diagnostic", "scientific_verdict": "inconclusive",
            "promotion_execution_status": "not_run", "dead_lever_authority": False,
        }
        if row["execution_status"] == "partial":
            row["scientific_verdict"] = "invalid"
        self.rows()
        self.evidence_root.mkdir(parents=True, exist_ok=True)
        stage_dir = Path(tempfile.mkdtemp(prefix=".pending-", dir=self.evidence_root))
        try:
            if row["execution_status"] == "complete":
                if reference is None or candidate is None or weekly is None:
                    raise ValueError("Completed diagnostic requires paired frames and weekly trace")
                pools = paired_playable_metrics(reference, candidate, str(row["eval_target"]))
                first, last = map(int, str(identity["gw_range"]).split("-"))
                requested = set(range(first, last + 1))
                if set(reference["gameweek"]) != requested or set(weekly["gameweek"]) != requested:
                    raise ValueError("Diagnostic evidence does not cover requested calendar")
                if weekly.empty or weekly["gameweek"].duplicated().any() or not np.isfinite(weekly.to_numpy(dtype=float)).all():
                    raise ValueError("Paired weekly trace must be unique, finite and nonempty")
                if not np.allclose(weekly["delta"], weekly["champion_regret"] - weekly["candidate_regret"], rtol=0, atol=1e-9):
                    raise ValueError("Paired weekly trace does not reconcile")
                if row.get("combined_delta") is not None and not np.isclose(float(row["combined_delta"]), float(weekly["delta"].to_numpy(dtype=float).mean()), rtol=0, atol=1e-8):
                    raise ValueError("Diagnostic delta differs from paired weekly trace")
                reference.to_parquet(stage_dir / "reference.parquet", index=False)
                candidate.to_parquet(stage_dir / "candidate.parquet", index=False)
                weekly.to_csv(stage_dir / "weekly.csv", index=False)
                (stage_dir / "playable_pool.json").write_bytes(_json_bytes({"champion": pools[0], "candidate": pools[1]}))
            normalized = {field: "" if row.get(field) is None else str(row[field]) for field in SUMMARY_FIELDS if field not in ("evidence_path", "evidence_sha256")}
            manifest = {
                "version": SCHEMA_VERSION, "identity": identity, "summary": normalized,
                "files": {path.name: file_digest(path) for path in sorted(stage_dir.iterdir())},
            }
            payload = _json_bytes(manifest)
            manifest_hash = hashlib.sha256(payload).hexdigest()
            (stage_dir / "manifest.json").write_bytes(payload)
            destination = self.evidence_root / manifest_hash
            if destination.exists():
                for path in stage_dir.iterdir():
                    if not (destination / path.name).is_file() or file_digest(path) != file_digest(destination / path.name):
                        raise ValueError("Existing diagnostic evidence was modified")
            else:
                os.rename(stage_dir, destination)
            normalized["evidence_path"] = str((destination / "manifest.json").relative_to(self.output.parent))
            normalized["evidence_sha256"] = manifest_hash
            self.output.parent.mkdir(parents=True, exist_ok=True)
            with self.output.open("a", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=SUMMARY_FIELDS, lineterminator="\n")
                if handle.tell() == 0:
                    writer.writeheader()
                writer.writerow(normalized)
            return normalized
        finally:
            if stage_dir.exists():
                for path in stage_dir.iterdir():
                    path.unlink()
                stage_dir.rmdir()

    def verify(self, row: dict[str, str]) -> None:
        path = (self.output.parent / row["evidence_path"]).resolve()
        if not path.is_relative_to(self.evidence_root.resolve()) or file_digest(path) != row["evidence_sha256"]:
            raise ValueError("Diagnostic manifest is missing, changed or outside evidence root")
        manifest = json.loads(path.read_text())
        if manifest["version"] != SCHEMA_VERSION or digest(manifest["identity"]) != row["run_id"]:
            raise ValueError("Diagnostic identity mismatch")
        if manifest["summary"] != {key: row[key] for key in SUMMARY_FIELDS if key not in ("evidence_path", "evidence_sha256")}:
            raise ValueError("Diagnostic summary differs from retained manifest")
        required = {"reference.parquet", "candidate.parquet", "weekly.csv", "playable_pool.json"}
        if row["execution_status"] == "complete" and set(manifest["files"]) != required:
            raise ValueError("Completed diagnostic evidence is incomplete")
        for name, expected in manifest["files"].items():
            artifact = (path.parent / name).resolve()
            if artifact.parent != path.parent or file_digest(artifact) != expected:
                raise ValueError("Diagnostic artifact changed or escaped its bundle")

    def completed(self, identities: dict[str, dict[str, Any]]) -> set[str]:
        rows = self.rows()
        completed: set[str] = set()
        for name, identity in identities.items():
            selected = [row for row in rows if row["run_id"] == digest(identity)]
            for row in selected:
                self.verify(row)
            terminals = [row for row in selected if row["terminal"] == "True" and row["execution_status"] == "complete"]
            if not terminals:
                continue
            if identity["initial_tier"] == "2" and terminals[-1]["stage"] == "integrated" and not any(row["stage"] == "oracle" and row["pass"] == "True" for row in selected):
                raise ValueError("Integrated event screen lacks its successful oracle stage")
            completed.add(name)
        return completed
