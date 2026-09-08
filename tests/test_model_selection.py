import json
from pathlib import Path

import pytest

from models.selection import (
    ModelSelection,
    default_model_name,
    load_model_selection,
    projection_model_names,
    save_model_selection,
)


def test_load_model_selection_reads_champion_and_candidates(tmp_path: Path) -> None:
    config_path = tmp_path / "model_selection.json"
    config_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "champion": "participation_state_hybrid",
                "candidates": ["metrics_component_hybrid"],
                "promotion_status": "provisional",
            }
        ),
        encoding="utf-8",
    )

    selection = load_model_selection(config_path)

    assert selection.champion == "participation_state_hybrid"
    assert selection.candidates == ("metrics_component_hybrid",)
    assert selection.promotion_status == "provisional"


def test_save_model_selection_round_trips(tmp_path: Path) -> None:
    config_path = tmp_path / "model_selection.json"
    selection = ModelSelection(
        champion="participation_state_hybrid",
        candidates=("metrics_component_hybrid",),
        promotion_status="validated",
    )

    save_model_selection(selection, config_path)
    loaded = load_model_selection(config_path)

    assert loaded == selection


def test_load_model_selection_rejects_more_than_two_candidates(tmp_path: Path) -> None:
    config_path = tmp_path / "model_selection.json"
    config_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "champion": "a",
                "candidates": ["b", "c", "d"],
                "promotion_status": "provisional",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="at most two"):
        load_model_selection(config_path)


def test_default_model_name_returns_champion(tmp_path: Path) -> None:
    config_path = tmp_path / "model_selection.json"
    config_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "champion": "participation_state_hybrid",
                "candidates": [],
                "promotion_status": "provisional",
            }
        ),
        encoding="utf-8",
    )

    assert default_model_name(config_path) == "participation_state_hybrid"


def test_projection_model_names_defaults_to_champion_not_slate(tmp_path: Path) -> None:
    config_path = tmp_path / "model_selection.json"
    config_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "champion": "dual_vector_state_hybrid",
                "candidates": ["participation_state_hybrid", "metrics_component_hybrid"],
                "promotion_status": "provisional",
            }
        ),
        encoding="utf-8",
    )

    assert projection_model_names(config_path=config_path) == ["dual_vector_state_hybrid"]
    assert projection_model_names("metrics_component_hybrid", config_path=config_path) == [
        "metrics_component_hybrid"
    ]
    assert projection_model_names(
        "dual_vector_state_hybrid",
        ["a", "b", "a"],
        config_path=config_path,
    ) == ["a", "b"]
