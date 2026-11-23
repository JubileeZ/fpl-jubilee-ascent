"""Fixed additions to the prior-trained EXT-40 event-count designs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

from backtesting.forecast_export import REQUIRED_COMPONENTS
from prototypes.ext_40.prototypes import FEATURES as STATIC_FEATURES
from prototypes.ext_40.prototypes import KEYS, Component, FloatArray

Arm = Literal["a", "b", "c"]
PENALTY = 0.03
ARMS: tuple[Arm, ...] = ("a", "b", "c")
FEATURES = (*STATIC_FEATURES, *(f"features.{name}" for name in REQUIRED_COMPONENTS))


def arm_features(arm: Arm, component: Component) -> tuple[str, ...]:
    return {"a": (), "b": (f"xp_{component}",), "c": REQUIRED_COMPONENTS}[arm]


def attach_champion_components(
    rows: pd.DataFrame, issued: pd.DataFrame, *, exact: bool
) -> pd.DataFrame:
    """Join immutable issue-time vectors without changing the matched cohort."""
    if set(REQUIRED_COMPONENTS).intersection(rows):
        raise ValueError("Candidate rows cannot supply Champion components")
    vectors = issued[[*KEYS, *REQUIRED_COMPONENTS]]
    if exact and len(vectors) != len(rows):
        raise ValueError("Champion and predictor fixture populations differ")
    joined = rows.merge(vectors, on=KEYS, how="left", validate="one_to_one")
    if not np.isfinite(joined[list(REQUIRED_COMPONENTS)].to_numpy(dtype=float)).all():
        raise ValueError("Missing or nonfinite original Champion component vector")
    return joined


def _signed_log(rows: pd.DataFrame) -> FloatArray:
    values = rows[list(REQUIRED_COMPONENTS)].to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("Champion features require finite issued components")
    return np.sign(values) * np.log1p(np.abs(values))


@dataclass(frozen=True)
class ChampionFeatureScale:
    """Source-only center and scale, frozen for destination updates."""

    mean: FloatArray
    scale: FloatArray

    @classmethod
    def fit(cls, source: pd.DataFrame) -> ChampionFeatureScale:
        values = _signed_log(source)
        constant = np.ptp(values, axis=0) == 0
        mean = np.where(constant, values[0], values.mean(axis=0))
        scale = np.where(constant, 1.0, values.std(axis=0))
        return cls(mean, scale)

    def transform(self, rows: pd.DataFrame) -> pd.DataFrame:
        features = (_signed_log(rows) - self.mean) / self.scale
        return rows.assign(**dict(zip(REQUIRED_COMPONENTS, features.T, strict=True)))
