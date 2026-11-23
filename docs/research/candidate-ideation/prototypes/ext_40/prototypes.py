"""EXT-40 fixture counts and isolated scoring after Champion allocation."""

from __future__ import annotations

from typing import Literal

import numpy as np
import pandas as pd
from numpy.typing import NDArray
from scipy.optimize import minimize
from scipy.special import gammainc, logsumexp

from backtesting.forecast_export import REQUIRED_COMPONENTS, validate_components
from backtesting.season_rules import get_rules
from models.scoring_matrix import Position, event_points

FloatArray = NDArray[np.float64]
Component = Literal["goals", "assists"]
Mode = Literal["dynamic", "static", "prior"]
KEYS = ["player_id", "gameweek_id", "fixture_id"]
POSITIONS: dict[int, Position] = {1: "GK", 2: "D", 3: "M", 4: "F"}
OUTFIELD = (2, 3, 4)
STATE_COLUMNS = ["p_start", "p_sub_in", "p_dnp", "xmins_if_start", "xmins_if_sub_in"]
COUNT_COLUMNS = ["p_zero", "p_one", "p_two", "p_three_plus"]
EVENT: dict[Component, tuple[str, str]] = {
    "goals": ("expected_goals", "goals_scored"),
    "assists": ("expected_assists", "assists"),
}
# One fixed matched control and frozen-prior diagnostic per penalty and component.
GRID: tuple[tuple[Component, float, Mode], ...] = (
    ("goals", 0.03, "dynamic"),
    ("assists", 0.03, "dynamic"),
    ("goals", 0.10, "dynamic"),
    ("assists", 0.10, "dynamic"),
    ("goals", 0.03, "static"),
    ("assists", 0.03, "static"),
    ("goals", 0.10, "static"),
    ("assists", 0.10, "static"),
    ("goals", 0.03, "prior"),
    ("assists", 0.03, "prior"),
    ("goals", 0.10, "prior"),
    ("assists", 0.10, "prior"),
)
FEATURES = (
    "features.player_id",
    "features.code",
    "features.position_id",
    "features.gameweek_id",
    "features.fixture_id",
    "features.is_home",
    "features.opponent_id",
    "features.native_rules_version",
    "history.player_id",
    "history.gameweek_id",
    "history.fixture_id",
    "history.kickoff_time",
    "history.opponent_club_id",
    "history.was_home",
    "history.minutes",
    "history.starts",
    "history.expected_goals",
    "history.expected_assists",
    "history.goals_scored",
    "history.assists",
)


def poisson_categories(mu: FloatArray) -> tuple[FloatArray, FloatArray]:
    """Poisson masses and conditional means for 0, 1, 2 and 3+ counts."""
    if not np.isfinite(mu).all() or (mu < 0).any():
        raise ValueError("Poisson means must be finite and nonnegative")
    tail = gammainc(3, mu)
    tail_mean = np.divide(
        mu * gammainc(2, mu), tail, out=np.full_like(mu, 3.0), where=tail > 0
    )
    with np.errstate(divide="ignore"):
        log_mu = np.log(mu)
    q = np.column_stack(
        (np.exp(-mu), np.exp(log_mu - mu), np.exp(2 * log_mu - mu - np.log(2)), tail)
    )
    means = np.broadcast_to(np.array([0.0, 1.0, 2.0, 3.0]), q.shape).copy()
    means[:, 3] = tail_mean
    return q, means


def _design(
    rows: pd.DataFrame, dynamic: bool, extra_features: tuple[str, ...]
) -> FloatArray:
    rate = rows["rate"].to_numpy(dtype=float)
    position = rows["position_id"].to_numpy(dtype=float)
    form = rows["form"].to_numpy(dtype=float)
    matrix = np.column_stack(
        (
            np.ones(len(rows)),
            np.log1p(rate),
            position == 2,
            position == 4,
            rows["is_home"].to_numpy(dtype=float),
            rows["opponent_form"].to_numpy(dtype=float),
        )
    )
    if dynamic:
        matrix = np.column_stack((matrix, form, np.square(form)))
    if extra_features:
        matrix = np.column_stack(
            (matrix, rows[list(extra_features)].to_numpy(dtype=float))
        )
    if (
        not np.isfinite(matrix).all()
        or (rate < 0).any()
        or not np.isin(position, OUTFIELD).all()
    ):
        raise ValueError("Invalid outfield count predictors")
    return matrix


def _log_reference(mu: FloatArray) -> FloatArray:
    # Playing states use positive exposure and an explicit per-90 reference floor.
    # Compute exact-count logits directly so large exponents never erase mass.
    log_mu = np.log(mu)
    return np.column_stack(
        (-mu, log_mu - mu, 2 * log_mu - mu - np.log(2), np.log(gammainc(3, mu)))
    )


def fit_count_head(
    rows: pd.DataFrame,
    targets: FloatArray,
    *,
    penalty: float,
    dynamic: bool,
    prior: FloatArray | None = None,
    extra_features: tuple[str, ...] = (),
) -> FloatArray:
    """Fit source coefficients or the current-season penalized update."""
    matrix = _design(rows, dynamic, extra_features)
    shape = (matrix.shape[1], 3)
    if not np.isfinite(penalty) or penalty <= 0:
        raise ValueError("The count likelihood requires a positive penalty")
    if prior is None:
        if rows.empty:
            raise ValueError("No admitted source labels for count head")
        center = np.zeros(shape)
        scale = 1.0
    else:
        center = prior
        if center.shape != shape or not np.isfinite(center).all():
            raise ValueError("Invalid source coefficients for count head")
        gameweeks = rows["gameweek_id"].nunique()
        if gameweeks == 0:
            return prior.copy()
        scale = gameweeks / (gameweeks + 8.0)
    if (
        targets.shape != (len(rows), 4)
        or not np.isfinite(targets).all()
        or (targets < 0).any()
        or not np.allclose(targets.sum(axis=1), 1.0, atol=1e-12, rtol=0)
    ):
        raise ValueError("Invalid four-category training targets")
    minutes = rows["minutes"].to_numpy(dtype=float)
    if not np.isfinite(minutes).all() or (minutes <= 0).any():
        raise ValueError("Count training requires positive finite label exposure")
    mu = (
        np.minimum(minutes, 90)
        / 90
        * np.maximum(0.01, rows["rate"].to_numpy(dtype=float))
    )
    reference = _log_reference(mu)

    def objective(flat: FloatArray) -> tuple[float, FloatArray]:
        coefficient = flat.reshape(shape)
        logits = reference.copy()
        logits[:, 1:] += matrix @ coefficient
        log_prob = logits - logsumexp(logits, axis=1, keepdims=True)
        distance = coefficient - center
        loss = -scale * np.mean(np.sum(targets * log_prob, axis=1))
        gradient = (
            scale / len(rows) * matrix.T @ (np.exp(log_prob)[:, 1:] - targets[:, 1:])
        )
        return float(loss + 0.5 * penalty * np.square(distance).sum()), (
            gradient + penalty * distance
        ).ravel()

    result = minimize(
        objective,
        center.ravel(),
        jac=True,
        method="L-BFGS-B",
        options={"ftol": 1e-13, "gtol": 1e-10},
    )
    if not result.success or not np.isfinite(result.x).all():
        raise ValueError(f"Count likelihood optimization failed: {result.message}")
    return result.x.reshape(shape)


def state_distribution(
    issued: pd.DataFrame,
    coefficients: FloatArray | None,
    *,
    dynamic: bool,
    champion_rate: FloatArray | None = None,
    extra_features: tuple[str, ...] = (),
) -> tuple[FloatArray, FloatArray]:
    """Mix DNP, start and cameo laws using issued duration conditional means."""
    states = issued[STATE_COLUMNS].to_numpy(dtype=float)
    if (
        not np.isfinite(states).all()
        or (states < 0).any()
        or (states[:, :3] > 1).any()
        or not np.allclose(states[:, :3].sum(axis=1), 1, atol=1e-9, rtol=0)
    ):
        raise ValueError("Invalid issued Champion participation states")
    if coefficients is None:
        if (
            champion_rate is None
            or not np.isfinite(champion_rate).all()
            or (champion_rate < 0).any()
        ):
            raise ValueError("Missing or invalid derived Champion count rate")
        rate = champion_rate
        adjustment = None
    else:
        adjustment = _design(issued, dynamic, extra_features) @ coefficients
        rate = np.maximum(0.01, issued["rate"].to_numpy(dtype=float))
    probabilities = np.zeros((len(issued), 4))
    probabilities[:, 0] = states[:, 2]
    expected = np.zeros(len(issued))
    for probability, minutes in (
        (states[:, 0], states[:, 3]),
        (states[:, 1], states[:, 4]),
    ):
        mu = np.minimum(minutes, 90) / 90 * rate
        state_prob, means = poisson_categories(mu)
        if adjustment is not None:
            active = mu > 0
            logits = _log_reference(mu[active])
            logits[:, 1:] += adjustment[active]
            state_prob[active] = np.exp(
                logits - logsumexp(logits, axis=1, keepdims=True)
            )
        probabilities += probability[:, None] * state_prob
        expected += probability * np.sum(state_prob * means, axis=1)
    return probabilities, expected


def score_fixture_component(
    champion: pd.DataFrame,
    predictors: pd.DataFrame,
    component: Component | None,
    coefficients: FloatArray | None,
    rules_version: str,
    *,
    dynamic: bool,
    source_positions: frozenset[int] = frozenset(OUTFIELD),
    extra_features: tuple[str, ...] = (),
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Preserve issued keys and all other components; also return count diagnostics."""
    if component is None:
        return champion, pd.DataFrame()
    get_rules(rules_version)
    keys = pd.MultiIndex.from_frame(champion[KEYS])
    issue_keys = pd.MultiIndex.from_frame(predictors[KEYS])
    if not keys.is_unique or not issue_keys.is_unique or set(keys) != set(issue_keys):
        raise ValueError(
            "Champion and count predictors require identical unique fixture keys"
        )
    rows = predictors.set_index(KEYS).loc[keys].reset_index()
    rows[STATE_COLUMNS] = champion[STATE_COLUMNS].to_numpy()
    position = rows["position_id"].to_numpy(dtype=int)
    weights = np.array(
        [
            event_points(component, POSITIONS[p], 1, rules_version=rules_version)
            for p in position
        ]
    )
    column = f"xp_{component}"
    expected_count = champion[column].to_numpy(dtype=float) / weights
    states = rows[STATE_COLUMNS].to_numpy(dtype=float)
    expected_exposure = (
        states[:, 0] * np.minimum(states[:, 3], 90)
        + states[:, 1] * np.minimum(states[:, 4], 90)
    ) / 90
    if ((expected_exposure == 0) & (expected_count != 0)).any():
        raise ValueError("Champion has attacking points at zero exposure")
    derived_rate = np.divide(
        expected_count,
        expected_exposure,
        out=np.zeros(len(rows)),
        where=expected_exposure > 0,
    )
    probabilities, _ = state_distribution(
        rows, None, dynamic=False, champion_rate=derived_rate
    )
    supported = (
        (rows["fixture_id"].to_numpy(dtype=int) > 0)
        & np.isin(position, list(source_positions))
        & rows["rate"].notna().to_numpy()
    )
    support = rows["support"].to_numpy(copy=True)
    support[~supported] = "fallback_position_pool"
    support[~np.isin(position, OUTFIELD)] = "fallback_goalkeeper"
    support[rows["fixture_id"].eq(-1).to_numpy()] = "blank"
    if coefficients is None:
        support[rows["fixture_id"].gt(0).to_numpy()] = "champion_derived"
        forecast = champion
    else:
        probabilities[supported], expected_count[supported] = state_distribution(
            rows.loc[supported],
            coefficients,
            dynamic=dynamic,
            extra_features=extra_features,
        )
        forecast = champion.copy()
        forecast[column] = np.where(
            supported, expected_count * weights, champion[column]
        )
        forecast["projected_points"] = forecast[list(REQUIRED_COMPONENTS)].sum(axis=1)
        validate_components(forecast, rules_version)
        residual = forecast["projected_points"] - forecast[
            list(REQUIRED_COMPONENTS)
        ].sum(axis=1)
        if not residual.abs().le(1e-9).all():
            raise ValueError("Enabled component must reconcile to its native ledger")
    diagnostics = champion[KEYS].copy()
    diagnostics[COUNT_COLUMNS] = probabilities
    diagnostics["support"] = support
    return forecast, diagnostics
