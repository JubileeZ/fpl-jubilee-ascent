"""Expected Role Table registry and Feature Contract Club Fixture minutes (ADR 0022)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from features.builder import build_features
from features.expected_role_prior import (
    appearance_blend_weight,
    ensure_expected_role_rebuild_choice,
    load_expected_role_table,
    write_lineup_signals,
)


def _write_role_csv(
    path: Path,
    rows: list[dict[str, object]],
    season: str = "2026-27",
) -> Path:
    frame = pd.DataFrame(rows)
    frame["season"] = season
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return path


def _write_processed(root: Path, appearances: int = 0) -> Path:
    processed = root / "processed"
    processed.mkdir(parents=True)
    pd.DataFrame(
        [
            {
                "id": 1,
                "code": 101,
                "club_id": 1,
                "position_id": 4,
                "now_cost": 90,
                "chance_of_playing_next_round": 100.0,
            },
            {
                "id": 2,
                "code": 102,
                "club_id": 1,
                "position_id": 4,
                "now_cost": 90,
                "chance_of_playing_next_round": 100.0,
            },
        ]
    ).to_parquet(processed / "players.parquet", index=False)
    pd.DataFrame([{"id": 1, "name": "A", "short_name": "A", "strength": 3}]).to_parquet(
        processed / "clubs.parquet", index=False
    )
    pd.DataFrame(
        [
            {
                "id": gw,
                "gameweek_id": gw,
                "home_club_id": 1,
                "away_club_id": 2,
                "team_h_difficulty": 3,
                "team_a_difficulty": 3,
            }
            for gw in range(1, 8)
        ]
    ).to_parquet(processed / "fixtures.parquet", index=False)
    if appearances:
        perf_rows = [
            {
                "player_id": 1,
                "gameweek_id": gw,
                "minutes": 90,
                "starts": 1,
                "total_points": 6,
                "goals_scored": 0,
                "assists": 0,
                "clean_sheets": 0,
                "goals_conceded": 0,
                "own_goals": 0,
                "penalties_saved": 0,
                "penalties_missed": 0,
                "yellow_cards": 0,
                "red_cards": 0,
                "saves": 0,
                "bonus": 0,
            }
            for gw in range(1, appearances + 1)
        ]
        pd.DataFrame(perf_rows).to_parquet(processed / "player_performances.parquet", index=False)
    else:
        pd.DataFrame(columns=["player_id", "gameweek_id", "minutes", "total_points", "starts"]).to_parquet(
            processed / "player_performances.parquet", index=False
        )
    return processed


NAILED = {
    "player_id": 1,
    "p_start": 0.90,
    "p_sub_in": 0.05,
    "p_dnp": 0.05,
    "mins_if_start": 85.0,
    "mins_if_sub": 20.0,
    "draft_availability": "eligible",
    "availability_override": "",
}


def test_appearance_blend_weight_is_zero_through_one_appearance() -> None:
    assert appearance_blend_weight(0) == 0.0
    assert appearance_blend_weight(1) == 0.0
    assert appearance_blend_weight(2) == 0.25
    assert appearance_blend_weight(3) == 0.5
    assert appearance_blend_weight(4) == 0.75
    assert appearance_blend_weight(5) == 1.0
    assert appearance_blend_weight(8) == 1.0


def test_load_expected_role_table_refuses_missing_and_other_season(tmp_path: Path) -> None:
    missing = tmp_path / "missing.csv"
    with pytest.raises(ValueError, match="Expected Role Table"):
        load_expected_role_table(missing, "2026-27")

    other = _write_role_csv(tmp_path / "roles.csv", [NAILED], season="2025-26")
    with pytest.raises(ValueError, match="2025-26"):
        load_expected_role_table(other, "2026-27")


def test_snapshot_season_does_not_gate_feature_contract_minutes(tmp_path: Path) -> None:
    processed = _write_processed(tmp_path)
    table = _write_role_csv(tmp_path / "roles.csv", [NAILED])
    for snapshot_season in ("test_backtest_cli_run0", "2025-26"):
        df = build_features(
            processed,
            target_gw=2,
            use_archive_seed=False,
            expected_role_table=table,
            season=snapshot_season,
        )
        row = df[df["player_id"] == 1].iloc[0]
        assert row["p_start"] == pytest.approx(1.0 / 3.0)


def test_empty_tenure_does_not_use_expected_role_or_out_of_contention(tmp_path: Path) -> None:
    processed = _write_processed(tmp_path, appearances=0)
    table = _write_role_csv(tmp_path / "roles.csv", [NAILED])
    df = build_features(
        processed,
        target_gw=2,
        use_archive_seed=False,
        expected_role_table=table,
        season="2026-27",
    )
    nailed = df[df["player_id"] == 1].iloc[0]
    missing = df[df["player_id"] == 2].iloc[0]
    assert nailed["p_start"] == pytest.approx(1.0 / 3.0)
    assert nailed["xmins_if_start"] == pytest.approx(78.0)
    assert missing["p_dnp"] == pytest.approx(1.0 / 3.0)
    assert missing["xmins_if_start"] == pytest.approx(78.0)


def test_draft_availability_does_not_overlay_feature_contract_minutes(tmp_path: Path) -> None:
    processed = _write_processed(tmp_path, appearances=0)
    excluded = dict(NAILED)
    excluded["draft_availability"] = "exclude_gw1-5"
    table = _write_role_csv(tmp_path / "roles.csv", [excluded])
    df = build_features(
        processed,
        target_gw=1,
        horizon=6,
        use_archive_seed=False,
        expected_role_table=table,
        season="2026-27",
    )
    player = df[df["player_id"] == 1]
    gw5 = player[player["gameweek_id"] == 5].iloc[0]
    gw6 = player[player["gameweek_id"] == 6].iloc[0]
    assert gw5["p_start"] == pytest.approx(1.0 / 3.0)
    assert gw6["p_start"] == pytest.approx(gw5["p_start"])


def test_five_appearances_use_full_current_season_minutes(tmp_path: Path) -> None:
    processed = _write_processed(tmp_path, appearances=5)
    table = _write_role_csv(tmp_path / "roles.csv", [NAILED])
    df = build_features(
        processed,
        target_gw=6,
        use_archive_seed=False,
        expected_role_table=table,
        season="2026-27",
    )
    row = df[df["player_id"] == 1].iloc[0]
    assert row["xmins_if_start"] == pytest.approx(90.0)
    assert row["avg_mins_3gw"] == pytest.approx(90.0)


def test_refresh_requires_rebuild_or_keep_when_table_is_other_season(tmp_path: Path) -> None:
    table = _write_role_csv(tmp_path / "roles.csv", [NAILED], season="2025-26")
    with pytest.raises(ValueError, match="--rebuild-roles"):
        ensure_expected_role_rebuild_choice("2026-27", False, False, table)
    ensure_expected_role_rebuild_choice("2026-27", True, False, table)
    ensure_expected_role_rebuild_choice("2026-27", False, True, table)


def test_write_lineup_signals_pins_dual_source_extract(tmp_path: Path) -> None:
    path = tmp_path / "lineup-signals.json"
    write_lineup_signals(
        path,
        season="2026-27",
        predicted_xi={"ARS": ["Raya", "Gabriel"]},
        nailed={"ARS": ["Raya"]},
    )
    import json

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["season"] == "2026-27"
    assert payload["predicted_xi"]["ARS"] == ["Raya", "Gabriel"]
    assert payload["nailed"]["ARS"] == ["Raya"]
