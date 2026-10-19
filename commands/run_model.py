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

from models import get_model, resolve_model_or_champion
from features.builder import (
    build_features,
    load_fit_history,
    resolve_operational_processed_dir,
)
from features.contracts import assert_projection_contract
from projections.exporter import export_projections
from solver.planning import SEASON_END_GW, resolve_default_target_gw

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]

def generate_model_projections(
    model_name: str,
    target_gw: int,
    horizon: int,
    *,
    xmins_override: Path | str | None = None,
    output_name: str | None = None,
    processed_dir: Path | None = None,
    **feature_kwargs,
) -> Path:
    """Generate model predictions and export solver-ready projections CSV."""
    root = PROJECT_ROOT
    if processed_dir is None:
        processed_dir = resolve_operational_processed_dir(root)
    if not (processed_dir / "players.parquet").exists():
        raise FileNotFoundError("No processed data found. Please run 'python -m commands.refresh_data' first.")

    kwargs = dict(feature_kwargs)
    if xmins_override is not None:
        path = Path(xmins_override)
        kwargs["xmins_override"] = path if path.is_absolute() else root / path

    logger.info(f"Building features for {model_name} (horizon {horizon}, GW{target_gw})...")
    df_feat = build_features(
        processed_dir,
        target_gw,
        horizon=horizon,
        history_before_gw=SEASON_END_GW + 1,
        **kwargs,
    )

    resolved_model = resolve_model_or_champion(model_name)
    logger.info(f"Loading model '{resolved_model}'...")
    model = get_model(resolved_model)
    if hasattr(model, "fit"):
        fit_history = load_fit_history(processed_dir, target_gw)
        if fit_history is not None:
            model.fit(fit_history)

    logger.info("Generating predictions...")
    df_proj = assert_projection_contract(model.predict(df_feat, horizon))

    output_stem = output_name or resolved_model
    output_csv = root / "data" / f"{output_stem}.csv"
    logger.info(f"Exporting projections to {output_csv}...")
    df_players = pd.read_parquet(processed_dir / "players.parquet")
    df_clubs = pd.read_parquet(processed_dir / "clubs.parquet")
    export_projections(df_proj, df_players, df_clubs, output_csv)
    logger.info("Projections successfully generated!")
    return output_csv


def main():
    parser = argparse.ArgumentParser(description="Run a scoring model to generate score projections.")
    parser.add_argument(
        "model",
        type=str,
        nargs="?",
        default=None,
        help="Name of the model to run (default: Champion)",
    )
    parser.add_argument(
        "--model",
        type=str,
        dest="model_flag",
        default=None,
        help="Explicit model name (overrides positional)",
    )
    parser.add_argument(
        "--champion",
        action="store_true",
        help="Explicitly run the active Champion model",
    )
    parser.add_argument("--horizon", type=int, default=5, help="Number of gameweeks to predict ahead")
    parser.add_argument(
        "--xmins_override",
        "--xmins-override",
        type=Path,
        default=None,
        dest="xmins_override",
        help="Optional CSV of external player xMins predictions",
    )
    parser.add_argument(
        "--output_name",
        "--output-name",
        type=str,
        default=None,
        dest="output_name",
        help="Optional custom stem for data/<stem>.csv export",
    )

    parser.add_argument(
        "--blend_start_appearances",
        type=int,
        help="Appearances before current-season rates enter the blend (default: 1)",
    )
    parser.add_argument(
        "--blend_full_appearances",
        type=int,
        help="Appearances at which current-season rates fully replace the seed (default: 5)",
    )
    parser.add_argument(
        "--state_recency_decay",
        type=float,
        help="Participation-state historical weight per elapsed Gameweek (default: 0.95)",
    )
    parser.add_argument(
        "--state_prior_strength",
        type=float,
        help="Participation-state prior pseudo-observations (default: 1)",
    )
    parser.add_argument(
        "--availability_overrides",
        type=Path,
        default=Path("data/availability_overrides.csv"),
        help="Optional CSV of source-attributed, expiring player xMins caps",
    )
    parser.add_argument(
        "--target_gw",
        type=int,
        help="Target Gameweek to start projections from (default: next unfinished GW or GW1)",
    )
    args = parser.parse_args()
    
    processed_dir = resolve_operational_processed_dir(PROJECT_ROOT)
    if not (processed_dir / "players.parquet").exists():
        logger.error("No processed data found. Please run 'python -m commands.refresh_data' first.")
        sys.exit(1)
        
    target_gw = (
        args.target_gw
        if args.target_gw is not None
        else resolve_default_target_gw(processed_dir)
    )
        
    raw_model = None if args.champion else (args.model_flag or args.model)
    model_name = resolve_model_or_champion(raw_model)

    availability_overrides = args.availability_overrides
    if not availability_overrides.is_absolute():
        availability_overrides = PROJECT_ROOT / availability_overrides
    feature_kwargs = {
        key: value
        for key, value in {
            "blend_start_appearances": args.blend_start_appearances,
            "blend_full_appearances": args.blend_full_appearances,
            "state_recency_decay": args.state_recency_decay,
            "state_prior_strength": args.state_prior_strength,
            "availability_overrides": availability_overrides,
        }.items()
        if value is not None
    }

    try:
        generate_model_projections(
            model_name=model_name,
            target_gw=target_gw,
            horizon=args.horizon,
            xmins_override=args.xmins_override,
            output_name=args.output_name,
            processed_dir=processed_dir,
            **feature_kwargs,
        )
    except Exception as exc:
        logger.error(exc)
        sys.exit(1)

if __name__ == "__main__":
    main()
