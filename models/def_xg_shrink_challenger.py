"""DEF xG-shrink Model Candidate (explore-candidate Queue mode 2026-09-29; smoke variant ``atk_04_def2400``).

Subclass of ``learned_start_challenger`` with position-specific xG rate shrinkage (``docs/research/component-model-ideas``
idea ATK-04): DEF xG/90 shrinks to the as-of DEF mean with 2400 pseudo-minutes instead of 360 (split-half reliability of
DEF xG/90 is low). Applied as ratio ``rate_K / rate_360`` on ``features.per90_xg`` so builder prior, matchup addon and
penalty isolation survive. Both rates: current-season history before target GW, recency decay 0.95, position-mean
prior pooled over the same rows. Other positions and assists unchanged.
"""

from __future__ import annotations

import pandas as pd

from models.learned_start_challenger import LearnedStartChallengerModel

_BASE_K = 360.0
_POSITION_K: dict[int, float] = {2: 2400.0}
_DECAY = 0.95
_RATIO_CLIP = (0.1, 10.0)
_MIDFIELDER = 3
_HIST_COLUMNS = ("player_id", "gameweek_id", "minutes", "expected_goals")


def shrunk_xg_rates(hist: pd.DataFrame, positions: pd.Series, k_map: dict[int, float]) -> pd.Series:
    """player_id -> decayed xG/90 shrunk to position mean with K_pos pseudo-minutes (default 360)."""
    pos = hist["player_id"].map(positions).fillna(_MIDFIELDER)
    by_pos = hist.groupby(pos)[["expected_goals", "minutes"]].sum()
    pos_rate = by_pos["expected_goals"] / by_pos["minutes"].clip(lower=1.0) * 90.0
    last = hist.groupby("player_id")["gameweek_id"].transform("max")
    weight = _DECAY ** (last - hist["gameweek_id"])
    sums = pd.DataFrame({"events": hist["expected_goals"] * weight, "mins": hist["minutes"] * weight,
                         "player_id": hist["player_id"]}).groupby("player_id").sum()
    player_pos = positions.reindex(sums.index).fillna(_MIDFIELDER)
    prior = player_pos.map(pos_rate.to_dict()).fillna(0.0)
    k = player_pos.map(k_map).fillna(_BASE_K)
    return (sums["events"] + k * prior / 90.0) / (sums["mins"] + k) * 90.0


class DefXgShrinkChallengerModel(LearnedStartChallengerModel):
    """Learned-start Champion plus DEF xG/90 shrink K=2400 (other positions 360)."""

    def __init__(self) -> None:
        super().__init__()
        self._xg_hist = pd.DataFrame(columns=list(_HIST_COLUMNS))

    @property
    def name(self) -> str:
        return "def_xg_shrink_challenger"

    def fit(self, history_df: pd.DataFrame) -> None:
        super().fit(history_df)
        if history_df.empty or not set(_HIST_COLUMNS).issubset(history_df.columns):
            self._xg_hist = pd.DataFrame(columns=list(_HIST_COLUMNS))
            return
        hist = history_df[list(_HIST_COLUMNS)].apply(pd.to_numeric, errors="coerce").fillna(0.0)
        self._xg_hist = hist[hist["minutes"] > 0]

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        if self._xg_hist.empty:
            return super().predict(features_df, horizon)
        positions = features_df.drop_duplicates("player_id").set_index("player_id")["position_id"]
        new = shrunk_xg_rates(self._xg_hist, positions, _POSITION_K)
        old = shrunk_xg_rates(self._xg_hist, positions, {})
        ratio = (new / old.where(old > 1e-9)).fillna(1.0).clip(*_RATIO_CLIP)
        features = features_df.copy()
        features["per90_xg"] = features["per90_xg"] * features["player_id"].map(ratio).fillna(1.0).to_numpy()
        return super().predict(features, horizon)
