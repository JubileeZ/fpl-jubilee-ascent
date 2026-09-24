"""Three-arm fixture-swing experiment: Champion vs adjusted-additive vs multiplicative.

Design locked 2026-09-24 (fixture-swing-candidates note): same Champion model,
different Matchup Share application per arm. Score on blend MAE primary,
realized/process MAE hold, easy_mid_fwd process bias cap +0.450, Attack Swing
Ratio diagnostic. Expected runtime ~75 min for GW1-38; GW_START/GW_END env
overrides allow a 1-GW smoke.
"""

from __future__ import annotations

import csv
import importlib.util
import os
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

_DV_PATH = ROOT / "docs/archive/dual-vector-official-xg-2025-26/runner.py"
_spec = importlib.util.spec_from_file_location("dv_xg_runner", _DV_PATH)
assert _spec is not None and _spec.loader is not None
_dv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_dv)

from backtesting.metrics import evaluate_predictions  # noqa: E402
from backtesting.process_points import aggregate_process_points, blended_points  # noqa: E402
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
START_GW = int(os.environ.get("GW_START", "1"))
END_GW = int(os.environ.get("GW_END", "38"))
MODEL = "calibrated_matchup_hybrid"
EASY_BIAS_CAP = 0.450

_easy_mask = _dv._easy_mask


def _swing(values: pd.DataFrame, col: str) -> float:
    ordered = values.sort_values(["player_id", "gameweek_id"])
    return float(
        ordered.groupby("player_id")[col].apply(lambda s: s.std(ddof=1)).mean()
    )


def main() -> int:
    df_perf = pd.read_parquet(DATA_DIR / "player_performances.parquet")
    df_fixtures = pd.read_parquet(DATA_DIR / "fixtures.parquet")
    deadlines = load_gameweek_deadlines(DATA_DIR)
    seed_dir = resolve_seed_processed_dir(DATA_DIR, MODEL, SEED_SEASON)

    arms: dict[str, dict[str, Any]] = {
        "champion": {"shrink_att": 0.40, "shrink_def": 0.40},
        "additive_adjusted": {"shrink_att": 0.60, "shrink_def": 0.40},
        "multiplicative": {
            "shrink_att": 0.40,
            "shrink_def": 0.40,
            "attack_scale": "ratio",
        },
    }
    buckets: dict[str, list[pd.DataFrame]] = {arm: [] for arm in arms}

    for gw in range(START_GW, END_GW + 1):
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

        for arm, overlay_kwargs in arms.items():
            feat, _ = apply_matchup_share_overlay(
                df_base,
                df_perf,
                df_fixtures,
                history_cutoff_gw=gw,
                **overlay_kwargs,
            )
            df_proj = assert_projection_contract(model.predict(feat, horizon=1))
            comp_cols = [c for c in LEDGER_COMPONENTS if c in df_proj.columns]
            df_proj_gw = (
                df_proj[df_proj["gameweek_id"] == gw]
                .groupby(["player_id", "gameweek_id"], as_index=False)[
                    ["projected_points", "projected_minutes", *comp_cols]
                ]
                .sum()
            )
            gw_perf = _build_actual_components(
                df_perf[df_perf["gameweek_id"] == gw].copy(), feat
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
            position_map = feat[["player_id", "position_id"]].drop_duplicates("player_id")
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
            df_compare["blended_points"] = blended_points(
                df_compare["actual_points"], df_compare["process_points"]
            )
            df_compare["gameweek"] = gw
            buckets[arm].append(df_compare)
        print(f"GW{gw} done", flush=True)

    rows: list[dict[str, object]] = []
    for arm, parts in buckets.items():
        frame = pd.concat(parts, ignore_index=True)
        reg60 = frame[frame["actual_minutes"] >= 60]
        atk = reg60[reg60["position_id"].isin([3, 4])].copy()
        atk["xp_attack"] = atk["xp_goals"] + atk["xp_assists"]
        attack_swing = _swing(atk, "xp_attack") / _swing(atk, "process_points")
        easy = frame.loc[_easy_mask(frame)]
        if easy.empty:
            easy_bias: object = ""
            easy_mae: object = ""
        else:
            easy_process = evaluate_predictions(easy, target_column="process_points")
            easy_bias = round(float(easy_process["bias"]), 4)
            easy_mae = round(float(easy_process["mae"]), 4)
        blend = evaluate_predictions(frame, target_column="blended_points")
        realized = evaluate_predictions(frame, target_column="actual_points")
        process = evaluate_predictions(frame, target_column="process_points")
        rows.append(
            {
                "arm": arm,
                "sample_count": int(len(frame)),
                "blend_mae": round(float(blend["mae"]), 4),
                "blend_bias": round(float(blend["bias"]), 4),
                "realized_mae": round(float(realized["mae"]), 4),
                "process_mae": round(float(process["mae"]), 4),
                "easy_bias": easy_bias,
                "easy_mae": easy_mae,
                "xp_swing_60": round(_swing(reg60, "projected_points"), 4),
                "attack_swing": round(float(attack_swing), 4),
            }
        )
        print(
            f"{arm:<20}: blend_mae={rows[-1]['blend_mae']} easy_bias={rows[-1]['easy_bias']:+} "
            f"attack_swing={rows[-1]['attack_swing']} n={rows[-1]['sample_count']}",
            flush=True,
        )

    out = TOPIC / "candidate_swing_summary.csv"
    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
