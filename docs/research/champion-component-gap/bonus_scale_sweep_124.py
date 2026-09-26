"""AFK follow-up: xp_bonus scale experiments on goals_path ± CS scales.

Caches reuse .tmp/agent walkforward parquets from segment_fix_sweep_124.py.

  uv run python .tmp/agent/bonus_scale_sweep_124.py
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

SCRATCH = ROOT / ".tmp" / "agent"
TOPIC = ROOT / "docs" / "research" / "champion-component-gap"
OUT_CSV = TOPIC / "bonus_scale_sweep_124.csv"
OUT_JSON = TOPIC / "bonus_scale_sweep_124.json"
PROD_CS = 1.296903
SEASON = "2025-26"
SEED = "2024-25"
CHAMPION = "hold_chase_challenger"
GOALS = "goals_path_challenger"


def _load(model: str) -> pd.DataFrame:
    path = SCRATCH / f"wf_{model}_{SEASON}_{SEED}_1-38.parquet"
    if not path.exists():
        raise FileNotFoundError(f"missing cache {path}; run segment_fix_sweep_124.py first")
    return pd.read_parquet(path)


def _apply(
    base: pd.DataFrame,
    *,
    k_cs: float = 1.0,
    k_gc: float = 1.0,
    k_bonus: float = 1.0,
) -> pd.DataFrame:
    out = base.copy()
    cs0 = pd.to_numeric(out["xp_clean_sheet"], errors="coerce").fillna(0.0)
    gc0 = pd.to_numeric(out["xp_conceded"], errors="coerce").fillna(0.0)
    b0 = pd.to_numeric(out["xp_bonus"], errors="coerce").fillna(0.0)
    pts0 = pd.to_numeric(out["projected_points"], errors="coerce").fillna(0.0)
    out["xp_clean_sheet"] = cs0 * k_cs
    out["xp_conceded"] = gc0 * k_gc
    out["xp_bonus"] = b0 * k_bonus
    out["projected_points"] = (
        pts0 + (k_cs - 1.0) * cs0 + (k_gc - 1.0) * gc0 + (k_bonus - 1.0) * b0
    )
    return out


def _gate(label: str, champ: pd.DataFrame, cand: pd.DataFrame, meta: dict[str, Any]) -> dict[str, Any]:
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
    segs = {
        name: primary_metric_value(blend_c[name]) - primary_metric_value(blend_a[name])
        for name in ("cold_start", "early_mid", "late")
        if name in blend_c and name in blend_a
    }
    return {
        "label": label,
        **meta,
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
        "realized_mae_cand": float(realized_a["combined"]["mae"]),
        "realized_mae_champ": float(realized_c["combined"]["mae"]),
        "process_mae_cand": float(process_a["combined"]["mae"]),
        "process_mae_champ": float(process_c["combined"]["mae"]),
    }


def main() -> int:
    champ = _load(CHAMPION)
    goals = _load(GOALS)
    rows: list[dict[str, Any]] = []

    bases = [
        ("goals", 1.0, 1.0),
        ("cs_prod", PROD_CS, 1.0),  # best 2/3 primary↑ from prior sweep
        ("cs_1.10", 1.10, 1.0),  # MAE-ok 2/3 but primary↓
    ]
    bonus_ks = [0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0, 4.0]

    for base_name, k_cs, k_gc in bases:
        for k_b in bonus_ks:
            label = f"{base_name}_bonus_{k_b:.2f}"
            cand = _apply(goals, k_cs=k_cs, k_gc=k_gc, k_bonus=k_b)
            row = _gate(
                label,
                champ,
                cand,
                {"base": base_name, "k_cs": k_cs, "k_gc": k_gc, "k_bonus": k_b},
            )
            rows.append(row)
            flag = "PASS" if row["passed"] else "fail"
            print(
                f"{flag} {label}: segs={row['segment_wins']}/3 Δpri={row['combined_primary_delta']:+.4f} "
                f"early={row['early_mid_delta']:+.3f} late={row['late_delta']:+.3f} "
                f"Rmae={row['realized_mae_cand']:.4f} | {row['reasons'] or 'ok'}",
                flush=True,
            )

    frame = pd.DataFrame(rows).sort_values(
        by=["passed", "segment_wins", "late_delta", "combined_primary_delta"],
        ascending=[False, False, False, False],
    )
    frame.to_csv(OUT_CSV, index=False)
    payload = {
        "any_pass": bool(frame["passed"].any()),
        "best_segment_wins": int(frame["segment_wins"].max()),
        "any_late_win": bool((frame["late_delta"] > 0).any()),
        "pass_labels": frame.loc[frame["passed"], "label"].tolist(),
        "two_plus_and_late_pos": frame.loc[
            (frame["segment_wins"] >= 2) & (frame["late_delta"] > 0), "label"
        ].tolist(),
        "best_late": frame.nlargest(5, "late_delta")[
            ["label", "late_delta", "segment_wins", "combined_primary_delta", "realized_mae_cand"]
        ].to_dict(orient="records"),
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT_CSV}", flush=True)
    print(json.dumps(payload, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
