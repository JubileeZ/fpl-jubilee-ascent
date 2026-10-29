import pandas as pd
import pytest

from backtesting.data_admission import require_input
from backtesting.forecast_export import REQUIRED_COMPONENTS, strict_solver_table, validate_components
from models.base import resolve_asof_target_gw
from test_data_admission import authorize, catalog, rehash, request


def test_issue_cutoff_is_independent_of_first_fixture() -> None:
    features = pd.DataFrame({"gameweek_id": [3, 4]})
    features.attrs["issue_gameweek"] = 2
    assert resolve_asof_target_gw(features, pd.DataFrame({"gameweek_id": [1]})) == 2
    with pytest.raises(ValueError, match="History"):
        resolve_asof_target_gw(features, pd.DataFrame({"gameweek_id": [2]}))


def test_strict_table_requires_every_admitted_target() -> None:
    value = request()
    retained = catalog(value)
    capability = require_input(value, retained, "test", 1)
    rows = [
        {"player_id": item["player"], "gameweek_id": item["gw"], "fixture_id": item["fixture"] or -1,
         "projected_points": 2.0 if item["fixture"] else 0.0,
         "projected_minutes": 60.0 if item["fixture"] else 0.0}
        for item in value["origins"][0]["schedule"]
    ]
    frame = pd.DataFrame(rows)
    result = strict_solver_table(frame, capability, value, retained)
    assert result.loc[result.player_id == 2, "6_Pts"].iloc[0] == 0
    with pytest.raises(ValueError, match="coverage"):
        strict_solver_table(frame.iloc[:-1], capability, value, retained)
    frame.loc[frame.player_id == 2, "projected_points"] = 1
    with pytest.raises(ValueError, match="blank"):
        strict_solver_table(frame, capability, value, retained)


def test_validate_components_and_native_reconciliation() -> None:
    base_row = {col: 0.0 for col in REQUIRED_COMPONENTS}
    base_row["xp_minutes"] = 90.0
    base_row["xp_goals"] = 4.0
    base_row["fixture_id"] = 1
    base_row["projected_points"] = 94.0
    df = pd.DataFrame([base_row])

    # Valid row reconciles
    validate_components(df, "2024-25")

    # Sum mismatch fails
    bad_sum = df.copy()
    bad_sum["projected_points"] = 95.0
    with pytest.raises(ValueError, match="reconciliation"):
        validate_components(bad_sum, "2024-25")

    # Missing required component fails
    missing_col = df.drop(columns=["xp_bonus"])
    with pytest.raises(ValueError, match="missing"):
        validate_components(missing_col, "2024-25")

    # Nonfinite component fails
    non_finite = df.copy()
    non_finite["xp_goals"] = float("nan")
    with pytest.raises(ValueError, match="Nonfinite"):
        validate_components(non_finite, "2024-25")

    # Defensive contribution (xp_defcon != 0) unsupported in 2024-25
    defcon_row = df.copy()
    defcon_row["xp_defcon"] = 1.0
    defcon_row["projected_points"] = 95.0
    with pytest.raises(ValueError, match="Defensive contribution unsupported"):
        validate_components(defcon_row, "2024-25")
    # But supported in 2025-26
    validate_components(defcon_row, "2025-26")

    # Blank fixture must have all zero components
    blank_row = {col: 0.0 for col in REQUIRED_COMPONENTS}
    blank_row["fixture_id"] = -1
    blank_row["projected_points"] = 0.0
    validate_components(pd.DataFrame([blank_row]), "2024-25")

    blank_with_points = pd.DataFrame([{**blank_row, "xp_minutes": 10.0, "projected_points": 10.0}])
    with pytest.raises(ValueError, match="Blank components must be zero"):
        validate_components(blank_with_points, "2024-25")


def test_strict_table_dgw_aggregation() -> None:
    import copy
    value = request()
    origin = copy.deepcopy(value["origins"][0])
    origin["fixtures"].append({"id": 99, "gw": 1, "home_club": 1, "away_club": 3})
    origin["fixture_events"].append({
        "fixture": 99, "gw": 1, "status": "final", "home_club": 1, "away_club": 3,
        "changed_at": None, "finalized_at": "2025-01-02T12:00:00Z"
    })
    origin["outcomes"].append({"player": 1, "gw": 1, "fixture": 99, "status": "played", "points": 3})
    origin["schedule"].append({"player": 1, "gw": 1, "status": "fixture", "fixture": 99, "price": 50, "ownership": 20.0})
    value["origins"][0] = origin
    rehash(value)
    authorize(value)
    retained = catalog(value)
    capability = require_input(value, retained, "test", 1)

    rows = [
        {"player_id": item["player"], "gameweek_id": item["gw"], "fixture_id": item["fixture"] or -1,
         "projected_points": 3.0 if item["fixture"] == 99 else (2.0 if item["fixture"] else 0.0),
         "projected_minutes": 45.0 if item["fixture"] == 99 else (60.0 if item["fixture"] else 0.0)}
        for item in origin["schedule"]
    ]
    frame = pd.DataFrame(rows)
    result = strict_solver_table(frame, capability, value, retained)

    # For player 1, GW1 had two fixtures (one with 2.0 pts/60 mins, one with 3.0 pts/45 mins)
    # They should be aggregated to 5.0 pts and 105.0 mins
    p1 = result[result.player_id == 1].iloc[0]
    assert p1["1_Pts"] == 5.0
    assert p1["1_xMins"] == 105.0
