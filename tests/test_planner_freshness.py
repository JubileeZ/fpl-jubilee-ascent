"""Tests for Weekly Transfer Planner selection, remote freshness, stale-checkout guard, and rerun pinning (#192, #197, #200, ADR 0070)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from backtesting.portable_evidence import (
    ExclusionLedger,
    TamperedLedgerError,
    VerificationScorecard,
    write_scorecard,
)
from models.planner_selection import (
    PlannerSelectionPreflight,
    RemoteFreshnessResult,
    StaleCheckoutError,
    check_remote_main_freshness,
    resolve_latest_officially_settled_gw,
    resolve_weekly_planner_model,
    sync_validation_evidence_readonly,
)
from models.selection import ModelSelection, eligible_slate_models, save_model_selection

CHAMPION = "def_xg_shrink_challenger"
FINALIST_1 = "adaptive_causal_challenger"
FINALIST_2 = "club_def_prior_challenger"
SEASON = "2026-27"
SLATE_ID = "slate-2026-27-v1"


def _write_sealed_selection(
    path: Path,
    *,
    champion: str = CHAMPION,
    candidates: tuple[str, ...] = (FINALIST_1, FINALIST_2),
    provisional_active: str | None = None,
    podium_sealed: bool = True,
    season: str | None = SEASON,
) -> ModelSelection:
    sel = ModelSelection(
        champion=champion,
        candidates=candidates,
        provisional_active=provisional_active,
        podium_frozen_season=season,
        podium_sealed=podium_sealed,
    )
    save_model_selection(sel, path)
    return sel


def _write_verified_scorecard(
    evidence_dir: Path,
    *,
    checkpoint_gw: int = 15,
    settled_through_gw: int = 15,
    cumulative_net_points: dict[str, float] | None = None,
    gap_status: str = "complete",
    first_blocked_gw: int | None = None,
    champion: str = CHAMPION,
    candidates: tuple[str, ...] = (FINALIST_1, FINALIST_2),
    slate_sealed: bool = True,
    season: str = SEASON,
    slate_id: str = SLATE_ID,
    active_exclusions: tuple[str, ...] = (),
) -> VerificationScorecard:
    scores = cumulative_net_points or {
        CHAMPION: 820.0,
        FINALIST_1: 814.0,
        FINALIST_2: 810.0,
    }
    leader = max(scores, key=lambda k: scores[k]) if scores else None
    sc = VerificationScorecard(
        season=season,
        checkpoint_gw=checkpoint_gw,
        slate_id=slate_id,
        slate_sealed=slate_sealed,
        confirmed_champion=champion,
        podium_order=candidates,
        provisional_active=None,
        serving_model_closure_hash="a" * 64,
        model_runtime_bindings={},
        evaluator_code_hash="b" * 64,
        producer_git_sha="c" * 40,
        settled_through_gw=settled_through_gw,
        gap_status=gap_status,  # type: ignore[arg-type]
        first_blocked_gw=first_blocked_gw,
        reason_codes=(),
        cumulative_net_points=scores,
        weekly_leader=leader,
        active_exclusions=active_exclusions,
        generated_at="2026-11-20T12:00:00+00:00",
    )
    write_scorecard(evidence_dir, sc)
    return sc


def test_weekly_ranking_trailing_finalist_stays_eligible_and_serves_when_leading(tmp_path: Path) -> None:
    """Champion 820 vs finalist 814 at GW15 -> Champion serves, finalist stays eligible;
    Finalist 851 vs Champion 846 at GW16 -> finalist serves next plan on verified complete prefix."""
    sel_path = tmp_path / "model_selection.json"
    evidence_dir = tmp_path / "evidence"
    # Even with provisional_active=None, finalist stays eligible on sealed slate!
    _write_sealed_selection(sel_path, candidates=(FINALIST_1,), provisional_active=None)

    # GW15: Champion 820, Finalist 814
    _write_verified_scorecard(
        evidence_dir,
        checkpoint_gw=15,
        settled_through_gw=15,
        candidates=(FINALIST_1,),
        cumulative_net_points={CHAMPION: 820.0, FINALIST_1: 814.0},
    )
    preflight_gw15 = resolve_weekly_planner_model(
        sel_path,
        evidence_dir=evidence_dir,
        settled_gw=15,
    )
    assert preflight_gw15.effective_model == CHAMPION
    assert preflight_gw15.eligible_models == (CHAMPION, FINALIST_1)
    assert preflight_gw15.excluded_models == ()
    assert preflight_gw15.comparable_scores == {CHAMPION: 820.0, FINALIST_1: 814.0}
    assert preflight_gw15.latest_settled_gw == 15
    assert preflight_gw15.verified_prefix_end_gw == 15
    assert preflight_gw15.fallback_reason is None

    # GW16: Finalist 851, Champion 846 -> Finalist serves automatically!
    _write_verified_scorecard(
        evidence_dir,
        checkpoint_gw=16,
        settled_through_gw=16,
        candidates=(FINALIST_1,),
        cumulative_net_points={CHAMPION: 846.0, FINALIST_1: 851.0},
    )
    preflight_gw16 = resolve_weekly_planner_model(
        sel_path,
        evidence_dir=evidence_dir,
        settled_gw=16,
    )
    assert preflight_gw16.effective_model == FINALIST_1
    assert preflight_gw16.eligible_models == (CHAMPION, FINALIST_1)
    assert preflight_gw16.comparable_scores == {CHAMPION: 846.0, FINALIST_1: 851.0}
    assert preflight_gw16.latest_settled_gw == 16
    assert preflight_gw16.verified_prefix_end_gw == 16
    assert preflight_gw16.fallback_reason is None
    lines = "\n".join(preflight_gw16.format_preflight_lines())
    assert FINALIST_1 in lines
    assert "851.0" in lines
    assert "GW16" in lines


def test_weekly_ranking_tie_breaks_champion_first_then_frozen_podium_rank(tmp_path: Path) -> None:
    """Tie for first with Champion (820 vs 820) -> Champion serves;
    Tie between two finalists above Champion (835 vs 835 vs Champion 820) -> higher frozen rank (#1) serves."""
    sel_path = tmp_path / "model_selection.json"
    evidence_dir = tmp_path / "evidence"
    _write_sealed_selection(sel_path, candidates=(FINALIST_1, FINALIST_2), provisional_active=None)

    # Case 1: Tie for first includes Champion (820 vs 820 vs 810) -> Champion wins
    _write_verified_scorecard(
        evidence_dir,
        checkpoint_gw=15,
        settled_through_gw=15,
        candidates=(FINALIST_1, FINALIST_2),
        cumulative_net_points={CHAMPION: 820.0, FINALIST_1: 820.0, FINALIST_2: 810.0},
    )
    tie_champ = resolve_weekly_planner_model(sel_path, evidence_dir=evidence_dir, settled_gw=15)
    assert tie_champ.effective_model == CHAMPION
    assert "tie" in tie_champ.selection_reason

    # Case 2: Two finalists tie above Champion (835 vs 835 vs Champion 820) -> #1 (FINALIST_1) wins
    _write_verified_scorecard(
        evidence_dir,
        checkpoint_gw=15,
        settled_through_gw=15,
        candidates=(FINALIST_1, FINALIST_2),
        cumulative_net_points={CHAMPION: 820.0, FINALIST_1: 835.0, FINALIST_2: 835.0},
    )
    tie_finalists = resolve_weekly_planner_model(sel_path, evidence_dir=evidence_dir, settled_gw=15)
    assert tie_finalists.effective_model == FINALIST_1
    assert "tie" in tie_finalists.selection_reason


def test_missing_settled_gameweek_falls_back_to_champion_and_shows_missing_week(tmp_path: Path) -> None:
    """GW16 officially settled locally, scorecard verified only through GW15 ->
    Champion fallback with missing week shown in preflight."""
    sel_path = tmp_path / "model_selection.json"
    evidence_dir = tmp_path / "evidence"
    processed_dir = tmp_path / "processed"
    processed_dir.mkdir()
    _write_sealed_selection(sel_path, candidates=(FINALIST_1,))

    # Local gameweeks.parquet shows GW1..16 finished and data_checked=True
    pd.DataFrame(
        [{"id": gw, "finished": True, "data_checked": True} for gw in range(1, 17)]
    ).to_parquet(processed_dir / "gameweeks.parquet")
    assert resolve_latest_officially_settled_gw(processed_dir) == 16

    # Scorecard only settled through GW15 (where finalist led 830 vs 820)
    _write_verified_scorecard(
        evidence_dir,
        checkpoint_gw=15,
        settled_through_gw=15,
        candidates=(FINALIST_1,),
        cumulative_net_points={CHAMPION: 820.0, FINALIST_1: 830.0},
    )

    preflight = resolve_weekly_planner_model(
        sel_path,
        evidence_dir=evidence_dir,
        processed_dir=processed_dir,
    )
    assert preflight.effective_model == CHAMPION
    assert preflight.latest_settled_gw == 16
    assert preflight.verified_prefix_end_gw == 15
    assert preflight.fallback_reason == "missing_settled_gw:16"
    rendered = "\n".join(preflight.format_preflight_lines())
    assert "missing_settled_gw:16" in rendered or "GW16" in rendered


def test_terminal_exclusion_removes_finalist_and_blocks_manual_override(tmp_path: Path) -> None:
    """Verified terminal exclusion in exclusions.jsonl excludes finalist from automatic ranking
    AND blocks manual --model override to that excluded finalist; eligible trailing finalist CAN be selected via override."""
    sel_path = tmp_path / "model_selection.json"
    evidence_dir = tmp_path / "evidence"
    _write_sealed_selection(sel_path, candidates=(FINALIST_1, FINALIST_2))

    ledger = ExclusionLedger(evidence_dir / "exclusions.jsonl")
    ledger.record_exclusion(
        slate_id=SLATE_ID,
        season=SEASON,
        candidate_name=FINALIST_1,
        checkpoint_gw=8,
        reason_code="early_harm_terminal",
        details="GW1-8 cumulative net points harm",
    )

    # Even if FINALIST_1 had highest points in raw dict and FINALIST_2 trails Champion (814 vs 820):
    _write_verified_scorecard(
        evidence_dir,
        checkpoint_gw=15,
        settled_through_gw=15,
        candidates=(FINALIST_1, FINALIST_2),
        cumulative_net_points={CHAMPION: 820.0, FINALIST_1: 860.0, FINALIST_2: 814.0},
        active_exclusions=(FINALIST_1,),
    )

    # 1. Automatic selection excludes FINALIST_1 and picks Champion (820 > 814)
    auto_preflight = resolve_weekly_planner_model(sel_path, evidence_dir=evidence_dir, settled_gw=15)
    assert auto_preflight.effective_model == CHAMPION
    assert auto_preflight.excluded_models == (FINALIST_1,)
    assert auto_preflight.eligible_models == (CHAMPION, FINALIST_2)
    assert FINALIST_1 not in auto_preflight.comparable_scores

    # 2. Manual override to terminally excluded FINALIST_1 is rejected
    with pytest.raises(ValueError, match="Cannot override Transfer Planner with terminally excluded finalist"):
        resolve_weekly_planner_model(
            sel_path,
            evidence_dir=evidence_dir,
            settled_gw=15,
            override_model=FINALIST_1,
        )

    # 3. Manual override to eligible trailing finalist FINALIST_2 is permitted and does not mutate selection.json
    before_bytes = sel_path.read_bytes()
    override_preflight = resolve_weekly_planner_model(
        sel_path,
        evidence_dir=evidence_dir,
        settled_gw=15,
        override_model=FINALIST_2,
    )
    assert override_preflight.effective_model == FINALIST_2
    assert override_preflight.override_applied is True
    assert sel_path.read_bytes() == before_bytes


def test_injury_audit_rerun_pins_reviewed_base_model_unless_invalidated(tmp_path: Path) -> None:
    """New scorecard changes leader between initial solve and --xmins-override minutes-correction rerun ->
    rerun pins and uses the originally reviewed base_model (unless invalidated by verified exclusion,
    expired deadline, or remote selection change)."""
    sel_path = tmp_path / "model_selection.json"
    evidence_dir = tmp_path / "evidence"
    processed_dir = tmp_path / "processed"
    processed_dir.mkdir()
    _write_sealed_selection(sel_path, candidates=(FINALIST_1, FINALIST_2))

    pd.DataFrame(
        [
            {"id": 15, "finished": True, "data_checked": True, "is_next": False, "deadline_time": "2026-12-01T11:00:00Z"},
            {"id": 16, "finished": False, "data_checked": False, "is_next": True, "deadline_time": "2026-12-08T11:00:00Z"},
        ]
    ).to_parquet(processed_dir / "gameweeks.parquet")

    # Initial solve at GW16: FINALIST_1 leads at GW15 (830 vs 820)
    _write_verified_scorecard(
        evidence_dir,
        checkpoint_gw=15,
        settled_through_gw=15,
        candidates=(FINALIST_1, FINALIST_2),
        cumulative_net_points={CHAMPION: 820.0, FINALIST_1: 830.0, FINALIST_2: 810.0},
    )
    initial = resolve_weekly_planner_model(
        sel_path,
        evidence_dir=evidence_dir,
        processed_dir=processed_dir,
        target_gw=16,
    )
    assert initial.effective_model == FINALIST_1

    # Save prior solution.json from Step 5 (even with _external_xmins suffix)
    prior_solution = tmp_path / "solution.json"
    prior_solution.write_text(
        json.dumps(
            {
                "meta": {
                    "champion": f"{FINALIST_1}_external_xmins",
                    "reviewed_base_model": FINALIST_1,
                    "base_model": FINALIST_1,
                    "next_gw": 16,
                    "target_gw_deadline": "2026-12-08T11:00:00Z",
                },
                "weeks": [],
            }
        ),
        encoding="utf-8",
    )

    # Before Step 6 rerun completes, a newer scorecard arrives where CHAMPION leads (840 vs 830)!
    _write_verified_scorecard(
        evidence_dir,
        checkpoint_gw=15,
        settled_through_gw=15,
        candidates=(FINALIST_1, FINALIST_2),
        cumulative_net_points={CHAMPION: 840.0, FINALIST_1: 830.0, FINALIST_2: 810.0},
    )

    # 1. Rerun keeps pinned FINALIST_1!
    rerun = resolve_weekly_planner_model(
        sel_path,
        evidence_dir=evidence_dir,
        processed_dir=processed_dir,
        target_gw=16,
        is_rerun=True,
        prior_solution_path=prior_solution,
    )
    assert rerun.effective_model == FINALIST_1
    assert rerun.pinned_for_rerun is True

    # 2. If target GW deadline changed/expired (e.g. target_gw is now 17 or GW16 finished=True), pin is invalidated!
    pd.DataFrame(
        [
            {"id": 15, "finished": True, "data_checked": True, "is_next": False, "deadline_time": "2026-12-01T11:00:00Z"},
            {"id": 16, "finished": True, "data_checked": False, "is_next": False, "deadline_time": "2026-12-08T11:00:00Z"},
        ]
    ).to_parquet(processed_dir / "gameweeks.parquet")
    expired_rerun = resolve_weekly_planner_model(
        sel_path,
        evidence_dir=evidence_dir,
        processed_dir=processed_dir,
        target_gw=16,
        is_rerun=True,
        prior_solution_path=prior_solution,
    )
    assert expired_rerun.pinned_for_rerun is False
    assert expired_rerun.effective_model == CHAMPION

    # Restore open GW16 deadline, then record terminal exclusion for FINALIST_1 -> pin is invalidated!
    pd.DataFrame(
        [
            {"id": 15, "finished": True, "data_checked": True, "is_next": False, "deadline_time": "2026-12-01T11:00:00Z"},
            {"id": 16, "finished": False, "data_checked": False, "is_next": True, "deadline_time": "2026-12-08T11:00:00Z"},
        ]
    ).to_parquet(processed_dir / "gameweeks.parquet")
    ExclusionLedger(evidence_dir / "exclusions.jsonl").record_exclusion(
        slate_id=SLATE_ID,
        season=SEASON,
        candidate_name=FINALIST_1,
        checkpoint_gw=15,
        reason_code="mandatory_guard_failure",
        details="Guard failure",
    )
    excluded_rerun = resolve_weekly_planner_model(
        sel_path,
        evidence_dir=evidence_dir,
        processed_dir=processed_dir,
        target_gw=16,
        is_rerun=True,
        prior_solution_path=prior_solution,
    )
    assert excluded_rerun.pinned_for_rerun is False
    assert excluded_rerun.effective_model == CHAMPION


def test_remote_adoption_stale_checkout_blocks_even_when_local_scorecard_agrees_then_syncs(tmp_path: Path) -> None:
    """Immediately after remote adoption on protected main, a stale local checkout blocks a fresh plan
    (StaleCheckoutError) requiring manual git pull, EVEN WHEN local cached scorecard agrees with local Champion!
    After manual sync (local model_selection.json updated to new Champion and closed slate), planner recognizes
    new Champion and closed slate."""
    sel_path = tmp_path / "model_selection.json"
    evidence_dir = tmp_path / "evidence"
    _write_sealed_selection(sel_path, champion=CHAMPION, candidates=(FINALIST_1,))

    # Local cached scorecard agrees with local selection.json (CHAMPION, FINALIST_1)
    _write_verified_scorecard(
        evidence_dir,
        checkpoint_gw=15,
        settled_through_gw=15,
        champion=CHAMPION,
        candidates=(FINALIST_1,),
        cumulative_net_points={CHAMPION: 820.0, FINALIST_1: 850.0},
    )

    # Remote protected main has adopted FINALIST_1 and closed the slate (candidates=[], podium_sealed=False)
    remote_merged_selection: dict[str, Any] = {
        "schema_version": 1,
        "champion": FINALIST_1,
        "candidates": [],
        "promotion_status": "adopted",
        "provisional_active": None,
        "podium_frozen_season": SEASON,
        "podium_sealed": False,
    }

    with pytest.raises(StaleCheckoutError, match="manual 'git pull'"):
        resolve_weekly_planner_model(
            sel_path,
            evidence_dir=evidence_dir,
            settled_gw=15,
            remote_selection_payload=remote_merged_selection,
        )

    # Simulate manual sync (local model_selection.json updated to match protected main)
    _write_sealed_selection(
        sel_path,
        champion=FINALIST_1,
        candidates=(),
        provisional_active=None,
        podium_sealed=False,
        season=SEASON,
    )
    synced = resolve_weekly_planner_model(
        sel_path,
        evidence_dir=evidence_dir,
        settled_gw=15,
        remote_selection_payload=remote_merged_selection,
    )
    assert synced.freshness_status == "verified_current"
    assert synced.effective_model == FINALIST_1
    assert synced.eligible_models == (FINALIST_1,)


def test_github_unreachable_serves_only_local_champion_with_unverified_status(tmp_path: Path) -> None:
    """With GitHub unreachable, planner serves ONLY locally recorded Confirmed Champion and labels
    freshness_status == 'unverified'. Never auto-pulls."""
    sel_path = tmp_path / "model_selection.json"
    evidence_dir = tmp_path / "evidence"
    _write_sealed_selection(sel_path, champion=CHAMPION, candidates=(FINALIST_1,))

    # Even though FINALIST_1 leads on the local verified scorecard (850 vs 820):
    _write_verified_scorecard(
        evidence_dir,
        checkpoint_gw=15,
        settled_through_gw=15,
        champion=CHAMPION,
        candidates=(FINALIST_1,),
        cumulative_net_points={CHAMPION: 820.0, FINALIST_1: 850.0},
    )

    def _unreachable_remote() -> dict[str, Any] | None:
        raise OSError("GitHub connection timed out")

    preflight = resolve_weekly_planner_model(
        sel_path,
        evidence_dir=evidence_dir,
        settled_gw=15,
        remote_loader=_unreachable_remote,
    )
    assert isinstance(preflight, PlannerSelectionPreflight)
    assert preflight.freshness_status == "unverified"
    assert preflight.effective_model == CHAMPION
    assert preflight.fallback_reason == "github_unreachable_unverified_champion_only"
    rendered = "\n".join(preflight.format_preflight_lines())
    assert "unverified" in rendered


def test_sync_validation_evidence_readonly_and_tampered_ledger_guard(tmp_path: Path) -> None:
    """sync_validation_evidence_readonly skips unsealed slates without subprocess calls,
    and tampered ExclusionLedger falls back to Champion and blocks finalist overrides."""
    sel_path = tmp_path / "model_selection.json"
    _write_sealed_selection(sel_path, podium_sealed=False)
    assert sync_validation_evidence_readonly(sel_path, evidence_dir=tmp_path / "ev") is False

    _write_sealed_selection(sel_path, candidates=(FINALIST_1, FINALIST_2), podium_sealed=True)
    assert eligible_slate_models(sel_path) == [CHAMPION, FINALIST_1, FINALIST_2]

    fresh = check_remote_main_freshness(
        sel_path,
        remote_selection_payload={
            "champion": FINALIST_1,
            "candidates": [],
            "podium_sealed": False,
            "podium_frozen_season": SEASON,
        },
        raise_on_stale=False,
    )
    assert isinstance(fresh, RemoteFreshnessResult)
    assert fresh.status == "stale_remote_changed"

    evidence_dir = tmp_path / "evidence"
    _write_verified_scorecard(
        evidence_dir,
        checkpoint_gw=15,
        settled_through_gw=15,
        candidates=(FINALIST_1, FINALIST_2),
        cumulative_net_points={CHAMPION: 820.0, FINALIST_1: 860.0, FINALIST_2: 850.0},
    )
    (evidence_dir / "exclusions.jsonl").write_text('{"corrupt": true}\n', encoding="utf-8")

    auto_tampered = resolve_weekly_planner_model(sel_path, evidence_dir=evidence_dir, settled_gw=15)
    assert auto_tampered.effective_model == CHAMPION
    assert auto_tampered.fallback_reason == "exclusion_ledger_tampered"

    with pytest.raises(TamperedLedgerError):
        resolve_weekly_planner_model(
            sel_path,
            evidence_dir=evidence_dir,
            settled_gw=15,
            override_model=FINALIST_1,
        )


def test_processor_preserves_data_checked_and_contiguous_settlement_and_surface_guards(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify processor data_checked column, contiguous settled prefix + 24h default, no_settled fallback, and dashboard/planner guards."""
    from datetime import UTC, datetime, timedelta
    from features.processor import process_directory
    from commands import dashboard as dash
    from commands import export_dashboard
    from dashboard.planner import Planner
    from dashboard.planner_service import PlannerPaths, make_solve_request

    # 1. features/processor.py preserves data_checked in gameweeks.parquet
    raw_dir = tmp_path / "raw"
    proc_dir = tmp_path / "proc"
    raw_dir.mkdir()
    (raw_dir / "bootstrap_static.json").write_text(
        json.dumps(
            {
                "teams": [{"id": 1, "name": "C1", "short_name": "C1"}],
                "events": [
                    {"id": 1, "name": "GW1", "deadline_time": "2026-08-15T10:00:00Z", "finished": True, "data_checked": True, "is_current": False, "is_next": False},
                    {"id": 2, "name": "GW2", "deadline_time": "2026-08-22T10:00:00Z", "finished": True, "data_checked": False, "is_current": True, "is_next": False},
                ],
                "elements": [
                    {"id": 1, "code": 101, "first_name": "A", "second_name": "B", "web_name": "AB", "team": 1, "element_type": 3, "now_cost": 50, "selected_by_percent": "1.0"}
                ],
            }
        ),
        encoding="utf-8",
    )
    (raw_dir / "fixtures_all.json").write_text("[]", encoding="utf-8")
    process_directory(raw_dir, proc_dir)
    gw_out = pd.read_parquet(proc_dir / "gameweeks.parquet")
    assert "data_checked" in gw_out.columns
    assert bool(gw_out.loc[gw_out["id"] == 1, "data_checked"].iloc[0]) is True
    assert bool(gw_out.loc[gw_out["id"] == 2, "data_checked"].iloc[0]) is False

    # 2. Contiguous settled prefix stops before GW15 when GW15 is unchecked even if GW16 is checked
    p2 = tmp_path / "proc2"
    p2.mkdir()
    pd.DataFrame(
        [
            {"id": gw, "finished": True, "data_checked": (gw != 15)}
            for gw in range(1, 17)
        ]
    ).to_parquet(p2 / "gameweeks.parquet")
    assert resolve_latest_officially_settled_gw(p2) == 14

    # Default now_utc enforces >=24h post-kickoff window without explicit now_utc argument
    recent_ko = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
    pd.DataFrame(
        [
            {"id": 1, "finished": True, "data_checked": True},
        ]
    ).to_parquet(p2 / "gameweeks.parquet")
    pd.DataFrame(
        [
            {"id": 10, "gameweek_id": 1, "finished": True, "kickoff_time": recent_ko},
        ]
    ).to_parquet(p2 / "fixtures.parquet")
    assert resolve_latest_officially_settled_gw(p2) == 0

    # 3. Missing local settled GWs (latest_settled_gw == 0) NEVER trusts a stale scorecard
    sel_path = tmp_path / "model_selection.json"
    _write_sealed_selection(sel_path, candidates=(FINALIST_1,))
    ev_dir = tmp_path / "ev"
    _write_verified_scorecard(
        ev_dir,
        checkpoint_gw=15,
        settled_through_gw=15,
        candidates=(FINALIST_1,),
        cumulative_net_points={CHAMPION: 800.0, FINALIST_1: 850.0},
    )
    preflight_zero = resolve_weekly_planner_model(
        sel_path,
        evidence_dir=ev_dir,
        processed_dir=p2,
        remote_loader=lambda: json.loads(sel_path.read_text(encoding="utf-8")),
    )
    assert preflight_zero.effective_model == CHAMPION
    assert preflight_zero.fallback_reason == "no_settled_gameweeks"

    # 4. export_dashboard never falls back to provisional_active when scorecard is missing/stale
    monkeypatch.setattr("models.selection.DEFAULT_CONFIG_PATH", sel_path)
    monkeypatch.setattr("models.planner_selection.PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(export_dashboard, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(export_dashboard, "resolve_operational_processed_dir", lambda _r: p2)
    monkeypatch.setattr(
        export_dashboard,
        "check_remote_main_freshness",
        lambda *_a, **_kw: RemoteFreshnessResult(
            status="stale_remote_changed",
            local_champion=CHAMPION,
            local_candidates=(FINALIST_1,),
            local_podium_sealed=True,
            local_podium_frozen_season=SEASON,
            remote_champion=FINALIST_1,
        ),
    )
    pd.DataFrame(
        [{"id": 1, "club_id": 1, "position_id": 3, "now_cost": 50, "web_name": "P1", "status": "a", "selected_by_percent": 1.0}]
    ).to_parquet(p2 / "players.parquet")
    pd.DataFrame([{"id": 1, "name": "C1", "short_name": "C1", "strength": 3, "strength_overall_home": 1000, "strength_overall_away": 1000, "strength_attack_home": 1000, "strength_attack_away": 1000, "strength_defence_home": 1000, "strength_defence_away": 1000}]).to_parquet(p2 / "clubs.parquet")
    pd.DataFrame(
        [{"id": 2, "name": "GW2", "is_next": True, "finished": False, "data_checked": False}]
    ).to_parquet(p2 / "gameweeks.parquet")
    pd.DataFrame([{"id": 20, "gameweek_id": 2, "home_club_id": 1, "away_club_id": 1, "team_h_difficulty": 3, "team_a_difficulty": 3, "kickoff_time": None, "finished": False}]).to_parquet(p2 / "fixtures.parquet")
    pd.DataFrame(columns=["player_id", "fixture_id", "gameweek_id", "minutes", "total_points"]).to_parquet(p2 / "player_performances.parquet")

    class _StubModel:
        def fit(self, _h: pd.DataFrame) -> None:
            return None

        def predict(self, df_f: pd.DataFrame, _hz: int) -> pd.DataFrame:
            return pd.DataFrame(
                [
                    {
                        "player_id": int(r["player_id"]),
                        "gameweek_id": int(r["gameweek_id"]),
                        "projected_points": 5.0,
                        "projected_minutes": 90.0,
                        "xp_goals": 0.0,
                        "xp_assists": 0.0,
                        "xp_clean_sheet": 0.0,
                        "xp_defcon": 0.0,
                        "xp_bonus": 0.0,
                    }
                    for _, r in df_f.iterrows()
                ]
            )

    monkeypatch.setattr(export_dashboard, "get_model", lambda _n: _StubModel())
    _write_sealed_selection(sel_path, candidates=(FINALIST_1,), provisional_active=FINALIST_1)
    out_stale = export_dashboard.run_dashboard_export(config_path=sel_path)
    stale_doc = json.loads(out_stale.read_text(encoding="utf-8"))
    assert stale_doc["meta"]["default_model"] == CHAMPION
    assert stale_doc["meta"]["active_transfer_plan_model"] == CHAMPION
    assert stale_doc["meta"]["planner_preflight"]["freshness_status"] == "stale_remote_changed"

    # 5. dashboard/planner_service.make_solve_request blocks unverified non-Champion solving
    dataset_unver = {
        "meta": {
            "target_gw": 2,
            "horizon": 1,
            "horizon_start": 2,
            "horizon_end": 2,
            "default_model": FINALIST_1,
            "models": [CHAMPION, FINALIST_1],
            "owned_squad_ids": [],
            "itb": 0.0,
            "free_transfers": 1,
            "planner_preflight": {
                "freshness_status": "unverified",
                "confirmed_champion": CHAMPION,
                "effective_model": CHAMPION,
                "excluded_models": [],
            },
        },
        "players": [],
    }
    monkeypatch.setattr("dashboard.planner_service.check_remote_main_freshness", lambda **_kw: RemoteFreshnessResult("unverified", CHAMPION, (FINALIST_1,), True, SEASON))
    with pytest.raises(ValueError, match="unverified"):
        make_solve_request(Planner(dataset_unver), PlannerPaths(tmp_path / "d.json", p2, tmp_path / "st"))

    # 6. commands/dashboard.start_transfer_plan rejects stale checkout with HTTP 409
    monkeypatch.setattr(dash, "resolve_operational_processed_dir", lambda _r: p2)
    monkeypatch.setattr(
        "commands.dashboard.resolve_weekly_planner_model",
        lambda **_kw: (_ for _ in ()).throw(StaleCheckoutError("Run manual 'git pull'")),
    )
    st_code, st_body = dash.start_transfer_plan(
        target_gw=2, horizon=1, booked_chips={"use_wc": [], "use_bb": [], "use_fh": [], "use_tc": []}, enabled_chips=[]
    )
    assert st_code == 409
    assert "git pull" in str(st_body["error"])


def test_sync_root_evidence_and_live_unverified_override_when_cached_meta_stale_verified(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify root-level validation-evidence sync filtering and live unverified blocking even when cached meta says verified_current."""
    import subprocess
    from dashboard.planner import Planner
    from dashboard.planner_service import PlannerPaths, make_solve_request

    repo = tmp_path / "repo"
    bare = tmp_path / "bare.git"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    (repo / "README.md").write_text("hi\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True)

    # Create orphan validation-evidence branch with root-level scorecards + exclusions
    subprocess.run(["git", "checkout", "--orphan", "validation-evidence"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "rm", "-rf", "."], cwd=repo, check=True, capture_output=True)
    ev_stage = tmp_path / "ev_stage"
    ev_stage.mkdir()
    sc = _write_verified_scorecard(
        ev_stage,
        checkpoint_gw=6,
        settled_through_gw=6,
        candidates=(FINALIST_1, FINALIST_2),
        cumulative_net_points={CHAMPION: 300.0, FINALIST_1: 315.0, FINALIST_2: 295.0},
    )
    assert sc.checkpoint_gw == 6
    (repo / "latest_scorecard.json").write_text((ev_stage / "latest_scorecard.json").read_text(encoding="utf-8"), encoding="utf-8")
    (repo / "scorecards").mkdir()
    (repo / "scorecards" / "gw06.json").write_text((ev_stage / "scorecards" / "gw06.json").read_text(encoding="utf-8"), encoding="utf-8")
    (repo / "scorecards" / "gw01.json").write_text(
        json.dumps({"season": "2027-28", "checkpoint_gw": 1}), encoding="utf-8"
    )
    (repo / "exclusions.jsonl").write_bytes(b"")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "evidence root"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "init", "--bare", str(bare)], check=True, capture_output=True)
    subprocess.run(["git", "remote", "add", "origin", str(bare)], cwd=repo, check=True)
    subprocess.run(["git", "push", "origin", "validation-evidence"], cwd=repo, check=True, capture_output=True)

    work = tmp_path / "work"
    work.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=work, check=True, capture_output=True)
    subprocess.run(["git", "remote", "add", "origin", str(bare)], cwd=work, check=True)
    sel_path = work / "config" / "model_selection.json"
    _write_sealed_selection(sel_path, candidates=(FINALIST_1, FINALIST_2), podium_sealed=True)
    sync_dest = tmp_path / "synced_ev"
    assert sync_validation_evidence_readonly(sel_path, evidence_dir=sync_dest, project_root=work) is True
    assert (sync_dest / "latest_scorecard.json").is_file()
    assert (sync_dest / "scorecards" / "gw06.json").is_file()
    assert not (sync_dest / "scorecards" / "gw01.json").exists()
    assert (sync_dest / "exclusions.jsonl").is_file()

    # Cached dataset claims verified_current, but live check_remote_main_freshness fails -> non-Champion blocked
    proc_dir = tmp_path / "proc2"
    proc_dir.mkdir()
    cached_verified_dataset = {
        "meta": {
            "target_gw": 7,
            "horizon": 1,
            "horizon_start": 7,
            "horizon_end": 7,
            "default_model": FINALIST_1,
            "models": [CHAMPION, FINALIST_1],
            "owned_squad_ids": [],
            "itb": 0.0,
            "free_transfers": 1,
            "planner_preflight": {
                "freshness_status": "verified_current",
                "confirmed_champion": CHAMPION,
                "effective_model": FINALIST_1,
                "excluded_models": [],
            },
        },
        "players": [],
    }
    monkeypatch.setattr(
        "dashboard.planner_service.check_remote_main_freshness",
        lambda **_kw: RemoteFreshnessResult("unverified", CHAMPION, (FINALIST_1,), True, SEASON),
    )
    with pytest.raises(ValueError, match="unverified"):
        make_solve_request(Planner(cached_verified_dataset), PlannerPaths(tmp_path / "d2.json", proc_dir, tmp_path / "s2"))

