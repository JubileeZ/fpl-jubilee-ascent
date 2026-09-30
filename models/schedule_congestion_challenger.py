"""Schedule congestion start shift Model Candidate (explore-candidate Queue mode 2026-09-30; idea MIN-07).

Subclass of ``club_def_prior_challenger``: applies a -0.2 logit shift to learned p_start for fixtures occurring
less than 3.5 days after the player's previous fixture kickoff (schedule congestion / short rest penalty).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from models.club_def_prior_challenger import ClubDefPriorChallengerModel, club_def_ratio
from models.learned_start_challenger import (
    MultiFeatureAssistChallengerModel,
    learned_start_probabilities,
    target_start_probabilities,
)

_CONGESTION_DAYS = 3.5
_LOGIT_SHIFT = -0.2


class ScheduleCongestionChallengerModel(ClubDefPriorChallengerModel):
    """ClubDefPriorChallenger plus logit shift (-0.2) on p_start for short-rest (<3.5 days) fixtures."""

    def __init__(self) -> None:
        super().__init__()
        self._last_kickoff_by_player: dict[int, pd.Timestamp] = {}

    @property
    def name(self) -> str:
        return "schedule_congestion_challenger"

    def fit(self, history_df: pd.DataFrame) -> None:
        super().fit(history_df)
        if not history_df.empty and "kickoff_time" in history_df.columns:
            valid = history_df.dropna(subset=["kickoff_time", "player_id"])
            if not valid.empty:
                times = pd.to_datetime(valid["kickoff_time"], utc=True, errors="coerce")
                mask = times.notna()
                if mask.any():
                    self._last_kickoff_by_player = (
                        times[mask].groupby(valid.loc[mask, "player_id"].astype(int)).max().to_dict()
                    )
                    return
        self._last_kickoff_by_player = {}

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        features = features_df.copy()
        if not self._xg_hist.empty:
            current = features[["player_id", "position_id", "club_id"]].drop_duplicates(subset=["player_id"])
            ratio = club_def_ratio(self._xg_hist, current)
            features["per90_xg"] = features["per90_xg"] * features["player_id"].map(ratio).fillna(1.0).to_numpy()

        p_target = target_start_probabilities(features, learned_start_probabilities(self._raw_history, features))

        if (
            p_target
            and self._last_kickoff_by_player
            and "kickoff_time" in features.columns
        ):
            target_times = pd.to_datetime(features["kickoff_time"], utc=True, errors="coerce")
            new_targets = dict(p_target)
            for idx, row in enumerate(features.itertuples(index=False)):
                pid = int(row.player_id)
                fix_id = int(row.fixture_id)
                key = (pid, fix_id)
                p = p_target.get(key)
                if p is None:
                    continue
                t_target = target_times.iloc[idx]
                t_last = self._last_kickoff_by_player.get(pid)
                if pd.notna(t_target) and t_last is not None:
                    diff_days = (t_target - t_last).total_seconds() / 86400.0
                    if 0.0 < diff_days < _CONGESTION_DAYS:
                        p_clamped = min(max(p, 0.01), 0.99)
                        logit = np.log(p_clamped / (1.0 - p_clamped)) + _LOGIT_SHIFT
                        p_adj = 1.0 / (1.0 + np.exp(-logit))
                        new_targets[key] = p_adj

            self._p_target = new_targets
        else:
            self._p_target = p_target

        return MultiFeatureAssistChallengerModel.predict(self, features, horizon)
