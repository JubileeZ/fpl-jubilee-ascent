"""Editable transfer sequence, legal XI selection, and durable draft storage."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import threading
from collections import Counter
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

from projections.expected_gw_score import expected_gw_score, player_gw_from_dashboard
from solver.scenarios import ARM_NAMES
from solver.planning import chip_set_for_gw, normalize_chip_key

SHAPES = ((3, 4, 3), (3, 5, 2), (4, 3, 3), (4, 4, 2), (4, 5, 1), (5, 2, 3), (5, 3, 2), (5, 4, 1))
SQUAD_COUNTS = {1: 2, 2: 5, 3: 5, 4: 3}
POSITION_NAMES = {1: "Goalkeeper", 2: "Defender", 3: "Midfielder", 4: "Forward"}


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


class PlanStore:
    _lock = threading.RLock()

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> dict[str, Any] | None:
        if not self.path.exists():
            return None
        state = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(state, dict):
            raise ValueError("Saved plan must be a JSON object. Preserve file and restore a valid backup.")
        return state

    def save(self, state: dict[str, Any], *, expected_digest: str | None = None) -> None:
        with self._lock:
            if expected_digest is not None and digest(self.load()) != expected_digest:
                raise ValueError("Another browser saved a newer draft. Reload the latest draft before editing again.")
            self._write(state)

    def _write(self, state: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(f".{self.path.name}.{uuid4().hex}.tmp")
        try:
            temporary.write_text(json.dumps(state, indent=2, allow_nan=False), encoding="utf-8")
            os.replace(temporary, self.path)
        finally:
            temporary.unlink(missing_ok=True)


class Planner:
    def __init__(self, dataset: dict[str, Any], state: dict[str, Any] | None = None) -> None:
        self.dataset = dataset
        self.players = {int(player["id"]): player for player in dataset.get("players", [])}
        self.data_digest = digest(dataset)
        meta = dataset.get("meta") or {}
        start = int(meta.get("transfer_plan_start", 1))
        self.state = copy.deepcopy(state) if state else {
            "version": 1, "start": start, "end": min(start + 5, 38),
            "scenario": "optimal", "base_ids": meta.get("owned_squad_ids", []),
            "base_bank": float(meta.get("itb", 0)), "base_ft": int(meta.get("free_transfers", 1)),
            "data_digest": self.data_digest, "edits": {}, "overrides": {}, "chips": {},
            "recommendations": {}, "revision": 0, "job_id": None,
        }
        if self.state.get("version") != 1:
            raise ValueError("Unsupported saved planner version. Preserve file before migrating.")

    @property
    def stale(self) -> bool:
        return self.state["data_digest"] != self.data_digest

    def snapshot(self) -> str:
        return digest({key: self.state[key] for key in (
            "start", "end", "scenario", "base_ids", "base_bank", "base_ft",
            "edits", "overrides", "chips", "revision", "data_digest",
        )})

    def change_horizon(self, start: int, end: int) -> None:
        deadline = int(self.dataset.get("meta", {}).get("transfer_plan_start", 1))
        if start != deadline or not start <= end <= min(start + 9, 38):
            raise ValueError("Plan starts at upcoming open deadline and spans 1–10 Gameweeks.")
        self.state.update(start=start, end=end)
        self.state["edits"] = {key: value for key, value in self.state["edits"].items() if start <= int(key) <= end}
        self.state["overrides"] = {key: value for key, value in self.state["overrides"].items() if start <= int(key) <= end}
        self.state["chips"] = {key: value for key, value in self.state["chips"].items() if start <= int(key) <= end}
        self.state["revision"] += 1

    def reset(self, scenario: str | None = None) -> None:
        if scenario is not None:
            if scenario not in ARM_NAMES:
                raise ValueError("Unknown scenario.")
            self.state["scenario"] = scenario
        self.state.update(edits={}, overrides={}, chips={})
        self.state["revision"] += 1

    def accept_recommendations(self, plans: dict[str, Any], snapshot: str, data_digest: str) -> bool:
        applicable = snapshot == self.snapshot() and data_digest == self.data_digest
        if not applicable:
            self.state["unapplied_result"] = {"plans": copy.deepcopy(plans), "snapshot": snapshot, "data_digest": data_digest}
            return False
        for arm, plan in plans.items():
            if arm in ARM_NAMES and plan.get("weeks"):
                self.state["recommendations"][arm] = {
                    "plan": copy.deepcopy(plan), "data_digest": data_digest,
                    "start": self.state["start"], "end": self.state["end"],
                    "snapshot": snapshot, "applicable": applicable,
                    "revision": self.state["revision"],
                    "edits_digest": digest(self.state["edits"]),
                    "chips_digest": digest(self.state["chips"]),
                }
        return applicable

    def recommendation_valid(self) -> bool:
        rec = self.state["recommendations"].get(self.state["scenario"])
        return bool(rec and rec["applicable"] and rec["data_digest"] == self.data_digest
                    and rec["start"] == self.state["start"] and rec["end"] == self.state["end"])

    def _recommendation_weeks(self) -> dict[int, dict[str, Any]]:
        if not self.recommendation_valid():
            return {}
        return {int(week["gw"]): week for week in self.state["recommendations"][self.state["scenario"]]["plan"]["weeks"]}

    def _recommendation_matches_transfers(self) -> bool:
        rec = self.state["recommendations"].get(self.state["scenario"], {})
        return (rec.get("edits_digest") == digest(self.state["edits"]) and rec.get("chips_digest") == digest(self.state["chips"])) if "edits_digest" in rec else rec.get("revision") == self.state["revision"]

    def _touch_transfers(self, gw: int) -> list[dict[str, int | None]]:
        key = str(gw)
        if key not in self.state["edits"] or (self.recommendation_valid() and self._recommendation_matches_transfers()):
            current = self.week(gw)
            self.state["edits"][key] = copy.deepcopy(current["transfers"])
            if current["chip"]:
                self.state["chips"][key] = current["chip"]
        return self.state["edits"][key]

    def sell(self, gw: int, player_id: int) -> None:
        if player_id not in self.week(gw)["squad_ids"]:
            raise ValueError("Player is not owned in selected Gameweek.")
        moves = self._touch_transfers(gw)
        purchase = next((move for move in moves if move["in"] == player_id), None)
        if purchase:
            purchase["in"] = None
        else:
            moves.append({"out": player_id, "in": None})
        self.state["revision"] += 1

    def undo_sale(self, gw: int, outgoing: int) -> None:
        moves = self._touch_transfers(gw)
        self.state["edits"][str(gw)] = [move for move in moves if move["out"] != outgoing]
        self.state["revision"] += 1

    def buy(self, gw: int, outgoing: int, incoming: int) -> None:
        if incoming not in self.candidates(gw, outgoing):
            raise ValueError("Replacement violates Position, budget, uniqueness, or Club limit.")
        moves = self._touch_transfers(gw)
        move = next((move for move in moves if move["out"] == outgoing), None)
        if move is None:
            moves.append({"out": outgoing, "in": incoming})
        else:
            move["in"] = incoming
        self.state["revision"] += 1

    def override(self, gw: int, kind: str, player_id: int | None) -> None:
        if kind not in ("bench", "captain", "vice"):
            raise ValueError("Unknown lineup override.")
        if player_id is not None and player_id not in self.week(gw)["squad_ids"]:
            raise ValueError("Override Player is not owned in selected Gameweek.")
        overrides = self.state["overrides"].setdefault(str(gw), {})
        if kind == "bench":
            bench = set(overrides.get("bench", []))
            if player_id is None:
                bench.clear()
            elif player_id in bench:
                bench.remove(player_id)
            else:
                bench.add(player_id)
            overrides["bench"] = sorted(bench)
        else:
            overrides[kind] = player_id
        self.state["revision"] += 1

    def set_chip(self, gw: int, chip: str | None) -> None:
        available = self.dataset.get("meta", {}).get("transfer_plan_available_chips", [])
        if chip and not any(row["chip"] == chip and gw in row["gws"] for row in available):
            raise ValueError("Chip unavailable in selected Gameweek.")
        if chip and any(week["chip"] == chip and week["gw"] != gw and chip_set_for_gw(week["gw"]) == chip_set_for_gw(gw) for week in self.weeks()):
            raise ValueError("Chip already booked in another Gameweek.")
        self._touch_transfers(gw)
        self.state["chips"][str(gw)] = chip
        self.state["revision"] += 1

    def xp(self, player_id: int, gw: int) -> float:
        return float(self.players[player_id].get("projections", {}).get(f"gw{gw}", {}).get("total_xp") or 0)

    def select_lineup(self, squad: list[int], gw: int) -> dict[str, Any]:
        overrides = self.state["overrides"].get(str(gw), {})
        excluded = set(overrides.get("bench", []))
        required = {pid for pid in (overrides.get("captain"), overrides.get("vice")) if pid is not None}
        conflicts = []
        if required & excluded or not required.issubset(squad):
            conflicts.append("Captain/vice override conflicts with ownership or bench override.")
        if overrides.get("captain") is not None and overrides.get("captain") == overrides.get("vice"):
            conflicts.append("Captain and vice-captain must differ.")
        eligible = [pid for pid in squad if pid in self.players and pid not in excluded]
        groups = {pos: sorted((pid for pid in eligible if self.players[pid]["pos_id"] == pos),
                              key=lambda pid: (-self.xp(pid, gw), pid)) for pos in SQUAD_COUNTS}
        best: list[int] = []
        best_score = float("-inf")
        for defence, midfield, forward in SHAPES:
            counts = {1: 1, 2: defence, 3: midfield, 4: forward}
            selected = []
            for pos, count in counts.items():
                pinned = [pid for pid in groups[pos] if pid in required]
                rest = [pid for pid in groups[pos] if pid not in required]
                if len(pinned) > count:
                    selected = []
                    break
                selected.extend(pinned + rest[:count - len(pinned)])
            if len(selected) != 11 or not required.issubset(selected):
                continue
            captain_pool = [pid for pid in selected if pid != overrides.get("vice")]
            captain = overrides.get("captain") or max(captain_pool, key=lambda pid: (self.xp(pid, gw), -pid))
            score = sum(self.xp(pid, gw) for pid in selected) + self.xp(captain, gw)
            if score > best_score:
                best, best_score = selected, score
        if not best:
            conflicts.append("Cannot select eleven legal starters. Fill vacancies or clear conflicting overrides.")
            best = eligible[:11]
        ordered = sorted(best, key=lambda pid: (-self.xp(pid, gw), pid))
        captain = overrides.get("captain") if overrides.get("captain") in best else next((pid for pid in ordered if pid != overrides.get("vice")), None)
        vice = overrides.get("vice") if overrides.get("vice") in best else next((pid for pid in ordered if pid != captain), None)
        bench = sorted((pid for pid in squad if pid not in best and pid in self.players),
                       key=lambda pid: (self.players[pid]["pos_id"] != 1, -self.xp(pid, gw), pid))
        return {"lineup_ids": best, "bench_ids": bench, "captain_id": captain,
                "vice_id": vice, "lineup_conflicts": conflicts}

    def _pair_moves(self, sells: list[int], buys: list[int]) -> list[dict[str, int | None]]:
        incoming = list(buys)
        moves: list[dict[str, int | None]] = []
        for outgoing in sells:
            position = self.players.get(outgoing, {}).get("pos_id")
            replacement = next((pid for pid in incoming if self.players.get(pid, {}).get("pos_id") == position), None)
            if replacement is not None:
                incoming.remove(replacement)
            moves.append({"out": outgoing, "in": replacement})
        return moves

    def weeks(self) -> list[dict[str, Any]]:
        squad = list(self.state["base_ids"])
        bank = float(self.state["base_bank"])
        free_transfers = int(self.state["base_ft"])
        recommendation = self._recommendation_weeks()
        first_edit = min((int(key) for key in self.state["edits"] | self.state["chips"]), default=39)
        transfers_match = self._recommendation_matches_transfers()
        result = []
        pending_sales: set[int] = set()
        for gw in range(self.state["start"], self.state["end"] + 1):
            before, bank_before = list(squad), bank
            rec_week = recommendation.get(gw, {})
            if rec_week.get("chip"):
                rec_week = {**rec_week, "chip": normalize_chip_key(rec_week["chip"])}
            stale_week = gw > first_edit and not transfers_match
            if str(gw) in self.state["edits"] and (not rec_week or not transfers_match or stale_week):
                moves = copy.deepcopy(self.state["edits"][str(gw)])
            elif rec_week and not stale_week:
                sells = [int(row["id"]) for row in rec_week.get("sell", [])]
                buys = [int(row["id"]) for row in rec_week.get("buy", [])]
                moves = self._pair_moves(sells, buys)
                # Free Hit weeks serialize temporary squad without transfer variables.
                if rec_week.get("chip") == "fh":
                    sells = [pid for pid in squad if pid not in rec_week["squad_ids"]]
                    buys = [pid for pid in rec_week["squad_ids"] if pid not in squad]
                    moves = self._pair_moves(sells, buys)
            else:
                moves = []
            conflicts = []
            sales = [move["out"] for move in moves]
            purchases = [move["in"] for move in moves if move["in"] is not None]
            for pid in sales:
                if pid not in squad:
                    conflicts.append(f"Sale Player {pid} no longer owned in GW{gw}.")
                elif pid not in self.players:
                    conflicts.append(f"Player {pid} missing from refreshed data.")
                else:
                    squad.remove(pid)
                    player = self.players[pid]
                    selling = player.get("selling_price") if pid in self.state["base_ids"] else player["price"]
                    bank += float(selling if selling is not None else player["price"])
            for pid in purchases:
                if pid not in self.players or pid in squad:
                    conflicts.append(f"Incoming Player {pid} unavailable or duplicated.")
                else:
                    squad.append(pid)
                    bank -= float(self.players[pid]["price"])
            chip = self.state["chips"].get(str(gw), rec_week.get("chip") if not stale_week else None)
            pending_sales.update(cast(int, move["out"]) for move in moves if move["in"] is None)
            pending_sales.difference_update(cast(int, move["out"]) for move in moves if move["in"] is not None)
            vacancies = sorted(pending_sales)
            counts = Counter(self.players[pid]["pos_id"] for pid in squad if pid in self.players)
            clubs = Counter(self.players[pid]["team_id"] for pid in squad if pid in self.players)
            if dict(counts) != SQUAD_COUNTS or len(squad) != 15 or len(set(squad)) != len(squad):
                conflicts.append("Fill replacement vacancies to restore a valid 15-player squad.")
            if len([pid for pid in squad if pid in self.players]) != len(squad):
                conflicts.append("Squad contains Players absent from current data.")
            if any(self.players.get(pid, {}).get("projections", {}).get(f"gw{gw}", {}).get("total_xp") is None for pid in squad):
                conflicts.append("Gameweek projections missing. Refresh projections before solving.")
            if any(count > 3 for count in clubs.values()):
                conflicts.append("Maximum three Players per Club.")
            if bank < -0.01:
                conflicts.append("Insufficient bank for proposed transfers.")
            hits = 0 if chip in ("wc", "fh") else max(0, len(purchases) - free_transfers)
            limit = 1 if self.state["scenario"] == "optimal" else 0
            if hits > limit:
                conflicts.append(f"Proposed Hits exceed {ARM_NAMES[self.state['scenario']]} policy.")
            lineup = self.select_lineup(squad, gw)
            conflicts.extend(lineup["lineup_conflicts"])
            projected = sum(self.xp(pid, gw) for pid in lineup["lineup_ids"])
            captain_xp = self.xp(lineup["captain_id"], gw) if lineup["captain_id"] else 0
            projected += captain_xp * (2 if chip == "tc" else 1)
            if chip == "bb":
                projected += sum(self.xp(pid, gw) for pid in lineup["bench_ids"])
            next_ft = free_transfers if chip in ("wc", "fh") else min(5, max(1, free_transfers - len(purchases) + 1))
            result.append({"gw": gw, "squad_ids": list(squad), "bank": round(bank, 1),
                           "bank_before": round(bank_before, 1), "ft": free_transfers, "next_ft": next_ft,
                           "hits": hits, "vacancies": vacancies, "complete": not conflicts,
                           "conflicts": conflicts, "transfers": moves, "chip": chip,
                           "projected_points": round(projected - hits * 4, 2),
                           "needs_recalculation": stale_week or self.stale,
                           "has_recommendation": bool(rec_week), **lineup})
            if chip == "fh":
                squad, bank = before, bank_before
            free_transfers = next_ft
        return result

    def week(self, gw: int) -> dict[str, Any]:
        return next(week for week in self.weeks() if week["gw"] == gw)

    def candidates(self, gw: int, outgoing: int) -> list[int]:
        week = self.week(gw)
        player = self.players.get(outgoing)
        if player is None:
            return []
        retained = [pid for pid in week["squad_ids"] if pid != outgoing]
        clubs = Counter(self.players[pid]["team_id"] for pid in retained if pid in self.players)
        available = week["bank"]
        if outgoing in week["squad_ids"]:
            available += float(player.get("selling_price") if player.get("selling_price") is not None else player["price"])
        return sorted((pid for pid, candidate in self.players.items()
                       if pid not in retained and pid != outgoing and candidate["pos_id"] == player["pos_id"]
                       and float(candidate["price"]) <= available + 0.01
                       and (self.state["scenario"] != "conservative" or
                            (candidate.get("status", "a") == "a" and (candidate.get("chance") is None or candidate["chance"] >= 100)))
                       and clubs[candidate["team_id"]] < 3), key=lambda pid: (-self.xp(pid, gw), pid))

    def expected_score(self, gw: int) -> float | None:
        week = self.week(gw)
        if not week["complete"]:
            return None
        lookup = player_gw_from_dashboard(self.dataset)
        return expected_gw_score(lineup_ids=week["lineup_ids"], bench_ids=week["bench_ids"],
                                 captain_id=week["captain_id"], vice_id=week["vice_id"],
                                 players={pid: value for (pid, week_id), value in lookup.items() if week_id == gw},
                                 hits=week["hits"], chip=week["chip"])
