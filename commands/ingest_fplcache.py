"""CLI for quarantined Randdalf/fplcache GW1-38 ingestion and outcome reconciliation."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backtesting.fplcache_ingest import GitHubFplCacheAdapter, ingest_season_fplcache
from backtesting.season_rules import load_season_lifecycle

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest quarantined Randdalf/fplcache GW1-38 snapshots.")
    parser.add_argument("--season", default=None, help="Lifecycle active_validation season (default from config)")
    parser.add_argument("--manifest", type=Path, default=None, help="Output manifest JSON path")
    parser.add_argument("--quarantine", type=Path, default=None, help="Local quarantine output directory")
    args = parser.parse_args(argv)

    season = args.season or load_season_lifecycle().active_season
    archive_dir = PROJECT_ROOT / "data" / "archive" / season
    processed_dir = archive_dir / "processed"
    slug = season.replace("-", "_")

    gameweeks_df = pd.read_parquet(processed_dir / "gameweeks.parquet")
    bootstrap_path = archive_dir / "raw" / "bootstrap_static.json"
    if bootstrap_path.is_file():
        bootstrap = json.loads(bootstrap_path.read_text(encoding="utf-8"))
        checked_map = {int(ev["id"]): bool(ev.get("data_checked", False)) for ev in bootstrap.get("events", [])}
        gameweeks_df["data_checked"] = gameweeks_df["id"].map(checked_map).fillna(False)
        outcome_captured_at = datetime.fromtimestamp(bootstrap_path.stat().st_mtime, tz=UTC)
    else:
        gameweeks_df["data_checked"] = False
        outcome_captured_at = None

    fixtures_df = pd.read_parquet(processed_dir / "fixtures.parquet")
    perf_path = processed_dir / "player_performances.parquet"
    performances_df = pd.read_parquet(perf_path) if perf_path.is_file() else None

    quarantine_dir = args.quarantine or (PROJECT_ROOT / "data" / "reports" / "fplcache" / season)
    manifest_path = args.manifest or (PROJECT_ROOT / "config" / f"fplcache_{slug}_manifest.json")

    manifest = ingest_season_fplcache(
        season=season,
        gameweeks_df=gameweeks_df,
        fixtures_df=fixtures_df,
        performances_df=performances_df,
        source_port=GitHubFplCacheAdapter(),
        quarantine_dir=quarantine_dir,
        manifest_path=manifest_path,
        reference_utc=datetime.now(UTC),
        outcome_captured_at=outcome_captured_at,
    )
    summary = manifest["summary"]
    print(
        f"Ingested {season}: admitted={summary['admitted_gws']} "
        f"disclosed_8h_24h={summary['disclosed_8h_24h_gws']} "
        f"settled={summary['settled_verified_gws']} "
        f"pending={len(summary['pending_future_gws'])} "
        f"lag=[{summary['min_lag_hours']}h, {summary['max_lag_hours']}h] -> {manifest_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
