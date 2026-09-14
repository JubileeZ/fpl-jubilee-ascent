import json
from pathlib import Path

from commands.snapshot_season import main, process_season_archive
from features.expected_role_prior import LIVE_SEASON
from features.season_archive import pin_season_archive


def test_from_raw_dir_writes_processed_archive(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "bootstrap_static.json").write_text(json.dumps({
        "teams": [{"id": 1, "name": "Arsenal", "short_name": "ARS", "strength": 4}],
        "events": [{"id": 1, "name": "Gameweek 1", "deadline_time": "2025-08-15T17:30:00Z", "finished": True, "is_current": True}],
        "elements": [{
            "id": 1, "code": 99, "first_name": "A", "second_name": "B", "web_name": "AB",
            "team": 1, "element_type": 3, "now_cost": 50, "status": "a",
        }],
    }), encoding="utf-8")
    (raw / "fixtures_all.json").write_text(json.dumps([{
        "id": 1, "event": 1, "kickoff_time": "2025-08-15T19:00:00Z",
        "team_h": 1, "team_a": 2, "finished": True, "started": True,
        "team_h_score": 1, "team_a_score": 0, "team_h_difficulty": 2, "team_a_difficulty": 4,
    }]), encoding="utf-8")
    archive_root = tmp_path / "archive"
    processed = process_season_archive("2024-25", raw, archive_root=archive_root)
    assert processed == archive_root / "2024-25" / "processed"
    assert (processed / "players.parquet").exists()
    assert (processed / "fixtures.parquet").exists()


def test_cli_from_raw_dir(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "bootstrap_static.json").write_text(json.dumps({
        "teams": [{"id": 1, "name": "Arsenal", "short_name": "ARS", "strength": 4}],
        "events": [{"id": 1, "name": "Gameweek 1", "deadline_time": "2025-08-15T17:30:00Z", "finished": True, "is_current": True}],
        "elements": [{"id": 1, "first_name": "A", "second_name": "B", "web_name": "AB", "team": 1, "element_type": 3, "now_cost": 50, "status": "a"}],
    }), encoding="utf-8")
    (raw / "fixtures_all.json").write_text(json.dumps([{
        "id": 1, "event": 1, "team_h": 1, "team_a": 2, "team_h_difficulty": 2, "team_a_difficulty": 4,
        "finished": True, "started": True,
    }]), encoding="utf-8")
    archive_root = tmp_path / "archive"
    assert main(["--season", "2024-25", "--from-raw-dir", str(raw), "--archive-root", str(archive_root)]) == 0
    assert (archive_root / "2024-25" / "processed" / "clubs.parquet").exists()


def test_cli_rejects_live_fetch_for_other_seasons() -> None:
    try:
        main(["--season", "2024-25"])
    except ValueError as exc:
        assert "from-raw-dir" in str(exc)
    else:
        raise AssertionError("expected live-fetch rejection")


def test_pin_season_archive_copies_raw_and_processed(tmp_path: Path) -> None:
    raw = tmp_path / "data" / "raw"
    processed = tmp_path / "data" / "processed"
    raw.mkdir(parents=True)
    processed.mkdir(parents=True)
    (raw / "bootstrap_static.json").write_text("{}", encoding="utf-8")
    (processed / "players.parquet").write_bytes(b"parquet-bytes")
    archive_root = tmp_path / "data" / "archive"
    pin = pin_season_archive(
        LIVE_SEASON,
        raw,
        processed,
        archive_root=archive_root,
    )
    assert pin.processed_dir == archive_root / LIVE_SEASON / "processed"
    assert (archive_root / LIVE_SEASON / "raw" / "bootstrap_static.json").read_text(encoding="utf-8") == "{}"
    assert (archive_root / LIVE_SEASON / "processed" / "players.parquet").read_bytes() == b"parquet-bytes"
    assert pin.changed is True


def test_pin_season_archive_excludes_user_squad_files(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    processed = tmp_path / "processed"
    raw.mkdir()
    processed.mkdir()
    (raw / "bootstrap_static.json").write_text('{"teams": []}', encoding="utf-8")
    (raw / "fixtures_all.json").write_text("[]", encoding="utf-8")
    (raw / "element_summary_1.json").write_text('{"history": []}', encoding="utf-8")
    (raw / "me.json").write_text('{"email": "secret"}', encoding="utf-8")
    (raw / "my_team_822158.json").write_text('{"picks": []}', encoding="utf-8")
    (raw / "entry_822158.json").write_text("{}", encoding="utf-8")
    (processed / "players.parquet").write_bytes(b"players")
    (processed / "price_history.parquet").write_bytes(b"prices")
    (processed / "user_picks.parquet").write_bytes(b"picks")
    (processed / "user_state.parquet").write_bytes(b"state")
    (processed / "user_chips.parquet").write_bytes(b"chips")
    dest_raw = tmp_path / "archive" / LIVE_SEASON / "raw"
    dest_processed = tmp_path / "archive" / LIVE_SEASON / "processed"
    dest_raw.mkdir(parents=True)
    dest_processed.mkdir(parents=True)
    (dest_raw / "me.json").write_text('{"stale": true}', encoding="utf-8")
    (dest_raw / "my_team_6025459.json").write_text("{}", encoding="utf-8")
    (dest_processed / "user_picks.parquet").write_bytes(b"stale")
    pin = pin_season_archive(LIVE_SEASON, raw, processed, archive_root=tmp_path / "archive")
    assert (pin.processed_dir / "players.parquet").read_bytes() == b"players"
    assert (pin.processed_dir / "price_history.parquet").read_bytes() == b"prices"
    assert (pin.processed_dir.parent / "raw" / "bootstrap_static.json").exists()
    assert (pin.processed_dir.parent / "raw" / "element_summary_1.json").exists()
    assert not (pin.processed_dir.parent / "raw" / "me.json").exists()
    assert not (pin.processed_dir.parent / "raw" / "my_team_822158.json").exists()
    assert not (pin.processed_dir.parent / "raw" / "my_team_6025459.json").exists()
    assert not (pin.processed_dir.parent / "raw" / "entry_822158.json").exists()
    assert not (pin.processed_dir / "user_picks.parquet").exists()
    assert not (pin.processed_dir / "user_state.parquet").exists()
    assert not (pin.processed_dir / "user_chips.parquet").exists()


def test_official_content_hash_ignores_json_key_order_and_user_files(tmp_path: Path) -> None:
    raw_a = tmp_path / "raw_a"
    raw_b = tmp_path / "raw_b"
    processed = tmp_path / "processed"
    for raw in (raw_a, raw_b):
        raw.mkdir()
    processed.mkdir()
    (processed / "players.parquet").write_bytes(b"players")
    (raw_a / "bootstrap_static.json").write_text('{"b": 1, "a": 2}', encoding="utf-8")
    (raw_a / "me.json").write_text('{"email": "a"}', encoding="utf-8")
    (raw_b / "bootstrap_static.json").write_text('{"a": 2, "b": 1}', encoding="utf-8")
    (raw_b / "me.json").write_text('{"email": "b"}', encoding="utf-8")
    first = pin_season_archive(LIVE_SEASON, raw_a, processed, archive_root=tmp_path / "arch_a")
    second = pin_season_archive(LIVE_SEASON, raw_b, processed, archive_root=tmp_path / "arch_b")
    assert first.content_hash == second.content_hash
    assert len(first.content_hash) == 64


def test_second_pin_of_same_official_raw_is_unchanged(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    processed = tmp_path / "processed"
    raw.mkdir()
    processed.mkdir()
    (raw / "bootstrap_static.json").write_text('{"teams": [1]}', encoding="utf-8")
    (processed / "players.parquet").write_bytes(b"players")
    archive_root = tmp_path / "archive"
    first = pin_season_archive(LIVE_SEASON, raw, processed, archive_root=archive_root)
    (processed / "players.parquet").write_bytes(b"rewritten-parquet")
    second = pin_season_archive(LIVE_SEASON, raw, processed, archive_root=archive_root)
    assert first.changed is True
    assert second.changed is False
    assert first.content_hash == second.content_hash


def test_pin_reports_changed_when_official_raw_moves(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    processed = tmp_path / "processed"
    raw.mkdir()
    processed.mkdir()
    (raw / "bootstrap_static.json").write_text('{"teams": []}', encoding="utf-8")
    (processed / "players.parquet").write_bytes(b"players")
    archive_root = tmp_path / "archive"
    first = pin_season_archive(LIVE_SEASON, raw, processed, archive_root=archive_root)
    (raw / "bootstrap_static.json").write_text('{"teams": [{"id": 1}]}', encoding="utf-8")
    second = pin_season_archive(LIVE_SEASON, raw, processed, archive_root=archive_root)
    assert first.changed is True
    assert second.changed is True
    assert first.content_hash != second.content_hash


def test_pin_refuses_frozen_completed_season(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    processed = tmp_path / "processed"
    raw.mkdir()
    processed.mkdir()
    (raw / "bootstrap_static.json").write_text("{}", encoding="utf-8")
    (processed / "players.parquet").write_bytes(b"players")
    frozen = "2024-25" if LIVE_SEASON != "2024-25" else "2023-24"
    try:
        pin_season_archive(frozen, raw, processed, archive_root=tmp_path / "archive")
    except ValueError as exc:
        assert "frozen" in str(exc)
        assert frozen in str(exc)
    else:
        raise AssertionError("expected frozen Season Archive refusal")
