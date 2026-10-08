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
    assert not planner.accept_recommendations({"optimal": {"weeks": [{"gw": 6, "squad_ids": list(range(1, 16))}]}},
                                               snapshot, planner.data_digest)
    assert planner.week(6)["vacancies"] == [7]
    assert not planner.recommendation_valid()
