from __future__ import annotations

import numpy as np
import pandas as pd

from models.adaptive_causal_challenger import AdaptiveCausalChallengerModel
from models.base import resolve_asof_target_gw
from models.face_value_challenger import FaceValueChallengerModel
from models.learned_start_challenger import (
    _COVARIATES,
    _HIST_COLUMNS,
    _MIN_ROWS,
    _MIN_TRAIN_GW,
    _RIDGE_LAMBDA,
    _covariates,
    _panel,
    blend_states,
    learned_start_probabilities,
    target_start_probabilities,
)


def fit_binomial(
    x: np.ndarray, successes: np.ndarray, trials: np.ndarray, lam: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mean, std = x.mean(axis=0), x.std(axis=0)
    std = np.where(std > 1e-9, std, 1.0)
    design = np.column_stack([np.ones(len(x)), (x - mean) / std])
    penalty = np.eye(design.shape[1]) * lam
    penalty[0, 0] = 0.0
    beta = np.zeros(design.shape[1])
    for _ in range(50):
        p = 1.0 / (1.0 + np.exp(-np.clip(design @ beta, -30, 30)))
        w = trials * np.clip(p * (1.0 - p), 1e-9, None)
        step = np.linalg.solve(
            design.T @ (design * w[:, None]) + penalty,
            design.T @ (successes - trials * p) - penalty @ beta,
        )
        beta += step
        if np.max(np.abs(step)) < 1e-8:
            break
    return beta, mean, std


def fixture_exposures(history: pd.DataFrame) -> pd.DataFrame:
    keys = ["player_id", "gameweek_id"]
    hist = history[[*keys, "fixture_id", "starts"]].copy()
    fixture = pd.to_numeric(hist["fixture_id"], errors="coerce")
    starts = pd.to_numeric(hist["starts"], errors="coerce")
    valid = fixture.notna() & fixture.ge(0) & starts.isin([0, 1])
    consistent = hist.groupby([*keys, "fixture_id"])["starts"].transform("nunique").le(1)
    valid &= consistent
    hist["known"] = valid
    complete = hist.groupby(keys)["known"].all().rename("complete")
    hist = hist.loc[valid].drop_duplicates(subset=[*keys, "fixture_id"])
    hist["starts"] = pd.to_numeric(hist["starts"], errors="coerce")
    counts = hist.groupby(keys).agg(fixture_count=("fixture_id", "nunique"), start_count=("starts", "sum"))
    counts = counts.join(complete).reset_index()
    return counts.loc[counts["complete"] & counts["start_count"].le(counts["fixture_count"])]


def corrected_probabilities(history: pd.DataFrame, features: pd.DataFrame) -> dict[int, float]:
    if history.empty or features.empty or not set(_HIST_COLUMNS).issubset(history.columns):
        return {}
    target_gw = resolve_asof_target_gw(features, history)
    if target_gw < 20:
        return {}
    current = features[["player_id", "position_id", "club_id"]].drop_duplicates(subset=["player_id"])
    positions = current.set_index("player_id")["position_id"]
    history = history.loc[pd.to_numeric(history["gameweek_id"], errors="coerce").lt(target_gw)]
    panel = _panel(history)
    seen = current[current["player_id"].isin(panel["player_id"])]
    future = pd.DataFrame({
        "player_id": seen["player_id"], "gameweek_id": target_gw,
        "started": np.nan, "minutes": np.nan, "club": seen["club_id"],
    })
    cov = _covariates(pd.concat([panel, future], ignore_index=True), positions)
    train = cov.loc[
        cov["started"].notna() & cov["gameweek_id"].ge(_MIN_TRAIN_GW)
        & cov["n_prior"].ge(1) & cov["has_pos"]
    ].merge(fixture_exposures(history), on=["player_id", "gameweek_id"], how="inner")
    if len(train) < _MIN_ROWS or not train["fixture_count"].gt(1).any():
        return {}
    beta, mean, std = fit_binomial(
        train[list(_COVARIATES)].to_numpy(float), train["start_count"].to_numpy(float),
        train["fixture_count"].to_numpy(float), _RIDGE_LAMBDA,
    )
    pred = cov.loc[cov["gameweek_id"].eq(target_gw) & cov["started"].isna() & cov["n_prior"].ge(1)]
    x = (pred[list(_COVARIATES)].to_numpy(float) - mean) / std
    p = 1.0 / (1.0 + np.exp(-np.clip(beta[0] + x @ beta[1:], -30, 30)))
    return {int(pid): float(value) for pid, value in zip(pred["player_id"], p)}


class BinomialFixtureExposure(AdaptiveCausalChallengerModel):
    def __init__(self) -> None:
        super().__init__()
        self._fixture_targets: dict[tuple[int, int], float] | None = None

    @property
    def name(self) -> str:
        return "ext_09_binomial_fixture_exposure"

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        self._fixture_targets = None
        if not features_df.empty and resolve_asof_target_gw(features_df, self._raw_history) >= 20:
            corrected = corrected_probabilities(self._raw_history, features_df)
            if corrected:
                baseline = learned_start_probabilities(self._raw_history, features_df)
                genuine_rows = len(self._raw_history.drop_duplicates(subset=["player_id", "fixture_id"]))
                alpha = float(np.clip((genuine_rows - 3500.0) / 4000.0, 0.0, 1.0))
                blended = {pid: baseline[pid] + alpha * (value - baseline[pid])
                           for pid, value in corrected.items() if pid in baseline}
                self._fixture_targets = target_start_probabilities(
                    features_df, blended, target_gw=resolve_asof_target_gw(features_df, self._raw_history),
                )
        try:
            return super().predict(features_df, horizon)
        finally:
            self._fixture_targets = None

    def _state_probabilities(self, row: pd.Series) -> tuple[float, float, float]:
        if self._fixture_targets is None:
            return super()._state_probabilities(row)
        states = FaceValueChallengerModel._state_probabilities(row)
        fixture = row.get("fixture_id")
        target = None if fixture is None or pd.isna(fixture) else self._fixture_targets.get((int(row["player_id"]), int(fixture)))
        return super()._state_probabilities(row) if target is None else blend_states(*states, target)


PROTOTYPES = {"ext_09_binomial_fixture_exposure": BinomialFixtureExposure}
FEATURES = {"ext_09_binomial_fixture_exposure": (
    "history.player_id", "history.fixture_id", "history.gameweek_id", "history.starts",
    "history.minutes", "history.was_home", "history.opponent_club_id",
    "features.position_id", "features.club_id", "features.player_id", "features.fixture_id", "features.gameweek_id",
    "history.known", "history.complete", "history.fixture_count", "history.start_count", "history.started",
    "history.club", "history.n_prior", "history.has_pos", "local.coerce",
    "history.s_lag1", "history.s_lag2", "history.s_lag3", "history.s_lag4", "history.s_lag5", "history.s_lag6",
    "history.min3", "history.starts6", "history.since_start", "history.pos_gk", "history.pos_def", "history.pos_mid",
    "history.club_frac",
)}
