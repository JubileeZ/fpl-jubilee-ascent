import json
import logging
from pathlib import Path
from typing import Any, Optional
import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

# Walk up to project root
PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_CACHE_DIR = PROJECT_ROOT / "data" / "raw"

BASE_URL = "https://fantasy.premierleague.com/api"


def save_raw_cache(filename: str, data: Any) -> None:
    """Helper to save raw API responses to the gitignored raw data cache."""
    try:
        RAW_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path = RAW_CACHE_DIR / filename
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Saved raw cache to {path}")
    except Exception as e:
        logger.warning(f"Failed to write to raw cache {filename}: {e}")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.RequestError)),
    reraise=True,
)
async def _make_get_request(
    client: httpx.AsyncClient,
    url: str,
    headers: Optional[dict[str, str]] = None,
    params: Optional[dict[str, Any]] = None,
) -> Any:
    """Make an HTTP GET request with retries and raise for status."""
    response = await client.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()


async def fetch_bootstrap_static(
    client: httpx.AsyncClient, write_cache: bool = True
) -> dict[str, Any]:
    """Fetch the bootstrap-static endpoint (general clubs, players, gameweeks metadata)."""
    url = f"{BASE_URL}/bootstrap-static/"
    data = await _make_get_request(client, url)
    if write_cache:
        save_raw_cache("bootstrap_static.json", data)
    return data


async def fetch_element_gameweek_live(
    client: httpx.AsyncClient, gw_id: int, write_cache: bool = True
) -> dict[str, Any]:
    """Fetch live gameweek stats for all players."""
    url = f"{BASE_URL}/event/{gw_id}/live/"
    data = await _make_get_request(client, url)
    if write_cache:
        save_raw_cache(f"event_{gw_id}_live.json", data)
    return data


async def fetch_gameweek_fixtures(
    client: httpx.AsyncClient, gw_id: Optional[int] = None, write_cache: bool = True
) -> list[dict[str, Any]]:
    """Fetch fixtures, optionally filtered by gameweek ID."""
    url = f"{BASE_URL}/fixtures/"
    params = {"event": gw_id} if gw_id is not None else None
    data = await _make_get_request(client, url, params=params)
    if write_cache:
        filename = f"fixtures_gw_{gw_id}.json" if gw_id is not None else "fixtures_all.json"
        save_raw_cache(filename, data)
    return data


async def fetch_element_summary(
    client: httpx.AsyncClient, player_id: int, write_cache: bool = True
) -> dict[str, Any]:
    """Fetch historical and fixture summary for a specific player."""
    url = f"{BASE_URL}/element-summary/{player_id}/"
    data = await _make_get_request(client, url)
    if write_cache:
        save_raw_cache(f"element_summary_{player_id}.json", data)
    return data


async def fetch_user_details(
    client: httpx.AsyncClient, token: str, write_cache: bool = True
) -> dict[str, Any]:
    """Fetch logged-in user profile details (entry ID, personal details)."""
    url = f"{BASE_URL}/me/"
    headers = {"x-api-authorization": f"Bearer {token}"}
    data = await _make_get_request(client, url, headers=headers)
    if write_cache:
        save_raw_cache("me.json", data)
    return data


async def fetch_user_team(
    client: httpx.AsyncClient, entry_id: int, token: str, write_cache: bool = True
) -> dict[str, Any]:
    """Fetch current user's team squad, transfer status, chips (requires authentication)."""
    url = f"{BASE_URL}/my-team/{entry_id}/"
    headers = {"x-api-authorization": f"Bearer {token}"}
    data = await _make_get_request(client, url, headers=headers)
    if write_cache:
        save_raw_cache(f"my_team_{entry_id}.json", data)
    return data


async def fetch_entry_summary(
    client: httpx.AsyncClient, entry_id: int, token: Optional[str] = None, write_cache: bool = True
) -> dict[str, Any]:
    """Fetch general manager details, standings, and budget history."""
    url = f"{BASE_URL}/entry/{entry_id}/"
    headers = {"x-api-authorization": f"Bearer {token}"} if token else None
    data = await _make_get_request(client, url, headers=headers)
    if write_cache:
        save_raw_cache(f"entry_{entry_id}.json", data)
    return data


async def fetch_entry_history(
    client: httpx.AsyncClient, entry_id: int, token: Optional[str] = None, write_cache: bool = True
) -> dict[str, Any]:
    """Fetch past seasons, gameweek performance history, and active chips."""
    url = f"{BASE_URL}/entry/{entry_id}/history/"
    headers = {"x-api-authorization": f"Bearer {token}"} if token else None
    data = await _make_get_request(client, url, headers=headers)
    if write_cache:
        save_raw_cache(f"entry_{entry_id}_history.json", data)
    return data


async def fetch_entry_transfers(
    client: httpx.AsyncClient, entry_id: int, token: Optional[str] = None, write_cache: bool = True
) -> list[dict[str, Any]]:
    """Fetch transaction history of all player transfers made."""
    url = f"{BASE_URL}/entry/{entry_id}/transfers/"
    headers = {"x-api-authorization": f"Bearer {token}"} if token else None
    data = await _make_get_request(client, url, headers=headers)
    if write_cache:
        save_raw_cache(f"entry_{entry_id}_transfers.json", data)
    return data


async def fetch_gameweek_picks(
    client: httpx.AsyncClient, entry_id: int, gw_id: int, token: Optional[str] = None, write_cache: bool = True
) -> dict[str, Any]:
    """Fetch manager's player selections/picks for a specific gameweek."""
    url = f"{BASE_URL}/entry/{entry_id}/event/{gw_id}/picks/"
    headers = {"x-api-authorization": f"Bearer {token}"} if token else None
    data = await _make_get_request(client, url, headers=headers)
    if write_cache:
        save_raw_cache(f"entry_{entry_id}_picks_gw_{gw_id}.json", data)
    return data
