"""Walk-forward backtest runner shared by CLI and model promotion."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from backtesting.metrics import evaluate_predictions
from features.builder import build_features, history_before_target
from models import get_model

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


@dataclass(frozen=True)
class WalkforwardConfig:
    model_name: str
    data_dir: Path
    start_gw: int
    end_gw: int
    seed_processed_dir: Path | None = None
    snapshot_root: Path | None = None
    snapshot_season: str | None = None
    require_snapshots: bool = False
    state_recency_decay: float | None = None
    state_prior_strength: float | None = None


@dataclass(frozen=True)
class WalkforwardResult:
    model_name: str
    data_dir: Path
    start_gw: int
    end_gw: int
    metrics: dict[str, Any]
    df_eval: pd.DataFrame
    snapshot_ids: dict[int, str]
    snapshot_backed: bool


def _build_actual_components(gw_perf: pd.DataFrame, df_feat: pd.DataFrame) -> pd.DataFrame:
    if gw_perf.empty:
        return gw_perf
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
    return gw_perf


def load_gameweek_deadlines(data_dir: Path) -> dict[int, Any]:
    gameweeks_path = data_dir / "gameweeks.parquet"
    if not gameweeks_path.exists():
        return {}
    gameweeks = pd.read_parquet(gameweeks_path)
    if {"id", "deadline_time"}.issubset(gameweeks.columns):
        return gameweeks.set_index("id")["deadline_time"].to_dict()
    return {}


def run_walkforward_backtest(config: WalkforwardConfig) -> WalkforwardResult:
    data_dir = config.data_dir
    perf_path = data_dir / "player_performances.parquet"
    if not perf_path.exists():
        raise FileNotFoundError(f"player_performances.parquet is required in {data_dir}")

    df_perf = pd.read_parquet(perf_path)
    gameweek_deadlines = load_gameweek_deadlines(data_dir)
    if config.require_snapshots:
        if config.snapshot_root is None or config.snapshot_season is None:
            raise ValueError("snapshot_root and snapshot_season are required when require_snapshots is enabled")
        missing_deadlines = [
            gw for gw in range(config.start_gw, config.end_gw + 1) if gw not in gameweek_deadlines
        ]
        if missing_deadlines:
            raise ValueError(f"Missing deadline metadata for Gameweeks: {missing_deadlines}")

    model = get_model(config.model_name)
    all_results: list[pd.DataFrame] = []
    snapshot_ids: dict[int, str] = {}
    feature_kwargs = {
        key: value
        for key, value in {
            "state_recency_decay": config.state_recency_decay,
            "state_prior_strength": config.state_prior_strength,
        }.items()
        if value is not None
    }

    for gw in range(config.start_gw, config.end_gw + 1):
        df_feat = build_features(
            data_dir,
            target_gw=gw,
            horizon=1,
            seed_processed_dir=config.seed_processed_dir,
            use_archive_seed=False,
            as_of_gw=gw,
            availability_snapshot_root=config.snapshot_root,
            season=config.snapshot_season,
            target_deadline=gameweek_deadlines.get(gw),
            require_availability_snapshot=config.require_snapshots,
            **feature_kwargs,
        )
        if df_feat.empty:
            if config.require_snapshots:
                raise ValueError(f"Point-in-time backtest cannot evaluate empty GW {gw}")
            continue
        if config.require_snapshots:
            snapshot_id = df_feat["availability_snapshot_id"].iloc[0]
            if pd.isna(snapshot_id) or not df_feat["has_availability_snapshot"].all():
                raise ValueError(f"Point-in-time backtest cannot verify the snapshot for GW {gw}")
            snapshot_ids[gw] = str(snapshot_id)

        if hasattr(model, "fit"):
            model.fit(
                history_before_target(
                    df_perf,
                    gw,
                    gameweek_deadlines.get(gw),
                    config.require_snapshots,
                )
            )

        df_proj = model.predict(df_feat, horizon=1)
        comp_cols = [column for column in LEDGER_COMPONENTS if column in df_proj.columns]
        proj_group_cols = ["projected_points", "projected_minutes"] + comp_cols
        df_proj_gw = (
            df_proj[df_proj["gameweek_id"] == gw]
            .groupby(["player_id", "gameweek_id"], as_index=False)[proj_group_cols]
            .sum()
        )

        gw_perf = _build_actual_components(df_perf[df_perf["gameweek_id"] == gw].copy(), df_feat)
        actual_group_cols = ["total_points", "minutes"] + [
            f"actual_{component}" for component in LEDGER_COMPONENTS
        ]
        actual_group_cols = [column for column in actual_group_cols if column in gw_perf.columns]
        df_actual_gw = (
            gw_perf.groupby(["player_id", "gameweek_id"], as_index=False)[actual_group_cols]
            .sum()
            .rename(columns={"total_points": "actual_points", "minutes": "actual_minutes"})
        )

        df_compare = df_proj_gw.merge(df_actual_gw, on=["player_id", "gameweek_id"], how="left")
        fill_cols = [column for column in df_compare.columns if column.startswith(("actual_", "xp_"))]
        df_compare[fill_cols] = df_compare[fill_cols].fillna(0.0)
        position_map = df_feat[["player_id", "position_id"]].drop_duplicates("player_id")
        df_compare = df_compare.merge(position_map, on="player_id", how="left")
        if not df_compare.empty:
            df_compare["gameweek"] = gw
            all_results.append(df_compare)

    if not all_results:
        raise ValueError("No backtesting results generated for the selected range")

    df_eval = pd.concat(all_results, ignore_index=True)
    metrics = evaluate_predictions(df_eval)
    snapshot_backed = bool(snapshot_ids) and len(snapshot_ids) == (config.end_gw - config.start_gw + 1)
    return WalkforwardResult(
        model_name=config.model_name,
        data_dir=data_dir,
        start_gw=config.start_gw,
        end_gw=config.end_gw,
        metrics=metrics,
        df_eval=df_eval,
        snapshot_ids=snapshot_ids,
        snapshot_backed=snapshot_backed,
    )
