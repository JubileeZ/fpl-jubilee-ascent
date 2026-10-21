"""Unit tests for AdaptiveCausalChallengerModel."""

from __future__ import annotations

import pandas as pd

from features.contracts import assert_projection_contract
from models import get_model, list_model_names
from models.adaptive_causal_challenger import AdaptiveCausalChallengerModel
from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel
from tests.test_learned_start_challenger import _features, _start_history


def test_catalog_discovers_adaptive_causal_challenger() -> None:
    assert "adaptive_causal_challenger" in list_model_names()
    assert get_model("adaptive_causal_challenger").name == "adaptive_causal_challenger"


def test_adaptive_causal_matches_champion_before_min_ml_gw() -> None:
    history = _start_history()
    champ = DefXgShrinkChallengerModel()
    cand = AdaptiveCausalChallengerModel(min_ml_gw=20)

    champ.fit(history)
    cand.fit(history)

    # In GW10 (< 20), candidate falls back 100% to Champion
    features_gw10 = _features(10)
    pred_champ = champ.predict(features_gw10, horizon=1)
    pred_cand = cand.predict(features_gw10, horizon=1)

    assert_projection_contract(pred_cand)
    pd.testing.assert_frame_equal(pred_cand, pred_champ)


def test_adaptive_causal_satisfies_projection_contract_at_gw20() -> None:
    history = _start_history()
    cand = AdaptiveCausalChallengerModel(min_ml_gw=20)
    cand.fit(history)

    features_gw20 = _features(20)
    pred = cand.predict(features_gw20, horizon=1)

    assert_projection_contract(pred)
    component_cols = [c for c in pred.columns if c.startswith("xp_")]
    reconstructed = pred[component_cols].sum(axis=1)
    diff = (pred["projected_points"] - reconstructed).abs().max()
    assert diff < 1e-9
