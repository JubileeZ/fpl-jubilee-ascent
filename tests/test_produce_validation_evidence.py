"""Tests for commands.produce_validation_evidence and .github/workflows/validation-collector.yml (#193, #198)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from backtesting.confirmation_registry import ConfirmationRegistry
from backtesting.portable_evidence import (
    BlobStore,
    ExclusionLedger,
    load_and_verify_scorecard,
    verify_checkpoint_snapshot_archive,
)
from backtesting.promotion_evidence import GUARD_SEMANTICS
from test_empirical_admission import _build_empirical_bundle


def _write_origin_manifest_inputs(root: Path, request: dict[str, Any], catalog: dict[str, bytes]) -> Path:
    """Materialize an empirical origin manifest directory for collector ingestion."""
    src_dir = root / "incoming"
    src_dir.mkdir(parents=True, exist_ok=True)
    items: list[dict[str, Any]] = []
    for origin in request["origins"]:
        gw = origin["gw"]
        roles: dict[str, Any] = {}
        for role, spec in origin["sources"].items():
            raw = catalog[spec["source_id"]]
            rel = f"gw{gw:02d}_{role}.bin"
            (src_dir / rel).write_bytes(raw)
            roles[role] = {**{k: v for k, v in spec.items() if k != "source_id"}, "file": rel}
        items.append(
            {
                "season": origin["season"],
                "gw": gw,
                "deadline": origin["deadline"],
                "prev_deadline": origin.get("prev_deadline"),
                "max_kickoff_utc": origin["max_kickoff_utc"],
                "disclosed_limitations": origin.get("disclosed_limitations", []),
                "sources": roles,
            }
        )
    batch_file = src_dir / "batch.json"
    batch_file.write_text(
        json.dumps(
            {
                "track": request["track"],
                "season": request["season"],
                "purpose": request.get("purpose", "validation"),
                "checkpoint_gw": request.get("checkpoint_gw"),
                "shared_chip_calendar": request.get("shared_chip_calendar", []),
                "anchor": request.get("anchor", {}),
                "origins": items,
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return batch_file


def test_produce_validation_evidence_collect_gaps_and_freeze(tmp_path: Path) -> None:
    from commands.produce_validation_evidence import main as produce_main

    req, cat, _ = _build_empirical_bundle(
        gws=(1, 2, 3),
        track="validation_fplcache",
        season="2026-27",
        seed_season="2025-26",
        bootstrap_age_hours=6.0,
        fixtures_age_hours=1.5,
        partial_prefix=False,
        checkpoint_gw=15,
        with_manager=False,
    )
    batch = _write_origin_manifest_inputs(tmp_path / "stage", req, cat)
    evidence_root = tmp_path / "validation-evidence"

    rc = produce_main(
        [
            "collect",
            "--evidence-root",
            str(evidence_root),
            "--batch-json",
            str(batch),
            "--slate-id",
            "slate-2026-27",
        ]
    )
    assert rc == 0

    blobs_dir = evidence_root / "blobs"
    assert blobs_dir.is_dir() and any(blobs_dir.iterdir())
    ctx_file = evidence_root / "admissions" / "2026-27" / "gw03.json"
    assert ctx_file.is_file()
    ctx_obj = json.loads(ctx_file.read_text(encoding="utf-8"))
    assert all(isinstance(v, dict) and "blob_sha256" in v for v in ctx_obj["catalog"].values())

    scorecard = load_and_verify_scorecard(evidence_root / "latest_scorecard.json")
    assert scorecard.settled_through_gw == 3
    assert scorecard.gap_status == "complete"
    assert scorecard.first_blocked_gw is None

    # Inject transient gap at GW4 (data_checked=False) -> scorecard records transient_gap
    req4, cat4, _ = _build_empirical_bundle(
        gws=(1, 2, 3, 4),
        track="validation_fplcache",
        season="2026-27",
        seed_season="2025-26",
        bootstrap_age_hours=6.0,
        fixtures_age_hours=1.5,
        partial_prefix=False,
        checkpoint_gw=15,
        with_manager=False,
    )
    req4["origins"][3]["sources"]["outcomes"]["data_checked"] = False
    batch4 = _write_origin_manifest_inputs(tmp_path / "stage_gap", req4, cat4)
    rc_gap = produce_main(
        [
            "collect",
            "--evidence-root",
            str(evidence_root),
            "--batch-json",
            str(batch4),
            "--slate-id",
            "slate-2026-27",
        ]
    )
    assert rc_gap == 0
    sc_gap = load_and_verify_scorecard(evidence_root / "latest_scorecard.json")
    assert sc_gap.gap_status == "transient_gap"
    assert sc_gap.first_blocked_gw == 4
    assert sc_gap.settled_through_gw == 3

    # Freeze slate & verify duplicate freeze with modified candidates fails closed
    rc_freeze = produce_main(
        [
            "freeze",
            "--evidence-root",
            str(evidence_root),
            "--season",
            "2026-27",
            "--development-season",
            "2025-26",
            "--champion",
            "calibrated_matchup_hybrid",
            "--candidates",
            "metrics_component_hybrid",
            "--slate-id",
            "slate-2026-27",
            "--approval-reference",
            "approved-test-slate",
        ]
    )
    assert rc_freeze == 0
    assert (evidence_root / "selection.json").is_file()
    assert (evidence_root / "protocol.json").is_file()
    assert (evidence_root / "registry.jsonl").is_file()
    reg_records = ConfirmationRegistry(evidence_root / "registry.jsonl").load_all_records()
    assert len(reg_records) == 1 and reg_records[0].candidate_name == "metrics_component_hybrid"
    assert (evidence_root / "slate.json").is_file()

    with pytest.raises(ValueError, match="already sealed"):
        produce_main(
            [
                "freeze",
                "--evidence-root",
                str(evidence_root),
                "--season",
                "2026-27",
                "--development-season",
                "2025-26",
                "--champion",
                "calibrated_matchup_hybrid",
                "--candidates",
                "def_xg_shrink_challenger",
                "--slate-id",
                "slate-2026-27",
                "--approval-reference",
                "approved-test-slate",
            ]
        )


def test_produce_validation_evidence_replay_gaps_exclusions_and_s1_guard_bootstrap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from commands.produce_validation_evidence import main as produce_main

    # 1. bootstrap-s1-baseline refuses active_validation 2026-27
    lc_path = tmp_path / "season_lifecycle.json"
    lc_path.write_text(Path("config/season_lifecycle.json").read_text(encoding="utf-8"), encoding="utf-8")
    with pytest.raises(ValueError, match="active_validation|sealed|2027-28"):
        produce_main(
            [
                "bootstrap-s1-baseline",
                "--evidence-root",
                str(tmp_path / "ev_refuse"),
                "--season",
                "2026-27",
                "--development-season",
                "2025-26",
                "--archive-processed-dir",
                str(tmp_path / "unused"),
                "--champion",
                "calibrated_matchup_hybrid",
            ]
        )

    # 2. Permanent gap recorded cleanly and replay fails closed on incomplete prefix
    req_bad, cat_bad, _ = _build_empirical_bundle(
        gws=(1,),
        track="validation_fplcache",
        season="2026-27",
        seed_season="2025-26",
        bootstrap_age_hours=28.0,
        fixtures_age_hours=1.5,
        partial_prefix=False,
        checkpoint_gw=15,
        with_manager=False,
    )
    batch_bad = _write_origin_manifest_inputs(tmp_path / "bad_stage", req_bad, cat_bad)
    ev_perm = tmp_path / "ev_perm"
    produce_main(["collect", "--evidence-root", str(ev_perm), "--batch-json", str(batch_bad), "--slate-id", "s1"])
    sc_perm = load_and_verify_scorecard(ev_perm / "latest_scorecard.json")
    assert sc_perm.gap_status == "permanent_gap" and sc_perm.first_blocked_gw == 1

    produce_main(
        [
            "freeze",
            "--evidence-root",
            str(ev_perm),
            "--season",
            "2026-27",
            "--development-season",
            "2025-26",
            "--champion",
            "calibrated_matchup_hybrid",
            "--candidates",
            "metrics_component_hybrid",
            "--slate-id",
            "s1",
            "--approval-reference",
            "approved-s1",
        ]
    )
    with pytest.raises(ValueError, match="incomplete|blocked"):
        produce_main(
            [
                "replay",
                "--evidence-root",
                str(ev_perm),
                "--season",
                "2026-27",
                "--checkpoint-gw",
                "15",
            ]
        )

    # 3. 2027-28 S-1 Season Archive transition bootstrap with isolated rolled-over lifecycle
    monkeypatch.setattr("backtesting.season_rules.DEFAULT_LIFECYCLE_PATH", lc_path)
    lc_data = json.loads(lc_path.read_text(encoding="utf-8"))
    lc_data["active_season"] = "2027-28"
    lc_data["seasons"]["2026-27"] = {
        "role": "development",
        "cycle_slot": "S-1",
        "prior_seed": "2025-26",
        "rules_id": "native-2026-27-v1",
    }
    lc_data["seasons"]["2025-26"]["role"] = "historical_filter"
    lc_data["seasons"]["2025-26"]["cycle_slot"] = "S-2"
    lc_data["seasons"]["2027-28"] = {
        "role": "active_validation",
        "cycle_slot": "S",
        "prior_seed": "2026-27",
        "rules_id": "native-2026-27-v1",
    }
    lc_path.write_text(json.dumps(lc_data), encoding="utf-8")

    arch = tmp_path / "synthetic_2026_27_processed"
    arch.mkdir()
    pd.DataFrame([{"id": 1, "position_id": 2, "club_id": 1, "now_cost": 50}]).to_parquet(arch / "players.parquet", index=False)
    pd.DataFrame([{"id": 1, "gameweek_id": 1, "home_club_id": 1, "away_club_id": 2, "finished": True}]).to_parquet(
        arch / "fixtures.parquet", index=False
    )
    perf_row: dict[str, Any] = {
        "player_id": 1,
        "fixture_id": 1,
        "gameweek_id": 1,
        "minutes": 90,
        "total_points": 6,
    }
    for _gname, (fcol, acol, _loss, _units) in GUARD_SEMANTICS.items():
        perf_row[fcol] = 0.0
        perf_row[acol] = 0.0
    pd.DataFrame([perf_row]).to_parquet(arch / "player_performances.parquet", index=False)
    pd.DataFrame([{"id": 1, "finished": True, "data_checked": True}]).to_parquet(arch / "gameweeks.parquet", index=False)

    ev_27 = tmp_path / "ev_2027_28"
    rc_boot = produce_main(
        [
            "bootstrap-s1-baseline",
            "--evidence-root",
            str(ev_27),
            "--season",
            "2027-28",
            "--development-season",
            "2026-27",
            "--archive-processed-dir",
            str(arch),
            "--champion",
            "calibrated_matchup_hybrid",
        ]
    )
    assert rc_boot == 0
    assert (ev_27 / "s1_guard_baseline.json").is_file()
    baseline = json.loads((ev_27 / "s1_guard_baseline.json").read_text(encoding="utf-8"))
    assert baseline["season"] == "2026-27" and len(baseline["rows"]) == 1
    assert len(baseline["archive_manifest_sha256"]) == 64

    # 4. ExclusionLedger recording prevents future inclusion
    excl = ExclusionLedger(ev_27 / "exclusions.jsonl")
    excl.record_exclusion(
        slate_id="slate-2027-28",
        season="2027-28",
        candidate_name="metrics_component_hybrid",
        checkpoint_gw=15,
        reason_code="early_harm",
        details="Early harm triggered",
    )
    assert excl.is_excluded("metrics_component_hybrid", season="2027-28") is True


def test_produce_validation_evidence_replay_reuses_prefix_and_packs_passing_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backtesting import promotion_evidence
    from backtesting.promotion_evidence import DualTierCheckpointResult
    from commands.produce_validation_evidence import main as produce_main
    from models.calibrated_matchup_hybrid import CalibratedMatchupHybridModel

    ev_root = tmp_path / "ev_replay"
    req_s1, cat_s1, _ = _build_empirical_bundle(gws=(1, 2), with_manager=False)
    req_s, cat_s, _ = _build_empirical_bundle(
        gws=tuple(range(1, 16)),
        track="validation_fplcache",
        season="2026-27",
        seed_season="2025-26",
        bootstrap_age_hours=6.0,
        fixtures_age_hours=1.5,
        partial_prefix=False,
        checkpoint_gw=15,
        with_manager=False,
    )

    batch_s1 = _write_origin_manifest_inputs(tmp_path / "s1", req_s1, cat_s1)
    batch_s = _write_origin_manifest_inputs(tmp_path / "s", req_s, cat_s)
    assert produce_main(["collect", "--evidence-root", str(ev_root), "--batch-json", str(batch_s1), "--slate-id", "sl1"]) == 0
    assert produce_main(["collect", "--evidence-root", str(ev_root), "--batch-json", str(batch_s), "--slate-id", "sl1"]) == 0
    assert (
        produce_main(
            [
                "freeze",
                "--evidence-root",
                str(ev_root),
                "--season",
                "2026-27",
                "--development-season",
                "2025-26",
                "--champion",
                "calibrated_matchup_hybrid",
                "--candidates",
                "metrics_component_hybrid",
                "--slate-id",
                "sl1",
                "--approval-reference",
                "app-1",
                "--time-limit-seconds",
                "120",
            ]
        )
        == 0
    )

    predict_calls: list[int] = []
    orig_predict = CalibratedMatchupHybridModel.predict

    def spy_predict(self: CalibratedMatchupHybridModel, features_df: Any, horizon: int) -> Any:
        predict_calls.append(1)
        return orig_predict(self, features_df, horizon)

    monkeypatch.setattr(CalibratedMatchupHybridModel, "predict", spy_predict)

    bundle_out = ev_root / "bundle_inconclusive.json"
    snap_dir = ev_root / "snapshots"
    monkeypatch.setattr(
        promotion_evidence,
        "evaluate_dual_tier_checkpoint",
        lambda **kwargs: DualTierCheckpointResult(
            checkpoint_gw=kwargs["checkpoint_gw"],
            num_finalists=1,
            alpha_spent=0.05,
            action="retain_dual_tier",
            recommended_champion=None,
            next_provisional_active="metrics_component_hybrid",
            requires_manual_adopt=False,
            outcomes={},
            reasons=("test inconclusive",),
        ),
    )
    rc = produce_main(
        [
            "replay",
            "--evidence-root",
            str(ev_root),
            "--season",
            "2026-27",
            "--checkpoint-gw",
            "15",
            "--output-bundle",
            str(bundle_out),
            "--snapshots-dir",
            str(snap_dir),
        ]
    )
    assert rc == 0
    assert bundle_out.is_file()
    assert len(predict_calls) > 0
    assert not snap_dir.exists() or not list(snap_dir.glob("*.tar.gz"))

    # Second run reuses forecast & replay prefix caches with 0 model predict() calls and packs passing snapshot
    predict_calls.clear()
    monkeypatch.setattr(
        promotion_evidence,
        "evaluate_dual_tier_checkpoint",
        lambda **kwargs: DualTierCheckpointResult(
            checkpoint_gw=kwargs["checkpoint_gw"],
            num_finalists=1,
            alpha_spent=0.05,
            action="eligible_for_manual_adopt",
            recommended_champion="metrics_component_hybrid",
            next_provisional_active="metrics_component_hybrid",
            requires_manual_adopt=True,
            outcomes={},
            reasons=("test pass",),
        ),
    )
    bundle_pass = ev_root / "bundle_pass.json"
    rc_pass = produce_main(
        [
            "replay",
            "--evidence-root",
            str(ev_root),
            "--season",
            "2026-27",
            "--checkpoint-gw",
            "15",
            "--output-bundle",
            str(bundle_pass),
            "--snapshots-dir",
            str(snap_dir),
        ]
    )
    assert rc_pass == 0
    assert predict_calls == []
    archives = list(snap_dir.glob("*.tar.gz"))
    manifests = list(snap_dir.glob("*.manifest.json"))
    assert len(archives) == 1 and len(manifests) == 1
    verified = verify_checkpoint_snapshot_archive(
        archives[0],
        manifest_path=manifests[0],
        expected_champion="calibrated_matchup_hybrid",
        canonical_registry_path=ev_root / "registry.jsonl",
        canonical_exclusions_path=ev_root / "exclusions.jsonl",
    )
    assert verified["bundle"]["recommended_champion"] == "metrics_component_hybrid"
    assert BlobStore(ev_root).root == ev_root.resolve()


def test_validation_collector_workflow_contract() -> None:
    wf_path = Path(".github/workflows/validation-collector.yml")
    assert wf_path.is_file(), "Unified validation collector workflow missing"
    text = wf_path.read_text(encoding="utf-8")
    assert "ubuntu-24.04" in text
    assert "ubuntu-latest" not in text
    assert "uv sync --frozen" in text
    assert "group: validation-evidence" in text
    assert "vars.CHAMPION_ADOPTION_LIVE_ENABLED == 'true'" in text
    assert "workflow_dispatch" in text
    assert "commands.produce_validation_evidence" in text
    assert "validation-evidence" in text
    assert "has_passing_snapshot == 'true'" in text
