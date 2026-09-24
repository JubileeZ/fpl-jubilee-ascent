"""Hold-vs-chase challenger projection model.

Model Candidate from hold-vs-chase evidence (``docs/research/hold-vs-chase-2025-26``):
minutes persist (0.79) while points do not (autocorr 0.09); hauls drive seasons
(28% from top 3); clean sheets pay 3-to-1 on fixtures; a nailed core of ~82 is
measurable. Extends the Champion (``calibrated_matchup_hybrid``) with three
levers; defaults elsewhere untouched. Design locked in #107; gate verdict in #108.
"""

import pandas as pd

from models.calibrated_matchup_hybrid import CalibratedMatchupHybridModel
from models.metrics_component_hybrid import _number
from models.participation_state_hybrid import ParticipationStateHybridModel

_NAILED_APP = 0.90
_NAILED_AVG_MINS = 75.0
_NAILED_LIFT = 0.30
_FRINGE_APP = 0.50
_FRINGE_PUSH = 0.50
_XG_SHARP_FROM = 0.45
_XG_SHARP_SLOPE = 0.25
_XG_TRIM_BELOW = 0.10
_XG_TRIM_FACTOR = 0.95
_CEILING_TILT_FROM = 0.70
_MINS_TILT = 1.04
_HARD_DIFF = 4.0
_DEF_RELAX = 0.15


class HoldChaseChallengerModel(CalibratedMatchupHybridModel):
    """Champion plus start-persistence participation, top-end ordering, relaxed defense."""

    @property
    def name(self) -> str:
        return "hold_chase_challenger"

    @staticmethod
    def _state_probabilities(row: pd.Series) -> tuple[float, float, float]:
        p_dnp, p_start, p_sub_in = ParticipationStateHybridModel._state_probabilities(row)
        app = min(1.0, max(0.0, _number(row, "appearance_probability", 1.0 - p_dnp)))
        avg_mins = _number(row, "avg_mins_3gw", 0.0)
        if app >= _NAILED_APP and avg_mins >= _NAILED_AVG_MINS:
            p_start += _NAILED_LIFT * (1.0 - p_start)
            p_dnp *= 1.0 - _NAILED_LIFT
            p_sub_in *= 1.0 - _NAILED_LIFT
        elif app < _FRINGE_APP:
            p_dnp += _FRINGE_PUSH * (1.0 - app) * (1.0 - p_dnp)
            p_start *= 1.0 - _FRINGE_PUSH * (1.0 - app)
            p_sub_in *= 1.0 - _FRINGE_PUSH * (1.0 - app)
        total = p_dnp + p_start + p_sub_in
        return (p_dnp / total, p_start / total, p_sub_in / total) if total > 0 else (p_dnp, p_start, p_sub_in)

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        feat = features_df.copy()
        xg = pd.to_numeric(feat.get("per90_xg", 0.0), errors="coerce").fillna(0.0)
        xa = pd.to_numeric(feat.get("per90_xa", 0.0), errors="coerce").fillna(0.0)
        sharp = 1.0 + _XG_SHARP_SLOPE * ((xg - _XG_SHARP_FROM) / _XG_SHARP_FROM).clip(lower=0.0, upper=1.0)
        sharp = sharp.where(xg >= _XG_TRIM_BELOW, _XG_TRIM_FACTOR)
        feat["per90_xg"] = (xg * sharp).clip(lower=0.0)
        ceiling = (feat["per90_xg"] + xa) >= _CEILING_TILT_FROM
        for column in ("xmins_if_start", "xmins_if_sub_in"):
            if column in feat.columns:
                feat.loc[ceiling, column] = pd.to_numeric(feat.loc[ceiling, column], errors="coerce").fillna(0.0) * _MINS_TILT
        diff = pd.to_numeric(feat.get("difficulty", 3.0), errors="coerce").fillna(3.0)
        hard = diff >= _HARD_DIFF
        if "per90_goals_conceded" in feat.columns:
            gc = pd.to_numeric(feat["per90_goals_conceded"], errors="coerce").fillna(1.2)
            feat.loc[hard, "per90_goals_conceded"] = gc[hard] * (1.0 + _DEF_RELAX * (diff[hard] - 3.0) / 2.0)
        return super().predict(feat, horizon)
