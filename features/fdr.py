"""Modified FDR: Official Fixture Difficulty with focal-venue overlay."""

from __future__ import annotations

import pandas as pd

DEFAULT_FDR = 3.0
MODIFIED_FDR_HOME_DELTA = -0.25
MODIFIED_FDR_AWAY_DELTA = 0.25


def official_fdr(value: object) -> float | None:
    number = pd.to_numeric(value, errors="coerce")
    if pd.isna(number):
        return None
    return float(number)


def modified_fdr(official: float | None, is_home: bool) -> float:
    if official is None:
        return DEFAULT_FDR
    delta = MODIFIED_FDR_HOME_DELTA if is_home else MODIFIED_FDR_AWAY_DELTA
    return official + delta
