"""Capture a changed-only public FPL availability snapshot."""

import argparse
import asyncio
import logging
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pandas as pd

from clients.env_loader import configure_utf8_stdio, load_env
from clients.fpl_api import fetch_bootstrap_static, fetch_gameweek_fixtures
from features.availability_snapshots import write_availability_snapshot

load_env()
configure_utf8_stdio()

PROJECT_ROOT = Path(__file__).resolve().parents[1]
logger = logging.getLogger(__name__)


def _players_frame(bootstrap: dict[str, object]) -> pd.DataFrame:
    players = pd.DataFrame(bootstrap.get("elements", []))
    return players.rename(columns={"team": "club_id", "element_type": "position_id"})


def _clubs_frame(bootstrap: dict[str, object]) -> pd.DataFrame:
    return pd.DataFrame(bootstrap.get("teams", []))


def _fixtures_frame(fixtures: list[dict[str, object]]) -> pd.DataFrame:
    return pd.DataFrame(fixtures).rename(
        columns={"event": "gameweek_id", "team_h": "home_club_id", "team_a": "away_club_id"}
    )


def _target_event(bootstrap: dict[str, object], now: datetime) -> dict[str, object] | None:
    events = bootstrap.get("events", [])
    future_events = [
        event
        for event in events
        if isinstance(event, dict)
        and event.get("deadline_time")
        and datetime.fromisoformat(str(event["deadline_time"]).replace("Z", "+00:00")) > now
    ]
    if not future_events:
        return None
    return next(
        (event for event in future_events if event.get("is_next")),
        min(
            future_events,
            key=lambda event: datetime.fromisoformat(
                str(event["deadline_time"]).replace("Z", "+00:00")
            ),
        ),
    )


def capture_payload(
    season: str,
    snapshot_root: Path,
    bootstrap: dict[str, object],
    fixtures: list[dict[str, object]],
    captured_at: datetime,
) -> Path | None:
    target = _target_event(bootstrap, captured_at)
    if target is None:
        logger.info("No future Gameweek deadline found; snapshot skipped.")
        return None
    deadline = datetime.fromisoformat(str(target["deadline_time"]).replace("Z", "+00:00"))
    package = write_availability_snapshot(
        snapshot_root=snapshot_root,
        season=season,
        target_gw=int(target["id"]),
        deadline=deadline,
        captured_at=captured_at,
        players=_players_frame(bootstrap),
        clubs=_clubs_frame(bootstrap),
        fixtures=_fixtures_frame(fixtures),
        source_endpoint_versions={
            "bootstrap-static": "public",
            "fixtures": "public",
        },
    )
    if package is None:
        logger.info("Snapshot skipped: outside capture window or source unchanged.")
    else:
        logger.info("Availability snapshot written to %s", package)
    return package


async def capture(
    season: str,
    snapshot_root: Path,
    captured_at: datetime | None = None,
) -> Path | None:
    async with httpx.AsyncClient(timeout=30.0) as client:
        bootstrap = await fetch_bootstrap_static(client, write_cache=False)
        fixtures = await fetch_gameweek_fixtures(client, write_cache=False)
    captured = captured_at or datetime.now(UTC)
    return capture_payload(season, snapshot_root, bootstrap, fixtures, captured)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", required=True, help="Season directory name, for example 2026-27")
    parser.add_argument(
        "--snapshot-root",
        type=Path,
        default=PROJECT_ROOT / "data" / "availability-snapshots",
    )
    args = parser.parse_args()
    asyncio.run(capture(args.season, args.snapshot_root))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    main()
