import argparse
import logging
import sys
import numpy as np
import pandas as pd
from pathlib import Path

# Set up path to include root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from clients.env_loader import load_env, configure_utf8_stdio
load_env()
configure_utf8_stdio()

from models import get_model
from features.builder import build_features

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser(description="Backtest a scoring model against historical data.")
    parser.add_argument("model", type=str, help="Name of the model to backtest (e.g. linear_baseline)")
    parser.add_argument("--gw_range", type=str, default="20-30", help="Range of gameweeks to backtest on (e.g. 10-25)")
    parser.add_argument("--data_dir", type=str, default="data/processed", help="Path to processed Parquet directory")
    args = parser.parse_args()
    
    data_dir = PROJECT_ROOT / args.data_dir
    if not data_dir.exists():
        logger.error(f"Data directory {data_dir} does not exist. Please run snapshot_season or refresh_data first.")
        sys.exit(1)
        
    try:
        start_gw, end_gw = map(int, args.gw_range.split("-"))
    except ValueError:
        logger.error("Invalid gw_range format. Use StartGW-EndGW (e.g. 15-25).")
        sys.exit(1)
        
    perf_path = data_dir / "player_performances.parquet"
    if not perf_path.exists():
        logger.error("player_performances.parquet is required for backtesting. Please run snapshot_season first.")
        sys.exit(1)
        
    df_perf = pd.read_parquet(perf_path)
    
    # Instantiate model
    try:
        model = get_model(args.model)
    except Exception as e:
        logger.error(e)
        sys.exit(1)
        
    logger.info(f"Starting backtesting for model '{args.model}' on GW {start_gw} to {end_gw}...")
    
    all_results = []
    
    for gw in range(start_gw, end_gw + 1):
        logger.info(f"Running backtest for Gameweek {gw}...")
        # 1. Compile features using only pre-gw data (builder.py automatically handles df_perf[df_perf['gameweek_id'] < gw])
        try:
            df_feat = build_features(data_dir, target_gw=gw)
        except Exception as e:
            logger.warning(f"Skipping GW {gw} because feature construction failed: {e}")
            continue
            
        if df_feat.empty:
            logger.warning(f"Skipping GW {gw} because feature dataframe is empty.")
            continue
            
        # 2. Predict next gameweek points (horizon=1)
        df_proj = model.predict(df_feat, horizon=1)
        # We only look at predictions for the current target gw
        df_proj_gw = df_proj[df_proj["gameweek_id"] == gw]
        
        # 3. Load actual points for this gw
        df_actual_gw = df_perf[df_perf["gameweek_id"] == gw][["player_id", "total_points", "minutes"]]
        df_actual_gw = df_actual_gw.rename(columns={"total_points": "actual_points", "minutes": "actual_minutes"})
        
        # Merge predictions and actuals
        df_compare = df_proj_gw.merge(df_actual_gw, on="player_id", how="inner")
        
        if not df_compare.empty:
            df_compare["gameweek"] = gw
            all_results.append(df_compare)
            
    if not all_results:
        logger.error("No backtesting results generated. Check if actual performance data exists for the selected range.")
        sys.exit(1)
        
    df_eval = pd.concat(all_results, ignore_index=True)
    
    # Calculate metrics
    errors_points = df_eval["projected_points"] - df_eval["actual_points"]
    mae = np.mean(np.abs(errors_points))
    rmse = np.sqrt(np.mean(errors_points ** 2))
    
    # Rank correlation per gameweek
    correlations = []
    for gw, group in df_eval.groupby("gameweek"):
        if len(group) > 1:
            corr = group["projected_points"].corr(group["actual_points"], method="spearman")
            if not np.isnan(corr):
                correlations.append(corr)
    mean_rank_corr = np.mean(correlations) if correlations else 0.0
    
    print("\n" + "="*50)
    print(f"BACKTESTING REPORT: {args.model.upper()}")
    print("="*50)
    print(f"Gameweek Range  : {start_gw} - {end_gw}")
    print(f"Sample Count    : {len(df_eval)}")
    print(f"Points MAE      : {mae:.4f}")
    print(f"Points RMSE     : {rmse:.4f}")
    print(f"Rank Correlation: {mean_rank_corr:.4f} (Spearman)")
    print("="*50 + "\n")
    
if __name__ == "__main__":
    main()
