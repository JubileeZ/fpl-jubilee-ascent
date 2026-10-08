from pathlib import Path
from typing import Any

import pandas as pd

from commands.solve import build_my_data_from_parent_state
from dashboard.planner import Planner
from dashboard.planner_service import PlannerPaths, solver_options
from solver.solver import prep_data, solve_multi_period_fpl
from test_streamlit_planner import dataset


def test_real_milp_preserves_manual_transfer_bench_and_captain(tmp_path: Path) -> None:
    data = dataset()
    planner = Planner(data)
    planner.change_horizon(6, 6)
    planner.buy(6, 7, 16)
    planner.override(6, "bench", 15)
    planner.override(6, "captain", 14)
    planner.override(6, "vice", 13)
    processed = tmp_path / "processed"
    processed.mkdir()
    players = [{"id": row["id"], "position_id": row["pos_id"], "now_cost": 50} for row in data["players"]]
    pd.DataFrame(players).to_parquet(processed / "players.parquet")
    paths = PlannerPaths(tmp_path / "dataset.json", processed, tmp_path / "storage")
    options = solver_options(planner, paths)
    projection_path = tmp_path / "projections.csv"
    pd.DataFrame([{"ID": row["id"], "Name": row["name"], "Pos": row["pos"],
                   "Price": row["price"], "Team": f"Club{row['team_id']}",
                   "6_Pts": row["projections"]["gw6"]["total_xp"], "6_xMins": 90}
                  for row in data["players"]]).to_csv(projection_path, index=False)
    bootstrap: dict[str, Any] = {
        "elements": [{"id": row["id"], "web_name": row["name"], "team": row["team_id"],
                      "element_type": row["pos_id"], "now_cost": 50} for row in data["players"]],
        "teams": [{"id": club, "name": f"Club{club}", "short_name": f"C{club}"} for club in range(5)],
        "events": [{"id": 6, "is_next": True, "finished": False}],
        "element_types": [{"id": pos, "singular_name_short": label, "squad_min_play": low,
                           "squad_max_play": high, "squad_select": count}
                          for pos, label, low, high, count in [(1, "GKP", 1, 1, 2), (2, "DEF", 3, 5, 5),
                                                               (3, "MID", 2, 5, 5), (4, "FWD", 1, 3, 3)]],
    }
    options.update(fpl_bootstrap=bootstrap, fpl_fixtures=[], projections_path=str(projection_path),
                   override_next_gw=6, xmin_lb=0, keep_top_ev_percent=100, secs=5, verbose=False)
    my_data = build_my_data_from_parent_state(options["parent_state"], processed)
    prepared = prep_data(my_data, options)
    solution = solve_multi_period_fpl(prepared, options)[0]
    picks = solution["picks"]
    assert picks.loc[picks["captain"] == 1, "id"].tolist() == [14]
    assert picks.loc[picks["vicecaptain"] == 1, "id"].tolist() == [13]
    assert 15 not in picks.loc[picks["lineup"] == 1, "id"].tolist()
    assert picks.loc[picks["transfer_in"] == 1, "id"].tolist() == [16]


def test_parent_state_preserves_zero_free_transfers(tmp_path: Path) -> None:
    pd.DataFrame([{"id": pid, "position_id": 3, "now_cost": 50} for pid in range(1, 16)]).to_parquet(tmp_path / "players.parquet")
    state = {"lineup": {"slots": {str(pid): pid for pid in range(1, 16)}},
             "evaluation": {"freeTransfersNext": 0, "bankRemaining": 0}}
    result = build_my_data_from_parent_state(state, tmp_path)
    assert result["transfers"]["limit"] == 0
