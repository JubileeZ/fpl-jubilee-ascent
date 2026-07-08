import argparse
import logging
import sys
import pandas as pd
from pathlib import Path
from tabulate import tabulate

# Set up path to include root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from clients.env_loader import load_env, configure_utf8_stdio
load_env()
configure_utf8_stdio()

from solver.utils import load_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser(description="Generate top-picks rankings report.")
    parser.add_argument("--model", type=str, help="Projections model name to rank (e.g. linear_baseline)")
    parser.add_argument("--horizon", type=int, help="Number of gameweeks to rank over")
    args = parser.parse_args()
    
    options = load_settings()
    model_name = args.model or options.get("datasource")
    horizon = args.horizon or options.get("horizon", 5)
    
    proj_csv = PROJECT_ROOT / "data" / f"{model_name}.csv"
    if not proj_csv.exists():
        logger.error(f"Projections file {proj_csv} not found. Please run run_model first.")
        sys.exit(1)
        
    df_proj = pd.read_csv(proj_csv)
    
    # Identify GW points columns
    pts_cols = [c for c in df_proj.columns if c.endswith("_Pts")]
    if not pts_cols:
        logger.error("No gameweek points columns found in projections CSV.")
        sys.exit(1)
        
    # Sort and pick the first N gameweeks based on horizon
    pts_cols = sorted(pts_cols, key=lambda x: int(x.split("_")[0]))[:horizon]
    actual_horizon = len(pts_cols)
    
    logger.info(f"Generating top-picks report for '{model_name}' over next {actual_horizon} gameweeks: {', '.join(pts_cols)}")
    
    # Calculate metrics
    df_proj["Total_xP"] = df_proj[pts_cols].sum(axis=1)
    df_proj["Value_xP"] = df_proj["Total_xP"] / df_proj["Price"].clip(lower=0.1)
    
    # Group by position and get top 5
    positions = {"G": "Goalkeepers", "D": "Defenders", "M": "Midfielders", "F": "Forwards"}
    
    df_report_list = []
    
    print("\n" + "="*70)
    print(f"TOP PICKS REPORT: {model_name.upper()} (Next {actual_horizon} GWs)")
    print("="*70)
    
    for pos_code, pos_name in positions.items():
        df_pos = df_proj[df_proj["Pos"] == pos_code].copy()
        df_pos_sorted = df_pos.sort_values(by="Total_xP", ascending=False).head(5)
        
        # Add to full report data
        df_report_list.append(df_pos)
        
        # Format table for print
        print(f"\n--- {pos_name} ---")
        headers = ["Rank", "Name", "Team", "Price (£m)", "Total xP", "Value (xP/£m)"]
        rows = []
        for rank, (_, row) in enumerate(df_pos_sorted.iterrows(), 1):
            rows.append([
                rank,
                row["Name"],
                row["Team"],
                f"£{row['Price']:.1f}m",
                f"{row['Total_xP']:.2f}",
                f"{row['Value_xP']:.2f}"
            ])
        print(tabulate(rows, headers=headers, tablefmt="grid"))
        
    print("\n" + "="*70 + "\n")
    
    # Save full report
    df_all_ranks = pd.concat(df_report_list, ignore_index=True)
    df_all_ranks = df_all_ranks.sort_values(by=["Pos", "Total_xP"], ascending=[True, False])
    
    reports_dir = PROJECT_ROOT / "data" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_csv = reports_dir / f"top_picks_{model_name}.csv"
    
    df_all_ranks[["ID", "Name", "Pos", "Price", "Team", "Total_xP", "Value_xP"]].to_csv(report_csv, index=False)
    logger.info(f"Full top picks report saved to {report_csv}")

if __name__ == "__main__":
    main()
