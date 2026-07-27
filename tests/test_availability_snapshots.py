from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

import commands.capture_availability_snapshot as capture_command
from features.availability_snapshots import (
    is_inside_capture_window,
    resolve_latest_snapshot,
    write_availability_snapshot,
)


DEADLINE = datetime(2026, 8, 1, 12, tzinfo=UTC)
PLAYERS = pd.DataFrame([{"id": 1, "club_id": 10, "chance_of_playing_next_round": 50}])
CLUBS = pd.DataFrame([{"id": 10, "strength": 4}])
FIXTURES = pd.DataFrame([{"id": 20, "event": 1, "team_h": 10, "team_a": 11}])


def test_capture_window_boundaries():
    assert is_inside_capture_window(DEADLINE, DEADLINE - timedelta(hours=48))
    assert is_inside_capture_window(DEADLINE, DEADLINE - timedelta(hours=1))
    assert not is_inside_capture_window(DEADLINE, DEADLINE)
    assert not is_inside_capture_window(DEADLINE, DEADLINE - timedelta(hours=49))


def test_writer_skips_unchanged_content_and_resolver_uses_latest_before_deadline(tmp_path: Path):
    first = write_availability_snapshot(
        tmp_path,
        "2026-27",
        1,
        DEADLINE,
        DEADLINE - timedelta(hours=24),
        PLAYERS,
        CLUBS,
        FIXTURES,
    )
    assert first is not None

    unchanged = write_availability_snapshot(
        tmp_path,
        "2026-27",
        1,
        DEADLINE,
        DEADLINE - timedelta(hours=12),
        PLAYERS,
        CLUBS,
        FIXTURES,
    )
    assert unchanged is None

    changed_players = PLAYERS.assign(chance_of_playing_next_round=0)
    changed = write_availability_snapshot(
        tmp_path,
        "2026-27",
        1,
        DEADLINE,
        DEADLINE - timedelta(hours=6),
        changed_players,
        CLUBS,
        FIXTURES,
    )
    assert changed is not None

    resolved = resolve_latest_snapshot(tmp_path, "2026-27", 1, DEADLINE)
    assert resolved is not None
    assert resolved["players"].iloc[0]["chance_of_playing_next_round"] == 0
    assert resolved["metadata"]["content_hash"] != ""

    assert resolve_latest_snapshot(tmp_path, "2026-27", 1, DEADLINE - timedelta(hours=7)) is None
    assert resolve_latest_snapshot(tmp_path, "2026-27", 1, DEADLINE - timedelta(hours=25)) is None


def test_resolver_rejects_tampered_snapshot_content(tmp_path: Path):
    package = write_availability_snapshot(
        tmp_path,
        "2026-27",
        1,
        DEADLINE,
        DEADLINE - timedelta(hours=24),
        PLAYERS,
        CLUBS,
        FIXTURES,
    )
    assert package is not None
    PLAYERS.assign(chance_of_playing_next_round=0).to_parquet(package / "players.parquet", index=False)

    assert resolve_latest_snapshot(tmp_path, "2026-27", 1, DEADLINE) is None


def test_writer_removes_failed_temporary_package(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    def fail_to_parquet(self: pd.DataFrame, *args: object, **kwargs: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(pd.DataFrame, "to_parquet", fail_to_parquet)

    with pytest.raises(OSError, match="disk full"):
        write_availability_snapshot(
            tmp_path,
            "2026-27",
            1,
            DEADLINE,
            DEADLINE - timedelta(hours=24),
            PLAYERS,
            CLUBS,
            FIXTURES,
        )

    assert not list(tmp_path.glob("2026-27/GW1/.*.tmp-*"))


@pytest.mark.asyncio
async def test_capture_command_uses_mocked_public_endpoints(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    async def bootstrap(*args: object, **kwargs: object) -> dict[str, object]:
        return {
            "events": [
                {
                    "id": 1,
                    "is_next": True,
                    "deadline_time": "2026-08-01T12:00:00Z",
                }
            ],
            "elements": [{"id": 1, "team": 10, "element_type": 2}],
            "teams": [{"id": 10, "strength": 4}],
        }

    async def fixtures(*args: object, **kwargs: object) -> list[dict[str, object]]:
        return [{"id": 20, "event": 1, "team_h": 10, "team_a": 11}]

    monkeypatch.setattr(capture_command, "fetch_bootstrap_static", bootstrap)
    monkeypatch.setattr(capture_command, "fetch_gameweek_fixtures", fixtures)

    package = await capture_command.capture(
        "2026-27",
        tmp_path,
        captured_at=datetime(2026, 8, 1, 0, tzinfo=UTC),
    )

    assert package is not None
    assert (package / "players.parquet").exists()
    assert (package / "fixtures.parquet").exists()
