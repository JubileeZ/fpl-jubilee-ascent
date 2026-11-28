"""Run Track B state-stratified xMins (t+0..t+5, GKP vs all) and Oracle Participation State diagnostics for m1_gkp_solo on S-1."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backtesting import walkforward  # noqa: E402
from backtesting.walkforward import (  # noqa: E402
    WalkforwardConfig,
    load_gameweek_deadlines,
    run_walkforward_backtest,
)
from commands.evaluate_minutes import (  # noqa: E402
    build_minutes_evaluation_frame,
    compute_horizon_minutes_decay,
    compute_minutes_metrics,
    evaluate_minutes_from_eval_frames,
    extract_minutes_prediction_frame,
)
from features.builder import build_features, history_before_target  # noqa: E402
from models import get_model  # noqa: E402

PROTOTYPE_PATH = Path(__file__).resolve().with_name("prototypes.py")
OUT_CSV = Path(__file__).resolve().with_name("s1_split_minutes_diagnostics.csv")
OUT_ORACLE_JSON = Path(__file__).resolve().with_name("s1_oracle_parity_check.json")
S1_DATA_DIR = ROOT / "data/archive/2025-26/processed"
S1_SEED_DIR = ROOT / "data/archive/2024-25/processed"


def _load_prototype_cls() -> type:
    spec = importlib.util.spec_from_file_location("m1_gkp_solo_diag", PROTOTYPE_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["m1_gkp_solo_diag"] = mod
    spec.loader.exec_module(mod)
    return mod.PROTOTYPES["m1_gkp_solo"]


def _flatten_slice(
    *,
    horizon_step: int,
    slice_name: str,
    model_name: str,
    strat: dict[str, Any],
    summary_mae: float | None = None,
    summary_rmse: float | None = None,
    summary_bias: float | None = None,
    summary_overall_mae: float | None = None,
    brier_score: float | None = None,
    brier_start: float | None = None,
    brier_sub: float | None = None,
    brier_dnp: float | None = None,
    sample_count: int | None = None,
    active_count: int | None = None,
) -> dict[str, Any]:
    states = strat["states"]
    cond = strat["conditional_duration"]
    p60 = strat["p_60_if_start"]
    return {
        "horizon_step": horizon_step,
        "slice": slice_name,
        "model": model_name,
        "sample_count": sample_count if sample_count is not None else strat.get("sample_count"),
        "active_count": active_count if active_count is not None else strat.get("active_count"),
        "active_mae": summary_mae if summary_mae is not None else strat.get("mae"),
        "active_rmse": summary_rmse,
        "active_bias": summary_bias if summary_bias is not None else strat.get("bias"),
        "overall_mae": summary_overall_mae,
        "brier_score": brier_score,
        "brier_start": brier_start if brier_start is not None else states["start"]["brier"],
        "brier_sub": brier_sub if brier_sub is not None else states["sub_in"]["brier"],
        "brier_dnp": brier_dnp if brier_dnp is not None else states["dnp"]["brier"],
        "start_actual_rate": states["start"]["actual_rate"],
        "start_mean_prob": states["start"]["mean_predicted_prob"],
        "start_cal_err": states["start"]["calibration_error"],
        "sub_in_cal_err": states["sub_in"]["calibration_error"],
        "dnp_cal_err": states["dnp"]["calibration_error"],
        "false_start_rate": strat["false_start_rate"],
        "missed_starter_rate": strat["missed_starter_rate"],
        "xmins_if_start_mae": cond["start"]["mae"],
        "xmins_if_start_bias": cond["start"]["bias"],
        "xmins_if_sub_in_mae": cond["sub_in"]["mae"],
        "p60_if_start_cal_err": p60["calibration_error"],
        "p60_if_start_brier": p60["brier"],
    }


def run_split_minutes_diagnostics(horizon: int = 6) -> list[dict[str, Any]]:
    cand_cls = _load_prototype_cls()
    cand_model = cand_cls()
    champ_model = get_model("def_xg_shrink_challenger")

    df_perf = pd.read_parquet(S1_DATA_DIR / "player_performances.parquet")
    deadlines = load_gameweek_deadlines(S1_DATA_DIR)
    completed_gws = sorted(df_perf["gameweek_id"].dropna().unique().astype(int).tolist())
    max_gw = completed_gws[-1]

    cand_by_step: dict[int, list[pd.DataFrame]] = {step: [] for step in range(horizon)}
    champ_by_step: dict[int, list[pd.DataFrame]] = {step: [] for step in range(horizon)}

    for gw in completed_gws:
        deadline = deadlines.get(gw)
        eff_h = min(horizon, max_gw - gw + 1)
        df_feat = build_features(
            S1_DATA_DIR,
            gw,
            horizon=eff_h,
            seed_processed_dir=S1_SEED_DIR,
            use_archive_seed=False,
            as_of_gw=gw,
            history_before_gw=gw,
            target_deadline=deadline,
            minutes_prior_source="seed_state",
        )
        df_feat["native_rules_version"] = "2025-26"
        hist_before = history_before_target(df_perf, gw, deadline, require_kickoff_time=False)

        cand_model.fit(hist_before)
        champ_model.fit(hist_before)

        c_preds = extract_minutes_prediction_frame(cand_model, df_feat, horizon=eff_h, issue_gw=gw)
        ch_preds = extract_minutes_prediction_frame(champ_model, df_feat, horizon=eff_h, issue_gw=gw)

        for step in range(eff_h):
            eval_gw = gw + step
            c_step = build_minutes_evaluation_frame(c_preds, df_perf, eval_gw)
            ch_step = build_minutes_evaluation_frame(ch_preds, df_perf, eval_gw)
            c_step["gameweek"] = eval_gw
            ch_step["gameweek"] = eval_gw
            cand_by_step[step].append(c_step)
            champ_by_step[step].append(ch_step)

    t0_cand = pd.concat(cand_by_step[0], ignore_index=True)
    t0_champ = pd.concat(champ_by_step[0], ignore_index=True)
    t0_gate_all = evaluate_minutes_from_eval_frames(t0_champ, t0_cand)
    t0_gate_gkp = evaluate_minutes_from_eval_frames(
        t0_champ[t0_champ["position_id"] == 1],
        t0_cand[t0_cand["position_id"] == 1],
    )

    decay = compute_horizon_minutes_decay(cand_by_step, champ_by_step)
    rows: list[dict[str, Any]] = []
    for step in range(horizon):
        c_df = pd.concat(cand_by_step[step], ignore_index=True)
        ch_df = pd.concat(champ_by_step[step], ignore_index=True)
        c_all = compute_minutes_metrics(c_df)
        ch_all = compute_minutes_metrics(ch_df)
        c_gkp = compute_minutes_metrics(c_df[c_df["position_id"] == 1])
        ch_gkp = compute_minutes_metrics(ch_df[ch_df["position_id"] == 1])

        for slice_name, model_name, mm in (
            ("all", "m1_gkp_solo", c_all),
            ("all", "def_xg_shrink_challenger", ch_all),
            ("GKP", "m1_gkp_solo", c_gkp),
            ("GKP", "def_xg_shrink_challenger", ch_gkp),
        ):
            row = _flatten_slice(
                horizon_step=step,
                slice_name=slice_name,
                model_name=model_name,
                strat=mm.stratified,
                summary_mae=mm.mae,
                summary_rmse=mm.rmse,
                summary_bias=mm.bias,
                summary_overall_mae=mm.overall_mae,
                brier_score=mm.brier_score,
                brier_start=mm.brier_start,
                brier_sub=mm.brier_sub,
                brier_dnp=mm.brier_dnp,
                sample_count=mm.sample_count,
                active_count=mm.active_count,
            )
            if step == 0:
                gate = t0_gate_all if slice_name == "all" else t0_gate_gkp
                row["t0_tier1_passed"] = gate.passed
                row["t0_delta_mae"] = gate.delta_mae
                row["t0_bootstrap_p"] = gate.bootstrap_p
            else:
                key = f"t+{step}"
                row["t0_tier1_passed"] = None
                row["t0_delta_mae"] = (
                    (ch_gkp.mae - c_gkp.mae) if slice_name == "GKP" else decay[key]["delta_mae"]
                )
                row["t0_bootstrap_p"] = None
            rows.append(row)

    pd.DataFrame(rows).to_csv(OUT_CSV, index=False)
    return rows


def run_oracle_parity_sanity() -> dict[str, Any]:
    cand_cls = _load_prototype_cls()
    orig_get_model = walkforward.get_model
    walkforward.get_model = lambda name: cand_cls() if name == "m1_gkp_solo" else orig_get_model(name)
    try:
        cand_res = run_walkforward_backtest(
            WalkforwardConfig(
                model_name="m1_gkp_solo",
                data_dir=S1_DATA_DIR,
                start_gw=1,
                end_gw=5,
                seed_processed_dir=S1_SEED_DIR,
                oracle_minutes=True,
            )
        )
        champ_res = run_walkforward_backtest(
            WalkforwardConfig(
                model_name="def_xg_shrink_challenger",
                data_dir=S1_DATA_DIR,
                start_gw=1,
                end_gw=5,
                seed_processed_dir=S1_SEED_DIR,
                oracle_minutes=True,
            )
        )
    finally:
        walkforward.get_model = orig_get_model

    payload = {
        "gw_range": "1-5",
        "cand_oracle_enabled": cand_res.metrics["oracle_participation_state_enabled"],
        "champ_oracle_enabled": champ_res.metrics["oracle_participation_state_enabled"],
        "cand_all_players": cand_res.metrics["oracle_event_pools"]["all_players"],
        "champ_all_players": champ_res.metrics["oracle_event_pools"]["all_players"],
        "cand_appeared": cand_res.metrics["oracle_event_pools"]["appeared"],
        "champ_appeared": champ_res.metrics["oracle_event_pools"]["appeared"],
        "df_eval_exact_equal": bool(cand_res.df_eval.equals(champ_res.df_eval)),
    }
    OUT_ORACLE_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return payload


def main() -> None:
    rows = run_split_minutes_diagnostics(horizon=6)
    oracle = run_oracle_parity_sanity()
    df = pd.DataFrame(rows)
    print("=== Track B S-1 Split Diagnostics Summary (GKP vs all, t+0..t+5) ===")
    cols = [
        "horizon_step",
        "slice",
        "model",
        "active_mae",
        "active_bias",
        "brier_score",
        "false_start_rate",
        "missed_starter_rate",
        "t0_delta_mae",
        "t0_bootstrap_p",
    ]
    print(df[cols].to_string(index=False))
    print("=== Oracle Participation State GW1-5 Sanity ===")
    print(json.dumps(oracle, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
