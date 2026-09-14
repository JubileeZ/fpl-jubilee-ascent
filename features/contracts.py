"""Runtime column contracts for Operational Dataset, Feature Contract, and Projection."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

OPERATIONAL_REQUIRED: dict[str, frozenset[str]] = {
    "clubs": frozenset({"id", "name", "short_name"}),
    "gameweeks": frozenset({"id", "finished", "is_current", "is_next"}),
    "players": frozenset({"id", "code", "club_id", "position_id", "now_cost", "web_name"}),
    "fixtures": frozenset({"id", "gameweek_id", "home_club_id", "away_club_id", "finished"}),
    "player_performances": frozenset({"player_id", "gameweek_id", "minutes", "total_points"}),
    "price_history": frozenset({"player_id", "now_cost", "gameweek_id", "captured_at"}),
}

FEATURE_CONTRACT_REQUIRED = frozenset({"player_id", "fixture_id", "gameweek_id"})
PROJECTION_CONTRACT_REQUIRED = frozenset(
    {"player_id", "gameweek_id", "projected_points", "projected_minutes"}
)


class ContractError(ValueError):
    """Operational Dataset, Feature Contract, or Projection columns do not match the required set."""


def require_columns(frame: pd.DataFrame, required: frozenset[str], *, name: str) -> pd.DataFrame:
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ContractError(f"{name} missing columns: {', '.join(missing)}")
    return frame


def assert_operational_table(table: str, frame: pd.DataFrame) -> pd.DataFrame:
    required = OPERATIONAL_REQUIRED.get(table)
    if required is None:
        raise ContractError(f"unknown Operational Dataset table: {table}")
    return require_columns(frame, required, name=table)


def assert_feature_contract(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    return require_columns(frame, FEATURE_CONTRACT_REQUIRED, name="Feature Contract")


def assert_projection_contract(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    return require_columns(frame, PROJECTION_CONTRACT_REQUIRED, name="Projection")


def assert_operational_processed_dir(processed_dir: Path) -> None:
    for table in OPERATIONAL_REQUIRED:
        parquet = processed_dir / f"{table}.parquet"
        if parquet.exists():
            assert_operational_table(table, pd.read_parquet(parquet))
