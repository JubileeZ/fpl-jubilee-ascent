"""Explorer projection slices and an independent, session-only Squad What-If."""

from __future__ import annotations

import copy
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from dashboard.planner import Planner, SHAPES
from projections.explorer_slice import COMPONENT_KEYS, GameweekScore, aggregate_slice, assume_ninety_gameweek
from projections.expected_gw_score import expected_gw_score, player_gw_from_dashboard


def projections(player: dict[str, Any], model: str) -> dict[str, Any]:
    return player.get("models", {}).get(model, player).get("projections", {})


def player_slice(player: dict[str, Any], model: str, gws: tuple[int, ...], assume_ninety: bool = False) -> dict[str, Any]:
    scores = {}
    cells = [projections(player, model).get(f"gw{gw}", {}) for gw in gws]
    for gw in gws:
        cell = projections(player, model).get(f"gw{gw}", {})
        score = GameweekScore(float(cell.get("total_xp") or 0), float(cell.get("xmins") or 0),
                             **{key: float(cell.get(key) or 0) for key in COMPONENT_KEYS})
        scores[gw] = assume_ninety_gameweek(score) if assume_ninety else score
    metrics = aggregate_slice(scores, gws)
    points_available = all(cell.get("total_xp") is not None for cell in cells)
    minutes_available = all(cell.get("xmins") is not None for cell in cells)
    goals_available = all(cell.get("xp_goals") is not None for cell in cells)
    assists_available = all(cell.get("xp_assists") is not None for cell in cells)
    gi_available = goals_available and assists_available
    return {
        "ID": int(player["id"]),
        "Player": player["name"],
        "Club": player.get("team", "Unavailable"),
        "Position": player.get("pos", ""),
        "Price": float(player["price"]),
        "Ownership %": player.get("ownership_pct"),
        "Projection": "Available" if points_available and minutes_available else "Unavailable",
        "xP": metrics.total if points_available else None,
        "xP / GW": metrics.per_gameweek if points_available else None,
        "xP / 90": metrics.rate_per_90 if points_available and minutes_available else None,
        "xMins / GW": metrics.avg_minutes if minutes_available else None,
        "xp_gi": round(metrics.xp_goals + metrics.xp_assists, 2) if gi_available else None,
        "Apps": player.get("apps"),
        "Starts": player.get("actual_starts", player.get("starts")),
        "Actual Mins": player.get("actual_minutes", player.get("minutes")),
        "Goals": player.get("actual_goals", player.get("goals_scored")),
        "Goals / 90": player.get("goals_per_90"),
        "Goals / App": player.get("goals_per_app"),
        "Assists": player.get("actual_assists", player.get("assists")),
        "Assists / 90": player.get("assists_per_90"),
        "Assists / App": player.get("assists_per_app"),
        "GI": player.get("actual_gi"),
        "GI / 90": player.get("gi_per_90"),
        "GI / App": player.get("gi_per_app"),
        "xG": player.get("actual_xg"),
        "xG / 90": player.get("xg_per_90"),
        "xG / App": player.get("xg_per_app"),
        "xA": player.get("actual_xa"),
        "xA / 90": player.get("xa_per_90"),
        "xA / App": player.get("xa_per_app"),
        "xGI": player.get("actual_xgi"),
        "xGI / 90": player.get("xgi_per_90"),
        "xGI / App": player.get("xgi_per_app"),
        "CS": player.get("actual_clean_sheets", player.get("clean_sheets")),
        "CS %": player.get("cs_rate"),
        "GC": player.get("actual_goals_conceded", player.get("goals_conceded")),
        "GC / 90": player.get("gc_per_90"),
        "xGC": player.get("actual_xgc"),
        "xGC / 90": player.get("xgc_per_90"),
        "Defcon Hits": player.get("defcon_hits"),
        "Defcon %": player.get("defcon_hit_rate"),
        "Saves": player.get("actual_saves"),
        "Saves / 90": player.get("saves_per_90"),
        "Saves / App": player.get("saves_per_app"),
        **{key: getattr(metrics, key) if all(cell.get(key) is not None for cell in cells) else None for key in COMPONENT_KEYS},
    }


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
            total = player_slice(player, model, gws)["xP"] or 0
            player["projections"] = {f"gw{gws[0]}": {"total_xp": total}}
        planner = Planner(projected)
        ids = [pid for pid in planner.state["base_ids"] if pid in planner.players]
        result = planner.select_lineup(ids, gws[0])
        official = [pid for pid in ids if 0 < int(planner.players[pid].get("lineup_index") or 0) <= 11]
        lineup = official if len(official) == 11 else result["lineup_ids"]
        bench = sorted((pid for pid in ids if pid not in lineup), key=lambda pid: (planner.players[pid]["pos_id"] != 1, int(planner.players[pid].get("lineup_index") or 99), -(player_slice(planner.players[pid], model, gws)["xP"] or 0)))
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


def compare_squads(dataset: dict[str, Any], model: str, gws: tuple[int, ...], squad: ExplorerSquad) -> list[dict[str, Any]]:
    players = {int(player["id"]): player for player in dataset["players"]}
    projected = {**dataset, "players": [{**player, "projections": projections(player, model)} for player in dataset["players"]]}
    lookup = player_gw_from_dashboard(projected)
    baseline = ExplorerSquad.from_dataset(dataset, model, gws)
    transfers = len(set(squad.ids) - set(squad.baseline))
    hits = max(0, transfers - int(dataset.get("meta", {}).get("free_transfers", 1)))
    rows = []
    for gw in gws:
        values = {pid: value for (pid, week), value in lookup.items() if week == gw}

        def score(selected: ExplorerSquad) -> float | None:
            cells = {pid: projections(players[pid], model).get(f"gw{gw}", {}) for pid in selected.ids}
            if any(cell.get("total_xp") is None or cell.get("xmins") is None for cell in cells.values()):
                return None
            captain = selected.captain or max((pid for pid in selected.lineup if pid != selected.vice), key=lambda pid: float(cells[pid]["total_xp"]))
            vice = selected.vice or max((pid for pid in selected.lineup if pid != captain), key=lambda pid: float(cells[pid]["total_xp"]))
            return expected_gw_score(lineup_ids=selected.lineup, bench_ids=selected.bench_order, captain_id=captain, vice_id=vice, players=values,
                                     hits=hits if selected is squad and gw == gws[0] else 0)

        base_score, new_score = score(baseline), score(squad)
        cells = [projections(players[pid], model).get(f"gw{gw}", {}) for pid in squad.ids]
        squad_xp = round(sum(float(cell["total_xp"]) for cell in cells), 2) if all(cell.get("total_xp") is not None for cell in cells) else None
        rows.append({"GW": gw, "Projection": "Available" if base_score is not None and new_score is not None else "Unavailable",
                     "Squad xP": squad_xp, "User Squad Expected": base_score, "What-If Expected": new_score,
                     "Difference": round(new_score - base_score, 2) if base_score is not None and new_score is not None else None})
    return rows


def watchlist_rows(dataset: dict[str, Any], model: str, gws: tuple[int, ...], watchlist_ids: list[int]) -> list[dict[str, Any]]:
    players = {int(p["id"]): p for p in dataset.get("players", [])}
    rows = []
    for pid in watchlist_ids:
        player = players.get(pid)
        if not player:
            continue
        base = player_slice(player, model, gws)
        row = {
            "ID": pid,
            "Player": player["name"],
            "Club": player.get("team", ""),
            "Position": player.get("pos", ""),
            "Price": f"£{float(player['price']):.1f}m",
            "xP": round(base["xP"], 1) if base["xP"] is not None else None,
            "xP / GW": round(base["xP / GW"], 2) if base["xP / GW"] is not None else None,
            "xMins / GW": round(base["xMins / GW"], 1) if base["xMins / GW"] is not None else None,
        }
        for gw in gws:
            cell = projections(player, model).get(f"gw{gw}", {})
            fix_text = cell.get("fixture_label") or cell.get("opponent", "-")
            xp_cell = f"{float(cell['total_xp']):.1f}" if cell.get("total_xp") is not None else "-"
            diff = cell.get("difficulty")
            diff_str = f" [FDR {diff:.1f}]" if diff is not None else ""
            row[f"GW{gw}"] = f"{fix_text} ({xp_cell} xP{diff_str})"
        rows.append(row)
    return rows

