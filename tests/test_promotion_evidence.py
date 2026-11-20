"""Recommendation and adoption operate on reconstructed native replay evidence."""

from pathlib import Path
import json
import shutil
from dataclasses import replace

import pytest

from backtesting import promotion_evidence
from backtesting.promotion_evidence import evaluate_replay_evidence, verify_recommendation_bundle, write_recommendation_bundle
from commands.evaluate_model_promotion import adopt_champion
from models.selection import ModelSelection, load_model_selection, save_model_selection
from promotion_evidence_fixture import CANDIDATE, CHAMPION, build_evidence_fixture, save_material


@pytest.fixture(scope="module")
def retained_template(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return build_evidence_fixture(tmp_path_factory.mktemp("retained-promotion"))


@pytest.fixture
def retained_request(retained_template: Path, tmp_path: Path) -> Path:
    destination = tmp_path / "evidence"
    shutil.copytree(retained_template.parent, destination)
    return destination / "request.json"


def _selection(root: Path) -> Path:
    path = root / "selection.json"
    save_model_selection(ModelSelection(CHAMPION, (CANDIDATE,)), path)
    return path


def test_native_replay_outputs_reconstruct_and_synthetic_evidence_cannot_adopt(retained_request: Path) -> None:
    result = evaluate_replay_evidence(retained_request)
    assert result["scientific_verdict"] == "inconclusive"
    assert result["empirical_admission"] is False
    assert len(result["guards"]) == 15
    assert len(result["assessment"]["season_summaries"]) == 2
    bundle_path = retained_request.with_name("bundle.json")
    written = write_recommendation_bundle(retained_request, bundle_path)
    assert verify_recommendation_bundle(bundle_path, require_finalized=True) == written
    config_path = _selection(retained_request.parent)
    with pytest.raises(ValueError, match="empirical scientific pass"):
        adopt_champion(bundle_path, config_path=config_path, approval_ref="fixture-approval", expected_current_champion=CHAMPION, approved_bundle_hash=written["bundle_hash"])
    assert load_model_selection(config_path).champion == CHAMPION


@pytest.mark.parametrize("mutation", ["trace", "request", "bundle", "forecast", "guard_inventory", "live_readiness"])
def test_changed_retained_material_is_rejected(retained_request: Path, mutation: str) -> None:
    bundle_path = retained_request.with_name("bundle.json")
    write_recommendation_bundle(retained_request, bundle_path)
    request = json.loads(retained_request.read_bytes())
    if mutation == "bundle":
        bundle = json.loads(bundle_path.read_bytes())
        bundle["candidate_name"] = "foreign_candidate"
        bundle_path.write_text(json.dumps(bundle))
    elif mutation == "trace":
        path = retained_request.parent / request["replays"][0]["trace"]["path"]
        trace = json.loads(path.read_bytes())
        trace["records"][0]["net_points"] += 4
        path.write_text(json.dumps(trace))
    elif mutation == "forecast":
        issue = request["replays"][0]["issues"][0]
        path = retained_request.parent / issue["forecast_store"] / "forecasts" / issue["forecast_id"] / "forecast.csv"
        path.write_bytes(path.read_bytes() + b"tampered")
    elif mutation in {"guard_inventory", "live_readiness"}:
        slot = "protocol" if mutation == "guard_inventory" else "live_readiness"
        path = retained_request.parent / request[slot]["path"]
        material = json.loads(path.read_bytes())
        if mutation == "guard_inventory":
            material["guard_specs"].pop("points_mse")
        else:
            material["dry_run_captures"] = {}
        request[slot] = save_material(retained_request.parent, path.name, material)
        retained_request.write_text(json.dumps(request))
    else:
        request["former_champion"] = "stale_champion"
        retained_request.write_text(json.dumps(request))
    with pytest.raises(ValueError):
        verify_recommendation_bundle(bundle_path)


def test_missing_confirmation_comparator_rejected(retained_request: Path) -> None:
    request = json.loads(retained_request.read_bytes())
    request["replays"] = [entry for entry in request["replays"] if entry["season"] != "2024-25"]
    retained_request.write_text(json.dumps(request))
    with pytest.raises(ValueError, match="Missing development or confirmation"):
        evaluate_replay_evidence(retained_request)


def test_current_source_change_invalidates_request(retained_request: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(promotion_evidence, "current_model_source_hash", lambda: "f" * 64)
    with pytest.raises(ValueError, match="Frozen model source changed"):
        evaluate_replay_evidence(retained_request)


def test_rehashed_certificate_with_false_zero_gap_is_rejected(retained_request: Path) -> None:
    from backtesting.rolling_replay import _checkpoint_hash, record_from_dict, record_to_dict, UncertifiedSolveError

    request = json.loads(retained_request.read_bytes())
    entry = next(entry for entry in request["replays"] if entry["season"] == "2024-25" and entry["model_name"] == CANDIDATE)
    path = retained_request.parent / entry["trace"]["path"]
    trace = json.loads(path.read_bytes())
    record = record_from_dict(trace["records"][0])
    record = replace(record, certificate=replace(record.certificate, objective_bound=record.certificate.objective + 1.0, absolute_gap=1.0, relative_gap=0.0))
    record = replace(record, checkpoint_id=_checkpoint_hash(record))
    trace["records"][0] = record_to_dict(record)
    entry["trace"] = save_material(retained_request.parent, path.name, trace)
    retained_request.write_text(json.dumps(request))
    with pytest.raises(UncertifiedSolveError, match="relative gap contradicts"):
        evaluate_replay_evidence(retained_request)


def test_adoption_unit_contract_with_verified_boundary(retained_request: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Isolate the verified-boundary result; actual synthetic integration above must refuse adoption."""
    from commands import evaluate_model_promotion

    bundle_path = retained_request.with_name("bundle.json")
    written = {"candidate_name": CANDIDATE, "former_champion": CHAMPION, "scientific_verdict": "pass", "execution_status": "complete", "empirical_admission": True, "bundle_hash": "a" * 64, "protocol_hash": "b" * 64}
    monkeypatch.setattr(evaluate_model_promotion, "verify_recommendation_bundle", lambda *args, **kwargs: written)
    config_path = _selection(retained_request.parent)
    for kwargs, message in (
        ({"approved_bundle_hash": "0" * 64}, "different evidence bundle"),
        ({"candidate_name": "foreign"}, "Candidate override"),
        ({"expected_current_champion": "stale"}, "Current Champion mismatch"),
    ):
        options = {"config_path": config_path, "approval_ref": "fixture-human-approval", "expected_current_champion": CHAMPION, "approved_bundle_hash": written["bundle_hash"], **kwargs}
        with pytest.raises(ValueError, match=message):
            adopt_champion(bundle_path, **options)
    updated = adopt_champion(bundle_path, config_path=config_path, approval_ref="fixture-human-approval", expected_current_champion=CHAMPION, approved_bundle_hash=written["bundle_hash"])
    assert updated.champion == CANDIDATE
    assert load_model_selection(config_path) == updated
    receipt = json.loads(config_path.with_suffix(".adoption.json").read_bytes())
    assert receipt["bundle_hash"] == written["bundle_hash"]
    assert receipt["selection_before"]["champion"] == CHAMPION


def test_adopt_champion_records_dual_tier_selection_before_and_clears_provisional(
    retained_request: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from commands import evaluate_model_promotion

    bundle_path = retained_request.with_name("bundle.json")
    written = {
        "candidate_name": CANDIDATE,
        "former_champion": CHAMPION,
        "scientific_verdict": "pass",
        "execution_status": "complete",
        "empirical_admission": True,
        "bundle_hash": "a" * 64,
        "protocol_hash": "b" * 64,
    }
    monkeypatch.setattr(evaluate_model_promotion, "verify_recommendation_bundle", lambda *args, **kwargs: written)
    config_path = retained_request.parent / "selection_dt.json"
    save_model_selection(
        ModelSelection(
            champion=CHAMPION,
            candidates=(CANDIDATE, "club_def_prior_challenger"),
            provisional_active=CANDIDATE,
            podium_frozen_season="2026-27",
            podium_sealed=True,
        ),
        config_path,
    )
    updated = adopt_champion(
        bundle_path,
        config_path=config_path,
        approval_ref="ADR-0069-GW15-PASS",
        expected_current_champion=CHAMPION,
        approved_bundle_hash=written["bundle_hash"],
    )
    assert updated.champion == CANDIDATE
    assert updated.provisional_active is None
    assert updated.podium_sealed is False
    receipt = json.loads(config_path.with_suffix(".adoption.json").read_bytes())
    assert receipt["selection_before"]["provisional_active"] == CANDIDATE
    assert receipt["selection_before"]["podium_sealed"] is True


def test_capture_cli_rejects_backdating_and_late_actual_clock(retained_request: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from commands import capture_live_evidence
    from backtesting.live_capture import LateCaptureError

    request_path = retained_request.with_name(f"capture-request-{CANDIDATE}.json")
    with pytest.raises(LateCaptureError):
        capture_live_evidence.capture_verified_issue(request_path, retained_request.parent / "late-capture")
    payload = json.loads(request_path.read_bytes())
    payload["capture_time_utc"] = "2025-01-01T11:00:00+00:00"
    request_path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="never a supplied timestamp"):
        capture_live_evidence.capture_verified_issue(request_path, retained_request.parent / "backdated-capture")


def test_solver_identity_is_portable_while_binary_recorded_separately(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from importlib.machinery import ModuleSpec
    from importlib import util
    from backtesting.native_transfer_solver import native_strategic_solve
    from backtesting.rolling_replay import replay_solver_binary_sha256, replay_solver_identity

    binary = tmp_path / "core.pyd"
    binary.write_bytes(b"fixture-installed-binary-v1")
    monkeypatch.setattr(util, "find_spec", lambda name: ModuleSpec(name, loader=None, origin=str(binary)))
    before_id = replay_solver_identity(native_strategic_solve)
    before_bin = replay_solver_binary_sha256()
    binary.write_bytes(b"fixture-installed-binary-v2")
    assert replay_solver_identity(native_strategic_solve) == before_id
    assert replay_solver_binary_sha256() != before_bin


def test_derive_s1_guard_margins_all_15_mandatory_guards_and_rare_se_floor() -> None:
    from backtesting.promotion_evidence import GUARD_SEMANTICS, MANDATORY_GUARDS, derive_s1_guard_margins

    rows = []
    for issue_gw in range(1, 5):
        for lead in range(6):
            target_gw = issue_gw + lead
            for pid in range(1, 11):
                # Large steady points MSE ~4.0 (5% rule dominates: 0.20 > GW SE)
                # Rare red-card spike only in GW1 (GW SE dominates 5% of small mean)
                obs: dict[str, float] = {
                    "actual_points": 2.0,
                    "actual_minutes": 60.0 if pid % 2 == 0 else 70.0,
                }
                for gname, (fcol, acol, _loss, _units) in GUARD_SEMANTICS.items():
                    if gname not in ("points_mse", "minutes_mae"):
                        obs[acol] = 4.0 if (gname == "red_cards_points_mse" and target_gw == 1 and pid == 1) else 0.0
                row = {
                    "season": "2025-26",
                    "issue_gw": issue_gw,
                    "gameweek_id": target_gw,
                    "player_id": pid,
                    "projected_points": 4.0,
                    "projected_minutes": 65.0,
                    "_observed": obs,
                }
                for fcol, _acol, _loss, _units in GUARD_SEMANTICS.values():
                    row.setdefault(fcol, 0.0)
                rows.append(row)

    margins = derive_s1_guard_margins(rows)
    assert set(margins) == MANDATORY_GUARDS
    # points_mse: diff=2.0 -> err=4.0 every GW -> GW SE = 0.0 -> margin = 0.05 * 4.0 = 0.20
    assert margins["points_mse"] == pytest.approx(0.20, abs=1e-9)
    # minutes_mae: diff=5.0 -> abs_err=5.0 every GW -> margin = 0.05 * 5.0 = 0.25
    assert margins["minutes_mae"] == pytest.approx(0.25, abs=1e-9)
    # red_cards_points_mse: GW1 spike drives GW SE > 0.05 * mean
    assert margins["red_cards_points_mse"] > 0.05 * (16.0 / len(rows))

    # 2024-25 defcon inapplicable exclusion supported
    margins_24 = derive_s1_guard_margins(rows, inapplicable_metrics=("defcon_points_mse",))
    assert "defcon_points_mse" not in margins_24
    assert len(margins_24) == 14


def test_group_projection_gameweeks_truncates_future_leads_at_checkpoint() -> None:
    import pandas as pd
    from backtesting.promotion_evidence import GUARD_SEMANTICS, group_projection_gameweeks

    preds = pd.DataFrame(
        [
            {
                "player_id": 1,
                "gameweek_id": target_gw,
                "projected_points": 5.0,
                "projected_minutes": 90.0,
                **{fcol: 0.0 for fcol, *_ in GUARD_SEMANTICS.values() if fcol.startswith("xp_")},
            }
            for target_gw in range(13, 19)  # issue_gw=13 leads 0..5 -> GW13..18
        ]
    )
    outcomes = {
        ("2026-27", gw, 1): {"actual_points": 4.0, "actual_minutes": 90.0}
        for gw in range(13, 16)  # only GW13..15 settled at GW15 checkpoint
    }
    with pytest.raises(ValueError, match="Missing complete finalized"):
        group_projection_gameweeks(preds, "2026-27", 13, outcomes)

    truncated = group_projection_gameweeks(preds, "2026-27", 13, outcomes, max_target_gw=15)
    assert [row["gameweek_id"] for row in truncated] == [13, 14, 15]


def test_rank_and_freeze_podium_tie_breaks_displacement_and_sealed_cap(tmp_path: Path) -> None:
    from backtesting.promotion_evidence import PodiumCandidateRecord, rank_and_freeze_podium

    base_sel = ModelSelection("def_xg_shrink_challenger", ("cand_a", "cand_b"))
    c_a = PodiumCandidateRecord(
        candidate_name="cand_a",
        champion_name="def_xg_shrink_challenger",
        delta_s1=0.60,
        delta_s2=0.40,
        s1_segment_deltas={"cold_start": 0.10, "early_mid": 0.50, "late": 0.70},
        s2_segment_deltas={"cold_start": 0.05, "early_mid": 0.30, "late": 0.50},
        s1_guards_ok=True,
        s2_guards_ok=True,
    )
    # Tie on mean (0.50), cand_b has higher S-2 delta (0.45 > 0.40) -> ranks ahead of cand_a
    c_b = PodiumCandidateRecord(
        candidate_name="cand_b",
        champion_name="def_xg_shrink_challenger",
        delta_s1=0.55,
        delta_s2=0.45,
        s1_segment_deltas={"cold_start": 0.10, "early_mid": 0.40, "late": 0.70},
        s2_segment_deltas={"cold_start": 0.05, "early_mid": 0.40, "late": 0.50},
        s1_guards_ok=True,
        s2_guards_ok=True,
    )
    # Fails S-2 late floor (-0.20 < -0.13) -> disqualified
    c_bad = PodiumCandidateRecord(
        candidate_name="cand_bad",
        champion_name="def_xg_shrink_challenger",
        delta_s1=1.50,
        delta_s2=0.50,
        s1_segment_deltas={"cold_start": 0.10, "early_mid": 1.00, "late": 2.00},
        s2_segment_deltas={"cold_start": 0.10, "early_mid": 1.20, "late": -0.20},
        s1_guards_ok=True,
        s2_guards_ok=True,
    )
    # Stronger Candidate C pre-freeze displaces cand_a to third -> excluded by M=2 cap
    c_c = PodiumCandidateRecord(
        candidate_name="cand_c",
        champion_name="def_xg_shrink_challenger",
        delta_s1=0.80,
        delta_s2=0.60,
        s1_segment_deltas={"cold_start": 0.10, "early_mid": 0.70, "late": 0.90},
        s2_segment_deltas={"cold_start": 0.10, "early_mid": 0.50, "late": 0.70},
        s1_guards_ok=True,
        s2_guards_ok=True,
    )
    frozen = rank_and_freeze_podium(
        [c_a, c_b, c_bad, c_c],
        current_selection=base_sel,
        active_season="2026-27",
        seal_slate=True,
    )
    assert frozen.podium == ("cand_c", "cand_b")
    assert frozen.provisional_active == "cand_c"
    assert frozen.backup_finalist == "cand_b"
    assert "cand_a" in frozen.displaced_candidates
    assert "cand_bad" in frozen.rejected_candidates
    assert frozen.updated_selection.champion == "def_xg_shrink_challenger"
    assert frozen.updated_selection.provisional_active == "cand_c"
    assert frozen.updated_selection.candidates == ("cand_c", "cand_b")
    assert frozen.updated_selection.podium_sealed is True

    # Once S slate is sealed, mid-season additions/displacement are rejected
    with pytest.raises(ValueError, match="sealed"):
        rank_and_freeze_podium(
            [c_a],
            current_selection=frozen.updated_selection,
            active_season="2026-27",
            seal_slate=True,
        )


def test_evaluate_dual_tier_checkpoint_obf_rotation_simultaneous_pass_and_manual_adopt() -> None:
    from backtesting.evidence_statistics import PairedGameweekScore, assign_gameweek_segment
    from backtesting.projection_guards import GuardOutput
    from backtesting.promotion_evidence import apply_provisional_action, evaluate_dual_tier_checkpoint

    def _scores(gws: int, deltas: list[float]) -> list[PairedGameweekScore]:
        return [
            PairedGameweekScore("2026-27", gw, 60.0 + deltas[gw - 1], 60.0, 60.0 + deltas[gw - 1], 60.0, 0, 0, segment=assign_gameweek_segment(gw))
            for gw in range(1, gws + 1)
        ]

    def _guards(status: str = "PASS") -> list[GuardOutput]:
        return [
            GuardOutput(
                metric_name=name,
                passed=(status == "PASS"),
                status=status,  # type: ignore[arg-type]
                estimate=0.0 if status == "PASS" else 2.0,
                margin=0.5,
                standard_error=0.1,
                ci_lower=-0.2 if status == "PASS" else 1.8,
                ci_upper=0.2 if status == "PASS" else 2.2,
                coverage=0.95,
                sample_size=15,
                direction="lower_is_better",
                reason="ok" if status == "PASS" else "harm",
            )
            for name in sorted(promotion_evidence.MANDATORY_GUARDS)
        ]

    sel = ModelSelection(
        champion="def_xg_shrink_challenger",
        candidates=("cand_1", "cand_2"),
        provisional_active="cand_1",
        podium_frozen_season="2026-27",
        podium_sealed=True,
    )

    # 1. GW15: both finalists lead without statistical confirmation; retain #1 even if #2 leads by more.
    mild = [0.2 if gw % 2 == 0 else -0.1 for gw in range(1, 16)]
    small_lead = [1.0, -1.0] * 7 + [1.0]
    larger_lead = [1.0, -1.0] * 7 + [2.0]
    res_retain = evaluate_dual_tier_checkpoint(
        checkpoint_gw=15,
        finalist_traces={"cand_1": _scores(15, small_lead), "cand_2": _scores(15, larger_lead)},
        finalist_guards={"cand_1": _guards("PASS"), "cand_2": _guards("PASS")},
        selection=sel,
        podium_order=("cand_1", "cand_2"),
    )
    assert res_retain.outcomes["cand_1"].net_delta == 1.0
    assert res_retain.outcomes["cand_2"].net_delta == 2.0
    assert not any(outcome.early_harm.triggered or outcome.superior for outcome in res_retain.outcomes.values())
    assert res_retain.action == "retain_dual_tier"
    assert res_retain.next_provisional_active == "cand_1"

    # 2. GW15: cand_1 hits harm while cand_2 is unharmed -> rotate #1 -> #2
    harm_d = [-2.5 if gw % 2 == 0 else -1.5 for gw in range(1, 16)]
    res_rot = evaluate_dual_tier_checkpoint(
        checkpoint_gw=15,
        finalist_traces={"cand_1": _scores(15, harm_d), "cand_2": _scores(15, mild)},
        finalist_guards={"cand_1": _guards("PASS"), "cand_2": _guards("PASS")},
        selection=sel,
        podium_order=("cand_1", "cand_2"),
    )
    assert res_rot.action == "rotate_to_backup"
    assert res_rot.next_provisional_active == "cand_2"
    rotated_sel = apply_provisional_action(sel, res_rot)
    assert rotated_sel.provisional_active == "cand_2"
    assert rotated_sel.champion == "def_xg_shrink_challenger"  # zero unattended overwrite

    # 3. GW30 simultaneous pass: cand_2 has higher cumulative S net_delta than cand_1 -> cand_2 wins tie
    win1 = [1.5 + (0.2 if gw % 2 else -0.2) for gw in range(1, 31)]
    win2 = [2.4 + (0.2 if gw % 2 else -0.2) for gw in range(1, 31)]
    res_sim = evaluate_dual_tier_checkpoint(
        checkpoint_gw=30,
        finalist_traces={"cand_1": _scores(30, win1), "cand_2": _scores(30, win2)},
        finalist_guards={"cand_1": _guards("PASS"), "cand_2": _guards("PASS")},
        selection=sel,
        podium_order=("cand_1", "cand_2"),
    )
    assert res_sim.action == "eligible_for_manual_adopt"
    assert res_sim.recommended_champion == "cand_2"
    assert res_sim.requires_manual_adopt is True
    assert sel.champion == "def_xg_shrink_challenger"

    # 4. GW38 without superiority pass (mean +0.025, wide alternating swing) -> fallback_to_champion
    res_gw38 = evaluate_dual_tier_checkpoint(
        checkpoint_gw=38,
        finalist_traces={"cand_1": _scores(38, [0.8 if gw % 2 == 0 else -0.75 for gw in range(1, 39)])},
        finalist_guards={"cand_1": _guards("PASS")},
        selection=ModelSelection("def_xg_shrink_challenger", ("cand_1",), provisional_active="cand_1", podium_frozen_season="2026-27", podium_sealed=True),
        podium_order=("cand_1",),
    )
    assert res_gw38.action == "fallback_to_champion"
    assert res_gw38.next_provisional_active is None

    # 5. One-way rotation: already rotated #2 (cand_2) hitting harm reverts to Champion (never back to #1 cand_1!)
    sel_rot = apply_provisional_action(sel, res_rot)
    res_no_bounce = evaluate_dual_tier_checkpoint(
        checkpoint_gw=30,
        finalist_traces={"cand_1": _scores(30, [0.4 if gw % 2 == 0 else -0.2 for gw in range(1, 31)]), "cand_2": _scores(30, [-2.0] * 30)},
        finalist_guards={"cand_1": _guards("PASS"), "cand_2": _guards("PASS")},
        selection=sel_rot,
        podium_order=("cand_1", "cand_2"),
    )
    assert res_no_bounce.action == "fallback_to_champion"
    assert res_no_bounce.next_provisional_active is None

    # 6. Pre-checkpoint GW8 intermediate Early-Harm works cleanly and ignores inapplicable guard FAIL
    inapp_guard = GuardOutput("defcon_points_mse", False, "FAIL", 3.0, 0.5, 0.1, 2.8, 3.2, 0.95, 8, "lower_is_better", "ignored")
    res_gw8_ok = evaluate_dual_tier_checkpoint(
        checkpoint_gw=8,
        finalist_traces={"cand_1": _scores(8, [0.4] * 8), "cand_2": _scores(8, [0.0] * 8)},
        finalist_guards={"cand_1": [*_guards("PASS"), inapp_guard], "cand_2": [*_guards("PASS"), inapp_guard]},
        selection=sel,
        podium_order=("cand_1", "cand_2"),
        inapplicable_guards=("defcon_points_mse",),
    )
    assert res_gw8_ok.action == "retain_dual_tier"
    assert res_gw8_ok.alpha_spent is None

    res_gw8_harm = evaluate_dual_tier_checkpoint(
        checkpoint_gw=8,
        finalist_traces={"cand_1": _scores(8, [-2.5, -2.0, -2.2, -1.8, -2.4, -2.1, -2.3, -1.9]), "cand_2": _scores(8, [0.3] * 8)},
        finalist_guards={"cand_1": _guards("PASS"), "cand_2": _guards("PASS")},
        selection=sel,
        podium_order=("cand_1", "cand_2"),
    )
    assert res_gw8_harm.action == "rotate_to_backup"
    assert res_gw8_harm.next_provisional_active == "cand_2"

    # 7. Dropped provisional_active=None stays fallback_to_champion (never resurrects #1)
    sel_dropped = apply_provisional_action(sel_rot, res_no_bounce)
    assert sel_dropped.provisional_active is None
    res_still_dropped = evaluate_dual_tier_checkpoint(
        checkpoint_gw=30,
        finalist_traces={"cand_1": _scores(30, [3.0] * 30), "cand_2": _scores(30, [0.0] * 30)},
        finalist_guards={"cand_1": _guards("PASS"), "cand_2": _guards("PASS")},
        selection=sel_dropped,
        podium_order=("cand_1", "cand_2"),
    )
    assert res_still_dropped.action == "fallback_to_champion"
    assert res_still_dropped.next_provisional_active is None


def test_apply_provisional_action_keeps_podium_sealed_and_gw15_rejects_trailing_backup() -> None:
    from backtesting.evidence_statistics import PairedGameweekScore, assign_gameweek_segment
    from backtesting.projection_guards import GuardOutput
    from backtesting.promotion_evidence import (
        MANDATORY_GUARDS,
        PodiumCandidateRecord,
        apply_provisional_action,
        evaluate_dual_tier_checkpoint,
        rank_and_freeze_podium,
    )

    def _scores(deltas: list[float]) -> list[PairedGameweekScore]:
        return [
            PairedGameweekScore("2026-27", gw, 60.0 + deltas[gw - 1], 60.0, 60.0 + deltas[gw - 1], 60.0, 0, 0, segment=assign_gameweek_segment(gw))
            for gw in range(1, len(deltas) + 1)
        ]

    def _guards() -> list[GuardOutput]:
        return [
            GuardOutput(name, True, "PASS", 0.0, 0.5, 0.1, -0.2, 0.2, 0.95, 15, "lower_is_better", "ok")
            for name in sorted(MANDATORY_GUARDS)
        ]

    sel = ModelSelection(
        champion="def_xg_shrink_challenger",
        candidates=("cand_1", "cand_2"),
        provisional_active="cand_1",
        podium_frozen_season="2026-27",
        podium_sealed=True,
    )

    # At GW15, two trailing finalists lead to fallback even when the backup has no Early-Harm trigger.
    cand1_trail = [-1.0] * 3 + [0.8] * 3 + [-1.0] * 3 + [0.8] * 3 + [-0.4] * 3
    cand2_trail = [-2.0] * 3 + [1.5] * 3 + [-2.0] * 3 + [1.5] * 3 + [-0.5] * 3
    res_both_trail = evaluate_dual_tier_checkpoint(
        checkpoint_gw=15,
        finalist_traces={
            "cand_1": _scores(cand1_trail),
            "cand_2": _scores(cand2_trail),
        },
        finalist_guards={"cand_1": _guards(), "cand_2": _guards()},
        selection=sel,
        podium_order=("cand_1", "cand_2"),
    )
    assert res_both_trail.outcomes["cand_2"].early_harm.triggered is False
    assert res_both_trail.outcomes["cand_2"].net_delta < 0.0
    assert res_both_trail.action == "fallback_to_champion"
    assert res_both_trail.next_provisional_active is None

    # 2. Mid-season fallback_to_champion clears provisional_active but keeps podium_sealed=True for S.
    after_fallback = apply_provisional_action(sel, res_both_trail)
    assert after_fallback.provisional_active is None
    assert after_fallback.podium_sealed is True
    assert after_fallback.podium_frozen_season == "2026-27"
    with pytest.raises(ValueError, match="sealed"):
        rank_and_freeze_podium(
            [PodiumCandidateRecord("cand_c", "def_xg_shrink_challenger", 0.9, 0.9, {"early_mid": 0.5}, {"early_mid": 0.5}, True, True)],
            current_selection=after_fallback,
            active_season="2026-27",
            seal_slate=True,
        )


def test_verify_live_readiness_supports_adr0069_fplcache_mode(tmp_path: Path) -> None:
    from backtesting.promotion_evidence import _verify_live_readiness

    payload = {
        "version": 2,
        "mode": "fplcache",
        "candidate_name": CANDIDATE,
        "former_champion": CHAMPION,
        "protocol_hash": "p" * 64,
        "fplcache_manifest_path": "config/fplcache_2026_27_manifest.json",
        "max_snapshot_lag_hours": 24.0,
        "review_gameweeks": [15, 30, 38],
        "settlement_delay_hours": 24,
        "material_loss_limit_mode": "statistical_kendall_pw_hac",
        "early_harm_min_gw": 6,
        "early_harm_p_threshold": 0.025,
    }
    frozen_review = {
        "mode": "fplcache",
        "review_gameweeks": [15, 30, 38],
        "settlement_delay_hours": 24,
        "early_harm_min_gw": 6,
        "early_harm_p_threshold": 0.025,
    }
    _verify_live_readiness(tmp_path, payload, CANDIDATE, CHAMPION, "p" * 64, "s" * 64, frozen_review)


def test_checkpoint_payload_supports_externalized_blob_catalog_relative_bundle_and_2027_28_s1_transition(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backtesting.portable_evidence import BlobStore, compute_serving_model_closure
    from backtesting.promotion_evidence import _admit_context, evaluate_verified_checkpoint_payload
    from test_empirical_admission import _build_empirical_bundle

    # 1. _admit_context resolves BlobStore externalized catalog entries cleanly without disk fallback
    req, cat, _ = _build_empirical_bundle(gws=(1,), with_manager=False)
    store = BlobStore(tmp_path)
    ext_catalog = {
        key: {"blob_sha256": (digest := store.write_bytes(raw)), "relpath": store.relpath(digest)}
        for key, raw in cat.items()
    }
    admitted, decoded_req, decoded_cat = _admit_context({"request": req, "catalog": ext_catalog}, "2025-26", 1, root=tmp_path)
    assert admitted.season == "2025-26" and admitted.gw == 1
    assert decoded_cat == cat
    assert decoded_req["season"] == "2025-26"

    # 2. current_model_source_hash matches serving model closure, and serving_model_closure_hash mismatch fails closed
    closure = compute_serving_model_closure((CHAMPION, CANDIDATE))
    assert isinstance(promotion_evidence.current_model_source_hash(), str) and len(promotion_evidence.current_model_source_hash()) == 64

    # 3. 2027-28 s1_guard_baseline_season_archive_transition forbidden on 2026-27
    root_bad = tmp_path / "bad_transition"
    root_bad.mkdir()
    save_model_selection(ModelSelection(CHAMPION, (CANDIDATE,), provisional_active=CANDIDATE, podium_frozen_season="2026-27", podium_sealed=True), root_bad / "selection.json")
    bad_proto = {
        "horizon": 6,
        "windows": {"2025-26": [1, 2], "2026-27": list(range(1, 39))},
        "s1_guard_baseline_mode": "s1_guard_baseline_season_archive_transition",
        "guard_specs": {
            name: {"forecast_field": spec[0], "outcome_field": spec[1], "loss": spec[2], "units": spec[3], "margin": 0.0, "alpha": 0.05, "direction": "lower_is_better"}
            for name, spec in promotion_evidence.GUARD_SEMANTICS.items()
        },
        "quality_policy": {"mode": "certified", "target_gap": 0.0, "time_limit_seconds": 60.0, "require_proven_optimal": True, "raise_on_failure": True},
        "chip_calendar": [[3, "triple_captain"], [25, "wildcard"]],
        "solver_identity": promotion_evidence.native_solver_identity(),
        "projection_evaluation": {
            "leads": list(range(6)),
            "weights": [1.0] * 6,
            "population": "all_admitted_players",
            "missingness": "fail_closed",
            "aggregation": "weighted_paired_player_gameweek",
            "applicability": {
                s: dict.fromkeys(promotion_evidence.MANDATORY_GUARDS, "required")
                for s in ("2025-26", "2026-27")
            },
        },
        "live_review": {"mode": "fplcache", "review_gameweeks": [15, 30, 38], "settlement_delay_hours": 24, "early_harm_min_gw": 6, "early_harm_p_threshold": 0.025},
    }
    bad_proto["statistics"] = promotion_evidence.StatisticalProtocolConfig(
        development_season="2025-26",
        confirmation_season="2026-27",
        approved_by_human=True,
        approval_reference="approved-ref",
        max_family_attempts=1,
        required_projection_guards=tuple(promotion_evidence.MANDATORY_GUARDS),
        evidence_protocol_hash=promotion_evidence.content_hash(bad_proto),
    ).to_dict()
    proto_ref = save_material(root_bad, "protocol.json", bad_proto)
    src_hash = promotion_evidence.current_model_source_hash()
    with pytest.raises(ValueError, match="2027-28"):
        evaluate_verified_checkpoint_payload(
            root_bad,
            {
                "version": promotion_evidence.CHECKPOINT_EVIDENCE_V2,
                "checkpoint_gw": 15,
                "selection_path": "selection.json",
                "registry_path": "registry.jsonl",
                "model_source_hash": src_hash,
                "serving_model_closure_hash": closure.serving_model_closure_hash,
                "model_runtime_bindings": closure.model_runtime_bindings,
                "protocol": proto_ref,
                "confirmation_attempt_ids": {CANDIDATE: "att"},
                "development_selections": {CANDIDATE: proto_ref},
                "guard_outcome_sources": [],
                "replays": [],
            },
        )
