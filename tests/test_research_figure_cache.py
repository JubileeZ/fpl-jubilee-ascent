"""Research note caches must match named companion CSV cells."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

SUMMARY = Path("docs/archive/gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/gw1-6_wc4_summary.csv")
STAGE3 = Path("docs/archive/gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/gw1-6-chip-wc4-squads.md")
INDEX = Path("docs/research/INDEX.md")
AGENTS = Path("AGENTS.md")


def test_canonical_note_and_index_cite_summary_total() -> None:
    if not SUMMARY.exists():
        pytest.skip("Stage 3 summary missing")
    total = f"{float(pd.read_csv(SUMMARY).iloc[0]['total_6gw_xp']):.2f}"
    note = STAGE3.read_text(encoding="utf-8")
    assert total in note
    assert "`gw1-6_wc4_summary.csv`" in note or "gw1-6_wc4_summary.csv" in note
    index = INDEX.read_text(encoding="utf-8")
    assert total in index
    assert "`total_6gw_xp`" in index


def test_live_notes_do_not_freeze_retired_fdr_total() -> None:
    for path in (STAGE3, INDEX, AGENTS, Path("docs/agents/current-state.md")):
        assert "356.61" not in path.read_text(encoding="utf-8"), path