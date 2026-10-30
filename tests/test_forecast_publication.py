"""Windows atomic forecast publication retries preserve cache verification."""

from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from backtesting import forecast_store
from backtesting.data_admission import require_input
from promotion_evidence_fixture import CANDIDATE, _context


def _windows_lock(code: int) -> PermissionError:
    error = PermissionError("synthetic Windows file lock")
    setattr(error, "winerror", code)
    return error


def test_transient_windows_lock_retries_then_loads_verified_forecast(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    request, catalog, training_authority = _context("2024-25", 1)
    capability = require_input(request, catalog, "2024-25", 1)
    original = forecast_store.os.rename
    attempts: list[int] = []
    def rename(source: Any, destination: Any) -> None:
        attempts.append(1)
        if len(attempts) <= 2:
            raise _windows_lock(32)
        original(source, destination)
    monkeypatch.setattr(forecast_store.os, "rename", rename)
    monkeypatch.setattr(forecast_store.time, "sleep", lambda seconds: None)
    forecast_id, generated, hit = forecast_store.generate_forecast(tmp_path, capability, request, catalog, training_authority, CANDIDATE)
    restored, _ = forecast_store.load_forecast_verified(tmp_path, forecast_id, capability, request, catalog, training_authority, CANDIDATE)
    assert len(attempts) == 3 and not hit
    pd.testing.assert_frame_equal(generated, restored)


def test_permanent_windows_lock_retains_failed_attempt_without_false_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    request, catalog, training_authority = _context("2024-25", 1)
    capability = require_input(request, catalog, "2024-25", 1)
    calls: list[int] = []
    def denied(source: Any, destination: Any) -> None:
        calls.append(1)
        raise _windows_lock(5)
    monkeypatch.setattr(forecast_store.os, "rename", denied)
    monkeypatch.setattr(forecast_store.time, "sleep", lambda seconds: None)
    with pytest.raises(PermissionError):
        forecast_store.generate_forecast(tmp_path, capability, request, catalog, training_authority, CANDIDATE)
    assert len(calls) == 5
    assert len(list((tmp_path / "attempts").glob("*/failed.json"))) == 1
    assert not list((tmp_path / "attempts").glob("*/complete.json"))
    assert all(path.name.startswith(".stage-") for path in (tmp_path / "forecasts").iterdir())


def test_windows_existing_destination_never_overwrites_conflicting_content(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    request, catalog, training_authority = _context("2024-25", 1)
    capability = require_input(request, catalog, "2024-25", 1)
    def competitor(source: Any, destination: Any) -> None:
        destination.mkdir()
        (destination / "forecast.csv").write_bytes(b"conflicting concurrent content")
        raise _windows_lock(5)
    monkeypatch.setattr(forecast_store.os, "rename", competitor)
    with pytest.raises(ValueError, match="Concurrent forecast content mismatch"):
        forecast_store.generate_forecast(tmp_path, capability, request, catalog, training_authority, CANDIDATE)
    published = next(path for path in (tmp_path / "forecasts").iterdir() if not path.name.startswith(".stage-"))
    assert (published / "forecast.csv").read_bytes() == b"conflicting concurrent content"
    assert len(list((tmp_path / "attempts").glob("*/failed.json"))) == 1
