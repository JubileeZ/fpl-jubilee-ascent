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
from backtesting.metrics import evaluate_predictions

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _archive_processed_candidates(data_dir: Path) -> list[Path]:
    archive_root = data_dir.parent / "archive"
    if not archive_root.exists():
        return []

    return sorted(
        (
            season_dir / "processed"
            for season_dir in archive_root.iterdir()
            if (season_dir / "processed" / "player_performances.parquet").exists()
        ),
        key=lambda candidate: candidate.parent.name,
    )


def resolve_backtest_data_dir(data_dir: Path) -> Path:
    """Use the newest processed archive when active performance data is absent."""
    if (data_dir / "player_performances.parquet").exists():
        return data_dir

    candidates = _archive_processed_candidates(data_dir)
    if candidates:
        fallback = candidates[-1]
        logger.info(
            "Active player performance data not found in %s; using archive %s",
            data_dir,
            fallback,
        )
        return fallback
    return data_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Backtest a scoring model against historical data.")
    parser.add_argument("model", type=str, help="Name of the model to backtest (e.g. linear_baseline)")
    parser.add_argument("--gw_range", type=str, default="20-30", help="Range of gameweeks to backtest on (e.g. 10-25)")
    parser.add_argument("--data_dir", type=str, default="data/processed", help="Path to processed Parquet directory")
    parser.add_argument(
        "--seed_season",
        type=str,
        default=None,
        help="Explicit prior-season archive directory name (for example 2025-26)",
    )
    args = parser.parse_args()
    
    requested_data_dir = (PROJECT_ROOT / args.data_dir).resolve()
    data_dir = resolve_backtest_data_dir(requested_data_dir)
    if not data_dir.exists():
        logger.error(
            f"Data directory {requested_data_dir} does not exist and no processed archive fallback was found. "
            "Please run snapshot_season or refresh_data first."
        )
        sys.exit(1)
        
    try:
        start_gw, end_gw = map(int, args.gw_range.split("-"))
    except ValueError:
        logger.error("Invalid gw_range format. Use StartGW-EndGW (e.g. 15-25).")
        sys.exit(1)
        
    perf_path = data_dir / "player_performances.parquet"
    if not perf_path.exists():
        logger.error(
            f"player_performances.parquet is required for backtesting in {data_dir}. "
            "Please run snapshot_season first."
        )
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
        # 1. Compile features using only pre-GW data and point-in-time-safe
        # mutable metadata. The builder keeps one row per player/fixture.
        try:
            df_feat = build_features(
                data_dir,
                target_gw=gw,
                horizon=1,
                seed_season=args.seed_season,
                as_of_gw=gw,
            )
        except Exception as e:
            logger.warning(f"Skipping GW {gw} because feature construction failed: {e}")
            continue
            
        if df_feat.empty:
            logger.warning(f"Skipping GW {gw} because feature dataframe is empty.")
            continue
            
        if hasattr(model, "fit"):
            model.fit(df_perf[df_perf["gameweek_id"] < gw])

        # 2. Predict target gameweek points (fixture grain)
        df_proj = model.predict(df_feat, horizon=1)
        df_proj_gw = (
            df_proj[df_proj["gameweek_id"] == gw]
            .groupby(["player_id", "gameweek_id"], as_index=False)[
                ["projected_points", "projected_minutes"]
            ]
            .sum()
        )

        # 3. Aggregate actual fixture rows to the same player/gameweek grain.
        df_actual_gw = (
            df_perf[df_perf["gameweek_id"] == gw]
            .groupby(["player_id", "gameweek_id"], as_index=False)[["total_points", "minutes"]]
            .sum()
            .rename(columns={"total_points": "actual_points", "minutes": "actual_minutes"})
        )

        # Include modeled players without a performance row (blank/no-fixture
        # candidates) as zero outcomes instead of silently dropping them.
        df_compare = df_proj_gw.merge(
            df_actual_gw,
            on=["player_id", "gameweek_id"],
            how="left",
        )
        df_compare[["actual_points", "actual_minutes"]] = df_compare[
            ["actual_points", "actual_minutes"]
        ].fillna(0.0)
        position_map = df_feat[["player_id", "position_id"]].drop_duplicates("player_id")
        df_compare = df_compare.merge(position_map, on="player_id", how="left")
        
        if not df_compare.empty:
            df_compare["gameweek"] = gw
            all_results.append(df_compare)
            
    if not all_results:
        logger.error("No backtesting results generated. Check if actual performance data exists for the selected range.")
        sys.exit(1)
        
    df_eval = pd.concat(all_results, ignore_index=True)
    
    metrics = evaluate_predictions(df_eval)
    mean_rank_corr = metrics["spearman"]
    rank_display = "n/a" if mean_rank_corr is None else f"{mean_rank_corr:.4f}"
    
    print("\n" + "="*50)
    print(f"BACKTESTING REPORT: {args.model.upper()}")
    print("="*50)
    print(f"Gameweek Range  : {start_gw} - {end_gw}")
    print(f"Data Directory  : {data_dir}")
    print(f"Sample Count    : {metrics['sample_count']}")
    print(f"Points MAE      : {metrics['mae']:.4f}")
    print(f"Points RMSE     : {metrics['rmse']:.4f}")
    print(f"Signed Bias     : {metrics['bias']:.4f}")
    print(f"Rank Correlation: {rank_display} (Spearman)")
    print(
        "Rank GWs        : "
        f"{metrics['valid_rank_gameweeks']} valid / "
        f"{metrics['undefined_rank_gameweeks']} undefined"
    )
    print(f"Top-11 Overlap  : {metrics['top_11_overlap']:.4f}")
    print(f"Top-15 Overlap  : {metrics['top_15_overlap']:.4f}")
    print(f"Seed Season     : {args.seed_season or 'legacy latest archive fallback'}")
    print("Availability     : point-in-time snapshot, else neutral 100% fallback")
    print("Evaluation Grain : player/gameweek (fixture rows aggregated)")
    print("="*50 + "\n")
    
if __name__ == "__main__":
    main()
