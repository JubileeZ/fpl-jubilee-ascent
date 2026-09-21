"""2025-26 Dual-Vector vs participation under Club Strength vs forced FDR multipliers."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from backtesting.metrics import evaluate_predictions  # noqa: E402
from backtesting.walkforward import (  # noqa: E402
    LEDGER_COMPONENTS,
    _build_actual_components,
    load_gameweek_deadlines,
)
from commands.backtest import resolve_seed_processed_dir  # noqa: E402
from features.builder import build_features, history_before_target  # noqa: E402
from features.contracts import assert_projection_contract  # noqa: E402
from models import get_model  # noqa: E402

TOPIC = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data" / "archive" / "2025-26" / "processed"
SEED_SEASON = "2024-25"
START_GW = 1
END_GW = 38
MODELS = ("participation_penalty_hybrid", "participation_state_hybrid")
EASY_DIFF_MAX = 2.0
EASY_XMINS_MIN = 60.0
EASY_POSITION_IDS = (3, 4)  # MID, FWD


def apply_fdr_fallback_multipliers(df_feat: pd.DataFrame) -> pd.DataFrame:
    """Overwrite multipliers with live 2026-27 path: Modified FDR formula, clamp 0.4–1.8."""
    out = df_feat.copy()
    difficulty = out["difficulty"].astype(float)
    out["attack_multiplier"] = ((6.0 - difficulty) / 3.0).clip(lower=0.4, upper=1.8)
    out["defence_multiplier"] = (difficulty / 3.0).clip(lower=0.4, upper=1.8)
    return out


def _summarize(frame: pd.DataFrame, *, model: str, regime: str, slice_name: str) -> dict[str, object]:
    metrics = evaluate_predictions(frame)
    return {
        "model": model,
        "multiplier_regime": regime,
        "slice": slice_name,
        "evaluation_season": "2025-26",
        "gw_start": START_GW,
        "gw_end": END_GW,
        "seed_season": SEED_SEASON,
        "sample_count": int(len(frame)),
        "signed_bias": float((frame["projected_points"] - frame["actual_points"]).mean()),
        "mae": float(metrics["mae"]),
        "rmse": float(metrics["rmse"]),
        "minutes_bias": float(metrics["minutes_forecast_metrics"]["bias"]),
        "snapshot_backed": "false",
    }


def _easy_mask(frame: pd.DataFrame) -> pd.Series:
    return (
        (frame["difficulty"] <= EASY_DIFF_MAX)
        & (frame["position_id"].isin(EASY_POSITION_IDS))
        & (frame["projected_minutes"] >= EASY_XMINS_MIN)
    )


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def run() -> list[dict[str, object]]:
    if not (DATA_DIR / "player_performances.parquet").exists():
        raise FileNotFoundError(f"missing archive: {DATA_DIR}")
    seed_dir = resolve_seed_processed_dir(DATA_DIR, "participation_state_hybrid", SEED_SEASON)
    df_perf = pd.read_parquet(DATA_DIR / "player_performances.parquet")
    deadlines = load_gameweek_deadlines(DATA_DIR)

    buckets: dict[tuple[str, str], list[pd.DataFrame]] = {
        (model, regime): [] for model in MODELS for regime in ("club_strength", "fdr_fallback")
    }

    for gw in range(START_GW, END_GW + 1):
        df_feat = build_features(
            DATA_DIR,
            target_gw=gw,
            horizon=1,
            seed_processed_dir=seed_dir,
            use_archive_seed=False,
            as_of_gw=gw,
            target_deadline=deadlines.get(gw),
        )
        if df_feat.empty:
            continue
        feat_by_regime = {
            "club_strength": df_feat,
            "fdr_fallback": apply_fdr_fallback_multipliers(df_feat),
        }
        difficulty_map = (
            df_feat.groupby(["player_id", "gameweek_id"], as_index=False)["difficulty"]
            .mean()
            .rename(columns={"difficulty": "difficulty"})
        )

        for model_name in MODELS:
            model = get_model(model_name)
            if hasattr(model, "fit"):
                model.fit(history_before_target(df_perf, gw, deadlines.get(gw), False))
            for regime, features in feat_by_regime.items():
                df_proj = model.predict(features, horizon=1)
                assert_projection_contract(df_proj)
                comp_cols = [c for c in LEDGER_COMPONENTS if c in df_proj.columns]
                proj_group_cols = ["projected_points", "projected_minutes"] + comp_cols
                df_proj_gw = (
                    df_proj[df_proj["gameweek_id"] == gw]
                    .groupby(["player_id", "gameweek_id"], as_index=False)[proj_group_cols]
                    .sum()
                )
                gw_perf = _build_actual_components(df_perf[df_perf["gameweek_id"] == gw].copy(), features)
                actual_group_cols = ["total_points", "minutes"] + [
                    f"actual_{c}" for c in LEDGER_COMPONENTS
                ]
                actual_group_cols = [c for c in actual_group_cols if c in gw_perf.columns]
                df_actual_gw = (
                    gw_perf.groupby(["player_id", "gameweek_id"], as_index=False)[actual_group_cols]
                    .sum()
                    .rename(columns={"total_points": "actual_points", "minutes": "actual_minutes"})
                )
                df_compare = df_proj_gw.merge(df_actual_gw, on=["player_id", "gameweek_id"], how="left")
                fill_cols = [c for c in df_compare.columns if c.startswith(("actual_", "xp_"))]
                df_compare[fill_cols] = df_compare[fill_cols].fillna(0.0)
                position_map = features[["player_id", "position_id"]].drop_duplicates("player_id")
                df_compare = df_compare.merge(position_map, on="player_id", how="left")
                df_compare = df_compare.merge(difficulty_map, on=["player_id", "gameweek_id"], how="left")
                df_compare["gameweek"] = gw
                buckets[(model_name, regime)].append(df_compare)

    summary_rows: list[dict[str, object]] = []
    for (model_name, regime), parts in buckets.items():
        frame = pd.concat(parts, ignore_index=True)
        summary_rows.append(_summarize(frame, model=model_name, regime=regime, slice_name="all"))
        easy = frame.loc[_easy_mask(frame)].copy()
        if easy.empty:
            summary_rows.append(
                {
                    "model": model_name,
                    "multiplier_regime": regime,
                    "slice": "easy_mid_fwd",
                    "evaluation_season": "2025-26",
                    "gw_start": START_GW,
                    "gw_end": END_GW,
                    "seed_season": SEED_SEASON,
                    "sample_count": 0,
                    "signed_bias": "",
                    "mae": "",
                    "rmse": "",
                    "minutes_bias": "",
                    "snapshot_backed": "false",
                }
            )
        else:
            summary_rows.append(
                _summarize(frame=easy, model=model_name, regime=regime, slice_name="easy_mid_fwd")
            )
    return summary_rows


def main() -> int:
    rows = run()
    out = TOPIC / "model_regime_summary.csv"
    _write_csv(out, rows)
    print(f"Wrote {out}")
    for row in rows:
        print(
            f"{row['model']} {row['multiplier_regime']} {row['slice']}: "
            f"signed_bias={row['signed_bias']} mae={row['mae']} n={row['sample_count']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
