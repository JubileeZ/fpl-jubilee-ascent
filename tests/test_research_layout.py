"""Research companions stay under docs/research or docs/archive topic folders."""

from __future__ import annotations

import re
from pathlib import Path

SEASON_DIR = re.compile(r"^\d{4}-\d{2}$")


def test_data_research_tree_absent() -> None:
    root = Path("data/research")
    assert not root.exists(), "research companions belong in docs/research/<topic>/ not data/research/"


def test_data_archive_is_season_snapshots_only() -> None:
    archive = Path("data/archive")
    assert archive.is_dir()
    stray = [
        child.name
        for child in archive.iterdir()
        if child.name not in {".", ".."} and not child.name.startswith(".") and not SEASON_DIR.fullmatch(child.name)
    ]
    assert stray == [], f"research CSVs must not live under data/archive/: {stray}"


def test_live_research_root_has_no_loose_notes() -> None:
    live = Path("docs/research")
    loose = [
        child.name
        for child in live.iterdir()
        if child.is_file() and child.name != "INDEX.md" and not child.name.startswith(".")
    ]
    assert loose == [], f"live notes belong in docs/research/<topic-slug>/; loose files: {loose}"
