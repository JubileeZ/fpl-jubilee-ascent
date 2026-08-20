"""Immutable, point-in-time availability snapshot packages."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd

SNAPSHOT_SCHEMA_VERSION = "1"
SNAPSHOT_ENTITIES = ("players", "clubs", "fixtures")


def _as_utc(value: datetime | str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00")) if isinstance(value, str) else value
    return (parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)).astimezone(UTC)


def is_inside_capture_window(deadline: datetime | str, captured_at: datetime | str) -> bool:
    """Return whether `captured_at` is in the inclusive 48-hour pre-deadline window."""
    deadline_utc = _as_utc(deadline)
    captured_utc = _as_utc(captured_at)
    return deadline_utc - timedelta(hours=48) <= captured_utc < deadline_utc


def _canonical_cell(value: object) -> object:
    """Serialize nested JSON so row sort stays hashable across FPL payload shapes."""
    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    if isinstance(value, (list, tuple)):
        return json.dumps(list(value), sort_keys=True, separators=(",", ":"), default=str)
    return value


def _canonical_frame(frame: pd.DataFrame) -> list[dict[str, object]]:
    if frame.empty:
        return []
    columns = sorted(frame.columns)
    normalized = frame.reindex(columns=columns).map(_canonical_cell)
    normalized = normalized.sort_values(columns, kind="mergesort", na_position="first").reset_index(drop=True)
    return json.loads(normalized.to_json(orient="records", date_format="iso"))


def canonical_content_hash(
    players: pd.DataFrame,
    clubs: pd.DataFrame,
    fixtures: pd.DataFrame,
) -> str:
    """Hash prediction-critical entities independent of row or column order."""
    payload = {
        "players": _canonical_frame(players),
        "clubs": _canonical_frame(clubs),
        "fixtures": _canonical_frame(fixtures),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _metadata_paths(snapshot_root: Path, season: str, target_gw: int) -> list[Path]:
    gameweek_root = snapshot_root / season / f"GW{target_gw}"
    if not gameweek_root.exists():
        return []
    return sorted(
        package / "metadata.json"
        for package in gameweek_root.iterdir()
        if package.is_dir() and (package / "metadata.json").exists()
    )


def write_availability_snapshot(
    snapshot_root: Path,
    season: str,
    target_gw: int,
    deadline: datetime | str,
    captured_at: datetime | str,
    players: pd.DataFrame,
    clubs: pd.DataFrame,
    fixtures: pd.DataFrame,
    source_endpoint_versions: dict[str, str] | None = None,
) -> Path | None:
    """Write a complete package only when inside the window and content changed."""
    deadline_utc = _as_utc(deadline)
    captured_utc = _as_utc(captured_at)
    if not is_inside_capture_window(deadline_utc, captured_utc):
        return None

    content_hash = canonical_content_hash(players, clubs, fixtures)
    for metadata_path in _metadata_paths(snapshot_root, season, target_gw):
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if metadata.get("content_hash") == content_hash:
            return None

    gameweek_root = snapshot_root / season / f"GW{target_gw}"
    gameweek_root.mkdir(parents=True, exist_ok=True)
    captured_label = captured_utc.strftime("%Y%m%dT%H%M%SZ")
    package_name = f"{captured_label}-{content_hash[:12]}"
    if (gameweek_root / package_name).exists():
        package_name = f"{package_name}-{uuid.uuid4().hex[:8]}"
    package_path = gameweek_root / package_name
    temporary_path = gameweek_root / f".{package_name}.tmp-{uuid.uuid4().hex}"
    temporary_path.mkdir()
    metadata = {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "source_endpoint_versions": source_endpoint_versions or {},
        "season": season,
        "target_gameweek": target_gw,
        "deadline": deadline_utc.isoformat().replace("+00:00", "Z"),
        "captured_at": captured_utc.isoformat().replace("+00:00", "Z"),
        "content_hash": content_hash,
        "snapshot_id": f"{season}-GW{target_gw}-{captured_label}-{content_hash[:12]}",
    }
    try:
        players.to_parquet(temporary_path / "players.parquet", index=False)
        clubs.to_parquet(temporary_path / "clubs.parquet", index=False)
        fixtures.to_parquet(temporary_path / "fixtures.parquet", index=False)
        (temporary_path / "metadata.json").write_text(
            json.dumps(metadata, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        try:
            temporary_path.replace(package_path)
        except PermissionError:
            if os.name != "nt":
                raise
            shutil.copytree(temporary_path, package_path)
            shutil.rmtree(temporary_path, ignore_errors=True)  # DESTRUCTIVE: Windows cannot rename dir with open parquet handles.
    except Exception:
        if package_path.exists():
            shutil.rmtree(package_path, ignore_errors=True)  # DESTRUCTIVE: remove incomplete snapshot package.
        shutil.rmtree(temporary_path, ignore_errors=True)  # DESTRUCTIVE: remove failed temporary snapshot package.
        raise
    return package_path


def resolve_latest_snapshot(
    snapshot_root: Path,
    season: str,
    target_gw: int,
    deadline: datetime | str,
) -> dict[str, object] | None:
    """Load the latest complete package captured strictly before a deadline."""
    deadline_utc = _as_utc(deadline)
    candidates: list[tuple[datetime, Path, dict[str, object], pd.DataFrame, pd.DataFrame, pd.DataFrame]] = []
    for metadata_path in _metadata_paths(snapshot_root, season, target_gw):
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        try:
            captured_at = _as_utc(str(metadata["captured_at"]))
            snapshot_deadline = _as_utc(str(metadata["deadline"]))
        except (KeyError, TypeError, ValueError):
            continue
        if (
            metadata.get("schema_version") != SNAPSHOT_SCHEMA_VERSION
            or metadata.get("season") != season
            or metadata.get("target_gameweek") != target_gw
            or snapshot_deadline != deadline_utc
        ):
            continue
        if captured_at >= deadline_utc:
            continue
        package_path = metadata_path.parent
        if not all((package_path / f"{entity}.parquet").exists() for entity in SNAPSHOT_ENTITIES):
            continue
        players = pd.read_parquet(package_path / "players.parquet")
        clubs = pd.read_parquet(package_path / "clubs.parquet")
        fixtures = pd.read_parquet(package_path / "fixtures.parquet")
        if metadata.get("content_hash") != canonical_content_hash(players, clubs, fixtures):
            continue
        candidates.append((captured_at, package_path, metadata, players, clubs, fixtures))
    if not candidates:
        return None

    _, package_path, metadata, players, clubs, fixtures = max(candidates, key=lambda candidate: candidate[0])
    return {
        "path": package_path,
        "metadata": metadata,
        "players": players,
        "clubs": clubs,
        "fixtures": fixtures,
    }
