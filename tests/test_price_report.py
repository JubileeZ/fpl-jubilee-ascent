from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from commands.price_report import append_price_snapshot, build_price_change_report


def _write_price_inputs(processed_dir: Path, prices: list[int]) -> None:
    pd.DataFrame([
        {"id": 1, "web_name": "Riser", "club_id": 1, "now_cost": prices[0]},
        {"id": 2, "web_name": "Faller", "club_id": 2, "now_cost": prices[1]},
    ]).to_parquet(processed_dir / "players.parquet", index=False)
    pd.DataFrame([
        {"id": 2, "is_current": True, "is_next": False},
    ]).to_parquet(processed_dir / "gameweeks.parquet", index=False)


def test_price_history_appends_snapshots_and_reports_changes(tmp_path: Path) -> None:
    processed = tmp_path / "processed"
    processed.mkdir()
    _write_price_inputs(processed, [100, 100])
    history_path = append_price_snapshot(
        processed,
        captured_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )

    _write_price_inputs(processed, [105, 95])
    append_price_snapshot(
        processed,
        history_path=history_path,
        captured_at=datetime(2026, 8, 8, tzinfo=timezone.utc),
    )

    history = pd.read_parquet(history_path)
    assert len(history) == 4
    report = build_price_change_report(history)
    riser = report[report["player"] == "Riser"].iloc[0]
    faller = report[report["player"] == "Faller"].iloc[0]
    assert riser["change_since_refresh"] == 0.5
    assert faller["change_since_refresh"] == -0.5
    assert riser["change_since_season_start"] == 0.5
