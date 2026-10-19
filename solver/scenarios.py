"""Transfer Plan Scenario arms: Strategic, Unconstrained, No Hit (ADR 0042, ADR 0061)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from projections.expected_gw_score import PlayerGw, auto_captain_alternatives, expected_gw_score

ARM_STRATEGIC = "strategic"
ARM_UNCONSTRAINED = "unconstrained"
ARM_NO_HIT = "no_hit"

# Legacy backward-compatibility aliases
ARM_OPTIMAL = ARM_UNCONSTRAINED
ARM_CONSERVATIVE = ARM_STRATEGIC

ARM_NAMES: dict[str, str] = {
    ARM_STRATEGIC: "Strategic",
    ARM_UNCONSTRAINED: "Unconstrained",
    ARM_NO_HIT: "No Hit",
}
ARM_TIEBREAK: dict[str, int] = {
    ARM_STRATEGIC: 0,
    ARM_UNCONSTRAINED: 1,
    ARM_NO_HIT: 2,
}
LEGACY_ARM_MAP: dict[str, str] = {
    "optimal": ARM_UNCONSTRAINED,
    "conservative": ARM_STRATEGIC,
}

LIVE_WEEKLY_HIT_LIMIT = 1
LIVE_HIT_COST = 4.0
NO_HIT_WEEKLY_HIT_LIMIT = 0

DEFAULT_STRATEGIC_OPTIONS: dict[str, Any] = {
    "hit_friction": 1.8,
    "starter_xmins_floor": 65.0,
    "starter_xmins_penalty": 10.0,
    "bench_cover_min": 12,
    "bench_cover_xmins": 65.0,
    "bench_cover_penalty": 1.5,
    "def_stack_cap": 2,
    "def_stack_penalty": 1.2,
    "gk_transfer_friction": 1.5,
}

_STRATEGIC_KEY_ALIASES: dict[str, str] = {
    "hit_buffer": "hit_friction",
    "starter_min_xmins": "starter_xmins_floor",
    "defensive_stack_cap": "def_stack_cap",
    "gk_friction_penalty": "gk_transfer_friction",
}


def normalize_strategic_options(raw: Mapping[str, Any] | None) -> dict[str, Any]:
    out = dict(DEFAULT_STRATEGIC_OPTIONS)
    if not raw:
        return out
    for key, val in raw.items():
        if val is None:
            continue
        canon = _STRATEGIC_KEY_ALIASES.get(str(key), str(key))
        if canon in out:
            out[canon] = int(val) if isinstance(out[canon], int) else float(val)
    return out


def normalize_arm_key(arm: str | None) -> str:
    if arm is None:
        return ARM_STRATEGIC
    raw = str(arm).strip().lower().replace("-", "_")
    return LEGACY_ARM_MAP.get(raw, raw)


def feasible_scenario_arms(free_transfer_bank: int = 1) -> tuple[str, ...]:
    """Must arms are Strategic + Unconstrained + No Hit (ADR 0042, ADR 0061)."""
    _ = int(free_transfer_bank)
    return (ARM_STRATEGIC, ARM_UNCONSTRAINED, ARM_NO_HIT)


def scenario_arm_overrides(
    arm: str,
    *,
    start_gw: int = 1,
    free_transfer_bank: int = 1,
    strategic_options: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    norm_arm = normalize_arm_key(arm)
    if norm_arm not in ARM_NAMES:
        raise ValueError(f"unknown Transfer Plan Scenario arm {arm!r}")
    _ = int(start_gw)
    _ = int(free_transfer_bank)
    if norm_arm == ARM_NO_HIT:
        return {
            "weekly_hit_limit": NO_HIT_WEEKLY_HIT_LIMIT,
            "hit_cost": LIVE_HIT_COST,
            "strategic_mode": False,
            "strategic_options": None,
        }
    if norm_arm == ARM_UNCONSTRAINED:
        return {
            "weekly_hit_limit": LIVE_WEEKLY_HIT_LIMIT,
            "hit_cost": LIVE_HIT_COST,
            "strategic_mode": False,
            "strategic_options": None,
        }
    strat = normalize_strategic_options(strategic_options)
    return {
        "weekly_hit_limit": LIVE_WEEKLY_HIT_LIMIT,
        "hit_cost": LIVE_HIT_COST,
        "strategic_mode": True,
        "strategic_options": strat,
        **strat,
    }


def apply_scenario_arm(
    base_options: Mapping[str, Any],
    arm: str,
    *,
    start_gw: int = 1,
    free_transfer_bank: int = 1,
    strategic_options: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    options = dict(base_options)
    options.pop("num_transfers", None)
    options.pop("no_transfer_gws", None)
    active_strategic = dict(base_options.get("strategic_options") or {})
    if strategic_options:
        active_strategic.update(dict(strategic_options))
    overrides = scenario_arm_overrides(
        arm,
        start_gw=start_gw,
        free_transfer_bank=free_transfer_bank,
        strategic_options=active_strategic,
    )
    options.update(overrides)
    return options


def rank_scenarios(scenarios: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    ordered = sorted(
        scenarios,
        key=lambda row: (
            -float(row.get("horizon_egs") or 0.0),
            ARM_TIEBREAK.get(normalize_arm_key(str(row.get("id"))), 99),
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


def compute_scenarios_digest(
    *,
    processed_dir: Path,
    target_gw: int,
    horizon: int,
    champion: str,
    booked_chips: Mapping[str, Sequence[int]] | None = None,
    enabled_chips: Sequence[Mapping[str, object]] | None = None,
    force_keep: Sequence[Mapping[str, object]] | None = None,
    gap: float = 0.0,
    strategic_options: Mapping[str, Any] | None = None,
    xmins_override: Path | str | None = None,
) -> str:
    """Deterministic SHA-256 fingerprint of inputs for cache avoidance (ADR 0057, ADR 0061)."""
    hasher = hashlib.sha256()
    for filename in ("user_picks.parquet", "user_state.parquet", "players.parquet"):
        p = processed_dir / filename
        if p.exists():
            hasher.update(p.read_bytes())
        else:
            hasher.update(b"missing")
    if xmins_override is not None:
        xp = Path(xmins_override)
        if xp.exists():
            hasher.update(xp.read_bytes())
        else:
            hasher.update(str(xmins_override).encode("utf-8"))
    params = {
        "target_gw": int(target_gw),
        "horizon": int(horizon),
        "champion": str(champion),
        "booked_chips": {k: sorted(v) for k, v in (booked_chips or {}).items()},
        "enabled_chips": sorted(
            [dict(x) for x in (enabled_chips or [])],
            key=lambda d: (str(d.get("chip")), int(d.get("chip_set") or 0)),
        ),
        "force_keep": sorted(
            [dict(x) for x in (force_keep or [])],
            key=lambda d: (int(d.get("player_id") or 0), int(d.get("gw") or 0)),
        ),
        "gap": float(gap),
        "strategic_options": normalize_strategic_options(strategic_options),
    }
    hasher.update(json.dumps(params, sort_keys=True).encode("utf-8"))
    return hasher.hexdigest()
