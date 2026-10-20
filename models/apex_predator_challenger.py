"""Apex Predator Challenger Model (Composite ML + Scheduling Champion Candidate).

Stacks zero-leakage Causal Panel ML components (Tier 1 Ridge p_start + start duration,
Tier 2 shrunk xG residual goals + calibrated LOO assist finishing) with Champion
stability across early-season sample building (GW1-9) and schedule congestion rest penalty
(-0.20 logit on p_start for fixtures with <3.5 rest days).
"""

from __future__ import annotations

import pandas as pd

from models.ml_component_challenger import MLComponentChallengerModel


class ApexPredatorChallengerModel(MLComponentChallengerModel):
    """Composite ML Champion Candidate with calibrated warm-up and schedule congestion.

    - GW 1–9: Pure Champion (DefXgShrinkChallengerModel) fallback to protect sample building.
    - GW 10+: Stacked ML Components (H1 p_start Ridge, H3 duration Ridge, Group A Goals residual,
      Group B LOO Assists) with smooth Bayesian ramp.
    - Schedule Congestion: -0.20 logit penalty on p_start for short turnarounds (<3.5 days rest).
    """

    def __init__(
        self,
        *,
        min_ml_gw: int = 10,
        ramp_span: float = 8.0,
        enable_congestion: bool = True,
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
            enable_congestion=enable_congestion,
        )
        self.min_ml_gw = min_ml_gw

    @property
    def name(self) -> str:
        return "apex_predator_challenger"

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        if features_df.empty:
            return super().predict(features_df, horizon)
        target_gw = features_df["gameweek_id"].iloc[0] if "gameweek_id" in features_df.columns else 1
        if target_gw < self.min_ml_gw:
            return super(MLComponentChallengerModel, self).predict(features_df, horizon)
        return super().predict(features_df, horizon)
