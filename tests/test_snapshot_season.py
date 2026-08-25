import json
from pathlib import Path

from commands.snapshot_season import main, process_season_archive


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
