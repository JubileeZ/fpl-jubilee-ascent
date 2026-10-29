"""Offline checks for admission inventory provenance handling."""

import runpy
from pathlib import Path

import pytest

MODULE = runpy.run_path(str(Path(__file__).resolve().parents[1] / "docs/research/backtesting-promotion-foundation/build_admission_inventory.py"))


def tables() -> dict[str, dict[str, dict[str, str]]]:
    return {
        name: {season: {column: "0" for column in columns} | {"season": season} for season in MODULE["RULE_SOURCES"]}
        for name, columns in MODULE["REQUIRED_COLUMNS"].items()
    }


def test_changed_provenance_is_reported_without_admission() -> None:
    inputs = tables()
    inputs["provenance"]["2023-24"]["recorded_commit_before_deadline"] = "False"
    rows = MODULE["build_rows"](inputs)
    opening = next(row for row in rows if row["season"] == "2023-24" and row["field"] == "opening_ownership")
    assert "recorded commit before deadline=False" in opening["evidence_note"]
    assert opening["evidence_status"] == "unverified"


def test_missing_provenance_column_fails() -> None:
    inputs = tables()
    del inputs["provenance"]["2023-24"]["recorded_commit_before_deadline"]
    with pytest.raises(ValueError, match="recorded_commit_before_deadline"):
        MODULE["build_rows"](inputs)
