"""Tests for Manager Performance tracking, two-tier cached service, analytics, and Streamlit workspace."""

import json
from pathlib import Path
from typing import Any
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from clients.fpl_api import fetch_classic_league_standings
from dashboard.performance_analytics import (
    compute_chip_timing_differential,
    compute_composite_comparison_series,
    compute_kpis,
    compute_manager_series,
    extract_chip_inventory,
)
from dashboard.performance_service import (
    extract_joined_classic_leagues,
    extract_top_standings_peers,
    fetch_with_two_tier_cache,
)
from features.processor import process_directory
from test_streamlit_planner import dataset


# Sample fixtures
def sample_entry_summary() -> dict[str, Any]:
    return {
        "id": 12345,
        "player_first_name": "Jubilee",
        "player_last_name": "Ascent",
        "name": "Jubilee XI",
        "summary_overall_points": 340,
        "summary_overall_rank": 45000,
        "leagues": {
            "classic": [
                {
                    "id": 999,
                    "name": "Work League",
                    "league_type": "x",
                    "entry_rank": 3,
                    "entry_last_rank": 5,
                },
                {
                    "id": 888,
                    "name": "Friends League",
                    "league_type": "x",
                    "entry_rank": 1,
                    "entry_last_rank": 1,
                },
                {
                    "id": 1,
                    "name": "Overall",
                    "league_type": "s",
                    "entry_rank": 45000,
                    "entry_last_rank": 52000,
                },
            ]
        },
    }


def sample_entry_history() -> dict[str, Any]:
    return {
        "current": [
            {
                "event": 1,
                "points": 75,
                "total_points": 75,
                "rank": 200000,
                "overall_rank": 200000,
                "bank": 5,
                "value": 1000,
                "event_transfers": 0,
                "event_transfers_cost": 0,
                "points_on_bench": 4,
            },
            {
                "event": 2,
                "points": 60,
                "total_points": 135,
                "rank": 450000,
                "overall_rank": 150000,
                "bank": 5,
                "value": 1005,
                "event_transfers": 1,
                "event_transfers_cost": 0,
                "points_on_bench": 2,
            },
            {
                "event": 3,
                "points": 85,
                "total_points": 216,
                "rank": 80000,
                "overall_rank": 65000,
                "bank": 2,
                "value": 1012,
                "event_transfers": 2,
                "event_transfers_cost": 4,  # -4 hit
                "points_on_bench": 12,
            },
            {
                "event": 4,
                "points": 90,
                "total_points": 306,
                "rank": 35000,
                "overall_rank": 45000,
                "bank": 10,
                "value": 1018,
                "event_transfers": 0,
                "event_transfers_cost": 0,
                "points_on_bench": 6,
            },
        ],
        "chips": [
            {"name": "3xc", "time": "2026-09-01T10:00:00Z", "event": 4},
        ],
    }


def sample_league_standings() -> dict[str, Any]:
    return {
        "league": {"id": 999, "name": "Work League"},
        "standings": {
            "results": [
                {
                    "id": 1,
                    "entry": 54321,
                    "player_name": "Rival One",
                    "entry_name": "Rival FC",
                    "rank": 1,
                    "last_rank": 2,
                    "total": 350,
                    "event_total": 70,
                },
                {
                    "id": 2,
                    "entry": 12345,
                    "player_name": "Jubilee Ascent",
                    "entry_name": "Jubilee XI",
                    "rank": 2,
                    "last_rank": 3,
                    "total": 340,
                    "event_total": 90,
                },
                {
                    "id": 3,
                    "entry": 67890,
                    "player_name": "Rival Two",
                    "entry_name": "Second Rival",
                    "rank": 3,
                    "last_rank": 1,
                    "total": 330,
                    "event_total": 55,
                },
            ]
        },
    }


def sample_global_benchmarks() -> dict[int, dict[str, Any]]:
    return {
        1: {"id": 1, "average_entry_score": 55, "highest_score": 120, "ranked_count": 9000000, "chip_plays": []},
        2: {"id": 2, "average_entry_score": 50, "highest_score": 115, "ranked_count": 9100000, "chip_plays": []},
        3: {"id": 3, "average_entry_score": 52, "highest_score": 130, "ranked_count": 9150000, "chip_plays": [{"chip_name": "wildcard", "num_played": 300000}]},
        4: {"id": 4, "average_entry_score": 62, "highest_score": 140, "ranked_count": 9200000, "chip_plays": [{"chip_name": "3xc", "num_played": 500000}]},
    }


# 1. API Client tests
@pytest.mark.asyncio
async def test_fetch_classic_league_standings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import httpx

    expected = {"league": {"id": 123}, "standings": {"results": []}}

    class MockTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            assert "leagues-classic/123/standings" in str(request.url)
            assert request.url.params.get("page_standings") == "1"
            return httpx.Response(200, json=expected)

    client = httpx.AsyncClient(transport=MockTransport())
    monkeypatch.setattr("clients.fpl_api.RAW_CACHE_DIR", tmp_path)
    res = await fetch_classic_league_standings(client, 123, page_standings=1, write_cache=True)
    assert res == expected
    assert (tmp_path / "league_classic_123_standings_p1.json").exists()


# 2. Performance service & caching tests
def test_two_tier_cache_and_stale_fallback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True)

    # Pre-populate disk cache
    initial_data = {"key": "cached_val"}
    (cache_dir / "test_endpoint.json").write_text(json.dumps(initial_data), encoding="utf-8")

    # Read from cache without network
    read_data = fetch_with_two_tier_cache("test_endpoint", "http://fake-url", storage_dir=cache_dir)
    assert read_data == initial_data

    # When force_refresh=True and network returns 429, falls back to stale cache
    def mock_429(url: str, params: Any = None) -> dict[str, Any]:
        import httpx
        req = httpx.Request("GET", url)
        resp = httpx.Response(429, request=req)
        raise httpx.HTTPStatusError("Rate limited", request=req, response=resp)

    monkeypatch.setattr("dashboard.performance_service._http_get_json", mock_429)
    fallback_data = fetch_with_two_tier_cache("test_endpoint", "http://fake-url", storage_dir=cache_dir, force_refresh=True)
    assert fallback_data.get("_cached_fallback") is True
    assert "429" in str(fallback_data.get("_stale_warning"))


def test_extract_joined_classic_leagues_and_peers() -> None:
    summary = sample_entry_summary()
    custom_leagues = extract_joined_classic_leagues(summary)
    assert len(custom_leagues) == 2
    # Overall (type 's') is excluded
    assert all(lg["id"] != 1 for lg in custom_leagues)
    # Sorted by entry_rank
    assert custom_leagues[0]["name"] == "Friends League"
    assert custom_leagues[1]["name"] == "Work League"

    standings = sample_league_standings()
    peers = extract_top_standings_peers(standings, exclude_entry_id=12345)
    assert len(peers) == 2
    assert all(p["entry_id"] != 12345 for p in peers)
    assert peers[0]["entry_id"] == 54321
    assert peers[0]["total"] == 350


# 3. Analytics tests
def test_compute_manager_series_and_deltas() -> None:
    hist = sample_entry_history()
    benchmarks = sample_global_benchmarks()
    df = compute_manager_series(hist, global_benchmarks=benchmarks)

    assert len(df) == 4
    assert list(df["gw"]) == [1, 2, 3, 4]
    # Net points in GW3 accounts for -4 hit: 85 - 4 = 81
    gw3 = df[df["gw"] == 3].iloc[0]
    assert gw3["points"] == 85
    assert gw3["cost"] == 4
    assert gw3["net_points"] == 81
    assert gw3["delta_vs_global"] == 81 - 52  # +29

    # GW4 chip is Triple Captain
    gw4 = df[df["gw"] == 4].iloc[0]
    assert gw4["chip"] == "TC"
    assert gw4["delta_vs_global"] == 90 - 62  # +28
    assert df["cum_delta_vs_global"].iloc[-1] > 0


def test_compute_composite_comparison_series() -> None:
    hist_user = sample_entry_history()
    benchmarks = sample_global_benchmarks()
    user_df = compute_manager_series(hist_user, global_benchmarks=benchmarks)

    # Create rival series
    hist_rival = sample_entry_history()
    hist_rival["current"][3]["points"] = 70  # Rival scored 70 in GW4
    rival_dfs = {54321: compute_manager_series(hist_rival, global_benchmarks=benchmarks)}

    comp_df = compute_composite_comparison_series(user_df, rival_dfs)
    assert "rivals_mean" in comp_df.columns
    assert "delta_vs_rivals_mean" in comp_df.columns
    # In GW4: user net 90, rival net 70 -> delta +20
    gw4_comp = comp_df[comp_df["gw"] == 4].iloc[0]
    assert gw4_comp["delta_vs_rivals_mean"] == 20.0


def test_chip_timing_differential_and_inventory() -> None:
    hist = sample_entry_history()
    benchmarks = sample_global_benchmarks()
    df = compute_manager_series(hist, global_benchmarks=benchmarks)

    diff = compute_chip_timing_differential(df, benchmark_col="global_avg")
    assert diff["chip_weeks"] == 1
    assert diff["chip_delta_sum"] == 28  # GW4: 90 - 62
    assert diff["chip_swing"] > 0

    inv = extract_chip_inventory(hist)
    # Triple Captain played on GW4
    assert inv["TC"]["Set 1 (GW1–19)"] == "Played GW4"
    assert inv["TC"]["Set 2 (GW20–38)"] == "Available"
    # Wildcard, Bench Boost, Free Hit are Available
    assert inv["WC"]["Set 1 (GW1–19)"] == "Available"
    assert inv["BB"]["Set 1 (GW1–19)"] == "Available"
    assert inv["FH"]["Set 1 (GW1–19)"] == "Available"


def test_compute_kpis() -> None:
    hist = sample_entry_history()
    summary = sample_entry_summary()
    standings = sample_league_standings()
    benchmarks = sample_global_benchmarks()
    df = compute_manager_series(hist, global_benchmarks=benchmarks)

    kpis = compute_kpis(df, summary, league_standings=standings)
    assert kpis["overall_rank"] == 45000
    assert kpis["rank_delta"] == 65000 - 45000  # climbed 20,000 places in GW4
    assert kpis["total_hits_cost"] == 4
    assert kpis["total_bench_points"] == 4 + 2 + 12 + 6
    assert kpis["league_rank"] == 2
    assert kpis["league_leader_gap"] == 350 - 340  # 10 pts gap


# 4. Processor retaining global event benchmarks
def test_processor_retains_gameweek_benchmarks(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"
    raw_dir.mkdir(parents=True)

    bs = {
        "teams": [{"id": 1, "name": "Arsenal", "short_name": "ARS"}],
        "events": [
            {
                "id": 1,
                "name": "Gameweek 1",
                "deadline_time": "2026-08-15T10:00:00Z",
                "finished": True,
                "is_current": False,
                "is_next": False,
                "average_entry_score": 58,
                "highest_score": 134,
                "chip_plays": [{"chip_name": "bboost", "num_played": 10000}],
                "ranked_count": 8900000,
            }
        ],
        "elements": [],
    }
    (raw_dir / "bootstrap_static.json").write_text(json.dumps(bs), encoding="utf-8")

    process_directory(raw_dir, processed_dir)
    df_gw = pd.read_parquet(processed_dir / "gameweeks.parquet")
    assert "average_entry_score" in df_gw.columns
    assert "highest_score" in df_gw.columns
    assert "chip_plays" in df_gw.columns
    assert "ranked_count" in df_gw.columns
    assert int(df_gw.iloc[0]["average_entry_score"]) == 58


# 5. Streamlit Performance view testing
def test_performance_onboarding_rendered_when_no_entry_id(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    data_path = tmp_path / "dataset.json"
    data_path.write_text(json.dumps(dataset()), encoding="utf-8")
    monkeypatch.setenv("FPL_PLANNER_DATASET", str(data_path))
    monkeypatch.setenv("FPL_PLANNER_STORAGE", str(tmp_path / "storage"))
    monkeypatch.setenv("FPL_PLANNER_PROCESSED_DIR", str(tmp_path / "processed"))

    script = Path(__file__).resolve().parents[1] / "streamlit_app.py"
    app = AppTest.from_file(script, default_timeout=30).run()
    assert not app.exception
    # Default page is Performance
    assert app.radio(key="dashboard-page").value == "Performance"
    # Onboarding input appears
    assert any(num.key == "onboarding-entry-input" for num in app.number_input)
    assert any(b.key == "onboarding-load-btn" for b in app.button)


def test_performance_view_with_loaded_entry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    data_path = tmp_path / "dataset.json"
    data_path.write_text(json.dumps(dataset()), encoding="utf-8")
    storage_dir = tmp_path / "storage"
    storage_dir.mkdir(parents=True)
    fpl_cache = storage_dir / "fpl_cache"
    fpl_cache.mkdir(parents=True)

    # Pre-populate cached FPL responses so test never hits external network
    (fpl_cache / "entry_12345.json").write_text(json.dumps(sample_entry_summary()), encoding="utf-8")
    (fpl_cache / "entry_12345_history.json").write_text(json.dumps(sample_entry_history()), encoding="utf-8")
    (fpl_cache / "league_999_standings_p1.json").write_text(json.dumps(sample_league_standings()), encoding="utf-8")

    # Set saved entry_id in preferences
    (storage_dir / "preferences.json").write_text(json.dumps({"entry_id": 12345, "page": "Performance"}), encoding="utf-8")

    monkeypatch.setenv("FPL_PLANNER_DATASET", str(data_path))
    monkeypatch.setenv("FPL_PLANNER_STORAGE", str(storage_dir))
    monkeypatch.setenv("FPL_PLANNER_PROCESSED_DIR", str(tmp_path / "processed"))

    script = Path(__file__).resolve().parents[1] / "streamlit_app.py"
    app = AppTest.from_file(script, default_timeout=30).run()
    assert not app.exception
    assert app.radio(key="dashboard-page").value == "Performance"

    # Manager display appears in caption
    assert any("Jubilee XI" in c.value for c in app.caption)
    # KPI cards rendered
    assert any("Overall Rank" in m.label for m in app.metric)
    assert any("Cumulative Points" in m.label for m in app.metric)
    assert any("Chip Timing Swing" in m.label for m in app.metric)
    assert any("Hit & Bench Drag" in m.label for m in app.metric)

    # Tabs and DataFrame rendered
    assert len(app.tabs) >= 2
    assert any("Attribution" in t.label or "Gameweek" in t.label for t in app.tabs)
    assert len(app.dataframe) >= 1
    assert any(s.key == "perf-trajectory-metric" for s in app.segmented_control)

    # Switch entry button
    btn_switch = next(b for b in app.button if b.key == "perf-switch-btn")
    assert btn_switch is not None
    btn_switch.click().run()
    assert not app.exception
    # After switching, onboarding prompt appears
    assert any(num.key == "onboarding-entry-input" for num in app.number_input)


def test_performance_chart_builders() -> None:
    from dashboard.performance_view import (
        _build_chip_adoption_figure,
        _build_delta_figure,
        _build_trajectory_figure,
    )

    m_series = compute_manager_series(sample_entry_history(), global_benchmarks=sample_global_benchmarks())
    fig_traj = _build_trajectory_figure(
        user_name="Jubilee XI",
        user_df=m_series,
        rival_dfs={},
        rival_labels={},
        metric="Overall Rank",
        use_log_scale=False,
    )
    assert fig_traj is not None
    assert len(fig_traj.data) >= 1

    fig_delta = _build_delta_figure(m_series, benchmark_mode="Global Average")
    assert fig_delta is not None
    assert len(fig_delta.data) >= 1

    fig_chips = _build_chip_adoption_figure(m_series, benchmarks=sample_global_benchmarks())
    assert fig_chips is not None
    assert len(fig_chips.data) >= 1

