"""Development Screen evidence and common-population integration regressions."""

from pathlib import Path

import pandas as pd
import pytest

from backtesting.metrics import evaluate_predictions
from backtesting.smoke_diagnostics import DiagnosticStore, input_identity, oracle_event_screen, paired_weekly_regret
from backtesting.walkforward import WalkforwardResult


def result(name: str, frame: pd.DataFrame) -> WalkforwardResult:
    metrics = evaluate_predictions(frame, target_column="blended_points")
    metrics["oracle_formation_xi_regret"] = metrics["top_11_regret"]
    metrics["oracle_captain_regret"] = 0.0
    return WalkforwardResult(name, Path("unused"), 1, 20, metrics, frame, {}, False)


def test_oracle_screen_rejects_playable_bias_hidden_by_global_cancellation() -> None:
    champion = pd.DataFrame([
        {"player_id": player, "gameweek": gw, "projected_points": projection,
         "blended_points": target, "actual_minutes": minutes}
        for gw in range(1, 21)
        for player, (projection, target, minutes) in enumerate(zip(
            [8.0] + [2.0] * 9 + [1.0] * 90,
            [5.0] + [2.0] * 9 + [1.0] * 89 + [4.0],
            [90.0] * 10 + [10.0] * 89 + [90.0], strict=True))
    ])
    candidate = champion.copy()
    mask = (champion.projected_points >= 2) | (champion.actual_minutes >= 30)
    candidate.loc[mask, "projected_points"] += 0.5
    candidate.loc[~mask, "projected_points"] -= 5.5 / 89
    reference, challenger = result("champion", champion), result("candidate", candidate)
    assert abs(float(reference.metrics["bias"])) < 1e-12
    assert abs(float(challenger.metrics["bias"])) < 1e-12

    verdict, weekly = oracle_event_screen(reference, challenger, target="blended_points")

    assert verdict.oracle_delta == 3.0
    assert verdict.bootstrap_p == 1.0
    assert verdict.candidate_playable_bias == 0.5
    assert not verdict.passed
    assert len(weekly) == 20
    assert any("playable pool signed bias" in reason for reason in verdict.reasons)


def diagnostic_frames() -> tuple[pd.DataFrame, pd.DataFrame]:
    reference = pd.DataFrame({"gameweek": [1, 2], "player_id": [1, 1], "projected_points": [3.0, 3.0],
                              "blended_points": [2.0, 2.0], "actual_minutes": [90.0, 90.0]})
    return reference, reference.assign(projected_points=[2.5, 2.5])


def retain(store: DiagnosticStore, *, identity: dict[str, object] | None = None, stage: str = "integrated", terminal: bool = True) -> dict[str, str]:
    reference, candidate = diagnostic_frames()
    return store.record(identity or {"initial_tier": "3", "gw_range": "1-2", "source": "original"}, {
        "stage": stage, "terminal": terminal, "execution_status": "complete", "eval_target": "blended_points", "variant": "toy",
        "pass": stage == "oracle", "segs": None if stage == "oracle" else 0,
    }, reference=reference, candidate=candidate, weekly=paired_weekly_regret(reference, candidate, "blended_points"))


def test_store_retains_both_stages_and_verifies_complete_identity(tmp_path: Path) -> None:
    legacy = tmp_path / "smoke.csv"
    legacy.write_text("legacy evidence\n")
    store = DiagnosticStore(legacy)
    identity: dict[str, object] = {"initial_tier": "2", "gw_range": "1-2", "source": "original"}
    oracle = retain(store, identity=identity, stage="oracle", terminal=False)
    integrated = retain(store, identity=identity)
    assert legacy.read_text() == "legacy evidence\n"
    assert oracle["segs"] == ""
    assert integrated["pass"] == "False"
    assert integrated["execution_status"] == "complete"
    assert integrated["scientific_verdict"] == "inconclusive"
    assert integrated["promotion_execution_status"] == "not_run"
    assert integrated["dead_lever_authority"] == "False"
    assert store.completed({"toy": identity}) == {"toy"}
    assert store.completed({"toy": {**identity, "source": "modified"}}) == set()
    assert len(store.rows()) == 2


@pytest.mark.parametrize("artifact", ["candidate.parquet", "weekly.csv", "playable_pool.json"])
def test_modified_trace_cannot_resume(tmp_path: Path, artifact: str) -> None:
    store = DiagnosticStore(tmp_path / "smoke.csv")
    row = retain(store)
    path = tmp_path / row["evidence_path"]
    (path.parent / artifact).write_bytes(b"modified")
    with pytest.raises(ValueError, match="artifact changed"):
        store.completed({"toy": {"initial_tier": "3", "gw_range": "1-2", "source": "original"}})


def test_incomplete_requested_calendar_cannot_be_completed(tmp_path: Path) -> None:
    store = DiagnosticStore(tmp_path / "smoke.csv")
    with pytest.raises(ValueError, match="requested calendar"):
        retain(store, identity={"initial_tier": "3", "gw_range": "1-3", "source": "original"})


def test_source_and_seed_bytes_change_identity(tmp_path: Path) -> None:
    source = tmp_path / "models"
    source.mkdir()
    parent = source / "parent.py"
    parent.write_text("parameter = 1\n")
    season, seed = tmp_path / "season", tmp_path / "seed"
    for directory in (season, seed):
        directory.mkdir()
        for name in ("players", "player_performances", "fixtures", "clubs", "gameweeks"):
            pd.DataFrame({"id": [1]}).to_parquet(directory / f"{name}.parquet")
    before = input_identity(tmp_path, season, seed, None)
    parent.write_text("parameter = 2\n")
    changed_source = input_identity(tmp_path, season, seed, None)
    pd.DataFrame({"id": [2]}).to_parquet(seed / "players.parquet")
    changed_seed = input_identity(tmp_path, season, seed, None)
    assert before != changed_source
    assert changed_source != changed_seed


def test_partial_attempt_is_not_resumable(tmp_path: Path) -> None:
    store = DiagnosticStore(tmp_path / "smoke.csv")
    identity = {"initial_tier": "3", "gw_range": "1-2"}
    row = store.record(identity, {"stage": "integrated", "terminal": True, "execution_status": "partial", "reasons": "worker stopped"})
    assert row["scientific_verdict"] == "invalid"
    assert row["combined_delta"] == ""
    assert store.completed({"toy": identity}) == set()


def test_note_consumer_keeps_baselines_and_stages_separate() -> None:
    import runpy

    module = runpy.run_path(str(Path(__file__).resolve().parents[1] / "docs/research/candidate-ideation/refresh_evidence.py"))
    row = {"season": "dev", "data_season": "2025-26", "champion": "original", "variant": "toy", "gw_range": "1-38",
           "pass": "False", "combined_delta": "1", "segs": "0", "boot_p_gt0": "0.8", "guardrails_passed": "False", "reasons": "tier2_oracle_fail: captain guard"}
    block, count = module["evidence_block"]([row, {**row, "champion": "different"}, {**row, "stage": "integrated", "run_id": "a" * 64}], "smoke.csv")
    assert count == 3
    assert block.count("segments unassessed") == 2
    assert "vs `different`" in block
    assert "0/3 segments" in block


@pytest.mark.parametrize("change", ["missing", "duplicate", "target", "empty_pool", "nan"])
def test_oracle_screen_rejects_invalid_population(change: str) -> None:
    reference, candidate = diagnostic_frames()
    if change == "missing":
        candidate = candidate.iloc[:1]
    elif change == "duplicate":
        candidate = pd.concat([candidate, candidate])
    elif change == "target":
        candidate = candidate.assign(blended_points=4.0)
    elif change == "empty_pool":
        reference = reference.assign(projected_points=0.0, actual_minutes=0.0)
        candidate = candidate.assign(actual_minutes=0.0)
    else:
        candidate = candidate.assign(projected_points=float("nan"))
    with pytest.raises(ValueError):
        oracle_event_screen(result("champion", reference), result("candidate", candidate), target="blended_points")
