from pathlib import Path
from typing import Any

import pytest

from dashboard.planner import Planner, PlanStore


def dataset() -> dict[str, Any]:
    positions = [1, 1] + [2] * 5 + [3] * 5 + [4] * 3 + [2]
    players = [{
        "id": index, "name": f"Player {index}", "pos_id": position,
        "pos": {1: "G", 2: "D", 3: "M", 4: "F"}[position],
        "team_id": (7 if index == 16 else index) % 5, "price": 5.0, "selling_price": 4.5,
        "projections": {f"gw{gw}": {"total_xp": float(index), "xmins": 90.0,
                                    "p_appear": 1.0} for gw in range(6, 12)},
    } for index, position in enumerate(positions, 1)]
    return {"players": players, "meta": {"owned_squad_ids": list(range(1, 16)),
            "itb": 2.0, "free_transfers": 1, "transfer_plan_start": 6}}


def test_sell_creates_real_vacancy_and_replacement_reselects_xi(tmp_path: Path) -> None:
    planner = Planner(dataset())
    planner.sell(6, 7)
    partial = planner.week(6)
    assert partial["vacancies"] == [7]
    assert len(partial["lineup_ids"]) == 11
    assert not partial["complete"]
    planner.buy(6, 7, 16)
    week = planner.week(6)
    assert week["complete"]
    assert 16 in week["lineup_ids"]
    assert 7 not in planner.week(7)["squad_ids"]
    assert week["bank"] == 1.5
    store = PlanStore(tmp_path / "plan.json")
    store.save(planner.state)
    restored = Planner(dataset(), store.load())
    assert restored.week(6)["squad_ids"] == week["squad_ids"]


def test_manual_vice_does_not_become_auto_captain() -> None:
    planner = Planner(dataset())
    planner.override(6, "vice", 15)
    week = planner.week(6)
    assert week["vice_id"] == 15
    assert week["captain_id"] == 14
    planner.override(6, "bench", 15)
    assert any("override" in message for message in planner.week(6)["conflicts"])


def test_incomplete_sale_keeps_vacancy_visible_next_week() -> None:
    planner = Planner(dataset())
    planner.sell(6, 7)
    assert planner.week(7)["vacancies"] == [7]


def test_invalid_replacement_does_not_modify_draft() -> None:
    planner = Planner(dataset())
    before = planner.snapshot()
    with pytest.raises(ValueError, match="Replacement"):
        planner.buy(6, 7, 15)
    assert planner.snapshot() == before


def test_changed_input_retains_recommendation_without_overwriting_draft() -> None:
    planner = Planner(dataset())
    snapshot = planner.snapshot()
    planner.sell(6, 7)
    assert not planner.accept_recommendations({"strategic": {"weeks": [{"gw": 6, "squad_ids": list(range(1, 16))}]}},
                                               snapshot, planner.data_digest)
    assert planner.week(6)["vacancies"] == [7]
    assert not planner.recommendation_valid()


def test_optimized_moves_display_alongside_manual_choices() -> None:
    data = dataset()
    data["players"].append({**data["players"][-1], "id": 17, "name": "Player 17", "team_id": 3})
    planner = Planner(data)
    planner.sell(6, 7)
    planner.buy(6, 7, 16)
    planner.sell(7, 16)
    planner.buy(7, 16, 7)
    plan = {"weeks": [{"gw": 6, "sell": [{"id": 7}, {"id": 3}], "buy": [{"id": 16}, {"id": 17}]},
                      {"gw": 7, "sell": [{"id": 16}], "buy": [{"id": 7}]}]}
    assert planner.accept_recommendations({"strategic": plan}, planner.snapshot(), planner.data_digest)
    week = planner.week(6)
    assert week["transfers"] == [{"out": 7, "in": 16}, {"out": 3, "in": 17}]
    assert 17 in week["squad_ids"] and week["complete"]
    planner.override(6, "captain", 14)
    assert 17 in planner.week(6)["squad_ids"]
    assert planner.week(7)["transfers"] == [{"out": 16, "in": 7}]
    planner.sell(6, 17)
    assert planner.week(6)["transfers"] == [{"out": 7, "in": 16}, {"out": 3, "in": None}]
    assert planner.week(7)["transfers"] == [{"out": 16, "in": 7}]


def test_reset_restores_solver_chip() -> None:
    data = dataset()
    data["meta"]["transfer_plan_available_chips"] = [{"chip": "bb", "gws": [6]}]
    planner = Planner(data)
    planner.set_chip(6, "bb")
    planner.accept_recommendations({"strategic": {"weeks": [{"gw": 6, "chip": None, "buy": [], "sell": []}]}},
                                  planner.snapshot(), planner.data_digest)
    planner.reset()
    assert planner.week(6)["chip"] is None
    assert planner.state["chips"] == {}


def test_legacy_scenario_normalization() -> None:
    data = dataset()
    p1 = Planner(data, {"version": 1, "start": 6, "end": 11, "scenario": "optimal"})
    assert p1.state["scenario"] == "unconstrained"
    p2 = Planner(data, {"version": 1, "start": 6, "end": 11, "scenario": "conservative"})
    assert p2.state["scenario"] == "strategic"


def test_planner_dual_tier_model_switch_scores_selected_model_projections() -> None:
    data = dataset()
    data["meta"]["default_model"] = "adaptive_causal_challenger"
    data["meta"]["confirmed_champion"] = "def_xg_shrink_challenger"
    data["meta"]["provisional_active"] = "adaptive_causal_challenger"
    data["meta"]["models"] = ["adaptive_causal_challenger", "def_xg_shrink_challenger"]
    for p in data["players"]:
        p["models"] = {
            "adaptive_causal_challenger": {
                "projections": {
                    f"gw{gw}": {"total_xp": float(p["id"]) * 2.0, "xmins": 90.0, "p_appear": 1.0}
                    for gw in range(6, 12)
                }
            },
            "def_xg_shrink_challenger": {
                "projections": {
                    f"gw{gw}": {"total_xp": float(p["id"]), "xmins": 90.0, "p_appear": 1.0}
                    for gw in range(6, 12)
                }
            },
        }

    planner = Planner(data)
    assert planner.state["model"] == "adaptive_causal_challenger"
    assert planner.xp(10, 6) == 20.0
    prov_egs = planner.expected_score(6)
    assert prov_egs is not None

    planner.set_model("def_xg_shrink_challenger")
    assert planner.state["model"] == "def_xg_shrink_challenger"
    assert planner.xp(10, 6) == 10.0
    champ_egs = planner.expected_score(6)
    assert champ_egs is not None and champ_egs < prov_egs


def test_planner_service_dual_tier_digest_request_and_switch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from dashboard.planner_service import PlannerPaths, make_solve_request, solver_options, source_digest
    from models.selection import ModelSelection, save_model_selection

    sel_path = tmp_path / "model_selection.json"
    save_model_selection(
        ModelSelection(
            champion="def_xg_shrink_challenger",
            candidates=("adaptive_causal_challenger",),
            provisional_active="adaptive_causal_challenger",
            podium_frozen_season="2026-27",
            podium_sealed=True,
        ),
        sel_path,
    )
    monkeypatch.setattr("models.selection.DEFAULT_CONFIG_PATH", sel_path)
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "adaptive_causal_challenger.csv").write_text("a\n", encoding="utf-8")
    (data_dir / "def_xg_shrink_challenger.csv").write_text("b\n", encoding="utf-8")
    monkeypatch.setattr("solver.paths.DATA_DIR", data_dir)

    processed = tmp_path / "processed"
    processed.mkdir()
    ds_path = tmp_path / "dashboard_data.json"
    data = dataset()
    data["meta"].update(
        {
            "default_model": "def_xg_shrink_challenger",
            "confirmed_champion": "def_xg_shrink_challenger",
            "provisional_active": "adaptive_causal_challenger",
            "active_transfer_plan_model": "adaptive_causal_challenger",
            "models": ["def_xg_shrink_challenger", "adaptive_causal_challenger"],
        }
    )
    ds_path.write_text("{}", encoding="utf-8")
    paths = PlannerPaths(dataset=ds_path, processed=processed, storage=tmp_path / "storage")

    d1 = source_digest(paths)
    (data_dir / "adaptive_causal_challenger.csv").write_text("a2\n", encoding="utf-8")
    d2 = source_digest(paths)
    assert d1 != d2

    planner = Planner(data)
    req_prov = make_solve_request(planner, paths)
    assert req_prov["state"]["model"] == "adaptive_causal_challenger"
    opts_prov = solver_options(planner, paths)
    assert opts_prov["datasource"] == "adaptive_causal_challenger"

    planner.set_model("def_xg_shrink_challenger")
    req_champ = make_solve_request(planner, paths)
    assert req_champ["state"]["model"] == "def_xg_shrink_challenger"
    opts_champ = solver_options(planner, paths)
    assert opts_champ["datasource"] == "def_xg_shrink_challenger"

    # Champion-only dataset must fail closed when Dual-Tier Provisional Active is live
    champ_only_data = dataset()
    champ_only_data["meta"].update({"default_model": "def_xg_shrink_challenger", "models": ["def_xg_shrink_challenger"]})
    with pytest.raises(ValueError, match="omit active Dual-Tier"):
        make_solve_request(Planner(champ_only_data), paths)


def test_planner_service_allows_second_sealed_finalist_and_blocks_stale_remote_checkout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from dashboard.planner_service import PlannerPaths, make_solve_request, solver_options
    from models.planner_selection import StaleCheckoutError
    from models.selection import ModelSelection, save_model_selection

    sel_path = tmp_path / "model_selection.json"
    save_model_selection(
        ModelSelection(
            champion="def_xg_shrink_challenger",
            candidates=("adaptive_causal_challenger", "club_def_prior_challenger"),
            provisional_active=None,
            podium_frozen_season="2026-27",
            podium_sealed=True,
        ),
        sel_path,
    )
    monkeypatch.setattr("models.selection.DEFAULT_CONFIG_PATH", sel_path)
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    for m in ("def_xg_shrink_challenger", "adaptive_causal_challenger", "club_def_prior_challenger"):
        (data_dir / f"{m}.csv").write_text("id\n1\n", encoding="utf-8")
    monkeypatch.setattr("solver.paths.DATA_DIR", data_dir)

    processed = tmp_path / "processed"
    processed.mkdir()
    ds_path = tmp_path / "dashboard_data.json"
    ds_path.write_text("{}", encoding="utf-8")
    paths = PlannerPaths(dataset=ds_path, processed=processed, storage=tmp_path / "storage")

    data = dataset()
    data["meta"].update(
        {
            "default_model": "club_def_prior_challenger",
            "confirmed_champion": "def_xg_shrink_challenger",
            "provisional_active": None,
            "active_transfer_plan_model": "club_def_prior_challenger",
            "models": [
                "def_xg_shrink_challenger",
                "adaptive_causal_challenger",
                "club_def_prior_challenger",
            ],
            "planner_preflight": {
                "effective_model": "club_def_prior_challenger",
                "selection_reason": "verified_scorecard_leader",
                "freshness_status": "verified_current",
                "comparable_scores": {
                    "def_xg_shrink_challenger": 820.0,
                    "adaptive_causal_challenger": 830.0,
                    "club_def_prior_challenger": 845.0,
                },
                "latest_settled_gw": 15,
                "verified_prefix_end_gw": 15,
            },
        }
    )
    planner = Planner(data)
    assert planner.active_model == "club_def_prior_challenger"
    req = make_solve_request(planner, paths)
    assert req["state"]["model"] == "club_def_prior_challenger"
    opts = solver_options(planner, paths)
    assert opts["datasource"] == "club_def_prior_challenger"

    # When preflight marks stale_remote_changed, make_solve_request blocks with StaleCheckoutError
    stale_data = dataset()
    stale_data["meta"].update(
        {
            **data["meta"],
            "planner_preflight": {
                **data["meta"]["planner_preflight"],
                "freshness_status": "stale_remote_changed",
            },
        }
    )
    with pytest.raises(StaleCheckoutError, match="manual 'git pull'"):
        make_solve_request(Planner(stale_data), paths)

