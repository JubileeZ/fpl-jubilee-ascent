"""EO crawl with mocked HTTP — no live Official requests."""

from __future__ import annotations

from pathlib import Path

import httpx
import pandas as pd
import pytest

from commands.effective_ownership_crawl import crawl_effective_ownership
from projections.effective_ownership import load_complete_eo_cache


@pytest.mark.asyncio
async def test_crawl_writes_complete_cache_only(tmp_path: Path) -> None:
    processed = tmp_path / "processed"
    processed.mkdir()
    pd.DataFrame([{"id": 5, "is_next": True, "finished": False}]).to_parquet(
        processed / "gameweeks.parquet", index=False
    )
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "me.json").write_text('{"player": {"entry": 99}}', encoding="utf-8")
    cache = tmp_path / "effective_ownership.json"

    async def fetch_entry(client: httpx.AsyncClient, entry_id: int) -> dict:
        assert entry_id == 99
        return {"leagues": {"classic": [{"id": 314, "short_name": "overall"}]}}

    async def fetch_standings(client: httpx.AsyncClient, league_id: int, page: int) -> dict:
        assert league_id == 314
        if page == 1:
            return {
                "standings": {
                    "has_next": False,
                    "results": [
                        {"entry": 1, "rank": 1},
                        {"entry": 2, "rank": 2},
                    ],
                }
            }
        return {"standings": {"has_next": False, "results": []}}

    async def fetch_picks(client: httpx.AsyncClient, entry_id: int, gw_id: int) -> dict:
        assert gw_id == 5
        if entry_id == 1:
            return {"picks": [{"element": 10, "multiplier": 2}, {"element": 11, "multiplier": 1}]}
        return {"picks": [{"element": 10, "multiplier": 1}, {"element": 12, "multiplier": 1}]}

    path = await crawl_effective_ownership(
        processed_dir=processed,
        raw_dir=raw,
        cache_path=cache,
        project_root=tmp_path,
        rank_cap=10_000,
        client=httpx.AsyncClient(),
        fetch_entry=fetch_entry,
        fetch_standings=fetch_standings,
        fetch_picks=fetch_picks,
    )
    assert path == cache
    loaded = load_complete_eo_cache(cache)
    assert loaded is not None
    assert loaded["n"] == 2
    assert loaded["label"] == "Overall top 2"
    assert loaded["by_player"][10] == 150.0
    assert loaded["gameweek_id"] == 5
