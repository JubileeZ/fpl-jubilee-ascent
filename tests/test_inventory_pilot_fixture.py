"""Tests for admissible non-live pilot fixture inventory command (#198)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from commands.inventory_pilot_fixture import (
    build_pilot_fixture_inventory,
    main,
    render_inventory_markdown,
)


def test_inventory_records_non_live_prefixes_digests_and_missing_prerequisites(tmp_path: Path) -> None:
    report = build_pilot_fixture_inventory(verify_fixture=False)

    assert report["forbidden_live_season_accessed"] is False
    seasons = {entry["season"]: entry for entry in report["seasons"]}
    assert set(seasons) == {"2023-24", "2024-25", "2025-26"}

    assert seasons["2025-26"]["contiguous_admitted_prefix_end_gw"] == 7
    assert seasons["2025-26"]["contiguous_admitted_prefix"] == "GW1..7"
    assert seasons["2025-26"]["first_blocked_gw"] == 8
    assert seasons["2025-26"]["manifest_sha256"]

    assert seasons["2024-25"]["contiguous_admitted_prefix_end_gw"] == 1
    assert seasons["2024-25"]["contiguous_admitted_prefix"] == "GW1..1"
    assert seasons["2024-25"]["first_blocked_gw"] == 2
    assert seasons["2024-25"]["manifest_sha256"]

    assert seasons["2023-24"]["contiguous_admitted_prefix_end_gw"] == 0
    assert seasons["2023-24"]["contiguous_admitted_prefix"] == "0"

    assert report["seed_manifests"]["2024-25"]["exists"] is True
    assert report["seed_manifests"]["2024-25"]["sha256"]
    assert report["seed_manifests"]["2023-24"]["exists"] is False

    assert report["has_admissible_historical_gw15_passing_fixture"] is False
    assert report["certification_artifacts_verified"] is True
    assert report["retained_gw15_fixture"]["verification_skipped"] is True
    prereqs = " ".join(report["missing_prerequisites"]).lower()
    assert "gw15" in prereqs
    assert "finalist" in prereqs or "podium" in prereqs
    assert "2025-26" in prereqs
    assert "2024-25" in prereqs

    md = render_inventory_markdown(report)
    assert "GW1..7" in md
    assert "GW1..1" in md
    assert "2023-24" in md
    assert "inconclusive" in md.lower()

    out_md = tmp_path / "pilot-fixture-inventory.md"
    out_json = tmp_path / "pilot-fixture-inventory.json"
    rc = main(["--output", str(out_md), "--json-output", str(out_json), "--skip-fixture-verify"])
    assert rc == 0
    assert out_md.is_file()
    assert out_json.is_file()
    parsed = json.loads(out_json.read_text(encoding="utf-8"))
    assert parsed["seasons"] == report["seasons"]


def test_inventory_computes_prerequisites_and_passing_gate_dynamically(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from commands import inventory_pilot_fixture as mod

    monkeypatch.setattr(
        mod,
        "_inspect_mirror_manifest",
        lambda root, season: {
            "manifest_path": f"config/dev_mirror_{season.replace('-', '_')}_manifest.json",
            "manifest_sha256": "a" * 64,
            "track": "dev_mirror",
            "bootstrap_admitted_count": 15 if season == "2025-26" else 1,
            "fixture_admitted_count": 15 if season == "2025-26" else 1,
            "settled_outcomes_zero_diff": True,
            "verified_outcome_rows": 150,
            "ledger_mismatch_rows": 0,
            "contiguous_admitted_prefix_end_gw": 15 if season == "2025-26" else 1,
            "contiguous_admitted_prefix": "GW1..15" if season == "2025-26" else "GW1..1",
            "admitted_gws": list(range(1, 16)) if season == "2025-26" else [1],
            "first_blocked_gw": 16 if season == "2025-26" else 2,
            "first_blocked_reasons": ["stop"],
            "full_season_admitted": False,
            "local_blobs_hydrated": season == "2025-26",
            "attributions": [],
        },
    )
    report = build_pilot_fixture_inventory(verify_fixture=False)
    assert report["has_admissible_historical_gw15_passing_fixture"] is False
    prereq_text = " ".join(report["missing_prerequisites"]).lower()
    assert "no non-live season reaches >=15" not in prereq_text
    assert "podium" in prereq_text or "finalist" in prereq_text


def test_inventory_refuses_2026_27_inspection(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from commands import inventory_pilot_fixture as mod

    called: list[Path] = []
    orig = mod._inspect_archive_season

    def spy_archive(root: Path, season: str) -> dict[str, object]:
        called.append(root / "data" / "archive" / season)
        assert season != "2026-27"
        return orig(root, season)

    monkeypatch.setattr(mod, "_inspect_archive_season", spy_archive)
    report = build_pilot_fixture_inventory(verify_fixture=False)
    assert all("2026-27" not in str(p) for p in called)
    assert "2026-27" not in {s["season"] for s in report["seasons"]}


def test_inventory_returns_passing_when_hydrated_prefix_sealed_and_certified(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from commands import inventory_pilot_fixture as mod
    from models.selection import ModelSelection

    monkeypatch.setattr(
        mod,
        "_inspect_mirror_manifest",
        lambda root, season: {
            "manifest_path": f"config/dev_mirror_{season.replace('-', '_')}_manifest.json",
            "manifest_sha256": "a" * 64,
            "track": "dev_mirror",
            "bootstrap_admitted_count": 15 if season == "2025-26" else 1,
            "fixture_admitted_count": 15 if season == "2025-26" else 1,
            "settled_outcomes_zero_diff": True,
            "verified_outcome_rows": 150,
            "ledger_mismatch_rows": 0,
            "contiguous_admitted_prefix_end_gw": 15 if season == "2025-26" else 1,
            "contiguous_admitted_prefix": "GW1..15" if season == "2025-26" else "GW1..1",
            "admitted_gws": list(range(1, 16)) if season == "2025-26" else [1],
            "first_blocked_gw": 16 if season == "2025-26" else 2,
            "first_blocked_reasons": ["stop"],
            "full_season_admitted": False,
            "local_blobs_hydrated": True,
            "attributions": [],
        },
    )
    monkeypatch.setattr(
        mod,
        "load_model_selection",
        lambda _path: ModelSelection(
            champion="def_xg_shrink_challenger",
            candidates=("cand_a",),
            provisional_active="cand_a",
            podium_frozen_season="2026-27",
            podium_sealed=True,
        ),
    )
    monkeypatch.setattr(
        mod,
        "verify_certification_artifacts",
        lambda *_args, **_kwargs: {"passed": True, "errors": []},
    )
    report = build_pilot_fixture_inventory(verify_fixture=False)
    assert report["certification_artifacts_verified"] is True
    assert report["missing_prerequisites"] == []
    assert report["has_admissible_historical_gw15_passing_fixture"] is True
