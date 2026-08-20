import argparse
import json
import logging
import sys
import pandas as pd
from pathlib import Path

# Set up path to include root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from clients.env_loader import load_env, configure_utf8_stdio
load_env()
configure_utf8_stdio()

from models import get_default_model_name
from solver.utils import DEFAULT_PLANNING_HORIZON, load_settings
from solver.solver import prep_data, solve_multi_period_fpl
from solver.transfer_plan import serialize_transfer_plan

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CHIP_KEYS: tuple[str, ...] = ("use_wc", "use_bb", "use_fh", "use_tc")
SUPPORTED_DYNAMIC_OVERRIDES = frozenset({
    "allowed_chip_gws",
    "banned",
    "banned_next_gw",
    "bench_weights",
    "booked_transfers",
    "chip_limits",
    "delete_tmp",
    "double_defense_pick",
    "ev_per_price_cutoff",
    "export_debug",
    "force_ft_state_lb",
    "force_ft_state_ub",
    "forced_chip_gws",
    "ft_use_penalty",
    "ft_value",
    "ft_value_list",
    "future_transfer_limit",
    "gap",
    "hit_limit",
    "hide_transfers",
    "itb_loss_per_transfer",
    "itb_value",
    "iteration_criteria",
    "iteration_difference",
    "iteration_target",
    "keep",
    "keep_top_ev_percent",
    "locked",
    "locked_next_gw",
    "max_defenders_per_team",
    "max_players_from_team",
    "no_chip_gws",
    "no_future_transfer",
    "no_opposing_play",
    "no_transfer_by_position",
    "no_transfer_gws",
    "no_transfer_last_gws",
    "no_trs_except_wc",
    "num_iterations",
    "num_transfers",
    "objective",
    "only_booked_transfers",
    "opposing_play_group",
    "opposing_play_penalty",
    "pick_prices",
    "price_changes",
    "presolve",
    "random_seed",
    "randomized",
    "randomization_seed",
    "randomization_strength",
    "report_decay_base",
    "secs",
    "solver",
    "team_id",
    "team_data",
    "transfer_itb_buffer",
    "use_bb",
    "use_cmd",
    "use_fh",
    "use_tc",
    "use_wc",
    "vcap_weight",
    "verbose",
    "weekly_hit_limit",
    "xmin_lb",
})
BOOLEAN_DYNAMIC_OVERRIDES = frozenset({
    "delete_tmp",
    "double_defense_pick",
    "export_debug",
    "hide_transfers",
    "no_future_transfer",
    "no_opposing_play",
    "no_trs_except_wc",
    "only_booked_transfers",
    "randomized",
    "use_cmd",
    "verbose",
})


def _chip_values(value: object, chip_key: str) -> list[object]:
    if value is None:
        return []
    if isinstance(value, (str, int, float)):
        return [value]
    try:
        return list(value)  # type: ignore[arg-type]
    except TypeError as exc:
        raise ValueError(f"{chip_key} must be a gameweek list") from exc


def validate_booked_chips(options: dict[str, object], next_gw: int, horizon: int) -> None:
    """Validate booked chips before any solver/API work is started."""
    if next_gw < 1 or next_gw > 38:
        raise ValueError(f"next gameweek must be between 1 and 38, got {next_gw}")
    if horizon < 1:
        raise ValueError(f"horizon must be at least 1, got {horizon}")

    planning_gameweeks = set(range(next_gw, min(39, next_gw + horizon)))
    used_gameweeks: dict[int, str] = {}
    for chip_key in CHIP_KEYS:
        seen_for_chip: set[int] = set()
        for raw_gameweek in _chip_values(options.get(chip_key), chip_key):
            if isinstance(raw_gameweek, bool):
                raise ValueError(f"{chip_key} contains invalid gameweek {raw_gameweek!r}")
            try:
                gameweek = int(raw_gameweek)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{chip_key} contains invalid gameweek {raw_gameweek!r}") from exc
            if gameweek not in planning_gameweeks:
                first_gw = min(planning_gameweeks)
                last_gw = max(planning_gameweeks)
                raise ValueError(
                    f"{chip_key} uses GW{gameweek}, outside planning horizon GW{first_gw}-GW{last_gw}"
                )
            if gameweek in seen_for_chip:
                raise ValueError(f"{chip_key} is booked more than once for GW{gameweek}")
            if gameweek in used_gameweeks:
                raise ValueError(
                    f"{chip_key} conflicts with {used_gameweeks[gameweek]}: "
                    f"at most one chip may be booked in GW{gameweek}"
                )
            seen_for_chip.add(gameweek)
            used_gameweeks[gameweek] = chip_key


def booked_chips_from_options(options: dict[str, object]) -> dict[str, list[int]]:
    chips: dict[str, list[int]] = {}
    for chip_key in CHIP_KEYS:
        chips[chip_key] = []
        for raw in _chip_values(options.get(chip_key), chip_key):
            try:
                chips[chip_key].append(int(raw))
            except (TypeError, ValueError):
                continue
    return chips


def transfer_plan_options_for_dashboard(
    booked_chips: dict[str, list[int]],
    horizon: int,
) -> dict[str, object]:
    options = load_settings()
    options["horizon"] = int(horizon)
    options["datasource"] = get_default_model_name()
    for chip_key in CHIP_KEYS:
        options[chip_key] = [int(g) for g in booked_chips.get(chip_key, [])]
    return options


def execute_transfer_plan(
    options: dict[str, object],
    *,
    processed_dir: Path,
    target_gw: int,
    solution_path: Path,
) -> dict:
    """Run MILP and write a JSON-safe Transfer Plan."""
    horizon = int(options.get("horizon", DEFAULT_PLANNING_HORIZON))
    validate_booked_chips(options, target_gw, horizon)
    options["override_next_gw"] = target_gw

    if options.get("preseason", False):
        logger.info(f"Solving for Preseason starting from GW {target_gw}...")
        my_data = {"picks": [], "chips": [], "transfers": {"limit": None, "cost": 4, "bank": 1000, "value": 0}}
    else:
        logger.info("Loading current squad picks and state from processed Parquet...")
        my_data = build_my_data_from_parquet(processed_dir)

    logger.info(f"Preparing solver data using projections from '{options['datasource']}.csv'...")
    solver_data = prep_data(my_data, options)
    logger.info("Executing MILP solver...")
    solutions = solve_multi_period_fpl(solver_data, options)
    best_sol = solutions[0] if isinstance(solutions, list) and solutions else {}
    plan = serialize_transfer_plan(
        best_sol,
        champion=str(options.get("datasource") or get_default_model_name()),
        horizon=horizon,
        next_gw=target_gw,
        decay_base=float(options.get("decay_base", 0.85)),
        booked_chips=booked_chips_from_options(options),
    )
    solution_path.parent.mkdir(parents=True, exist_ok=True)
    with open(solution_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2)
    logger.info(f"Saved Transfer Plan to {solution_path}")
    return plan


def _apply_dynamic_overrides(options: dict[str, object], unknown: list[str]) -> None:
    """Apply supported solver overrides and reject typos before solving."""
    i = 0
    while i < len(unknown):
        arg = unknown[i]
        if not arg.startswith("--"):
            raise ValueError(f"Unsupported positional argument: {arg}")
        key = arg[2:]
        value: str | None = None
        if "=" in key:
            key, value = key.split("=", 1)
        key = key.replace("-", "_")
        if key not in SUPPORTED_DYNAMIC_OVERRIDES:
            raise ValueError(f"Unsupported solver option '--{key}'")
        if value is None and i + 1 < len(unknown) and not unknown[i + 1].startswith("--"):
            value = unknown[i + 1]
            i += 1
        if value is None:
            if key in BOOLEAN_DYNAMIC_OVERRIDES:
                options[key] = True
            else:
                raise ValueError(f"Solver option '--{key}' requires a value")
        elif value.lower() in {"true", "false"}:
            options[key] = value.lower() == "true"
        elif key in CHIP_KEYS or key in {"locked", "banned", "keep"}:
            options[key] = [int(v.strip()) if v.strip().isdigit() else v.strip() for v in str(value).split(",") if v.strip()]
        elif value.isdigit():
            options[key] = int(value)
        else:
            try:
                options[key] = float(value)
            except ValueError:
                options[key] = value
        i += 1


def build_my_data_from_parquet(processed_dir: Path) -> dict:
    """Loads squad picks and user state from processed Parquet files to form the my_data dict."""
    picks_path = processed_dir / "user_picks.parquet"
    state_path = processed_dir / "user_state.parquet"
    players_path = processed_dir / "players.parquet"
    
    if not picks_path.exists() or not state_path.exists() or not players_path.exists():
        raise FileNotFoundError(
            "Squad picks or state Parquet files not found. "
            "Please run 'python -m commands.refresh_data' with FPL credentials set to retrieve your team squad."
        )
        
    df_picks = pd.read_parquet(picks_path)
    df_state = pd.read_parquet(state_path)
    df_players = pd.read_parquet(players_path)
    
    # Map player_id to position_id
    player_pos_map = df_players.set_index("id")["position_id"].to_dict()
    
    picks_list = []
    for _, row in df_picks.iterrows():
        pid = int(row["player_id"])
        picks_list.append({
            "element": pid,
            "purchase_price": int(row["purchase_price"]),
            "selling_price": int(row["selling_price"]),
            "element_type": player_pos_map.get(pid, 3)
        })
        
    state_row = df_state.iloc[0]
    
    # Transfers limit/free transfers
    limit = None if pd.isna(state_row["free_transfers"]) else int(state_row["free_transfers"])
    
    return {
        "chips": [],
        "picks": picks_list,
        "team_id": int(state_row["entry_id"]),
        "transfers": {
            "bank": int(state_row["bank"]),
            "limit": limit,
            "made": 0
        }
    }

def main() -> None:
    parser = argparse.ArgumentParser(description="Run the FPL MILP optimization solver.")
    parser.add_argument("--horizon", type=int, default=DEFAULT_PLANNING_HORIZON, help="Number of gameweeks to optimize")
    parser.add_argument("--model", type=str, help="Projections model name to use as datasource")
    parser.add_argument("--decay_base", type=float, help="Decay multiplier for later gameweeks")
    parser.add_argument("--hit_cost", type=float, help="Points cost applied to each paid transfer")
    parser.add_argument("--preseason", action="store_true", help="Solve for a blank preseason squad selection")
    parser.add_argument("--target_gw", type=int, help="Target Gameweek to start optimization from")
    args, unknown = parser.parse_known_args()
    
    # 1. Load configuration settings
    options = load_settings()
    
    # Apply CLI overrides
    options["horizon"] = args.horizon
    if args.model:
        options["datasource"] = args.model
    if args.decay_base is not None:
        options["decay_base"] = args.decay_base
    if args.hit_cost is not None:
        options["hit_cost"] = args.hit_cost
    if args.preseason:
        options["preseason"] = True
        
    try:
        _apply_dynamic_overrides(options, unknown)
    except ValueError as exc:
        parser.error(str(exc))
        
    processed_dir = PROJECT_ROOT / "data" / "processed"
    
    # Load target gameweek from processed parquet
    if args.target_gw is not None:
        target_gw = args.target_gw
    else:
        try:
            df_gw = pd.read_parquet(processed_dir / "gameweeks.parquet")
            next_gw_row = df_gw[df_gw["is_next"]]
            if not next_gw_row.empty:
                target_gw = int(next_gw_row.iloc[0]["id"])
            else:
                unfinished = df_gw[~df_gw["finished"]]
                if not unfinished.empty:
                    target_gw = int(unfinished.iloc[0]["id"])
                else:
                    target_gw = 1 if options.get("preseason", False) else 38
        except Exception:
            target_gw = 1 if options.get("preseason", False) else 38
        
    options["override_next_gw"] = target_gw

    try:
        plan = execute_transfer_plan(
            options,
            processed_dir=processed_dir,
            target_gw=target_gw,
            solution_path=PROJECT_ROOT / "data" / "solution.json",
        )
    except ValueError as exc:
        logger.error(f"Invalid chip configuration: {exc}")
        sys.exit(1)
    except FileNotFoundError as e:
        logger.error(e)
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to prepare or solve Transfer Plan: {e}")
        sys.exit(1)

    logger.info("Solver run complete!")
    if plan.get("summary"):
        print("\n" + "="*50)
        print("RECOMMENDED SQUAD & TRANSFER PLAN")
        print("="*50)
        print(plan["summary"])
        print("="*50 + "\n")

if __name__ == "__main__":
    main()
