from pathlib import Path

import pandas as pd

from solver.solver import prep_data
from solver.utils import load_solver_static
from solver.vendor import UPSTREAM_COMMIT, UPSTREAM_REPO


def test_load_solver_static_uses_injected_payloads() -> None:
    bootstrap = {"elements": [{"id": 1}]}
    fixtures = [{"event": 1, "team_h": 1, "team_a": 2}]
    got_bootstrap, got_fixtures = load_solver_static(
        {"fpl_bootstrap": bootstrap, "fpl_fixtures": fixtures}
    )
    assert got_bootstrap is bootstrap
    assert got_fixtures is fixtures


def test_vendor_pin_is_open_fpl_solver_main() -> None:
    src = Path("solver/solver.py").read_text(encoding="utf-8")
    assert "sasoptpy" not in src
    assert "highspy.Highs()" in src
    assert UPSTREAM_COMMIT in src
    assert UPSTREAM_REPO == "https://github.com/solioanalytics/open-fpl-solver"
    assert UPSTREAM_COMMIT == "2ff829fff2a4740e71e637f2c5823dbb2fb0a93d"


def _bootstrap() -> dict:
    return {
        "elements": [
            {"id": 1, "code": 101, "web_name": "A", "team": 1, "element_type": 3, "now_cost": 80},
            {"id": 2, "code": 202, "web_name": "B", "team": 1, "element_type": 3, "now_cost": 70},
        ],
        "teams": [{"id": 1, "name": "Arsenal", "short_name": "ARS"}],
        "events": [{"id": 1, "is_next": True, "finished": False}],
        "element_types": [
            {"id": 1, "singular_name_short": "GKP", "squad_min_play": 1, "squad_max_play": 1, "squad_select": 2},
            {"id": 2, "singular_name_short": "DEF", "squad_min_play": 3, "squad_max_play": 5, "squad_select": 5},
            {"id": 3, "singular_name_short": "MID", "squad_min_play": 2, "squad_max_play": 5, "squad_select": 5},
            {"id": 4, "singular_name_short": "FWD", "squad_min_play": 1, "squad_max_play": 3, "squad_select": 3},
        ],
    }


def test_prep_data_injects_missing_squad_player_and_preseason_itb(tmp_path: Path) -> None:
    csv_path = tmp_path / "dual_vector_state_hybrid.csv"
    pd.DataFrame([{
        "ID": 1, "code": 101, "Name": "A", "Pos": "M", "Price": 8.0, "Team": "ARS",
        "1_Pts": 5.0, "1_xMins": 90.0,
    }]).to_csv(csv_path, index=False)
    my_data = {
        "picks": [
            {"element": 1, "selling_price": 80, "purchase_price": 80, "element_type": 3},
            {"element": 2, "selling_price": 70, "purchase_price": 70, "element_type": 3},
        ],
        "chips": [],
        "transfers": {"bank": 1000, "limit": None, "made": 0, "cost": 4},
    }
    options = {
        "fpl_bootstrap": _bootstrap(),
        "fpl_fixtures": [{"event": 1, "team_h": 1, "team_a": 1}],
        "projections_path": str(csv_path),
        "horizon": 1,
        "override_next_gw": 1,
        "preseason": True,
        "xmin_lb": 0,
        "keep_top_ev_percent": 100,
        "chip_limits": {"wc": 0, "bb": 0, "fh": 0, "tc": 0},
        "pick_prices": {},
    }
    data = prep_data(my_data, options)
    assert 2 in data["merged_data"].index
    assert data["merged_data"].loc[2, "total_ev"] == 0
    assert data["itb"] == 100
    assert data["initial_squad"] == [1, 2]
