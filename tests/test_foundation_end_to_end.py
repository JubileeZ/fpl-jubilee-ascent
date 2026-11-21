"""Known-answer lifecycle uses actual outputs and preserves empirical barriers."""

from pathlib import Path

from backtesting.confirmation_registry import ConfirmationRegistry
from backtesting.promotion_evidence import verify_recommendation_bundle, write_recommendation_bundle
from commands.evaluate_model_promotion import adopt_champion
from models.selection import ModelSelection, load_model_selection, save_model_selection
from promotion_evidence_fixture import CANDIDATE, CHAMPION, build_evidence_fixture
import pytest


def test_complete_foundation_lifecycle_end_to_end(tmp_path: Path) -> None:
    request = build_evidence_fixture(tmp_path / "retained")
    bundle_path = request.with_name("recommendation_bundle.json")
    bundle = write_recommendation_bundle(request, bundle_path)
    assert verify_recommendation_bundle(bundle_path, require_finalized=True) == bundle
    assert bundle["scientific_verdict"] == "inconclusive"
    assert bundle["empirical_admission"] is False
    assert bundle["assessment"]["is_confirmation_available"] is True
    registry = ConfirmationRegistry(request.parent / "registry.jsonl")
    attempt = registry.get_attempt("fixture-attempt")
    assert attempt is not None and attempt.status == "completed"
    assert attempt.scientific_verdict == bundle["scientific_verdict"]
    config = request.parent / "selection.json"
    original = ModelSelection(CHAMPION, (CANDIDATE,))
    save_model_selection(original, config)
    with pytest.raises(ValueError, match="complete empirical scientific pass"):
        adopt_champion(bundle_path, config_path=config, approval_ref="fixture-human-approval", expected_current_champion=CHAMPION, approved_bundle_hash=bundle["bundle_hash"])
    assert load_model_selection(config) == original


def test_adr0069_dual_tier_end_to_end_podium_checkpoints_serving_and_rollover(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import json
    from backtesting.evidence_statistics import (
        PairedGameweekScore,
        assign_gameweek_segment,
        compute_score_trace_hash,
    )
    from backtesting.projection_guards import GuardOutput
    from backtesting.promotion_evidence import (
        CHECKPOINT_EVIDENCE_VERSION,
        GUARD_SEMANTICS,
        MANDATORY_GUARDS,
        PodiumCandidateRecord,
        apply_provisional_action,
        derive_s1_guard_margins,
        evaluate_dual_tier_checkpoint,
        rank_and_freeze_podium,
        verify_checkpoint_recommendation_bundle,
        write_checkpoint_recommendation_bundle,
    )
    from backtesting.season_rules import SeasonRules
    from commands.evaluate_model_promotion import adopt_champion, evaluate_checkpoint_request, perform_annual_rollover
    from models import get_active_transfer_plan_model_name, get_default_model_name
    from models.selection import dual_tier_models

    # 1. Derive all 15 S-1 guard margins from Champion S-1 rows
    s1_rows = []
    for issue_gw in range(1, 5):
        for lead in range(6):
            target_gw = issue_gw + lead
            obs = {"actual_points": 2.0, "actual_minutes": 90.0}
            for gname, (_fcol, acol, _loss, _units) in GUARD_SEMANTICS.items():
                if gname not in ("points_mse", "minutes_mae"):
                    obs[acol] = 0.0
            row = {
                "season": "2025-26",
                "issue_gw": issue_gw,
                "gameweek_id": target_gw,
                "player_id": 1,
                "projected_points": 4.0,
                "projected_minutes": 80.0,
                "_observed": obs,
            }
            for fcol, _acol, _loss, _units in GUARD_SEMANTICS.values():
                row.setdefault(fcol, 0.0)
            s1_rows.append(row)
    margins = derive_s1_guard_margins(s1_rows)
    assert set(margins) == MANDATORY_GUARDS

    # 2. Rank & freeze M=2 podium (cand_3 displaces cand_1 pre-freeze)
    sel_path = tmp_path / "model_selection.json"
    initial_sel = ModelSelection(champion="def_xg_shrink_challenger", candidates=())
    save_model_selection(initial_sel, sel_path)
    monkeypatch.setattr("models.selection.DEFAULT_CONFIG_PATH", sel_path)

    cand_specs = [
        PodiumCandidateRecord(
            "cand_1",
            "def_xg_shrink_challenger",
            0.30,
            0.25,
            {"cold_start": 0.1, "early_mid": 0.2, "late": 0.2},
            {"cold_start": 0.1, "early_mid": 0.2, "late": 0.2},
            True,
            True,
        ),
        PodiumCandidateRecord(
            "cand_2",
            "def_xg_shrink_challenger",
            0.50,
            0.45,
            {"cold_start": 0.2, "early_mid": 0.4, "late": 0.4},
            {"cold_start": 0.2, "early_mid": 0.4, "late": 0.4},
            True,
            True,
        ),
        PodiumCandidateRecord(
            "cand_3",
            "def_xg_shrink_challenger",
            0.70,
            0.60,
            {"cold_start": 0.3, "early_mid": 0.6, "late": 0.6},
            {"cold_start": 0.3, "early_mid": 0.6, "late": 0.6},
            True,
            True,
        ),
    ]
    frozen = rank_and_freeze_podium(cand_specs, current_selection=initial_sel, active_season="2026-27", seal_slate=True)
    save_model_selection(frozen.updated_selection, sel_path)
    assert frozen.podium == ("cand_3", "cand_2")
    assert get_default_model_name() == "def_xg_shrink_challenger"
    assert get_active_transfer_plan_model_name() == "cand_3"
    assert dual_tier_models() == ["def_xg_shrink_challenger", "cand_3"]

    # 3. Register both frozen finalists on active_validation 2026-27
    registry = ConfirmationRegistry(tmp_path / "registry.jsonl")
    reg3 = registry.register_finalist(
        "cand_3", "def_xg_shrink_challenger", "fam_3", "a" * 64, "b" * 64, "dev-3", "p" * 64,
        requested_seasons=("2026-27",), registered_gameweeks=tuple(range(1, 39)), max_family_attempts=2,
    )
    reg2 = registry.register_finalist(
        "cand_2", "def_xg_shrink_challenger", "fam_2", "c" * 64, "d" * 64, "dev-2", "p" * 64,
        requested_seasons=("2026-27",), registered_gameweeks=tuple(range(1, 39)), max_family_attempts=2,
    )

    def _mk_scores(deltas: list[float]) -> list[PairedGameweekScore]:
        return [
            PairedGameweekScore("2026-27", gw, 60.0 + deltas[gw - 1], 60.0, 60.0 + deltas[gw - 1], 60.0, 0, 0, segment=assign_gameweek_segment(gw))
            for gw in range(1, len(deltas) + 1)
        ]

    def _mk_guards(sample_size: int) -> list[GuardOutput]:
        return [
            GuardOutput(name, True, "PASS", 0.0, margins[name], 0.05, -0.1, 0.1, 0.95, sample_size, "lower_is_better", "ok")
            for name in sorted(MANDATORY_GUARDS)
        ]

    # 4. GW15 checkpoint: cand_3 hits Early-Harm -> rotates #1 -> #2 (cand_2) cleanly
    s3_15 = _mk_scores([-2.2 if gw % 2 == 0 else -1.6 for gw in range(1, 16)])
    s2_15 = _mk_scores([0.3 if gw % 2 == 0 else -0.1 for gw in range(1, 16)])
    registry.record_checkpoint(reg3.attempt_id, checkpoint_gw=15, completed_gameweeks=tuple(range(1, 16)), score_trace_hash=compute_score_trace_hash(s3_15))
    registry.record_checkpoint(reg2.attempt_id, checkpoint_gw=15, completed_gameweeks=tuple(range(1, 16)), score_trace_hash=compute_score_trace_hash(s2_15))

    gw15 = evaluate_dual_tier_checkpoint(
        checkpoint_gw=15,
        finalist_traces={"cand_3": s3_15, "cand_2": s2_15},
        finalist_guards={"cand_3": _mk_guards(15), "cand_2": _mk_guards(15)},
        selection=load_model_selection(sel_path),
        podium_order=("cand_3", "cand_2"),
    )
    assert gw15.action == "rotate_to_backup"
    rotated = apply_provisional_action(load_model_selection(sel_path), gw15, config_path=sel_path)
    assert rotated.champion == "def_xg_shrink_challenger"
    assert rotated.provisional_active == "cand_2"
    assert get_active_transfer_plan_model_name() == "cand_2"

    # 5. A GW30 statistical pass and finalized registry cannot establish empirical admission.
    s3_30 = _mk_scores([-2.0 if gw <= 15 else 0.0 for gw in range(1, 31)])
    s2_30 = _mk_scores([2.4 + (0.2 if gw % 2 == 0 else -0.2) for gw in range(1, 31)])
    req_path = tmp_path / "gw30_checkpoint.json"
    req_path.write_text(
        json.dumps(
            {
                "version": CHECKPOINT_EVIDENCE_VERSION,
                "checkpoint_gw": 30,
                "selection_path": "model_selection.json",
                "registry_path": "registry.jsonl",
                "empirical_admission": True,
                "podium_order": ["cand_3", "cand_2"],
                "confirmation_attempt_ids": {
                    "cand_3": reg3.attempt_id,
                    "cand_2": reg2.attempt_id,
                },
                "finalist_traces": {
                    "cand_3": [{"season": s.season, "gameweek": s.gameweek, "candidate_net_points": s.candidate_net_points, "champion_net_points": s.champion_net_points} for s in s3_30],
                    "cand_2": [{"season": s.season, "gameweek": s.gameweek, "candidate_net_points": s.candidate_net_points, "champion_net_points": s.champion_net_points} for s in s2_30],
                },
                "s1_champion_rows": s1_rows,
                "finalist_guard_errors": {
                    candidate: {
                        metric: {
                            "candidate_by_gw": {str(gw): [0.0] for gw in range(1, 31)},
                            "champion_by_gw": {str(gw): [1.0] for gw in range(1, 31)},
                        }
                        for metric in sorted(MANDATORY_GUARDS)
                    }
                    for candidate in ("cand_3", "cand_2")
                },
            }
        ),
        encoding="utf-8",
    )
    gw30 = evaluate_checkpoint_request(req_path)
    assert gw30["action"] == "eligible_for_manual_adopt"
    assert gw30["recommended_champion"] == "cand_2"
    assert gw30["requires_manual_adopt"] is True
    assert load_model_selection(sel_path).champion == "def_xg_shrink_challenger"  # still unmutated until manual adopt

    # Finalize the statistical pass and verify the retained checkpoint bundle.
    bundle_path = tmp_path / "gw30_bundle.json"
    registry.finalize_early_checkpoint_pass(
        reg2.attempt_id,
        checkpoint_gw=30,
        completed_gameweeks=tuple(range(1, 31)),
        score_trace_hash=compute_score_trace_hash(s2_30),
        bundle_path=bundle_path.name,
    )
    bundle = write_checkpoint_recommendation_bundle(req_path, bundle_path)
    assert bundle["action"] == gw30["action"]
    assert bundle["recommended_champion"] == gw30["recommended_champion"]
    assert verify_checkpoint_recommendation_bundle(bundle_path, require_finalized=True) == bundle
    with pytest.raises(ValueError, match="complete empirical scientific pass"):
        adopt_champion(
            bundle_path,
            config_path=sel_path,
            approval_ref="ADR-0069-GW30-EARLY-PASS",
            expected_current_champion="def_xg_shrink_challenger",
            approved_bundle_hash=bundle["bundle_hash"],
        )
    assert bundle["empirical_admission"] is False
    assert load_model_selection(sel_path) == rotated

    # Re-seed provisional state to verify summer rollover clears unconfirmed provisional while keeping Champion
    re_provisional = ModelSelection("cand_2", ("def_xg_shrink_challenger", "cand_3"), provisional_active="cand_3", podium_frozen_season="2026-27", podium_sealed=True)
    save_model_selection(re_provisional, sel_path)
    lc_path = tmp_path / "season_lifecycle.json"
    lc_path.write_text(Path("config/season_lifecycle.json").read_text(encoding="utf-8"), encoding="utf-8")
    new_lc, new_sel = perform_annual_rollover(
        new_season="2027-28",
        bootstrap_payload={"events": [{"id": 38, "finished": True, "data_checked": True}]},
        lifecycle_path=lc_path,
        selection_path=sel_path,
        new_rules=SeasonRules("2027-28", "native-2027-28-v1", 5, True, 10, True, True, False),
    )
    assert new_lc.season_for_role("active_validation") == "2027-28"
    assert new_lc.season_for_role("development") == "2026-27"
    assert new_lc.season_for_role("historical_filter") == "2025-26"
    assert new_lc.season_for_role("prior_seed_only") == "2024-25"
    assert new_sel.champion == "cand_2"
    assert new_sel.provisional_active is None
    assert new_sel.podium_sealed is False
