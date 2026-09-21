"""2025-26 Official FPL Dual-Vector multipliers vs Club Strength / neutral / raw FDR."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

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
from models import get_model  # noqa: E402

TOPIC = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data" / "archive" / "2025-26" / "processed"
SEED_SEASON = "2024-25"
START_GW, END_GW = 1, 38
MODEL = "participation_penalty_hybrid"
EASY_DIFF_MAX = 2.0
EASY_XMINS_MIN = 60.0
EASY_POSITION_IDS = (3, 4)
K_VALUES = (6, 10)
EPS = 1e-6


def build_club_fixture_xg(data_dir: Path) -> pd.DataFrame:
    """Official FPL club-fixture xG (Σ expected_goals) and xGC (max among ≥60′)."""
    perf = pd.read_parquet(data_dir / "player_performances.parquet")
    fixtures = pd.read_parquet(data_dir / "fixtures.parquet")
    merged = perf.merge(
        fixtures[["id", "home_club_id", "away_club_id"]],
        left_on="fixture_id",
        right_on="id",
        how="inner",
    )
    merged["club_id"] = np.where(
        merged["was_home"], merged["home_club_id"], merged["away_club_id"]
    ).astype(int)
    merged["expected_goals"] = pd.to_numeric(merged["expected_goals"], errors="coerce").fillna(0.0)
    merged["expected_goals_conceded"] = pd.to_numeric(
        merged["expected_goals_conceded"], errors="coerce"
    ).fillna(0.0)
    xg = merged.groupby(
        ["fixture_id", "club_id", "gameweek_id", "was_home"], as_index=False
    )["expected_goals"].sum()
    full = merged[merged["minutes"] >= 60]
    xgc = (
        full.groupby(["fixture_id", "club_id"], as_index=False)["expected_goals_conceded"]
        .max()
        .rename(columns={"expected_goals_conceded": "expected_goals_conceded"})
    )
    return xg.merge(xgc, on=["fixture_id", "club_id"], how="left")


def _blended_rate(
    history: pd.DataFrame,
    *,
    value_col: str,
    is_home: bool,
    k: int,
    league_avg: float,
) -> float:
    """0.5·all + 0.5·venue, then w·mix + (1−w)·league_avg with w=min(1, n/K)."""
    if history.empty or league_avg <= 0:
        return float(league_avg) if league_avg > 0 else 1.0
    hist = history.sort_values("gameweek_id").tail(k)
    n = len(hist)
    w = min(1.0, n / float(k))
    rate_all = float(hist[value_col].mean())
    venue = hist[hist["was_home"] == is_home]
    rate_venue = float(venue[value_col].mean()) if not venue.empty else rate_all
    rate_mix = 0.5 * rate_all + 0.5 * rate_venue
    return w * rate_mix + (1.0 - w) * float(league_avg)


def apply_dual_vector_multipliers(
    df_feat: pd.DataFrame,
    club_fixtures: pd.DataFrame,
    *,
    target_gw: int,
    k: int,
) -> pd.DataFrame:
    """Overwrite attack/defence multipliers with Official FPL Dual-Vector ratios."""
    out = df_feat.copy()
    hist_all = club_fixtures[club_fixtures["gameweek_id"] < target_gw]
    if hist_all.empty:
        out["attack_multiplier"] = 1.0
        out["defence_multiplier"] = 1.0
        return out
    league_xg = float(hist_all["expected_goals"].mean())
    league_xgc = float(hist_all["expected_goals_conceded"].mean())
    if league_xg <= 0 or league_xgc <= 0:
        out["attack_multiplier"] = 1.0
        out["defence_multiplier"] = 1.0
        return out

    by_club = {int(cid): g for cid, g in hist_all.groupby("club_id")}

    def strengths(club_id: int, is_home: bool) -> tuple[float, float]:
        hist = by_club.get(int(club_id), pd.DataFrame())
        xg = _blended_rate(
            hist, value_col="expected_goals", is_home=is_home, k=k, league_avg=league_xg
        )
        xgc = _blended_rate(
            hist,
            value_col="expected_goals_conceded",
            is_home=is_home,
            k=k,
            league_avg=league_xgc,
        )
        attack_str = xg / league_xg
        defence_str = league_xgc / max(xgc, EPS)
        return attack_str, defence_str

    attack_vals: list[float] = []
    defence_vals: list[float] = []
    for row in out.itertuples(index=False):
        team_att, team_def = strengths(int(row.club_id), bool(row.is_home))
        opp_att, opp_def = strengths(int(row.opponent_id), not bool(row.is_home))
        attack_vals.append(float(np.clip(team_att / max(opp_def, EPS), 0.4, 1.8)))
        defence_vals.append(float(np.clip(opp_att / max(team_def, EPS), 0.4, 1.8)))
    out["attack_multiplier"] = attack_vals
    out["defence_multiplier"] = defence_vals
    return out


def apply_raw_fdr_multipliers(df_feat: pd.DataFrame) -> pd.DataFrame:
    out = df_feat.copy()
    difficulty = out["difficulty"].astype(float)
    out["attack_multiplier"] = ((6.0 - difficulty) / 3.0).clip(lower=0.4, upper=1.8)
    out["defence_multiplier"] = (difficulty / 3.0).clip(lower=0.4, upper=1.8)
    return out


def apply_neutral_multipliers(df_feat: pd.DataFrame) -> pd.DataFrame:
    out = df_feat.copy()
    out["attack_multiplier"] = 1.0
    out["defence_multiplier"] = 1.0
    return out


def _easy_mask(frame: pd.DataFrame) -> pd.Series:
    return (
        (frame["difficulty"] <= EASY_DIFF_MAX)
        & (frame["position_id"].isin(EASY_POSITION_IDS))
        & (frame["projected_minutes"] >= EASY_XMINS_MIN)
    )


def _row(
    frame: pd.DataFrame,
    *,
    regime: str,
    slice_name: str,
    target_column: str,
) -> dict[str, object]:
    metrics = evaluate_predictions(frame, target_column=target_column)
    return {
        "model": MODEL,
        "multiplier_regime": regime,
        "slice": slice_name,
        "eval_target": "process" if target_column == "process_points" else "realized",
        "evaluation_season": "2025-26",
        "gw_start": START_GW,
        "gw_end": END_GW,
        "seed_season": SEED_SEASON,
        "sample_count": int(len(frame)),
        "signed_bias": float((frame["projected_points"] - frame[target_column]).mean()),
        "mae": float(metrics["mae"]),
        "rmse": float(metrics["rmse"]),
        "snapshot_backed": "false",
    }


def run() -> list[dict[str, object]]:
    seed_dir = resolve_seed_processed_dir(DATA_DIR, "participation_state_hybrid", SEED_SEASON)
    df_perf = pd.read_parquet(DATA_DIR / "player_performances.parquet")
    deadlines = load_gameweek_deadlines(DATA_DIR)
    club_fixtures = build_club_fixture_xg(DATA_DIR)

    regimes = (
        ["club_strength", "neutral", "raw_fdr"]
        + [f"dual_vector_k{k}" for k in K_VALUES]
    )
    buckets: dict[str, list[pd.DataFrame]] = {r: [] for r in regimes}

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
        difficulty_map = df_feat.groupby(["player_id", "gameweek_id"], as_index=False)[
            "difficulty"
        ].mean()
        model = get_model(MODEL)
        model.fit(history_before_target(df_perf, gw, deadlines.get(gw), False))

        variants: dict[str, pd.DataFrame] = {
            "club_strength": df_feat,
            "neutral": apply_neutral_multipliers(df_feat),
            "raw_fdr": apply_raw_fdr_multipliers(df_feat),
        }
        for k in K_VALUES:
            variants[f"dual_vector_k{k}"] = apply_dual_vector_multipliers(
                df_feat, club_fixtures, target_gw=gw, k=k
            )

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
            df_compare = df_compare.merge(
                features[["player_id", "position_id"]].drop_duplicates("player_id"),
                on="player_id",
                how="left",
            )
            df_compare = df_compare.merge(
                difficulty_map, on=["player_id", "gameweek_id"], how="left"
            )
            process_src = df_perf[df_perf["gameweek_id"] == gw].merge(
                features[["player_id", "position_id"]].drop_duplicates("player_id"),
                on="player_id",
                how="left",
            )
            process_gw = aggregate_process_points(process_src)
            df_compare = df_compare.merge(
                process_gw, on=["player_id", "gameweek_id"], how="left"
            )
            df_compare["process_points"] = df_compare["process_points"].fillna(0.0)
            df_compare["gameweek"] = gw
            buckets[regime].append(df_compare)

    rows: list[dict[str, object]] = []
    for regime, parts in buckets.items():
        frame = pd.concat(parts, ignore_index=True)
        for slice_name, subset in (
            ("all", frame),
            ("easy_mid_fwd", frame.loc[_easy_mask(frame)]),
        ):
            for target in ("actual_points", "process_points"):
                rows.append(
                    _row(
                        subset,
                        regime=regime,
                        slice_name=slice_name,
                        target_column=target,
                    )
                )
    return rows


def main() -> int:
    rows = run()
    out = TOPIC / "dual_vector_xg_summary.csv"
    with out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {out}")
    for row in rows:
        print(
            f"{row['eval_target']} {row['multiplier_regime']} {row['slice']}: "
            f"bias={row['signed_bias']:.4f} mae={row['mae']:.4f} n={row['sample_count']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
