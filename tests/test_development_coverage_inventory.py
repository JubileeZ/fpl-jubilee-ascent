"""Offline unit tests for development coverage and training lineage audit."""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import lzma
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "docs/research/backtesting-promotion-foundation/development_coverage_inventory.py"
TOPIC_DIR = ROOT / "docs/research/backtesting-promotion-foundation"


def _load_inventory_module() -> Any:
    spec = importlib.util.spec_from_file_location("development_coverage_inventory", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_lzma_json(path: Path, payload: dict[str, Any]) -> str:
    compressed = lzma.compress(json.dumps(payload).encode("utf-8"))
    path.write_bytes(compressed)
    return hashlib.sha256(compressed).hexdigest()


def _make_sample_elements() -> list[dict[str, Any]]:
    # Valid 15-man minimum squad: 2 GKP, 5 DEF, 5 MID, 3 FWD (cost = 2*40 + 5*40 + 5*45 + 3*45 = 640).
    specs = [(1, 2, 40), (2, 5, 40), (3, 5, 45), (4, 3, 45)]
    elements: list[dict[str, Any]] = []
    idx = 1
    for pos, count, cost in specs:
        for _ in range(count):
            elements.append(
                {
                    "id": idx,
                    "code": 1000 + idx,
                    "first_name": f"First{idx}",
                    "second_name": f"Second{idx}",
                    "element_type": pos,
                    "now_cost": cost,
                    "can_select": True,
                    "status": "a",
                    "chance_of_playing_next_round": None,
                    "news_added": "2025-08-15T12:03:26.000Z" if idx == 1 else "2025-08-14T10:00:00.000Z",
                }
            )
            idx += 1
    # Unselectable player + Assistant Manager (element_type == 5).
    elements.append(
        {
            "id": 99,
            "code": 1099,
            "first_name": "Unavailable",
            "second_name": "Player",
            "element_type": 3,
            "now_cost": 40,
            "can_select": False,
            "status": "u",
            "chance_of_playing_next_round": 0,
            "news_added": None,
        }
    )
    elements.append(
        {
            "id": 100,
            "code": 1100,
            "first_name": "Assistant",
            "second_name": "Manager",
            "element_type": 5,
            "now_cost": 15,
            "can_select": True,
            "status": "a",
            "chance_of_playing_next_round": None,
            "news_added": None,
        }
    )
    return elements


def test_assert_unsealed_path_rejects_2026_27(tmp_path: Path) -> None:
    mod = _load_inventory_module()
    mod._assert_unsealed_path(tmp_path / "data/archive/2025-26/processed")
    with pytest.raises(ValueError, match="2026-27"):
        mod._assert_unsealed_path(tmp_path / "data/archive/2026-27/processed")


def test_inspect_bootstrap_snapshot_excludes_managers_and_computes_capture_lower(tmp_path: Path) -> None:
    mod = _load_inventory_module()
    boot_path = tmp_path / "07-opening_bootstrap.raw"
    commit_path = tmp_path / "08-opening_bootstrap-commit.raw"

    payload = {
        "events": [{"id": 1, "deadline_time": "2025-08-15T17:30:00Z", "is_next": True}],
        "teams": [{"id": t} for t in range(1, 21)],
        "elements": _make_sample_elements(),
    }
    expected_sha = _write_lzma_json(boot_path, payload)
    commit_path.write_text(
        json.dumps(
            {
                "commit": {
                    "committer": {"date": "2025-08-15T12:52:48Z"},
                    "verification": {"verified": False, "reason": "unsigned"},
                }
            }
        ),
        encoding="utf-8",
    )

    info = mod.inspect_bootstrap_snapshot(boot_path=boot_path, commit_path=commit_path, expected_gw=1)

    assert info["total_elements"] == 17
    assert info["excluded_assistant_managers"] == 1
    assert info["player_rows"] == 16
    assert info["can_select_true"] == 15
    assert info["min_15_selectable_cost_tenths"] == 640
    assert info["status_u"] == 1
    assert info["status_a_null_chance"] == 15
    assert info["events_is_next"] is True
    assert info["commit_before_deadline"] is True
    assert info["capture_lower_utc"] == "2025-08-15T12:22:48+00:00"
    assert info["age_from_commit"] == "4h 37m 12s"
    assert info["age_from_capture_lower"] == "5h 07m 12s"
    assert info["within_8h_target"] is True
    assert info["sha256"] == expected_sha


def test_inspect_fixture_snapshot_checks_horizon_and_fallback_bound(tmp_path: Path) -> None:
    mod = _load_inventory_module()
    csv_path = tmp_path / "11-fixture_pilot.raw"
    commit_path = tmp_path / "12-fixture_pilot-commit.raw"

    rows = ["id,event,team_h,team_a,kickoff_time"]
    fid = 1
    for gw in range(1, 9):
        rows.append(f"{fid},{gw},1,2,2025-08-22T19:00:00Z")
        fid += 1
    csv_path.write_bytes(("\n".join(rows) + "\n").encode("utf-8-sig"))
    commit_path.write_text(
        json.dumps(
            {
                "commit": {
                    "committer": {"date": "2025-08-20T07:59:03Z"},
                    "verification": {"verified": True, "reason": "valid"},
                },
                "parents": [{"sha": "46277afda0090000000000000000000000000000"}],
            }
        ),
        encoding="utf-8",
    )

    prev_deadline = datetime(2025, 8, 15, 17, 30, tzinfo=timezone.utc)
    origin_deadline = datetime(2025, 8, 22, 17, 30, tzinfo=timezone.utc)
    info = mod.inspect_fixture_snapshot(
        csv_path=csv_path,
        commit_path=commit_path,
        prev_gw_deadline=prev_deadline,
        origin_deadline=origin_deadline,
    )

    assert info["total_rows"] == 8
    assert info["gw2_7_rows"] == 6
    assert info["duplicate_horizon_ids"] == 0
    assert info["missing_required_cells"] == 0
    assert info["strict_between_deadlines"] is True
    assert info["within_7d_target"] is True
    assert info["commit_verified"] is True
    assert info["age_from_fallback_lower"] == "7d 00h 00m 00s"


def test_reconcile_2025_26_ledger_exact_and_mismatch_detection() -> None:
    mod = _load_inventory_module()
    players = pd.DataFrame(
        [
            {"id": 1, "position_id": 1},
            {"id": 2, "position_id": 2},
            {"id": 3, "position_id": 3},
            {"id": 4, "position_id": 4},
        ]
    )
    perf = pd.DataFrame(
        [
            # GKP: 90m(2) + 1G(10) + CS(4) + 3 saves(1) = 17
            {
                "player_id": 1,
                "gameweek_id": 1,
                "minutes": 90,
                "goals_scored": 1,
                "assists": 0,
                "clean_sheets": 1,
                "goals_conceded": 0,
                "saves": 3,
                "penalties_saved": 0,
                "penalties_missed": 0,
                "own_goals": 0,
                "yellow_cards": 0,
                "red_cards": 0,
                "bonus": 0,
                "defensive_contribution": 0,
                "total_points": 17,
            },
            # DEF: 90m(2) - 2GC(-1) + defcon=10(+2) - 1 YC(-1) = 2
            {
                "player_id": 2,
                "gameweek_id": 1,
                "minutes": 90,
                "goals_scored": 0,
                "assists": 0,
                "clean_sheets": 0,
                "goals_conceded": 2,
                "saves": 0,
                "penalties_saved": 0,
                "penalties_missed": 0,
                "own_goals": 0,
                "yellow_cards": 1,
                "red_cards": 0,
                "bonus": 0,
                "defensive_contribution": 10,
                "total_points": 2,
            },
            # MID: 45m(1) + defcon=11(0) + 1 assist(3) + 2 bonus(2) = 6
            {
                "player_id": 3,
                "gameweek_id": 2,
                "minutes": 45,
                "goals_scored": 0,
                "assists": 1,
                "clean_sheets": 0,
                "goals_conceded": 3,
                "saves": 0,
                "penalties_saved": 0,
                "penalties_missed": 0,
                "own_goals": 1,
                "yellow_cards": 0,
                "red_cards": 0,
                "bonus": 2,
                "defensive_contribution": 11,
                "total_points": 4,
            },
            # FWD: 90m(2) + 1G(4) + defcon=12(+2) - PM(-2) = 6
            {
                "player_id": 4,
                "gameweek_id": 2,
                "minutes": 90,
                "goals_scored": 1,
                "assists": 0,
                "clean_sheets": 1,
                "goals_conceded": 0,
                "saves": 0,
                "penalties_saved": 0,
                "penalties_missed": 1,
                "own_goals": 0,
                "yellow_cards": 0,
                "red_cards": 0,
                "bonus": 0,
                "defensive_contribution": 12,
                "total_points": 6,
            },
        ]
    )
    clean_res = mod.reconcile_2025_26_ledger(players, perf)
    assert clean_res["checked_rows"] == 4
    assert clean_res["mismatches"] == 0
    assert clean_res["exact_matches"] == 4
    assert clean_res["distinct_gameweeks"] == 2

    corrupted = perf.copy()
    corrupted.loc[0, "total_points"] = 99
    bad_res = mod.reconcile_2025_26_ledger(players, corrupted)
    assert bad_res["mismatches"] == 1
    assert bad_res["exact_matches"] == 3


def test_seed_resolution_splits_code_name_threshold_and_newcomers() -> None:
    mod = _load_inventory_module()
    seed_players = pd.DataFrame(
        [
            {"id": 10, "code": 500, "first_name": "Alpha", "second_name": "One"},
            {"id": 20, "code": 501, "first_name": "Beta", "second_name": "Two"},
        ]
    )
    seed_fixtures = pd.DataFrame([{"id": fid, "finished": True} for fid in range(1, 11)])
    perf_rows = [{"player_id": 10, "fixture_id": fid, "minutes": 70} for fid in range(1, 9)]
    perf_rows.extend([{"player_id": 20, "fixture_id": fid, "minutes": 90} for fid in range(1, 4)])
    seed_perf = pd.DataFrame(perf_rows)

    elements = [
        {"id": 1, "code": 500, "first_name": "Alpha", "second_name": "One", "element_type": 3},
        {"id": 2, "code": 999, "first_name": "Beta", "second_name": "Two", "element_type": 2},
        {"id": 3, "code": 777, "first_name": "Gamma", "second_name": "Three", "element_type": 4},
        {"id": 4, "code": 888, "first_name": "Mgr", "second_name": "Five", "element_type": 5},
    ]

    res = mod._seed_resolution_for_elements(
        elements=elements,
        seed_players=seed_players,
        seed_perf=seed_perf,
        seed_fixtures=seed_fixtures,
    )
    assert res["players_excl_pos5"] == 3
    assert res["matched_by_code"] == 1
    assert res["matched_by_name_fallback"] == 1
    assert res["unmatched_newcomers"] == 1
    assert res["player_prior_eligible"] == 1
    assert res["matched_below_threshold_fallback"] == 1
    assert res["total_position_price_fallback"] == 2


def test_quarantine_pilot_fails_closed_on_sha256_mismatch(tmp_path: Path) -> None:
    mod = _load_inventory_module()
    (tmp_path / "07-opening_bootstrap.raw").write_bytes(b"corrupted")
    (tmp_path / "summary.json").write_text(
        json.dumps(
            {
                "origin": "2025-26 GW2",
                "attempts": [{"attempt": 7, "label": "opening_bootstrap", "status": "recovered", "sha256": "0" * 64}],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        mod._inspect_quarantine_pilot(tmp_path, tmp_path)


def test_generated_companions_and_report_stay_in_sync() -> None:
    mod = _load_inventory_module()
    assessment_path = TOPIC_DIR / "development_coverage_assessment.json"
    inventory_path = TOPIC_DIR / "development_coverage_inventory.csv"
    sources_path = TOPIC_DIR / "development_coverage_sources.csv"
    report_path = TOPIC_DIR / "development_coverage_report.md"

    assessment = json.loads(assessment_path.read_text(encoding="utf-8"))
    with inventory_path.open("r", encoding="utf-8", newline="") as handle:
        inv_rows = list(csv.DictReader(handle))
    with sources_path.open("r", encoding="utf-8", newline="") as handle:
        src_rows = list(csv.DictReader(handle))

    assert len(inv_rows) == assessment["coverage_summary_counts"]["total_gameweek_field_evaluations"] == 342
    observed_breakdown: dict[str, int] = {}
    for row in inv_rows:
        observed_breakdown[row["status"]] = observed_breakdown.get(row["status"], 0) + 1
    assert observed_breakdown == assessment["coverage_summary_counts"]["status_breakdown"]

    for row in src_rows:
        row["size_bytes"] = int(row["size_bytes"])

    expected_md = mod.render_report(assessment=assessment, source_rows=src_rows)
    assert report_path.read_text(encoding="utf-8") == expected_md
    assert "### Metric Definitions & Direction" in expected_md
    assert "## Method" in expected_md
    assert "## Findings" in expected_md
    assert "## Risks and unknowns" in expected_md
    assert "## Agent Prompt" in expected_md
