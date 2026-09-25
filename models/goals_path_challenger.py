"""Goals-path Model Candidate (wayfinder #111 / #116).

Subclass of ``hold_chase_challenger``: identity xG sharp/trim, no ceiling minutes
tilt, keep start-persistence + hard-fixture defence relax; after ``fit``, scale
fitted ``goal_weights`` by data-driven ``_GOAL_WEIGHT_SCALE`` toward gate
``xp_goals`` |signed_bias| ≤ τ=0.05. Recalibrate via
``docs/research/champion-component-gap/calibrate_goals_k.py``.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from models.calibrated_matchup_hybrid import CalibratedMatchupHybridModel
from models.hold_chase_challenger import HoldChaseChallengerModel

# Set by calibrate_goals_k.py from 2025-26 gate pool=all / ALL xp_goals (τ=0.05).
_GOAL_WEIGHT_SCALE = 0.891559


class GoalsPathChallengerModel(HoldChaseChallengerModel):
    """Hold-chase participation/defence without haul xG sharp; conversion scale ``k``."""

    @property
    def name(self) -> str:
        return "goals_path_challenger"

    def fit(self, history_df: pd.DataFrame) -> None:
        super().fit(history_df)
        self.goal_weights = np.asarray(self.goal_weights, dtype=float) * float(_GOAL_WEIGHT_SCALE)

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        # Identity sharp/ceiling: skip HoldChaseChallengerModel.predict haul levers.
        feat = self._apply_hard_fixture_defence(features_df.copy())
        return CalibratedMatchupHybridModel.predict(self, feat, horizon)
