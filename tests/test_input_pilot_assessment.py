from __future__ import annotations

import csv
import hashlib
import io
import json
import lzma
from pathlib import Path
from typing import Any

import pytest

from backtesting.input_pilot import assess_retained_pilot


def retained(tmp_path: Path) -> Path:
    player = {"id": 1, "team": 1, "element_type": 2, "now_cost": 50,
              "status": "a", "selected_by_percent": "2.0", "chance_of_playing_next_round": None,
              "total_points": "OUTCOME MUST STAY OUT"}
    bootstrap = lzma.compress(json.dumps({"elements": [player], "teams": [{"id": 1}, {"id": 2}],
        "events": [{"id": 1, "deadline_time": "2025-08-15T17:30:00Z"},
                   {"id": 2, "deadline_time": "2025-08-22T17:30:00Z"}]}).encode())
    text = io.StringIO()
    writer = csv.DictWriter(text, fieldnames=("id", "event", "team_h", "team_a", "kickoff_time"))
    writer.writeheader()
    for gw in range(2, 8):
        writer.writerow({"id": gw, "event": gw, "team_h": 1, "team_a": 2, "kickoff_time": "2025-08-23T19:00:00Z"})
    attempts: list[dict[str, Any]] = []
    for index, (label, raw) in enumerate((("opening_bootstrap", bootstrap),
            ("origin_bootstrap_pilot", bootstrap), ("fixture_pilot", text.getvalue().encode())), 1):
        (tmp_path / f"{index:02}-{label}.raw").write_bytes(raw)
        attempts.append({"attempt": index, "label": label, "status": "recovered", "sha256": hashlib.sha256(raw).hexdigest()})
    (tmp_path / "summary.json").write_text(json.dumps({"origin": "2025-26 GW2", "attempts": attempts}))
    return tmp_path


def test_retained_pilot_reports_blockers_without_promoting(tmp_path: Path) -> None:
    assess = assess_retained_pilot
    report = assess(retained(tmp_path))
    fields = {row["name"]: row for row in report["fields"]}
    assert fields["availability"]["status"] == "unresolved"
    assert "capture_bounds_missing" in fields["availability"]["reasons"]
    assert fields["prior_season_training"]["status"] == "unresolved"
    assert report["promotion_authority"] is False
    assert "OUTCOME MUST STAY OUT" not in json.dumps(report)
    (tmp_path / "02-origin_bootstrap_pilot.raw").write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="hash"):
        assess(tmp_path)
