"""TDD tests for historical mirror acquisition, validation, zero-diff, and chip calendar."""

from __future__ import annotations

import csv
import io
import json
import lzma
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from backtesting.empirical_mirrors import (
    build_bootstrap_mirror_record,
    build_causal_chip_calendar,
    build_fixture_mirror_record,
    build_seed_manifest,
    load_empirical_manifest_bundle,
    validate_mirror_url,
    verify_settled_outcomes_zero_diff,
)
from backtesting.season_rules import get_rules, validate_chip_calendar

UTC = timezone.utc


def _bootstrap_xz(
    *,
    gw: int,
    deadline: datetime,
    news_added: datetime | None = None,
    with_manager: bool = False,
) -> bytes:
    elements = [
        {
            "id": 1,
            "code": 1001,
            "team": 1,
            "element_type": 2,
            "now_cost": 50,
            "selected_by_percent": "12.5",
            "status": "a",
            "can_select": True,
            "chance_of_playing_next_round": None,
            "news": "",
            "news_added": news_added.isoformat().replace("+00:00", "Z") if news_added else None,
        },
        {
            "id": 2,
            "code": 1002,
            "team": 2,
            "element_type": 3,
            "now_cost": 80,
            "selected_by_percent": "5.0",
            "status": "u",
            "can_select": False,
            "chance_of_playing_next_round": 0,
            "news": "Loaned out",
            "news_added": None,
        },
    ]
    if with_manager:
        elements.append(
            {
                "id": 900,
                "code": 9000,
                "team": 1,
                "element_type": 5,
                "now_cost": 15,
                "selected_by_percent": "1.0",
                "status": "a",
                "can_select": True,
                "chance_of_playing_next_round": None,
                "news": "",
                "news_added": None,
            }
        )
    payload = {
        "events": [{"id": gw, "deadline_time": deadline.isoformat().replace("+00:00", "Z"), "is_next": True}],
        "teams": [{"id": 1, "name": "TeamA"}, {"id": 2, "name": "TeamB"}],
        "elements": elements,
        "chips": [{"name": "wildcard", "start_event": 1, "stop_event": 19}],
    }
    return lzma.compress(json.dumps(payload, sort_keys=True).encode("utf-8"))


def _fixtures_csv(gws: range) -> bytes:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=["id", "event", "team_h", "team_a", "kickoff_time", "provisional_start_time"])
    writer.writeheader()
    fid = 1
    for gw in gws:
        writer.writerow(
            {
                "id": fid,
                "event": gw,
                "team_h": 1,
                "team_a": 2,
                "kickoff_time": (datetime(2025, 8, 16, 14, 0, tzinfo=UTC) + timedelta(days=7 * (gw - 1))).isoformat(),
                "provisional_start_time": "False",
            }
        )
        fid += 1
    return buf.getvalue().encode("utf-8")


def test_validate_mirror_url_blocks_sealed_2026_27_and_unapproved_hosts() -> None:
    validate_mirror_url("https://raw.githubusercontent.com/Randdalf/fplcache/abc/cache/2025/8/15/1252.json.xz")
    validate_mirror_url("https://raw.githubusercontent.com/Randdalf/fplcache/abc/cache/2026/5/24/0839.json.xz")
    validate_mirror_url("https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/abc/data/2025-26/fixtures.csv")
    validate_mirror_url("https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/abc/data/2024-25/fixtures.csv")

    for bad in (
        "https://raw.githubusercontent.com/Randdalf/fplcache/abc/cache/2026/8/14/1200.json.xz",
        "https://raw.githubusercontent.com/Randdalf/fplcache/abc/cache/2026/6/1/0000.json.xz",
        "https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/abc/data/2026-27/fixtures.csv",
        "https://raw.githubusercontent.com/attacker/evil/main/cache/2025/8/15/1252.json.xz",
        "https://raw.githubusercontent.com/attacker/evil/main/data/2025-26/fixtures.csv",
        "https://example.com/Randdalf/fplcache/cache/2025/8/15/1252.json.xz",
        "http://raw.githubusercontent.com/Randdalf/fplcache/abc/cache/2025/8/15/1252.json.xz",
    ):
        with pytest.raises(ValueError):
            validate_mirror_url(bad)


def test_bootstrap_mirror_record_hashes_bounds_and_disclosures() -> None:
    dl = datetime(2025, 8, 15, 17, 30, tzinfo=UTC)
    raw = _bootstrap_xz(gw=1, deadline=dl, news_added=datetime(2025, 8, 15, 10, 0, tzinfo=UTC), with_manager=True)
    rec = build_bootstrap_mirror_record(
        season="2025-26",
        gw=1,
        deadline=dl,
        prev_deadline=None,
        url="https://raw.githubusercontent.com/Randdalf/fplcache/sha1/cache/2025/8/15/1252.json.xz",
        repo_path="cache/2025/8/15/1252.json.xz",
        commit_sha="a" * 40,
        commit_time=datetime(2025, 8, 15, 12, 53, tzinfo=UTC),
        raw_bytes=raw,
    )
    assert rec["status"] == "supported"
    assert rec["blob_sha256"] != rec["decompressed_sha256"]
    assert rec["decompressed_sha256"] != rec["table_sha256"]
    assert rec["element_count"] == 2
    assert rec["excluded_manager_count"] == 1
    assert rec["purchase_eligible_count"] == 1
    assert rec["null_chance_count"] == 1
    assert "fplcache_mirror_provenance" in rec["disclosed_limitations"]
    assert "bootstrap_stale_band_8h_to_24h" not in rec["disclosed_limitations"]

    # 12h old -> supported with 8h-24h stale band disclosure
    dl_stale_band = datetime(2025, 8, 16, 1, 0, tzinfo=UTC)
    rec_band = build_bootstrap_mirror_record(
        season="2025-26",
        gw=1,
        deadline=dl_stale_band,
        prev_deadline=None,
        url="https://raw.githubusercontent.com/Randdalf/fplcache/sha1/cache/2025/8/15/1252.json.xz",
        repo_path="cache/2025/8/15/1252.json.xz",
        commit_sha="a" * 40,
        commit_time=datetime(2025, 8, 15, 12, 53, tzinfo=UTC),
        raw_bytes=_bootstrap_xz(gw=1, deadline=dl_stale_band),
    )
    assert rec_band["status"] == "supported"
    assert "bootstrap_stale_band_8h_to_24h" in rec_band["disclosed_limitations"]

    # >24h -> source_stale; news_added > commit -> invalid
    rec_too_old = build_bootstrap_mirror_record(
        season="2025-26",
        gw=1,
        deadline=datetime(2025, 8, 17, 0, 0, tzinfo=UTC),
        prev_deadline=None,
        url="https://raw.githubusercontent.com/Randdalf/fplcache/sha1/cache/2025/8/15/1252.json.xz",
        repo_path="cache/2025/8/15/1252.json.xz",
        commit_sha="a" * 40,
        commit_time=datetime(2025, 8, 15, 12, 53, tzinfo=UTC),
        raw_bytes=_bootstrap_xz(gw=1, deadline=datetime(2025, 8, 17, 0, 0, tzinfo=UTC)),
    )
    assert rec_too_old["status"] == "source_stale"

    raw_future_news = _bootstrap_xz(gw=1, deadline=dl, news_added=datetime(2025, 8, 15, 14, 0, tzinfo=UTC))
    rec_invalid = build_bootstrap_mirror_record(
        season="2025-26",
        gw=1,
        deadline=dl,
        prev_deadline=None,
        url="https://raw.githubusercontent.com/Randdalf/fplcache/sha1/cache/2025/8/15/1252.json.xz",
        repo_path="cache/2025/8/15/1252.json.xz",
        commit_sha="a" * 40,
        commit_time=datetime(2025, 8, 15, 12, 53, tzinfo=UTC),
        raw_bytes=raw_future_news,
    )
    assert rec_invalid["status"] == "invalid"


def test_fixture_mirror_record_window_and_staleness_checks() -> None:
    dl2 = datetime(2025, 8, 22, 17, 30, tzinfo=UTC)
    dl1 = datetime(2025, 8, 15, 17, 30, tzinfo=UTC)
    csv_bytes = _fixtures_csv(range(2, 8))

    ok = build_fixture_mirror_record(
        season="2025-26",
        gw=2,
        deadline=dl2,
        prev_deadline=dl1,
        url="https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/s1/data/2025-26/fixtures.csv",
        commit_sha="b" * 40,
        commit_time=datetime(2025, 8, 20, 7, 59, tzinfo=UTC),
        prev_commit_time=datetime(2025, 8, 1, 8, 49, tzinfo=UTC),
        raw_bytes=csv_bytes,
    )
    assert ok["status"] == "supported"
    assert "fixture_schedule_gt_48h" in ok["disclosed_limitations"]

    # Commit before previous deadline must fail out_of_window
    pre_prev = build_fixture_mirror_record(
        season="2025-26",
        gw=2,
        deadline=dl2,
        prev_deadline=dl1,
        url="https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/s0/data/2025-26/fixtures.csv",
        commit_sha="c" * 40,
        commit_time=datetime(2025, 8, 15, 12, 0, tzinfo=UTC),
        prev_commit_time=datetime(2025, 8, 1, 8, 49, tzinfo=UTC),
        raw_bytes=csv_bytes,
    )
    assert pre_prev["status"] == "out_of_window"

    # GW1 allows pre-season opening release <= 21d
    gw1_ok = build_fixture_mirror_record(
        season="2025-26",
        gw=1,
        deadline=dl1,
        prev_deadline=None,
        url="https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/s0/data/2025-26/fixtures.csv",
        commit_sha="d" * 40,
        commit_time=datetime(2025, 8, 1, 8, 49, tzinfo=UTC),
        prev_commit_time=None,
        raw_bytes=_fixtures_csv(range(1, 7)),
    )
    assert gw1_ok["status"] == "supported"


def test_zero_diff_settled_outcomes_and_causal_chip_calendar(tmp_path: Path) -> None:
    perf = pd.DataFrame(
        [
            {
                "player_id": 1, "fixture_id": 1, "gameweek_id": 1, "minutes": 90, "total_points": 6,
                "goals_scored": 0, "assists": 0, "clean_sheets": 1, "goals_conceded": 0,
                "own_goals": 0, "penalties_saved": 0, "penalties_missed": 0, "yellow_cards": 0,
                "red_cards": 0, "saves": 0, "bonus": 0, "bps": 24, "defensive_contribution": 0,
            },
            {
                "player_id": 218, "fixture_id": 220, "gameweek_id": 22, "minutes": 0, "total_points": -1,
                "goals_scored": 0, "assists": 0, "clean_sheets": 0, "goals_conceded": 0,
                "own_goals": 0, "penalties_saved": 0, "penalties_missed": 0, "yellow_cards": 1,
                "red_cards": 0, "saves": 0, "bonus": 0, "bps": -2, "defensive_contribution": 0,
            },
        ]
    )
    players = pd.DataFrame([{"id": 1, "position_id": 2}, {"id": 218, "position_id": 3}])
    va_df = pd.DataFrame(
        [
            {
                "element": 1, "fixture": 1, "GW": 1, "minutes": 90, "total_points": 6,
                "goals_scored": 0, "assists": 0, "clean_sheets": 1, "goals_conceded": 0,
                "own_goals": 0, "penalties_saved": 0, "penalties_missed": 0, "yellow_cards": 0,
                "red_cards": 0, "saves": 0, "bonus": 0, "bps": 24, "defensive_contribution": 0,
            },
            # Exact duplicate row like vaastav Junior Kroupi GW1-9 must dedup cleanly
            {
                "element": 1, "fixture": 1, "GW": 1, "minutes": 90, "total_points": 6,
                "goals_scored": 0, "assists": 0, "clean_sheets": 1, "goals_conceded": 0,
                "own_goals": 0, "penalties_saved": 0, "penalties_missed": 0, "yellow_cards": 0,
                "red_cards": 0, "saves": 0, "bonus": 0, "bps": 24, "defensive_contribution": 0,
            },
            {
                "element": 218, "fixture": 220, "GW": 22, "minutes": 0, "total_points": -1,
                "goals_scored": 0, "assists": 0, "clean_sheets": 0, "goals_conceded": 0,
                "own_goals": 0, "penalties_saved": 0, "penalties_missed": 0, "yellow_cards": 1,
                "red_cards": 0, "saves": 0, "bonus": 0, "bps": -2, "defensive_contribution": 0,
            },
        ]
    )
    summary = verify_settled_outcomes_zero_diff(va_df, perf, players, season="2025-26")
    assert summary["zero_diff"] is True
    assert summary["duplicate_rows_collapsed"] == 1
    assert summary["ledger_mismatch_rows"] == 0
    assert summary["zero_minute_card_rows"] == 1

    # Conflicting duplicate or total_points diff fails closed
    bad_va = va_df.copy()
    bad_va.loc[2, "total_points"] = 5
    with pytest.raises(ValueError, match="zero-diff|mismatch|residual"):
        verify_settled_outcomes_zero_diff(bad_va, perf, players, season="2025-26")

    # Causal shared chip calendar passes SeasonRules validation
    fx_rows = {gw: pd.DataFrame([{"event": w, "team_h": 1, "team_a": 2} for w in range(gw, min(gw + 6, 39))]) for gw in range(1, 39)}
    cal = build_causal_chip_calendar("2025-26", fixtures_by_gw=fx_rows)
    validate_chip_calendar(get_rules("2025-26"), cal)
    cal24 = build_causal_chip_calendar("2024-25", fixtures_by_gw=fx_rows)
    validate_chip_calendar(get_rules("2024-25"), cal24)


def test_seed_manifest_records_assistant_manager_exclusions(tmp_path: Path) -> None:
    proc = tmp_path / "processed"
    proc.mkdir()
    pd.DataFrame(
        [
            {"id": 1, "code": 100, "position_id": 2},
            {"id": 900, "code": 9000, "position_id": 5},
        ]
    ).to_parquet(proc / "players.parquet", index=False)
    pd.DataFrame(
        [
            {"player_id": 1, "fixture_id": 1, "gameweek_id": 1, "minutes": 90, "total_points": 2},
            {"player_id": 900, "fixture_id": 1, "gameweek_id": 1, "minutes": 90, "total_points": 10},
        ]
    ).to_parquet(proc / "player_performances.parquet", index=False)
    manifest = build_seed_manifest(
        season="2024-25",
        processed_dir=proc,
        vaastav_commits=[{"sha": "a" * 40, "committed_at_utc": "2026-01-02T07:35:49Z", "message": "Schema fix"}],
        upstream_digests={"players_raw.csv": {"sha256": "1" * 64, "bytes": 10}},
    )
    assert manifest["excluded_position_5_count"] == 1
    assert manifest["excluded_position_5_perf_rows"] == 1
    assert manifest["retained_player_count"] == 1
    assert manifest["defensive_contribution_status"] == "inapplicable_native"


def test_load_empirical_manifest_bundle_validates_digests_and_prefix(tmp_path: Path) -> None:
    qroot = tmp_path / "quarantine"
    (qroot / "2025-26/bootstraps").mkdir(parents=True)
    (qroot / "2025-26/fixtures").mkdir(parents=True)
    (qroot / "2025-26/outcomes").mkdir(parents=True)

    dl1 = datetime(2025, 8, 15, 17, 30, tzinfo=UTC)
    bs_raw = _bootstrap_xz(gw=1, deadline=dl1)
    fx_raw = _fixtures_csv(range(1, 7))
    bs_path = qroot / "2025-26/bootstraps/gw01.json.xz"
    fx_path = qroot / "2025-26/fixtures/f1.csv"
    out_path = qroot / "2025-26/outcomes/m.csv"
    bs_path.write_bytes(bs_raw)
    fx_path.write_bytes(fx_raw)
    out_path.write_text(
        "element,fixture,GW,minutes,total_points,yellow_cards,red_cards\n"
        "1,1,1,90,6,0,0\n2,1,1,0,0,0,0\n",
        encoding="utf-8",
    )

    bs_rec = build_bootstrap_mirror_record(
        season="2025-26",
        gw=1,
        deadline=dl1,
        prev_deadline=None,
        url="https://raw.githubusercontent.com/Randdalf/fplcache/sha1/cache/2025/8/15/1252.json.xz",
        repo_path="cache/2025/8/15/1252.json.xz",
        commit_sha="a" * 40,
        commit_time=datetime(2025, 8, 15, 12, 53, tzinfo=UTC),
        raw_bytes=bs_raw,
        local_relpath="2025-26/bootstraps/gw01.json.xz",
    )
    fx_rec = build_fixture_mirror_record(
        season="2025-26",
        gw=1,
        deadline=dl1,
        prev_deadline=None,
        url="https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/s1/data/2025-26/fixtures.csv",
        commit_sha="b" * 40,
        commit_time=datetime(2025, 8, 14, 12, 0, tzinfo=UTC),
        prev_commit_time=None,
        raw_bytes=fx_raw,
        local_relpath="2025-26/fixtures/f1.csv",
    )
    import hashlib

    m_path = tmp_path / "manifest.json"
    m_path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "season": "2025-26",
                "track": "development_mirror",
                "shared_chip_calendar": [{"gameweek": 3, "chip": "triple_captain"}],
                "origins": [
                    {
                        "gw": 1,
                        "deadline_utc": dl1.isoformat(),
                        "origin_admitted": True,
                        "bootstrap": bs_rec,
                        "fixtures": fx_rec,
                        "settled_outcomes": {
                            "finalized_at_utc": (dl1 + timedelta(days=3)).isoformat(),
                            "max_kickoff_utc": (dl1 + timedelta(days=1)).isoformat(),
                            "meets_plus_24h": True,
                            "local_relpath": "2025-26/outcomes/m.csv",
                            "blob_sha256": hashlib.sha256(out_path.read_bytes()).hexdigest(),
                        },
                    }
                ],
            }
        )
    )
    bundle = load_empirical_manifest_bundle(m_path, quarantine_root=qroot, prefix_end_gw=1)
    assert bundle["season"] == "2025-26" and bundle["partial_prefix"] is True and bundle["promotable"] is False
    assert len(bundle["origins"]) == 1

    # Digest tampering raises ValueError
    bs_path.write_bytes(b"corrupted")
    with pytest.raises(ValueError, match="sha256|hash|mismatch"):
        load_empirical_manifest_bundle(m_path, quarantine_root=qroot, prefix_end_gw=1)


def test_acquire_csv_schema_shift_pagination_and_zdiff_merge(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Mocked unit tests for 2024-25 mng_* schema drift, commit pagination, and shared zero-diff preservation."""
    from commands import acquire_empirical_mirrors as acq

    header_42 = [f"c{i}" for i in range(41)] + ["GW"]
    header_42[9], header_42[14], header_42[20] = "element", "fixture", "minutes"
    header_42[21] = "modified"
    header_42[34], header_42[40] = "total_points", "yellow_cards"
    row_gw1 = ["0"] * 42
    row_gw1[9], row_gw1[14], row_gw1[41] = "1", "10", "1"
    row_gw25_49 = ["0"] * 49
    row_gw25_49[9], row_gw25_49[14], row_gw25_49[48] = "2", "250", "25"
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerows([header_42, row_gw1, row_gw25_49])
    raw_csv = buf.getvalue().encode("utf-8")

    assert acq._extract_gws_from_merged_csv(raw_csv) == {1, 25}
    df25 = acq._extract_gw_df_from_merged_csv(raw_csv, 25)
    assert len(df25) == 1 and int(df25.iloc[0]["GW"]) == 25 and int(df25.iloc[0]["element"]) == 2

    # Pagination collects > 100 commits cleanly
    page1 = [{"sha": f"{i:040x}", "commit": {"committer": {"date": f"2025-01-{(i % 28) + 1:02d}T12:00:00Z"}, "message": "p1"}} for i in range(100)]
    page2 = [{"sha": f"{200 + i:040x}", "commit": {"committer": {"date": "2025-05-26T12:00:00Z"}, "message": "p2"}} for i in range(5)]
    commits = acq._vaastav_commits(lambda p: page1 if "&page=1" in p else (page2 if "&page=2" in p else []), "data/2024-25/gws/merged_gw.csv")
    assert len(commits) == 105

    # main() preserves existing season entries in zero_diff_verification.json
    qroot = tmp_path / "mirrors"
    croot = tmp_path / "config"
    qroot.mkdir()
    croot.mkdir()
    (qroot / "zero_diff_verification.json").write_text(json.dumps({"2025-26": {"zero_diff": True, "verified_rows": 29747}}))
    monkeypatch.setattr(acq, "QUARANTINE_ROOT", qroot)
    monkeypatch.setattr(acq, "CONFIG_ROOT", croot)
    monkeypatch.setattr(acq, "acquire_season_mirror", lambda season: (
        {
            "season": season,
            "summary": {
                "bootstrap_admitted_count": 38,
                "fixture_admitted_count": 1,
                "contiguous_admitted_prefix_end_gw": 0,
                "settled_outcomes_zero_diff": True,
                "verified_outcome_rows": 27283,
            },
        },
        {"season": season, "zero_diff": True, "verified_rows": 27283},
    ))
    monkeypatch.setattr(acq, "acquire_seed_manifest", lambda: {
        "players_total": 804,
        "excluded_position_5_count": 20,
        "retained_player_count": 784,
        "defensive_contribution_status": "inapplicable_native",
    })
    monkeypatch.setattr("sys.argv", ["acq", "--seasons", "2024-25"])
    acq.main()
    merged_zdiff = json.loads((qroot / "zero_diff_verification.json").read_text())
    assert "2025-26" in merged_zdiff and "2024-25" in merged_zdiff

    # Duplicate row with NaN must fail rather than coerce to 0; traversal fails closed
    perf = pd.DataFrame([{"player_id": 1, "fixture_id": 1, "gameweek_id": 1, "minutes": 90, "total_points": 6, "goals_scored": 0, "assists": 0, "clean_sheets": 1, "goals_conceded": 0, "own_goals": 0, "penalties_saved": 0, "penalties_missed": 0, "yellow_cards": 0, "red_cards": 0, "saves": 0, "bonus": 0, "bps": 24, "defensive_contribution": 0}])
    players = pd.DataFrame([{"id": 1, "position_id": 2}])
    va_nan = pd.DataFrame([
        {"element": 1, "fixture": 1, "GW": 1, "minutes": 90, "total_points": 6, "goals_scored": 0, "assists": 0, "clean_sheets": 1, "goals_conceded": 0, "own_goals": 0, "penalties_saved": 0, "penalties_missed": 0, "yellow_cards": 0, "red_cards": 0, "saves": 0, "bonus": 0, "bps": 24, "defensive_contribution": 0},
        {"element": 1, "fixture": 1, "GW": 1, "minutes": 90, "total_points": 6, "goals_scored": 0, "assists": 0, "clean_sheets": 1, "goals_conceded": 0, "own_goals": 0, "penalties_saved": 0, "penalties_missed": 0, "yellow_cards": 0, "red_cards": 0, "saves": 0, "bonus": None, "bps": 24, "defensive_contribution": 0},
    ])
    with pytest.raises(ValueError, match="Conflicting|missing|NaN|null|cannot"):
        verify_settled_outcomes_zero_diff(va_nan, perf, players, season="2025-26")

    bad_manifest = tmp_path / "trav_manifest.json"
    bad_manifest.write_text(json.dumps({
        "schema_version": 2,
        "season": "2025-26",
        "track": "development_mirror",
        "origins": [{"gw": 1, "origin_admitted": True, "bootstrap": {"status": "supported", "local_relpath": "../secret", "blob_sha256": "a" * 64}, "fixtures": {"status": "supported"}, "settled_outcomes": {"meets_plus_24h": True}}],
    }))
    with pytest.raises(ValueError, match="traversal|Missing"):
        load_empirical_manifest_bundle(bad_manifest, quarantine_root=qroot, prefix_end_gw=1)


def test_chip_calendar_consumes_bootstrap_chips_and_bundle_verifies_table_sha256(tmp_path: Path) -> None:
    """build_causal_chip_calendar respects bootstrap[t]['chips'] bounds and manifest bundle checks table_sha256."""
    fx_rows = {gw: pd.DataFrame([{"event": w, "team_h": 1, "team_a": 2} for w in range(gw, min(gw + 6, 39))]) for gw in range(1, 39)}
    chips_bs = [
        {"name": "wildcard", "start_event": 9, "stop_event": 19},
        {"name": "freehit", "start_event": 15, "stop_event": 19},
        {"name": "bboost", "start_event": 10, "stop_event": 19},
        {"name": "3xc", "start_event": 2, "stop_event": 19},
        {"name": "wildcard", "start_event": 25, "stop_event": 38},
    ]
    cal = build_causal_chip_calendar("2025-26", fixtures_by_gw=fx_rows, bootstrap_chips=chips_bs)
    cal_map = {c: [g for g, ch in cal if ch == c] for _, c in cal}
    assert all(9 <= g <= 19 for g in cal_map["wildcard"] if g <= 19)
    assert all(15 <= g <= 19 for g in cal_map["free_hit"] if g <= 19)

    qroot = tmp_path / "quarantine2"
    (qroot / "2025-26/bootstraps").mkdir(parents=True)
    (qroot / "2025-26/fixtures").mkdir(parents=True)
    dl1 = datetime(2025, 8, 15, 17, 30, tzinfo=UTC)
    bs_raw = _bootstrap_xz(gw=1, deadline=dl1)
    fx_raw = _fixtures_csv(range(1, 7))
    (qroot / "2025-26/bootstraps/gw01.json.xz").write_bytes(bs_raw)
    (qroot / "2025-26/fixtures/f1.csv").write_bytes(fx_raw)
    bs_rec = build_bootstrap_mirror_record(
        season="2025-26", gw=1, deadline=dl1, prev_deadline=None,
        url="https://raw.githubusercontent.com/Randdalf/fplcache/sha1/cache/2025/8/15/1252.json.xz",
        repo_path="cache/2025/8/15/1252.json.xz", commit_sha="a" * 40,
        commit_time=datetime(2025, 8, 15, 12, 53, tzinfo=UTC), raw_bytes=bs_raw, local_relpath="2025-26/bootstraps/gw01.json.xz",
    )
    fx_rec = build_fixture_mirror_record(
        season="2025-26", gw=1, deadline=dl1, prev_deadline=None,
        url="https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/s1/data/2025-26/fixtures.csv",
        commit_sha="b" * 40, commit_time=datetime(2025, 8, 14, 12, 0, tzinfo=UTC),
        prev_commit_time=None, raw_bytes=fx_raw, local_relpath="2025-26/fixtures/f1.csv",
    )
    fx_rec["table_sha256"] = "0" * 64
    bad_tbl_manifest = tmp_path / "bad_tbl.json"
    bad_tbl_manifest.write_text(json.dumps({
        "schema_version": 2, "season": "2025-26", "track": "development_mirror",
        "origins": [{"gw": 1, "origin_admitted": True, "bootstrap": bs_rec, "fixtures": fx_rec, "settled_outcomes": {"meets_plus_24h": True}}],
    }))
    with pytest.raises(ValueError, match="table_sha256"):
        load_empirical_manifest_bundle(bad_tbl_manifest, quarantine_root=qroot, prefix_end_gw=1)

    # Bootstrap with news_added after capture_upper fails sanitization inside load_empirical_manifest_bundle
    import hashlib
    bad_payload = json.loads(lzma.decompress(bs_raw).decode("utf-8"))
    bad_payload["elements"][0]["news_added"] = (dl1 + timedelta(hours=1)).isoformat()
    bad_raw = lzma.compress(json.dumps(bad_payload).encode("utf-8"))
    (qroot / "2025-26/bootstraps/gw01_bad.json.xz").write_bytes(bad_raw)
    bad_bs_rec = {
        **bs_rec,
        "local_relpath": "2025-26/bootstraps/gw01_bad.json.xz",
        "blob_sha256": hashlib.sha256(bad_raw).hexdigest(),
        "decompressed_sha256": hashlib.sha256(lzma.decompress(bad_raw)).hexdigest(),
        "table_sha256": None,
    }
    fx_rec_ok = dict(fx_rec, table_sha256=None)
    bad_san_manifest = tmp_path / "bad_san.json"
    bad_san_manifest.write_text(json.dumps({
        "schema_version": 2, "season": "2025-26", "track": "development_mirror",
        "origins": [{"gw": 1, "origin_admitted": True, "bootstrap": bad_bs_rec, "fixtures": fx_rec_ok, "settled_outcomes": {"meets_plus_24h": True}}],
    }))
    with pytest.raises(ValueError, match="sanitization|news_added"):
        load_empirical_manifest_bundle(bad_san_manifest, quarantine_root=qroot, prefix_end_gw=1)

    for bad_season in ("2026-27", "2023-24"):
        bad_season_manifest = tmp_path / f"bad_season_{bad_season}.json"
        bad_season_manifest.write_text(json.dumps({
            "schema_version": 2, "season": bad_season, "track": "development_mirror",
            "origins": [{"gw": 1, "origin_admitted": True, "bootstrap": {**bs_rec, "table_sha256": None}, "fixtures": fx_rec_ok, "settled_outcomes": {"meets_plus_24h": True}}],
        }))
        with pytest.raises(ValueError, match="prohibits"):
            load_empirical_manifest_bundle(bad_season_manifest, quarantine_root=qroot, prefix_end_gw=1)

    spoof_bs = {**bs_rec, "table_sha256": None, "url": "https://evil.example/Randdalf/fplcache/cache/2025/8/15/1252.json.xz"}
    bad_url_manifest = tmp_path / "bad_url.json"
    bad_url_manifest.write_text(json.dumps({
        "schema_version": 2, "season": "2025-26", "track": "development_mirror",
        "origins": [{"gw": 1, "origin_admitted": True, "bootstrap": spoof_bs, "fixtures": fx_rec_ok, "settled_outcomes": {"meets_plus_24h": True}}],
    }))
    with pytest.raises(ValueError, match="approved GitHub HTTPS"):
        load_empirical_manifest_bundle(bad_url_manifest, quarantine_root=qroot, prefix_end_gw=1)


def test_acquire_seed_manifest_accepts_prior_seed_only_season(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """acquire_seed_manifest accepts prior_seed_only seasons (2023-24) under SeasonLifecycle."""
    from commands.acquire_empirical_mirrors import acquire_seed_manifest

    proc_dir = tmp_path / "data/archive/2023-24/processed"
    proc_dir.mkdir(parents=True)
    pd.DataFrame([{"id": 1, "position_id": 2}, {"id": 900, "position_id": 5}]).to_parquet(
        proc_dir / "players.parquet", index=False
    )
    pd.DataFrame(
        [{"player_id": 1, "fixture_id": 1, "gameweek_id": 1, "minutes": 90, "total_points": 6}]
    ).to_parquet(proc_dir / "player_performances.parquet", index=False)

    monkeypatch.setattr("commands.acquire_empirical_mirrors.ROOT", tmp_path)
    qroot = tmp_path / "q"
    pin_sha = "a" * 40
    seed_dir = qroot / "2023-24/seed" / pin_sha[:10]
    seed_dir.mkdir(parents=True)
    for fname in ("players_raw.csv", "teams.csv", "fixtures.csv", "gws_merged_gw.csv"):
        (seed_dir / fname).write_text("col\n1\n", encoding="utf-8")

    def _fake_gh_api(_path: str) -> Any:
        return [
            {"sha": pin_sha, "commit": {"committer": {"date": "2024-06-01T12:00:00Z"}, "message": "final"}},
            {"sha": "b" * 40, "commit": {"committer": {"date": "2024-05-20T12:00:00Z"}, "message": "prev"}},
        ]

    manifest = acquire_seed_manifest(season="2023-24", quarantine_root=qroot, gh_api_fn=_fake_gh_api)
    assert manifest["season"] == "2023-24"
    assert manifest["role"] == "prior_season_seed"
    assert manifest["defensive_contribution_status"] == "inapplicable_native"
    assert manifest["retained_player_count"] == 1
