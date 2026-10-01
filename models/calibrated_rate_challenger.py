"""Calibrated-rate Model Candidate (explore-candidate 2026-10-01).

Subclass of ``def_xg_shrink_challenger`` addressing rate over-inflation and budget under-projection:
1. Unsharp xG: eliminates the heuristic +25% top-end xG sharp slope from ``hold_chase_challenger``
   (sharp_slope = 0.0), removing artificial over-projection on elite assets.
2. Untrim low-xG: eliminates the 5% down-trim on low-xG players (trim_factor = 1.0),
   protecting budget players from systematic deflation.
3. Untilt minutes: clamps starting minutes strictly to regulation 90.0 minutes (mins_tilt = 1.0),
   eliminating the unphysical 93.6-minute projection.
Lineage: def_xg_shrink_challenger -> learned_start_challenger -> multi_feature_assist_challenger
-> face_value_challenger -> hold_chase_challenger -> calibrated_matchup_hybrid.
"""

from __future__ import annotations

import pandas as pd

from models.base import resolve_asof_target_gw
from models.calibrated_matchup_hybrid import CalibratedMatchupHybridModel
from models.def_xg_shrink_challenger import (
    _POSITION_K,
    _RATIO_CLIP,
    DefXgShrinkChallengerModel,
    shrunk_xg_rates,
)
from models.learned_start_challenger import learned_start_probabilities, target_start_probabilities

_XG_SHARP_FROM = 0.45
_XG_TRIM_BELOW = 0.10
_CEILING_TILT_FROM = 0.70


class CalibratedRateChallengerModel(DefXgShrinkChallengerModel):
    """Champion plus unsharp xG (slope 0), low-xG restoration (trim 1.0), and 90-min clamp."""

    xg_sharp_slope: float = 0.0
    trim_factor: float = 1.0
    mins_tilt: float = 1.0

    @property
    def name(self) -> str:
        return "calibrated_rate_challenger"

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        if not self._xg_hist.empty:
            positions = features_df.drop_duplicates("player_id").set_index("player_id")["position_id"]
            new = shrunk_xg_rates(self._xg_hist, positions, _POSITION_K)
            old = shrunk_xg_rates(self._xg_hist, positions, {})
            ratio = (new / old.where(old > 1e-9)).fillna(1.0).clip(*_RATIO_CLIP)
            features = features_df.copy()
            features["per90_xg"] = features["per90_xg"] * features["player_id"].map(ratio).fillna(1.0).to_numpy()
        else:
            features = features_df.copy()

        target_gw = resolve_asof_target_gw(features, self._raw_history)
        self._p_target = target_start_probabilities(
            features,
            learned_start_probabilities(self._raw_history, features),
            target_gw=target_gw,
        )

        self._assist_rates = self._fit_assist_rates(features)

        feat = features.copy()
        xg = pd.to_numeric(feat.get("per90_xg", 0.0), errors="coerce").fillna(0.0)
        xa = pd.to_numeric(feat.get("per90_xa", 0.0), errors="coerce").fillna(0.0)
        sharp = 1.0 + self.xg_sharp_slope * ((xg - _XG_SHARP_FROM) / _XG_SHARP_FROM).clip(lower=0.0, upper=1.0)
        sharp = sharp.where(xg >= _XG_TRIM_BELOW, self.trim_factor)
        feat["per90_xg"] = (xg * sharp).clip(lower=0.0)
        ceiling = (feat["per90_xg"] + xa) >= _CEILING_TILT_FROM
        for column in ("xmins_if_start", "xmins_if_sub_in"):
            if column in feat.columns:
                feat.loc[ceiling, column] = (
                    pd.to_numeric(feat.loc[ceiling, column], errors="coerce").fillna(0.0) * self.mins_tilt
                ).clip(upper=90.0)
        feat = self._apply_hard_fixture_defence(feat)
        return CalibratedMatchupHybridModel.predict(self, feat, horizon)
