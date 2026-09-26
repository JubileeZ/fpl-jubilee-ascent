"""AFK #124 evidence: sweep post-link CS/GC scales on goals_path vs Champion gate.

Caches walk-forwards under .tmp/agent/; writes companion CSV into topic folder.
Does not mutate production model scales.

  uv run python .tmp/agent/segment_fix_sweep_124.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from backtesting.metrics import evaluate_predictions  # noqa: E402
from backtesting.promotion import (  # noqa: E402
    evaluate_historical_promotion_gate,
    metrics_by_season_window,
    primary_metric_value,
)
from backtesting.walkforward import WalkforwardConfig, run_walkforward_backtest  # noqa: E402
from commands.backtest import resolve_backtest_data_dir, resolve_seed_processed_dir  # noqa: E402

SCRATCH = ROOT / ".tmp" / "agent"
TOPIC = ROOT / "docs" / "research" / "champion-component-gap"
OUT_CSV = TOPIC / "segment_fix_sweep_124.csv"
OUT_JSON = TOPIC / "segment_fix_sweep_124.json"

CHAMPION = "hold_chase_challenger"
GOALS = "goals_path_challenger"
SEASON = "2025-26"
SEED = "2024-25"
# Production defence_link scales (#118)
PROD_CS = 1.296903
PROD_GC = 1.145226


def _cache_path(model: str) -> Path:
    return SCRATCH / f"wf_{model}_{SEASON}_{SEED}_1-38.parquet"


def _walkforward(model: str) -> pd.DataFrame:
    path = _cache_path(model)
    if path.exists():
        print(f"cache hit {path.name}", flush=True)
        return pd.read_parquet(path)
    data_dir = resolve_backtest_data_dir(
        (ROOT / "data" / "archive" / SEASON / "processed").resolve()
    )
    seed = resolve_seed_processed_dir(data_dir, model, SEED)
    print(f"walkforward {model} …", flush=True)
    result = run_walkforward_backtest(
        WalkforwardConfig(
            model_name=model,
            data_dir=data_dir,
            start_gw=1,
            end_gw=38,
            seed_processed_dir=seed,
            eval_target="blended_points",
        )
    )
    result.df_eval.to_parquet(path, index=False)
    print(f"wrote {path.name} rows={len(result.df_eval)}", flush=True)
    return result.df_eval


def _apply_scales(
    base: pd.DataFrame,
    *,
    k_cs: float,
    k_gc: float,
    positions: set[int] | None = None,
) -> pd.DataFrame:
    """Apply defence_link-style post-link scales onto goals_path ledger.

    If ``positions`` set, only those position_ids get CS/GC scales (else all).
    Assumes ``base`` is goals_path (pre-defence-link) projections.
    """
    out = base.copy()
    cs0 = pd.to_numeric(out["xp_clean_sheet"], errors="coerce").fillna(0.0)
    gc0 = pd.to_numeric(out["xp_conceded"], errors="coerce").fillna(0.0)
    pts0 = pd.to_numeric(out["projected_points"], errors="coerce").fillna(0.0)
    if positions is None:
        mask = pd.Series(True, index=out.index)
    else:
        mask = out["position_id"].isin(positions)
    k_cs_row = mask.map({True: k_cs, False: 1.0})
    k_gc_row = mask.map({True: k_gc, False: 1.0})
    out["xp_clean_sheet"] = cs0 * k_cs_row
    out["xp_conceded"] = gc0 * k_gc_row
    out["projected_points"] = pts0 + (k_cs_row - 1.0) * cs0 + (k_gc_row - 1.0) * gc0
    return out


def _gate_row(
    label: str,
    champ: pd.DataFrame,
    cand: pd.DataFrame,
    *,
    k_cs: float,
    k_gc: float,
    note: str,
) -> dict[str, Any]:
    blend_c = metrics_by_season_window(champ, target_column="blended_points")
    blend_a = metrics_by_season_window(cand, target_column="blended_points")
    realized_c = metrics_by_season_window(champ, target_column="actual_points")
    realized_a = metrics_by_season_window(cand, target_column="actual_points")
    process_c = metrics_by_season_window(champ, target_column="process_points")
    process_a = metrics_by_season_window(cand, target_column="process_points")
    verdict = evaluate_historical_promotion_gate(
        blend_c,
        blend_a,
        eval_target="blended_points",
        reference_windows={
            "actual_points": (realized_c["combined"], realized_a["combined"]),
            "process_points": (process_c["combined"], process_a["combined"]),
        },
    )
    segs: dict[str, float] = {}
    for name in ("cold_start", "early_mid", "late"):
        if name in blend_c and name in blend_a:
            segs[name] = primary_metric_value(blend_c[name]) - primary_metric_value(blend_a[name])
    return {
        "label": label,
        "note": note,
        "k_cs": k_cs,
        "k_gc": k_gc,
        "passed": verdict.passed,
        "primary_metric": verdict.primary_metric,
        "combined_primary_delta": verdict.combined_primary_delta,
        "segment_wins": verdict.segment_wins,
        "guardrails_passed": verdict.guardrails_passed,
        "reasons": "; ".join(verdict.reasons),
        "cold_start_delta": segs.get("cold_start"),
        "early_mid_delta": segs.get("early_mid"),
        "late_delta": segs.get("late"),
        "blend_mae_cand": float(evaluate_predictions(cand, target_column="blended_points")["mae"]),
        "blend_mae_champ": float(evaluate_predictions(champ, target_column="blended_points")["mae"]),
        "realized_mae_cand": float(realized_a["combined"]["mae"]),
        "realized_mae_champ": float(realized_c["combined"]["mae"]),
        "process_mae_cand": float(process_a["combined"]["mae"]),
        "process_mae_champ": float(process_c["combined"]["mae"]),
    }


def _bias_calibrate_k(
    frame: pd.DataFrame,
    *,
    component: str,
    pool: str,
    positions: set[int] | None,
    old_k: float,
    tau: float = 0.05,
) -> float:
    """Smallest scale toward |signed_bias|≤τ on Realized component (like calibrate_defence_k)."""
    df = frame
    if pool == "mins_60":
        df = df[pd.to_numeric(df["actual_minutes"], errors="coerce").fillna(0.0) >= 60.0]
    if positions is not None:
        df = df[df["position_id"].isin(positions)]
    if df.empty or component not in df.columns:
        return old_k
    proj = float(pd.to_numeric(df[component], errors="coerce").fillna(0.0).mean())
    actual_col = f"actual_{component}"
    if actual_col not in df.columns:
        return old_k
    actual = float(pd.to_numeric(df[actual_col], errors="coerce").fillna(0.0).mean())
    bias = proj - actual
    if abs(bias) <= tau:
        return old_k
    if abs(proj) <= 1e-12:
        return old_k
    target_proj = actual + (tau if bias > 0 else -tau)
    return max(0.0, old_k * (target_proj / proj))


def main() -> int:
    SCRATCH.mkdir(parents=True, exist_ok=True)
    champ = _walkforward(CHAMPION)
    goals = _walkforward(GOALS)

    # Calibrate helpers from goals_path base (k starts at 1.0)
    k_cs_mins60 = _bias_calibrate_k(
        goals, component="xp_clean_sheet", pool="mins_60", positions=None, old_k=1.0
    )
    k_cs_all = _bias_calibrate_k(
        goals, component="xp_clean_sheet", pool="all", positions=None, old_k=1.0
    )
    k_gc_mins60 = _bias_calibrate_k(
        goals, component="xp_conceded", pool="mins_60", positions={1, 2}, old_k=1.0
    )
    k_gc_all = _bias_calibrate_k(
        goals, component="xp_conceded", pool="all", positions={1, 2}, old_k=1.0
    )
    print(
        f"calibrate from goals_path: k_cs mins60={k_cs_mins60:.6f} all={k_cs_all:.6f}; "
        f"k_gc mins60={k_gc_mins60:.6f} all={k_gc_all:.6f}",
        flush=True,
    )

    configs: list[tuple[str, float, float, set[int] | None, str]] = [
        ("goals_only", 1.0, 1.0, None, "no defence link"),
        ("prod_defence_link", PROD_CS, PROD_GC, None, "shipped #118 scales"),
        ("cs_only_prod", PROD_CS, 1.0, None, "CS prod; GC off"),
        ("gc_only_prod", 1.0, PROD_GC, None, "GC prod; CS off"),
        ("cs_mins60_gc_mins60", k_cs_mins60, k_gc_mins60, None, "fresh mins_60 calibrate on goals_path"),
        ("cs_all_gc_all", k_cs_all, k_gc_all, None, "all-pool calibrate on goals_path"),
        ("cs_all_gc_mins60", k_cs_all, k_gc_mins60, None, "CS all-pool + GC mins_60"),
        ("cs_mins60_gc_1", k_cs_mins60, 1.0, None, "CS mins_60 only"),
        ("cs_all_gc_1", k_cs_all, 1.0, None, "CS all-pool only"),
        ("gkp_def_prod", PROD_CS, PROD_GC, {1, 2}, "prod scales only GKP+DEF"),
        ("gkp_def_cs_all", k_cs_all, k_gc_all, {1, 2}, "all-pool scales only GKP+DEF"),
    ]
    # Dense CS sweep at GC=1 and GC=prod
    for k in [0.85, 0.90, 0.95, 1.00, 1.05, 1.10, 1.15, 1.20, 1.25, 1.30]:
        configs.append((f"sweep_cs_{k:.2f}_gc1", k, 1.0, None, "CS sweep GC=1"))
        configs.append((f"sweep_cs_{k:.2f}_gcprod", k, PROD_GC, None, "CS sweep GC=prod"))
    # GC sweep at CS=all and CS=1
    for k in [0.90, 1.00, 1.05, 1.10, 1.15, 1.20]:
        configs.append((f"sweep_gc_{k:.2f}_cs1", 1.0, k, None, "GC sweep CS=1"))
        configs.append((f"sweep_gc_{k:.2f}_csall", k_cs_all, k, None, "GC sweep CS=all"))

    rows: list[dict[str, Any]] = []
    for label, k_cs, k_gc, positions, note in configs:
        cand = _apply_scales(goals, k_cs=k_cs, k_gc=k_gc, positions=positions)
        row = _gate_row(label, champ, cand, k_cs=k_cs, k_gc=k_gc, note=note)
        rows.append(row)
        flag = "PASS" if row["passed"] else "fail"
        print(
            f"{flag} {label}: segs={row['segment_wins']}/3 Δpri={row['combined_primary_delta']:+.4f} "
            f"early={row['early_mid_delta']:+.3f} late={row['late_delta']:+.3f} "
            f"Rmae {row['realized_mae_cand']:.4f}/{row['realized_mae_champ']:.4f} "
            f"| {row['reasons'] or 'ok'}",
            flush=True,
        )

    frame = pd.DataFrame(rows).sort_values(
        by=["passed", "segment_wins", "combined_primary_delta", "guardrails_passed"],
        ascending=[False, False, False, False],
    )
    frame.to_csv(OUT_CSV, index=False)
    payload = {
        "champion": CHAMPION,
        "base_candidate": GOALS,
        "calibrate": {
            "k_cs_mins60": k_cs_mins60,
            "k_cs_all": k_cs_all,
            "k_gc_mins60": k_gc_mins60,
            "k_gc_all": k_gc_all,
        },
        "n_configs": len(rows),
        "any_pass": bool(frame["passed"].any()),
        "best_segment_wins": int(frame["segment_wins"].max()),
        "pass_labels": frame.loc[frame["passed"], "label"].tolist(),
        "two_plus_seg_labels": frame.loc[frame["segment_wins"] >= 2, "label"].tolist(),
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT_CSV}", flush=True)
    print(f"wrote {OUT_JSON}", flush=True)
    print(f"any_pass={payload['any_pass']} best_segs={payload['best_segment_wins']}", flush=True)
    print(f"≥2/3 labels: {payload['two_plus_seg_labels']}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
