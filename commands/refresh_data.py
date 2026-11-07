import argparse
import asyncio
import logging
import os
import sys
import time
import json
from typing import Any
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
    fetch_entry_summary,
    fetch_entry_history,
    fetch_gameweek_picks,
    fetch_entry_transfers,
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
        "--entry-id",
        type=int,
        default=None,
        dest="entry_id",
        help="FPL Manager/Entry ID to fetch squad picks using public endpoints when unauthenticated",
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


def _reconstruct_picks_with_prices(
    picks: list[dict[str, Any]],
    transfers_history: list[dict[str, Any]],
    elements: dict[int, dict[str, Any]],
) -> list[dict[str, Any]]:
    sorted_transfers = sorted(
        transfers_history if isinstance(transfers_history, list) else [],
        key=lambda x: str(x.get("time", "")),
    )
    buy_prices: dict[int, int] = {}
    for p in picks:
        pid = int(p["element"])
        el = elements.get(pid, {})
        buy_prices[pid] = int(el.get("now_cost", 50)) - int(el.get("cost_change_start", 0))
    for t in sorted_transfers:
        buy_prices[int(t["element_in"])] = int(t["element_in_cost"])

    picks_list: list[dict[str, Any]] = []
    for p in picks:
        pid = int(p["element"])
        now_cost = int(elements.get(pid, {}).get("now_cost", 50))
        p_cost = int(buy_prices.get(pid, now_cost))
        profit = max(0, now_cost - p_cost)
        sell_price = p_cost + profit // 2 if now_cost >= p_cost else now_cost
        picks_list.append({
            "element": pid,
            "position": int(p["position"]),
            "multiplier": int(p.get("multiplier", 1)),
            "is_captain": bool(p.get("is_captain", False)),
            "is_vice_captain": bool(p.get("is_vice_captain", False)),
            "purchase_price": p_cost,
            "selling_price": sell_price,
        })
    return picks_list


def _reconstruct_chips_inventory(
    raw_chips: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[int, str]]:
    played_set_1: set[str] = set()
    played_set_2: set[str] = set()
    chip_events: dict[int, str] = {}
    for c in raw_chips:
        cname = str(c.get("name", ""))
        ev_id = int(c.get("event") or 1)
        chip_events[ev_id] = cname
        (played_set_1 if ev_id <= 19 else played_set_2).add(cname)

    chips_list: list[dict[str, Any]] = []
    for cname in ("wildcard", "freehit", "bboost", "3xc"):
        chips_list.append({
            "name": cname,
            "status": "played" if cname in played_set_1 else "available",
            "number": 1,
            "start_event": 1,
            "stop_event": 19,
            "chip_set": 1,
        })
        chips_list.append({
            "name": cname,
            "status": "played" if cname in played_set_2 else "available",
            "number": 2,
            "start_event": 20,
            "stop_event": 38,
            "chip_set": 2,
        })
    return chips_list, chip_events


def _reconstruct_free_transfers(
    current_events: list[dict[str, Any]],
    chip_events: dict[int, str],
) -> int:
    ft_acc = 1
    for ev in current_events:
        ev_id = int(ev.get("event") or 0)
        if chip_events.get(ev_id) in ("wildcard", "freehit"):
            ft_acc = max(1, min(5, ft_acc))
            continue
        tr_made = int(ev.get("event_transfers", 0))
        tr_cost = int(ev.get("event_transfers_cost", 0))
        free_used = max(0, tr_made - tr_cost // 4)
        ft_acc = min(5, max(0, ft_acc - free_used) + 1)
    return ft_acc


def reconstruct_public_team_payload(
    picks_data: dict[str, Any],
    history: dict[str, Any],
    transfers_history: list[dict[str, Any]],
    elements: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    """Reconstruct a my_team-compatible payload from public FPL endpoints."""
    picks_list = _reconstruct_picks_with_prices(
        picks_data.get("picks", []), transfers_history, elements
    )
    chips_list, chip_events = _reconstruct_chips_inventory(history.get("chips", []))
    ft_acc = _reconstruct_free_transfers(history.get("current", []), chip_events)

    entry_history_row = picks_data.get("entry_history", {})
    bank = int(entry_history_row.get("bank", 0))
    value = int(entry_history_row.get("value", sum(p["selling_price"] for p in picks_list) + bank))

    return {
        "picks": picks_list,
        "chips": chips_list,
        "transfers": {
            "bank": bank,
            "value": value,
            "limit": ft_acc,
            "made": 0,
            "cost": 0,
        },
    }


async def sync_public_entry_squad(
    client: httpx.AsyncClient,
    entry_id: int,
    bootstrap: dict[str, Any],
    raw_dir: Path,
) -> bool:
    """Fetch user squad and state via official public FPL API endpoints when unauthenticated."""
    try:
        logger.info(f"Fetching public profile for Entry #{entry_id}...")
        entry_summary = await fetch_entry_summary(client, entry_id, write_cache=True)
        player_name = f"{entry_summary.get('player_first_name', '')} {entry_summary.get('player_last_name', '')}".strip()
        team_name = entry_summary.get("name", "")
        logger.info(f"Entry #{entry_id}: {team_name} ({player_name})")

        history = await fetch_entry_history(client, entry_id, write_cache=True)
        events = bootstrap.get("events", [])
        elements = {int(el["id"]): el for el in bootstrap.get("elements", [])}

        now_utc = datetime.now(UTC)
        finished_gws = []
        for e in events:
            eid = e.get("id")
            if not eid:
                continue
            is_finished = bool(e.get("finished"))
            dl_str = e.get("deadline_time")
            dl_passed = False
            if dl_str:
                try:
                    dl_dt = datetime.fromisoformat(str(dl_str).replace("Z", "+00:00"))
                    dl_passed = dl_dt <= now_utc
                except Exception:
                    pass
            if is_finished or dl_passed:
                finished_gws.append(int(eid))

        if not finished_gws:
            finished_gws = [1]
        latest_gw = max(finished_gws)

        logger.info(f"Fetching public picks for Entry #{entry_id} (GW{latest_gw})...")
        picks_data = await fetch_gameweek_picks(client, entry_id, latest_gw, write_cache=True)
        if picks_data.get("active_chip") == "freehit" and latest_gw > 1:
            logger.info(f"GW{latest_gw} used Free Hit; fetching underlying squad from GW{latest_gw - 1}...")
            prev_picks_data = await fetch_gameweek_picks(client, entry_id, latest_gw - 1, write_cache=True)
            if prev_picks_data.get("picks"):
                picks_data = prev_picks_data

        if not picks_data.get("picks"):
            logger.warning(f"No picks returned for Entry #{entry_id} in GW{latest_gw}.")
            return False

        transfers_history = await fetch_entry_transfers(client, entry_id, write_cache=True)
        my_team = reconstruct_public_team_payload(
            picks_data=picks_data,
            history=history,
            transfers_history=transfers_history if isinstance(transfers_history, list) else [],
            elements=elements,
        )

        raw_dir.mkdir(parents=True, exist_ok=True)
        team_file = raw_dir / f"my_team_{entry_id}.json"
        with open(team_file, "w", encoding="utf-8") as f:
            json.dump(my_team, f, indent=2)
        with open(raw_dir / "me.json", "w", encoding="utf-8") as mf:
            json.dump({"player": {"entry": entry_id}}, mf, indent=2)
        logger.info(f"Saved reconstructed User Squad for Entry #{entry_id} -> {team_file}")

        try:
            pref_file = PROJECT_ROOT / "data" / "planner" / "preferences.json"
            pref_file.parent.mkdir(parents=True, exist_ok=True)
            existing_prefs = {}
            if pref_file.exists():
                with open(pref_file, "r", encoding="utf-8") as pf:
                    existing_prefs = json.load(pf)
            existing_prefs["entry_id"] = entry_id
            with open(pref_file, "w", encoding="utf-8") as pf:
                json.dump(existing_prefs, pf, indent=2)
        except Exception:
            pass

        return True
    except Exception as exc:
        logger.warning(f"Failed to fetch public squad for Entry #{entry_id}: {exc}")
        return False


async def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    if args.rebuild_roles or args.keep_roles:
        logger.warning("Expected Role Rebuild is retired; --rebuild-roles / --keep-roles are ignored.")

    raw_dir = PROJECT_ROOT / "data" / "raw"
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
        authenticated = False
        try:
            token = await get_jwt_token()
            logger.info("Authentication found. Fetching manager details...")
            user_details = await fetch_user_details(client, token, write_cache=True)
            entry_id = user_details.get("player", {}).get("entry")
            if entry_id:
                logger.info(f"Manager Entry ID: {entry_id}. Fetching current squad picks...")
                await fetch_user_team(client, entry_id, token, write_cache=True)
                authenticated = True
            else:
                logger.warning("No entry ID found in profile. Skipping squad picks download.")
        except Exception as e:
            logger.warning(
                f"Skipping authenticated endpoints (manager picks/bank/value): {e}\n"
                "To resolve, set FPL_TOKEN or FPL_EMAIL and FPL_PASSWORD in environment."
            )

        if not authenticated:
            if args.entry_id is not None:
                synced = await sync_public_entry_squad(client, int(args.entry_id), bootstrap, raw_dir)
                if not synced:
                    logger.warning(f"Could not sync squad for Entry #{args.entry_id} via public endpoints.")
            else:
                logger.info("No authenticated session or --entry-id provided. Skipping squad download.")
            
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
