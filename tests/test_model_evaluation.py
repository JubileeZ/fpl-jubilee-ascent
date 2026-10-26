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

