"""Crawl Overall Top-10k picks and write a complete Effective Ownership cache."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable

import httpx

from clients.fpl_api import (
    fetch_classic_league_standings,
    fetch_entry_summary,
    fetch_gameweek_picks,
)
from projections.effective_ownership import (
    aggregate_effective_ownership,
    overall_league_id,
    save_complete_eo_cache,
)
from solver.planning import resolve_default_target_gw

LOGGER = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
RANK_CAP = 10_000
DEFAULT_CONCURRENCY = 20

FetchStandings = Callable[[httpx.AsyncClient, int, int], Awaitable[dict[str, Any]]]
FetchPicks = Callable[[httpx.AsyncClient, int, int], Awaitable[dict[str, Any]]]
FetchEntry = Callable[[httpx.AsyncClient, int], Awaitable[dict[str, Any]]]


def default_eo_cache_path(project_root: Path | None = None) -> Path:
    root = project_root or PROJECT_ROOT
    return root / "data" / "effective_ownership.json"


def resolve_entry_id_from_me(raw_dir: Path) -> int | None:
    me_path = raw_dir / "me.json"
    if not me_path.exists():
        return None
    try:
        payload = json.loads(me_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    entry = (payload.get("player") or {}).get("entry")
    return int(entry) if entry is not None else None


async def collect_top_entry_ids(
    client: httpx.AsyncClient,
    league_id: int,
    *,
    rank_cap: int = RANK_CAP,
    fetch_standings: FetchStandings | None = None,
) -> list[int]:
    fetch = fetch_standings or (
        lambda c, lid, page: fetch_classic_league_standings(c, lid, page=page, write_cache=False)
    )
    entry_ids: list[int] = []
    page = 1
    while len(entry_ids) < rank_cap:
        payload = await fetch(client, league_id, page)
        results = ((payload.get("standings") or {}).get("results")) or []
        if not results:
            break
        for row in results:
            rank = int(row.get("rank") or 0)
            if rank <= 0 or rank > rank_cap:
                continue
            entry_ids.append(int(row["entry"]))
            if len(entry_ids) >= rank_cap:
                break
        has_next = bool((payload.get("standings") or {}).get("has_next"))
        if not has_next:
            break
        page += 1
    return entry_ids


async def fetch_all_picks(
    client: httpx.AsyncClient,
    entry_ids: list[int],
    gameweek_id: int,
    *,
    concurrency: int = DEFAULT_CONCURRENCY,
    fetch_picks: FetchPicks | None = None,
) -> list[list[dict[str, Any]]]:
    fetch = fetch_picks or (
        lambda c, eid, gw: fetch_gameweek_picks(c, eid, gw, write_cache=False)
    )
    sem = asyncio.Semaphore(max(1, concurrency))
    out: list[list[dict[str, Any]] | None] = [None] * len(entry_ids)

    async def one(index: int, entry_id: int) -> None:
        async with sem:
            payload = await fetch(client, entry_id, gameweek_id)
            picks = payload.get("picks") or []
            out[index] = [
                {"element": int(p["element"]), "multiplier": int(p.get("multiplier") or 0)}
                for p in picks
            ]

    await asyncio.gather(*(one(i, eid) for i, eid in enumerate(entry_ids)))
    completed: list[list[dict[str, Any]]] = []
    for row in out:
        if row is None:
            raise RuntimeError("Effective Ownership crawl incomplete: missing picks responses")
        completed.append(row)
    return completed


async def crawl_effective_ownership(
    *,
    processed_dir: Path,
    raw_dir: Path | None = None,
    cache_path: Path | None = None,
    project_root: Path | None = None,
    rank_cap: int = RANK_CAP,
    concurrency: int = DEFAULT_CONCURRENCY,
    client: httpx.AsyncClient | None = None,
    fetch_entry: FetchEntry | None = None,
    fetch_standings: FetchStandings | None = None,
    fetch_picks: FetchPicks | None = None,
) -> Path | None:
    """Complete Top-N EO crawl. Writes cache only on full success. Returns cache path or None."""
    root = project_root or PROJECT_ROOT
    raw = raw_dir or (root / "data" / "raw")
    out = cache_path or default_eo_cache_path(root)
    entry_id = resolve_entry_id_from_me(raw)
    if entry_id is None:
        LOGGER.warning("EO crawl skipped: no me.json entry id")
        return None
    gameweek_id = int(resolve_default_target_gw(processed_dir))
    owns_client = client is None
    http = client or httpx.AsyncClient(timeout=30.0)
    try:
        entry_fetch = fetch_entry or (lambda c, eid: fetch_entry_summary(c, eid, write_cache=False))
        entry_summary = await entry_fetch(http, entry_id)
        league_id = overall_league_id(entry_summary)
        if league_id is None:
            LOGGER.warning("EO crawl skipped: Overall league id not found on entry")
            return None
        entry_ids = await collect_top_entry_ids(
            http, league_id, rank_cap=rank_cap, fetch_standings=fetch_standings
        )
        if not entry_ids:
            LOGGER.warning("EO crawl skipped: empty Overall standings")
            return None
        pick_lists = await fetch_all_picks(
            http,
            entry_ids,
            gameweek_id,
            concurrency=concurrency,
            fetch_picks=fetch_picks,
        )
        if len(pick_lists) != len(entry_ids):
            raise RuntimeError("Effective Ownership crawl incomplete: pick count mismatch")
        result = aggregate_effective_ownership(pick_lists, rank_cap=rank_cap)
        save_complete_eo_cache(
            out,
            n=result.n,
            gameweek_id=gameweek_id,
            league_id=league_id,
            by_player=result.by_player,
            label=result.label,
            captured_at=datetime.now(timezone.utc).isoformat(),
        )
        LOGGER.info("EO cache written %s (%s, N=%s)", out, result.label, result.n)
        return out
    finally:
        if owns_client:
            await http.aclose()


def main() -> None:
    from clients.env_loader import configure_utf8_stdio, load_env
    from features.builder import resolve_operational_processed_dir

    load_env()
    configure_utf8_stdio()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    processed = resolve_operational_processed_dir(PROJECT_ROOT)
    path = asyncio.run(crawl_effective_ownership(processed_dir=processed, project_root=PROJECT_ROOT))
    if path is None:
        raise SystemExit("Effective Ownership crawl did not write a complete cache.")
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
