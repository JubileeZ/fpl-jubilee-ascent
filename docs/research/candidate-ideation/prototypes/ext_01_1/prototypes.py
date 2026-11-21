"""EXT-01_1: shrink on-pitch xGC minus goals conceded toward zero."""

from __future__ import annotations

import numpy as np
import pandas as pd

from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel

_APPEARANCE_KEY = ("player_id", "fixture_id")
_FIXTURE_FIELDS = (*_APPEARANCE_KEY, "gameweek_id", "opponent_club_id")
_MEASUREMENTS = ("minutes", "expected_goals_conceded", "goals_conceded")
_HISTORY_COLUMNS = (*_FIXTURE_FIELDS, *_MEASUREMENTS)
_PLAYER_CLUB = ("player_id", "club_id")
_DECAY = 0.95
_PSEUDO_MINUTES = 360.0
_RATE_FLOOR = 0.05


class ShotQualityInTheConcededGoalRateChallengerModel(DefXgShrinkChallengerModel):
    """Update the incoming concession rate before inherited fixture treatment."""

    variant_name: str = "ext_01_1_a05"
    a: float = 0.5

    def __init__(self) -> None:
        super().__init__()
        self._concession_delta: pd.Series = pd.Series(dtype=float)

    @property
    def name(self) -> str:
        return self.variant_name

    def fit(self, history_df: pd.DataFrame) -> None:
        super().fit(history_df)
        self._concession_delta = pd.Series(dtype=float)
        if history_df.empty or not set(_HISTORY_COLUMNS).issubset(history_df.columns):
            return

        history = history_df[list(_HISTORY_COLUMNS)].apply(pd.to_numeric, errors="coerce")
        history = history.replace([np.inf, -np.inf], np.nan)
        valid_keys = history[list(_FIXTURE_FIELDS)].fillna(0).gt(0).all(axis=1)
        history = history.loc[valid_keys].drop_duplicates().reset_index(drop=True)

        # Resolve both sides before filtering exposure or shot-quality measurements.
        # A fixture with conflicting side or gameweek assignments has no usable pairing.
        appearances = history.groupby(list(_APPEARANCE_KEY))["opponent_club_id"]
        conflicting_sides = appearances.transform("nunique").gt(1)
        conflicting_fixtures = history.loc[conflicting_sides, "fixture_id"]
        fixtures = history.groupby("fixture_id")
        sides = fixtures["opponent_club_id"]
        complete = sides.transform("nunique").eq(2) & fixtures["gameweek_id"].transform("nunique").eq(1)
        lower_club = sides.transform("min")
        own_club = sides.transform("max").where(history["opponent_club_id"].eq(lower_club), lower_club)
        history = history.loc[complete & ~history["fixture_id"].isin(conflicting_fixtures)].assign(club_id=own_club)

        history = history.drop_duplicates(subset=list(_APPEARANCE_KEY), keep=False).dropna(subset=list(_MEASUREMENTS))
        history = history.loc[history["minutes"].gt(0)]
        latest_gw = history.groupby(list(_PLAYER_CLUB))["gameweek_id"].transform("max")
        weights = _DECAY ** (latest_gw - history["gameweek_id"])
        groups = [history[column] for column in _PLAYER_CLUB]
        residual = history["expected_goals_conceded"] - history["goals_conceded"]
        weighted_residual = (residual * weights).groupby(groups).sum()
        weighted_minutes = (history["minutes"] * weights).groupby(groups).sum()
        self._concession_delta = 90.0 * weighted_residual / (_PSEUDO_MINUTES + weighted_minutes)

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        if features_df.empty:
            return super().predict(features_df, horizon)

        player_club_keys = pd.MultiIndex.from_frame(features_df[list(_PLAYER_CLUB)])
        delta = self._concession_delta.reindex(player_club_keys).fillna(0.0).to_numpy()
        eligible = features_df["position_id"].isin((1, 2))
        features = features_df.copy()
        incoming = pd.to_numeric(features["per90_goals_conceded"], errors="coerce").astype(float)
        adjusted = (incoming + self.a * delta).clip(lower=_RATE_FLOOR)
        features["per90_goals_conceded"] = incoming.where(~eligible, adjusted)
        return super().predict(features, horizon)


_GRID = (("ext_01_1_a05", 0.5), ("ext_01_1_a10", 1.0))
PROTOTYPES = {
    name: type(name, (ShotQualityInTheConcededGoalRateChallengerModel,), {"variant_name": name, "a": a})
    for name, a in _GRID
}
_MANIFEST = (
    *(f"history.{column}" for column in _HISTORY_COLUMNS),
    "features.player_id",
    "features.club_id",
    "features.position_id",
    "features.per90_goals_conceded",
)
FEATURES = {name: _MANIFEST for name in PROTOTYPES}
COMPONENTS = {name: "xp_clean_sheet" for name in PROTOTYPES}
