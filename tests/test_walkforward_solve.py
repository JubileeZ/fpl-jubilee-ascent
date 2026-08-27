from pathlib import Path

import pandas as pd
import pytest

from backtesting.archive_static import apply_deadline_prices, bootstrap_from_processed
from backtesting.strategy_policy import (
    FIRST_HALF_OAT_ARMS,
    Tilt,
    WalkforwardArm,
)
from backtesting.transfer_plan_walkforward import DeadlineWeekPlan
from backtesting.walkforward_solve import (
    clipped_horizon,
    deadline_my_data,
    make_solve_week,
    outcomes_from_performances,
    plan_from_picks,
    prices_at_deadline,
    run_first_half_ranking,
    tilt_projected_points,
    walkforward_solver_options,
)
from solver.data_parser import read_data


def test_clipped_horizon_is_five_until_gw19() -> None:
    assert clipped_horizon(1) == 5
    assert clipped_horizon(15) == 5
    assert clipped_horizon(17) == 3
    assert clipped_horizon(19) == 1


def test_prices_at_deadline_use_performance_price_not_terminal_now_cost(tmp_path: Path) -> None:
    processed = tmp_path / "processed"
    processed.mkdir()
    pd.DataFrame([{
        "id": 9, "code": 99, "first_name": "A", "second_name": "B", "web_name": "AB",
        "club_id": 2, "position_id": 3, "now_cost": 80,
    }]).to_parquet(processed / "players.parquet", index=False)
    pd.DataFrame([{"id": 2, "name": "Arsenal", "short_name": "ARS"}]).to_parquet(
        processed / "clubs.parquet", index=False
    )
    pd.DataFrame([
        {"player_id": 9, "gameweek_id": 1, "price": 50, "minutes": 90, "total_points": 2},
        {"player_id": 9, "gameweek_id": 2, "price": 51, "minutes": 90, "total_points": 3},
    ]).to_parquet(processed / "player_performances.parquet", index=False)
    prices = prices_at_deadline(pd.read_parquet(processed / "player_performances.parquet"), 1)
    assert prices[9] == 50
    bootstrap = apply_deadline_prices(bootstrap_from_processed(processed), prices)
    assert bootstrap["elements"][0]["now_cost"] == 50


def test_walkforward_options_forbid_chips_and_hits_and_clip_horizon() -> None:
    arm = FIRST_HALF_OAT_ARMS[0]
    gw1 = walkforward_solver_options(arm, deadline_gw=1, locked_ids=())
    assert gw1["weekly_hit_limit"] == 0
    assert gw1["hit_limit"] == 0
    assert gw1["chip_limits"] == {"wc": 1, "bb": 0, "fh": 0, "tc": 0}
    assert gw1["use_wc"] == [1]
    assert gw1["use_bb"] == []
    assert gw1["use_fh"] == []
    assert gw1["use_tc"] == []
    assert gw1["preseason"] is True
    assert gw1["horizon"] == 5
    assert gw1["override_next_gw"] == 1
    late = walkforward_solver_options(arm, deadline_gw=17, locked_ids=(3, 4))
    assert late["preseason"] is False
    assert late["horizon"] == 3
    assert late["locked"] == [3, 4]
    assert late["chip_limits"]["wc"] == 0
    assert late["use_wc"] == []


def test_gw1_my_data_is_empty_hundred_million_draft() -> None:
    my_data = deadline_my_data(1, (), {}, 0)
    assert my_data["picks"] == []
    assert my_data["chips"] == []
    assert my_data["transfers"]["bank"] == 1000
    assert my_data["transfers"]["limit"] is None


def test_later_gw_my_data_uses_owned_squad_and_ft_bank() -> None:
    my_data = deadline_my_data(
        4,
        (1, 2),
        {1: {"position_id": 1, "price": 45}, 2: {"position_id": 2, "price": 50}},
        ft_bank=3,
    )
    assert [row["element"] for row in my_data["picks"]] == [1, 2]
    assert my_data["picks"][0]["selling_price"] == 45
    assert my_data["transfers"]["limit"] == 3
    assert my_data["transfers"]["bank"] == 1000


def test_defcon_floor_tilts_def_and_mid_only() -> None:
    pred = pd.DataFrame([
        {"player_id": 1, "position_id": 2, "projected_points": 4.0, "xp_defcon": 1.0, "gameweek_id": 1},
        {"player_id": 2, "position_id": 4, "projected_points": 6.0, "xp_defcon": 2.0, "gameweek_id": 1},
    ])
    tilted = tilt_projected_points(pred, Tilt.DEFCON_FLOOR)
    assert tilted.loc[0, "projected_points"] == pytest.approx(5.0)
    assert tilted.loc[1, "projected_points"] == pytest.approx(6.0)
    ceiling = tilt_projected_points(pred, Tilt.ATTACK_CEILING)
    assert ceiling.loc[0, "projected_points"] == pytest.approx(3.0)


def test_plan_from_picks_reads_deadline_week_only() -> None:
    picks = pd.DataFrame([
        {"id": 1, "week": 2, "squad": 1, "lineup": 1, "bench": -1, "captain": 1, "vicecaptain": 0, "type": 4, "transfer_count": 1},
        {"id": 2, "week": 2, "squad": 1, "lineup": 1, "bench": -1, "captain": 0, "vicecaptain": 1, "type": 3, "transfer_count": 1},
        {"id": 3, "week": 2, "squad": 1, "lineup": 0, "bench": 0, "captain": 0, "vicecaptain": 0, "type": 1, "transfer_count": 1},
        {"id": 99, "week": 3, "squad": 1, "lineup": 1, "bench": -1, "captain": 1, "vicecaptain": 0, "type": 4, "transfer_count": 0},
    ])
    plan = plan_from_picks(picks, 2)
    assert plan.squad_ids == (1, 2, 3)
    assert plan.lineup_ids == (1, 2)
    assert plan.bench_ids == (3,)
    assert plan.captain_id == 1
    assert plan.vice_id == 2
    assert plan.transfer_count == 1


def test_outcomes_sum_double_gameweek_points() -> None:
    performances = pd.DataFrame([
        {"player_id": 1, "gameweek_id": 2, "total_points": 4, "minutes": 90},
        {"player_id": 1, "gameweek_id": 2, "total_points": 2, "minutes": 90},
        {"player_id": 2, "gameweek_id": 2, "total_points": 1, "minutes": 45},
    ])
    players = pd.DataFrame([{"id": 1, "position_id": 3}, {"id": 2, "position_id": 2}, {"id": 3, "position_id": 1}])
    outcomes = outcomes_from_performances(performances, players, 2)
    assert outcomes[1].points == pytest.approx(6.0)
    assert outcomes[1].minutes == pytest.approx(180.0)
    assert outcomes[3].points == pytest.approx(0.0)
    assert outcomes[3].minutes == pytest.approx(0.0)


def test_read_data_loads_injected_projections_path(tmp_path: Path) -> None:
    path = tmp_path / "proj.csv"
    pd.DataFrame({"ID": [1], "1_Pts": [2.0]}).to_csv(path, index=False)
    loaded = read_data({"projections_path": str(path)})
    assert int(loaded.iloc[0]["ID"]) == 1
    assert float(loaded.iloc[0]["1_Pts"]) == pytest.approx(2.0)


def test_ranking_runs_oat_then_winner_cross_with_injected_solver() -> None:
    recorded: list[str] = []

    def solve_week(gw: int, squad: tuple[int, ...], ft_bank: int, arm: WalkforwardArm) -> DeadlineWeekPlan:
        recorded.append(arm.arm_id)
        lineup = (1, 2, 3, 4, 7, 8, 9, 10, 12, 13, 14)
        bench = (5, 6, 11, 15)
        return DeadlineWeekPlan(lineup + bench, lineup, bench, 12, 13, 0 if gw == 1 else 1)

    from backtesting.decision_regret import PlayerOutcome

    def outcomes_for_week(_gw: int) -> dict[int, PlayerOutcome]:
        positions = {
            1: 1, 15: 1,
            2: 2, 3: 2, 4: 2, 5: 2, 6: 2,
            7: 3, 8: 3, 9: 3, 10: 3, 11: 3,
            12: 4, 13: 4, 14: 4,
        }
        bonus = 10.0 if recorded and recorded[-1].startswith("shape_3-5-2") else 0.0
        if recorded and recorded[-1] == "ft_attack":
            bonus += 3.0
        if recorded and recorded[-1] == "tilt_defcon_floor":
            bonus += 1.0
        return {
            pid: PlayerOutcome(pid, pos, 1.0 + bonus, 90.0) for pid, pos in positions.items()
        }

    rows = run_first_half_ranking(
        gameweeks=[1, 2],
        solve_week=solve_week,
        outcomes_for_week=outcomes_for_week,
    )
    arm_ids = [row["arm_id"] for row in rows]
    assert "baseline" in arm_ids
    assert "cross_3-5-2_attack_defcon_floor" in arm_ids
    assert all(row["status"] == "ok" for row in rows)
    assert all(row["realized_points"] != "" for row in rows)


def test_make_solve_week_passes_hit_ban_and_deadline_price_into_milp(tmp_path: Path) -> None:
    processed = tmp_path / "processed"
    processed.mkdir()
    pd.DataFrame([{
        "id": 9, "code": 99, "first_name": "A", "second_name": "B", "web_name": "AB",
        "club_id": 2, "position_id": 3, "now_cost": 80,
    }]).to_parquet(processed / "players.parquet", index=False)
    pd.DataFrame([{"id": 2, "name": "Arsenal", "short_name": "ARS"}]).to_parquet(
        processed / "clubs.parquet", index=False
    )
    pd.DataFrame([{
        "id": 1, "gameweek_id": 1, "home_club_id": 2, "away_club_id": 4,
        "team_h_difficulty": 3, "team_a_difficulty": 3,
    }]).to_parquet(processed / "fixtures.parquet", index=False)
    pd.DataFrame([
        {"player_id": 9, "gameweek_id": 1, "price": 50, "minutes": 90, "total_points": 2},
    ]).to_parquet(processed / "player_performances.parquet", index=False)
    captured: dict[str, object] = {}

    def project(_gw: int, horizon: int) -> pd.DataFrame:
        return pd.DataFrame([
            {
                "player_id": 9,
                "gameweek_id": gw,
                "projected_points": 4.0,
                "projected_minutes": 90.0,
                "xp_defcon": 1.0,
                "position_id": 3,
                "p_dnp": 0.1,
            }
            for gw in range(1, horizon + 1)
        ])

    def run_milp(my_data: dict[str, object], options: dict[str, object], arm: WalkforwardArm) -> pd.DataFrame:
        captured["options"] = options
        captured["my_data"] = my_data
        return pd.DataFrame([
            {"id": 9, "week": 1, "squad": 1, "lineup": 1, "bench": -1, "captain": 1, "vicecaptain": 0, "type": 3, "transfer_count": 15},
            {"id": 8, "week": 1, "squad": 1, "lineup": 0, "bench": 0, "captain": 0, "vicecaptain": 1, "type": 1, "transfer_count": 15},
        ])

    solve_week = make_solve_week(
        processed_dir=processed,
        seed_dir=tmp_path / "seed",
        work_dir=tmp_path / "work",
        project=project,
        run_milp=run_milp,
    )
    plan = solve_week(1, (), 0, FIRST_HALF_OAT_ARMS[0])
    options = captured["options"]
    assert isinstance(options, dict)
    assert options["weekly_hit_limit"] == 0
    assert options["preseason"] is True
    assert options["chip_limits"]["wc"] == 1
    assert options["use_wc"] == [1]
    assert captured["my_data"]["picks"] == []
    elements = options["fpl_bootstrap"]["elements"]
    assert elements[0]["now_cost"] == 50
    assert plan.captain_id == 9
    assert plan.transfer_count == 15
