"""2025-26 matchup share add-on vs neutral ×1.0 (all positions / all fixtures).

Attack:
  xG/90' = max(0, xG/90 + share_xg × (opp xGC/90 − league xGC))
  xA/90' = max(0, xA/90 + share_xa × (opp xGC/90 − league xGC))
  Pen takers (penalties_order==1): add-on applies to open-play only (~0.15 xG/90 held out).

Defence:
  gc/90' = max(0.05, gc/90 + (opp xG/90 − league xG))   # CS / conceded λ
  saves/defcon rates × (opp xG / league xG)               # Q5 C ratio

Multipliers forced to 1.0 so Champion path does not double-scale.
"""

from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path

import numpy as np
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
from models import get_model  # noqa: E402

TOPIC = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data" / "archive" / "2025-26" / "processed"
SEED_SEASON = "2024-25"
START_GW, END_GW = 1, 38
MODEL = "participation_penalty_hybrid"
K = 10
EPS = 1e-6
PEN_XG_PER90 = 0.15

build_club_fixture_xg = _dv.build_club_fixture_xg
_blended_rate = _dv._blended_rate
apply_neutral_multipliers = _dv.apply_neutral_multipliers
_easy_mask = _dv._easy_mask


def build_club_fixture_xa(data_dir: Path) -> pd.DataFrame:
    """Club-fixture xA = Σ player expected_assists (same grain as club xG)."""
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
    merged["expected_assists"] = pd.to_numeric(
        merged["expected_assists"], errors="coerce"
    ).fillna(0.0)
    return merged.groupby(
        ["fixture_id", "club_id", "gameweek_id", "was_home"], as_index=False
    )["expected_assists"].sum()


def build_player_contrib(data_dir: Path) -> pd.DataFrame:
    """Player-fixture xG/xA for share numerators."""
    perf = pd.read_parquet(data_dir / "player_performances.parquet")
    fixtures = pd.read_parquet(data_dir / "fixtures.parquet")
    merged = perf.merge(
        fixtures[["id", "home_club_id", "away_club_id", "gameweek_id"]],
        left_on="fixture_id",
        right_on="id",
        how="inner",
        suffixes=("", "_fix"),
    )
    if "gameweek_id" not in merged.columns and "gameweek_id_fix" in merged.columns:
        merged["gameweek_id"] = merged["gameweek_id_fix"]
    merged["club_id"] = np.where(
        merged["was_home"], merged["home_club_id"], merged["away_club_id"]
    ).astype(int)
    for col in ("expected_goals", "expected_assists"):
        merged[col] = pd.to_numeric(merged[col], errors="coerce").fillna(0.0)
    return merged[
        ["player_id", "club_id", "fixture_id", "gameweek_id", "expected_goals", "expected_assists"]
    ].copy()


def _club_rates(
    by_club: dict[int, pd.DataFrame],
    club_id: int,
    is_home: bool,
    *,
    league_xg: float,
    league_xgc: float,
) -> tuple[float, float]:
    hist = by_club.get(int(club_id), pd.DataFrame())
    xg = _blended_rate(
        hist, value_col="expected_goals", is_home=is_home, k=K, league_avg=league_xg
    )
    xgc = _blended_rate(
        hist,
        value_col="expected_goals_conceded",
        is_home=is_home,
        k=K,
        league_avg=league_xgc,
    )
    return max(xg, EPS), max(xgc, EPS)


def _share_maps(
    player_contrib: pd.DataFrame,
    club_xg: pd.DataFrame,
    club_xa: pd.DataFrame,
    *,
    target_gw: int,
) -> tuple[dict[tuple[int, int], float], dict[tuple[int, int], float]]:
    """(player_id, club_id) → share of club xG / xA before target_gw."""
    p_hist = player_contrib[player_contrib["gameweek_id"] < target_gw]
    c_xg = club_xg[club_xg["gameweek_id"] < target_gw]
    c_xa = club_xa[club_xa["gameweek_id"] < target_gw]
    club_xg_tot = c_xg.groupby("club_id")["expected_goals"].sum().to_dict()
    club_xa_tot = c_xa.groupby("club_id")["expected_assists"].sum().to_dict()
    if p_hist.empty:
        return {}, {}
    player_sums = p_hist.groupby(["player_id", "club_id"], as_index=False)[
        ["expected_goals", "expected_assists"]
    ].sum()
    share_xg: dict[tuple[int, int], float] = {}
    share_xa: dict[tuple[int, int], float] = {}
    for row in player_sums.itertuples(index=False):
        key = (int(row.player_id), int(row.club_id))
        cx = float(club_xg_tot.get(int(row.club_id), 0.0))
        ca = float(club_xa_tot.get(int(row.club_id), 0.0))
        share_xg[key] = (
            float(min(max(float(row.expected_goals) / cx, 0.0), 1.0)) if cx > EPS else 0.0
        )
        share_xa[key] = (
            float(min(max(float(row.expected_assists) / ca, 0.0), 1.0)) if ca > EPS else 0.0
        )
    return share_xg, share_xa


def apply_matchup_share_addon(
    df_feat: pd.DataFrame,
    club_fixtures: pd.DataFrame,
    club_xa: pd.DataFrame,
    player_contrib: pd.DataFrame,
    *,
    target_gw: int,
) -> pd.DataFrame:
    """Neutral multipliers + rate add-ons / DEF ratio per grill design."""
    out = apply_neutral_multipliers(df_feat)
    hist_all = club_fixtures[club_fixtures["gameweek_id"] < target_gw]
    if hist_all.empty:
        return out
    league_xg = float(hist_all["expected_goals"].mean())
    league_xgc = float(hist_all["expected_goals_conceded"].mean())
    if league_xg <= 0 or league_xgc <= 0:
        return out
    by_club = {int(cid): group for cid, group in hist_all.groupby("club_id")}
    share_xg_map, share_xa_map = _share_maps(
        player_contrib, club_fixtures, club_xa, target_gw=target_gw
    )

    xg_vals: list[float] = []
    xa_vals: list[float] = []
    gc_vals: list[float] = []
    saves_vals: list[float] = []
    defcon_vals: list[float] = []

    for row in out.itertuples(index=False):
        opp_xg, opp_xgc = _club_rates(
            by_club,
            int(row.opponent_id),
            not bool(row.is_home),
            league_xg=league_xg,
            league_xgc=league_xgc,
        )
        delta_att = opp_xgc - league_xgc
        delta_def = opp_xg - league_xg
        def_scale = opp_xg / league_xg
        key = (int(row.player_id), int(row.club_id))
        share_xg = share_xg_map.get(key, 0.0)
        share_xa = share_xa_map.get(key, 0.0)

        per90_xg = float(getattr(row, "per90_xg", 0.0) or 0.0)
        per90_xa = float(getattr(row, "per90_xa", 0.0) or 0.0)
        per90_gc = float(getattr(row, "per90_goals_conceded", 1.2) or 1.2)
        per90_saves = float(getattr(row, "per90_saves", 0.0) or 0.0)
        per90_defcon = float(getattr(row, "per90_defensive_contribution", 0.0) or 0.0)
        pen_order = float(getattr(row, "penalties_order", 0.0) or 0.0)

        addon_g = share_xg * delta_att
        if pen_order == 1.0:
            open_xg = max(0.0, per90_xg - PEN_XG_PER90)
            per90_xg = max(0.0, open_xg + addon_g) + PEN_XG_PER90
        else:
            per90_xg = max(0.0, per90_xg + addon_g)

        xg_vals.append(per90_xg)
        xa_vals.append(max(0.0, per90_xa + share_xa * delta_att))
        gc_vals.append(max(0.05, per90_gc + delta_def))
        saves_vals.append(max(0.0, per90_saves * def_scale))
        defcon_vals.append(max(0.0, per90_defcon * def_scale))

    out["per90_xg"] = xg_vals
    out["per90_xa"] = xa_vals
    out["per90_goals_conceded"] = gc_vals
    out["per90_saves"] = saves_vals
    out["per90_defensive_contribution"] = defcon_vals
    return out


def _row(
    frame: pd.DataFrame, *, regime: str, slice_name: str, target_column: str
) -> dict[str, object]:
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
    deadlines = load_gameweek_deadlines(DATA_DIR)
    club_fixtures = build_club_fixture_xg(DATA_DIR)
    club_xa = build_club_fixture_xa(DATA_DIR)
    player_contrib = build_player_contrib(DATA_DIR)
    regimes = ("neutral", "matchup_share_k10")
    buckets: dict[str, list[pd.DataFrame]] = {name: [] for name in regimes}

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
        variants = {
            "neutral": apply_neutral_multipliers(df_feat),
            "matchup_share_k10": apply_matchup_share_addon(
                df_feat,
                club_fixtures,
                club_xa,
                player_contrib,
                target_gw=gw,
            ),
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
    for regime, parts in buckets.items():
        frame = pd.concat(parts, ignore_index=True)
        # Primary gate: all positions × all fixtures. easy_mid_fwd kept for ADR 0037 compare.
        for slice_name, subset in (("all", frame), ("easy_mid_fwd", frame.loc[_easy_mask(frame)])):
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
        print(
            f"{row['eval_target']} {row['regime']} {row['slice']}: "
            f"bias={row['signed_bias']:.4f} mae={row['mae']:.4f} n={row['sample_count']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
