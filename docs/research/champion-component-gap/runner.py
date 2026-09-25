"""Champion Event Component gap companion (mse_share + diagnostic twins)."""

from __future__ import annotations

import csv
import math
import sys
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from backtesting.process_points import blended_points  # noqa: E402
from backtesting.walkforward import LEDGER_COMPONENTS, WalkforwardConfig, run_walkforward_backtest  # noqa: E402
from commands.backtest import resolve_backtest_data_dir, resolve_seed_processed_dir  # noqa: E402
from models.scoring_matrix import Position, event_points  # noqa: E402
from models.selection import load_model_selection  # noqa: E402

OUTPUT = Path(__file__).resolve().parent / "component_gap_summary.csv"
TOTALS_OUTPUT = Path(__file__).resolve().parent / "component_gap_totals.csv"

_POS = {1: "GK", 2: "D", 3: "M", 4: "F"}
_POS_LABEL = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}
_CS_PTS = {"GK": 4.0, "D": 4.0, "M": 1.0, "F": 0.0}
_TWIN_COMPONENTS = {"xp_goals", "xp_assists", "xp_clean_sheet", "xp_conceded"}
_SHRINK_THETA = 0.50
_BIAS_TAU = 0.05


def _poisson_pmf(k: int, lmbda: float) -> float:
    if lmbda <= 0.0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lmbda) * (lmbda**k) / math.factorial(k)


def _expected_poisson_floor_half(lmbda: float) -> float:
    """E[floor(X/2)] for X ~ Poisson(lmbda)."""
    if lmbda <= 0.0:
        return 0.0
    max_k = int(math.ceil(lmbda + 10.0 * math.sqrt(lmbda) + 20.0))
    return sum(math.floor(k / 2) * _poisson_pmf(k, lmbda) for k in range(max_k + 1))


def _numeric(frame: pd.DataFrame, name: str) -> pd.Series:
    if name not in frame.columns:
        return pd.Series(0.0, index=frame.index, dtype=float)
    return pd.to_numeric(frame[name], errors="coerce").fillna(0.0).astype(float)


def build_fixture_twins(perf: pd.DataFrame, players: pd.DataFrame) -> pd.DataFrame:
    """Fixture-grain Process G/A + Poisson-xGC CS/GC twin actuals."""
    pos_frame = players.rename(columns={"id": "player_id"})[["player_id", "position_id"]].drop_duplicates(
        "player_id"
    )
    frame = perf.merge(pos_frame, on="player_id", how="left")
    pos = frame["position_id"].map(_POS).fillna("M")
    minutes = _numeric(frame, "minutes")
    xg = _numeric(frame, "expected_goals")
    xa = _numeric(frame, "expected_assists")
    xgc = _numeric(frame, "expected_goals_conceded")
    twin_goals = pd.Series(
        [
            event_points("goals", cast(Position, str(p)), float(q))
            for p, q in zip(pos, xg, strict=True)
        ],
        index=frame.index,
        dtype=float,
    )
    twin_assists = pd.Series(
        [
            event_points("assists", cast(Position, str(p)), float(q))
            for p, q in zip(pos, xa, strict=True)
        ],
        index=frame.index,
        dtype=float,
    )
    twin_cs = np.exp(-xgc.to_numpy()) * (minutes.to_numpy() >= 60.0).astype(float) * pos.map(_CS_PTS).to_numpy()
    twin_gc = np.array(
        [
            -_expected_poisson_floor_half(float(lam)) if code in {"GK", "D"} else 0.0
            for lam, code in zip(xgc, pos, strict=True)
        ],
        dtype=float,
    )
    out = frame[["player_id", "gameweek_id"]].copy()
    out["twin_xp_goals"] = twin_goals
    out["twin_xp_assists"] = twin_assists
    out["twin_xp_clean_sheet"] = twin_cs
    out["twin_xp_conceded"] = twin_gc
    return out.groupby(["player_id", "gameweek_id"], as_index=False)[
        ["twin_xp_goals", "twin_xp_assists", "twin_xp_clean_sheet", "twin_xp_conceded"]
    ].sum()


def attach_twins(df_eval: pd.DataFrame, data_dir: Path) -> pd.DataFrame:
    perf = pd.read_parquet(data_dir / "player_performances.parquet")
    players = pd.read_parquet(data_dir / "players.parquet")
    twins = build_fixture_twins(perf, players)
    merged = df_eval.merge(twins, on=["player_id", "gameweek_id"], how="left")
    for col in ("twin_xp_goals", "twin_xp_assists", "twin_xp_clean_sheet", "twin_xp_conceded"):
        merged[col] = merged[col].fillna(0.0)
    return merged


def _mse_partition(frame: pd.DataFrame, actual_map: dict[str, str]) -> dict[str, dict[str, float]]:
    e_total = frame["projected_points"] - frame["actual_points"]
    denom = float(np.mean(np.square(e_total.to_numpy())))
    out: dict[str, dict[str, float]] = {}
    for comp in LEDGER_COMPONENTS:
        if comp not in frame.columns:
            continue
        act_col = actual_map.get(comp, f"actual_{comp}")
        if act_col not in frame.columns:
            continue
        e_c = frame[comp] - frame[act_col]
        contrib = float(np.mean((e_c * e_total).to_numpy()))
        share = contrib / denom if denom > 0.0 else float("nan")
        out[comp] = {
            "mean_projected": float(frame[comp].mean()),
            "mean_actual": float(frame[act_col].mean()),
            "signed_bias": float(e_c.mean()),
            "mae": float(e_c.abs().mean()),
            "rmse": float(np.sqrt(np.mean(np.square(e_c.to_numpy())))),
            "mse_contrib": contrib,
            "mse_share": share,
        }
    return out


def _demotion_label(
    component: str,
    mse_share: float,
    mse_share_twin: float | None,
    signed_bias: float,
) -> str:
    if component not in _TWIN_COMPONENTS or mse_share_twin is None or math.isnan(mse_share):
        return "no_twin"
    abs_r = abs(mse_share)
    abs_t = abs(mse_share_twin)
    if abs_r <= 1e-12:
        return "no_twin"
    twin_shrink = 1.0 - (abs_t / abs_r)
    if twin_shrink >= _SHRINK_THETA and abs(signed_bias) <= _BIAS_TAU:
        return "variance"
    if twin_shrink >= _SHRINK_THETA and abs(signed_bias) > _BIAS_TAU:
        return "link-bias" if component in {"xp_clean_sheet", "xp_conceded"} else "structural"
    return "structural"


def _slice_rows(
    frame: pd.DataFrame,
    *,
    model: str,
    evaluation_season: str,
    gw_start: int,
    gw_end: int,
    seed_season: str,
    snapshot_backed: bool,
    pool: str,
    position: str,
) -> list[dict[str, Any]]:
    realized = _mse_partition(frame, {c: f"actual_{c}" for c in LEDGER_COMPONENTS})
    twin_actual = {
        "xp_goals": "twin_xp_goals",
        "xp_assists": "twin_xp_assists",
        "xp_clean_sheet": "twin_xp_clean_sheet",
        "xp_conceded": "twin_xp_conceded",
    }
    twin_part = _mse_partition(frame, twin_actual)
    ranked = sorted(realized.items(), key=lambda item: abs(item[1]["mse_share"]), reverse=True)
    rank_map = {comp: i + 1 for i, (comp, _) in enumerate(ranked)}
    e_total = frame["projected_points"] - frame["actual_points"]
    total_mse = float(np.mean(np.square(e_total.to_numpy())))
    total_bias = float(e_total.mean())
    rows: list[dict[str, Any]] = []
    for comp, stats in realized.items():
        twin_source = "none"
        mse_share_twin: float | str = ""
        twin_shrink: float | str = ""
        signed_bias_twin: float | str = ""
        twin_link_bias: float | str = ""
        if comp in twin_actual:
            twin_source = "process_ga" if comp in {"xp_goals", "xp_assists"} else "poisson_xgc"
            tstats = twin_part.get(comp)
            if tstats is not None:
                mse_share_twin = tstats["mse_share"]
                signed_bias_twin = tstats["signed_bias"]
                twin_link_bias = float(frame[twin_actual[comp]].mean() - frame[f"actual_{comp}"].mean())
                if abs(stats["mse_share"]) > 1e-12:
                    twin_shrink = 1.0 - abs(float(mse_share_twin)) / abs(stats["mse_share"])
        label = _demotion_label(
            comp,
            stats["mse_share"],
            float(mse_share_twin) if mse_share_twin != "" else None,
            stats["signed_bias"],
        )
        bias_share = stats["signed_bias"] / total_bias if abs(total_bias) > 1e-12 else float("nan")
        rows.append(
            {
                "model": model,
                "evaluation_season": evaluation_season,
                "gw_start": gw_start,
                "gw_end": gw_end,
                "seed_season": seed_season,
                "pool": pool,
                "position": position,
                "eval_target": "realized",
                "component": comp,
                "sample_count": int(len(frame)),
                "mean_projected": stats["mean_projected"],
                "mean_actual": stats["mean_actual"],
                "signed_bias": stats["signed_bias"],
                "bias_share": bias_share,
                "mae": stats["mae"],
                "rmse": stats["rmse"],
                "mse_contrib": stats["mse_contrib"],
                "mse_share": stats["mse_share"],
                "rank_by_mse_share": rank_map[comp],
                "twin_source": twin_source,
                "mse_share_twin": mse_share_twin,
                "twin_shrink": twin_shrink,
                "signed_bias_twin": signed_bias_twin,
                "twin_link_bias": twin_link_bias,
                "demotion_label": label,
                "snapshot_backed": str(snapshot_backed).lower(),
                "total_mse": total_mse,
                "total_signed_bias": total_bias,
                "shrink_theta": _SHRINK_THETA,
                "bias_tau": _BIAS_TAU,
            }
        )
    return rows


def summarize_frame(
    df_eval: pd.DataFrame,
    *,
    model: str,
    evaluation_season: str,
    gw_start: int,
    gw_end: int,
    seed_season: str,
    snapshot_backed: bool,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    pools = {
        "all": df_eval,
        "mins_60": df_eval[df_eval["actual_minutes"] >= 60].copy(),
    }
    for pool_name, pool_frame in pools.items():
        if pool_frame.empty:
            continue
        rows.extend(
            _slice_rows(
                pool_frame,
                model=model,
                evaluation_season=evaluation_season,
                gw_start=gw_start,
                gw_end=gw_end,
                seed_season=seed_season,
                snapshot_backed=snapshot_backed,
                pool=pool_name,
                position="ALL",
            )
        )
        if "position_id" not in pool_frame.columns:
            continue
        for pid, label in _POS_LABEL.items():
            pos_frame = pool_frame[pool_frame["position_id"] == pid]
            if pos_frame.empty:
                continue
            rows.extend(
                _slice_rows(
                    pos_frame,
                    model=model,
                    evaluation_season=evaluation_season,
                    gw_start=gw_start,
                    gw_end=gw_end,
                    seed_season=seed_season,
                    snapshot_backed=snapshot_backed,
                    pool=pool_name,
                    position=label,
                )
            )
    return rows


def _finished_end_gw(data_dir: Path) -> int:
    gameweeks = pd.read_parquet(data_dir / "gameweeks.parquet")
    finished = gameweeks.loc[gameweeks["finished"] == True, "id"]  # noqa: E712
    if finished.empty:
        raise ValueError(f"No finished Gameweeks in {data_dir}")
    return int(finished.max())


def _totals_row(
    df_eval: pd.DataFrame,
    *,
    model: str,
    evaluation_season: str,
    gw_start: int,
    gw_end: int,
    seed_season: str,
    snapshot_backed: bool,
) -> dict[str, Any]:
    actual = df_eval["actual_points"]
    proj = df_eval["projected_points"]
    process = df_eval["process_points"]
    blend = blended_points(actual, process, weight=0.5)
    return {
        "model": model,
        "evaluation_season": evaluation_season,
        "gw_start": gw_start,
        "gw_end": gw_end,
        "seed_season": seed_season,
        "sample_count": int(len(df_eval)),
        "realized_signed_bias": float((proj - actual).mean()),
        "realized_mae": float((proj - actual).abs().mean()),
        "realized_mse": float(np.mean(np.square((proj - actual).to_numpy()))),
        "process_signed_bias": float((proj - process).mean()),
        "process_mae": float((proj - process).abs().mean()),
        "blend_signed_bias": float((proj - blend).mean()),
        "blend_mae": float((proj - blend).abs().mean()),
        "snapshot_backed": str(snapshot_backed).lower(),
    }


def run_window(
    *,
    model_name: str,
    evaluation_season: str,
    seed_season: str,
    gw_start: int,
    gw_end: int | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    data_dir = resolve_backtest_data_dir((ROOT / "data" / "archive" / evaluation_season / "processed").resolve())
    end = gw_end if gw_end is not None else _finished_end_gw(data_dir)
    seed_dir = resolve_seed_processed_dir(data_dir, model_name, seed_season)
    result = run_walkforward_backtest(
        WalkforwardConfig(
            model_name=model_name,
            data_dir=data_dir,
            start_gw=gw_start,
            end_gw=end,
            seed_processed_dir=seed_dir,
        )
    )
    df_eval = attach_twins(result.df_eval, data_dir)
    rows = summarize_frame(
        df_eval,
        model=model_name,
        evaluation_season=evaluation_season,
        gw_start=gw_start,
        gw_end=end,
        seed_season=seed_season,
        snapshot_backed=result.snapshot_backed,
    )
    totals = _totals_row(
        df_eval,
        model=model_name,
        evaluation_season=evaluation_season,
        gw_start=gw_start,
        gw_end=end,
        seed_season=seed_season,
        snapshot_backed=result.snapshot_backed,
    )
    return rows, totals


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"no rows for {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


# Research-only companions (#116/#118); not Comparison Slate until admission (#112).
_EXTRA_RESEARCH_MODELS = ("goals_path_challenger", "defence_link_challenger")


def main() -> int:
    selection = load_model_selection()
    models = [selection.champion, *list(selection.candidates)]
    for name in _EXTRA_RESEARCH_MODELS:
        if name not in models:
            models.append(name)
    windows: list[tuple[str, str, int, int | None]] = [
        ("2025-26", "2024-25", 1, 38),
        ("2026-27", "2025-26", 1, None),
    ]
    all_rows: list[dict[str, Any]] = []
    all_totals: list[dict[str, Any]] = []
    for model_name in models:
        for evaluation_season, seed_season, gw_start, gw_end in windows:
            print(f"Running {model_name} {evaluation_season} seed={seed_season} …", flush=True)
            rows, totals = run_window(
                model_name=model_name,
                evaluation_season=evaluation_season,
                seed_season=seed_season,
                gw_start=gw_start,
                gw_end=gw_end,
            )
            all_rows.extend(rows)
            all_totals.append(totals)
    _write_csv(OUTPUT, all_rows)
    _write_csv(TOTALS_OUTPUT, all_totals)
    print(f"Wrote {OUTPUT} ({len(all_rows)} rows)", flush=True)
    print(f"Wrote {TOTALS_OUTPUT} ({len(all_totals)} rows)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
