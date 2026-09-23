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

from solver.planning import resolve_default_target_gw
from solver.utils import load_settings
from models import resolve_model_or_champion

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def recommend_captain_vice(
    projections: pd.DataFrame,
    points_column: str,
) -> tuple[pd.Series | None, pd.Series | None]:
    """Return the top two projected players for the next gameweek."""
    if projections.empty or points_column not in projections.columns:
        return None, None

    ranked = projections.copy()
    ranked["_captain_points"] = pd.to_numeric(ranked[points_column], errors="coerce").fillna(0.0)
    ranked = ranked.sort_values("_captain_points", ascending=False, kind="stable")
    captain = ranked.iloc[0] if len(ranked) > 0 else None
    vice_captain = ranked.iloc[1] if len(ranked) > 1 else None
    return captain, vice_captain


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate top-picks rankings report.")
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Projections model name to rank (default: Champion)",
    )
    parser.add_argument(
        "--champion",
        action="store_true",
        help="Explicitly rank active Champion model projections",
    )
    parser.add_argument("--horizon", type=int, help="Number of gameweeks to rank over")
    parser.add_argument("--target_gw", type=int, help="Target Gameweek to start ranking from")
    args = parser.parse_args()
    
    options = load_settings()
    raw_model = None if args.champion else args.model
    model_name = resolve_model_or_champion(raw_model)
    horizon = args.horizon or options.get("horizon", 5)
    
    proj_csv = PROJECT_ROOT / "data" / f"{model_name}.csv"
    if not proj_csv.exists():
        logger.error(f"Projections file {proj_csv} not found. Please run run_model first.")
        sys.exit(1)
        
    df_proj = pd.read_csv(proj_csv)
    
    processed_dir = PROJECT_ROOT / "data" / "processed"
    if args.target_gw is not None:
        target_gw = args.target_gw
    elif (processed_dir / "gameweeks.parquet").exists():
        target_gw = resolve_default_target_gw(processed_dir)
    else:
        pts_cols_all = [c for c in df_proj.columns if c.endswith("_Pts")]
        gws_in_csv = sorted(int(c.split("_")[0]) for c in pts_cols_all if c.split("_")[0].isdigit())
        target_gw = gws_in_csv[0] if gws_in_csv else 1

    expected_pts_cols = [f"{gw}_Pts" for gw in range(target_gw, min(39, target_gw + horizon))]
    missing_cols = [c for c in expected_pts_cols if c not in df_proj.columns]
    if missing_cols:
        logger.error(
            f"Projections file {proj_csv.name} is missing expected columns {missing_cols}. "
            f"Please run 'python -m commands.run_model {model_name} --horizon {horizon}' first."
        )
        sys.exit(1)
        
    pts_cols = expected_pts_cols
    actual_horizon = len(pts_cols)
    next_gw_points = pts_cols[0]
    
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
    captain, vice_captain = recommend_captain_vice(df_proj, next_gw_points)
    if captain is None:
        logger.error("No players available for captain recommendation.")
        sys.exit(1)

    captain_id = captain["ID"]
    vice_captain_id = vice_captain["ID"] if vice_captain is not None else None
    df_all_ranks["Captain"] = df_all_ranks["ID"] == captain_id
    df_all_ranks["Vice_Captain"] = df_all_ranks["ID"] == vice_captain_id

    print("--- Captaincy ---")
    captain_points = float(captain["_captain_points"])
    print(
        f"Captain      : {captain['Name']} ({captain['Team']}) "
        f"{next_gw_points} xP={captain_points:.2f}, captain return={captain_points * 2:.2f}"
    )
    if vice_captain is None:
        print("Vice-Captain : n/a (fewer than two projected players)")
    else:
        vice_points = float(vice_captain["_captain_points"])
        print(
            f"Vice-Captain : {vice_captain['Name']} ({vice_captain['Team']}) "
            f"{next_gw_points} xP={vice_points:.2f}"
        )
    print()
    
    reports_dir = PROJECT_ROOT / "data" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_csv = reports_dir / f"top_picks_{model_name}.csv"
    
    df_all_ranks[
        ["ID", "Name", "Pos", "Price", "Team", "Total_xP", "Value_xP", "Captain", "Vice_Captain"]
    ].to_csv(report_csv, index=False)
    logger.info(f"Full top picks report saved to {report_csv}")

if __name__ == "__main__":
    main()
