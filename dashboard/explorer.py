"""Explorer projection slices and an independent, session-only Squad What-If."""

from __future__ import annotations

import copy
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from dashboard.planner import Planner, SHAPES
from projections.explorer_slice import COMPONENT_KEYS, GameweekScore, aggregate_slice, assume_ninety_gameweek


def projections(player: dict[str, Any], model: str) -> dict[str, Any]:
    return player.get("models", {}).get(model, player).get("projections", {})


def player_slice(player: dict[str, Any], model: str, gws: tuple[int, ...], assume_ninety: bool = False) -> dict[str, Any]:
    scores = {}
    for gw in gws:
        cell = projections(player, model).get(f"gw{gw}", {})
        score = GameweekScore(float(cell.get("total_xp") or 0), float(cell.get("xmins") or 0),
                             **{key: float(cell.get(key) or 0) for key in COMPONENT_KEYS})
        scores[gw] = assume_ninety_gameweek(score) if assume_ninety else score
    metrics = aggregate_slice(scores, gws)
    return {"ID": int(player["id"]), "Player": player["name"], "Club": player.get("team", "Unavailable"),
            "Position": player.get("pos", ""), "Price": float(player["price"]),
            "Ownership %": player.get("ownership_pct"), "xP": metrics.total, "xP / GW": metrics.per_gameweek,
            "xP / 90": metrics.rate_per_90, "xMins / GW": metrics.avg_minutes,
            **{key: getattr(metrics, key) for key in COMPONENT_KEYS}}


@dataclass
class ExplorerSquad:
    ids: list[int]
    lineup: list[int]
    captain: int | None
    vice: int | None
    baseline: list[int] = field(default_factory=list)
    bench_order: list[int] = field(default_factory=list)

    @classmethod
    def from_dataset(cls, dataset: dict[str, Any], model: str, gws: tuple[int, ...]) -> ExplorerSquad:
        projected = copy.deepcopy(dataset)
        for player in projected["players"]:
            total = player_slice(player, model, gws)["xP"]
            player["projections"] = {f"gw{gws[0]}": {"total_xp": total}}
        planner = Planner(projected)
        ids = [pid for pid in planner.state["base_ids"] if pid in planner.players]
        result = planner.select_lineup(ids, gws[0])
        official = [pid for pid in ids if 0 < int(planner.players[pid].get("lineup_index") or 0) <= 11]
        lineup = official if len(official) == 11 else result["lineup_ids"]
        bench = sorted((pid for pid in ids if pid not in lineup), key=lambda pid: (planner.players[pid]["pos_id"] != 1, int(planner.players[pid].get("lineup_index") or 99), -player_slice(planner.players[pid], model, gws)["xP"]))
        return cls(ids, lineup, None, None, list(ids), bench)

    def replace(self, outgoing: int, incoming: int, players: dict[int, dict[str, Any]]) -> None:
        if outgoing not in self.ids or incoming in self.ids or incoming not in players:
            raise ValueError("Choose an owned Player and an unowned replacement.")
        if players[outgoing]["pos_id"] != players[incoming]["pos_id"]:
            raise ValueError("Replacement must have the same Position.")
        self.ids[self.ids.index(outgoing)] = incoming
        if outgoing in self.lineup:
            self.lineup[self.lineup.index(outgoing)] = incoming
        if outgoing in self.bench_order:
            self.bench_order[self.bench_order.index(outgoing)] = incoming
        if self.captain == outgoing:
            self.captain = incoming
        if self.vice == outgoing:
            self.vice = incoming

    def swap(self, starter: int, substitute: int, players: dict[int, dict[str, Any]]) -> None:
        if starter not in self.lineup or substitute not in self.ids or substitute in self.lineup:
            raise ValueError("Select one starter and one substitute.")
        lineup = [substitute if pid == starter else pid for pid in self.lineup]
        counts = Counter(players[pid]["pos_id"] for pid in lineup)
        if counts[1] != 1 or (counts[2], counts[3], counts[4]) not in SHAPES:
            raise ValueError("Swap would leave an illegal Starting XI. Choose a different substitute.")
        self.lineup = lineup
        self.bench_order[self.bench_order.index(substitute)] = starter
        if self.captain == starter:
            self.captain = substitute
        if self.vice == starter:
            self.vice = substitute

    def bank(self, players: dict[int, dict[str, Any]], base_bank: float) -> float:
        sales = sum(float(price if (price := players[pid].get("selling_price")) is not None else players[pid]["price"]) for pid in self.baseline if pid not in self.ids)
        purchases = sum(float(players[pid]["price"]) for pid in self.ids if pid not in self.baseline)
        return round(base_bank + sales - purchases, 1)

    def warnings(self, players: dict[int, dict[str, Any]], base_bank: float) -> list[str]:
        warnings = []
        clubs = Counter(players[pid]["team_id"] for pid in self.ids)
        if any(count > 3 for count in clubs.values()):
            warnings.append("What-If exceeds three Players from one Club.")
        bank = self.bank(players, base_bank)
        if bank < 0:
            warnings.append(f"What-If exceeds available bank by £{-bank:.1f}m.")
        return warnings
