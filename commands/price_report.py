from __future__ import annotations

import argparse
import logging
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from tabulate import tabulate

from clients.env_loader import configure_utf8_stdio, load_env

load_env()
configure_utf8_stdio()

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOGGER = logging.getLogger(__name__)


def _current_gameweek(processed_dir: Path) -> int:
    gameweeks_path = processed_dir / "gameweeks.parquet"
    if not gameweeks_path.exists():
        raise FileNotFoundError(f"Gameweek data not found: {gameweeks_path}")

    gameweeks = pd.read_parquet(gameweeks_path)
    for flag in ("is_current", "is_next"):
        if flag in gameweeks.columns:
            selected = gameweeks[gameweeks[flag].fillna(False)]
            if not selected.empty:
                return int(selected.iloc[0]["id"])
    if "id" in gameweeks.columns and not gameweeks.empty:
        return int(pd.to_numeric(gameweeks["id"], errors="coerce").max())
    raise ValueError(f"Could not determine a gameweek from {gameweeks_path}")


def _utc_timestamp(value: datetime | None) -> pd.Timestamp:
    timestamp = pd.Timestamp(value or datetime.now(timezone.utc))
    return timestamp.tz_localize("UTC") if timestamp.tzinfo is None else timestamp.tz_convert("UTC")


def append_price_snapshot(
    processed_dir: Path,
    history_path: Path | None = None,
    captured_at: datetime | None = None,
) -> Path:
    """Append the current player prices to the refresh history."""
    players_path = processed_dir / "players.parquet"
    if not players_path.exists():
        raise FileNotFoundError(f"Player data not found: {players_path}")

    players = pd.read_parquet(players_path)
    if "id" not in players.columns or "now_cost" not in players.columns:
        raise ValueError("players.parquet must contain id and now_cost columns")

    snapshot_columns = ["id", "now_cost", *[column for column in ("web_name", "club_id") if column in players.columns]]
    snapshot = players[snapshot_columns].rename(columns={"id": "player_id"})
    snapshot["gameweek_id"] = _current_gameweek(processed_dir)
    snapshot["captured_at"] = _utc_timestamp(captured_at)

    output_path = history_path or processed_dir / "price_history.parquet"
    if output_path.exists():
        history = pd.read_parquet(output_path)
        history = pd.concat([history, snapshot], ignore_index=True)
    else:
        history = snapshot

    output_path.parent.mkdir(parents=True, exist_ok=True)
    # DESTRUCTIVE: rewrite the append-only Parquet with prior snapshots plus this refresh.
    history.to_parquet(output_path, index=False)
    return output_path


def build_price_change_report(history: pd.DataFrame) -> pd.DataFrame:
    """Compare the latest prices with the prior refresh and season start."""
    required = {"player_id", "now_cost", "captured_at", "gameweek_id"}
    missing = sorted(required - set(history.columns))
    if missing:
        raise ValueError(f"price history is missing columns: {', '.join(missing)}")
    if history.empty:
        return pd.DataFrame()

    data = history.copy()
    data["_captured_at"] = pd.to_datetime(data["captured_at"], utc=True, errors="coerce")
    data = data.dropna(subset=["_captured_at"]).sort_values("_captured_at")
    timestamps = data["_captured_at"].drop_duplicates().tolist()
    if not timestamps:
        return pd.DataFrame()

    latest_timestamp = timestamps[-1]
    previous_timestamp = timestamps[-2] if len(timestamps) > 1 else None
    season_start_timestamp = timestamps[0]

    latest = data[data["_captured_at"] == latest_timestamp].drop_duplicates("player_id", keep="last")
    latest = latest[["player_id", "now_cost", "gameweek_id", "_captured_at"]].rename(
        columns={
            "now_cost": "latest_price",
            "gameweek_id": "gameweek",
            "_captured_at": "captured_at",
        }
    )
    first = data[data["_captured_at"] == season_start_timestamp].drop_duplicates("player_id", keep="last")
    first = first[["player_id", "now_cost"]].rename(columns={"now_cost": "season_start_price"})

    if previous_timestamp is None:
        previous = pd.DataFrame(columns=["player_id", "previous_price"])
    else:
        previous = data[data["_captured_at"] == previous_timestamp].drop_duplicates("player_id", keep="last")
        previous = previous[["player_id", "now_cost"]].rename(columns={"now_cost": "previous_price"})

    report = latest.merge(previous, on="player_id", how="left").merge(first, on="player_id", how="left")
    if "web_name" in data.columns:
        names = data[data["_captured_at"] == latest_timestamp][["player_id", "web_name"]].drop_duplicates("player_id")
        report = report.merge(names, on="player_id", how="left")
    if "club_id" in data.columns:
        clubs = data[data["_captured_at"] == latest_timestamp][["player_id", "club_id"]].drop_duplicates("player_id")
        report = report.merge(clubs, on="player_id", how="left")

    report["player"] = report.get("web_name", report["player_id"].map(lambda player_id: f"Player {player_id}"))
    report["player"] = report["player"].fillna(report["player_id"].map(lambda player_id: f"Player {player_id}"))
    for column in ("latest_price", "previous_price", "season_start_price"):
        report[column] = pd.to_numeric(report[column], errors="coerce") / 10.0
    report["change_since_refresh"] = report["latest_price"] - report["previous_price"]
    report["change_since_season_start"] = report["latest_price"] - report["season_start_price"]
    columns = [
        "player_id",
        "player",
        "club_id",
        "gameweek",
        "captured_at",
        "latest_price",
        "previous_price",
        "change_since_refresh",
        "season_start_price",
        "change_since_season_start",
    ]
    return report[[column for column in columns if column in report.columns]].sort_values("player")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Report FPL price changes since the previous refresh.")
    parser.add_argument(
        "--data_dir",
        "--data-dir",
        dest="data_dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "processed",
    )
    parser.add_argument("--top", type=int, default=10, help="Number of risers/fallers to print")
    parser.add_argument("--output", type=Path, default=None, help="CSV output path")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    history_path = args.data_dir / "price_history.parquet"
    if not history_path.exists():
        raise SystemExit(f"Price history not found: {history_path}. Run refresh_data first.")
    if args.top < 1:
        raise SystemExit("--top must be at least 1")

    report = build_price_change_report(pd.read_parquet(history_path))
    if report.empty:
        raise SystemExit("No price snapshots available.")

    latest_gameweek = report["gameweek"].iloc[0]
    print(f"PRICE CHANGE REPORT: GW{latest_gameweek}")
    display_columns = ["player", "latest_price", "change_since_refresh", "change_since_season_start"]
    for title, ascending in (("Top risers", False), ("Top fallers", True)):
        changes = report.dropna(subset=["change_since_refresh"]).sort_values(
            "change_since_refresh",
            ascending=ascending,
        ).head(args.top)
        print(f"\n--- {title} ---")
        print(tabulate(changes[display_columns], headers="keys", tablefmt="grid", showindex=False))

    output = args.output or PROJECT_ROOT / "data" / "reports" / "price_changes.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(output, index=False)
    LOGGER.info("Price change report saved to %s", output)


if __name__ == "__main__":
    main()
