"""Two-tier cached service for fetching public FPL manager entries and league standings."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

import httpx
import streamlit as st

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 900  # 15 minutes
BASE_FPL_API_URL = "https://fantasy.premierleague.com/api"


def _default_cache_dir() -> Path:
    import os
    from dashboard.planner_service import PROJECT_ROOT

    storage_base = Path(os.environ.get("FPL_PLANNER_STORAGE", PROJECT_ROOT / "data" / "planner"))
    cache_dir = storage_base / "fpl_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir



def _read_disk_cache(cache_file: Path, max_age_seconds: int = CACHE_TTL_SECONDS) -> tuple[dict[str, Any] | None, bool]:
    """Read cached JSON file from disk. Returns (data, is_stale)."""
    if not cache_file.exists():
        return None, True
    try:
        stat = cache_file.stat()
        age = time.time() - stat.st_mtime
        data = json.loads(cache_file.read_text(encoding="utf-8"))
        is_stale = age > max_age_seconds
        return data, is_stale
    except Exception as exc:
        logger.warning(f"Error reading disk cache {cache_file}: {exc}")
        return None, True


def _write_disk_cache(cache_file: Path, data: dict[str, Any]) -> None:
    try:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception as exc:
        logger.warning(f"Error writing disk cache {cache_file}: {exc}")


def _http_get_json(url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
    }
    with httpx.Client(timeout=12.0) as client:
        resp = client.get(url, headers=headers, params=params)
        resp.raise_for_status()
        return resp.json()


def fetch_with_two_tier_cache(
    endpoint_slug: str,
    url: str,
    params: dict[str, Any] | None = None,
    storage_dir: Path | None = None,
    force_refresh: bool = False,
) -> dict[str, Any]:
    """Fetch JSON from FPL API with disk + memory caching and graceful fallback on 429/5xx."""
    cache_dir = storage_dir or _default_cache_dir()
    cache_file = cache_dir / f"{endpoint_slug}.json"

    if not force_refresh:
        cached_data, is_stale = _read_disk_cache(cache_file)
        if cached_data is not None and not is_stale:
            return cached_data

    # Attempt network fetch
    try:
        fresh_data = _http_get_json(url, params=params)
        _write_disk_cache(cache_file, fresh_data)
        return fresh_data
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code
        logger.warning(f"HTTP error {status_code} fetching {url}: {exc}")
        cached_data, _ = _read_disk_cache(cache_file, max_age_seconds=86400 * 7)
        if cached_data is not None:
            cached_data["_cached_fallback"] = True
            cached_data["_stale_warning"] = f"Using cached snapshot (FPL API returned HTTP {status_code})."
            return cached_data
        if status_code == 429:
            raise RuntimeError("FPL API rate limit encountered. Please wait a minute and try again.") from exc
        if status_code == 404:
            raise ValueError("Entry or league not found in Official FPL.") from exc
        raise RuntimeError(f"FPL API error (HTTP {status_code}). Please try again later.") from exc
    except (httpx.RequestError, OSError) as exc:
        logger.warning(f"Network error fetching {url}: {exc}")
        cached_data, _ = _read_disk_cache(cache_file, max_age_seconds=86400 * 7)
        if cached_data is not None:
            cached_data["_cached_fallback"] = True
            cached_data["_stale_warning"] = "Using offline cached snapshot (network request failed)."
            return cached_data
        raise RuntimeError(f"Unable to reach FPL API: {exc}") from exc


@st.cache_data(ttl=CACHE_TTL_SECONDS, max_entries=256)
def load_entry_summary(entry_id: int, force_refresh: bool = False) -> dict[str, Any]:
    """Load manager profile and joined leagues from /entry/{entry_id}/."""
    url = f"{BASE_FPL_API_URL}/entry/{entry_id}/"
    return fetch_with_two_tier_cache(f"entry_{entry_id}", url, force_refresh=force_refresh)


@st.cache_data(ttl=CACHE_TTL_SECONDS, max_entries=256)
def load_entry_history(entry_id: int, force_refresh: bool = False) -> dict[str, Any]:
    """Load per-gameweek rank, points, and chip history from /entry/{entry_id}/history/."""
    url = f"{BASE_FPL_API_URL}/entry/{entry_id}/history/"
    return fetch_with_two_tier_cache(f"entry_{entry_id}_history", url, force_refresh=force_refresh)


@st.cache_data(ttl=CACHE_TTL_SECONDS, max_entries=128)
def load_classic_league_standings(league_id: int, page_standings: int = 1, force_refresh: bool = False) -> dict[str, Any]:
    """Load standings for a classic mini-league (page 1 by default)."""
    url = f"{BASE_FPL_API_URL}/leagues-classic/{league_id}/standings/"
    return fetch_with_two_tier_cache(
        f"league_{league_id}_standings_p{page_standings}",
        url,
        params={"page_standings": page_standings},
        force_refresh=force_refresh,
    )


def extract_joined_classic_leagues(summary: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract custom classic mini-leagues (league_type == 'x') sorted by rank."""
    leagues = (summary.get("leagues") or {}).get("classic") or []
    # Filter to custom mini-leagues (type 'x'), excluding broadcast / massive system leagues ('s')
    custom_leagues = [
        {
            "id": int(lg["id"]),
            "name": str(lg["name"]),
            "entry_rank": int(lg.get("entry_rank") or 0),
            "entry_last_rank": int(lg.get("entry_last_rank") or 0),
        }
        for lg in leagues
        if lg.get("league_type") == "x"
    ]
    custom_leagues.sort(key=lambda item: (item["entry_rank"] <= 0, item["entry_rank"], item["name"]))
    return custom_leagues


def extract_top_standings_peers(standings: dict[str, Any], exclude_entry_id: int | None = None) -> list[dict[str, Any]]:
    """Extract top 50 peers from standings results for search & selection."""
    results = (standings.get("standings") or {}).get("results") or []
    peers: list[dict[str, Any]] = []
    for r in results:
        eid = int(r.get("entry") or 0)
        if eid <= 0 or (exclude_entry_id is not None and eid == exclude_entry_id):
            continue
        peers.append(
            {
                "entry_id": eid,
                "player_name": str(r.get("player_name") or ""),
                "entry_name": str(r.get("entry_name") or ""),
                "rank": int(r.get("rank") or 0),
                "total": int(r.get("total") or 0),
                "event_total": int(r.get("event_total") or 0),
            }
        )
    return peers


def load_global_benchmarks(
    dataset_meta: dict[str, Any] | None = None,
    paths: Any | None = None,
) -> dict[int, dict[str, Any]]:
    """Extract or load global gameweek averages and chip usage from meta, processed parquet, or raw bootstrap."""
    if dataset_meta and "global_gameweeks" in dataset_meta and dataset_meta["global_gameweeks"]:
        raw_gw_dict = dataset_meta["global_gameweeks"]
        return {int(k): v for k, v in raw_gw_dict.items()}

    if paths is not None and getattr(paths, "dataset", None) is not None and paths.dataset.exists():
        try:
            ds_json = json.loads(paths.dataset.read_text(encoding="utf-8"))
            gw_meta = (ds_json.get("meta") or {}).get("global_gameweeks")
            if gw_meta:
                return {int(k): v for k, v in gw_meta.items()}
        except Exception as exc:
            logger.warning(f"Error reading dataset meta for global benchmarks: {exc}")

    from dashboard.planner_service import PROJECT_ROOT

    processed_dir = getattr(paths, "processed", None) or (PROJECT_ROOT / "data" / "processed")
    gw_parquet = Path(processed_dir) / "gameweeks.parquet"
    if gw_parquet.exists():
        try:
            import pandas as pd

            df = pd.read_parquet(gw_parquet)
            if "average_entry_score" in df.columns:
                out: dict[int, dict[str, Any]] = {}
                for _, row in df.iterrows():
                    gid = int(row["id"])
                    c_raw = row.get("chip_plays")
                    if isinstance(c_raw, str):
                        try:
                            chips = json.loads(c_raw)
                        except Exception:
                            chips = []
                    elif isinstance(c_raw, list):
                        chips = c_raw
                    else:
                        chips = []
                    out[gid] = {
                        "id": gid,
                        "average_entry_score": int(row["average_entry_score"]) if pd.notna(row.get("average_entry_score")) else None,
                        "highest_score": int(row["highest_score"]) if pd.notna(row.get("highest_score")) else None,
                        "ranked_count": int(row["ranked_count"]) if pd.notna(row.get("ranked_count")) else None,
                        "chip_plays": chips,
                    }
                if out:
                    return out
        except Exception as exc:
            logger.warning(f"Error loading gameweeks.parquet for benchmarks: {exc}")

    # Fallback to bootstrap_static.json
    for bs_candidate in (
        PROJECT_ROOT / "data" / "raw" / "bootstrap_static.json",
        PROJECT_ROOT / "data" / "archive" / "2026-27" / "raw" / "bootstrap_static.json",
    ):
        if bs_candidate.exists():
            try:
                bs_data = json.loads(bs_candidate.read_text(encoding="utf-8"))
                events = bs_data.get("events") or []
                out_bs: dict[int, dict[str, Any]] = {}
                for ev in events:
                    gid = int(ev.get("id", 0))
                    if gid <= 0:
                        continue
                    out_bs[gid] = {
                        "id": gid,
                        "average_entry_score": ev.get("average_entry_score"),
                        "highest_score": ev.get("highest_score"),
                        "ranked_count": ev.get("ranked_count"),
                        "chip_plays": ev.get("chip_plays") or [],
                    }
                if out_bs:
                    return out_bs
            except Exception as exc:
                logger.warning(f"Error reading {bs_candidate}: {exc}")

    return {}
