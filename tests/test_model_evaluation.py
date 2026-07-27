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
