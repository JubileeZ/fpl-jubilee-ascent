import pandas as pd
import pytest

from backtesting.data_admission import require_input
from backtesting.forecast_export import strict_solver_table
from models.base import resolve_asof_target_gw
from test_data_admission import catalog, request


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
