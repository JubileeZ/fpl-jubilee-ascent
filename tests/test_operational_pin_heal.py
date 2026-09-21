"""Live Season Pin heals Official Operational tables on resolve (ADR 0036)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from features.builder import resolve_operational_processed_dir
from features.expected_role_prior import LIVE_SEASON
from features.season_archive import OFFICIAL_PROCESSED_FILES


def _write_parquet(path: Path, marker: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"id": marker}]).to_parquet(path, index=False)


def _pin_dir(root: Path) -> Path:
    return root / "data" / "archive" / LIVE_SEASON / "processed"


def _processed_dir(root: Path) -> Path:
    return root / "data" / "processed"


def _write_official_set(directory: Path, marker: int) -> None:
    for name in sorted(OFFICIAL_PROCESSED_FILES):
        _write_parquet(directory / name, marker)


def test_resolve_heals_stale_processed_official_from_pin(tmp_path: Path) -> None:
    pin = _pin_dir(tmp_path)
    processed = _processed_dir(tmp_path)
    _write_official_set(pin, marker=10)
    _write_official_set(processed, marker=1)
    # Stale hybrid: users often keep leftovers after pin pull
    pd.DataFrame([{"id": 99}]).to_parquet(processed / "user_picks.parquet", index=False)

    resolved = resolve_operational_processed_dir(tmp_path)

    assert resolved == processed
    assert pd.read_parquet(processed / "players.parquet").iloc[0]["id"] == 10
    assert pd.read_parquet(processed / "player_performances.parquet").iloc[0]["id"] == 10
    assert pd.read_parquet(processed / "user_picks.parquet").iloc[0]["id"] == 99


def test_resolve_copies_pin_when_processed_missing(tmp_path: Path) -> None:
    pin = _pin_dir(tmp_path)
    processed = _processed_dir(tmp_path)
    _write_official_set(pin, marker=7)

    resolved = resolve_operational_processed_dir(tmp_path)

    assert resolved == processed
    assert pd.read_parquet(processed / "players.parquet").iloc[0]["id"] == 7
    assert not (processed / "user_picks.parquet").exists()


def test_resolve_noop_when_processed_matches_pin(tmp_path: Path) -> None:
    pin = _pin_dir(tmp_path)
    processed = _processed_dir(tmp_path)
    _write_official_set(pin, marker=5)
    _write_official_set(processed, marker=5)
    before = (processed / "players.parquet").read_bytes()

    resolved = resolve_operational_processed_dir(tmp_path)

    assert resolved == processed
    assert (processed / "players.parquet").read_bytes() == before


def test_resolve_uses_processed_when_pin_absent(tmp_path: Path) -> None:
    processed = _processed_dir(tmp_path)
    for name in ("players.parquet", "player_performances.parquet", "fixtures.parquet"):
        _write_parquet(processed / name, 3)

    assert resolve_operational_processed_dir(tmp_path) == processed
