from pathlib import Path

import pandas as pd
import pytest

from features.contracts import (
    ContractError,
    assert_feature_contract,
    assert_operational_processed_dir,
    assert_operational_table,
    assert_projection_contract,
    require_columns,
)


def test_require_columns_rejects_missing_required_field() -> None:
    with pytest.raises(ContractError, match="players missing columns: code"):
        require_columns(pd.DataFrame({"id": [1]}), frozenset({"id", "code"}), name="players")


def test_require_columns_accepts_complete_frame() -> None:
    frame = require_columns(
        pd.DataFrame({"id": [1], "code": [99]}),
        frozenset({"id", "code"}),
        name="players",
    )
    assert list(frame.columns) == ["id", "code"]


def test_assert_operational_players_requires_code() -> None:
    with pytest.raises(ContractError, match="players"):
        assert_operational_table("players", pd.DataFrame({"id": [1], "club_id": [1], "position_id": [3], "now_cost": [50]}))


def test_assert_operational_table_rejects_unknown_name() -> None:
    with pytest.raises(ContractError, match="unknown Operational Dataset table"):
        assert_operational_table("not_a_table", pd.DataFrame({"id": [1]}))


def test_assert_feature_contract_requires_fixture_identity() -> None:
    with pytest.raises(ContractError, match="Feature Contract"):
        assert_feature_contract(pd.DataFrame({"player_id": [1], "gameweek_id": [1]}))


def test_assert_projection_contract_requires_points_and_minutes() -> None:
    with pytest.raises(ContractError, match="Projection"):
        assert_projection_contract(
            pd.DataFrame({"player_id": [1], "fixture_id": [10], "gameweek_id": [1], "projected_points": [2.0]})
        )


def test_assert_feature_contract_allows_empty_frame() -> None:
    empty = pd.DataFrame()
    assert assert_feature_contract(empty) is empty


def test_assert_operational_processed_dir_skips_missing_parquet(tmp_path: Path) -> None:
    assert_operational_processed_dir(tmp_path)


def test_assert_operational_processed_dir_rejects_players_without_code(tmp_path: Path) -> None:
    pd.DataFrame(
        {"id": [1], "club_id": [1], "position_id": [3], "now_cost": [50], "web_name": ["AB"]}
    ).to_parquet(tmp_path / "players.parquet")
    with pytest.raises(ContractError, match="players missing columns: code"):
        assert_operational_processed_dir(tmp_path)

