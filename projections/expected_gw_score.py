"""Expected GW Score for a Transfer Plan week."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from backtesting.decision_regret import LineupDecision, PlayerOutcome, score_lineup

_BB_CHIPS = frozenset({"bb", "bboost", "benchboost"})
_TC_CHIPS = frozenset({"tc", "3xc", "triplecaptain"})


@dataclass(frozen=True)
class PlayerGw:
    player_id: int
    position_id: int
    xp: float
    p_appear: float


def appearance_probability(xp: float, xmins: float, p_dnp: float | None) -> float:
    if p_dnp is not None:
        return max(0.0, min(1.0, 1.0 - float(p_dnp)))
    if xmins <= 0:
        return 0.0 if xp <= 0 else 0.0
    return max(0.0, min(1.0, float(xmins) / 90.0))


def _norm_chip(chip: str | None) -> str:
    if not chip:
        return ""
    return str(chip).strip().lower().replace("_", "").replace("-", "")


def _points_if_play(player: PlayerGw) -> float:
    if player.p_appear <= 0:
        return 0.0
    if player.p_appear >= 1:
        return float(player.xp)
    return float(player.xp) / player.p_appear


def _outcome(player: PlayerGw, appeared: bool) -> PlayerOutcome:
    pts = _points_if_play(player) if appeared else 0.0
    minutes = 90.0 if appeared else 0.0
    return PlayerOutcome(player.player_id, player.position_id, pts, minutes)


def _score_appearance(
    *,
    lineup_ids: Sequence[int],
    bench_ids: Sequence[int],
    captain_id: int | None,
    vice_id: int | None,
    players: Mapping[int, PlayerGw],
    appeared: Mapping[int, bool],
    chip: str,
) -> float:
    outcomes = {
        pid: _outcome(players[pid], appeared.get(pid, False))
        for pid in list(lineup_ids) + list(bench_ids)
        if pid in players
    }
    captain = int(captain_id or lineup_ids[0])
    vice = int(vice_id or (lineup_ids[1] if len(lineup_ids) > 1 else lineup_ids[0]))
    decision = LineupDecision(tuple(lineup_ids), tuple(bench_ids), captain, vice)
    scored = score_lineup(decision, outcomes)
    points = scored.points
    if _norm_chip(chip) in _TC_CHIPS:
        cap = outcomes.get(captain)
        if cap and captain in scored.final_starters and cap.minutes > 0:
            points += cap.points
    if _norm_chip(chip) in _BB_CHIPS:
        in_xi = set(scored.final_starters)
        for pid in bench_ids:
            if pid in in_xi:
                continue
            bench = outcomes.get(pid)
            if bench and bench.minutes > 0:
                points += bench.points
    return float(points)


def expected_gw_score(
    *,
    lineup_ids: Sequence[int],
    bench_ids: Sequence[int],
    captain_id: int | None,
    vice_id: int | None,
    players: Mapping[int, PlayerGw],
    hits: float = 0.0,
    hit_cost: float = 4.0,
    chip: str | None = None,
) -> float:
    squad = [pid for pid in list(lineup_ids) + list(bench_ids) if pid in players]
    certain_on = {pid for pid in squad if players[pid].p_appear >= 1.0}
    certain_off = {pid for pid in squad if players[pid].p_appear <= 0.0}
    uncertain = [pid for pid in squad if pid not in certain_on and pid not in certain_off]
    chip_key = _norm_chip(chip)
    total = 0.0
    n = len(uncertain)
    for mask in range(1 << n):
        prob = 1.0
        appeared: dict[int, bool] = {pid: True for pid in certain_on}
        appeared.update({pid: False for pid in certain_off})
        for index, pid in enumerate(uncertain):
            play = bool(mask & (1 << index))
            p = players[pid].p_appear
            prob *= p if play else (1.0 - p)
            appeared[pid] = play
        total += prob * _score_appearance(
            lineup_ids=lineup_ids,
            bench_ids=bench_ids,
            captain_id=captain_id,
            vice_id=vice_id,
            players=players,
            appeared=appeared,
            chip=chip_key,
        )
    return round(total - float(hits) * float(hit_cost), 4)


def auto_captain_alternatives(
    lineup_ids: Sequence[int],
    players: Mapping[int, PlayerGw],
    *,
    next_best: int = 2,
) -> dict[str, object]:
    ranked = sorted(
        (pid for pid in lineup_ids if pid in players),
        key=lambda pid: (-players[pid].xp, pid),
    )
    auto_c = ranked[0] if ranked else None
    auto_vc = ranked[1] if len(ranked) > 1 else None
    rest = ranked[2 : 2 + max(0, int(next_best))]
    return {
        "auto_captain_id": auto_c,
        "auto_vice_id": auto_vc,
        "next_best": [{"id": pid, "xp": round(players[pid].xp, 4)} for pid in rest],
    }


_POS_ID = {"G": 1, "D": 2, "M": 3, "F": 4}


def player_gw_from_dashboard(dataset: Mapping[str, Any]) -> dict[tuple[int, int], PlayerGw]:
    out: dict[tuple[int, int], PlayerGw] = {}
    for player in dataset.get("players") or []:
        pid = int(player["id"])
        pos = int(player.get("pos_id") or _POS_ID.get(str(player.get("pos") or "M"), 3))
        for key, row in (player.get("projections") or {}).items():
            if not str(key).startswith("gw"):
                continue
            gw = int(str(key)[2:])
            xp = float(row.get("total_xp") or 0.0)
            xmins = float(row.get("xmins") or 0.0)
            p_dnp = row.get("p_dnp")
            p_appear = row.get("p_appear")
            if p_appear is None:
                p_appear = appearance_probability(xp, xmins, None if p_dnp is None else float(p_dnp))
            out[pid, gw] = PlayerGw(pid, pos, xp, float(p_appear))
    return out

