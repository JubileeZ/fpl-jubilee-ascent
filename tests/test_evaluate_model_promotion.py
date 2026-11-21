"""Legacy diagnostic routes cannot grant scientific or adoption authority."""

import json
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from backtesting.metrics import evaluate_predictions
from backtesting.promotion import CONFIRMATION_BOOTSTRAP_MIN_P
from backtesting.walkforward import WalkforwardResult
from commands.evaluate_model_promotion import adopt_champion, evaluate_and_apply, main
from models.selection import ModelSelection, load_model_selection, save_model_selection


def _result(model_name: str, *, worse: bool) -> WalkforwardResult:
    error = 2.0 if worse else 0.5
    frame = pd.DataFrame([{"player_id": pid, "gameweek": gw, "projected_points": 4.0 + error, "actual_points": 4.0, "process_points": 4.0, "blended_points": 4.0, "projected_minutes": 70.0, "actual_minutes": 60.0} for pid, gw in enumerate((2, 10, 25), 1)])
    return WalkforwardResult(model_name, Path("data"), 1, 38, evaluate_predictions(frame), frame, {}, False)


@pytest.mark.parametrize("candidate_worse", [False, True])
def test_legacy_proxy_result_never_recommends_or_mutates_selection(tmp_path: Path, candidate_worse: bool) -> None:
    config_path = tmp_path / "selection.json"
    selection = ModelSelection("metrics_component_hybrid", ("participation_state_hybrid",))
    save_model_selection(selection, config_path)
    with (
        patch("commands.evaluate_model_promotion._run_model", side_effect=lambda *, model_name, **kwargs: _result(model_name, worse=candidate_worse if model_name != selection.champion else True)),
        patch("commands.evaluate_model_promotion.EVIDENCE_DIR", tmp_path / "diagnostics"),
    ):
        updated, comparisons, evidence_paths = evaluate_and_apply(config_path=config_path, data_dir=tmp_path, start_gw=1, end_gw=38, seed_season=None, snapshot_root=None, snapshot_season="2025-26", require_snapshots=False, apply=True)
    assert updated == selection == load_model_selection(config_path)
    assert len(comparisons) == 1
    assert evidence_paths is not None
    payload = json.loads(evidence_paths[0].read_bytes())
    assert payload["scientific_verdict"] == "inconclusive"
    assert payload["execution_status"] == "not_run"
    assert payload["evidence_kind"] == "legacy_proxy_diagnostic"
    assert payload["comparisons"][0]["scientific_verdict"] == "inconclusive"
    with pytest.raises(ValueError, match="Unsupported verified recommendation"):
        adopt_champion(evidence_paths[0], config_path=config_path, approval_ref="human", expected_current_champion=selection.champion, approved_bundle_hash="0" * 64)


@pytest.mark.parametrize("status", [None, "partial", "complete"])
def test_plain_json_with_pass_fields_is_never_verified_evidence(tmp_path: Path, status: str | None) -> None:
    config_path = tmp_path / "selection.json"
    save_model_selection(ModelSelection("champ", ("cand",)), config_path)
    bundle = tmp_path / "bundle.json"
    bundle.write_text(json.dumps({"scientific_verdict": "pass", "execution_status": status, "candidate_name": "cand", "former_champion": "champ", "snapshot_backed": True}))
    with pytest.raises(ValueError, match="Unsupported verified recommendation"):
        adopt_champion(bundle, config_path=config_path, approval_ref="human", expected_current_champion="champ", approved_bundle_hash="a" * 64)
    assert load_model_selection(config_path).champion == "champ"


@pytest.mark.parametrize("options, expected", [
    ({}, "missing required human approval reference"),
    ({"approval_ref": "human"}, "explicit expected current Champion"),
    ({"approval_ref": "human", "expected_current_champion": "champ"}, "exact approved bundle hash"),
])
def test_adoption_requires_explicit_approval_and_exact_identity(tmp_path: Path, options: dict[str, str], expected: str) -> None:
    with pytest.raises(ValueError, match=expected):
        adopt_champion(tmp_path / "absent.json", approval_ref=options.get("approval_ref"), expected_current_champion=options.get("expected_current_champion"))


def test_confirmation_diagnostic_forwards_seed_and_legacy_bar(tmp_path: Path) -> None:
    selection = ModelSelection("champ", ())
    with patch("commands.evaluate_model_promotion.evaluate_and_apply", return_value=(selection, [], None)) as diagnostic:
        main(["--config", str(tmp_path / "selection.json"), "--confirmation"])
    assert diagnostic.call_args.kwargs["seed_season"] == "2023-24"
    assert diagnostic.call_args.kwargs["bootstrap_min_p"] == CONFIRMATION_BOOTSTRAP_MIN_P


def test_two_season_convenience_route_remains_diagnostic(tmp_path: Path) -> None:
    with patch("commands.evaluate_model_promotion.evaluate_and_apply_two_season", return_value=(ModelSelection("champ", ()), [], None)) as diagnostic:
        main(["--config", str(tmp_path / "selection.json"), "--confirmation_data_dir", str(tmp_path / "confirmation")])
    assert diagnostic.call_args.kwargs["dev_seed_season"] == "2024-25"
    assert diagnostic.call_args.kwargs["conf_seed_season"] == "2023-24"


def test_cli_verified_evidence_route_skips_legacy_backtests(tmp_path: Path) -> None:
    with (
        patch("commands.evaluate_model_promotion.write_recommendation_bundle", return_value={"scientific_verdict": "inconclusive", "bundle_hash": "a" * 64}) as evaluate,
        patch("commands.evaluate_model_promotion._run_model") as legacy,
    ):
        main(["--evidence_request", str(tmp_path / "request.json")])
    evaluate.assert_called_once_with(tmp_path / "request.json", tmp_path / "recommendation_bundle.json")
    legacy.assert_not_called()


def test_cli_checkpoint_request_route_is_read_only(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from backtesting.promotion_evidence import MANDATORY_GUARDS

    sel_path = tmp_path / "model_selection.json"
    save_model_selection(
        ModelSelection(
            champion="def_xg_shrink_challenger",
            candidates=("cand_1",),
            provisional_active="cand_1",
            podium_frozen_season="2026-27",
            podium_sealed=True,
        ),
        sel_path,
    )
    req_path = tmp_path / "checkpoint_request.json"
    req_path.write_text(
        json.dumps(
            {
                "checkpoint_gw": 15,
                "selection_path": str(sel_path),
                "podium_order": ["cand_1"],
                "finalist_traces": {
                    "cand_1": [
                        {
                            "season": "2026-27",
                            "gameweek": gw,
                            "candidate_net_points": 60.2 if gw % 2 == 0 else 59.9,
                            "champion_net_points": 60.0,
                        }
                        for gw in range(1, 16)
                    ]
                },
                "finalist_guards": {
                    "cand_1": [
                        {
                            "metric_name": g,
                            "passed": True,
                            "status": "PASS",
                            "estimate": 0.0,
                            "margin": 0.5,
                            "standard_error": 0.1,
                            "ci_lower": -0.2,
                            "ci_upper": 0.2,
                            "coverage": 0.95,
                            "sample_size": 15,
                            "direction": "lower_is_better",
                            "reason": "ok",
                        }
                        for g in sorted(MANDATORY_GUARDS)
                    ]
                },
            }
        ),
        encoding="utf-8",
    )
    before = sel_path.read_text(encoding="utf-8")
    main(["--checkpoint_request", str(req_path)])
    out = json.loads(capsys.readouterr().out)
    assert out["action"] == "retain_dual_tier"
    assert out["checkpoint_gw"] == 15
    assert sel_path.read_text(encoding="utf-8") == before


def test_perform_annual_rollover_resets_provisional_and_carries_confirmed_champion(tmp_path: Path) -> None:
    from backtesting.season_rules import SeasonRules
    from commands.evaluate_model_promotion import perform_annual_rollover

    lc_path = tmp_path / "season_lifecycle.json"
    lc_path.write_text(Path("config/season_lifecycle.json").read_text(encoding="utf-8"), encoding="utf-8")
    sel_path = tmp_path / "model_selection.json"
    save_model_selection(
        ModelSelection(
            champion="def_xg_shrink_challenger",
            candidates=("adaptive_causal_challenger", "club_def_prior_challenger"),
            provisional_active="adaptive_causal_challenger",
            podium_frozen_season="2026-27",
            podium_sealed=True,
        ),
        sel_path,
    )
    rules_27 = SeasonRules("2027-28", "native-2027-28-v1", 5, True, 10, True, True, False)
    bootstrap_gw38 = {"events": [{"id": 38, "finished": True, "data_checked": True}]}

    new_lc, new_sel = perform_annual_rollover(
        new_season="2027-28",
        bootstrap_payload=bootstrap_gw38,
        lifecycle_path=lc_path,
        selection_path=sel_path,
        new_rules=rules_27,
    )
    assert new_lc.active_season == "2027-28"
    assert new_sel.champion == "def_xg_shrink_challenger"
    assert new_sel.provisional_active is None
    assert new_sel.podium_frozen_season is None
    assert new_sel.podium_sealed is False
    persisted = load_model_selection(sel_path)
    assert persisted == new_sel


def test_adopt_champion_race_check_failure_leaves_zero_receipt_on_disk(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from commands import evaluate_model_promotion

    config_path = tmp_path / "model_selection.json"
    initial_sel = ModelSelection(
        champion="def_xg_shrink_challenger",
        candidates=("adaptive_causal_challenger",),
        provisional_active="adaptive_causal_challenger",
        podium_frozen_season="2026-27",
        podium_sealed=True,
    )
    save_model_selection(initial_sel, config_path)
    bundle_path = tmp_path / "bundle.json"
    written = {
        "candidate_name": "adaptive_causal_challenger",
        "former_champion": "def_xg_shrink_challenger",
        "scientific_verdict": "pass",
        "execution_status": "complete",
        "empirical_admission": True,
        "bundle_hash": "a" * 64,
        "protocol_hash": "b" * 64,
    }
    monkeypatch.setattr(evaluate_model_promotion, "verify_recommendation_bundle", lambda *args, **kwargs: written)

    calls = 0
    mutated_sel = ModelSelection(
        champion="club_def_prior_challenger",
        candidates=("adaptive_causal_challenger",),
    )

    def fake_load(path: Path | None = None) -> ModelSelection:
        nonlocal calls
        calls += 1
        return initial_sel if calls == 1 else mutated_sel

    monkeypatch.setattr(evaluate_model_promotion, "load_model_selection", fake_load)

    receipt_path = config_path.with_suffix(".adoption.json")
    with pytest.raises(ValueError, match="Current Champion configuration changed during adoption"):
        adopt_champion(
            bundle_path,
            config_path=config_path,
            approval_ref="GH-APPROVAL-1",
            expected_current_champion="def_xg_shrink_challenger",
            approved_bundle_hash="a" * 64,
            request_id="req-race-1",
            slate_id="slate-2026-27",
        )
    assert not receipt_path.exists()
    assert list(tmp_path.glob("*.tmp*")) == []


def test_adopt_champion_allows_weekly_provisional_active_rotation_but_blocks_slate_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from dataclasses import asdict
    from backtesting.portable_evidence import compute_serving_model_closure
    from backtesting.promotion_evidence import CHECKPOINT_EVIDENCE_V2, content_hash
    from commands import evaluate_model_promotion

    frozen_sel = ModelSelection(
        champion="def_xg_shrink_challenger",
        candidates=("adaptive_causal_challenger", "club_def_prior_challenger"),
        provisional_active="adaptive_causal_challenger",
        podium_frozen_season="2026-27",
        podium_sealed=True,
    )
    frozen_sel_sha = content_hash(asdict(frozen_sel))
    closure = compute_serving_model_closure((frozen_sel.champion, *frozen_sel.candidates))

    config_path = tmp_path / "model_selection.json"
    # Weekly serving rotated provisional_active to club_def_prior_challenger while slate stayed frozen
    rotated_sel = ModelSelection(
        champion="def_xg_shrink_challenger",
        candidates=("adaptive_causal_challenger", "club_def_prior_challenger"),
        provisional_active="club_def_prior_challenger",
        podium_frozen_season="2026-27",
        podium_sealed=True,
    )
    save_model_selection(rotated_sel, config_path)

    bundle_path = tmp_path / "bundle.json"
    bundle_data = {
        "version": CHECKPOINT_EVIDENCE_V2,
        "checkpoint_gw": 15,
        "candidate_name": "adaptive_causal_challenger",
        "former_champion": "def_xg_shrink_challenger",
        "scientific_verdict": "pass",
        "execution_status": "complete",
        "empirical_admission": True,
        "selection_sha256": frozen_sel_sha,
        "serving_model_closure_hash": closure.serving_model_closure_hash,
        "model_runtime_bindings": closure.model_runtime_bindings,
        "bundle_hash": "c" * 64,
        "protocol_hash": "d" * 64,
    }
    bundle_path.write_text(json.dumps(bundle_data), encoding="utf-8")
    monkeypatch.setattr(
        evaluate_model_promotion,
        "verify_checkpoint_recommendation_bundle",
        lambda *args, **kwargs: bundle_data,
    )

    # First test that unsealing or changing candidate set fails closed
    unsealed_path = tmp_path / "unsealed_selection.json"
    save_model_selection(
        ModelSelection(
            champion="def_xg_shrink_challenger",
            candidates=("adaptive_causal_challenger", "club_def_prior_challenger"),
            provisional_active="club_def_prior_challenger",
            podium_frozen_season="2026-27",
            podium_sealed=False,
        ),
        unsealed_path,
    )
    with pytest.raises(ValueError, match="Current sealed podium differs"):
        adopt_champion(
            bundle_path,
            config_path=unsealed_path,
            approval_ref="GH-APPROVAL-2",
            expected_current_champion="def_xg_shrink_challenger",
            approved_bundle_hash="c" * 64,
        )
    assert not unsealed_path.with_suffix(".adoption.json").exists()

    # Now test that weekly provisional_active rotation succeeds and closes slate
    updated = adopt_champion(
        bundle_path,
        config_path=config_path,
        approval_ref="GH-APPROVAL-2",
        expected_current_champion="def_xg_shrink_challenger",
        approved_bundle_hash="c" * 64,
        request_id="req-v2-1",
        slate_id="slate-2026-27",
        approved_commit_sha="e" * 40,
    )
    assert updated.champion == "adaptive_causal_challenger"
    assert updated.podium_sealed is False
    assert updated.provisional_active is None
    assert updated.podium_frozen_season is None
    receipt = json.loads(config_path.with_suffix(".adoption.json").read_text(encoding="utf-8"))
    assert receipt["request_id"] == "req-v2-1"
    assert receipt["slate_id"] == "slate-2026-27"
    assert receipt["approved_commit_sha"] == "e" * 40
    assert receipt["serving_model_closure_hash"] == closure.serving_model_closure_hash
    assert receipt["selection_after"]["champion"] == "adaptive_causal_challenger"
    assert receipt["selection_after"]["podium_sealed"] is False


def test_adopt_champion_with_portable_snapshot_and_ledgers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from dataclasses import asdict
    from backtesting import portable_evidence, promotion_evidence
    from backtesting.confirmation_registry import ConfirmationRegistry
    from backtesting.portable_evidence import (
        AdoptionLedger,
        BlobStore,
        ExclusionLedger,
        compute_serving_model_closure,
        pack_checkpoint_snapshot,
    )
    from backtesting.promotion_evidence import CHECKPOINT_EVIDENCE_V2, content_hash

    root = tmp_path / "evidence"
    root.mkdir()
    frozen_sel = ModelSelection(
        champion="def_xg_shrink_challenger",
        candidates=("adaptive_causal_challenger",),
        provisional_active="adaptive_causal_challenger",
        podium_frozen_season="2026-27",
        podium_sealed=True,
    )
    save_model_selection(frozen_sel, root / "selection.json")
    (root / "protocol.json").write_text('{"windows":{"2025-26":[1,2],"2026-27":[1,2,3]}}', encoding="utf-8")
    (root / "parameters.json").write_text("{}", encoding="utf-8")
    reg = ConfirmationRegistry(root / "registry.jsonl")
    reg.register_finalist(
        candidate_name="adaptive_causal_challenger",
        champion_name="def_xg_shrink_challenger",
        mechanism_family="fam-a",
        model_source_hash="1" * 64,
        parameters_hash="2" * 64,
        dev_selection_record_ref="3" * 64,
        protocol_hash="4" * 64,
        attempt_id="att-1",
        requested_seasons=("2026-27",),
        max_family_attempts=1,
    )
    reg.finalize_early_checkpoint_pass(
        "att-1",
        checkpoint_gw=15,
        completed_gameweeks=tuple(range(1, 16)),
        score_trace_hash="5" * 64,
        bundle_path="bundle.json",
    )
    ExclusionLedger(root / "exclusions.jsonl")
    (root / "exclusions.jsonl").write_bytes(b"")

    closure = compute_serving_model_closure(("def_xg_shrink_challenger", "adaptive_causal_challenger"))
    blob_ref = BlobStore(root).write_canonical_json({"hello": "world"})
    request = {
        "version": CHECKPOINT_EVIDENCE_V2,
        "checkpoint_gw": 15,
        "selection_path": "selection.json",
        "registry_path": "registry.jsonl",
        "protocol": {"path": "protocol.json", "sha256": content_hash({"p": 1})},
        "parameters": {"path": "parameters.json", "sha256": content_hash({})},
        "guard_outcome_sources": [{"season": "2026-27", "gameweek": 15, "admission": blob_ref}],
        "development_selections": {},
        "replays": [],
    }
    req_bytes = json.dumps(request, sort_keys=True).encode("utf-8")
    (root / "request.json").write_bytes(req_bytes)
    bundle = {
        "version": CHECKPOINT_EVIDENCE_V2,
        "checkpoint_gw": 15,
        "candidate_name": "adaptive_causal_challenger",
        "former_champion": "def_xg_shrink_challenger",
        "recommended_champion": "adaptive_causal_challenger",
        "scientific_verdict": "pass",
        "execution_status": "complete",
        "empirical_admission": True,
        "confirmation_attempt_id": "att-1",
        "request_path": "request.json",
        "request_sha256": "6" * 64,
        "selection_sha256": content_hash(asdict(frozen_sel)),
        "serving_model_closure_hash": closure.serving_model_closure_hash,
        "model_runtime_bindings": closure.model_runtime_bindings,
        "protocol_hash": "4" * 64,
        "bundle_hash": "a" * 64,
    }
    bundle_path = root / "bundle.json"
    bundle_path.write_text(json.dumps(bundle, sort_keys=True), encoding="utf-8")

    monkeypatch.setattr(promotion_evidence, "verify_checkpoint_recommendation_bundle", lambda bp, **kw: json.loads(Path(bp).read_bytes()))
    monkeypatch.setattr(portable_evidence, "_verify_bundle_in_dir", lambda bp, **kw: json.loads(Path(bp).read_bytes()))

    packed = pack_checkpoint_snapshot(bundle_path, output_dir=tmp_path / "snapshots")
    archive_path = Path(packed["archive_path"])
    archive_sha = str(packed["archive_sha256"])

    config_path = tmp_path / "live_selection.json"
    save_model_selection(frozen_sel, config_path)
    adoption_ledger_file = tmp_path / "adoption_ledger.jsonl"

    # If candidate becomes excluded in canonical exclusions ledger, adopt_champion fails closed
    excl_blocked = tmp_path / "blocked_exclusions.jsonl"
    ExclusionLedger(excl_blocked).record_exclusion(
        slate_id="slate-2026-27",
        season="2026-27",
        candidate_name="adaptive_causal_challenger",
        checkpoint_gw=16,
        reason_code="early_harm",
        details="Excluded after GW15 snapshot",
    )
    with pytest.raises(ValueError, match="excluded"):
        adopt_champion(
            bundle_path,
            config_path=config_path,
            approval_ref="GH-APPROVAL-SNAP",
            expected_current_champion="def_xg_shrink_challenger",
            approved_bundle_hash="a" * 64,
            snapshot_archive_path=archive_path,
            expected_archive_sha256=archive_sha,
            canonical_registry_path=root / "registry.jsonl",
            canonical_exclusions_path=excl_blocked,
            adoption_ledger_path=adoption_ledger_file,
        )
    assert not config_path.with_suffix(".adoption.json").exists()

    # Clean canonical exclusions ledger succeeds
    updated = adopt_champion(
        archive_path,
        config_path=config_path,
        approval_ref="GH-APPROVAL-SNAP",
        expected_current_champion="def_xg_shrink_challenger",
        approved_bundle_hash="a" * 64,
        expected_archive_sha256=archive_sha,
        canonical_registry_path=root / "registry.jsonl",
        canonical_exclusions_path=root / "exclusions.jsonl",
        adoption_ledger_path=adoption_ledger_file,
        request_id="req-snap-1",
        slate_id="slate-2026-27",
        approved_commit_sha="f" * 40,
    )
    assert updated.champion == "adaptive_causal_challenger"
    receipt = json.loads(config_path.with_suffix(".adoption.json").read_text(encoding="utf-8"))
    assert receipt["archive_sha256"] == archive_sha
    assert receipt["request_id"] == "req-snap-1"
    assert receipt["slate_id"] == "slate-2026-27"
    ledger_rec = AdoptionLedger(adoption_ledger_file).latest_for_request("req-snap-1")
    assert ledger_rec is not None
    assert ledger_rec.disposition == "adopted"
    assert ledger_rec.bundle_hash == "a" * 64

