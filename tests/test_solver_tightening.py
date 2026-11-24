"""Exactness parity and adaptive live threading tests for V3+ solver tightening (#239, #240)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pandas as pd
import pytest

from commands.solve import execute_transfer_plan
from commands.transfer_plan_scenarios import (
    adaptive_arm_options,
    execute_transfer_plan_scenarios,
)
from solver.solver import _exact_k_domination_prune, prep_data, solve_multi_period_fpl
from solver.utils import load_settings
from test_streamlit_planner import dataset


# Pre-V3+ exact golden outputs verified against main (95d22e09): (score, total_xp, iter2_score).
_PRE_V3_GOLDEN: dict[str, tuple[float, float, float | None]] = {
    "normal": (355.369799, 404.100000, None),
    "strategic": (353.869799, 404.100000, None),
    "no_hit": (353.869799, 404.100000, None),
    "use_wc": (352.557416, 400.300000, None),
    "use_wc_gw6": (357.867816, 404.100000, None),
    "use_bb": (367.077694, 421.700000, None),
    "use_tc": (367.597298, 404.100000, None),
    "use_fh": (352.283699, 404.100000, None),
    "force_keep_booked": (337.450309, 397.100000, None),
    "num_iterations_2": (355.369799, 404.100000, 355.2668985),
}


def _build_synthetic_solver_inputs(
    tmp_path: Path,
    *,
    horizon: int = 3,
    ft: int = 2,
    ft_base: int = 2,
    extra_players: int = 0,
) -> tuple[dict[str, Any], dict[str, Any], Path]:
    data = dataset()
    players = list(data["players"])
    # Add dominated + competitive extra candidates in Club1/Club2 to exercise k-domination pruning
    next_id = max(p["id"] for p in players) + 1
    for i in range(extra_players):
        pos_id = (i % 4) + 1
        pos_code = {1: "G", 2: "D", 3: "M", 4: "F"}[pos_id]
        club_id = i % 5
        players.append(
            {
                "id": next_id + i,
                "name": f"Extra{i}",
                "pos": pos_code,
                "pos_id": pos_id,
                "team_id": club_id,
                "price": 5.0 + 0.5 * (i % 3),
                "projections": {
                    f"gw{gw}": {"total_xp": 2.0 + 0.3 * (i % 5) + 0.1 * gw, "xmins": 90.0 if i % 2 == 0 else 45.0}
                    for gw in range(6, 6 + horizon)
                },
            }
        )

    projection_path = tmp_path / "projections.csv"
    rows = []
    for p in players:
        row: dict[str, Any] = {
            "ID": p["id"],
            "Name": p["name"],
            "Pos": p["pos"],
            "Price": p["price"],
            "Team": f"Club{p['team_id']}",
        }
        for gw in range(6, 6 + horizon):
            proj = p["projections"].get(f"gw{gw}") or p["projections"]["gw6"]
            row[f"{gw}_Pts"] = float(proj["total_xp"]) + 0.15 * (gw - 6)
            row[f"{gw}_xMins"] = float(proj.get("xmins", 90.0))
        rows.append(row)
    pd.DataFrame(rows).to_csv(projection_path, index=False)

    bootstrap: dict[str, Any] = {
        "elements": [
            {
                "id": p["id"],
                "web_name": p["name"],
                "team": p["team_id"],
                "element_type": p["pos_id"],
                "now_cost": int(round(p["price"] * 10)),
            }
            for p in players
        ],
        "teams": [{"id": club, "name": f"Club{club}", "short_name": f"C{club}"} for club in range(5)],
        "events": [{"id": gw, "is_next": gw == 6, "finished": False} for gw in range(6, 6 + horizon)],
        "element_types": [
            {"id": pos, "singular_name_short": label, "squad_min_play": low, "squad_max_play": high, "squad_select": count}
            for pos, label, low, high, count in [(1, "GKP", 1, 1, 2), (2, "DEF", 3, 5, 5), (3, "MID", 2, 5, 5), (4, "FWD", 1, 3, 3)]
        ],
    }

    initial_ids = [p["id"] for p in data["players"][:15]]
    my_data = {
        "picks": [
            {
                "element": pid,
                "position": idx + 1,
                "purchase_price": 50,
                "selling_price": 50,
                "is_captain": idx == 0,
                "is_vice_captain": idx == 1,
            }
            for idx, pid in enumerate(initial_ids)
        ],
        "chips": [],
        "transfers": {"bank": 20, "limit": ft_base if ft == ft_base else None, "made": 0},
    }
    if ft != ft_base:
        my_data["transfers"]["limit"] = ft

    options = load_settings()
    options.update(
        {
            "horizon": horizon,
            "override_next_gw": 6,
            "fpl_bootstrap": bootstrap,
            "fpl_fixtures": [],
            "projections_path": str(projection_path),
            "xmin_lb": 0,
            "keep_top_ev_percent": 100,
            "secs": 30,
            "gap": 0.0,
            "threads": 1,
            "parallel": "off",
            "random_seed": 42,
            "verbose": False,
            "ft_value_list": {"2": 2.4, "3": 1.44, "4": 0.72, "5": 0.24},
            "spare_ft_hold_weight": 0.15,
            "ft_use_penalty": 0.6,
        }
    )
    return my_data, options, tmp_path


@pytest.mark.parametrize(
    "case_name,extra_opts",
    [
        ("normal", {}),
        ("strategic", {"strategic_mode": True}),
        ("no_hit", {"strategic_mode": True, "weekly_hit_limit": 0}),
        ("use_wc", {"strategic_mode": True, "use_wc": [7]}),
        ("use_wc_gw6", {"strategic_mode": True, "use_wc": [6]}),
        ("use_bb", {"strategic_mode": True, "use_bb": [7]}),
        ("use_tc", {"strategic_mode": True, "use_tc": [7]}),
        ("use_fh", {"strategic_mode": True, "use_fh": [7]}),
        ("force_keep_booked", {"strategic_mode": True, "force_keep_gws": [(1, 7)]}),
        ("num_iterations_2", {"num_iterations": 2}),
    ],
)
def test_v3_plus_tightening_exact_parity_and_golden_oracle(
    tmp_path: Path,
    case_name: str,
    extra_opts: dict[str, Any],
) -> None:
    my_data, base_opts, _ = _build_synthetic_solver_inputs(tmp_path, horizon=3, ft=2, ft_base=2, extra_players=25)

    if case_name == "force_keep_booked":
        extra_opts = {
            **extra_opts,
            "booked_transfers": [{"gw": 6, "transfer_out": my_data["picks"][14]["element"]}],
        }

    opts_new = {**base_opts, **extra_opts}
    opts_unpruned = {**base_opts, **extra_opts}

    prepared_new = prep_data(my_data, opts_new)
    prepared_unpruned = prep_data(my_data, opts_unpruned)

    sols_new = solve_multi_period_fpl(prepared_new, opts_new)
    with patch("solver.solver._exact_k_domination_prune", side_effect=lambda data, *_a, **_k: data):
        sols_unpruned = solve_multi_period_fpl(prepared_unpruned, opts_unpruned)

    exp_score, exp_xp, exp_iter2_score = _PRE_V3_GOLDEN[case_name]
    assert sols_new[0]["score"] == pytest.approx(exp_score, abs=1e-5)
    assert sols_new[0]["total_xp"] == pytest.approx(exp_xp, abs=1e-5)
    if exp_iter2_score is not None:
        assert sols_new[1]["score"] == pytest.approx(exp_iter2_score, abs=1e-5)

    assert len(sols_new) == len(sols_unpruned)
    assert sols_new[0]["score"] == pytest.approx(sols_unpruned[0]["score"], abs=1e-6)
    assert sols_new[0]["total_xp"] == pytest.approx(sols_unpruned[0]["total_xp"], abs=1e-6)
    for gw_key, stat_old in sols_unpruned[0]["statistics"].items():
        stat_new = sols_new[0]["statistics"][gw_key]
        if int(gw_key) < int(opts_new["override_next_gw"]):
            assert stat_new.get("itb") == pytest.approx(stat_old.get("itb"), abs=1e-2)
            continue
        for field in ("itb", "ft", "ft_after", "ft_used", "pt", "nt", "xP", "obj", "chip"):
            if isinstance(stat_old.get(field), float):
                assert stat_new.get(field) == pytest.approx(stat_old.get(field), abs=1e-2)
            else:
                assert stat_new.get(field) == stat_old.get(field)

    if opts_new.get("strategic_mode"):
        assert sols_new[0]["strategic_audit"]["total_slack_penalty"] == pytest.approx(
            sols_unpruned[0]["strategic_audit"]["total_slack_penalty"], abs=1e-2
        )
        assert sols_new[0]["strategic_audit"]["total_hits"] == sols_unpruned[0]["strategic_audit"]["total_hits"]

    if case_name == "num_iterations_2":
        assert sols_new[1]["score"] == pytest.approx(sols_unpruned[1]["score"], abs=1e-6)


def test_exact_k_domination_prune_reduces_pool_and_respects_must_keep(tmp_path: Path) -> None:
    my_data, opts, _ = _build_synthetic_solver_inputs(tmp_path, horizon=3, extra_players=20)
    prepared = prep_data(my_data, opts)
    raw_len = len(prepared["merged_data"])
    pruned = _exact_k_domination_prune(prepared, opts, [6, 7, 8])
    assert len(pruned["merged_data"]) <= raw_len
    # All initial squad players are strictly preserved
    assert set(prepared["initial_squad"]).issubset(set(pruned["merged_data"].index))

    # Bypass when num_iterations > 1, num_transfers is set, or itb_value < 0
    assert len(_exact_k_domination_prune(prepared, {**opts, "num_iterations": 2}, [6, 7, 8])["merged_data"]) == raw_len
    assert len(_exact_k_domination_prune(prepared, {**opts, "num_transfers": 1}, [6, 7, 8])["merged_data"]) == raw_len
    assert len(_exact_k_domination_prune(prepared, {**opts, "itb_value": -0.1}, [6, 7, 8])["merged_data"]) == raw_len


def test_execute_transfer_plan_sets_adaptive_threads(tmp_path: Path) -> None:
    processed = tmp_path / "processed"
    processed.mkdir(parents=True)
    pd.DataFrame([{"id": 10, "code": 101, "web_name": "Haaland", "club_id": 1, "position_id": 4, "now_cost": 150}]).to_parquet(
        processed / "players.parquet"
    )
    pd.DataFrame([{"entry_id": 1, "gameweek_id": 1, "player_id": 10, "lineup_index": 11, "multiplier": 1, "is_captain": True, "is_vice_captain": False, "purchase_price": 145, "selling_price": 146}]).to_parquet(
        processed / "user_picks.parquet"
    )
    pd.DataFrame([{"entry_id": 1, "bank": 5, "value": 1000, "free_transfers": 1, "active_chip": None}]).to_parquet(
        processed / "user_state.parquet"
    )
    captured: dict[str, Any] = {}

    def fake_solve(_data: dict[str, Any], opts: dict[str, Any]) -> list[dict[str, Any]]:
        captured.update(opts)
        return [{"summary": "", "statistics": {}, "picks": pd.DataFrame(), "buy": "-", "sell": "-", "chip": "-", "score": 1.0, "total_xp": 1.0}]

    fake_csv = tmp_path / "champ.csv"
    fake_csv.write_text("Pos,ID,Name,Price,Team,6_Pts,6_xMins\nF,10,Haaland,15.0,ARS,8.0,90\n", encoding="utf-8")

    with (
        patch("commands.solve.DATA_DIR", tmp_path),
        patch("commands.solve.pad_solver_csv_horizon"),
        patch("commands.solve.prep_data", return_value={"next_gw": 6}),
        patch("commands.solve.solve_multi_period_fpl", side_effect=fake_solve),
        patch("solver.parallelism.detect_physical_cores", return_value=12),
    ):
        execute_transfer_plan(
            {"datasource": "champ", "horizon": 1},
            processed_dir=processed,
            target_gw=6,
            solution_path=tmp_path / "sol.json",
        )
    assert captured["threads"] == 4
    assert captured["parallel"] == "on"


def test_scenarios_dispatch_uses_process_pool_when_multithreaded_and_thread_pool_otherwise(tmp_path: Path) -> None:
    with patch("solver.parallelism.detect_physical_cores", return_value=12):
        opts_12 = adaptive_arm_options({"horizon": 6}, num_arms=3)
        assert opts_12["threads"] == 4
        assert opts_12["parallel"] == "on"
    with patch("solver.parallelism.detect_physical_cores", return_value=4):
        opts_4 = adaptive_arm_options({"horizon": 6}, num_arms=3)
        assert opts_4["threads"] == 1
        assert opts_4["parallel"] == "off"

    processed = tmp_path / "processed"
    processed.mkdir(parents=True)
    pd.DataFrame([{"id": 10, "code": 101, "web_name": "Haaland", "club_id": 1, "position_id": 4, "now_cost": 150}]).to_parquet(
        processed / "players.parquet"
    )
    pd.DataFrame([{"entry_id": 1, "gameweek_id": 1, "player_id": 10, "lineup_index": 11, "multiplier": 1, "is_captain": True, "is_vice_captain": False, "purchase_price": 145, "selling_price": 146}]).to_parquet(
        processed / "user_picks.parquet"
    )
    pd.DataFrame([{"entry_id": 1, "bank": 5, "value": 1000, "free_transfers": 1, "active_chip": None}]).to_parquet(
        processed / "user_state.parquet"
    )

    pool_kinds: list[str] = []

    class _FakeFuture:
        def __init__(self, val: Any) -> None:
            self._val = val

        def result(self) -> Any:
            return self._val

    class _FakeProcPool:
        def __init__(self, max_workers: int) -> None:
            pool_kinds.append(f"proc:{max_workers}")

        def __enter__(self) -> "_FakeProcPool":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def submit(self, fn: Any, arm: str, *_args: Any) -> _FakeFuture:
            del fn
            return _FakeFuture((arm, {"meta": {"solver_objective": 1.0, "next_gw": 6, "horizon": 1}, "weeks": [{"gw": 6, "lineup_ids": [10], "bench_ids": [], "captain_id": 10, "vice_id": 10, "hits": 0, "transfers_in": [], "transfers_out": []}]}))

    with (
        patch("solver.parallelism.detect_physical_cores", return_value=12),
        patch("commands.transfer_plan_scenarios.ProcessPoolExecutor", _FakeProcPool),
        patch("commands.transfer_plan_scenarios.as_completed", side_effect=lambda futs: list(futs)),
    ):
        payload = execute_transfer_plan_scenarios(
            processed_dir=processed,
            target_gw=6,
            horizon=1,
            dataset={"players": [{"id": 10, "pos": "F", "pos_id": 4, "projections": {"gw6": {"total_xp": 8.0, "xmins": 90.0, "p_appear": 1.0}}}]},
            scenarios_path=tmp_path / "scenarios.json",
            solution_path=tmp_path / "solution.json",
            force=True,
        )
    assert pool_kinds == ["proc:3"]
    assert payload["meta"]["status"] == "ok"
    assert json.loads((tmp_path / "scenarios.json").read_text(encoding="utf-8"))["meta"]["status"] == "ok"
