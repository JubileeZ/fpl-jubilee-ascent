"""JSON-safe Transfer Plan from a MILP solution."""

from __future__ import annotations

from typing import Any

import pandas as pd


def _json_value(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, bool):
        return value
    if isinstance(value, float):
        return round(float(value), 4)
    if isinstance(value, int):
        return int(value)
    if isinstance(value, str):
        return value
    return value


def _chip(raw: Any) -> str | None:
    if raw is None:
        return None
    text = str(raw).strip()
    return text or None


def _player_move(row: pd.Series) -> dict[str, Any]:
    return {"id": _json_value(row["id"]), "name": str(row["name"])}


def serialize_transfer_plan(
    solution: dict[str, Any],
    *,
    champion: str,
    horizon: int,
    next_gw: int,
    decay_base: float,
    booked_chips: dict[str, list[int]] | None = None,
) -> dict[str, Any]:
    picks = solution.get("picks")
    if not isinstance(picks, pd.DataFrame) or picks.empty:
        weeks: list[dict[str, Any]] = []
    else:
        weeks = _weeks_from_picks(picks, solution.get("statistics") or {})

    chips = booked_chips or {}
    return {
        "meta": {
            "champion": champion,
            "horizon": int(horizon),
            "next_gw": int(next_gw),
            "decay_base": _json_value(decay_base),
            "solver_objective": _json_value(solution.get("score")),
            "total_xp": _json_value(solution.get("total_xp")),
            "booked_chips": {
                "use_wc": [int(g) for g in chips.get("use_wc", [])],
                "use_bb": [int(g) for g in chips.get("use_bb", [])],
                "use_fh": [int(g) for g in chips.get("use_fh", [])],
                "use_tc": [int(g) for g in chips.get("use_tc", [])],
            },
        },
        "weeks": weeks,
        "summary": str(solution.get("summary") or ""),
    }


def _weeks_from_picks(picks: pd.DataFrame, statistics: dict[Any, Any]) -> list[dict[str, Any]]:
    weeks: list[dict[str, Any]] = []
    for gw, group in picks.groupby("week", sort=True):
        gw_int = int(gw)
        stats = statistics.get(gw_int) or statistics.get(gw) or {}
        squad = group[group["squad"] == 1]
        lineup = group[group["lineup"] == 1]
        bench = group[group["bench"] >= 0]
        captains = group[group["captain"] == 1]
        vices = group[group["vicecaptain"] == 1]
        buys = group[group["transfer_in"] == 1]
        sells = group[group["transfer_out"] == 1]
        chip = _chip(stats.get("chip"))
        if chip is None and len(group):
            chip = _chip(group["chip"].iloc[0])
        xp = stats.get("xP")
        if xp is None:
            xp = lineup["xp_cont"].sum() if "xp_cont" in lineup else 0
        weeks.append(
            {
                "gw": gw_int,
                "chip": chip,
                "ft": _json_value(stats.get("ft", group["ft"].iloc[0] if len(group) else 0)),
                "hits": _json_value(stats.get("pt", 0)),
                "transfer_count": _json_value(stats.get("nt", group["transfer_count"].iloc[0] if len(group) else 0)),
                "itb": _json_value(stats.get("itb")),
                "xp": _json_value(xp),
                "objective": _json_value(stats.get("obj")),
                "buy": [_player_move(row) for _, row in buys.iterrows()],
                "sell": [_player_move(row) for _, row in sells.iterrows()],
                "squad_ids": [int(i) for i in squad["id"].tolist()],
                "lineup_ids": [int(i) for i in lineup["id"].tolist()],
                "bench_ids": [int(i) for i in bench["id"].tolist()],
                "captain_id": int(captains["id"].iloc[0]) if len(captains) else None,
                "vice_id": int(vices["id"].iloc[0]) if len(vices) else None,
            }
        )
    return weeks
