"""Walk-forward backtest runner shared by CLI and model promotion."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from backtesting.metrics import evaluate_dual_pool_event_metrics, evaluate_predictions
from backtesting.process_points import aggregate_process_points, blended_points
from backtesting.season_rules import get_rules
from features.builder import build_features, history_before_target
from features.contracts import assert_projection_contract
from models import get_model
from models.native_scoring_context import native_scoring_context
from models.participation_state_hybrid import ORACLE_STATE_COLUMNS
from models.scoring_matrix import event_points

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
# 2024-25 Assistant Manager elements (position 5) score team results outside the player ledger.
PLAYER_POSITIONS = (1, 2, 3, 4)


@dataclass(frozen=True)
class WalkforwardConfig:
    model_name: str
    data_dir: Path
    start_gw: int
    end_gw: int
    seed_processed_dir: Path | None = None
    seed_season: str | None = None
    snapshot_root: Path | None = None
    snapshot_season: str | None = None
    require_snapshots: bool = False
    state_recency_decay: float | None = None
    state_prior_strength: float | None = None
    trailing_start_k: int | None = None
    trailing_start_weight: float | None = None
    eval_target: str = "actual_points"  # actual_points | process_points | blended_points
    blend_weight: float = 0.5  # Process share of Blended Eval Target (ADR 0044)
    oracle_minutes: bool = False


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
    rules_version = native_scoring_context(df_feat)
    if gw_perf.empty:
        return gw_perf
    pos_map = df_feat[["player_id", "position_id"]].drop_duplicates("player_id")
    gw_perf = gw_perf.merge(pos_map, on="player_id", how="left")
    if rules_version is not None:
        required = ["total_points", "minutes", "goals_scored", "assists", "clean_sheets", "goals_conceded", "saves", "penalties_saved", "penalties_missed", "own_goals", "yellow_cards", "red_cards", "bonus"]
        if get_rules(rules_version).defensive_contributions:
            required.append("defensive_contribution")
        if not gw_perf["position_id"].isin(PLAYER_POSITIONS).all():
            raise ValueError("Unknown native actual position")
        for column in required:
            if column not in gw_perf:
                raise ValueError("Missing native actual component")
            values = pd.to_numeric(gw_perf[column], errors="coerce")
            if values.isna().any() or not np.isfinite(values).all():
                raise ValueError("Invalid native actual component")
            gw_perf[column] = values
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
    if rules_version is not None:
        gw_perf["actual_xp_goals"] = [event_points("goals", pos, float(q), rules_version=rules_version) for pos, q in zip(pos_series, gw_perf["goals_scored"], strict=True)]
        gw_perf["actual_xp_defcon"] = [event_points("defensive_contributions", pos, float(q) / 2, rules_version=rules_version) for pos, q in zip(pos_series, gw_perf["actual_xp_defcon"], strict=True)]
    return gw_perf


def extract_realized_participation_states(df_perf: pd.DataFrame, target_gw: int) -> pd.DataFrame:
    """Derive deduplicated fixture-grain realized participation outcomes for ``target_gw``."""
    gw_perf = df_perf[df_perf["gameweek_id"] == target_gw].drop_duplicates(
        subset=["player_id", "gameweek_id", "fixture_id"]
    )
    mins = pd.to_numeric(gw_perf["minutes"], errors="coerce").fillna(0.0).clip(lower=0.0)
    if "starts" in gw_perf.columns:
        starts_num = pd.to_numeric(gw_perf["starts"], errors="coerce")
        started = np.where(starts_num.notna(), (starts_num == 1) & (mins > 0.0), mins >= 60.0)
    else:
        started = (mins >= 60.0).to_numpy()
    mins_arr = mins.to_numpy(dtype=float)
    return pd.DataFrame({
        "player_id": gw_perf["player_id"].to_numpy(),
        "gameweek_id": gw_perf["gameweek_id"].to_numpy(),
        "fixture_id": gw_perf["fixture_id"].to_numpy(),
        "minutes": mins_arr,
        "started": started.astype(float),
        "sub_in": ((~started) & (mins_arr > 0.0)).astype(float),
        "dnp": (mins_arr <= 0.0).astype(float),
        "p_60": (mins_arr >= 60.0).astype(float),
    })


def inject_oracle_participation_state(
    df_feat: pd.DataFrame,
    df_perf: pd.DataFrame,
    target_gw: int,
) -> pd.DataFrame:
    """Inject fixture-grain realized Oracle Participation State into ``df_feat``."""
    df_feat = df_feat.copy()
    realized = extract_realized_participation_states(df_perf, target_gw)
    oracle_table = realized.rename(
        columns={
            "started": "oracle_p_start",
            "sub_in": "oracle_p_sub_in",
            "dnp": "oracle_p_dnp",
            "minutes": "oracle_minutes",
            "p_60": "oracle_p_60",
        }
    )
    drop_cols = [c for c in ("external_xmins", *ORACLE_STATE_COLUMNS) if c in df_feat.columns]
    if drop_cols:
        df_feat = df_feat.drop(columns=drop_cols)
    df_feat = df_feat.merge(
        oracle_table,
        on=["player_id", "gameweek_id", "fixture_id"],
        how="left",
    )
    blank_mask = df_feat["fixture_id"].isna() | (pd.to_numeric(df_feat["fixture_id"], errors="coerce").fillna(-1) < 0)
    defaults = {
        "oracle_p_start": 0.0,
        "oracle_p_sub_in": 0.0,
        "oracle_p_dnp": 1.0,
        "oracle_minutes": 0.0,
        "oracle_p_60": 0.0,
    }
    for col, val in defaults.items():
        df_feat[col] = pd.to_numeric(df_feat[col], errors="coerce").fillna(val).astype(float)
        if blank_mask.any():
            df_feat.loc[blank_mask, col] = val
    df_feat.attrs["oracle_participation_state"] = True
    df_feat.attrs["oracle_minutes"] = True
    return df_feat


def inject_oracle_minutes(
    df_feat: pd.DataFrame,
    df_perf: pd.DataFrame,
    target_gw: int,
) -> pd.DataFrame:
    """Inject realized fixture-grain Oracle Participation State into ``df_feat``."""
    return inject_oracle_participation_state(df_feat, df_perf, target_gw)


def _assert_oracle_participation_parity(
    df_feat: pd.DataFrame,
    df_proj: pd.DataFrame,
    target_gw: int,
    *,
    atol: float = 1e-6,
) -> None:
    """Assert projected_minutes and xp_minutes match fixture-grain Oracle Participation State."""
    feat_gw = df_feat[df_feat["gameweek_id"] == target_gw]
    proj_gw = df_proj[df_proj["gameweek_id"] == target_gw]
    join_keys = (
        ["player_id", "gameweek_id", "fixture_id"]
        if "fixture_id" in proj_gw.columns
        else ["player_id", "gameweek_id"]
    )
    if join_keys == ["player_id", "gameweek_id"]:
        exp_df = feat_gw[join_keys].copy()
        mins_col = feat_gw["oracle_minutes"].to_numpy(dtype=float)
        exp_df["expected_xp_minutes"] = np.where(mins_col >= 60.0, 2.0, np.where(mins_col > 0.0, 1.0, 0.0))
        expected = pd.concat(
            [
                feat_gw.groupby(join_keys, as_index=False)["oracle_minutes"].sum(),
                exp_df.groupby(join_keys, as_index=False)["expected_xp_minutes"].sum()[["expected_xp_minutes"]],
            ],
            axis=1,
        )
    else:
        expected = feat_gw[[*join_keys, "oracle_minutes"]].copy()
        expected["expected_xp_minutes"] = np.where(
            expected["oracle_minutes"] >= 60.0,
            2.0,
            np.where(expected["oracle_minutes"] > 0.0, 1.0, 0.0),
        )
    merged = expected.merge(proj_gw, on=join_keys, how="inner")
    if len(merged) != len(expected):
        raise ValueError(f"Oracle Participation State parity mismatch: missing rows at GW {target_gw}")
    mins_diff = np.abs(merged["projected_minutes"].to_numpy(dtype=float) - merged["oracle_minutes"].to_numpy(dtype=float))
    if mins_diff.size and float(np.max(mins_diff)) > atol:
        raise ValueError(
            f"Oracle Participation State parity breach on projected_minutes at GW {target_gw}: max diff {float(np.max(mins_diff)):.6g}"
        )
    if "xp_minutes" in merged.columns:
        xp_diff = np.abs(merged["xp_minutes"].to_numpy(dtype=float) - merged["expected_xp_minutes"].to_numpy(dtype=float))
        if xp_diff.size and float(np.max(xp_diff)) > atol:
            raise ValueError(
                f"Oracle Participation State parity breach on xp_minutes at GW {target_gw}: max diff {float(np.max(xp_diff)):.6g}"
            )


def load_gameweek_deadlines(data_dir: Path) -> dict[int, Any]:
    gameweeks_path = data_dir / "gameweeks.parquet"
    if not gameweeks_path.exists():
        return {}
    gameweeks = pd.read_parquet(gameweeks_path)
    if {"id", "deadline_time"}.issubset(gameweeks.columns):
        return gameweeks.set_index("id")["deadline_time"].to_dict()
    return {}


def _resolve_walkforward_seed_dir(data_dir: Path, seed_season: str) -> Path:
    resolved = data_dir.resolve()
    candidates = [
        resolved.parents[1] / seed_season / "processed",
        resolved.parent / "archive" / seed_season / "processed",
        Path(__file__).resolve().parents[1] / "data" / "archive" / seed_season / "processed",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        f"Prior-season archive not found for seed_season '{seed_season}'"
    )


def _default_seed_season_for_data_dir(data_dir: Path, snapshot_season: str | None) -> str | None:
    season = snapshot_season or (data_dir.parent.name if data_dir.parent.name != "data" else None)
    if season == "2024-25":
        try:
            cand = _resolve_walkforward_seed_dir(data_dir, "2023-24")
            if cand.exists():
                return "2023-24"
        except FileNotFoundError:
            pass
    return None


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
            "trailing_start_k": config.trailing_start_k,
            "trailing_start_weight": config.trailing_start_weight,
        }.items()
        if value is not None
    }

    seed_season = config.seed_season
    if seed_season is None and config.seed_processed_dir is None:
        seed_season = _default_seed_season_for_data_dir(data_dir, config.snapshot_season)

    seed_processed_dir = config.seed_processed_dir
    if seed_processed_dir is None and seed_season:
        seed_processed_dir = _resolve_walkforward_seed_dir(data_dir, seed_season)

    for gw in range(config.start_gw, config.end_gw + 1):
        df_feat = build_features(
            data_dir,
            target_gw=gw,
            horizon=1,
            seed_processed_dir=seed_processed_dir,
            use_archive_seed=False,
            as_of_gw=gw,
            availability_snapshot_root=config.snapshot_root,
            season=config.snapshot_season,
            target_deadline=gameweek_deadlines.get(gw),
            require_availability_snapshot=config.require_snapshots,
            **feature_kwargs,
        )
        df_feat = df_feat[df_feat["position_id"].isin(PLAYER_POSITIONS)] if "position_id" in df_feat.columns else df_feat
        if config.oracle_minutes:
            df_feat = inject_oracle_minutes(df_feat, df_perf, gw)
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
        assert_projection_contract(df_proj)
        if config.oracle_minutes:
            _assert_oracle_participation_parity(df_feat, df_proj, gw)
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
        meta_cols = [c for c in ["player_id", "position_id", "now_cost", "club_id"] if c in df_feat.columns]
        player_meta = df_feat[meta_cols].drop_duplicates("player_id")
        df_compare = df_compare.merge(player_meta, on="player_id", how="left")
        process_gw = aggregate_process_points(gw_perf)
        df_compare = df_compare.merge(process_gw, on=["player_id", "gameweek_id"], how="left")
        df_compare["process_points"] = df_compare["process_points"].fillna(0.0)
        if not df_compare.empty:
            df_compare["gameweek"] = gw
            all_results.append(df_compare)

    if not all_results:
        raise ValueError("No backtesting results generated for the selected range")

    df_eval = pd.concat(all_results, ignore_index=True)
    target = config.eval_target
    if target not in {"actual_points", "process_points", "blended_points"}:
        raise ValueError(f"Unsupported eval_target: {target}")
    if target == "blended_points":
        df_eval["blended_points"] = blended_points(
            df_eval["actual_points"], df_eval["process_points"], weight=config.blend_weight
        )
    metrics = evaluate_predictions(df_eval, target_column=target)
    if config.oracle_minutes:
        metrics["oracle_formation_xi_regret"] = metrics.get("formation_xi_regret")
        metrics["oracle_captain_regret"] = metrics.get("captain_regret")
        metrics["oracle_minutes_enabled"] = True
        metrics["oracle_participation_state_enabled"] = True
        metrics["oracle_event_pools"] = evaluate_dual_pool_event_metrics(
            df_eval,
            target_column=target,
            all_players_formation_regret=metrics.get("formation_xi_regret"),
            all_players_captain_regret=metrics.get("captain_regret"),
        )
    else:
        metrics["oracle_minutes_enabled"] = False
        metrics["oracle_participation_state_enabled"] = False
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
