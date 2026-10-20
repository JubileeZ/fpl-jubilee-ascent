"""Unit tests for ApexPredatorChallengerModel."""

from __future__ import annotations

import pandas as pd

from features.contracts import assert_projection_contract
from models import get_model, list_model_names
from models.apex_predator_challenger import ApexPredatorChallengerModel
from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel
from tests.test_learned_start_challenger import _features, _start_history


def test_catalog_discovers_apex_predator_challenger() -> None:
    assert "apex_predator_challenger" in list_model_names()
    assert get_model("apex_predator_challenger").name == "apex_predator_challenger"


def test_apex_predator_matches_champion_before_min_ml_gw() -> None:
    history = _start_history()
    champ = DefXgShrinkChallengerModel()
    apex = ApexPredatorChallengerModel(min_ml_gw=10)

    champ.fit(history)
    apex.fit(history)

    # In GW5 (< 10), apex falls back 100% to Champion
    features_gw5 = _features(5)
    pred_champ = champ.predict(features_gw5, horizon=1)
    pred_apex = apex.predict(features_gw5, horizon=1)

    assert_projection_contract(pred_apex)
    pd.testing.assert_frame_equal(pred_apex, pred_champ)


def test_apex_predator_satisfies_projection_contract_at_gw10() -> None:
    history = _start_history()
    apex = ApexPredatorChallengerModel(min_ml_gw=10)
    apex.fit(history)

    features_gw10 = _features(10)
    pred = apex.predict(features_gw10, horizon=1)

    assert_projection_contract(pred)
    component_cols = [c for c in pred.columns if c.startswith("xp_")]
    reconstructed = pred[component_cols].sum(axis=1)
    diff = (pred["projected_points"] - reconstructed).abs().max()
    assert diff < 1e-9
