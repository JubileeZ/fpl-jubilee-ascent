import argparse
import asyncio
import importlib.util
import logging
import os
import sys
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
from features.expected_role_prior import (
    DEFAULT_EXPECTED_ROLE_TABLE,
    LIVE_SEASON,
    ensure_expected_role_rebuild_choice,
    table_season_status,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh FPL API data into processed Parquet tables.")
    parser.add_argument(
        "--season",
        default=os.getenv("FPL_SEASON", LIVE_SEASON),
        help="FPL season identity for Expected Role Table (default: FPL_SEASON or 2026-27)",
    )
    parser.add_argument(
        "--rebuild-roles",
        action="store_true",
        help="Run Expected Role Rebuild after ingest when the table is missing or other-season",
    )
    parser.add_argument(
        "--keep-roles",
        action="store_true",
        help="Defer Expected Role Rebuild; API ingest proceeds, projections refuse until this-season table exists",
    )
    return parser.parse_args(argv)


def _run_expected_role_rebuild(season: str) -> None:
    script = (
        PROJECT_ROOT
        / "docs/research/gw1-6-preseason-pipeline/01-expected-role-gw1-5/refresh_expected_role.py"
    )
    spec = importlib.util.spec_from_file_location("refresh_expected_role", script)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load Expected Role Rebuild from {script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.refresh_expected_roles(season=season)


async def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    ensure_expected_role_rebuild_choice(args.season, args.rebuild_roles, args.keep_roles)

    async with httpx.AsyncClient(timeout=30.0) as client:
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
        logger.info(f"Fetching element summaries for all {len(player_ids)} players (concurrency limit = 5)...")
        
        semaphore_elements = asyncio.Semaphore(5)
        
        async def fetch_summary(player_id):
            async with semaphore_elements:
                try:
                    await fetch_element_summary(client, player_id, write_cache=True)
                except Exception as e:
                    logger.error(f"Failed to fetch summary for player {player_id}: {e}")
                    
        # Gather in chunks to avoid overwhelming endpoints
        chunk_size = 50
        for i in range(0, len(player_ids), chunk_size):
            chunk = player_ids[i:i + chunk_size]
            await asyncio.gather(*(fetch_summary(pid) for pid in chunk))
            logger.info(f"Progress: fetched {i + len(chunk)}/{len(player_ids)} player summaries.")
            await asyncio.sleep(0.5)
        
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
        process_directory(raw_dir, processed_dir)
        logger.info("Data processing complete! Parquet tables saved to data/processed/")
        try:
            price_history_path = append_price_snapshot(processed_dir)
            logger.info(f"Price history appended to {price_history_path}")
        except (FileNotFoundError, ValueError) as e:
            logger.warning(f"Price history snapshot skipped: {e}")

        if args.rebuild_roles:
            logger.info("Running Expected Role Rebuild...")
            _run_expected_role_rebuild(args.season)
        elif args.keep_roles and table_season_status(DEFAULT_EXPECTED_ROLE_TABLE, args.season) != "ok":
            logger.warning(
                "Expected Role Rebuild deferred (--keep-roles). "
                "API data refreshed; Feature Contract will refuse until a this-season table exists."
            )

if __name__ == "__main__":
    asyncio.run(main())
