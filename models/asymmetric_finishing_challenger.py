"""Asymmetric-finishing Model Candidate (explore-candidate dual-lane 2026-09-28).

Subclass of ``learned_start_challenger`` with asymmetric goal finishing shrinkage (``docs/research/asymmetric-finishing-challenger``):

- Goal finishing offset pooled over minutes with asymmetric shrinkage:
  ``res = goals_scored - expected_goals``.
  - If ``res >= 0.0``: ``offset = res * 90.0 / (minutes + 1500.0)`` (responsive to positive finishing skill/form).
  - If ``res < 0.0``: ``offset = res * 90.0 / (minutes + 3000.0)`` (faster regression to mean for cold streaks).
  Prevents over-penalizing elite attackers during temporary finishing slumps while capturing persistent positive overperformance.
"""

from __future__ import annotations

import pandas as pd

from models.learned_start_challenger import LearnedStartChallengerModel

_OFFSET_COLUMNS = ("player_id", "minutes", "goals_scored", "expected_goals")
_FINISHING_SHRINK_POS = 1500.0
_FINISHING_SHRINK_NEG = 3000.0


class AsymmetricFinishingChallengerModel(LearnedStartChallengerModel):
    """Learned-start Champion plus asymmetric goal finishing shrinkage (K_pos=1500, K_neg=3000)."""

    @property
    def name(self) -> str:
        return "asymmetric_finishing_challenger"

    def fit(self, history_df: pd.DataFrame) -> None:
        """Goal finishing offsets from pre-cutoff history with asymmetric shrinkage."""
        super().fit(history_df)
        if not set(_OFFSET_COLUMNS).issubset(history_df.columns):
            return
        history = pd.DataFrame(
            {column: pd.to_numeric(history_df[column], errors="coerce").astype(float) for column in _OFFSET_COLUMNS}
        ).fillna(0.0)
        history = history[history["minutes"] > 0]
        history["residual"] = history["goals_scored"] - self.goal_weights[0] * history["expected_goals"]
        pooled = history.groupby("player_id", as_index=True).agg(
            residual=("residual", "sum"), minutes=("minutes", "sum")
        )

        offsets: dict[int, float] = {}
        for pid, row in pooled.iterrows():
            res = float(row["residual"])
            mins = float(row["minutes"])
            if res >= 0.0:
                offsets[int(pid)] = res * 90.0 / (mins + _FINISHING_SHRINK_POS)
            else:
                offsets[int(pid)] = res * 90.0 / (mins + _FINISHING_SHRINK_NEG)
        self.goal_offsets = offsets
