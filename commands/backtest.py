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
from features.builder import build_features, history_before_target
from backtesting.metrics import evaluate_predictions

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SEED_BASED_MODELS = frozenset({
    "component_baseline",
    "metrics_component_hybrid",
    "participation_state_hybrid",
})
LEDGER_COMPONENTS = (
    "xp_minutes",
    "xp_goals",
    "xp_assists",
    "xp_clean_sheet",
    "xp_conceded",
    "xp_saves",
    "xp_penalties_saved",
    "xp_penalties_missed",
    "xp_own_goals",
    "xp_yellow_cards",
    "xp_red_cards",
    "xp_defcon",
    "xp_bonus",
)


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
    evaluation_season = data_dir.parent.name
    if model_name in SEED_BASED_MODELS:
        if evaluation_season == seed_season:
            raise ValueError(
                f"{model_name} cannot use {seed_season} as both evaluation data and Prior-Season Seed"
            )
        try:
            if int(seed_season.split("-", maxsplit=1)[0]) >= int(evaluation_season.split("-", maxsplit=1)[0]):
                raise ValueError(
                    f"{model_name} Prior-Season Seed {seed_season} must precede evaluation season "
                    f"{evaluation_season}"
                )
        except ValueError as exc:
            if "must precede" in str(exc):
                raise
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
    parser.add_argument(
        "--minutes_breakdown",
        action="store_true",
        help="Print expected-minutes error split by actual appearance outcome",
    )
    parser.add_argument(
        "--snapshot_root",
        type=str,
        default=None,
        help="Availability snapshot root for point-in-time package resolution",
    )
    parser.add_argument(
        "--season",
        type=str,
        default=None,
        help="Season directory name for availability snapshot resolution",
    )
    parser.add_argument(
        "--state_recency_decay",
        type=float,
        default=None,
        help="Participation-state historical weight per elapsed Gameweek",
    )
    parser.add_argument(
        "--state_prior_strength",
        type=float,
        default=None,
        help="Participation-state prior pseudo-observations",
    )
    parser.add_argument(
        "--require_snapshots",
        action="store_true",
        help="Require verified immutable pre-deadline snapshots for every evaluated Gameweek",
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
    snapshot_root = Path(args.snapshot_root).resolve() if args.snapshot_root else None
    snapshot_season = args.season or (
        data_dir.parent.name if data_dir.parent.name != "data" else None
    )
    gameweek_deadlines = {}
    gameweeks_path = data_dir / "gameweeks.parquet"
    if gameweeks_path.exists():
        gameweeks = pd.read_parquet(gameweeks_path)
        if {"id", "deadline_time"}.issubset(gameweeks.columns):
            gameweek_deadlines = gameweeks.set_index("id")["deadline_time"].to_dict()
    if args.require_snapshots:
        if snapshot_root is None or not args.season:
            logger.error("--require_snapshots requires --snapshot_root and --season.")
            sys.exit(1)
        missing_deadlines = [gw for gw in range(start_gw, end_gw + 1) if gw not in gameweek_deadlines]
        if missing_deadlines:
            logger.error("Missing deadline metadata for Gameweeks: %s", missing_deadlines)
            sys.exit(1)
    
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
    snapshot_ids: dict[int, str] = {}
    
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
                availability_snapshot_root=snapshot_root,
                season=snapshot_season,
                target_deadline=gameweek_deadlines.get(gw),
                require_availability_snapshot=args.require_snapshots,
                **{
                    key: value
                    for key, value in {
                        "state_recency_decay": args.state_recency_decay,
                        "state_prior_strength": args.state_prior_strength,
                    }.items()
                    if value is not None
                },
            )
        except Exception as e:
            if args.require_snapshots:
                logger.error("Point-in-time backtest cannot evaluate GW %s: %s", gw, e)
                sys.exit(1)
            logger.warning(f"Skipping GW {gw} because feature construction failed: {e}")
            continue
            
        if df_feat.empty:
            if args.require_snapshots:
                logger.error("Point-in-time backtest cannot evaluate empty GW %s.", gw)
                sys.exit(1)
            logger.warning(f"Skipping GW {gw} because feature dataframe is empty.")
            continue
        if args.require_snapshots:
            snapshot_id = df_feat["availability_snapshot_id"].iloc[0]
            if pd.isna(snapshot_id) or not df_feat["has_availability_snapshot"].all():
                logger.error("Point-in-time backtest cannot verify the snapshot for GW %s.", gw)
                sys.exit(1)
            snapshot_ids[gw] = str(snapshot_id)
            
        if hasattr(model, "fit"):
            model.fit(
                history_before_target(
                    df_perf,
                    gw,
                    gameweek_deadlines.get(gw),
                    args.require_snapshots,
                )
            )

        # 2. Predict target gameweek points (fixture grain)
        df_proj = model.predict(df_feat, horizon=1)
        comp_cols = [c for c in LEDGER_COMPONENTS if c in df_proj.columns]
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
            gw_perf["actual_xp_saves"] = np.where(pos_series == "GK", _col("saves") // 3, 0.0)
            gw_perf["actual_xp_penalties_saved"] = 5.0 * _col("penalties_saved")
            gw_perf["actual_xp_penalties_missed"] = -2.0 * _col("penalties_missed")
            gw_perf["actual_xp_own_goals"] = -2.0 * _col("own_goals")
            gw_perf["actual_xp_yellow_cards"] = -1.0 * _col("yellow_cards")
            gw_perf["actual_xp_red_cards"] = -3.0 * _col("red_cards")
            gw_perf["actual_xp_bonus"] = _col("bonus") * 1.0

            defcon_count = _col("defensive_contribution")
            defcon_threshold = np.where(pos_series == "D", 10, 12)
            gw_perf["actual_xp_defcon"] = np.where(
                pos_series.isin(["D", "M", "F"]) & (defcon_count >= defcon_threshold),
                2.0,
                0.0,
            )

        actual_group_cols = ["total_points", "minutes"] + [
            f"actual_{component}" for component in LEDGER_COMPONENTS
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
    if snapshot_ids:
        print(f"Snapshots       : {'; '.join(f'GW{gw}={snapshot_id}' for gw, snapshot_id in snapshot_ids.items())}")
    else:
        print("Snapshots       : none (exploratory only; not eligible for promotion)")
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
        print("-" * 67)
        spearman_str = f"{metrics['spearman']:+.4f}" if metrics.get("spearman") is not None else "N/A"
        top15_str = f"{metrics['top_15_overlap']:.4f}" if metrics.get("top_15_overlap") is not None else "N/A"
        print(f"Ranking Metrics    : Spearman Rank Corr = {spearman_str} | Top-15 Overlap = {top15_str}")
        print("=" * 67 + "\n")

    if args.minutes_breakdown and metrics.get("minutes_forecast_metrics"):
        minutes_m = metrics["minutes_forecast_metrics"]
        print("=" * 82)
        print("EXPECTED-MINUTES BREAKDOWN")
        print("=" * 82)
        print(
            f"Overall: projected={minutes_m['mean_projected']:.2f} "
            f"actual={minutes_m['mean_actual']:.2f} "
            f"MAE={minutes_m['mae']:.2f} "
            f"bias={minutes_m['bias']:+.2f} "
            f"RMSE={minutes_m['rmse']:.2f}"
        )
        print("-" * 82)
        print(
            f"{'Actual outcome':<16} {'Samples':>9} {'Mean proj':>12} "
            f"{'Mean act':>10} {'MAE':>10} {'Bias':>10}"
        )
        print("-" * 82)
        for band in ("0", "1-59", "60+"):
            band_m = minutes_m["by_actual_band"].get(band)
            if band_m is None:
                continue
            print(
                f"{band:<16} "
                f"{int(band_m['sample_count']):>9} "
                f"{band_m['mean_projected']:>12.2f} "
                f"{band_m['mean_actual']:>10.2f} "
                f"{band_m['mae']:>10.2f} "
                f"{band_m['bias']:>+10.2f}"
            )
        print("=" * 82 + "\n")
    
if __name__ == "__main__":
    main()
