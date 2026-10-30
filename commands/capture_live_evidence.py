"""Publish an immutable forecast capture using execution-time UTC."""

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path

from backtesting.data_admission import require_input
from backtesting.forecast_store import load_forecast_verified
from backtesting.live_capture import LiveCaptureManager, LiveDeadlineCapture, PlayerForecastSnapshot
from backtesting.promotion_evidence import _local_path, _read_material, _restore_bytes, current_model_source_hash


def _utc_now() -> datetime:
    return datetime.now(UTC)


def capture_verified_issue(request_path: Path | str, storage_dir: Path | str) -> LiveDeadlineCapture:
    path = Path(request_path).resolve()
    payload = json.loads(path.read_bytes())
    if payload.get("version") != 1 or "capture_time_utc" in payload:
        raise ValueError("Capture request must use execution-time UTC, never a supplied timestamp")
    if payload["model_source_hash"] != current_model_source_hash():
        raise ValueError("Live capture model source changed")
    context = _read_material(path.parent, payload["admission"])
    request = _restore_bytes(context["request"])
    catalog = {digest: bytes.fromhex(raw) for digest, raw in context["catalog"].items()}
    season, gw = payload["season"], payload["gameweek"]
    capability = require_input(request, catalog, season, gw)
    predictions, _ = load_forecast_verified(_local_path(path.parent, payload["forecast_store"]), payload["forecast_id"], capability, request, catalog, payload["training_authority"], payload["model_name"])
    origin = next(origin for origin in request["origins"] if origin["season"] == season and origin["gw"] == gw)
    immediate = predictions.loc[predictions["gameweek_id"] == gw]
    totals = immediate.groupby("player_id", as_index=False).sum(numeric_only=True).set_index("player_id")
    players = {row["id"]: row for row in origin["players"]}
    if set(totals.index) != set(players):
        raise ValueError("Live capture requires complete admitted player population")
    snapshots: list[PlayerForecastSnapshot] = []
    for pid, row in totals.iterrows():
        player = players[int(pid)]
        snapshots.append(PlayerForecastSnapshot(int(pid), f"Player {pid}", player["club"], {1: "GK", 2: "D", 3: "M", 4: "F"}[player["position"]], float(row["projected_minutes"]), float(row["projected_points"]), goals=float(row["xp_goals"]), assists=float(row["xp_assists"]), clean_sheets=float(row["xp_clean_sheet"]), goals_conceded=float(row["xp_conceded"]), saves=float(row["xp_saves"]), bonus=float(row["xp_bonus"])))
    captured_at = _utc_now().isoformat()
    return LiveCaptureManager(storage_dir).record_deadline_capture(season, gw, origin["deadline"], captured_at, payload["model_name"], payload["model_source_hash"], payload["protocol_hash"], snapshots)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--storage", type=Path, required=True)
    args = parser.parse_args(argv)
    capture = capture_verified_issue(args.request, args.storage)
    print(f"Capture: {capture.capture_id}; hash: {capture.capture_hash}; UTC: {capture.capture_time_utc}")


if __name__ == "__main__":
    main()
