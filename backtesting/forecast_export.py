"""Strict solver-table preparation for an admitted synthetic issue."""

import math
from typing import Any

import pandas as pd

from backtesting.data_admission import AdmittedInput, verify_input

REQUIRED_COMPONENTS = ("xp_minutes", "xp_goals", "xp_assists", "xp_clean_sheet", "xp_conceded", "xp_defcon", "xp_saves", "xp_yellow_cards", "xp_red_cards", "xp_penalties_saved", "xp_penalties_missed", "xp_own_goals", "xp_bonus")


def validate_components(predictions: pd.DataFrame, rules_version: str) -> None:
    """Require every declared component and reconcile each fixture total."""
    if not set(REQUIRED_COMPONENTS).issubset(predictions.columns):
        raise ValueError("Required forecast components missing")
    for row in predictions.to_dict(orient="records"):
        values: list[float] = []
        for component in REQUIRED_COMPONENTS:
            value = row[component]
            if type(value) not in (int, float) or not math.isfinite(value):
                raise ValueError("Nonfinite forecast component")
            values.append(float(value))
        if not math.isclose(sum(values), float(row["projected_points"]), rel_tol=1e-9, abs_tol=1e-9):
            raise ValueError("Forecast component reconciliation failed")
        if rules_version in ("2023-24", "2024-25") and row["xp_defcon"] != 0:
            raise ValueError("Defensive contribution unsupported by native rules")
        if row["fixture_id"] == -1 and any(value != 0 for value in values):
            raise ValueError("Blank components must be zero")


def strict_solver_table(
    predictions: pd.DataFrame,
    capability: AdmittedInput,
    request: dict[str, Any],
    catalog: dict[str, bytes],
) -> pd.DataFrame:
    """Validate every admitted fixture and blank before aggregating for the solver.

    A blank is represented by fixture_id -1 and must carry zero points/minutes.
    This function does not establish forecast provenance or promotion eligibility.
    """
    verify_input(capability, request, catalog)
    origins = [o for o in request["origins"] if o["season"] == capability.season and o["gw"] == capability.gw]
    if len(origins) != 1:
        raise ValueError("Ambiguous issue")
    origin = origins[0]
    targets = list(range(capability.gw, min(capability.gw + 5, 38) + 1))
    if origin["target_gws"] != targets:
        raise ValueError("Incomplete issue horizon")
    expected = {(int(row["player"]), int(row["gw"]), -1 if row["status"] == "blank" else int(row["fixture"])) for row in origin["schedule"]}
    columns = ["player_id", "gameweek_id", "fixture_id", "projected_points", "projected_minutes"]
    if not set(columns).issubset(predictions.columns):
        raise ValueError("Forecast columns missing")
    frame: Any = predictions[columns].copy()
    for col in columns:
        frame[col] = pd.to_numeric(frame[col], errors="raise")
        if not frame[col].map(math.isfinite).all():
            raise ValueError(f"Nonfinite {col}")
    for col in columns[:3]:
        if not (frame[col] == frame[col].astype(int)).all():
            raise ValueError(f"Nonintegral {col}")
        frame[col] = frame[col].astype(int)
    if frame.duplicated(columns[:3]).any() or set(map(tuple, frame[columns[:3]].itertuples(index=False, name=None))) != expected:
        raise ValueError("Forecast population or fixture coverage mismatch")
    if ((frame.projected_minutes < 0) | (frame.projected_minutes > 90)).any():
        raise ValueError("Fixture minutes outside bounds")
    blank = frame.fixture_id == -1
    if ((frame.loc[blank, "projected_points"] != 0) | (frame.loc[blank, "projected_minutes"] != 0)).any():
        raise ValueError("Known blank must be zero")
    grouped: Any = frame.groupby(["player_id", "gameweek_id"], as_index=False)[columns[3:]].sum()
    metadata: Any = pd.DataFrame(origin["players"])
    metadata = metadata[["id", "club", "position", "price"]].rename(columns={"id": "player_id"})
    points = grouped.pivot(index="player_id", columns="gameweek_id", values="projected_points")
    points.columns = [f"{gw}_Pts" for gw in points.columns]
    minutes = grouped.pivot(index="player_id", columns="gameweek_id", values="projected_minutes")
    minutes.columns = [f"{gw}_xMins" for gw in minutes.columns]
    return metadata.merge(points.join(minutes).reset_index(), on="player_id", validate="one_to_one")
