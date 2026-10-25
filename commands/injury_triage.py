"""CLI entrypoint for injury triage, scouting targets, and xMins override synthesis."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import pandas as pd

from features.builder import resolve_operational_processed_dir
from features.injury_triage import (
    build_broad_pool_shield,
    select_scouting_targets,
    synthesize_xmins_override,
)

logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="FPL Injury & Availability Triage")
    parser.add_argument("--target_gw", type=int, default=None, help="Target gameweek")
    parser.add_argument("--horizon", type=int, default=8, help="Planning horizon length")
    parser.add_argument("--base-csv", type=str, default=None, help="Path to base external xMins CSV")
    parser.add_argument(
        "--set",
        action="append",
        dest="overrides",
        help="Player curve in format 'pid:gw_val,gw_val...' e.g. '12:0,30,65,85'",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/planner/xmins_override.csv",
        help="Output CSV path for synthesized overrides",
    )
    parser.add_argument(
        "--audit-solution",
        type=str,
        default=None,
        help="Path to solution.json to audit solution-involved players",
    )
    parser.add_argument("--json", action="store_true", help="Output summary in JSON format")
    args = parser.parse_args()

    proc = resolve_operational_processed_dir(Path("."))

    if args.audit_solution:
        from features.injury_triage import audit_solution_players
        audit_res = audit_solution_players(
            proc,
            args.audit_solution,
            override_csv_path=args.output,
        )
        if args.json:
            print(json.dumps(audit_res, indent=2))
        else:
            print("\n" + "=" * 65)
            print("SOLUTION PLAYERS AUDIT (TRANSFERS & HELD FLAGGED ASSETS)")
            print("=" * 65)
            print("\n[TRANSFERS IN]")
            for p in audit_res["transfers_in"]:
                flag_str = f" [FLAGGED: {p['status']} - {p['news']}]" if p["is_flagged"] else " [CLEAN]"
                gws_str = ", ".join(f"GW{g}" for g in p["gameweeks"])
                print(f"  • {p['web_name']:14s} ({p['position']}, £{p['price']:.1f}m) in {gws_str}{flag_str}")
            print("\n[TRANSFERS OUT]")
            for p in audit_res["transfers_out"]:
                flag_str = f" [FLAGGED: {p['status']} - {p['news']}]" if p["is_flagged"] else " [CLEAN]"
                gws_str = ", ".join(f"GW{g}" for g in p["gameweeks"])
                print(f"  • {p['web_name']:14s} ({p['position']}, £{p['price']:.1f}m) out {gws_str}{flag_str}")
            print("\n[FLAGGED SQUAD MEMBERS HELD]")
            for p in audit_res["held_flagged"]:
                traj_str = ", ".join(f"GW{k}: {v}m" for k, v in p["override_xmins"].items()) if p["override_xmins"] else "Native Champion"
                print(f"  • {p['web_name']:14s} ({p['position']}, £{p['price']:.1f}m, status: {p['status']}) - {p['news']}")
                print(f"    Assigned Curve: {traj_str}")
            print("=" * 65 + "\n")
        return
    gw_parquet = proc / "gameweeks.parquet"
    if not gw_parquet.exists():
        logger.error("Missing %s. Run refresh_data first.", gw_parquet)
        sys.exit(1)

    from solver.planning import resolve_default_target_gw
    target_gw = args.target_gw if args.target_gw is not None else resolve_default_target_gw(proc)

    horizon = args.horizon
    planning_gws = list(range(target_gw, target_gw + horizon))

    # Parse targeted overrides from CLI e.g. "12:0,30,65,85"
    targeted_map: dict[tuple[int, int], float] = {}
    if args.overrides:
        for item in args.overrides:
            if ":" not in item:
                continue
            pid_str, vals_str = item.split(":", 1)
            try:
                pid = int(pid_str.strip())
                val_list = [float(v.strip()) for v in vals_str.split(",") if v.strip()]
                for gw, val in zip(planning_gws, val_list):
                    targeted_map[(pid, gw)] = val
            except ValueError as e:
                logger.warning("Failed to parse override '%s': %s", item, e)

    # 1. Broad Pool Shield
    shield = build_broad_pool_shield(proc, target_gw=target_gw, horizon=horizon)
    unique_shield_pids = {pid for (pid, _gw) in shield.keys()}

    # 2. Scouting Targets
    picks_path = proc / "user_picks.parquet"
    user_squad_ids: set[int] = set()
    if picks_path.exists():
        df_picks = pd.read_parquet(picks_path)
        user_squad_ids = set(df_picks["player_id"].astype(int))

    targets = select_scouting_targets(proc, user_squad_ids=user_squad_ids, top_per_tier=2)

    # 3. Synthesize override CSV
    out_path = Path(args.output)
    saved_path = synthesize_xmins_override(
        processed_dir=proc,
        target_gw=target_gw,
        horizon=horizon,
        targeted_overrides=targeted_map,
        base_csv_path=args.base_csv,
        output_path=out_path,
        include_broad_pool_shield=True,
    )

    if args.json:
        payload = {
            "target_gw": target_gw,
            "horizon": horizon,
            "planning_gws": planning_gws,
            "shielded_players_count": len(unique_shield_pids),
            "squad_flagged": targets["squad_flagged"],
            "market_flagged_by_tier": targets["market_flagged_by_tier"],
            "targeted_overrides_applied": len(targeted_map),
            "output_csv": str(saved_path),
        }
        print(json.dumps(payload, indent=2, default=str))
        return

    # User-facing summary table
    print("\n" + "=" * 65)
    print(f"INJURY & AVAILABILITY TRIAGE (GW{target_gw}–GW{target_gw + horizon - 1})")
    print("=" * 65)

    print("\n[YOUR SQUAD - FLAGGED ASSETS]")
    if targets["squad_flagged"]:
        for p in targets["squad_flagged"]:
            ret_str = f"Expected back: {p['parsed_return_date']}" if p['parsed_return_date'] else "Unknown return"
            print(f"  • {p['web_name']:14s} (ID: {p['id']:3d}, £{p['price']:.1f}m, status: {p['status']}) - {p['news']}")
            print(f"    -> Triage: {ret_str}")
    else:
        print("  None. All squad players are currently unflagged.")

    print("\n[KEY MARKET TARGETS - FLAGGED BY PRICE TIER]")
    for tier, p_list in targets["market_flagged_by_tier"].items():
        if p_list:
            items_str = ", ".join([f"{p['web_name']} (£{p['price']:.1f}m, {p['status']})" for p in p_list])
            print(f"  • {tier:12s}: {items_str}")

    print("\n[BROAD POOL SHIELD]")
    print(f"  ✓ {len(unique_shield_pids)} flagged players automatically shielded (assigned 0.0 xMins before return date).")
    print(f"  ✓ Synthesized override file saved to: {saved_path}")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
