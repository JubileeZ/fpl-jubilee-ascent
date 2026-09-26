"""Calibrate ``bonus_arm_challenger`` ``_XBPS_WEIGHTS`` + ``_BONUS_SOFTMAX_T`` (#129).

1. Event-weight scale ``k`` on (goals, assists, CS, Defcon, saves); mins fixed at 0.1.
   Target: ``mins_60`` / ``ALL`` ``xp_bonus`` ``|signed_bias|≤τ`` (τ=0.05).
2. Then $T$ grid on 2025-26 Blended Decision Regret vs Champion; prefer
   ``early_mid`` / ``late`` segment deltas > 0.

Patches ``models/bonus_arm_challenger.py``. No ``model_selection`` mutate.

  uv run python docs/research/champion-component-gap/calibrate_bonus_arm.py
"""

from __future__ import annotations

import importlib.util
import json
import re
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

TOPIC = Path(__file__).resolve().parent
MODEL_PATH = ROOT / "models" / "bonus_arm_challenger.py"
SCRATCH = ROOT / ".tmp" / "agent"
OUT_JSON = TOPIC / "calibrate_bonus_arm_129.json"
OUT_NOTE = TOPIC / "calibrate-bonus-arm-129.md"

_BIAS_TAU = 0.05
_BASE_WEIGHTS = (0.1, 24.0, 12.0, 12.0, 6.0, 2.0)
_EVENT_SCALES = (1.0, 1.5, 2.0, 2.5, 3.0, 4.0)
_T_GRID = (3.0, 4.0, 5.0, 6.0, 8.0, 10.0)
CHAMPION = "hold_chase_challenger"
CANDIDATE = "bonus_arm_challenger"
SEASON = "2025-26"
SEED = "2024-25"


def _load_runner():  # noqa: ANN201
    spec = importlib.util.spec_from_file_location("component_gap_runner", TOPIC / "runner.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load component-gap runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _weights_for_scale(k: float) -> tuple[float, float, float, float, float, float]:
    return (
        _BASE_WEIGHTS[0],
        _BASE_WEIGHTS[1] * k,
        _BASE_WEIGHTS[2] * k,
        _BASE_WEIGHTS[3] * k,
        _BASE_WEIGHTS[4] * k,
        _BASE_WEIGHTS[5] * k,
    )


def _set_levers(*, weights: tuple[float, ...], temperature: float) -> None:
    import models.bonus_arm_challenger as bac

    bac._XBPS_WEIGHTS = tuple(float(w) for w in weights)
    bac._BONUS_SOFTMAX_T = float(temperature)


def _bonus_bias_mins60_all(runner: Any) -> dict[str, float]:
    rows, _totals = runner.run_window(
        model_name=CANDIDATE,
        evaluation_season=SEASON,
        seed_season=SEED,
        gw_start=1,
        gw_end=38,
    )
    gate = next(
        r
        for r in rows
        if r["pool"] == "mins_60"
        and r["position"] == "ALL"
        and r["component"] == "xp_bonus"
    )
    return {
        "mean_projected": float(gate["mean_projected"]),
        "mean_actual": float(gate["mean_actual"]),
        "signed_bias": float(gate["signed_bias"]),
        "mse_share": float(gate["mse_share"]),
    }


def _cache_path(model: str, tag: str) -> Path:
    return SCRATCH / f"wf_{model}_{SEASON}_{SEED}_1-38_{tag}.parquet"


def _walkforward_blended(model: str, tag: str) -> pd.DataFrame:
    path = _cache_path(model, tag)
    if path.exists():
        print(f"cache hit {path.name}", flush=True)
        return pd.read_parquet(path)
    SCRATCH.mkdir(parents=True, exist_ok=True)
    data_dir = resolve_backtest_data_dir(
        (ROOT / "data" / "archive" / SEASON / "processed").resolve()
    )
    seed = resolve_seed_processed_dir(data_dir, model, SEED)
    print(f"walkforward blended {model} tag={tag} …", flush=True)
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


def _gate_row(champ: pd.DataFrame, cand: pd.DataFrame, meta: dict[str, Any]) -> dict[str, Any]:
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
        **meta,
        "passed": bool(verdict.passed),
        "primary_metric": verdict.primary_metric,
        "combined_primary_delta": float(verdict.combined_primary_delta),
        "segment_wins": int(verdict.segment_wins),
        "guardrails_passed": bool(verdict.guardrails_passed),
        "reasons": "; ".join(verdict.reasons),
        "cold_start_delta": segs.get("cold_start"),
        "early_mid_delta": segs.get("early_mid"),
        "late_delta": segs.get("late"),
        "blend_mae_cand": float(evaluate_predictions(cand, target_column="blended_points")["mae"]),
        "realized_mae_cand": float(realized_a["combined"]["mae"]),
    }


def _score_t_row(row: dict[str, Any]) -> tuple[int, int, float, float]:
    """Prefer early_mid/late wins, then segment count, then primary delta."""
    em = 1 if (row.get("early_mid_delta") or 0) > 0 else 0
    late = 1 if (row.get("late_delta") or 0) > 0 else 0
    return (em + late, int(row["segment_wins"]), float(row["combined_primary_delta"]), -abs(float(row.get("T", 6))))


def _patch_model(*, weights: tuple[float, ...], temperature: float) -> None:
    text = MODEL_PATH.read_text(encoding="utf-8")
    w_lit = ", ".join(f"{float(w):.6f}" for w in weights)
    patched, n_w = re.subn(
        r"^(_XBPS_WEIGHTS\s*=\s*)\([^)]*\)(.*)$",
        rf"\g<1>({w_lit})\2",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    patched, n_t = re.subn(
        r"^(_BONUS_SOFTMAX_T\s*=\s*)([0-9.]+)\s*$",
        rf"\g<1>{float(temperature):.6f}",
        patched,
        count=1,
        flags=re.MULTILINE,
    )
    if n_w != 1 or n_t != 1:
        raise RuntimeError(f"failed to patch levers in {MODEL_PATH} (w={n_w} t={n_t})")
    MODEL_PATH.write_text(patched, encoding="utf-8")


def _write_note(payload: dict[str, Any]) -> None:
    w = payload["frozen_weights"]
    t = payload["frozen_T"]
    wb = payload["weight_best"]
    tb = payload["t_best"]
    OUT_NOTE.write_text(
        "\n".join(
            [
                "# Calibrate bonus_arm_challenger (#129)",
                "",
                "**Updated**: auto from `calibrate_bonus_arm.py`",
                f"**Data stamp**: {SEASON} GW1–38 seed {SEED}",
                "**Status**: Active — freezes `_XBPS_WEIGHTS` + `_BONUS_SOFTMAX_T`",
                "**Purpose**: Data-drive bonus-arm levers (#127); no Admission / `--apply`",
                "",
                "## Frozen constants",
                "",
                f"- `_XBPS_WEIGHTS` = `{tuple(w)}` (event scale k={wb['event_scale']})",
                f"- `_BONUS_SOFTMAX_T` = `{t}`",
                f"- Weight bias (mins_60/ALL xp_bonus): signed_bias={wb['signed_bias']:+.6f} "
                f"(τ={_BIAS_TAU}; inside={wb['inside_tau']})",
                f"- T pick: early_mid_delta={tb.get('early_mid_delta')} late_delta={tb.get('late_delta')} "
                f"segs={tb.get('segment_wins')} Δpri={tb.get('combined_primary_delta')}",
                "",
                "## Method",
                "",
                "1. Grid event scale on (g,a,CS,Defcon,saves); mins fixed 0.1; measure Realized "
                "`xp_bonus` bias via component-gap runner.",
                "2. Freeze best |bias| (prefer ≤τ); grid $T$; Blended Decision Regret vs Champion; "
                "prefer early_mid/late.",
                "",
                "Companion: [calibrate_bonus_arm_129.json](calibrate_bonus_arm_129.json)",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    SCRATCH.mkdir(parents=True, exist_ok=True)
    runner = _load_runner()

    print("=== Phase 1: event-weight scale → mins_60/ALL xp_bonus bias ===", flush=True)
    weight_rows: list[dict[str, Any]] = []
    for k in _EVENT_SCALES:
        weights = _weights_for_scale(k)
        _set_levers(weights=weights, temperature=6.0)
        print(f"measure event_scale={k} weights={weights} …", flush=True)
        bias = _bonus_bias_mins60_all(runner)
        row = {
            "event_scale": k,
            "weights": list(weights),
            "T": 6.0,
            **bias,
            "abs_bias": abs(bias["signed_bias"]),
            "inside_tau": abs(bias["signed_bias"]) <= _BIAS_TAU,
        }
        weight_rows.append(row)
        print(
            f"  bias={bias['signed_bias']:+.6f} proj={bias['mean_projected']:.4f} "
            f"act={bias['mean_actual']:.4f} inside_τ={row['inside_tau']}",
            flush=True,
        )

    # Prefer inside τ; else smallest |bias|; tie → smaller k (closest to shipped).
    weight_rows.sort(key=lambda r: (0 if r["inside_tau"] else 1, r["abs_bias"], r["event_scale"]))
    weight_best = weight_rows[0]
    frozen_weights = tuple(weight_best["weights"])
    print(
        f"weight pick: k={weight_best['event_scale']} bias={weight_best['signed_bias']:+.6f}",
        flush=True,
    )

    print("=== Phase 2: T grid on Blended Decision Regret ===", flush=True)
    _set_levers(weights=frozen_weights, temperature=6.0)
    champ = _walkforward_blended(CHAMPION, "champ")
    t_rows: list[dict[str, Any]] = []
    for t in _T_GRID:
        _set_levers(weights=frozen_weights, temperature=t)
        tag = f"w{weight_best['event_scale']}_T{t}"
        # Bust cache when levers change: tag encodes levers.
        cand = _walkforward_blended(CANDIDATE, tag)
        row = _gate_row(
            champ,
            cand,
            {"T": t, "event_scale": weight_best["event_scale"], "weights": list(frozen_weights)},
        )
        t_rows.append(row)
        print(
            f"  T={t}: segs={row['segment_wins']}/3 Δpri={row['combined_primary_delta']:+.4f} "
            f"early={row['early_mid_delta']:+.3f} late={row['late_delta']:+.3f} "
            f"pass={row['passed']}",
            flush=True,
        )

    t_rows.sort(key=_score_t_row, reverse=True)
    t_best = t_rows[0]
    frozen_t = float(t_best["T"])
    print(f"T pick: {frozen_t} score={_score_t_row(t_best)}", flush=True)

    _set_levers(weights=frozen_weights, temperature=frozen_t)
    _patch_model(weights=frozen_weights, temperature=frozen_t)
    print(
        f"Patched {MODEL_PATH} weights={frozen_weights} T={frozen_t}",
        flush=True,
    )

    payload = {
        "frozen_weights": list(frozen_weights),
        "frozen_T": frozen_t,
        "weight_best": weight_best,
        "weight_grid": weight_rows,
        "t_best": t_best,
        "t_grid": t_rows,
        "tau": _BIAS_TAU,
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    _write_note(payload)
    print(f"wrote {OUT_JSON} and {OUT_NOTE}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
