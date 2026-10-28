"""2025-26 calibrated matchup share add-on vs neutral ×1.0 and shrinkage variants.

Evaluates:
- neutral: x1.0 multipliers
- matchup_share_k10: production calibrated s=0.40 with Bayesian positional priors
- matchup_share_s030: s=0.30
- matchup_share_s050: s=0.50
- matchup_share_unshrunk: s=1.0 (historical comparison)

Slices evaluated across all positions (all, easy_mid_fwd, GK, DEF, MID, FWD, easy_def_gk).
"""

from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

_DV_PATH = ROOT / "docs/archive/dual-vector-official-xg-2025-26/runner.py"
_spec = importlib.util.spec_from_file_location("dv_xg_runner", _DV_PATH)
assert _spec is not None and _spec.loader is not None
_dv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_dv)

from backtesting.metrics import evaluate_predictions  # noqa: E402
from backtesting.process_points import aggregate_process_points  # noqa: E402
from backtesting.walkforward import (  # noqa: E402
    LEDGER_COMPONENTS,
    _build_actual_components,
    load_gameweek_deadlines,
)
from commands.backtest import resolve_seed_processed_dir  # noqa: E402
from features.builder import build_features, history_before_target  # noqa: E402
from features.contracts import assert_projection_contract  # noqa: E402
from features.matchup_share import apply_matchup_share_overlay  # noqa: E402
from models import get_model  # noqa: E402

TOPIC = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data" / "archive" / "2025-26" / "processed"
SEED_SEASON = "2024-25"
START_GW, END_GW = 1, 38
MODEL = "calibrated_matchup_hybrid"

apply_neutral_multipliers = _dv.apply_neutral_multipliers
_easy_mask = _dv._easy_mask


def _easy_def_gk_mask(frame: pd.DataFrame) -> pd.Series:
    return (
        (frame["difficulty"] <= 2.0)
        & (frame["position_id"].isin([1, 2]))
        & (frame["projected_minutes"] >= 60.0)
    )


def _row(
    frame: pd.DataFrame, *, regime: str, slice_name: str, target_column: str
) -> dict[str, object]:
    if frame.empty:
        return {
            "model": MODEL,
            "regime": regime,
            "slice": slice_name,
            "eval_target": "process" if target_column == "process_points" else "realized",
            "sample_count": 0,
            "signed_bias": 0.0,
            "mae": 0.0,
        }
    metrics = evaluate_predictions(frame, target_column=target_column)
    return {
        "model": MODEL,
        "regime": regime,
        "slice": slice_name,
        "eval_target": "process" if target_column == "process_points" else "realized",
        "sample_count": int(len(frame)),
        "signed_bias": float((frame["projected_points"] - frame[target_column]).mean()),
        "mae": float(metrics["mae"]),
    }


def run() -> list[dict[str, object]]:
    seed_dir = resolve_seed_processed_dir(DATA_DIR, "participation_state_hybrid", SEED_SEASON)
    df_perf = pd.read_parquet(DATA_DIR / "player_performances.parquet")
    df_fixtures = pd.read_parquet(DATA_DIR / "fixtures.parquet")
    deadlines = load_gameweek_deadlines(DATA_DIR)

    regimes = ("neutral", "matchup_share_k10", "matchup_share_s030", "matchup_share_s050")
    buckets: dict[str, list[pd.DataFrame]] = {name: [] for name in regimes}

    for gw in range(START_GW, END_GW + 1):
        # Build pure base features without pre-applied overlay
        df_base = build_features(
            DATA_DIR,
            target_gw=gw,
            horizon=1,
            seed_processed_dir=seed_dir,
            use_archive_seed=False,
            as_of_gw=gw,
            target_deadline=deadlines.get(gw),
            apply_matchup_share=False,
        )
        if df_base.empty:
            continue

        difficulty_map = df_base.groupby(["player_id", "gameweek_id"], as_index=False)[
            "difficulty"
        ].mean()
        model = get_model(MODEL)
        model.fit(history_before_target(df_perf, gw, deadlines.get(gw), False))

        feat_neutral = apply_neutral_multipliers(df_base)
        feat_k10, _ = apply_matchup_share_overlay(
            df_base, df_perf, df_fixtures, history_cutoff_gw=gw, shrink_att=0.40, shrink_def=0.40
        )
        feat_s030, _ = apply_matchup_share_overlay(
            df_base, df_perf, df_fixtures, history_cutoff_gw=gw, shrink_att=0.30, shrink_def=0.30
        )
        feat_s050, _ = apply_matchup_share_overlay(
            df_base, df_perf, df_fixtures, history_cutoff_gw=gw, shrink_att=0.50, shrink_def=0.50
        )

        variants = {
            "neutral": feat_neutral,
            "matchup_share_k10": feat_k10,
            "matchup_share_s030": feat_s030,
            "matchup_share_s050": feat_s050,
        }

        for regime, features in variants.items():
            df_proj = model.predict(features, horizon=1)
            assert_projection_contract(df_proj)
            comp_cols = [c for c in LEDGER_COMPONENTS if c in df_proj.columns]
            df_proj_gw = (
                df_proj[df_proj["gameweek_id"] == gw]
                .groupby(["player_id", "gameweek_id"], as_index=False)[
                    ["projected_points", "projected_minutes", *comp_cols]
                ]
                .sum()
            )
            gw_perf = _build_actual_components(
                df_perf[df_perf["gameweek_id"] == gw].copy(), features
            )
            actual_cols = ["total_points", "minutes"] + [
                f"actual_{c}" for c in LEDGER_COMPONENTS
            ]
            actual_cols = [c for c in actual_cols if c in gw_perf.columns]
            df_actual = (
                gw_perf.groupby(["player_id", "gameweek_id"], as_index=False)[actual_cols]
                .sum()
                .rename(columns={"total_points": "actual_points", "minutes": "actual_minutes"})
            )
            df_compare = df_proj_gw.merge(
                df_actual, on=["player_id", "gameweek_id"], how="left"
            )
            fill = [c for c in df_compare.columns if c.startswith(("actual_", "xp_"))]
            df_compare[fill] = df_compare[fill].fillna(0.0)
            position_map = features[["player_id", "position_id"]].drop_duplicates("player_id")
            df_compare = df_compare.merge(position_map, on="player_id", how="left")
            df_compare = df_compare.merge(
                difficulty_map, on=["player_id", "gameweek_id"], how="left"
            )
            process_src = df_perf[df_perf["gameweek_id"] == gw].merge(
                position_map, on="player_id", how="left"
            )
            df_compare = df_compare.merge(
                aggregate_process_points(process_src),
                on=["player_id", "gameweek_id"],
                how="left",
            )
            df_compare["process_points"] = df_compare["process_points"].fillna(0.0)
            df_compare["gameweek"] = gw
            buckets[regime].append(df_compare)

    rows: list[dict[str, object]] = []
    slices = [
        ("all", lambda f: f),
        ("easy_mid_fwd", lambda f: f.loc[_easy_mask(f)]),
        ("easy_def_gk", lambda f: f.loc[_easy_def_gk_mask(f)]),
        ("DEF", lambda f: f[f["position_id"] == 2]),
        ("MID", lambda f: f[f["position_id"] == 3]),
        ("FWD", lambda f: f[f["position_id"] == 4]),
    ]
    for regime, parts in buckets.items():
        frame = pd.concat(parts, ignore_index=True)
        for slice_name, filter_fn in slices:
            subset = filter_fn(frame)
            for target in ("actual_points", "process_points"):
                rows.append(
                    _row(subset, regime=regime, slice_name=slice_name, target_column=target)
                )
    return rows


def main() -> int:
    rows = run()
    out = TOPIC / "matchup_share_summary.csv"
    with out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {out}")
    for row in rows:
        if row["slice"] in ("all", "easy_mid_fwd", "easy_def_gk"):
            print(
                f"{row['eval_target'][:4]} {row['regime']:<18} {row['slice']:<12}: "
                f"bias={row['signed_bias']:+.4f} mae={row['mae']:.4f} n={row['sample_count']}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
