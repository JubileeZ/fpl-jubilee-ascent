import argparse
import asyncio
import logging
import os
import sys
import time
import httpx
from datetime import UTC, datetime
from pathlib import Path

# Set up path to include root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from clients.env_loader import load_env, configure_utf8_stdio
load_env()
configure_utf8_stdio()

from clients.fpl_api import (
    fetch_bootstrap_static,
    fetch_gameweek_fixtures,
    fetch_user_details,
    fetch_user_team,
    fetch_element_summary,
)
from clients.fpl_auth import get_jwt_token
from features.processor import process_directory
from commands.capture_availability_snapshot import capture_payload
from commands.price_report import append_price_snapshot
from features.season_archive import pin_season_archive, prune_stale_element_summaries
from features.expected_role_prior import LIVE_SEASON

PROJECT_ROOT = Path(__file__).resolve().parents[1]

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh raw FPL data and update processed tables.")
    parser.add_argument("--season", type=str, default=LIVE_SEASON, help=f"FPL season (default: {LIVE_SEASON})")
    parser.add_argument(
        "--concurrency",
        type=int,
        default=20,
        help="Concurrent player summary requests (default: 20)",
    )
    parser.add_argument(
        "--rebuild-roles",
        action="store_true",
        help="Ignored. Expected Role Rebuild is retired (ADR 0025).",
    )
    parser.add_argument(
        "--keep-roles",
        action="store_true",
        help="Ignored. Expected Role Rebuild is retired (ADR 0025).",
    )
    return parser.parse_args(argv)


async def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    if args.rebuild_roles or args.keep_roles:
        logger.warning("Expected Role Rebuild is retired; --rebuild-roles / --keep-roles are ignored.")

    limits = httpx.Limits(max_keepalive_connections=args.concurrency, max_connections=args.concurrency * 2)
    async with httpx.AsyncClient(timeout=30.0, limits=limits) as client:
        logger.info("Fetching public bootstrap-static data...")
        bootstrap = await fetch_bootstrap_static(client, write_cache=True)
        
        # Determine current gameweek
        events = bootstrap.get("events", [])
        current_gw = next((gw["id"] for gw in events if gw["is_current"]), None)
        logger.info(f"Current Gameweek determined as: {current_gw}")
        
        logger.info("Fetching all fixtures...")
        fixtures = await fetch_gameweek_fixtures(client, write_cache=True)
        
        # Fetch element summaries for all active players
        elements = bootstrap.get("elements", [])
        player_ids = [player["id"] for player in elements]
        logger.info(
            f"Fetching element summaries for all {len(player_ids)} players (concurrency limit = {args.concurrency})..."
        )
        
        semaphore_elements = asyncio.Semaphore(args.concurrency)
        completed = 0
        start_time = time.perf_counter()
        
        async def fetch_summary(player_id: int) -> None:
            nonlocal completed
            async with semaphore_elements:
                try:
                    await fetch_element_summary(client, player_id, write_cache=True)
                except Exception as e:
                    logger.error(f"Failed to fetch summary for player {player_id}: {e}")
                finally:
                    completed += 1
                    if completed % 100 == 0 or completed == len(player_ids):
                        logger.info(f"Progress: fetched {completed}/{len(player_ids)} player summaries.")

        if player_ids:
            await asyncio.gather(*(fetch_summary(pid) for pid in player_ids))
            elapsed = time.perf_counter() - start_time
            rate = len(player_ids) / elapsed if elapsed > 0 else 0.0
            logger.info(
                f"Fetched {len(player_ids)} player summaries in {elapsed:.1f}s ({rate:.1f} req/s)."
            )
        
        # Check authentication to fetch user-specific squad details
        try:
            token = await get_jwt_token()
            logger.info("Authentication found. Fetching manager details...")
            user_details = await fetch_user_details(client, token, write_cache=True)
            entry_id = user_details.get("player", {}).get("entry")
            if entry_id:
                logger.info(f"Manager Entry ID: {entry_id}. Fetching current squad picks...")
                await fetch_user_team(client, entry_id, token, write_cache=True)
            else:
                logger.warning("No entry ID found in profile. Skipping squad picks download.")
        except Exception as e:
            logger.warning(
                f"Skipping authenticated endpoints (manager picks/bank/value): {e}\n"
                "To resolve, set FPL_TOKEN or FPL_EMAIL and FPL_PASSWORD in environment."
            )
            
        logger.info("Data refresh complete! Raw JSON cache saved to data/raw/")

        season = os.getenv("FPL_SEASON")
        if season:
            capture_payload(
                season=season,
                snapshot_root=PROJECT_ROOT / "data" / "availability-snapshots",
                bootstrap=bootstrap,
                fixtures=fixtures,
                captured_at=datetime.now(UTC),
            )
        else:
            logger.info("FPL_SEASON is unset; availability snapshot capture skipped.")
        
        logger.info("Processing raw JSON files into Parquet tables...")
        raw_dir = PROJECT_ROOT / "data" / "raw"
        processed_dir = PROJECT_ROOT / "data" / "processed"
        pruned = prune_stale_element_summaries(raw_dir)
        if pruned:
            logger.info(f"Removed {pruned} prior-season element summaries from {raw_dir}")
        process_directory(raw_dir, processed_dir)
        logger.info("Data processing complete! Parquet tables saved to data/processed/")
        try:
            price_history_path = append_price_snapshot(processed_dir)
            logger.info(f"Price history appended to {price_history_path}")
        except (FileNotFoundError, ValueError) as e:
            logger.warning(f"Price history snapshot skipped: {e}")

        pin = pin_season_archive(args.season, raw_dir, processed_dir)
        if pin.changed:
            logger.info(
                "Live Season Pin Official FPL hash changed (%s). Git commit the pin if you want machine sync. -> %s",
                pin.content_hash,
                pin.processed_dir,
            )
        else:
            logger.info(
                "Live Season Pin Official FPL hash unchanged (%s). Skip git commit. -> %s",
                pin.content_hash,
                pin.processed_dir,
            )

if __name__ == "__main__":
    asyncio.run(main())
