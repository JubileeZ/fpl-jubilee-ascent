"""Live Season Pin: Official FPL only, hash-gated git commit hint."""

from __future__ import annotations

import hashlib
import json
import logging
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from features.expected_role_prior import LIVE_SEASON

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONTENT_HASH_FILENAME = "official_content_hash"
logger = logging.getLogger(__name__)

OFFICIAL_PROCESSED_FILES = frozenset(
    {
        "clubs.parquet",
        "fixtures.parquet",
        "gameweeks.parquet",
        "players.parquet",
        "player_performances.parquet",
        "price_history.parquet",
    }
)


@dataclass(frozen=True)
class LiveSeasonPin:
    processed_dir: Path
    content_hash: str
    changed: bool


def archive_raw_dir(season: str, *, archive_root: Path | None = None) -> Path:
    root = archive_root or (PROJECT_ROOT / "data" / "archive")
    return root / season / "raw"


def archive_processed_dir(season: str, *, archive_root: Path | None = None) -> Path:
    root = archive_root or (PROJECT_ROOT / "data" / "archive")
    return root / season / "processed"


def is_official_raw_filename(name: str) -> bool:
    if name in {"bootstrap_static.json", "fixtures_all.json"}:
        return True
    if name.startswith("element_summary_") and name.endswith(".json"):
        return True
    if name.startswith("event_") and name.endswith("_live.json"):
        return True
    if name.startswith("fixtures_gw_") and name.endswith(".json"):
        return True
    return False


def is_official_processed_filename(name: str) -> bool:
    return name in OFFICIAL_PROCESSED_FILES


def heal_operational_official_from_pin(
    project_root: Path,
    *,
    live_season: str = LIVE_SEASON,
) -> tuple[Path, bool]:
    """Copy Live Season Pin Official processed tables into `data/processed` when they diverge.

    User Squad and other non-Official files under `data/processed` are untouched.
    Returns (operational processed dir, healed).
    """
    processed = project_root / "data" / "processed"
    pin = archive_processed_dir(live_season, archive_root=project_root / "data" / "archive")
    if not pin.is_dir():
        return processed, False
    pin_files = [pin / name for name in sorted(OFFICIAL_PROCESSED_FILES) if (pin / name).is_file()]
    if not pin_files:
        return processed, False

    healed = False
    processed.mkdir(parents=True, exist_ok=True)
    for src in pin_files:
        dest = processed / src.name
        if dest.is_file() and dest.read_bytes() == src.read_bytes():
            continue
        shutil.copy2(src, dest)
        healed = True
    if healed:
        logger.info(
            "Healed Official Operational tables from Live Season Pin %s -> %s",
            pin,
            processed,
        )
    return processed, healed


def _canonical_json_bytes(path: Path) -> bytes:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return path.read_bytes()
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def official_content_hash(raw_dir: Path) -> str:
    digest = hashlib.sha256()
    if not raw_dir.is_dir():
        return digest.hexdigest()
    for path in sorted(p for p in raw_dir.iterdir() if p.is_file() and is_official_raw_filename(p.name)):
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(_canonical_json_bytes(path))
        digest.update(b"\n")
    return digest.hexdigest()


def _copy_official_files(source: Path, dest: Path, *, allow: Callable[[str], bool]) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    if not source.is_dir() or source.resolve() == dest.resolve():
        return
    for path in source.iterdir():
        if path.is_file() and allow(path.name):
            shutil.copy2(path, dest / path.name)


def _remove_non_official(directory: Path, *, allow: Callable[[str], bool]) -> None:
    if not directory.is_dir():
        return
    for path in directory.iterdir():
        if path.is_file() and path.name != CONTENT_HASH_FILENAME and not allow(path.name):
            path.unlink()


def pin_season_archive(
    season: str,
    raw_dir: Path,
    processed_dir: Path,
    *,
    archive_root: Path | None = None,
) -> LiveSeasonPin:
    """Copy Official FPL raw + core processed into data/archive/<season>/.

    Overwrites the Live Season Pin on each refresh. Does not git commit.
    Completed Season Archives (season != LIVE_SEASON) stay frozen.
    """
    if season != LIVE_SEASON:
        raise ValueError(
            f"Live Season Pin only mutates {LIVE_SEASON}; {season} Season Archive is frozen"
        )
    dest_raw = archive_raw_dir(season, archive_root=archive_root)
    dest_processed = archive_processed_dir(season, archive_root=archive_root)
    season_dir = dest_raw.parent
    hash_path = season_dir / CONTENT_HASH_FILENAME
    previous = hash_path.read_text(encoding="utf-8").strip() if hash_path.exists() else ""

    dest_raw.mkdir(parents=True, exist_ok=True)
    dest_processed.mkdir(parents=True, exist_ok=True)
    _copy_official_files(raw_dir, dest_raw, allow=is_official_raw_filename)
    _copy_official_files(processed_dir, dest_processed, allow=is_official_processed_filename)
    _remove_non_official(dest_raw, allow=is_official_raw_filename)
    _remove_non_official(dest_processed, allow=is_official_processed_filename)

    content_hash = official_content_hash(dest_raw)
    hash_path.write_text(content_hash + "\n", encoding="utf-8")
    return LiveSeasonPin(
        processed_dir=dest_processed,
        content_hash=content_hash,
        changed=content_hash != previous,
    )
