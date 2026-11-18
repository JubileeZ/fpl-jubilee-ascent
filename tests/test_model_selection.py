import json
from pathlib import Path

import pytest

from models import (
    get_active_transfer_plan_model_name,
    get_model,
    resolve_model_name,
    resolve_model_or_champion,
    resolve_model_or_transfer_plan_default,
)
from models.champion_trust import load_champion_trust
from models.selection import (
    ModelSelection,
    active_transfer_plan_model_name,
    default_model_name,
    dual_tier_models,
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
    assert selection.provisional_active is None
    assert selection.podium_sealed is False


def test_dual_tier_selection_validation_and_serving_order(tmp_path: Path) -> None:
    config_path = tmp_path / "model_selection.json"
    selection = ModelSelection(
        champion="def_xg_shrink_challenger",
        candidates=("adaptive_causal_challenger", "club_def_prior_challenger"),
        provisional_active="adaptive_causal_challenger",
        podium_frozen_season="2026-27",
        podium_sealed=True,
    )
    save_model_selection(selection, config_path)
    loaded = load_model_selection(config_path)

    assert loaded == selection
    assert default_model_name(config_path) == "def_xg_shrink_challenger"
    assert active_transfer_plan_model_name(config_path) == "adaptive_causal_challenger"
    assert dual_tier_models(config_path) == [
        "def_xg_shrink_challenger",
        "adaptive_causal_challenger",
    ]
    assert projection_model_names(config_path=config_path) == [
        "def_xg_shrink_challenger",
        "adaptive_causal_challenger",
    ]
    for model in (None, "", "default", "Champion", selection.champion, selection.provisional_active):
        assert projection_model_names(model, config_path=config_path) == [
            "def_xg_shrink_challenger",
            "adaptive_causal_challenger",
        ]
    assert projection_model_names("linear_baseline", config_path=config_path) == ["linear_baseline"]
    assert projection_model_names("champion", ["linear_baseline"], config_path=config_path) == ["linear_baseline"]

    with pytest.raises(ValueError, match="Confirmed Champion"):
        ModelSelection(
            champion="def_xg_shrink_challenger",
            candidates=("def_xg_shrink_challenger",),
            provisional_active="def_xg_shrink_challenger",
        )
    with pytest.raises(ValueError, match="Comparison Slate"):
        ModelSelection(
            champion="def_xg_shrink_challenger",
            candidates=("club_def_prior_challenger",),
            provisional_active="adaptive_causal_challenger",
        )


def test_resolve_model_or_transfer_plan_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = tmp_path / "model_selection.json"
    save_model_selection(
        ModelSelection(
            champion="def_xg_shrink_challenger",
            candidates=("adaptive_causal_challenger",),
            provisional_active="adaptive_causal_challenger",
            podium_frozen_season="2026-27",
            podium_sealed=True,
        ),
        config_path,
    )
    monkeypatch.setattr("models.selection.DEFAULT_CONFIG_PATH", config_path)

    assert get_active_transfer_plan_model_name() == "adaptive_causal_challenger"
    assert resolve_model_or_transfer_plan_default(None) == "adaptive_causal_challenger"
    assert resolve_model_or_transfer_plan_default(None, force_champion=True) == "def_xg_shrink_challenger"
    assert resolve_model_or_transfer_plan_default("champion") == "def_xg_shrink_challenger"
    assert resolve_model_or_transfer_plan_default("club_def_prior_challenger") == "club_def_prior_challenger"


def test_load_champion_trust_exposes_dual_tier_and_dynamic_dev_season(tmp_path: Path) -> None:
    import pandas as pd

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
    lifecycle_path = tmp_path / "season_lifecycle.json"
    lifecycle_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "active_season": "2027-28",
                "seasons": {
                    "2027-28": {"role": "active_validation", "cycle_slot": "S", "prior_seed": "2026-27", "rules_id": "native-2027-28-v1"},
                    "2026-27": {"role": "development", "cycle_slot": "S-1", "prior_seed": "2025-26", "rules_id": "native-2026-27-v1"},
                    "2025-26": {"role": "historical_filter", "cycle_slot": "S-2", "prior_seed": "2024-25", "rules_id": "native-2025-26-v1"},
                },
            }
        ),
        encoding="utf-8",
    )
    bias_path = tmp_path / "bias.csv"
    pd.DataFrame(
        [
            {"model": "def_xg_shrink_challenger", "evaluation_season": "2025-26", "gw_start": 1, "gw_end": 38, "signed_bias": 0.1111},
            {"model": "def_xg_shrink_challenger", "evaluation_season": "2026-27", "gw_start": 1, "gw_end": 38, "signed_bias": -0.0456},
        ]
    ).to_csv(bias_path, index=False)

    trust = load_champion_trust(
        selection_path=sel_path,
        bias_path=bias_path,
        lifecycle_path=lifecycle_path,
    )
    assert trust["confirmed_champion"] == "def_xg_shrink_challenger"
    assert trust["provisional_active"] == "adaptive_causal_challenger"
    assert trust["dual_tier_active"] is True
    assert trust["active_transfer_plan_model"] == "adaptive_causal_challenger"
    assert trust["podium_sealed"] is True
    assert trust["bias_season"] == "2026-27"
    assert trust["signed_bias"] == -0.0456

