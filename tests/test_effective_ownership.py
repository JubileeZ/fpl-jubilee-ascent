"""Seams: EO aggregate, complete cache, Differentials Ranking rows."""

from __future__ import annotations

import json
from pathlib import Path

from projections.differentials_ranking import build_differentials_ranking
from projections.effective_ownership import (
    aggregate_effective_ownership,
    load_complete_eo_cache,
    overall_league_id,
    save_complete_eo_cache,
)


def test_aggregate_eo_weights_owned_captain_and_tc() -> None:
    # Two managers: A owns 1 (C), B owns 1 (TC) and 2 (plain)
    entries = [
        [{"element": 1, "multiplier": 2}, {"element": 3, "multiplier": 1}],
        [{"element": 1, "multiplier": 3}, {"element": 2, "multiplier": 1}],
    ]
    result = aggregate_effective_ownership(entries, rank_cap=10_000)
    assert result.n == 2
    assert result.label == "Overall top 2"
    assert result.by_player[1] == 250.0  # (2+3)/2*100
    assert result.by_player[2] == 50.0
    assert result.by_player[3] == 50.0
    assert 4 not in result.by_player


def test_aggregate_eo_label_uses_rank_cap_when_full() -> None:
    entries = [[{"element": 1, "multiplier": 1}] for _ in range(10_000)]
    result = aggregate_effective_ownership(entries, rank_cap=10_000)
    assert result.n == 10_000
    assert result.label == "Overall top 10000"
    assert result.by_player[1] == 100.0


def test_overall_league_id_from_short_name() -> None:
    entry = {
        "leagues": {
            "classic": [
                {"id": 1, "short_name": "x"},
                {"id": 314, "short_name": "overall"},
            ]
        }
    }
    assert overall_league_id(entry) == 314
    assert overall_league_id({"leagues": {"classic": []}}) is None


def test_eo_cache_roundtrip_complete_only(tmp_path: Path) -> None:
    path = tmp_path / "effective_ownership.json"
    assert load_complete_eo_cache(path) is None
    path.write_text(json.dumps({"complete": False, "n": 3, "by_player": {"1": 10.0}}), encoding="utf-8")
    assert load_complete_eo_cache(path) is None
    save_complete_eo_cache(
        path,
        n=2,
        gameweek_id=5,
        league_id=314,
        by_player={1: 150.0, 2: 50.0},
        label="Overall top 2",
        captured_at="2026-09-18T05:00:00+00:00",
    )
    loaded = load_complete_eo_cache(path)
    assert loaded is not None
    assert loaded["n"] == 2
    assert loaded["by_player"][1] == 150.0
    assert loaded["label"] == "Overall top 2"


def test_differentials_ranking_excludes_owned_sorts_xp_then_eo() -> None:
    players = [
        {"id": 1, "name": "A", "pos": "MID", "team": "ARS", "price": 8.0, "total_xp_horizon": 40.0},
        {"id": 2, "name": "B", "pos": "FWD", "team": "MCI", "price": 12.0, "total_xp_horizon": 50.0},
        {"id": 3, "name": "C", "pos": "DEF", "team": "LIV", "price": 5.0, "total_xp_horizon": 50.0},
        {"id": 4, "name": "D", "pos": "MID", "team": "CHE", "price": 6.5, "total_xp_horizon": 30.0},
    ]
    eo = {1: 10.0, 2: 40.0, 3: 5.0, 4: 2.0}
    rows = build_differentials_ranking(
        players,
        eo,
        owned_ids={1},
        itb=1.0,
        owned_selling_prices={1: 7.5},
    )
    assert [r["id"] for r in rows] == [3, 2, 4]  # 50/5, 50/40, 30/2
    assert rows[0]["eo_pct"] == 5.0
    assert rows[0]["affordable"] is True  # 5.0 <= 1.0 + 7.5
    assert rows[1]["affordable"] is False  # 12.0 > 8.5
    assert rows[2]["affordable"] is True


def test_differentials_ranking_empty_without_squad() -> None:
    players = [{"id": 1, "name": "A", "pos": "MID", "team": "ARS", "price": 8.0, "total_xp_horizon": 40.0}]
    rows = build_differentials_ranking(players, {1: 10.0}, owned_ids=set(), itb=0.0, owned_selling_prices={})
    assert rows == []
