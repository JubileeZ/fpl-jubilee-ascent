"""Tests for Expected Role rebuild engine and transfer reconciliation."""

from __future__ import annotations

from pathlib import Path
import pandas as pd
import pytest

from features.expected_role_prior import load_expected_role_table
from features.rebuild_expected_role import rebuild_expected_roles


def test_rebuild_expected_roles_generates_complete_table(tmp_path: Path) -> None:
    proc = tmp_path / "processed"
    proc.mkdir(parents=True)
    
    # 3 players: 1 known, 1 expensive new forward, 1 cheap new defender
    pd.DataFrame([
        {"id": 1, "code": 101, "web_name": "Raya", "first_name": "David", "second_name": "Raya", "club_id": 1, "position_id": 1, "now_cost": 55, "status": "a", "chance_of_playing_next_round": 100.0, "news": "", "news_added": ""},
        {"id": 2, "code": 102, "web_name": "David", "first_name": "Promise", "second_name": "David", "club_id": 5, "position_id": 4, "now_cost": 60, "status": "a", "chance_of_playing_next_round": 100.0, "news": "", "news_added": ""},
        {"id": 3, "code": 103, "web_name": "Rowe", "first_name": "Triston", "second_name": "Rowe", "club_id": 2, "position_id": 2, "now_cost": 40, "status": "a", "chance_of_playing_next_round": 100.0, "news": "", "news_added": ""},
    ]).to_parquet(proc / "players.parquet", index=False)
    
    pd.DataFrame([
        {"id": 1, "name": "Arsenal", "short_name": "ARS"},
        {"id": 2, "name": "Aston Villa", "short_name": "AVL"},
        {"id": 5, "name": "Brighton", "short_name": "BHA"},
    ]).to_parquet(proc / "clubs.parquet", index=False)

    out_csv = tmp_path / "expected_roles.csv"
    df = rebuild_expected_roles(processed_dir=proc, output_path=out_csv, season="2026-27")

    assert len(df) == 3
    assert out_csv.exists()

    loaded = load_expected_role_table(out_csv, "2026-27")
    assert len(loaded) == 3

    # Check Promise David (£6.0m FWD) inferred as Regular Starter
    david = loaded[loaded["player_id"] == 2].iloc[0]
    assert david["expected_role"] == "Regular Starter"
    assert david["p_start"] == pytest.approx(0.75)
    assert david["draft_availability"] == "eligible"

    # Check Rowe (£4.0m DEF) inferred as Cameo
    rowe = loaded[loaded["player_id"] == 3].iloc[0]
    assert rowe["expected_role"] == "Cameo"
    assert rowe["p_start"] == pytest.approx(0.10)
    assert rowe["draft_availability"] == "not_role_eligible"
