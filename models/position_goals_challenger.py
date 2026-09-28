"""Position-split goals projection.

FWD keeps hold-chase haul sharp and full fitted goal weights (late top-11 hole).
Other positions keep the goals-path identity xG and ``_GOAL_WEIGHT_SCALE`` dampen
(pool MAE). Ceiling minutes tilt stays on every position so xMins can match Champion.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from models.calibrated_matchup_hybrid import CalibratedMatchupHybridModel
from models.goals_path_challenger import _GOAL_WEIGHT_SCALE
from models.hold_chase_challenger import (
    HoldChaseChallengerModel,
    _CEILING_TILT_FROM,
    _MINS_TILT,
    _XG_SHARP_FROM,
    _XG_SHARP_SLOPE,
    _XG_TRIM_BELOW,
    _XG_TRIM_FACTOR,
)


class PositionGoalsChallengerModel(HoldChaseChallengerModel):
    """Champion participation and defence; goals conversion split by position."""

    def __init__(self) -> None:
        super().__init__()
        self._apply_position_goal_weights()

    @property
    def name(self) -> str:
        return "position_goals_challenger"

    def _apply_position_goal_weights(self) -> None:
        self._fwd_goal_weights = np.asarray(self.goal_weights, dtype=float).copy()
        self.goal_weights = self._fwd_goal_weights * float(_GOAL_WEIGHT_SCALE)

    def fit(self, history_df: pd.DataFrame) -> None:
        HoldChaseChallengerModel.fit(self, history_df)
        self._apply_position_goal_weights()

    def _project_event_components(
        self,
        row: pd.Series,
        position: str,
        expected_minutes: float,
        *,
        clean_sheet_minutes: float,
        p_sixty_mins: float,
    ) -> dict[str, float]:
        saved = self.goal_weights
        if position == "F":
            self.goal_weights = self._fwd_goal_weights
        try:
            return CalibratedMatchupHybridModel._project_event_components(
                self,
                row,
                position,
                expected_minutes,
                clean_sheet_minutes=clean_sheet_minutes,
                p_sixty_mins=p_sixty_mins,
            )
        finally:
            self.goal_weights = saved

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        feat = features_df.copy()
        xg = pd.to_numeric(feat.get("per90_xg", 0.0), errors="coerce").fillna(0.0)
        xa = pd.to_numeric(feat.get("per90_xa", 0.0), errors="coerce").fillna(0.0)
        fwd = pd.to_numeric(feat.get("position_id", 3), errors="coerce").fillna(3).eq(4)
        sharp = 1.0 + _XG_SHARP_SLOPE * ((xg - _XG_SHARP_FROM) / _XG_SHARP_FROM).clip(lower=0.0, upper=1.0)
        sharp = sharp.where(xg >= _XG_TRIM_BELOW, _XG_TRIM_FACTOR)
        feat["per90_xg"] = xg.where(~fwd, (xg * sharp).clip(lower=0.0))
        ceiling = (pd.to_numeric(feat["per90_xg"], errors="coerce").fillna(0.0) + xa) >= _CEILING_TILT_FROM
        for column in ("xmins_if_start", "xmins_if_sub_in"):
            if column in feat.columns:
                feat.loc[ceiling, column] = (
                    pd.to_numeric(feat.loc[ceiling, column], errors="coerce").fillna(0.0) * _MINS_TILT
                )
        feat = self._apply_hard_fixture_defence(feat)
        return CalibratedMatchupHybridModel.predict(self, feat, horizon)
