from __future__ import annotations

import json
import lzma
import runpy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

PILOT = runpy.run_path(str(Path(__file__).resolve().parents[1] /
                         "docs/research/backtesting-promotion-foundation/readiness_source_pilot.py"))


def test_public_source_boundary() -> None:
    validate = PILOT["validate_url"]
    validate("https://raw.githubusercontent.com/Randdalf/fplcache/abc/cache/file")
    for url in ("http://raw.githubusercontent.com/Randdalf/fplcache/abc/file",
                "https://api.github.com/repos/other/project/commits/a",
                "https://example.com/Randdalf/fplcache/file"):
        with pytest.raises(ValueError, match="approved"):
            validate(url)


def test_download_stops_at_aggregate_cap(tmp_path: Path) -> None:
    fetcher = PILOT["Fetcher"](tmp_path / "run")
    fetcher.bytes = PILOT["MAX_BYTES"] - 3

    class Response:
        def __enter__(self) -> Response:
            return self

        def __exit__(self, *args: Any) -> None:
            pass

        def read(self, size: int) -> bytes:
            assert size == 3
            return b"abc"

    class Opener:
        def open(self, *args: Any, **kwargs: Any) -> Response:
            return Response()

    fetcher.opener = Opener()
    assert fetcher.fetch("cap", "https://raw.githubusercontent.com/Randdalf/fplcache/a/file") is None
    assert fetcher.bytes == PILOT["MAX_BYTES"]
    assert (fetcher.output / "01-cap.partial").read_bytes() == b"abc"
    with pytest.raises(RuntimeError, match="cap"):
        fetcher.fetch("again", "https://raw.githubusercontent.com/Randdalf/fplcache/a/file")
    assert fetcher.count == 1
    with pytest.raises(FileExistsError):
        PILOT["Fetcher"](fetcher.output)


def test_payload_audit_ignores_outcomes_and_detects_defects() -> None:
    player = {"id": 7, "team": 1, "element_type": 2, "now_cost": -1,
              "selected_by_percent": "101", "status": None, "total_points": "DO NOT READ"}
    raw = lzma.compress(json.dumps({"elements": [player, player], "events": [
        {"id": 2, "deadline_time": "2025-08-22T17:30:00Z", "is_next": True}]}).encode())
    audit = PILOT["bootstrap_audit"](raw, 2)
    assert audit["duplicate_ids"] == 1
    assert audit["invalid_price_ownership_position_rows"] == 2
    assert audit["missing_required_cells"] == 2
    assert "DO NOT READ" not in json.dumps(audit)


def test_fixture_input_window_excludes_outcome_values() -> None:
    audit = PILOT["fixture_audit"](b"id,event,team_h,team_a,kickoff_time,team_h_score\n"
                                   b"1,1,2,3,time,999\n2,2,2,3,,888\n")
    assert audit["window_rows"] == 1
    assert audit["missing_window_input_cells"] == 1
    assert "888" not in json.dumps(audit)


def test_resume_keeps_original_request_budget(tmp_path: Path) -> None:
    output = tmp_path / "run"
    output.mkdir()
    (output / "summary.json").write_text(json.dumps({
        "requests": 30, "downloaded_bytes": 123,
        "attempts": [{"retrieval_utc": datetime.now(timezone.utc).isoformat()}]}))
    resumed = PILOT["Fetcher"](output, resume=True)
    assert resumed.bytes == 123
    with pytest.raises(RuntimeError, match="cap"):
        resumed.fetch("never", "https://raw.githubusercontent.com/Randdalf/fplcache/a/file")
    assert resumed.count == 30
