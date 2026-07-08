import asyncio
import logging
import sys
import httpx
import json
from pathlib import Path

# Set up path to include root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from clients.env_loader import load_env, configure_utf8_stdio
load_env()
configure_utf8_stdio()

from clients.fpl_api import (
    fetch_bootstrap_static,
    fetch_gameweek_fixtures,
    fetch_element_gameweek_live,
    fetch_element_summary,
)
from features.processor import process_directory

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Target archive folder
PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_RAW_DIR = PROJECT_ROOT / "data" / "archive" / "2025-26" / "raw"

# Custom cache writer that writes to archive directory
def save_archive_raw(filename: str, data: any) -> None:
    try:
        ARCHIVE_RAW_DIR.mkdir(parents=True, exist_ok=True)
        path = ARCHIVE_RAW_DIR / filename
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.warning(f"Failed to write snapshot {filename}: {e}")

async def main():
    async with httpx.AsyncClient(timeout=30.0) as client:
        logger.info("Starting historical 2025/26 season raw snapshot...")
        
        # 1. Fetch bootstrap static
        logger.info("Fetching bootstrap-static...")
        bootstrap = await fetch_bootstrap_static(client, write_cache=False)
        save_archive_raw("bootstrap_static.json", bootstrap)
        
        # 2. Fetch all fixtures
        logger.info("Fetching fixtures...")
        fixtures = await fetch_gameweek_fixtures(client, write_cache=False)
        save_archive_raw("fixtures_all.json", fixtures)
        
        # 3. Fetch live data for all 38 gameweeks
        logger.info("Fetching live data for all 38 gameweeks...")
        semaphore_live = asyncio.Semaphore(5)
        
        async def fetch_live(gw_id):
            async with semaphore_live:
                try:
                    data = await fetch_element_gameweek_live(client, gw_id, write_cache=False)
                    save_archive_raw(f"event_{gw_id}_live.json", data)
                except Exception as e:
                    logger.error(f"Failed to fetch live data for GW {gw_id}: {e}")
                    
        await asyncio.gather(*(fetch_live(gw_id) for gw_id in range(1, 39)))
        
        # 4. Fetch element-summary for all players
        elements = bootstrap.get("elements", [])
        player_ids = [player["id"] for player in elements]
        logger.info(f"Fetching element summaries for all {len(player_ids)} players (concurrency limit = 5)...")
        
        semaphore_elements = asyncio.Semaphore(5)
        
        async def fetch_summary(player_id):
            async with semaphore_elements:
                try:
                    data = await fetch_element_summary(client, player_id, write_cache=False)
                    save_archive_raw(f"element_summary_{player_id}.json", data)
                except Exception as e:
                    logger.error(f"Failed to fetch summary for player {player_id}: {e}")
                    
        # Gather in chunks to avoid overwhelming endpoints
        chunk_size = 50
        for i in range(0, len(player_ids), chunk_size):
            chunk = player_ids[i:i + chunk_size]
            await asyncio.gather(*(fetch_summary(pid) for pid in chunk))
            logger.info(f"Progress: fetched {i + len(chunk)}/{len(player_ids)} player summaries.")
            await asyncio.sleep(0.5)  # brief pause between chunks to respect rate-limits
            
        logger.info("2025/26 season raw snapshot successfully saved to data/archive/2025-26/raw/")
        
        logger.info("Processing archived raw JSON files into Parquet tables...")
        processed_dir = PROJECT_ROOT / "data" / "archive" / "2025-26" / "processed"
        process_directory(ARCHIVE_RAW_DIR, processed_dir)
        logger.info("Archived data processing complete! Parquet tables saved to data/archive/2025-26/processed/")

if __name__ == "__main__":
    asyncio.run(main())
