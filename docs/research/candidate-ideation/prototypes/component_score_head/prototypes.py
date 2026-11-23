"""Fit a direct score head on forecasts captured before their fixtures settled."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
import pandas as pd

from backtesting.walkforward import LEDGER_COMPONENTS
from models.base import resolve_asof_target_gw
from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel

_KEYS = ["player_id", "gameweek_id", "fixture_id"]
_RATE_STATS = {"bps": "projected_bps", "ict_index": "projected_ict"}
_POSITION_COLUMNS = {
    position: f"appearance_points_pos_{position}" for position in range(1, 5)
}
_RATE_PRIOR_MINUTES = 360.0
_DESIGN_COLUMNS = (
    *LEDGER_COMPONENTS,
    "projected_minutes",
    *_RATE_STATS.values(),
    *_POSITION_COLUMNS.values(),
)


def _project_rate_stat(
    history: pd.DataFrame,
    stat: str,
    positions: pd.Series,
    projections: pd.DataFrame,
) -> NDArray[np.float64]:
    events = pd.to_numeric(history[stat], errors="coerce")
    minutes = pd.to_numeric(history["minutes"], errors="coerce")
    valid = minutes.gt(0) & np.isfinite(minutes) & np.isfinite(events)
    totals = (
        pd.DataFrame({"event_sum": events[valid], "minute_sum": minutes[valid]})
        .groupby(history.loc[valid, "player_id"])
        .sum()
    )
    pooled = totals.groupby(positions).sum()
    position_rate = pooled["event_sum"] / pooled["minute_sum"]
    prior = positions.map(position_rate).fillna(0.0)
    totals = totals.reindex(prior.index, fill_value=0.0)
    player_rate = (totals["event_sum"] + prior * _RATE_PRIOR_MINUTES) / (
        totals["minute_sum"] + _RATE_PRIOR_MINUTES
    )
    return (
        projections["player_id"].map(player_rate) * projections["projected_minutes"]
    ).to_numpy(dtype=np.float64)


def design_matrix(
    features: pd.DataFrame, projections: pd.DataFrame, history: pd.DataFrame
) -> pd.DataFrame:
    """Return direct score predictors in the same order as the base forecast."""
    roster = features[["player_id", "position_id"]].drop_duplicates()
    positions = roster.set_index("player_id")["position_id"]
    if not positions.index.is_unique:
        raise ValueError("Score head requires one native position per player")
    row_positions = projections["player_id"].map(positions)
    if not row_positions.isin(_POSITION_COLUMNS).all():
        raise ValueError("Score head requires a known native position for each player")
    design = projections[[*_KEYS, *LEDGER_COMPONENTS, "projected_minutes"]].copy()
    for stat, projection_name in _RATE_STATS.items():
        design[projection_name] = _project_rate_stat(
            history, stat, positions, projections
        )
    for position, column in _POSITION_COLUMNS.items():
        # Switch off the position-specific baseline for zero participation.
        design[column] = row_positions.eq(position) * projections["xp_minutes"]
    if not np.isfinite(design[list(_DESIGN_COLUMNS)].to_numpy(dtype=float)).all():
        raise ValueError("Score head requires finite predictors")
    return design


def _training_rows(
    history: pd.DataFrame,
    prior_forecasts: list[tuple[int, pd.DataFrame]],
    issue: int,
) -> pd.DataFrame:
    published_issues = [origin for origin, _ in prior_forecasts]
    if len(set(published_issues)) != len(published_issues) or any(
        not 1 <= origin < issue for origin in published_issues
    ):
        raise ValueError(
            "Score head training origins must be distinct earlier deadlines"
        )
    for origin, rows in prior_forecasts:
        if (
            not rows["gameweek_id"].eq(origin).all()
            or not rows["fixture_id"].ge(0).all()
            or rows.duplicated(_KEYS).any()
        ):
            raise ValueError("Training forecasts require unique same-deadline fixtures")
    if not prior_forecasts:
        return pd.DataFrame(columns=[*_KEYS, *_DESIGN_COLUMNS, "total_points"])
    prior_rows = pd.concat([rows for _, rows in prior_forecasts], ignore_index=True)
    # Use official results already visible at this issue, including recorded DNPs.
    return prior_rows.loc[prior_rows["projected_minutes"].gt(0)].merge(
        history[[*_KEYS, "total_points"]], on=_KEYS, validate="one_to_one"
    )


class ComponentScoreHeadModel(DefXgShrinkChallengerModel):
    """Gaussian identity-link ridge model of signed native FPL points."""

    ridge_alpha = 0.01
    minimum_labeled_gameweeks = 4

    @property
    def name(self) -> str:
        return "component_score_head"

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        raise ValueError("Score head requires the historical replay forecast inputs")

    def predict_with_prior_forecasts(
        self,
        features: pd.DataFrame,
        horizon: int,
        history: pd.DataFrame,
        prior_forecasts: list[tuple[int, pd.DataFrame]],
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Project with the head and return base predictors for future training."""
        issue = resolve_asof_target_gw(features, history)
        training = _training_rows(history, prior_forecasts, issue)
        projections = super().predict(features, horizon)
        design = design_matrix(features, projections, history)
        publishable = projections["fixture_id"].ge(0) & projections["gameweek_id"].eq(
            issue
        )
        scoreable = projections["fixture_id"].ge(0) & projections[
            "projected_minutes"
        ].gt(0)
        projections["score_head_adjustment"] = 0.0
        if training["gameweek_id"].nunique() >= self.minimum_labeled_gameweeks:
            train_x = training[list(_DESIGN_COLUMNS)].to_numpy(dtype=float)
            train_y = pd.to_numeric(training["total_points"], errors="raise").to_numpy(
                dtype=float
            )
            if not np.isfinite(train_x).all() or not np.isfinite(train_y).all():
                raise ValueError(
                    "Score head requires finite training features and labels"
                )
            # RMS scaling gives each column comparable regularization while keeping
            # the zero-exposure origin. Ridge objective uses mean squared loss.
            scale = np.sqrt(np.mean(np.square(train_x), axis=0))
            scale[scale == 0] = 1.0
            train_x = train_x / scale
            penalty = len(train_x) * self.ridge_alpha * np.eye(train_x.shape[1])
            coefficients = np.linalg.solve(
                train_x.T @ train_x + penalty, train_x.T @ train_y
            )
            current_x = design.loc[scoreable, list(_DESIGN_COLUMNS)].to_numpy(
                dtype=float
            )
            learned_points = (current_x / scale) @ coefficients
            additive_points = projections.loc[scoreable, "projected_points"].to_numpy(
                dtype=float
            )
            projections.loc[scoreable, "score_head_adjustment"] = (
                learned_points - additive_points
            )
            projections.loc[scoreable, "projected_points"] = learned_points
        return projections, design.loc[publishable].copy()


PROTOTYPES = {"component_score_head": ComponentScoreHeadModel}
FEATURES = {
    "component_score_head": (
        "features.player_id",
        "features.position_id",
        "history.player_id",
        "history.gameweek_id",
        "history.fixture_id",
        "history.minutes",
        "history.bps",
        "history.ict_index",
        "history.total_points",
        "local.event_sum",
        "local.minute_sum",
        "local.score_head_adjustment",
    ),
}
