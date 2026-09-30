"""Transfer Plan Scenario arms: Optimal, No Hit, Conservative (ADR 0042, ADR 0053)."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

import pandas as pd

from projections.expected_gw_score import PlayerGw, auto_captain_alternatives, expected_gw_score

ARM_OPTIMAL = "optimal"
ARM_NO_HIT = "no_hit"
ARM_CONSERVATIVE = "conservative"
ARM_NAMES: dict[str, str] = {
    ARM_OPTIMAL: "Optimal",
    ARM_NO_HIT: "No Hit",
    ARM_CONSERVATIVE: "Conservative",
}
ARM_TIEBREAK: dict[str, int] = {ARM_OPTIMAL: 0, ARM_NO_HIT: 1, ARM_CONSERVATIVE: 2}
LIVE_WEEKLY_HIT_LIMIT = 1
LIVE_HIT_COST = 4.0
NO_HIT_WEEKLY_HIT_LIMIT = 0


def feasible_scenario_arms(free_transfer_bank: int = 1) -> tuple[str, ...]:
    """Must arms are Optimal + No Hit + Conservative (ADR 0042, ADR 0053)."""
    _ = int(free_transfer_bank)
    return (ARM_OPTIMAL, ARM_NO_HIT, ARM_CONSERVATIVE)


def scenario_arm_overrides(
    arm: str,
    *,
    start_gw: int,
    free_transfer_bank: int,
) -> dict[str, Any]:
    if arm not in ARM_NAMES:
        raise ValueError(f"unknown Transfer Plan Scenario arm {arm!r}")
    _ = int(start_gw)
    _ = int(free_transfer_bank)
    if arm in (ARM_NO_HIT, ARM_CONSERVATIVE):
        return {
            "weekly_hit_limit": NO_HIT_WEEKLY_HIT_LIMIT,
            "hit_cost": LIVE_HIT_COST,
        }
    return {
        "weekly_hit_limit": LIVE_WEEKLY_HIT_LIMIT,
        "hit_cost": LIVE_HIT_COST,
    }


def find_unowned_flagged_players(
    players_df: pd.DataFrame,
    owned_ids: Sequence[int],
) -> list[int]:
    """Return IDs of unowned players carrying an injury/availability flag."""
    if players_df.empty:
        return []
    owned_set = set(owned_ids)
    flagged: list[int] = []
    id_col = "id" if "id" in players_df.columns else "player_id"
    for _, row in players_df.iterrows():
        pid = int(row[id_col])
        if pid in owned_set:
            continue
        status = str(row.get("status", "a"))
        chance = row.get("chance_of_playing_next_round")
        if chance is None or pd.isna(chance):
            chance = row.get("chance")
        is_flagged = False
        if status not in ("a", "", "None", "nan"):
            is_flagged = True
        elif chance is not None and not pd.isna(chance):
            try:
                if float(chance) < 100.0:
                    is_flagged = True
            except (ValueError, TypeError):
                pass
        if is_flagged:
            flagged.append(pid)
    return sorted(set(flagged))


def find_protected_one_match_missed_starters(
    perf_df: pd.DataFrame,
    owned_ids: Sequence[int],
    *,
    min_starter_rate: float = 0.6,
) -> list[int]:
    """Return owned players who started >= 60% of prior matches but missed only their most recent match."""
    if perf_df.empty or not owned_ids:
        return []
    owned_set = set(owned_ids)
    protected: list[int] = []
    sub = perf_df[perf_df["player_id"].isin(owned_set)]
    if sub.empty:
        return []
    for pid, group in sub.groupby("player_id"):
        ordered = group.sort_values("gameweek_id")
        if len(ordered) < 2:
            continue
        last_row = ordered.iloc[-1]
        last_mins = float(last_row.get("minutes", 0.0) or 0.0)
        last_starts = float(last_row.get("starts", 0.0) or 0.0)
        if last_mins == 0.0 and last_starts == 0.0:
            penultimate_row = ordered.iloc[-2]
            pen_mins = float(penultimate_row.get("minutes", 0.0) or 0.0)
            pen_starts = float(penultimate_row.get("starts", 0.0) or 0.0)
            if pen_mins == 0.0 and pen_starts == 0.0:
                continue
            prior = ordered.iloc[:-1]
            prior_starts = float(prior.get("starts", pd.Series(dtype=float)).sum())
            if len(prior) > 0 and (prior_starts / len(prior)) >= min_starter_rate:
                protected.append(int(pid))
    return sorted(protected)


def apply_scenario_arm(
    base_options: Mapping[str, Any],
    arm: str,
    *,
    start_gw: int,
    free_transfer_bank: int,
    banned_next_gw: Sequence[int] | None = None,
    locked_next_gw: Sequence[int] | None = None,
) -> dict[str, Any]:
    options = dict(base_options)
    options.pop("num_transfers", None)
    options.pop("no_transfer_gws", None)
    options.update(scenario_arm_overrides(arm, start_gw=start_gw, free_transfer_bank=free_transfer_bank))
    if arm == ARM_CONSERVATIVE:
        if banned_next_gw:
            existing_banned = list(options.get("banned_next_gw") or [])
            options["banned_next_gw"] = sorted(set(existing_banned) | set(banned_next_gw))
        if locked_next_gw:
            existing_locked = list(options.get("locked_next_gw") or [])
            options["locked_next_gw"] = sorted(set(existing_locked) | set(locked_next_gw))
    return options


def rank_scenarios(scenarios: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    ordered = sorted(
        scenarios,
        key=lambda row: (
            -float(row.get("horizon_egs") or 0.0),
            ARM_TIEBREAK.get(str(row.get("id")), 99),
            str(row.get("id")),
        ),
    )
    ranked: list[dict[str, Any]] = []
    for index, row in enumerate(ordered, start=1):
        item = dict(row)
        item["rank"] = index
        ranked.append(item)
    return ranked


def annotate_plan_with_egs(
    plan: Mapping[str, Any],
    players: Mapping[tuple[int, int], PlayerGw],
    *,
    hit_cost: float = LIVE_HIT_COST,
) -> dict[str, Any]:
    annotated = dict(plan)
    weeks_out: list[dict[str, Any]] = []
    horizon = 0.0
    start_gw = int((plan.get("meta") or {}).get("next_gw") or 0)
    start_auto: dict[str, object] | None = None
    for week in plan.get("weeks") or []:
        row = dict(week)
        gw = int(row.get("gw") or 0)
        lineup = [int(pid) for pid in row.get("lineup_ids") or []]
        bench = [int(pid) for pid in row.get("bench_ids") or []]
        gw_players = {pid: players[pid, gw] for pid in lineup + bench if (pid, gw) in players}
        egs = expected_gw_score(
            lineup_ids=lineup,
            bench_ids=bench,
            captain_id=row.get("captain_id"),
            vice_id=row.get("vice_id"),
            players=gw_players,
            hits=float(row.get("hits") or 0),
            hit_cost=hit_cost,
            chip=row.get("chip"),
        )
        row["expected_gw_score"] = egs
        horizon += egs
        weeks_out.append(row)
        if gw == start_gw or start_auto is None:
            start_auto = auto_captain_alternatives(lineup, gw_players)
    annotated["weeks"] = weeks_out
    annotated["horizon_egs"] = round(horizon, 4)
    annotated["auto_captain"] = start_auto or {
        "auto_captain_id": None,
        "auto_vice_id": None,
        "next_best": [],
    }
    return annotated
