"""Adaptive Causal ML Challenger Model.

Combines zero-leakage Causal Panel ML components (Tier 1 Ridge p_start + start duration,
Tier 2 shrunk xG residual goals + calibrated LOO assist finishing) with 100% Champion
stability across the first half of the season (GW 1-19).

Activates ML exclusively in the Late Season (GW 20+) once all clubs have completed
a full round-robin schedule (>19 matches per club), eliminating unseeded early-sample
estimation variance while capturing significant late-season predictive alpha.
"""

from __future__ import annotations

import pandas as pd

from models.ml_component_challenger import MLComponentChallengerModel


class AdaptiveCausalChallengerModel(MLComponentChallengerModel):
    """Composite ML Champion Candidate with late-season sample-sufficient activation.

    - GW 1–19: Pure Champion (DefXgShrinkChallengerModel) fallback to protect sample building
      and guarantee non-catastrophic loss bounds on cold-start and early-mid segments.
    - GW 20+: Stacked Causal ML Components (H1 p_start Ridge, H3 duration Ridge, Group A Goals residual,
      Group B LOO Assists) with smooth Bayesian ramp over 5 GWs.
    - Schedule Congestion: Strictly disabled (dead lever excluded per Ledger Law).
    """

    def __init__(
        self,
        *,
        min_ml_gw: int = 20,
        ramp_span: float = 5.0,
        enable_mins_h1: bool = True,
        enable_mins_h2: bool = False,
        enable_mins_h3: bool = True,
        enable_goals: bool = True,
        enable_assists: bool = True,
        enable_defense: bool = False,
        enable_bonus: bool = False,
    ) -> None:
        super().__init__(
            enable_mins_h1=enable_mins_h1,
            enable_mins_h2=enable_mins_h2,
            enable_mins_h3=enable_mins_h3,
            enable_goals=enable_goals,
            enable_assists=enable_assists,
            enable_defense=enable_defense,
            enable_bonus=enable_bonus,
            ramp_span=ramp_span,
            enable_congestion=False,
        )
        self.min_ml_gw = int(min_ml_gw)

    @property
    def name(self) -> str:
        return "adaptive_causal_challenger"

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        if features_df.empty:
            return super().predict(features_df, horizon)
        target_gw = (
            int(pd.to_numeric(features_df["gameweek_id"]).iloc[0])
            if "gameweek_id" in features_df.columns
            else 1
        )
        if target_gw < self.min_ml_gw:
            return super(MLComponentChallengerModel, self).predict(features_df, horizon)
        return super().predict(features_df, horizon)
