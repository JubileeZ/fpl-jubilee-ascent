"""Bounded Causal ML Challenger Model.

Extends Adaptive Causal ML to activate at Gameweek 10 (instead of GW20) by enforcing
continuous empirical Bayes safety bounds [0.90, 1.10] on early-mid goal multipliers.
Eliminates talisman haul shrinkage and prevents early-mid catastrophic loss bounds (ADR 0062)
while capturing predictive alpha 10 gameweeks earlier than the prior Champion.
"""

from __future__ import annotations

import pandas as pd

from features.contracts import assert_projection_contract
from models.ml_component_challenger import MLComponentChallengerModel


class BoundedCausalChallengerModel(MLComponentChallengerModel):
    """Early-mid ML Candidate with bounded goal multipliers across GW10-19.

    - GW 1–9: Pure Champion (DefXgShrinkChallengerModel) fallback to protect early sample building.
    - GW 10–19: Stacked Causal ML Components (H1 Ridge p_start, H3 duration Ridge, LOO assist finishing)
      with goal multiplier safety clamp bounded to [0.90, 1.10] over Champion baseline.
    - GW 20+: Full unconstrained ML event activation ([0.75, 1.35] goal multipliers).
    """

    def __init__(
        self,
        *,
        min_ml_gw: int = 10,
        unconstrained_gw: int = 20,
        clamp_lower: float = 0.90,
        clamp_upper: float = 1.10,
        ramp_span: float = 4.0,
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
        self.unconstrained_gw = int(unconstrained_gw)
        self.clamp_lower = float(clamp_lower)
        self.clamp_upper = float(clamp_upper)

    @property
    def name(self) -> str:
        return "bounded_causal_challenger"

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

        ml_proj = super().predict(features_df, horizon)
        if target_gw >= self.unconstrained_gw:
            return ml_proj

        champ_proj = super(MLComponentChallengerModel, self).predict(features_df, horizon)
        out = ml_proj.copy()

        champ_goals = champ_proj["xp_goals"].clip(lower=1e-6)
        raw_ratio = out["xp_goals"] / champ_goals
        clamped_ratio = raw_ratio.clip(lower=self.clamp_lower, upper=self.clamp_upper)
        out["xp_goals"] = champ_goals * clamped_ratio

        comp_cols = [c for c in out.columns if c.startswith("xp_")]
        out["projected_points"] = out[comp_cols].sum(axis=1)

        assert_projection_contract(out)
        return out
