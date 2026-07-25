"""Projection model contracts and shared feature-row iteration."""

import abc
from collections.abc import Iterator

import pandas as pd


def iter_feature_rows(
    features_df: pd.DataFrame,
    horizon: int,
) -> Iterator[tuple[pd.Series, int, int | None]]:
    """Yield feature rows without cloning long-format fixture rows.

    New Feature Contracts carry one row per player/fixture. Legacy callers that
    provide no ``fixture_id`` retain the original horizon expansion behavior.
    """
    if horizon < 1:
        raise ValueError("horizon must be at least 1")

    if "fixture_id" in features_df.columns:
        for _, row in features_df.iterrows():
            yield row, int(row["gameweek_id"]), int(row["fixture_id"])
        return

    for offset in range(horizon):
        for _, row in features_df.iterrows():
            yield row, int(row.get("gameweek_id", 1)) + offset, None


class BaseModel(abc.ABC):
    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Unique identifier name for the model."""
        pass
        
    @abc.abstractmethod
    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        """
        Generate predictions for the planning horizon.
        
        Args:
            features_df: pd.DataFrame conforming to the FeatureContract.
            horizon: The planning horizon (number of gameweeks).
            
        Returns:
            pd.DataFrame matching the ProjectionContract:
                - player_id (int)
                - fixture_id (int, optional for legacy callers)
                - gameweek_id (int)
                - projected_points (float)
                - projected_minutes (float)
        """
        pass
