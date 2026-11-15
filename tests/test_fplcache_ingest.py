from __future__ import annotations

import json
import lzma
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Sequence

import pandas as pd
import pytest

from backtesting.fplcache_ingest import ingest_season_fplcache
from backtesting.input_evidence import retain_receipt


class _FakeFplCachePort:
    def __init__(self, snapshots: dict[str, tuple[datetime, bytes]]) -> None:
        self._snapshots = snapshots

    def list_snapshots(self) -> Sequence[tuple[str, datetime]]:
        return sorted(((path, ts) for path, (ts, _) in self._snapshots.items()), key=lambda x: x[1])

    def fetch_snapshot_xz(self, path: str) -> bytes:
        return self._snapshots[path][1]


def _make_xz_bootstrap(
    *,
    gw: int,
    deadline: str,
    news_added: str,
    extra_player: bool = False,
) -> bytes:
    elements = [
        {
            "id": 1,
            "code": 1001,
            "team": 1,
            "element_type": 2,
            "now_cost": 55,
            "status": "a",
            "chance_of_playing_next_round": None,
            "chance_of_playing_this_round": None,
            "news": "",
            "news_added": news_added,
            "can_select": True,
            "removed": False,
            "selected_by_percent": "12.5",
            "total_points": 999,
        },
        {
            "id": 2,
            "code": 1002,
            "team": 2,
            "element_type": 3,
            "now_cost": 70,
            "status": "d",
            "chance_of_playing_next_round": 75,
            "chance_of_playing_this_round": 75,
            "news": "Knock",
            "news_added": news_added,
            "can_select": True,
            "removed": False,
            "selected_by_percent": "8.0",
            "total_points": 888,
        },
        {
            "id": 999,
            "code": 1999,
            "team": 1,
            "element_type": 5,
            "now_cost": 15,
            "status": "u",
            "chance_of_playing_next_round": 0,
            "chance_of_playing_this_round": 0,
            "news": "",
            "news_added": None,
            "can_select": False,
            "removed": True,
            "selected_by_percent": "0.0",
            "total_points": 777,
        },
    ]
    if extra_player:
        elements.append(
            {
                "id": 3,
                "code": 1003,
                "team": 3,
                "element_type": 4,
                "now_cost": 65,
                "status": "a",
                "chance_of_playing_next_round": None,
                "chance_of_playing_this_round": None,
                "news": "",
                "news_added": news_added,
                "can_select": True,
                "removed": False,
                "selected_by_percent": "5.0",
                "total_points": 666,
            }
        )
    payload = {
        "events": [{"id": gw, "deadline_time": deadline, "is_next": True}],
        "teams": [{"id": 1}, {"id": 2}, {"id": 3}],
        "elements": elements,
    }
    return lzma.compress(json.dumps(payload).encode("utf-8"))


def test_ingest_season_fplcache_freshness_disclosures_and_outcome_reconciliation(tmp_path: Path) -> None:
    now_utc = datetime.now(UTC).replace(microsecond=0)
    dl4 = now_utc + timedelta(hours=3)
    base_dl = dl4 - timedelta(days=21)
    gw_rows = []
    for gw in range(1, 39):
        dl = base_dl + timedelta(days=7 * (gw - 1))
        gw_rows.append(
            {
                "id": gw,
                "deadline_time": dl.isoformat().replace("+00:00", "Z"),
                "finished": gw == 1,
                "data_checked": gw == 1,
                "is_current": gw == 2,
                "is_next": gw == 3,
            }
        )
    gameweeks_df = pd.DataFrame(gw_rows)

    # GW1 includes DGW for club 1 (fixtures 11, 12) and BGW for club 3 (only plays in GW2+)
    ko1_a = (base_dl + timedelta(hours=18)).isoformat().replace("+00:00", "Z")
    ko1_b = (base_dl + timedelta(days=2, hours=18)).isoformat().replace("+00:00", "Z")
    fixtures_rows = [
        {"id": 11, "gameweek_id": 1, "home_club_id": 1, "away_club_id": 2, "kickoff_time": ko1_a, "finished": True},
        {"id": 12, "gameweek_id": 1, "home_club_id": 1, "away_club_id": 2, "kickoff_time": ko1_b, "finished": True},
    ]
    for gw in range(2, 39):
        ko = (base_dl + timedelta(days=7 * (gw - 1), hours=18)).isoformat().replace("+00:00", "Z")
        fixtures_rows.append(
            {"id": 100 + gw, "gameweek_id": gw, "home_club_id": 1, "away_club_id": 2, "kickoff_time": ko, "finished": False}
        )
        fixtures_rows.append(
            {"id": 200 + gw, "gameweek_id": gw, "home_club_id": 3, "away_club_id": 2, "kickoff_time": ko, "finished": False}
        )
    fixtures_df = pd.DataFrame(fixtures_rows)

    performances_df = pd.DataFrame(
        [
            {"player_id": 1, "fixture_id": 11, "gameweek_id": 1, "minutes": 90, "total_points": 6},
            {"player_id": 2, "fixture_id": 11, "gameweek_id": 1, "minutes": 0, "total_points": 0},
            {"player_id": 1, "fixture_id": 12, "gameweek_id": 1, "minutes": 90, "total_points": 2},
            {"player_id": 2, "fixture_id": 12, "gameweek_id": 1, "minutes": 80, "total_points": 5},
        ]
    )

    dl1 = base_dl
    dl2 = base_dl + timedelta(days=7)
    dl3 = base_dl + timedelta(days=14)

    snap1 = dl1 - timedelta(hours=4, minutes=30)
    snap2 = dl2 - timedelta(hours=12)
    snap3 = dl3 - timedelta(hours=30)
    snap4 = dl4 - timedelta(hours=30)

    snapshots = {
        "cache/2026/8/21/1300.json.xz": (
            snap1,
            _make_xz_bootstrap(
                gw=1,
                deadline=dl1.isoformat().replace("+00:00", "Z"),
                news_added=(snap1 - timedelta(hours=1)).isoformat().replace("+00:00", "Z"),
                extra_player=True,
            ),
        ),
        "cache/2026/8/28/0530.json.xz": (
            snap2,
            _make_xz_bootstrap(
                gw=2,
                deadline=dl2.isoformat().replace("+00:00", "Z"),
                news_added=(snap2 - timedelta(hours=1)).isoformat().replace("+00:00", "Z"),
            ),
        ),
        "cache/2026/9/3/1130.json.xz": (
            snap3,
            _make_xz_bootstrap(
                gw=3,
                deadline=dl3.isoformat().replace("+00:00", "Z"),
                news_added=(snap3 - timedelta(hours=1)).isoformat().replace("+00:00", "Z"),
            ),
        ),
        "cache/2026/9/10/1130.json.xz": (
            snap4,
            _make_xz_bootstrap(
                gw=4,
                deadline=dl4.isoformat().replace("+00:00", "Z"),
                news_added=(snap4 - timedelta(hours=1)).isoformat().replace("+00:00", "Z"),
            ),
        ),
    }

    receipt_dir = tmp_path / "receipts"
    manual_payload = lzma.decompress(snapshots["cache/2026/9/10/1130.json.xz"][1])
    manual_doc = json.loads(manual_payload)
    manual_doc["events"][0]["id"] = 4
    manual_bytes = json.dumps(manual_doc).encode("utf-8")
    rec4 = retain_receipt(
        receipt_dir,
        season="2026-27",
        gw=4,
        endpoint="bootstrap-static",
        deadline=dl4,
        payload=manual_bytes,
    )

    quarantine_dir = tmp_path / "quarantine"
    manifest_path = tmp_path / "manifest.json"
    manifest = ingest_season_fplcache(
        season="2026-27",
        gameweeks_df=gameweeks_df,
        fixtures_df=fixtures_df,
        performances_df=performances_df,
        source_port=_FakeFplCachePort(snapshots),
        quarantine_dir=quarantine_dir,
        manifest_path=manifest_path,
        reference_utc=dl4 + timedelta(hours=1),
        outcome_captured_at=base_dl + timedelta(days=4),
        receipt_storage=receipt_dir,
        receipt_ids_by_gw={4: rec4["receipt_id"]},
    )

    assert manifest["attribution"]["repo"] == "Randdalf/fplcache"
    assert manifest["attribution"]["license"] == "The Unlicense"
    limitation_codes = {item["code"] for item in manifest["disclosed_limitations"]}
    assert {"late_press_conference_lag", "gw1_5_exploratory_baseline_checks"} <= limitation_codes

    by_gw = {row["gw"]: row for row in manifest["gameweeks"]}
    assert len(by_gw) == 38
    assert by_gw[1]["input_status"] == "admitted"
    assert by_gw[1]["player_count"] == 3
    assert by_gw[1]["lag_hours"] == 4.5
    assert by_gw[1]["outcome_settlement_status"] == "settled_verified"
    assert by_gw[1]["schedule_coverage_errors"] == []

    assert by_gw[2]["input_status"] == "admitted_disclosed_8h_24h"
    assert by_gw[2]["lag_hours"] == 12.0
    assert "stale_window_8h_24h" in by_gw[2]["disclosed_limitations"]
    assert by_gw[2]["outcome_settlement_status"] == "unsettled"

    assert by_gw[3]["input_status"] == "source_stale"
    assert by_gw[4]["input_status"] == "admitted_local_receipt"
    assert by_gw[5]["input_status"] == "pending_future_gw"
    assert by_gw[38]["input_status"] == "pending_future_gw"

    gw1_quarantined = json.loads((quarantine_dir / "gw01_pre_deadline_inputs.json").read_text(encoding="utf-8"))
    ids = {p["id"] for p in gw1_quarantined["players"]}
    assert ids == {1, 2, 3}
    assert all("total_points" not in p for p in gw1_quarantined["players"])

    with pytest.raises(ValueError, match="scope/endpoint mismatch"):
        ingest_season_fplcache(
            season="2026-27",
            gameweeks_df=gameweeks_df,
            fixtures_df=fixtures_df,
            performances_df=performances_df,
            source_port=_FakeFplCachePort(snapshots),
            quarantine_dir=tmp_path / "q_bad_receipt",
            manifest_path=tmp_path / "m_bad_receipt.json",
            reference_utc=dl4 + timedelta(hours=1),
            receipt_storage=receipt_dir,
            receipt_ids_by_gw={3: rec4["receipt_id"]},
        )

    border_snap = dl1 - timedelta(hours=23, minutes=45)
    border_manifest = ingest_season_fplcache(
        season="2026-27",
        gameweeks_df=gameweeks_df.iloc[:1],
        fixtures_df=fixtures_df,
        performances_df=None,
        source_port=_FakeFplCachePort(
            {
                "cache/2026/8/20/1745.json.xz": (
                    border_snap,
                    _make_xz_bootstrap(
                        gw=1,
                        deadline=dl1.isoformat().replace("+00:00", "Z"),
                        news_added=(border_snap - timedelta(minutes=10)).isoformat().replace("+00:00", "Z"),
                    ),
                )
            }
        ),
        quarantine_dir=tmp_path / "q_border",
        manifest_path=tmp_path / "m_border.json",
        reference_utc=dl1 + timedelta(hours=1),
    )
    assert border_manifest["gameweeks"][0]["input_status"] == "source_stale"


def test_ingest_rejects_future_news_added_and_oversized_xz(tmp_path: Path) -> None:
    dl = datetime(2026, 8, 21, 17, 30, tzinfo=UTC)
    snap = dl - timedelta(hours=3)
    gameweeks_df = pd.DataFrame(
        [{"id": 1, "deadline_time": dl.isoformat().replace("+00:00", "Z"), "finished": False, "data_checked": False, "is_current": True, "is_next": False}]
    )
    fixtures_df = pd.DataFrame(
        [{"id": 1, "gameweek_id": 1, "home_club_id": 1, "away_club_id": 2, "kickoff_time": "2026-08-22T12:00:00Z", "finished": False}]
    )
    bad_xz = _make_xz_bootstrap(
        gw=1,
        deadline=dl.isoformat().replace("+00:00", "Z"),
        news_added=(snap + timedelta(minutes=30)).isoformat().replace("+00:00", "Z"),
    )
    manifest = ingest_season_fplcache(
        season="2026-27",
        gameweeks_df=gameweeks_df,
        fixtures_df=fixtures_df,
        performances_df=None,
        source_port=_FakeFplCachePort({"cache/2026/8/21/1430.json.xz": (snap, bad_xz)}),
        quarantine_dir=tmp_path / "q",
        manifest_path=tmp_path / "m.json",
        reference_utc=dl + timedelta(hours=1),
    )
    row = manifest["gameweeks"][0]
    assert row["input_status"] == "invalid"
    assert "news_added_after_capture" in row["issues"]


def test_ingest_reconciles_in_window_club_transfer_and_catches_missing_outcome(tmp_path: Path) -> None:
    from backtesting.fplcache_ingest import validate_fplcache_url

    with pytest.raises(ValueError, match="outside approved"):
        validate_fplcache_url("https://example.com/evil.json.xz")

    dl = datetime(2026, 8, 21, 17, 30, tzinfo=UTC)
    snap = dl - timedelta(hours=3)
    gameweeks_df = pd.DataFrame(
        [{"id": 1, "deadline_time": dl.isoformat().replace("+00:00", "Z"), "finished": True, "data_checked": True, "is_current": False, "is_next": False}]
    )
    fixtures_df = pd.DataFrame(
        [
            {"id": 1, "gameweek_id": 1, "home_club_id": 1, "away_club_id": 3, "kickoff_time": "2026-08-22T12:00:00Z", "finished": True},
            {"id": 2, "gameweek_id": 1, "home_club_id": 2, "away_club_id": 3, "kickoff_time": "2026-08-22T15:00:00Z", "finished": True},
        ]
    )
    snap_xz = _make_xz_bootstrap(
        gw=1,
        deadline=dl.isoformat().replace("+00:00", "Z"),
        news_added=(snap - timedelta(hours=1)).isoformat().replace("+00:00", "Z"),
    )
    perf_transfer = pd.DataFrame(
        [
            {"player_id": 1, "fixture_id": 2, "gameweek_id": 1, "was_home": True, "minutes": 90, "total_points": 6},
            {"player_id": 2, "fixture_id": 2, "gameweek_id": 1, "was_home": True, "minutes": 90, "total_points": 2},
        ]
    )
    ok_manifest = ingest_season_fplcache(
        season="2026-27",
        gameweeks_df=gameweeks_df,
        fixtures_df=fixtures_df,
        performances_df=perf_transfer,
        source_port=_FakeFplCachePort({"cache/2026/8/21/1430.json.xz": (snap, snap_xz)}),
        quarantine_dir=tmp_path / "q1",
        manifest_path=tmp_path / "m1.json",
        reference_utc=dl + timedelta(hours=1),
        outcome_captured_at=datetime(2026, 8, 24, 12, 0, tzinfo=UTC),
    )
    assert ok_manifest["gameweeks"][0]["outcome_settlement_status"] == "settled_verified"
    assert ok_manifest["gameweeks"][0]["transfer_reconciled_count"] == 1

    perf_missing = perf_transfer.iloc[:1]
    bad_manifest = ingest_season_fplcache(
        season="2026-27",
        gameweeks_df=gameweeks_df,
        fixtures_df=fixtures_df,
        performances_df=perf_missing,
        source_port=_FakeFplCachePort({"cache/2026/8/21/1430.json.xz": (snap, snap_xz)}),
        quarantine_dir=tmp_path / "q2",
        manifest_path=tmp_path / "m2.json",
        reference_utc=dl + timedelta(hours=1),
        outcome_captured_at=datetime(2026, 8, 24, 12, 0, tzinfo=UTC),
    )
    assert bad_manifest["gameweeks"][0]["outcome_settlement_status"] == "settlement_coverage_mismatch"
    assert bad_manifest["gameweeks"][0]["settlement_coverage_errors"] == ["outcome_coverage"]
