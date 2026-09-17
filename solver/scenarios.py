"""Transfer Plan Scenario arms: Roll, 1 FT, Optimal."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from projections.expected_gw_score import PlayerGw, auto_captain_alternatives, expected_gw_score

ARM_ROLL = "roll"
ARM_ONE_FT = "one_ft"
ARM_OPTIMAL = "optimal"
ARM_NAMES: dict[str, str] = {
    ARM_ROLL: "Roll",
    ARM_ONE_FT: "1 FT",
    ARM_OPTIMAL: "Optimal",
}
ARM_TIEBREAK: dict[str, int] = {ARM_OPTIMAL: 0, ARM_ONE_FT: 1, ARM_ROLL: 2}
LIVE_WEEKLY_HIT_LIMIT = 1
LIVE_HIT_COST = 4.0


def feasible_scenario_arms(free_transfer_bank: int) -> tuple[str, ...]:
    if int(free_transfer_bank) >= 1:
        return (ARM_ROLL, ARM_ONE_FT, ARM_OPTIMAL)
    return (ARM_ROLL, ARM_OPTIMAL)


def scenario_arm_overrides(
    arm: str,
    *,
    start_gw: int,
    free_transfer_bank: int,
) -> dict[str, Any]:
    if arm not in ARM_NAMES:
        raise ValueError(f"unknown Transfer Plan Scenario arm {arm!r}")
    if arm == ARM_ONE_FT and int(free_transfer_bank) < 1:
        raise ValueError("1 FT arm requires Free Transfer Bank ≥ 1")
    overrides: dict[str, Any] = {
        "weekly_hit_limit": LIVE_WEEKLY_HIT_LIMIT,
        "hit_cost": LIVE_HIT_COST,
    }
    if arm == ARM_ROLL:
        overrides["no_transfer_gws"] = [int(start_gw)]
    elif arm == ARM_ONE_FT:
        overrides["num_transfers"] = 1
    return overrides


def apply_scenario_arm(
    base_options: Mapping[str, Any],
    arm: str,
    *,
    start_gw: int,
    free_transfer_bank: int,
) -> dict[str, Any]:
    options = dict(base_options)
    options.pop("num_transfers", None)
    options.pop("no_transfer_gws", None)
    options.update(scenario_arm_overrides(arm, start_gw=start_gw, free_transfer_bank=free_transfer_bank))
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

