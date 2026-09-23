import json
from pathlib import Path

import pytest

from models import get_model, resolve_model_name, resolve_model_or_champion
from models.selection import (
    ModelSelection,
    default_model_name,
    load_model_selection,
    projection_model_names,
    save_model_selection,
)


def test_resolve_unknown_model_raises() -> None:
    with pytest.raises(ValueError, match="not found"):
        resolve_model_name("dual_vector_state_hybrid")
    with pytest.raises(ValueError, match="not found"):
        resolve_model_name("not_a_real_model")
    with pytest.raises(ValueError, match="not found"):
        get_model("dual_vector_state_hybrid")


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
                "champion": "calibrated_matchup_hybrid",
                "candidates": ["participation_state_hybrid", "metrics_component_hybrid"],
                "promotion_status": "provisional",
            }
        ),
        encoding="utf-8",
    )

    assert projection_model_names(config_path=config_path) == ["calibrated_matchup_hybrid"]
    assert projection_model_names("metrics_component_hybrid", config_path=config_path) == [
        "metrics_component_hybrid"
    ]
    assert projection_model_names(
        "calibrated_matchup_hybrid",
        ["a", "b", "a"],
        config_path=config_path,
    ) == ["a", "b"]
    assert projection_model_names("champion", config_path=config_path) == [
        "calibrated_matchup_hybrid"
    ]
    assert projection_model_names("Champion", config_path=config_path) == [
        "calibrated_matchup_hybrid"
    ]


def test_resolve_model_or_champion() -> None:
    expected_champion = load_model_selection().champion
    assert resolve_model_or_champion(None) == expected_champion
    assert resolve_model_or_champion("") == expected_champion
    assert resolve_model_or_champion("champion") == expected_champion
    assert resolve_model_or_champion("Champion") == expected_champion
    assert resolve_model_or_champion("CHAMPION") == expected_champion
    assert resolve_model_or_champion("linear_baseline") == "linear_baseline"
    assert resolve_model_or_champion("test_model") == "test_model"
    with pytest.raises(ValueError, match="not found"):
        resolve_model_or_champion("completely_fake_model", validate=True)


def test_load_model_selection_self_heals_missing_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target_path = tmp_path / "config" / "model_selection.json"
    monkeypatch.setattr("models.selection.DEFAULT_CONFIG_PATH", target_path)

    assert not target_path.exists()
    selection = load_model_selection()
    assert target_path.exists()
    assert selection.champion == "calibrated_matchup_hybrid"
    assert selection.candidates == ("participation_state_hybrid",)

