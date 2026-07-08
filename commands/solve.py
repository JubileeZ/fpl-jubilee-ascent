import argparse
import logging
import sys
import pandas as pd
from pathlib import Path

# Set up path to include root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from clients.env_loader import load_env, configure_utf8_stdio
load_env()
configure_utf8_stdio()

from solver.utils import load_settings
from solver.solver import prep_data, solve_multi_period_fpl
from solver.visualization import create_squad_timeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]

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

def main():
    parser = argparse.ArgumentParser(description="Run the FPL MILP optimization solver.")
    parser.add_argument("--horizon", type=int, help="Number of gameweeks to optimize")
    parser.add_argument("--model", type=str, help="Projections model name to use as datasource")
    parser.add_argument("--preseason", action="store_true", help="Solve for a blank preseason squad selection")
    args, unknown = parser.parse_known_args()
    
    # 1. Load configuration settings
    options = load_settings()
    
    # Apply CLI overrides
    if args.horizon:
        options["horizon"] = args.horizon
    if args.model:
        options["datasource"] = args.model
    if args.preseason:
        options["preseason"] = True
        
    # Apply dynamic unknown argument overrides (e.g. --xmin_lb=0 or --xmin_lb 0)
    # Re-parse unknown args as key-value pairs
    i = 0
    while i < len(unknown):
        arg = unknown[i]
        if arg.startswith("--"):
            key = arg[2:]
            val = None
            if "=" in key:
                key, val = key.split("=", 1)
            elif i + 1 < len(unknown) and not unknown[i+1].startswith("--"):
                val = unknown[i+1]
                i += 1
                
            if val is not None:
                # Convert type if numeric/boolean
                if val.lower() in ["true", "false"]:
                    options[key] = val.lower() == "true"
                elif val.isdigit():
                    options[key] = int(val)
                else:
                    try:
                        options[key] = float(val)
                    except ValueError:
                        options[key] = val
        i += 1
        
    processed_dir = PROJECT_ROOT / "data" / "processed"
    
    # Load target gameweek from processed parquet
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
                target_gw = 38
    except Exception:
        target_gw = 38
        
    options["override_next_gw"] = target_gw
    
    # 2. Compile user team data
    if options.get("preseason", False):
        logger.info(f"Solving for Preseason starting from GW {target_gw}...")
        my_data = {"picks": [], "chips": [], "transfers": {"limit": None, "cost": 4, "bank": 1000, "value": 0}}
    else:
        logger.info("Loading current squad picks and state from processed Parquet...")
        try:
            my_data = build_my_data_from_parquet(processed_dir)
        except Exception as e:
            logger.error(e)
            sys.exit(1)
            
    logger.info(f"Preparing solver data using projections from '{options['datasource']}.csv'...")
    try:
        solver_data = prep_data(my_data, options)
    except Exception as e:
        logger.error(f"Failed to prepare solver data: {e}")
        sys.exit(1)
        
    logger.info("Executing MILP solver...")
    solutions = solve_multi_period_fpl(solver_data, options)
    logger.info("Solver run complete!")
    
    if solutions and isinstance(solutions, list):
        best_sol = solutions[0]
        if "summary" in best_sol:
            print("\n" + "="*50)
            print("RECOMMENDED SQUAD & TRANSFER PLAN")
            print("="*50)
            print(best_sol["summary"])
            print("="*50 + "\n")
            
        if "picks" in best_sol and "statistics" in best_sol:
            try:
                model_name = options.get("datasource", "model")
                filename_base = f"squad_timeline_{model_name}"
                expected_filepath = PROJECT_ROOT / "data" / "images" / f"{filename_base}.png"
                
                initial_squad = [] if options.get("preseason") else [p["element"] for p in my_data.get("picks", [])]
                
                logger.info("Generating visual squad timeline plot...")
                create_squad_timeline(
                    current_squad=initial_squad,
                    statistics=best_sol["statistics"],
                    picks=best_sol["picks"],
                    filename=filename_base
                )
                logger.info(f"Visual squad timeline saved to {expected_filepath}")
            except Exception as e:
                logger.error(f"Failed to generate squad timeline plot: {e}")

if __name__ == "__main__":
    main()
