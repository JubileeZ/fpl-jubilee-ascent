"""Face-value Model Candidate (Champion search 2026-09-28).

Subclass of ``hold_chase_challenger`` with three levers from walk-forward smoke
tests (``docs/research/face-value-challenger``):

1. Attack at face value: goals ← per-90 xG, assists ← per-90 xA (weights 1.0 / 0.0).
   No in-season ridge refit on Realized goals/assists (it drifts to ~1.02 xG + 0.36
   threat and over-projects attackers).
2. Goal finishing offset pooled over minutes: Σ(goals − xG) · 90 / (Σ minutes + 1800).
   Replaces per-appearance n/(n+15) offsets that one cameo goal can blow up.
   No assist offset.
3. Start probability shrink for mid-range starters: p_start · (1 − k(1 − p_start)),
   k=0.15; removed mass → DNP (mid-range starts were overconfident).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from models.hold_chase_challenger import HoldChaseChallengerModel

_FACE_VALUE_WEIGHTS = (1.0, 0.0)
_FINISHING_SHRINK_MINUTES = 1800.0
_START_SHRINK_K = 0.15
_OFFSET_COLUMNS = ("player_id", "minutes", "goals_scored", "expected_goals")


class FaceValueChallengerModel(HoldChaseChallengerModel):
    """Hold-chase with face-value xG/xA, minute-pooled goal finishing, start shrink."""

    def __init__(self) -> None:
        super().__init__()
        self.goal_weights = np.array(_FACE_VALUE_WEIGHTS)
        self.assist_weights = np.array(_FACE_VALUE_WEIGHTS)

    @property
    def name(self) -> str:
        return "face_value_challenger"

    def fit(self, history_df: pd.DataFrame) -> None:
        """Goal finishing offsets from pre-cutoff history; weights stay at face value."""
        self.goal_offsets, self.assist_offsets = {}, {}
        if not set(_OFFSET_COLUMNS).issubset(history_df.columns):
            return
        history = pd.DataFrame(
            {column: pd.to_numeric(history_df[column], errors="coerce").astype(float) for column in _OFFSET_COLUMNS}
        ).fillna(0.0)
        history = history[history["minutes"] > 0]
        history["residual"] = history["goals_scored"] - self.goal_weights[0] * history["expected_goals"]
        pooled = history.groupby("player_id").agg(residual=("residual", "sum"), minutes=("minutes", "sum"))
        offsets = pooled["residual"] * 90.0 / (pooled["minutes"] + _FINISHING_SHRINK_MINUTES)
        self.goal_offsets = {int(player_id): float(value) for player_id, value in offsets.items()}

    @staticmethod
    def _state_probabilities(row: pd.Series) -> tuple[float, float, float]:
        p_dnp, p_start, p_sub_in = HoldChaseChallengerModel._state_probabilities(row)
        shrunk_start = p_start * (1.0 - _START_SHRINK_K * (1.0 - p_start))
        return 1.0 - shrunk_start - p_sub_in, shrunk_start, p_sub_in
