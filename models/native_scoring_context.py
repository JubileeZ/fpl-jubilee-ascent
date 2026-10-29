"""Resolve an optional, uniformly specified Feature Contract scoring context."""

import pandas as pd

from backtesting.season_rules import get_rules


def native_scoring_context(features: pd.DataFrame) -> str | None:
    if "native_rules_version" not in features.columns:
        return None
    values = features["native_rules_version"].tolist()
    if not values or any(not isinstance(value, str) for value in values) or len(set(values)) != 1:
        raise ValueError("Native scoring context must be complete and uniform")
    value = values[0]
    if not isinstance(value, str):
        raise ValueError("Native scoring version must be a string")
    get_rules(value)
    return value


def native_scoring_row(row: pd.Series) -> str | None:
    if "native_rules_version" not in row:
        return None
    value = row["native_rules_version"]
    if not isinstance(value, str):
        raise ValueError("Native scoring version must be present")
    get_rules(value)
    return value
