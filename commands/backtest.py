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
from backtesting.metrics import evaluate_predictions

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SEED_BASED_MODELS = frozenset({"component_baseline", "metrics_component_hybrid"})


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


def resolve_seed_processed_dir(data_dir: Path, model_name: str, seed_season: str | None) -> Path | None:
    """Resolve an explicit, distinct prior-season seed for Cold-Start evaluation."""
    if seed_season is None:
        return None
    if model_name in SEED_BASED_MODELS and data_dir.parent.name == seed_season:
        raise ValueError(
            f"{model_name} cannot use {seed_season} as both evaluation data and Prior-Season Seed"
        )
    seed_dir = PROJECT_ROOT / "data" / "archive" / seed_season / "processed"
    if not (seed_dir / "player_performances.parquet").exists() or not (seed_dir / "players.parquet").exists():
        raise FileNotFoundError(f"Prior-season archive not found: {seed_dir}")
    return seed_dir


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
    parser.add_argument(
        "--component_breakdown",
        action="store_true",
        help="Print component-by-component error and bias breakdown table",
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
    try:
        seed_processed_dir = resolve_seed_processed_dir(data_dir, args.model, args.seed_season)
    except (FileNotFoundError, ValueError) as exc:
        logger.error(exc)
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
                seed_processed_dir=seed_processed_dir,
                use_archive_seed=False,
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
        comp_cols = [c for c in ["xp_minutes", "xp_goals", "xp_assists", "xp_clean_sheet", "xp_conceded", "xp_defcon", "xp_bonus"] if c in df_proj.columns]
        proj_group_cols = ["projected_points", "projected_minutes"] + comp_cols

        df_proj_gw = (
            df_proj[df_proj["gameweek_id"] == gw]
            .groupby(["player_id", "gameweek_id"], as_index=False)[proj_group_cols]
            .sum()
        )

        # 3. Aggregate actual fixture rows to the same player/gameweek grain.
        gw_perf = df_perf[df_perf["gameweek_id"] == gw].copy()
        if not gw_perf.empty:
            pos_map = df_feat[["player_id", "position_id"]].drop_duplicates("player_id")
            gw_perf = gw_perf.merge(pos_map, on="player_id", how="left")
            pos_codes = {1: "GK", 2: "D", 3: "M", 4: "F"}
            pos_series = gw_perf["position_id"].map(pos_codes).fillna("M")

            goal_pts_map = {"GK": 10.0, "D": 6.0, "M": 5.0, "F": 4.0}
            cs_pts_map = {"GK": 4.0, "D": 4.0, "M": 1.0, "F": 0.0}

            def _col(name: str, default: float = 0.0):
                return gw_perf[name] if name in gw_perf.columns else default

            gw_perf["actual_xp_minutes"] = np.where(_col("minutes") >= 60, 2.0, np.where(_col("minutes") > 0, 1.0, 0.0))
            gw_perf["actual_xp_goals"] = _col("goals_scored") * pos_series.map(goal_pts_map)
            gw_perf["actual_xp_assists"] = _col("assists") * 3.0
            gw_perf["actual_xp_clean_sheet"] = _col("clean_sheets") * pos_series.map(cs_pts_map)
            gw_perf["actual_xp_conceded"] = np.where(pos_series.isin(["GK", "D"]), -(_col("goals_conceded") // 2), 0.0)
            gw_perf["actual_xp_bonus"] = _col("bonus") * 1.0

            save_pts = np.where(pos_series == "GK", _col("saves") // 3, 0.0)
            card_pts = -1.0 * _col("yellow_cards") - 3.0 * _col("red_cards")
            og_pts = -2.0 * _col("own_goals")
            pen_saved = 5.0 * _col("penalties_saved")
            pen_missed = -2.0 * _col("penalties_missed")
            base_pts = (
                gw_perf["actual_xp_minutes"]
                + gw_perf["actual_xp_goals"]
                + gw_perf["actual_xp_assists"]
                + gw_perf["actual_xp_clean_sheet"]
                + gw_perf["actual_xp_conceded"]
                + gw_perf["actual_xp_bonus"]
                + save_pts
                + card_pts
                + og_pts
                + pen_saved
                + pen_missed
            )
            gw_perf["actual_xp_defcon"] = np.maximum(0.0, gw_perf["total_points"] - base_pts)

        actual_group_cols = ["total_points", "minutes"] + [
            "actual_xp_minutes", "actual_xp_goals", "actual_xp_assists",
            "actual_xp_clean_sheet", "actual_xp_conceded", "actual_xp_defcon", "actual_xp_bonus"
        ]
        actual_group_cols = [c for c in actual_group_cols if c in gw_perf.columns]

        df_actual_gw = (
            gw_perf.groupby(["player_id", "gameweek_id"], as_index=False)[actual_group_cols]
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
        fill_cols = [c for c in df_compare.columns if c.startswith("actual_") or c.startswith("xp_")]
        df_compare[fill_cols] = df_compare[fill_cols].fillna(0.0)
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
    print(f"Seed Season     : {args.seed_season or 'none (in-season evaluation)'}")
    print("Availability     : point-in-time snapshot, else Prior-Season Seed appearance probability")
    print("Evaluation Grain : player/gameweek (fixture rows aggregated)")
    print("="*50 + "\n")

    if args.component_breakdown and metrics.get("component_metrics"):
        comp_m = metrics["component_metrics"]
        print("=" * 67)
        print("COMPONENT-BY-COMPONENT ATTRIBUTION BREAKDOWN")
        print("=" * 67)
        print(f"{'Component':<18} {'Mean Proj':>10} {'Mean Act':>10} {'MAE':>10} {'Signed Bias':>12}")
        print("-" * 67)
        for comp_name, comp_data in comp_m.items():
            print(
                f"{comp_name:<18} "
                f"{comp_data['mean_projected']:>10.4f} "
                f"{comp_data['mean_actual']:>10.4f} "
                f"{comp_data['mae']:>10.4f} "
                f"{comp_data['bias']:>+12.4f}"
            )
        print("-" * 67)
        mean_proj_total = sum(c["mean_projected"] for c in comp_m.values())
        mean_act_total = sum(c["mean_actual"] for c in comp_m.values())
        print(
            f"{'Total (Components)':<18} "
            f"{mean_proj_total:>10.4f} "
            f"{mean_act_total:>10.4f} "
            f"{metrics['mae']:>10.4f} "
            f"{metrics['bias']:>+12.4f}"
        )
        print("=" * 67 + "\n")
    
if __name__ == "__main__":
    main()
