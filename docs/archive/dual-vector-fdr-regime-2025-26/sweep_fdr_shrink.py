"""Sweep FDR-fallback shrink toward 1.0 on 2025-26 (research only)."""

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
START_GW, END_GW = 1, 38
MODEL = "participation_penalty_hybrid"
EASY_DIFF_MAX = 2.0
EASY_XMINS_MIN = 60.0
EASY_POSITION_IDS = (3, 4)
# 1.0 = current raw FDR; 0.0 = neutral 1.0 multipliers
SHRINKS = (1.0, 0.5, 0.35, 0.25, 0.0)


def apply_fdr_shrink(df_feat: pd.DataFrame, shrink: float) -> pd.DataFrame:
    out = df_feat.copy()
    difficulty = out["difficulty"].astype(float)
    raw_attack = ((6.0 - difficulty) / 3.0).clip(lower=0.4, upper=1.8)
    raw_defence = (difficulty / 3.0).clip(lower=0.4, upper=1.8)
    out["attack_multiplier"] = (1.0 + (raw_attack - 1.0) * shrink).clip(lower=0.4, upper=1.8)
    out["defence_multiplier"] = (1.0 + (raw_defence - 1.0) * shrink).clip(lower=0.4, upper=1.8)
    return out


def _easy_mask(frame: pd.DataFrame) -> pd.Series:
    return (
        (frame["difficulty"] <= EASY_DIFF_MAX)
        & (frame["position_id"].isin(EASY_POSITION_IDS))
        & (frame["projected_minutes"] >= EASY_XMINS_MIN)
    )


def _row(frame: pd.DataFrame, *, shrink: float | str, slice_name: str) -> dict[str, object]:
    metrics = evaluate_predictions(frame)
    return {
        "model": MODEL,
        "fdr_fallback_shrink": shrink,
        "slice": slice_name,
        "sample_count": int(len(frame)),
        "signed_bias": float((frame["projected_points"] - frame["actual_points"]).mean()),
        "mae": float(metrics["mae"]),
    }


def main() -> int:
    seed_dir = resolve_seed_processed_dir(DATA_DIR, "participation_state_hybrid", SEED_SEASON)
    df_perf = pd.read_parquet(DATA_DIR / "player_performances.parquet")
    deadlines = load_gameweek_deadlines(DATA_DIR)
    buckets: dict[object, list[pd.DataFrame]] = {s: [] for s in ("club_strength", *SHRINKS)}

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
        difficulty_map = df_feat.groupby(["player_id", "gameweek_id"], as_index=False)["difficulty"].mean()
        model = get_model(MODEL)
        model.fit(history_before_target(df_perf, gw, deadlines.get(gw), False))

        variants: dict[object, pd.DataFrame] = {"club_strength": df_feat}
        for shrink in SHRINKS:
            variants[shrink] = apply_fdr_shrink(df_feat, shrink)

        for key, features in variants.items():
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
            gw_perf = _build_actual_components(df_perf[df_perf["gameweek_id"] == gw].copy(), features)
            actual_cols = ["total_points", "minutes"] + [f"actual_{c}" for c in LEDGER_COMPONENTS]
            actual_cols = [c for c in actual_cols if c in gw_perf.columns]
            df_actual = (
                gw_perf.groupby(["player_id", "gameweek_id"], as_index=False)[actual_cols]
                .sum()
                .rename(columns={"total_points": "actual_points", "minutes": "actual_minutes"})
            )
            df_compare = df_proj_gw.merge(df_actual, on=["player_id", "gameweek_id"], how="left")
            fill = [c for c in df_compare.columns if c.startswith(("actual_", "xp_"))]
            df_compare[fill] = df_compare[fill].fillna(0.0)
            df_compare = df_compare.merge(
                features[["player_id", "position_id"]].drop_duplicates("player_id"),
                on="player_id",
                how="left",
            )
            df_compare = df_compare.merge(difficulty_map, on=["player_id", "gameweek_id"], how="left")
            df_compare["gameweek"] = gw
            buckets[key].append(df_compare)

    rows: list[dict[str, object]] = []
    for key, parts in buckets.items():
        frame = pd.concat(parts, ignore_index=True)
        shrink_label: float | str = key if key != "club_strength" else "club_strength"
        rows.append(_row(frame, shrink=shrink_label, slice_name="all"))
        easy = frame.loc[_easy_mask(frame)]
        rows.append(_row(easy, shrink=shrink_label, slice_name="easy_mid_fwd"))

    out = TOPIC / "fdr_fallback_shrink_sweep.csv"
    with out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {out}")
    for row in rows:
        print(
            f"shrink={row['fdr_fallback_shrink']} {row['slice']}: "
            f"bias={row['signed_bias']:.4f} mae={row['mae']:.4f} n={row['sample_count']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
