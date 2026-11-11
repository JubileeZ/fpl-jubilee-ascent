"""Synthetic EXT-35 checks; no season inputs or empirical outcomes."""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
from types import ModuleType

import numpy as np
import pandas as pd
import pytest

from models.calibrated_matchup_hybrid import CalibratedMatchupHybridModel
from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel, shrunk_xg_rates
from models.hold_chase_challenger import HoldChaseChallengerModel
from models.learned_start_challenger import LearnedStartChallengerModel
from models.multi_feature_assist_challenger import MultiFeatureAssistChallengerModel
from models.participation_state_hybrid import ParticipationStateHybridModel, target_to_states


def _module() -> ModuleType:
    path = Path(__file__).with_name("prototypes.py")
    spec = importlib.util.spec_from_file_location("ext_35_synthetic_prototypes", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PROTOTYPE = _module()
_STATE_COLUMNS = (
    "p_start", "p_sub_in", "p_dnp", "xmins_if_start", "xmins_if_sub_in", "p_60_if_start", "p_60_if_sub_in",
)


def _history(n_gws: int = 5) -> pd.DataFrame:
    identities = ((1, 1, 18.0, 0.12), (2, 2, 35.0, 0.40), (3, 3, 1.0, 0.02),
                  (4, 4, 20.0, 0.25), (5, 1, 40.0, 0.80), (6, 2, 100.0, 8.0))
    rows: list[dict[str, object]] = []
    for gw in range(1, n_gws + 1):
        for player_id, club, creativity, xg in identities:
            opponent = {1: 2, 2: 1, 3: 4, 4: 3}[club]
            rows.append({
                "player_id": player_id, "fixture_id": gw * 10 + (1 if club < 3 else 2),
                "gameweek_id": gw, "was_home": club in (1, 3), "opponent_club_id": opponent,
                "minutes": 90.0, "expected_goals": xg, "creativity": creativity,
                "starts": 1, "goals_scored": 0.0, "expected_assists": 0.03,
            })
    return pd.DataFrame(rows)


def _features(gw: int = 6) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for player_id, club in ((1, 1), (2, 2), (3, 3), (4, 4), (5, 1), (6, 2)):
        opponent = {1: 2, 2: 1, 3: 4, 4: 3}[club]
        rows.append({
            "player_id": player_id, "position_id": 3 if player_id == 6 else 2,
            "club_id": club, "opponent_id": opponent, "gameweek_id": gw,
            "fixture_id": gw * 10 + (1 if club < 3 else 2), "is_home": club in (1, 3),
            "per90_xg": 0.13, "per90_xa": 0.05, "p_start": 0.80, "p_sub_in": 0.10, "p_dnp": 0.10,
            "xmins_if_start": 78.0, "xmins_if_sub_in": 18.0,
            "p_60_if_start": 0.95, "p_60_if_sub_in": 0.0, "attack_multiplier": 0.70,
            "defence_multiplier": 1.0, "per90_goals_conceded": 1.10, "per90_defensive_contribution": 8.0,
            "penalties_order": 1 if player_id == 1 else 0, "difficulty": 3.0,
        })
    return pd.DataFrame(rows)


def _prepared(history: pd.DataFrame | None = None, features: pd.DataFrame | None = None) -> pd.DataFrame:
    history = _history() if history is None else history
    features = _features() if features is None else features
    positions = features.set_index("player_id")["position_id"]
    return PROTOTYPE.prepare_role_history(history, positions, int(features["gameweek_id"].min()))


def _delta(panel: pd.DataFrame, *, exclude: bool = True) -> tuple[float, float]:
    return PROTOTYPE.donor_prior_delta(
        panel, 1, 1, 6, 1.0, 0.70, h=0.45, k_pool=7200.0, exclude_target_club=exclude, cap=0.02,
    )


def _fingerprint(frame: pd.DataFrame) -> str:
    return hashlib.sha256(pd.util.hash_pandas_object(frame, index=True).to_numpy().tobytes()).hexdigest()


def test_exact_four_registered_variants() -> None:
    expected = ((0.45, 7200.0, True, 0.02), (0.70, 7200.0, True, 0.02),
                (0.45, 14400.0, True, 0.02), (0.45, 7200.0, False, 0.02))
    actual = []
    for name, cls in PROTOTYPE.PROTOTYPES.items():
        model = cls()
        assert name.startswith("ext_35_") and model.name == name
        assert issubclass(cls, DefXgShrinkChallengerModel)
        actual.append((model.h, model.k_pool, model.exclude_target_club, model.cap))
    assert tuple(actual) == expected


def test_whole_gw_lag_and_defender_only_population() -> None:
    history = _history()
    original = PROTOTYPE.lagged_donor_panel(_prepared(history))
    changed = history.copy()
    changed.loc[changed["gameweek_id"].eq(3), "creativity"] = 9999.0
    updated = PROTOTYPE.lagged_donor_panel(_prepared(changed))
    columns = ["player_id", "lag_role", "lag_role_reliability"]
    pd.testing.assert_frame_equal(
        original.loc[original["gameweek_id"].eq(3), columns].reset_index(drop=True),
        updated.loc[updated["gameweek_id"].eq(3), columns].reset_index(drop=True),
    )
    assert 6 not in original["player_id"].tolist()
    prior = _prepared(history.loc[history["gameweek_id"].eq(1)])
    role = PROTOTYPE.role_summary(prior).loc[2]
    pooled_creativity = prior["creativity"].sum() / prior["minutes"].sum() * 90.0
    expected_role = np.log1p((90.0 * 35.0 + 360.0 * pooled_creativity) / ((90.0 + 360.0) * 10.0))
    assert role["role"] == pytest.approx(expected_role)
    assert role["role_reliability"] == pytest.approx(90.0 / 450.0)


def test_double_fixture_gw_does_not_enter_its_own_role() -> None:
    history = _history()
    extra = history.loc[history["gameweek_id"].eq(3) & history["player_id"].isin([1, 2])].copy()
    extra["fixture_id"] = 999
    extra["creativity"] = 99999.0
    original = PROTOTYPE.lagged_donor_panel(_prepared(history))
    updated = PROTOTYPE.lagged_donor_panel(_prepared(pd.concat([history, extra], ignore_index=True)))
    columns = ["player_id", "lag_role", "lag_role_reliability"]
    before = original.loc[original["gameweek_id"].eq(3)].set_index("fixture_id")
    after = updated.loc[updated["gameweek_id"].eq(3) & updated["fixture_id"].ne(999)].set_index("fixture_id")
    pd.testing.assert_frame_equal(before[columns], after[columns])


def test_historical_club_not_current_club_and_malformed_sides_rejected() -> None:
    features = _features()
    features.loc[features["player_id"].eq(2), "club_id"] = 17
    prepared = _prepared(features=features)
    assert prepared.loc[prepared["player_id"].eq(2), "club"].eq(2).all()
    one_sided = _history().loc[lambda frame: frame["was_home"]]
    assert _prepared(one_sided).empty
    corrupt = _history()
    corrupt.loc[corrupt["player_id"].eq(6), "opponent_club_id"] = 19
    clean = _prepared(corrupt)
    assert not clean["player_id"].isin([1, 2, 5]).any()


def test_own_xg_primary_club_and_future_rows_leave_delta_unchanged() -> None:
    history = _history()
    panel = PROTOTYPE.lagged_donor_panel(_prepared(history))
    original = _delta(panel)
    history.loc[history["player_id"].eq(1), "expected_goals"] = 10000.0
    changed = PROTOTYPE.lagged_donor_panel(_prepared(history))
    assert _delta(changed) == pytest.approx(original)
    changed.loc[changed["club"].eq(1), "expected_goals"] = 100000.0
    assert _delta(changed) == pytest.approx(original)
    future = panel.copy()
    future["gameweek_id"] = 9
    assert _delta(pd.concat([panel, future], ignore_index=True)) == pytest.approx(original)
    assert _delta(panel, exclude=False)[0] != pytest.approx(original[0], abs=1e-8)


def test_fixed_k_own_xg_coefficient_and_prior_shift() -> None:
    weighted_xg, minutes, prior, delta = 2.0, 450.0, 0.10, 0.01
    rate = PROTOTYPE.fixed_k_defender_rate(weighted_xg, minutes, prior)
    impulse = PROTOTYPE.fixed_k_defender_rate(weighted_xg + 0.50, minutes, prior)
    shifted = PROTOTYPE.fixed_k_defender_rate(weighted_xg, minutes, prior + delta)
    assert impulse - rate == pytest.approx(90.0 * 0.50 / (minutes + 2400.0))
    assert shifted - rate == pytest.approx(2400.0 * delta / (minutes + 2400.0))
    model = next(iter(PROTOTYPE.PROTOTYPES.values()))()
    model.fit(_history())
    _, _, diagnostics = model.prepare_event_features(_features())
    expected = 2400.0 * diagnostics["prior_delta"] / (diagnostics["weighted_minutes"] + 2400.0)
    actual = diagnostics["candidate_xg_rate"] - diagnostics["champ_xg_rate"]
    np.testing.assert_allclose(actual, expected, atol=1e-15)


def test_exposure_cap_and_invalid_pool_fallback() -> None:
    panel = PROTOTYPE.lagged_donor_panel(_prepared())
    invalid = panel.copy()
    invalid["expected_goals"] = np.inf
    assert _delta(invalid) == (0.0, 0.0)
    invalid["expected_goals"] = -1.0
    assert _delta(invalid) == (0.0, 0.0)
    invalid["player_id"] = 0.0
    assert _delta(invalid) == (0.0, 0.0)
    duplicated = pd.concat([panel] * 100, ignore_index=True)
    delta, n_eff = _delta(duplicated)
    assert np.isfinite([delta, n_eff]).all()
    assert abs(delta) <= 0.02 and n_eff <= 3.0 + 1e-12
    flat = panel.copy()
    flat["expected_goals"] = flat["minutes"] * 0.1 / 90.0
    assert _delta(flat)[0] == pytest.approx(0.0, abs=1e-15)


def _post_hold_chase(model: HoldChaseChallengerModel, frame: pd.DataFrame, monkeypatch: pytest.MonkeyPatch) -> pd.DataFrame:
    def capture(_self: object, prepared: pd.DataFrame, _horizon: int) -> pd.DataFrame:
        return prepared.copy()

    monkeypatch.setattr(CalibratedMatchupHybridModel, "predict", capture)
    return model.predict(frame, 1)


@pytest.mark.parametrize("missing", [False, True])
def test_tilt_compensation_both_directions_and_missing_duration(
    monkeypatch: pytest.MonkeyPatch, missing: bool,
) -> None:
    champion = pd.DataFrame({"per90_xg": [0.45, 0.46, 0.10], "per90_xa": [0.24, 0.24, 0.02], "difficulty": [3.0] * 3})
    candidate = champion.copy()
    candidate["per90_xg"] = [0.46, 0.45, 0.11]
    for column, value in (("xmins_if_start", 78.0), ("xmins_if_sub_in", 18.0)):
        champion[column] = [np.nan, "invalid", value] if missing else value
        candidate[column] = champion[column]
    compensated = PROTOTYPE.compensate_minute_tilt(champion, candidate)
    base = _post_hold_chase(HoldChaseChallengerModel(), champion, monkeypatch)
    actual = _post_hold_chase(HoldChaseChallengerModel(), compensated, monkeypatch)
    for column, state, default in (("xmins_if_start", "start", 78.0), ("xmins_if_sub_in", "sub_in", 18.0)):
        expected = [ParticipationStateHybridModel._conditional_minutes(row, state, default) for _, row in base.iterrows()]
        observed = [ParticipationStateHybridModel._conditional_minutes(row, state, default) for _, row in actual.iterrows()]
        assert observed == pytest.approx(expected)
        assert compensated.iloc[2][column] == candidate.iloc[2][column]
    absent = champion.drop(columns=["xmins_if_start", "xmins_if_sub_in"])
    absent_candidate = candidate.drop(columns=["xmins_if_start", "xmins_if_sub_in"])
    assert set(PROTOTYPE.compensate_minute_tilt(absent, absent_candidate).columns) == set(absent.columns)


def test_identity_fallback_exact_parent_and_inputs_immutable() -> None:
    history, features = _history(), _features()
    original_history, original_features = history.copy(deep=True), features.copy(deep=True)
    candidate = next(iter(PROTOTYPE.PROTOTYPES.values()))()
    parent = DefXgShrinkChallengerModel()
    broken = history.drop(columns=["creativity"])
    candidate.fit(broken)
    parent.fit(broken)
    pd.testing.assert_frame_equal(candidate.predict(features, 1), parent.predict(features, 1))
    candidate.fit(history)
    candidate.prepare_event_features(features)
    assert not candidate._history.empty
    parent.fit(history)
    pd.testing.assert_frame_equal(candidate._history, parent._history)
    pd.testing.assert_frame_equal(history, original_history)
    pd.testing.assert_frame_equal(features, original_features)


def test_parent_assist_cache_penalty_convention_and_single_shrink(monkeypatch: pytest.MonkeyPatch) -> None:
    history, features = _history(), _features()
    candidate = next(iter(PROTOTYPE.PROTOTYPES.values()))()
    parent = DefXgShrinkChallengerModel()
    candidate.fit(history)
    parent.fit(history)
    pd.testing.assert_frame_equal(candidate._history, parent._history)
    pd.testing.assert_frame_equal(candidate._raw_history, parent._raw_history)
    positions = features.set_index("player_id")["position_id"]
    old = shrunk_xg_rates(candidate._xg_hist, positions, {})
    champion_rates = shrunk_xg_rates(candidate._xg_hist, positions, {2: 2400.0})
    base, changed, _ = candidate.prepare_event_features(features)
    np.testing.assert_allclose(base["per90_xg"], features["per90_xg"] * features["player_id"].map(champion_rates / old))
    seen: list[pd.DataFrame] = []

    def assist_rates(self: MultiFeatureAssistChallengerModel, frame: pd.DataFrame) -> dict[tuple[int, int], float]:
        seen.append(self._history.copy())
        return {(int(row["player_id"]), int(row["fixture_id"])): 0.20 for _, row in frame.iterrows()}

    monkeypatch.setattr(MultiFeatureAssistChallengerModel, "_fit_assist_rates", assist_rates)
    reference, actual = parent.predict(features, 1), candidate.predict(features, 1)
    np.testing.assert_allclose(actual["xp_assists"], reference["xp_assists"])
    assert len(seen) == 2
    pd.testing.assert_frame_equal(seen[0], seen[1])
    for column in _STATE_COLUMNS:
        np.testing.assert_allclose(actual[column], reference[column])
    row = pd.Series({"player_id": 1, "per90_xg": 0.30, "penalties_order": 1, "attack_multiplier": 0.50})
    event = CalibratedMatchupHybridModel._project_event_components(
        candidate, row, "D", 90.0, clean_sheet_minutes=90.0, p_sixty_mins=1.0,
    )
    finishing = candidate.goal_offsets.get(1, 0.0)
    expected = ((0.30 + finishing - 0.15) * 0.50 + 0.15) * 6.0
    assert event["xp_goals"] == pytest.approx(expected)
    assert changed.loc[features["position_id"].ne(2), "per90_xg"].equals(base.loc[features["position_id"].ne(2), "per90_xg"])


def test_frozen_event_inputs_shared_native_and_oracle_states() -> None:
    features = _features()
    for cls in PROTOTYPE.PROTOTYPES.values():
        candidate, parent = cls(), DefXgShrinkChallengerModel()
        candidate.fit(_history())
        parent.fit(_history())
        base, changed, _ = candidate.prepare_event_features(features)
        frozen_rates = (_fingerprint(base[["per90_xg"]]), _fingerprint(changed[["per90_xg"]]))
        native_parent = parent.predict(features, 1)
        native_candidate = candidate.predict(features, 1)
        pd.testing.assert_frame_equal(native_parent[list(_STATE_COLUMNS)], native_candidate[list(_STATE_COLUMNS)])
        external = features.assign(external_xmins=[0.0, 10.0, 50.0, 75.0, 90.0, 30.0])
        oracle_base, oracle_changed, _ = candidate.prepare_event_features(external)
        assert (_fingerprint(oracle_base[["per90_xg"]]), _fingerprint(oracle_changed[["per90_xg"]])) == frozen_rates
        oracle_parent = parent.predict(external, 1)
        oracle_candidate = candidate.predict(external, 1)
        pd.testing.assert_frame_equal(oracle_parent[list(_STATE_COLUMNS)], oracle_candidate[list(_STATE_COLUMNS)])
        for index, minutes in enumerate(external["external_xmins"]):
            expected = target_to_states(float(minutes))
            assert oracle_parent.loc[index, ["p_start", "p_sub_in", "p_dnp", "xmins_if_start", "xmins_if_sub_in"]].tolist() == pytest.approx(expected)
        assert _fingerprint(native_parent[list(_STATE_COLUMNS)]) != _fingerprint(oracle_parent[list(_STATE_COLUMNS)])
        for result in (native_parent, native_candidate, oracle_parent, oracle_candidate):
            components = [column for column in result.columns if column.startswith("xp_")]
            np.testing.assert_allclose(result["projected_points"], result[components].sum(axis=1), atol=1e-12)
        assert LearnedStartChallengerModel._project_event_components is candidate._project_event_components.__func__
