"""2025-26 team-λ Poisson multipliers vs Club Strength and neutral ×1.0."""

from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

_DV_PATH = (
    ROOT
    / "docs/archive/dual-vector-official-xg-2025-26/runner.py"
)
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

build_club_fixture_xg = _dv.build_club_fixture_xg
_blended_rate = _dv._blended_rate
apply_neutral_multipliers = _dv.apply_neutral_multipliers
_easy_mask = _dv._easy_mask


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


def apply_poisson_multipliers(
    df_feat: pd.DataFrame,
    club_fixtures: pd.DataFrame,
    *,
    target_gw: int,
    mode: str,
) -> pd.DataFrame:
    """Scale player rates so fixture context matches a Poisson team λ.

    ``opp``: attack_mult = opp xGC / league (own attack already in player rates).
    ``full``: attack_mult = (team xG / league) × (opp xGC / league) — reapplies own attack.
    Defence mirrors with opponent xG (and own xGC in ``full``).
    """
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
    by_club = {int(cid): group for cid, group in hist_all.groupby("club_id")}
    attack_vals: list[float] = []
    defence_vals: list[float] = []
    for row in out.itertuples(index=False):
        team_xg, team_xgc = _club_rates(
            by_club, int(row.club_id), bool(row.is_home), league_xg=league_xg, league_xgc=league_xgc
        )
        opp_xg, opp_xgc = _club_rates(
            by_club,
            int(row.opponent_id),
            not bool(row.is_home),
            league_xg=league_xg,
            league_xgc=league_xgc,
        )
        opp_concede = opp_xgc / league_xgc
        opp_attack = opp_xg / league_xg
        if mode == "opp":
            attack_mult = opp_concede
            defence_mult = opp_attack
        elif mode == "full":
            attack_mult = (team_xg / league_xg) * opp_concede
            defence_mult = opp_attack * (team_xgc / league_xgc)
        else:
            raise ValueError(mode)
        attack_vals.append(float(min(max(attack_mult, 0.4), 1.8)))
        defence_vals.append(float(min(max(defence_mult, 0.4), 1.8)))
    out["attack_multiplier"] = attack_vals
    out["defence_multiplier"] = defence_vals
    return out


def _row(frame: pd.DataFrame, *, regime: str, slice_name: str, target_column: str) -> dict[str, object]:
    metrics = evaluate_predictions(frame, target_column=target_column)
    return {
        "model": MODEL,
        "multiplier_regime": regime,
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
    regimes = ("club_strength", "neutral", "poisson_opp_k10", "poisson_full_k10")
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
        difficulty_map = df_feat.groupby(["player_id", "gameweek_id"], as_index=False)["difficulty"].mean()
        model = get_model(MODEL)
        model.fit(history_before_target(df_perf, gw, deadlines.get(gw), False))
        variants = {
            "club_strength": df_feat,
            "neutral": apply_neutral_multipliers(df_feat),
            "poisson_opp_k10": apply_poisson_multipliers(
                df_feat, club_fixtures, target_gw=gw, mode="opp"
            ),
            "poisson_full_k10": apply_poisson_multipliers(
                df_feat, club_fixtures, target_gw=gw, mode="full"
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
            position_map = features[["player_id", "position_id"]].drop_duplicates("player_id")
            df_compare = df_compare.merge(position_map, on="player_id", how="left")
            df_compare = df_compare.merge(difficulty_map, on=["player_id", "gameweek_id"], how="left")
            process_src = df_perf[df_perf["gameweek_id"] == gw].merge(position_map, on="player_id", how="left")
            df_compare = df_compare.merge(
                aggregate_process_points(process_src), on=["player_id", "gameweek_id"], how="left"
            )
            df_compare["process_points"] = df_compare["process_points"].fillna(0.0)
            df_compare["gameweek"] = gw
            buckets[regime].append(df_compare)

    rows: list[dict[str, object]] = []
    for regime, parts in buckets.items():
        frame = pd.concat(parts, ignore_index=True)
        for slice_name, subset in (("all", frame), ("easy_mid_fwd", frame.loc[_easy_mask(frame)])):
            for target in ("actual_points", "process_points"):
                rows.append(_row(subset, regime=regime, slice_name=slice_name, target_column=target))
    return rows


def main() -> int:
    rows = run()
    out = TOPIC / "team_poisson_summary.csv"
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
