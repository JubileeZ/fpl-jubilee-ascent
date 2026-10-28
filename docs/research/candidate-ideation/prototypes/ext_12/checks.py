from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd

from backtesting.walkforward import LEDGER_COMPONENTS
from features.contracts import assert_projection_contract
from models.adaptive_causal_challenger import AdaptiveCausalChallengerModel
from test_face_value_challenger import _row
from prototypes import (
    AttackChangeDetectionModel,
    compute_change_factors,
)


def test_early_parity() -> None:
    champ = AdaptiveCausalChallengerModel()
    cand = AttackChangeDetectionModel()

    features = pd.DataFrame([
        _row(player_id=1, gameweek_id=5, fixture_id=10, position_id=3),
        _row(player_id=2, gameweek_id=5, fixture_id=11, position_id=4),
    ])
    history = pd.DataFrame({
        "player_id": [1, 2],
        "fixture_id": [1, 2],
        "gameweek_id": [1, 1],
        "minutes": [90.0, 90.0],
        "expected_goals": [0.5, 0.3],
        "expected_assists": [0.2, 0.1],
        "price": [8.0, 9.0],
    })
    champ.fit(history)
    cand.fit(history)

    pred_champ = champ.predict(features, 1)
    pred_cand = cand.predict(features, 1)

    diff = (pred_cand[list(LEDGER_COMPONENTS)] - pred_champ[list(LEDGER_COMPONENTS)]).abs().max().max()
    assert diff < 1e-9, f"Early parity violated: diff={diff}"
    print("test_early_parity: PASS")


def test_contract_reconciliation() -> None:
    cand = AttackChangeDetectionModel()
    n_players = 100
    rows = []
    for p in range(1, n_players + 1):
        for gw in range(1, 22):
            rows.append({
                "player_id": p,
                "fixture_id": p * 100 + gw,
                "gameweek_id": gw,
                "club_id": 1 if p <= 50 else 2,
                "opponent_club_id": 2 if p <= 50 else 1,
                "was_home": True if p <= 50 else False,
                "minutes": 90.0 if p % 2 == 0 else 45.0,
                "starts": 1.0 if p % 2 == 0 else 0.0,
                "expected_goals": 0.4 if gw > 15 else 0.1,
                "expected_assists": 0.2,
                "goals_scored": 0.0,
                "creativity": 10.0,
                "threat": 10.0,
                "bps": 10.0,
                "price": 7.5,
            })
    history = pd.DataFrame(rows)
    cand.fit(history)

    features = pd.DataFrame([
        _row(player_id=1, gameweek_id=22, fixture_id=9991, position_id=3, club_id=1, opponent_id=2, is_home=True),
        _row(player_id=2, gameweek_id=22, fixture_id=9992, position_id=4, club_id=1, opponent_id=2, is_home=True),
    ])
    pred = cand.predict(features, 1)
    assert_projection_contract(pred)

    sum_components = pred[list(LEDGER_COMPONENTS)].sum(axis=1)
    diff = (pred["projected_points"] - sum_components).abs().max()
    assert diff < 1e-9, f"Component reconciliation violated: diff={diff}"
    print("test_contract_reconciliation: PASS")


def test_factor_properties() -> None:
    # A player whose xG surged in recent matches relative to early matches
    history_surge = pd.DataFrame({
        "minutes": [90.0] * 10,
        "expected_goals": [0.05] * 5 + [0.9] * 5,
        "expected_assists": [0.05] * 5 + [0.9] * 5,
    })
    f_g, f_a = compute_change_factors(
        history_surge, mu_prior_g=0.2, mu_prior_a=0.2,
        change_hazard=1.0 / 48.0, dispersion=1.0, alpha=1.0, horizon_step=0,
    )
    assert f_g > 1.0, f"Expected surge goal factor > 1.0, got {f_g}"
    assert f_a > 1.0, f"Expected surge assist factor > 1.0, got {f_a}"

    # A player whose performance collapsed in recent matches relative to early matches
    history_slump = pd.DataFrame({
        "minutes": [90.0] * 10,
        "expected_goals": [0.9] * 5 + [0.05] * 5,
        "expected_assists": [0.9] * 5 + [0.05] * 5,
    })
    f_g_slump, f_a_slump = compute_change_factors(
        history_slump, mu_prior_g=0.2, mu_prior_a=0.2,
        change_hazard=1.0 / 48.0, dispersion=1.0, alpha=1.0, horizon_step=0,
    )
    assert f_g_slump < 1.0, f"Expected slump goal factor < 1.0, got {f_g_slump}"
    assert f_a_slump < 1.0, f"Expected slump assist factor < 1.0, got {f_a_slump}"
    print("test_factor_properties: PASS")


if __name__ == "__main__":
    test_early_parity()
    test_contract_reconciliation()
    test_factor_properties()
    print("ALL CHECKS PASSED")
