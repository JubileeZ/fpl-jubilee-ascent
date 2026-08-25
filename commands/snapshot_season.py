"""Snapshot a season archive from live FPL (current historical target) or local raw JSON."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from clients.env_loader import configure_utf8_stdio, load_env

load_env()
configure_utf8_stdio()

from clients.fpl_api import (
    fetch_bootstrap_static,
    fetch_element_gameweek_live,
    fetch_element_summary,
    fetch_gameweek_fixtures,
)
from features.processor import process_directory

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LIVE_SNAPSHOT_SEASON = "2025-26"


def archive_raw_dir(season: str, *, archive_root: Path | None = None) -> Path:
    root = archive_root or (PROJECT_ROOT / "data" / "archive")
    return root / season / "raw"


def archive_processed_dir(season: str, *, archive_root: Path | None = None) -> Path:
    root = archive_root or (PROJECT_ROOT / "data" / "archive")
    return root / season / "processed"


def process_season_archive(
    season: str,
    raw_dir: Path,
    *,
    archive_root: Path | None = None,
) -> Path:
    processed = archive_processed_dir(season, archive_root=archive_root)
    process_directory(raw_dir, processed)
    return processed


def save_archive_raw(raw_dir: Path, filename: str, data: object) -> None:
    raw_dir.mkdir(parents=True, exist_ok=True)
    with (raw_dir / filename).open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)


async def fetch_live_season_raw(season: str, raw_dir: Path) -> None:
    if season != LIVE_SNAPSHOT_SEASON:
        raise ValueError(
            f"Live FPL API cannot snapshot {season}; pass --from-raw-dir with that season's raw JSON."
        )
    async with httpx.AsyncClient(timeout=30.0) as client:
        logger.info("Starting historical %s season raw snapshot...", season)
        bootstrap = await fetch_bootstrap_static(client, write_cache=False)
        save_archive_raw(raw_dir, "bootstrap_static.json", bootstrap)
        fixtures = await fetch_gameweek_fixtures(client, write_cache=False)
        save_archive_raw(raw_dir, "fixtures_all.json", fixtures)
        semaphore_live = asyncio.Semaphore(5)

        async def fetch_live(gw_id: int) -> None:
            async with semaphore_live:
                try:
                    data = await fetch_element_gameweek_live(client, gw_id, write_cache=False)
                    save_archive_raw(raw_dir, f"event_{gw_id}_live.json", data)
                except Exception as exc:
                    logger.error("Failed to fetch live data for GW %s: %s", gw_id, exc)

        await asyncio.gather(*(fetch_live(gw_id) for gw_id in range(1, 39)))
        elements = bootstrap.get("elements", [])
        player_ids = [player["id"] for player in elements]
        semaphore_elements = asyncio.Semaphore(5)

        async def fetch_summary(player_id: int) -> None:
            async with semaphore_elements:
                try:
                    data = await fetch_element_summary(client, player_id, write_cache=False)
                    save_archive_raw(raw_dir, f"element_summary_{player_id}.json", data)
                except Exception as exc:
                    logger.error("Failed to fetch summary for player %s: %s", player_id, exc)

        chunk_size = 50
        for i in range(0, len(player_ids), chunk_size):
            chunk = player_ids[i : i + chunk_size]
            await asyncio.gather(*(fetch_summary(pid) for pid in chunk))
            logger.info("Progress: fetched %s/%s player summaries.", i + len(chunk), len(player_ids))
            await asyncio.sleep(0.5)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write a season archive under data/archive/<season>/")
    parser.add_argument("--season", default=LIVE_SNAPSHOT_SEASON, help="Season folder name, e.g. 2024-25")
    parser.add_argument(
        "--from-raw-dir",
        type=Path,
        help="Process local FPL raw JSON into data/archive/<season>/processed (no HTTP)",
    )
    parser.add_argument(
        "--archive-root",
        type=Path,
        default=None,
        help="Override data/archive root (tests)",
    )
    args = parser.parse_args(argv)
    if args.from_raw_dir is not None:
        if not args.from_raw_dir.exists():
            raise FileNotFoundError(f"Raw directory not found: {args.from_raw_dir}")
        processed = process_season_archive(args.season, args.from_raw_dir, archive_root=args.archive_root)
        logger.info("Processed %s -> %s", args.from_raw_dir, processed)
        return 0
    if args.season != LIVE_SNAPSHOT_SEASON:
        raise ValueError(
            f"Live FPL API cannot snapshot {args.season}; pass --from-raw-dir with that season's raw JSON."
        )
    raw_dir = archive_raw_dir(args.season, archive_root=args.archive_root)
    asyncio.run(fetch_live_season_raw(args.season, raw_dir))
    processed = process_season_archive(args.season, raw_dir, archive_root=args.archive_root)
    logger.info("Archived data processing complete: %s", processed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
