"""Prototypes for explore-candidate: Apex Predator Challenger.

Combines zero-leakage causal panel ML components (Ridge p_start, duration offset,
shrunk xG residual goals, LOO assist finishing) with calibrated warm-up ramp
and schedule congestion turnaround penalty.
"""

from __future__ import annotations

import pandas as pd

from models.ml_component_challenger import MLComponentChallengerModel


class ApexPredatorGW15(MLComponentChallengerModel):
    """Apex Predator: 100% Champion stability in early season (GW1-14); ML activates at GW15+."""

    def __init__(self) -> None:
        super().__init__(ramp_span=5.0, enable_congestion=True)

    @property
    def name(self) -> str:
        return "apex_predator_gw15"

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        target_gw = features_df["gameweek_id"].iloc[0] if "gameweek_id" in features_df.columns else 1
        if target_gw < 15:
            return super(MLComponentChallengerModel, self).predict(features_df, horizon)
        return super().predict(features_df, horizon)


class ApexPredatorGW12(MLComponentChallengerModel):
    """Apex Predator: 100% Champion stability in GW1-11; ML activates at GW12+."""

    def __init__(self) -> None:
        super().__init__(ramp_span=6.0, enable_congestion=True)

    @property
    def name(self) -> str:
        return "apex_predator_gw12"

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        target_gw = features_df["gameweek_id"].iloc[0] if "gameweek_id" in features_df.columns else 1
        if target_gw < 12:
            return super(MLComponentChallengerModel, self).predict(features_df, horizon)
        return super().predict(features_df, horizon)


class ApexPredatorGW10(MLComponentChallengerModel):
    """Apex Predator: 100% Champion stability in GW1-9; ML activates at GW10+."""

    def __init__(self) -> None:
        super().__init__(ramp_span=8.0, enable_congestion=True)

    @property
    def name(self) -> str:
        return "apex_predator_gw10"

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        target_gw = features_df["gameweek_id"].iloc[0] if "gameweek_id" in features_df.columns else 1
        if target_gw < 10:
            return super(MLComponentChallengerModel, self).predict(features_df, horizon)
        return super().predict(features_df, horizon)


PROTOTYPES = {
    "apex_predator_gw15": ApexPredatorGW15,
    "apex_predator_gw12": ApexPredatorGW12,
    "apex_predator_gw10": ApexPredatorGW10,
}

_COMMON_FEATURES = (
    "features.external_xmins",
    "features.kickoff_time",
    "features.price",
    "features.position_id",
    "features.club_id",
    "features.per90_xg",
    "features.per90_xa",
    "features.per90_goals_conceded",
    "features.transfers_in",
    "features.transfers_out",
    "features.p_start",
    "features.p_sub_in",
    "features.p_dnp",
    "features.xmins_if_start",
    "features.xmins_if_sub_in",
    "features.p_60_if_start",
    "features.p_60_if_sub_in",
    "history.kickoff_time",
    "history.minutes",
    "history.starts",
    "history.expected_goals",
    "history.expected_assists",
    "history.expected_goals_conceded",
    "history.goals_scored",
    "history.assists",
    "history.goals_conceded",
    "history.clean_sheets",
    "history.saves",
    "history.defensive_contribution",
    "history.bps",
    "history.influence",
    "history.creativity",
    "history.threat",
    "history.transfers_in",
    "history.transfers_out",
    "history.price",
    "history.was_home",
    "history.team_h_score",
    "history.team_a_score",
    "history.opponent_club_id",
    "history.yellow_cards",
    "history.red_cards",
    "local.ramp_span",
    "local.enable_congestion",
)

FEATURES = {
    "apex_predator_gw15": _COMMON_FEATURES,
    "apex_predator_gw12": _COMMON_FEATURES,
    "apex_predator_gw10": _COMMON_FEATURES,
}
