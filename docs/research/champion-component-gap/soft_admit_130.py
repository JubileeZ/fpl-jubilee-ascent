"""Soft pre-gate flip checklist + Comparison Slate admission race for bonus_arm (#130).

Soft (#115/#120/#128): goals (all/ALL) · CS (mins_60/ALL) · conceded (mins_60 GKP+DEF
combined) · bonus (mins_60/ALL). Arm PASS = bias clears (|bias|≤τ or |bias|↓ vs
Champion) and/or twin demotion off structural/link-bias and/or |mse_share|↓.

Admission (#112): Blended gate vs each Candidate seat; beat both → replace worse
Blended primary; beat one → replace that seat; none → slate unchanged.
No Champion ``--apply``.

  uv run python docs/research/champion-component-gap/soft_admit_130.py [--write-slate]
"""

from __future__ import annotations

import argparse
import importlib.util
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
from backtesting.model_evaluation import replace_candidate  # noqa: E402
from commands.backtest import resolve_backtest_data_dir, resolve_seed_processed_dir  # noqa: E402
from models.selection import load_model_selection, save_model_selection  # noqa: E402

TOPIC = Path(__file__).resolve().parent
SCRATCH = ROOT / ".tmp" / "agent"
OUT_SOFT = TOPIC / "soft_pre_gate_130.json"
OUT_ADMIT = TOPIC / "admission_race_130.json"

SEASON = "2025-26"
SEED = "2024-25"
INCOMING = "bonus_arm_challenger"
TAU = 0.05
_BAD_LABELS = {"structural", "link-bias"}


def _load_runner() -> Any:
    spec = importlib.util.spec_from_file_location("component_gap_runner", TOPIC / "runner.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load component-gap runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _data_dir() -> Path:
    return resolve_backtest_data_dir((ROOT / "data" / "archive" / SEASON / "processed").resolve())


def _walkforward(model: str) -> tuple[pd.DataFrame, bool]:
    path = SCRATCH / f"wf130_{model}_{SEASON}_{SEED}_1-38.parquet"
    if path.exists():
        print(f"cache hit {path.name}", flush=True)
        return pd.read_parquet(path), False
    SCRATCH.mkdir(parents=True, exist_ok=True)
    data_dir = _data_dir()
    print(f"walkforward blended {model} …", flush=True)
    result = run_walkforward_backtest(
        WalkforwardConfig(
            model_name=model,
            data_dir=data_dir,
            start_gw=1,
            end_gw=38,
            seed_processed_dir=resolve_seed_processed_dir(data_dir, model, SEED),
            eval_target="blended_points",
        )
    )
    result.df_eval.to_parquet(path, index=False)
    return result.df_eval, bool(result.snapshot_backed)


def _rows(runner: Any, model: str, df_eval: pd.DataFrame) -> list[dict[str, Any]]:
    return runner.summarize_frame(
        runner.attach_twins(df_eval, _data_dir()),
        model=model,
        evaluation_season=SEASON,
        gw_start=1,
        gw_end=38,
        seed_season=SEED,
        snapshot_backed=False,
    )


def _cell(rows: list[dict[str, Any]], pool: str, position: str, component: str) -> dict[str, Any]:
    return next(
        r
        for r in rows
        if r["pool"] == pool and r["position"] == position and r["component"] == component
    )


def _combined_gkp_def(rows: list[dict[str, Any]]) -> dict[str, Any]:
    parts = [_cell(rows, "mins_60", pos, "xp_conceded") for pos in ("GKP", "DEF")]
    n = sum(int(p["sample_count"]) for p in parts)
    return {
        "signed_bias": sum(int(p["sample_count"]) * float(p["signed_bias"]) for p in parts) / n,
        "mse_share": sum(int(p["sample_count"]) * float(p["mse_share"]) for p in parts) / n,
        "demotion_label": "/".join(str(p["demotion_label"]) for p in parts),
    }


def _arm(name: str, champ: dict[str, Any], cand: dict[str, Any]) -> dict[str, Any]:
    cb, ab = float(champ["signed_bias"]), float(cand["signed_bias"])
    cm, am = abs(float(champ["mse_share"])), abs(float(cand["mse_share"]))
    champ_labels = set(str(champ["demotion_label"]).split("/"))
    cand_labels = set(str(cand["demotion_label"]).split("/"))
    bias_ok = abs(ab) <= TAU + 1e-6 or abs(ab) < abs(cb)
    demotion_ok = bool(champ_labels & _BAD_LABELS) and not (cand_labels & _BAD_LABELS)
    mse_ok = am < cm
    return {
        "arm": name,
        "pass": bias_ok or demotion_ok or mse_ok,
        "bias_ok": bias_ok,
        "demotion_ok": demotion_ok,
        "mse_ok": mse_ok,
        "champ_bias": cb,
        "cand_bias": ab,
        "champ_mse_share": float(champ["mse_share"]),
        "cand_mse_share": float(cand["mse_share"]),
        "champ_label": str(champ["demotion_label"]),
        "cand_label": str(cand["demotion_label"]),
    }


def _soft(runner: Any, champion: str, champ_df: pd.DataFrame, cand_df: pd.DataFrame) -> dict[str, Any]:
    champ_rows = _rows(runner, champion, champ_df)
    cand_rows = _rows(runner, INCOMING, cand_df)
    arms = [
        _arm("goals", _cell(champ_rows, "all", "ALL", "xp_goals"), _cell(cand_rows, "all", "ALL", "xp_goals")),
        _arm(
            "cs",
            _cell(champ_rows, "mins_60", "ALL", "xp_clean_sheet"),
            _cell(cand_rows, "mins_60", "ALL", "xp_clean_sheet"),
        ),
        _arm("conceded", _combined_gkp_def(champ_rows), _combined_gkp_def(cand_rows)),
        _arm(
            "bonus",
            _cell(champ_rows, "mins_60", "ALL", "xp_bonus"),
            _cell(cand_rows, "mins_60", "ALL", "xp_bonus"),
        ),
    ]
    return {
        "rule_tickets": [115, 120, 128],
        "rule": "arm PASS = bias(|b|<=tau or |b| down) and/or demotion off structural/link-bias and/or |mse_share| down",
        "champion": champion,
        "incoming": INCOMING,
        "tau": TAU,
        "arms": arms,
        "flip_soft_pre_gate": all(a["pass"] for a in arms),
    }


def _race(reference: str, ref_df: pd.DataFrame, cand_df: pd.DataFrame) -> dict[str, Any]:
    windows = {
        t: (
            metrics_by_season_window(ref_df, target_column=t)["combined"],
            metrics_by_season_window(cand_df, target_column=t)["combined"],
        )
        for t in ("actual_points", "process_points")
    }
    ref_w = metrics_by_season_window(ref_df, target_column="blended_points")
    cand_w = metrics_by_season_window(cand_df, target_column="blended_points")
    verdict = evaluate_historical_promotion_gate(
        ref_w, cand_w, eval_target="blended_points", reference_windows=windows
    )
    return {
        "reference_seat": reference,
        "incoming": INCOMING,
        "passed": bool(verdict.passed),
        "eval_target": "blended_points",
        "primary_metric": verdict.primary_metric,
        "combined_primary_delta": float(verdict.combined_primary_delta),
        "segment_wins": int(verdict.segment_wins),
        "segment_deltas": {
            s: primary_metric_value(ref_w[s]) - primary_metric_value(cand_w[s])
            for s in ("cold_start", "early_mid", "late")
            if s in ref_w and s in cand_w
        },
        "guardrails_passed": bool(verdict.guardrails_passed),
        "reasons": list(verdict.reasons),
        "reference_primary": primary_metric_value(ref_w["combined"]),
        "incoming_primary": primary_metric_value(cand_w["combined"]),
        "reference_mae": float(evaluate_predictions(ref_df, target_column="blended_points")["mae"]),
        "incoming_mae": float(evaluate_predictions(cand_df, target_column="blended_points")["mae"]),
    }


def _outcome(races: list[dict[str, Any]]) -> dict[str, Any]:
    beaten = [r for r in races if r["passed"]]
    if not beaten:
        return {"action": "no_admission", "replace": None, "note": "incoming beat no seat"}
    worst = max(beaten, key=lambda r: (r["reference_primary"], r["reference_mae"]))
    action = "replace_worse_of_both" if len(beaten) == len(races) else "replace_beaten_seat"
    return {"action": action, "replace": worst["reference_seat"], "note": "#112 rule; higher primary = worse"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-slate", action="store_true", help="apply admission to model_selection.json")
    args = parser.parse_args()

    runner = _load_runner()
    selection = load_model_selection()
    frames = {m: _walkforward(m)[0] for m in (selection.champion, *selection.candidates, INCOMING)}

    soft = _soft(runner, selection.champion, frames[selection.champion], frames[INCOMING])
    OUT_SOFT.write_text(json.dumps(soft, indent=2) + "\n", encoding="utf-8")
    for arm in soft["arms"]:
        print(
            f"soft {arm['arm']}: pass={arm['pass']} bias {arm['champ_bias']:+.4f}→{arm['cand_bias']:+.4f} "
            f"|mse| {abs(arm['champ_mse_share']):.4f}→{abs(arm['cand_mse_share']):.4f} "
            f"label {arm['champ_label']}→{arm['cand_label']}",
            flush=True,
        )
    print(f"flip_soft_pre_gate={soft['flip_soft_pre_gate']}", flush=True)

    races = [_race(seat, frames[seat], frames[INCOMING]) for seat in selection.candidates]
    outcome = _outcome(races)
    admit = {
        "evaluation_season": SEASON,
        "gw_range": "1-38",
        "seed_season": SEED,
        "slate_before": list(selection.candidates),
        "races": races,
        "outcome": outcome,
    }
    for race in races:
        print(
            f"race vs {race['reference_seat']}: pass={race['passed']} Δpri={race['combined_primary_delta']:+.4f} "
            f"segs={race['segment_wins']}/3 guard={race['guardrails_passed']} {'; '.join(race['reasons'])}",
            flush=True,
        )
    print(f"outcome={outcome}", flush=True)

    if args.write_slate and outcome["replace"]:
        after = replace_candidate(selection, INCOMING, outcome["replace"])
        save_model_selection(after)
        admit["slate_after"] = list(after.candidates)
        print(f"slate → {after.candidates}", flush=True)
    OUT_ADMIT.write_text(json.dumps(admit, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
