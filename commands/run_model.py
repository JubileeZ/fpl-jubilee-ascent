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

from models import get_model
from features.builder import build_features
from projections.exporter import export_projections

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser(description="Run a scoring model to generate score projections.")
    parser.add_argument("model", type=str, help="Name of the model to run (e.g. linear_baseline)")
    parser.add_argument("--horizon", type=int, default=5, help="Number of gameweeks to predict ahead")
    args = parser.parse_args()
    
    processed_dir = PROJECT_ROOT / "data" / "processed"
    if not processed_dir.exists():
        logger.error("No processed data found. Please run 'python -m commands.refresh_data' first.")
        sys.exit(1)
        
    # Load gameweeks to determine next GW
    try:
        df_gw = pd.read_parquet(processed_dir / "gameweeks.parquet")
        # Find next gameweek (is_next=True or first unfinished)
        next_gw_row = df_gw[df_gw["is_next"]]
        if not next_gw_row.empty:
            target_gw = int(next_gw_row.iloc[0]["id"])
        else:
            unfinished = df_gw[~df_gw["finished"]]
            if not unfinished.empty:
                target_gw = int(unfinished.iloc[0]["id"])
            else:
                target_gw = 38 # fallback
    except Exception as e:
        logger.warning(f"Failed to load gameweeks, falling back to GW 38: {e}")
        target_gw = 38
        
    logger.info(f"Generating projections starting from target Gameweek {target_gw}...")
    
    # 1. Build features for target gw
    logger.info("Building features...")
    df_feat = build_features(processed_dir, target_gw)
    
    # 2. Instantiate and run model
    logger.info(f"Loading model '{args.model}'...")
    try:
        model = get_model(args.model)
    except Exception as e:
        logger.error(e)
        sys.exit(1)
        
    logger.info("Generating predictions...")
    df_proj = model.predict(df_feat, args.horizon)
    
    # 3. Export to CSV
    output_csv = PROJECT_ROOT / "data" / f"{args.model}.csv"
    logger.info(f"Exporting projections to {output_csv}...")
    df_players = pd.read_parquet(processed_dir / "players.parquet")
    df_clubs = pd.read_parquet(processed_dir / "clubs.parquet")
    export_projections(df_proj, df_players, df_clubs, output_csv)
    
    logger.info("Projections successfully generated!")

if __name__ == "__main__":
    main()
