from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))
sys.path.insert(0, str(Path(__file__).resolve().parents[5] / "tests"))

from prototypes import OpponentRoleAllocation, RoleFixture, fit_contrasts, normalized_counts, profiles_before, training_fixtures
from test_face_value_challenger import _row

from backtesting.walkforward import LEDGER_COMPONENTS
from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel
from models.learned_start_challenger import LearnedStartChallengerModel
from models.scoring_matrix import event_points


def history_frame() -> tuple[pd.DataFrame, pd.Series]:
    rows: list[dict[str, object]] = []
    positions = pd.Series({1: 3, 2: 3, 3: 4, 4: 3, 5: 3, 6: 4})
    for gw in (1, 2, 3):
        for player in range(1, 7):
            shooter = player in (1, 3, 4, 6)
            rows.append({
                "player_id": player, "fixture_id": 100 + gw, "gameweek_id": gw,
                "was_home": player <= 3, "opponent_club_id": 2 if player <= 3 else 1,
                "minutes": 90.0, "expected_goals": 0.8 if shooter else 0.02,
                "expected_assists": 0.02 if shooter else 0.8, "price": 65.0,
            })
    return pd.DataFrame(rows), positions


def forecast_frame() -> pd.DataFrame:
    return pd.DataFrame([
        _row(player_id=i, gameweek_id=20, position_id=3 if i % 2 else 4,
             club_id=1 if i <= 2 else 2, opponent_id=2 if i <= 2 else 1,
             p_start=0.7 + 0.03 * i, p_sub_in=0.1, p_dnp=0.2 - 0.03 * i,
             per90_xg=0.15 + 0.1 * i)
        for i in range(1, 5)
    ])


def test_profile_and_offset_use_only_prior_observation() -> None:
    history, positions = history_frame()
    profiles = profiles_before(history, positions, 2)
    changed = history.copy()
    changed.loc[changed["gameweek_id"] >= 2, ["expected_goals", "expected_assists", "price"]] = [20.0, 0.0, 140.0]
    assert profiles == profiles_before(changed, positions, 2)
    base_rows = training_fixtures(history, positions, 4)
    altered_rows = training_fixtures(changed, positions, 4)
    for original, altered in zip(base_rows[:2], altered_rows[:2], strict=True):
        np.testing.assert_allclose(original.offsets, altered.offsets)
    assert profiles[1][0] == 0
    assert profiles[2][0] == 1
    assert profiles[3][0] == 2


def test_likelihood_learns_centered_role_contrast() -> None:
    observations = [RoleFixture(2, np.ones(3), np.array([3.0, 0.2, 0.2])) for _ in range(20)]
    theta = fit_contrasts(observations, 25.0)[2]
    assert theta[0] > theta[1]
    assert abs(float(theta.sum())) < 1e-10
    assert np.linalg.norm(fit_contrasts(observations, 100.0)[2]) < np.linalg.norm(theta)


def test_scalar_cancels_and_counts_are_conserved() -> None:
    counts = np.array([0.2, 0.4, 0.1])
    np.testing.assert_array_equal(normalized_counts(counts, np.full(3, 0.07), 1.0), counts)
    corrected = normalized_counts(counts, np.array([0.09, -0.09, 0.0]), 1.0)
    assert corrected[0] > counts[0]
    assert abs(float(corrected.sum() - counts.sum())) < 1e-12


def test_final_totals_after_group_a_and_original_bonus_states() -> None:
    features = forecast_frame()
    model = OpponentRoleAllocation()
    model.fit(pd.DataFrame())
    final = model.predict(features, 1)
    final["xp_goals"] *= np.array([1.2, 0.8, 1.1, 0.9])
    final["projected_points"] = final[list(LEDGER_COMPONENTS)].sum(axis=1)
    final["p_start"] *= 0.5
    profiles = {1: (0, 0.2), 2: (2, 0.4), 3: (0, 0.2), 4: (2, 0.4)}
    contrasts = {1: np.array([-0.08, 0.0, 0.03]), 2: np.array([0.07, 0.0, -0.05])}
    result = model._apply_role_counts(features, final, profiles, contrasts, 1.0)
    old_counts = final["xp_goals"].to_numpy() / np.array([5.0, 4.0, 5.0, 4.0])
    new_counts = result["xp_goals"].to_numpy() / np.array([5.0, 4.0, 5.0, 4.0])
    assert not np.allclose(new_counts, old_counts)
    for club in (1, 2):
        mask = features["club_id"].eq(club).to_numpy()
        assert abs(float(new_counts[mask].sum() - old_counts[mask].sum())) < 1e-12
    anchor = [component.copy() for component in model._anchor_components]
    for i, component in enumerate(anchor):
        component["xbps"] = float(component["xbps"]) + 24.0 * float(new_counts[i] - old_counts[i])
        component["xp_bonus"], component["projected_points"] = 0.0, 0.0
    LearnedStartChallengerModel._allocate_bonus(model, anchor, defaultdict(list))
    np.testing.assert_allclose(result["xp_bonus"], [c["xp_bonus"] for c in anchor], atol=1e-12)
    pd.testing.assert_series_equal(result["p_start"], final["p_start"])
    np.testing.assert_allclose(result["projected_points"], result[list(LEDGER_COMPONENTS)].sum(axis=1))
    assert event_points("goals", "M", 1.0) == 5.0


def test_missing_sides_and_no_correction_return_exact_champion_output() -> None:
    model = OpponentRoleAllocation()
    model.fit(pd.DataFrame())
    features = forecast_frame()
    final = model.predict(features, 1)
    profiles = {i: (0 if i % 2 else 2, 0.2) for i in range(1, 5)}
    theta = {1: np.array([0.1, 0.0, -0.1]), 2: np.array([0.1, 0.0, -0.1])}
    pd.testing.assert_frame_equal(model._apply_role_counts(features, final, profiles, theta, 0.0), final)
    zeros = {1: np.zeros(3), 2: np.zeros(3)}
    pd.testing.assert_frame_equal(model._apply_role_counts(features, final, profiles, zeros, 1.0), final)
    one_side = features.iloc[:2].copy()
    one_final = model.predict(one_side, 1)
    pd.testing.assert_frame_equal(model._apply_role_counts(one_side, one_final, profiles, theta, 1.0), one_final)


def test_unknown_historical_sides_are_excluded() -> None:
    history, positions = history_frame()
    one_side = history[history["was_home"]].copy()
    assert training_fixtures(one_side, positions, 4) == []


def test_early_parity() -> None:
    features = forecast_frame().assign(gameweek_id=19)
    candidate, champion = OpponentRoleAllocation(), DefXgShrinkChallengerModel()
    candidate.fit(pd.DataFrame())
    champion.fit(pd.DataFrame())
    pd.testing.assert_frame_equal(candidate.predict(features, 1), champion.predict(features, 1))
