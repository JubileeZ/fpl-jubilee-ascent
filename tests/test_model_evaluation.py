from pathlib import Path

from models.selection import ModelSelection
from backtesting.model_evaluation import promote_candidate, replace_candidate


def test_promote_candidate_keeps_former_champion_as_candidate() -> None:
    selection = ModelSelection(
        champion="participation_state_hybrid",
        candidates=("metrics_component_hybrid",),
    )

    promoted = promote_candidate(selection, "metrics_component_hybrid", snapshot_backed=False)

    assert promoted.champion == "metrics_component_hybrid"
    assert promoted.candidates == ("participation_state_hybrid",)
    assert promoted.promotion_status == "provisional"


def test_promote_candidate_marks_validated_when_snapshot_backed() -> None:
    selection = ModelSelection(
        champion="participation_state_hybrid",
        candidates=("metrics_component_hybrid",),
    )

    promoted = promote_candidate(selection, "metrics_component_hybrid", snapshot_backed=True)

    assert promoted.promotion_status == "validated"


def test_promote_candidate_preserves_second_candidate_from_full_slate() -> None:
    selection = ModelSelection(
        champion="a",
        candidates=("b", "c"),
    )

    promoted = promote_candidate(selection, "b", snapshot_backed=False)

    assert promoted.champion == "b"
    assert set(promoted.candidates) == {"a", "c"}


def test_replace_candidate_swaps_registered_candidate() -> None:
    selection = ModelSelection(champion="a", candidates=("b", "c"))

    updated = replace_candidate(selection, incoming="d", outgoing="c")

    assert updated.champion == "a"
    assert set(updated.candidates) == {"b", "d"}


def test_compare_to_reference_wires_active_window_metrics() -> None:
    from pathlib import Path
    import pandas as pd
    from backtesting.model_evaluation import compare_to_reference
    from backtesting.walkforward import WalkforwardResult

    df_champ = pd.DataFrame(
        [
            {"player_id": 1, "gameweek": 1, "projected_points": 5.0, "actual_points": 4.0, "actual_minutes": 90},
            {"player_id": 2, "gameweek": 1, "projected_points": 1.0, "actual_points": 0.0, "actual_minutes": 0},
            {"player_id": 1, "gameweek": 2, "projected_points": 5.0, "actual_points": 4.0, "actual_minutes": 90},
            {"player_id": 2, "gameweek": 2, "projected_points": 1.0, "actual_points": 0.0, "actual_minutes": 0},
        ]
    )
    # Candidate identical in GW1, diverges in GW2
    df_cand = pd.DataFrame(
        [
            {"player_id": 1, "gameweek": 1, "projected_points": 5.0, "actual_points": 4.0, "actual_minutes": 90},
            {"player_id": 2, "gameweek": 1, "projected_points": 1.0, "actual_points": 0.0, "actual_minutes": 0},
            {"player_id": 1, "gameweek": 2, "projected_points": 4.8, "actual_points": 4.0, "actual_minutes": 90},
            {"player_id": 2, "gameweek": 2, "projected_points": 1.0, "actual_points": 0.0, "actual_minutes": 0},
        ]
    )

    res_champ = WalkforwardResult(
        model_name="champ",
        data_dir=Path("."),
        start_gw=1,
        end_gw=2,
        metrics={},
        df_eval=df_champ,
        snapshot_ids={},
        snapshot_backed=False,
    )
    res_cand = WalkforwardResult(
        model_name="cand",
        data_dir=Path("."),
        start_gw=1,
        end_gw=2,
        metrics={},
        df_eval=df_cand,
        snapshot_ids={},
        snapshot_backed=False,
    )

    verdict = compare_to_reference(res_champ, res_cand, primary_target="actual_points")
    assert verdict.active_guardrails_passed is not None


def test_compare_two_season_gate_and_evidence_record_active_guardrails(tmp_path: Path) -> None:
    import pandas as pd
    from backtesting.model_evaluation import (
        CandidateComparison,
        build_evidence_record,
        compare_two_season_gate,
        write_promotion_evidence,
    )
    from backtesting.walkforward import WalkforwardResult

    def _make_season_dfs(cand_bonus: float) -> tuple[pd.DataFrame, pd.DataFrame]:
        champ_rows = []
        cand_rows = []
        for gw in range(1, 26):
            # 11 outfield/GK players with distinct actual points
            for pid in range(1, 16):
                pos = 1 if pid <= 2 else (2 if pid <= 7 else (3 if pid <= 12 else 4))
                actual = float(16 - pid) if pid <= 11 else 0.0
                mins = 90 if pid <= 11 else 0
                # Champion slightly misranks player 1 vs player 2
                champ_xp = float(15 - pid) if pid > 2 else (13.0 if pid == 1 else 14.5)
                # Candidate ranks player 1 above player 2 when cand_bonus > 0
                cand_xp = (15.0 + cand_bonus if pid == 1 else 14.0) if pid <= 2 else champ_xp
                base = {
                    "player_id": pid,
                    "position_id": pos,
                    "now_cost": 50,
                    "club_id": (pid % 10) + 1,
                    "gameweek": gw,
                    "actual_points": actual,
                    "process_points": actual,
                    "blended_points": actual,
                    "actual_minutes": mins,
                    "expected_minutes": float(mins),
                }
                champ_rows.append({**base, "projected_points": champ_xp})
                cand_rows.append({**base, "projected_points": cand_xp})
        return pd.DataFrame(champ_rows), pd.DataFrame(cand_rows)

    dev_champ_df, dev_cand_df = _make_season_dfs(cand_bonus=1.0)
    conf_champ_df, conf_cand_df = _make_season_dfs(cand_bonus=1.0)

    dev_ref = WalkforwardResult("champ", Path("."), 1, 25, {}, dev_champ_df, {}, False)
    dev_cand = WalkforwardResult("cand", Path("."), 1, 25, {}, dev_cand_df, {}, False)
    conf_ref = WalkforwardResult("champ", Path("."), 1, 25, {}, conf_champ_df, {}, False)
    conf_cand = WalkforwardResult("cand", Path("."), 1, 25, {}, conf_cand_df, {}, False)

    two_season = compare_two_season_gate(dev_ref, dev_cand, conf_ref, conf_cand)
    assert two_season.passed
    assert two_season.pooled_bootstrap_p == 1.0

    sel = ModelSelection(champion="champ", candidates=("cand",))
    record = build_evidence_record(
        selection_before=sel,
        selection_after=sel,
        comparisons=[CandidateComparison("cand", two_season.dev_verdict, True)],
        evaluation_season="2025-26",
        git_commit="abc1234",
    )
    assert record["comparisons"][0]["active_guardrails_passed"] is True
    _, md_path = write_promotion_evidence(record, tmp_path)
    assert "Active guardrails passed: True" in md_path.read_text(encoding="utf-8")


def test_compare_to_reference_and_two_season_forwards_segment_tolerances() -> None:
    from pathlib import Path
    import pandas as pd
    from backtesting.model_evaluation import compare_to_reference, compare_two_season_gate
    from backtesting.walkforward import WalkforwardResult

    # Test that segment_tolerances parameter is accepted and wired cleanly
    df = pd.DataFrame([
        {
            "player_id": 1,
            "position_id": 1,
            "now_cost": 50,
            "club_id": 1,
            "gameweek": 1,
            "projected_points": 4.0,
            "actual_points": 4.0,
            "process_points": 4.0,
            "blended_points": 4.0,
            "projected_minutes": 90.0,
            "actual_minutes": 90.0,
        }
    ])
    res1 = WalkforwardResult("m1", Path("."), 1, 1, {}, df, {}, False)
    res2 = WalkforwardResult("m2", Path("."), 1, 1, {}, df, {}, False)

    custom_tols = {"cold_start": -0.50, "early_mid": -0.30, "late": -0.20}
    verdict = compare_to_reference(res1, res2, segment_tolerances=custom_tols)
    assert verdict is not None

    two_season = compare_two_season_gate(
        res1, res2, res1, res2,
        dev_segment_tolerances=custom_tols,
        conf_segment_tolerances=custom_tols,
    )
    assert two_season is not None



