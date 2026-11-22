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


def test_produce_validation_evidence_immutable_admissions_v2_freeze_exclusions_and_s1_margins(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify incremental collect immutability, v2 freeze metadata, reservation-guarded exclusions, and S-1 margin roundtrip."""
    import hashlib
    from backtesting import adoption_transaction, promotion_evidence
    from backtesting.promotion_evidence import DualTierCheckpointResult, derive_s1_guard_margins
    from commands.produce_validation_evidence import main as produce_main

    ev_root = tmp_path / "ev_v2"
    req_s1, cat_s1, _ = _build_empirical_bundle(gws=(1, 2), with_manager=False)
    batch_s1 = _write_origin_manifest_inputs(tmp_path / "s1", req_s1, cat_s1)
    assert produce_main(["collect", "--evidence-root", str(ev_root), "--batch-json", str(batch_s1), "--slate-id", "sl-v2"]) == 0

    req1, cat1, _ = _build_empirical_bundle(
        gws=(1,), track="validation_fplcache", season="2026-27", seed_season="2025-26",
        bootstrap_age_hours=6.0, fixtures_age_hours=1.5, partial_prefix=False, checkpoint_gw=15, with_manager=False,
    )
    batch1 = _write_origin_manifest_inputs(tmp_path / "g1", req1, cat1)
    assert produce_main(["collect", "--evidence-root", str(ev_root), "--batch-json", str(batch1), "--slate-id", "sl-v2"]) == 0
    gw01_path = ev_root / "admissions" / "2026-27" / "gw01.json"
    gw01_before = hashlib.sha256(gw01_path.read_bytes()).hexdigest()

    # Incremental GW2 collection preserves GW1 admission byte-for-byte
    req2, cat2, _ = _build_empirical_bundle(
        gws=(1, 2), track="validation_fplcache", season="2026-27", seed_season="2025-26",
        bootstrap_age_hours=6.0, fixtures_age_hours=1.5, partial_prefix=False, checkpoint_gw=15, with_manager=False,
    )
    batch2 = _write_origin_manifest_inputs(tmp_path / "g2", {**req2, "origins": [req2["origins"][1]]}, cat2)
    assert produce_main(["collect", "--evidence-root", str(ev_root), "--batch-json", str(batch2), "--slate-id", "sl-v2"]) == 0
    assert hashlib.sha256(gw01_path.read_bytes()).hexdigest() == gw01_before

    # Default freeze writes v2.0 protocol and binds frozen hashes onto selection.json
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
                "metrics_component_hybrid,def_xg_shrink_challenger",
                "--slate-id",
                "sl-v2",
                "--approval-reference",
                "app-v2",
                "--time-limit-seconds",
                "120",
            ]
        )
        == 0
    )
    sel_obj = json.loads((ev_root / "selection.json").read_text(encoding="utf-8"))
    proto_obj = json.loads((ev_root / "protocol.json").read_text(encoding="utf-8"))
    assert proto_obj["statistics"]["protocol_version"] == "v2.0"
    assert proto_obj["statistics"]["certification_digest"]
    assert len(sel_obj["frozen_protocol_hash"]) == 64
    assert sel_obj["frozen_certification_digest"] == proto_obj["statistics"]["certification_digest"]

    # Configure a GW15 checkpoint in an isolated ev_root to verify staged admissions and reservation-guarded exclusions
    ev_fast = tmp_path / "ev_fast"
    req15, cat15, _ = _build_empirical_bundle(
        gws=tuple(range(1, 16)), track="validation_fplcache", season="2026-27", seed_season="2025-26",
        bootstrap_age_hours=6.0, fixtures_age_hours=1.5, partial_prefix=False, checkpoint_gw=15, with_manager=False,
    )
    batch15 = _write_origin_manifest_inputs(tmp_path / "g15", req15, cat15)
    assert produce_main(["collect", "--evidence-root", str(ev_fast), "--batch-json", str(batch_s1), "--slate-id", "sl-fast"]) == 0
    assert produce_main(["collect", "--evidence-root", str(ev_fast), "--batch-json", str(batch15), "--slate-id", "sl-fast"]) == 0
    assert (
        produce_main(
            [
                "freeze",
                "--evidence-root",
                str(ev_fast),
                "--season",
                "2026-27",
                "--development-season",
                "2025-26",
                "--champion",
                "calibrated_matchup_hybrid",
                "--candidates",
                "metrics_component_hybrid,def_xg_shrink_challenger",
                "--slate-id",
                "sl-fast",
                "--approval-reference",
                "app-fast",
                "--time-limit-seconds",
                "120",
            ]
        )
        == 0
    )
    fast_gw01_sha = hashlib.sha256((ev_fast / "admissions" / "2026-27" / "gw01.json").read_bytes()).hexdigest()
    fast_gw15_sha = hashlib.sha256((ev_fast / "admissions" / "2026-27" / "gw15.json").read_bytes()).hexdigest()

    recorded_via_coord: list[str] = []
    orig_record_excl = adoption_transaction.SharedReservationCoordinator.record_exclusion_under_reservation

    def spy_record_excl(self: Any, **kwargs: Any) -> Any:
        recorded_via_coord.append(str(kwargs["candidate_name"]))
        return orig_record_excl(self, **kwargs)

    monkeypatch.setattr(
        adoption_transaction.SharedReservationCoordinator,
        "record_exclusion_under_reservation",
        spy_record_excl,
    )
    monkeypatch.setattr(
        promotion_evidence,
        "evaluate_dual_tier_checkpoint",
        lambda **kwargs: DualTierCheckpointResult(
            checkpoint_gw=kwargs["checkpoint_gw"],
            num_finalists=2,
            alpha_spent=0.05,
            action="rotate_to_backup",
            recommended_champion=None,
            next_provisional_active="def_xg_shrink_challenger",
            requires_manual_adopt=False,
            outcomes={},
            reasons=("Early-Harm for Provisional Active 'metrics_component_hybrid'",),
            excluded_finalists=("metrics_component_hybrid",),
            newly_excluded_finalists=("metrics_component_hybrid",),
        ),
    )

    assert (
        produce_main(
            [
                "replay",
                "--evidence-root",
                str(ev_fast),
                "--season",
                "2026-27",
                "--checkpoint-gw",
                "15",
                "--evaluated-at-utc",
                "2026-12-01T18:00:00Z",
            ]
        )
        == 0
    )
    # admissions/ remained byte-identical; staged admission written under checkpoints/
    assert hashlib.sha256((ev_fast / "admissions" / "2026-27" / "gw01.json").read_bytes()).hexdigest() == fast_gw01_sha
    assert hashlib.sha256((ev_fast / "admissions" / "2026-27" / "gw15.json").read_bytes()).hexdigest() == fast_gw15_sha
    assert (ev_fast / "checkpoints" / "2026-27" / "gw15_admission.json").is_file()
    assert recorded_via_coord == ["metrics_component_hybrid"]
    excl = ExclusionLedger(ev_fast / "exclusions.jsonl")
    assert excl.is_candidate_excluded("metrics_component_hybrid", slate_id="sl-fast", season="2026-27") is True

    # Subsequent replay skips already-excluded finalist (does not replay or re-record checkpoint for it)
    from models.metrics_component_hybrid import MetricsComponentHybridModel

    excl_predicts: list[int] = []
    monkeypatch.setattr(MetricsComponentHybridModel, "predict", lambda self, df, h: excl_predicts.append(1))
    monkeypatch.setattr(
        promotion_evidence,
        "evaluate_dual_tier_checkpoint",
        lambda **kwargs: DualTierCheckpointResult(
            checkpoint_gw=kwargs["checkpoint_gw"],
            num_finalists=1,
            alpha_spent=0.05,
            action="retain_dual_tier",
            recommended_champion=None,
            next_provisional_active="def_xg_shrink_challenger",
            requires_manual_adopt=False,
            outcomes={},
            reasons=("retain remaining finalist",),
            excluded_finalists=("metrics_component_hybrid",),
            newly_excluded_finalists=(),
        ),
    )
    assert (
        produce_main(
            [
                "replay",
                "--evidence-root",
                str(ev_fast),
                "--season",
                "2026-27",
                "--checkpoint-gw",
                "15",
                "--output-bundle",
                str(ev_fast / "bundle_after_excl.json"),
                "--evaluated-at-utc",
                "2026-12-01T18:00:00Z",
            ]
        )
        == 0
    )
    assert excl_predicts == []

    # bootstrap-s1-baseline rows are directly compatible with derive_s1_guard_margins()
    lc_path = tmp_path / "season_lifecycle.json"
    lc_data = json.loads(Path("config/season_lifecycle.json").read_text(encoding="utf-8"))
    lc_data["active_season"] = "2027-28"
    lc_data["seasons"]["2026-27"] = {"role": "development", "cycle_slot": "S-1", "prior_seed": "2025-26", "rules_id": "native-2026-27-v1"}
    lc_data["seasons"]["2025-26"] = {"role": "historical_filter", "cycle_slot": "S-2", "prior_seed": "2024-25", "rules_id": "native-2025-26-v1"}
    lc_data["seasons"]["2027-28"] = {"role": "active_validation", "cycle_slot": "S", "prior_seed": "2026-27", "rules_id": "native-2026-27-v1"}
    lc_path.write_text(json.dumps(lc_data), encoding="utf-8")
    monkeypatch.setattr("backtesting.season_rules.DEFAULT_LIFECYCLE_PATH", lc_path)

    arch = tmp_path / "s1_arch"
    arch.mkdir()
    pd.DataFrame([{"id": 1, "position_id": 2, "club_id": 1, "now_cost": 50}]).to_parquet(arch / "players.parquet", index=False)
    pd.DataFrame(
        [
            {"id": 1, "gameweek_id": 1, "home_club_id": 1, "away_club_id": 2, "finished": True},
            {"id": 2, "gameweek_id": 2, "home_club_id": 1, "away_club_id": 2, "finished": True},
        ]
    ).to_parquet(arch / "fixtures.parquet", index=False)
    perf_rows: list[dict[str, Any]] = []
    for gw_i, pts in ((1, 6), (2, 2)):
        perf_row: dict[str, Any] = {"player_id": 1, "fixture_id": gw_i, "gameweek_id": gw_i, "minutes": 90, "total_points": pts}
        for _g, (fcol, acol, _loss, _u) in GUARD_SEMANTICS.items():
            perf_row[fcol] = 0.0
            perf_row[acol] = 0.0
        perf_rows.append(perf_row)
    pd.DataFrame(perf_rows).to_parquet(arch / "player_performances.parquet", index=False)
    pd.DataFrame(
        [
            {"id": 1, "finished": True, "data_checked": True},
            {"id": 2, "finished": True, "data_checked": True},
        ]
    ).to_parquet(arch / "gameweeks.parquet", index=False)

    ev_boot = tmp_path / "ev_boot"
    assert (
        produce_main(
            [
                "bootstrap-s1-baseline",
                "--evidence-root",
                str(ev_boot),
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
        == 0
    )
    s1_base = json.loads((ev_boot / "s1_guard_baseline.json").read_text(encoding="utf-8"))
    margins = derive_s1_guard_margins(s1_base["rows"])
    assert set(margins) == set(GUARD_SEMANTICS)


def test_collect_live_validation_evidence_http_modes_concurrency_and_retry(tmp_path: Path) -> None:
    """Test 2-call pre-deadline, 3-call post-settlement, DGW element-summary <=3 concurrency, and 429 Retry-After."""
    import csv
    from datetime import datetime, timedelta
    import io
    import lzma
    import threading
    import time
    import httpx
    from commands.produce_validation_evidence import collect_live_validation_evidence

    req_tpl, cat_tpl, _ = _build_empirical_bundle(
        gws=(1,), track="validation_fplcache", season="2026-27", seed_season="2025-26",
        bootstrap_age_hours=6.0, fixtures_age_hours=1.5, partial_prefix=False, checkpoint_gw=15, with_manager=False,
    )
    o1 = req_tpl["origins"][0]
    bs_payload = json.loads(lzma.decompress(cat_tpl[o1["sources"]["bootstrap"]["source_id"]]).decode("utf-8"))
    fx_csv = cat_tpl[o1["sources"]["fixtures"]["source_id"]].decode("utf-8")
    seed_obj = json.loads(cat_tpl[o1["sources"]["seed"]["source_id"]].decode("utf-8"))

    seed_path = tmp_path / "seed_2025_26.json"
    seed_path.write_text(
        json.dumps(
            {
                "season": "2025-26",
                "defensive_contribution_status": seed_obj.get("defensive_contribution_status", "native"),
                "players": seed_obj["players"],
                "history": seed_obj["history"],
                "fixtures": seed_obj.get("fixtures", []),
            }
        ),
        encoding="utf-8",
    )

    dl1 = datetime.fromisoformat(o1["deadline"].replace("Z", "+00:00"))
    ko1 = dl1 + timedelta(days=1)
    fx_json = [
        {
            "id": int(r["id"]),
            "event": int(r["event"]),
            "team_h": int(r["team_h"]),
            "team_a": int(r["team_a"]),
            "kickoff_time": ko1.isoformat().replace("+00:00", "Z") if int(r["event"]) == 1 else r["kickoff_time"],
            "team_h_difficulty": int(r["team_h_difficulty"]),
            "team_a_difficulty": int(r["team_a_difficulty"]),
            "finished": False,
            "finished_provisional": False,
            "minutes": 0,
        }
        for r in csv.DictReader(io.StringIO(fx_csv))
    ]
    bs_payload["events"][0] = {
        "id": 1,
        "deadline_time": dl1.isoformat().replace("+00:00", "Z"),
        "is_next": True,
        "finished": False,
        "data_checked": False,
    }

    lock = threading.Lock()
    in_flight = 0
    max_seen = 0
    retried_429 = 0
    saw_first_summary = False
    phase = {"settled": False}

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal in_flight, max_seen, retried_429, saw_first_summary
        path = request.url.path
        if path.endswith("/bootstrap-static/"):
            return httpx.Response(200, json=bs_payload)
        if path.endswith("/fixtures/"):
            return httpx.Response(200, json=fx_json)
        if path.endswith("/event/1/live/"):
            return httpx.Response(
                200,
                json={
                    "elements": [
                        {"id": el["id"], "stats": {"minutes": 90, "total_points": 2}}
                        for el in bs_payload["elements"]
                    ]
                },
            )
        if "/element-summary/" in path:
            with lock:
                in_flight += 1
                max_seen = max(max_seen, in_flight)
                do_429 = not saw_first_summary
                saw_first_summary = True
                if do_429:
                    retried_429 += 1
            try:
                time.sleep(0.01)
                if do_429:
                    return httpx.Response(429, headers={"Retry-After": "0"})
                return httpx.Response(
                    200,
                    json={
                        "history": [
                            {"round": 1, "fixture": 1, "minutes": 45, "total_points": 1},
                            {"round": 1, "fixture": 3, "minutes": 45, "total_points": 1},
                        ]
                    },
                )
            finally:
                with lock:
                    in_flight -= 1
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    ev_root = tmp_path / "live_ev"

    # Phase 1: pre-deadline (dl1 - 6h)
    res_pre = collect_live_validation_evidence(
        evidence_root=ev_root,
        season="2026-27",
        slate_id="live-slate",
        mode="pre_deadline",
        fpl_api_base="https://mock.fpl/api",
        now_utc=(dl1 - timedelta(hours=6)).isoformat(),
        max_concurrency=3,
        seed_file=seed_path,
        transport=transport,
    )
    assert res_pre["settled_through_gw"] == 0
    assert (ev_root / "admissions" / "2026-27" / "gw01.json").is_file()

    # Phase 2: post-settlement (> max_kickoff + 24h, finished & data_checked)
    phase["settled"] = True
    bs_payload["events"][0]["finished"] = True
    bs_payload["events"][0]["data_checked"] = True
    bs_payload["events"][0]["is_next"] = False
    for f in fx_json:
        if f["event"] == 1:
            f["finished"] = True
            f["minutes"] = 90

    res_post = collect_live_validation_evidence(
        evidence_root=ev_root,
        season="2026-27",
        slate_id="live-slate",
        mode="post_settlement",
        fpl_api_base="https://mock.fpl/api",
        now_utc=(ko1 + timedelta(hours=26)).isoformat(),
        max_concurrency=3,
        seed_file=seed_path,
        transport=transport,
    )
    assert res_post["settled_through_gw"] == 1, json.dumps(res_post)
    assert res_post["gap_status"] == "complete", json.dumps(res_post)
    assert retried_429 >= 1
    assert 1 <= max_seen <= 3


def test_pre_deadline_live_fallback_away_player_and_weekly_scorecard_subcommand(tmp_path: Path) -> None:
    """Verify <24h live history computes away was_home/opponent and scorecard subcommand leaves registry untouched."""
    from datetime import UTC, datetime, timedelta
    import httpx
    from backtesting.confirmation_registry import ConfirmationRegistry
    from backtesting.portable_evidence import BlobStore, load_and_verify_scorecard
    from commands.produce_validation_evidence import (
        _compose_pre_deadline_history,
        main as produce_main,
    )

    # 1. _compose_pre_deadline_history <24h fallback computes accurate was_home and opponent_club_id for away player
    dl_dt = datetime(2026, 8, 22, 10, 0, tzinfo=UTC)
    fx_ko = (dl_dt - timedelta(hours=12)).isoformat().replace("+00:00", "Z")
    live_transport = httpx.MockTransport(
        lambda req: httpx.Response(
            200,
            json={
                "elements": [
                    {
                        "id": 99,
                        "stats": {"minutes": 90, "total_points": 7},
                        "explain": [{"fixture": 10}],
                    }
                ]
            },
        )
        if req.url.path.endswith("/event/1/live/")
        else httpx.Response(404)
    )
    with httpx.Client(base_url="https://mock.fpl/api", transport=live_transport) as client:
        hist_rows = _compose_pre_deadline_history(
            store=BlobStore(tmp_path / "hist_ev"),
            season="2026-27",
            target_gw=2,
            deadline_dt=dl_dt,
            origins_by_gw={},
            ext_catalog={},
            client=client,
            events_by_id={1: {"id": 1, "finished": True}},
            fixtures_by_gw={
                1: [{"id": 10, "team_h": 5, "team_a": 12, "finished": True, "kickoff_time": fx_ko}]
            },
            pos_by_id={99: 3},
            team_by_id={99: 12},
        )
    assert len(hist_rows) == 1
    assert hist_rows[0]["player_id"] == 99
    assert hist_rows[0]["was_home"] is False
    assert hist_rows[0]["opponent_club_id"] == 5

    # 2. scorecard subcommand publishes non-empty GW2 scorecard and never modifies registry.jsonl
    ev_sc = tmp_path / "ev_sc"
    req_s1, cat_s1, _ = _build_empirical_bundle(gws=(1, 2), with_manager=False)
    batch_s1 = _write_origin_manifest_inputs(tmp_path / "sc_s1", req_s1, cat_s1)
    assert produce_main(["collect", "--evidence-root", str(ev_sc), "--batch-json", str(batch_s1), "--slate-id", "sl-sc"]) == 0

    req_s, cat_s, _ = _build_empirical_bundle(
        gws=(1, 2), track="validation_fplcache", season="2026-27", seed_season="2025-26",
        bootstrap_age_hours=6.0, fixtures_age_hours=1.5, partial_prefix=False, checkpoint_gw=15, with_manager=False,
    )
    batch_s = _write_origin_manifest_inputs(tmp_path / "sc_s", req_s, cat_s)
    assert produce_main(["collect", "--evidence-root", str(ev_sc), "--batch-json", str(batch_s), "--slate-id", "sl-sc"]) == 0

    assert (
        produce_main(
            [
                "freeze",
                "--evidence-root",
                str(ev_sc),
                "--season",
                "2026-27",
                "--development-season",
                "2025-26",
                "--champion",
                "calibrated_matchup_hybrid",
                "--candidates",
                "metrics_component_hybrid,def_xg_shrink_challenger",
                "--slate-id",
                "sl-sc",
                "--approval-reference",
                "app-sc",
                "--time-limit-seconds",
                "120",
            ]
        )
        == 0
    )
    reg_before = (ev_sc / "registry.jsonl").read_bytes()
    assert (
        produce_main(
            [
                "scorecard",
                "--evidence-root",
                str(ev_sc),
                "--season",
                "2026-27",
                "--through-gw",
                "2",
            ]
        )
        == 0
    )
    assert (ev_sc / "registry.jsonl").read_bytes() == reg_before
    for rec in ConfirmationRegistry(ev_sc / "registry.jsonl").load_all_records():
        assert rec.completed_gameweeks == ()

    latest_sc = load_and_verify_scorecard(ev_sc / "latest_scorecard.json")
    gw02_sc = load_and_verify_scorecard(ev_sc / "scorecards" / "gw02.json")
    assert latest_sc.settled_through_gw == 2
    assert latest_sc.checkpoint_action == "weekly_scorecard"
    assert set(latest_sc.cumulative_net_points) == {
        "calibrated_matchup_hybrid",
        "metrics_component_hybrid",
        "def_xg_shrink_challenger",
    }
    assert latest_sc.weekly_leader in latest_sc.cumulative_net_points
    assert gw02_sc.scorecard_hash == latest_sc.scorecard_hash


def test_freeze_parser_defaults_certified_time_limit_to_600() -> None:
    from commands.produce_validation_evidence import _build_parser

    parsed = _build_parser().parse_args(
        [
            "freeze",
            "--evidence-root",
            "/tmp/ev",
            "--season",
            "2026-27",
            "--development-season",
            "2025-26",
            "--champion",
            "def_xg_shrink_challenger",
            "--candidates",
            "cand_a",
            "--slate-id",
            "slate-1",
            "--approval-reference",
            "ref-1",
        ]
    )
    assert parsed.time_limit_seconds == 600.0


def test_freeze_rejects_stale_existing_protocol_certification_digest(tmp_path: Path) -> None:
    from commands.produce_validation_evidence import main as produce_main

    ev_root = tmp_path / "ev_stale_proto"
    req_s1, cat_s1, _ = _build_empirical_bundle(gws=(1, 2), with_manager=False)
    batch_s1 = _write_origin_manifest_inputs(tmp_path / "s1", req_s1, cat_s1)
    assert produce_main(["collect", "--evidence-root", str(ev_root), "--batch-json", str(batch_s1), "--slate-id", "sl-stale"]) == 0

    (ev_root / "protocol.json").write_text(
        json.dumps(
            {
                "statistics": {
                    "protocol_version": "v2.0",
                    "certification_digest": "0" * 64,
                }
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="certification_digest does not match CERTIFICATION_DIGEST_EXPECTED"):
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
                "sl-stale",
                "--approval-reference",
                "app-stale",
            ]
        )
