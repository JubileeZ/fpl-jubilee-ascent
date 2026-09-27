"""AFK #133: layer-by-layer late-segment + MAE diagnosis, plus cheap ablations.

Walk-forwards Champion, goals_path, bonus_arm on 2025-26 GW1–38 seed 2024-25.
defence_link is the goals ledger plus shipped post-link scales (exact predict algebra).
Ablations undo/reapply those scales on the bonus_arm ledger. No model or slate mutation.

  uv run python docs/research/champion-component-gap/layer_diagnosis_133.py
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
from backtesting.walkforward import LEDGER_COMPONENTS, WalkforwardConfig, run_walkforward_backtest  # noqa: E402
from commands.backtest import resolve_backtest_data_dir, resolve_seed_processed_dir  # noqa: E402
from models.defence_link_challenger import _CS_SCALE, _GC_SCALE  # noqa: E402

SCRATCH = ROOT / ".tmp" / "agent"
TOPIC = ROOT / "docs" / "research" / "champion-component-gap"
OUT_GATE = TOPIC / "layer_diagnosis_133_gate.csv"
OUT_POS = TOPIC / "layer_diagnosis_133_late_position.csv"
OUT_COMP = TOPIC / "layer_diagnosis_133_late_component.csv"
OUT_JSON = TOPIC / "layer_diagnosis_133.json"

CHAMPION = "hold_chase_challenger"
GOALS = "goals_path_challenger"
DEFENCE = "defence_link_challenger"
BONUS = "bonus_arm_challenger"
SEASON = "2025-26"
SEED = "2024-25"
PROD_CS = float(_CS_SCALE)
PROD_GC = float(_GC_SCALE)
# Reduced-k_cs family precommitted from the published #124 grid (not fit on this run).
REDUCED_K_CS = (1.00, 1.10, 1.15)
LATE = (20, 38)
POS = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}
FOCUS = (
    "xp_minutes",
    "xp_goals",
    "xp_assists",
    "xp_clean_sheet",
    "xp_conceded",
    "xp_bonus",
    "xp_defcon",
)
KEY = ["player_id", "gameweek"]


def _cache_path(model: str) -> Path:
    return SCRATCH / f"wf_{model}_{SEASON}_{SEED}_1-38.parquet"


def _walkforward(model: str) -> pd.DataFrame:
    path = _cache_path(model)
    if path.exists():
        print(f"cache hit {path.name}", flush=True)
        return pd.read_parquet(path)
    data_dir = resolve_backtest_data_dir((ROOT / "data" / "archive" / SEASON / "processed").resolve())
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


def _num(frame: pd.DataFrame, col: str) -> pd.Series:
    return pd.to_numeric(frame[col], errors="coerce").fillna(0.0)


def _apply_scales(
    base: pd.DataFrame,
    *,
    k_cs: float,
    k_gc: float,
    positions: set[int] | None = None,
) -> pd.DataFrame:
    out = base.copy()
    cs0 = _num(out, "xp_clean_sheet")
    gc0 = _num(out, "xp_conceded")
    pts0 = _num(out, "projected_points")
    mask = pd.Series(True, index=out.index) if positions is None else out["position_id"].isin(positions)
    k_cs_row = mask.map({True: k_cs, False: 1.0}).astype(float)
    k_gc_row = mask.map({True: k_gc, False: 1.0}).astype(float)
    out["xp_clean_sheet"] = cs0 * k_cs_row
    out["xp_conceded"] = gc0 * k_gc_row
    out["projected_points"] = pts0 + (k_cs_row - 1.0) * cs0 + (k_gc_row - 1.0) * gc0
    return out


def _undo_defence(bonus: pd.DataFrame) -> pd.DataFrame:
    """Reverse shipped post-link scales. Bonus allocation ran before that scale."""
    out = bonus.copy()
    cs = _num(out, "xp_clean_sheet")
    gc = _num(out, "xp_conceded")
    cs0 = cs / PROD_CS
    gc0 = gc / PROD_GC
    out["xp_clean_sheet"] = cs0
    out["xp_conceded"] = gc0
    out["projected_points"] = _num(out, "projected_points") - (PROD_CS - 1.0) * cs0 - (PROD_GC - 1.0) * gc0
    return out


def _keys(frame: pd.DataFrame) -> pd.DataFrame:
    return frame[KEY].drop_duplicates()


def _quality(name: str, frame: pd.DataFrame) -> dict[str, Any]:
    gw = pd.to_numeric(frame["gameweek"], errors="coerce")
    dup = int(frame.duplicated(KEY).sum())
    nulls = {
        col: int(frame[col].isna().sum())
        for col in ("projected_points", "actual_points", "process_points", "blended_points", "position_id")
        if col in frame.columns
    }
    pred_cols = [c for c in LEDGER_COMPONENTS if c in frame.columns]
    residual = _num(frame, "projected_points") - frame[pred_cols].apply(pd.to_numeric, errors="coerce").fillna(0.0).sum(axis=1)
    outside = int(((gw < 1) | (gw > 38)).sum())
    pos_bad = int((~frame["position_id"].isin(POS)).sum()) if "position_id" in frame.columns else -1
    report = {
        "model": name,
        "rows": int(len(frame)),
        "columns": list(frame.columns),
        "gw_min": int(gw.min()) if len(frame) else None,
        "gw_max": int(gw.max()) if len(frame) else None,
        "duplicate_player_gw": dup,
        "nulls": nulls,
        "rows_outside_gw_1_38": outside,
        "bad_position_id": pos_bad,
        "max_abs_ledger_residual": float(residual.abs().max()) if len(frame) else None,
    }
    print(
        f"quality {name}: rows={report['rows']} gw={report['gw_min']}-{report['gw_max']} "
        f"dups={dup} outside={outside} bad_pos={pos_bad} "
        f"max|ledger|={report['max_abs_ledger_residual']:.3e} nulls={nulls}",
        flush=True,
    )
    return report


def _align_check(left: pd.DataFrame, right: pd.DataFrame, cols: list[str], label: str) -> float:
    merged = left[KEY + cols].merge(right[KEY + cols], on=KEY, suffixes=("_l", "_r"))
    if len(merged) != len(left):
        raise RuntimeError(f"{label}: key mismatch {len(merged)} vs {len(left)}")
    worst = 0.0
    for col in cols:
        delta = (pd.to_numeric(merged[f"{col}_l"], errors="coerce").fillna(0.0) - pd.to_numeric(merged[f"{col}_r"], errors="coerce").fillna(0.0)).abs()
        worst = max(worst, float(delta.max()))
    print(f"align {label}: rows={len(merged)} max|Δ|={worst:.3e}", flush=True)
    if worst > 1e-6:
        raise RuntimeError(f"{label} max abs delta {worst} > 1e-6; scale algebra does not match")
    return worst


def _gate_row(label: str, kind: str, champ: pd.DataFrame, cand: pd.DataFrame, *, note: str) -> dict[str, Any]:
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
    late = cand[(cand["gameweek"] >= LATE[0]) & (cand["gameweek"] <= LATE[1])]
    late_c = champ[(champ["gameweek"] >= LATE[0]) & (champ["gameweek"] <= LATE[1])]
    return {
        "label": label,
        "kind": kind,
        "note": note,
        "passed": bool(verdict.passed),
        "primary_metric": verdict.primary_metric,
        "combined_primary_delta": float(verdict.combined_primary_delta),
        "segment_wins": int(verdict.segment_wins),
        "guardrails_passed": bool(verdict.guardrails_passed),
        "reasons": "; ".join(verdict.reasons),
        "cold_start_delta": segs.get("cold_start"),
        "early_mid_delta": segs.get("early_mid"),
        "late_delta": segs.get("late"),
        "champ_late_regret": float(primary_metric_value(blend_c["late"])),
        "cand_late_regret": float(primary_metric_value(blend_a["late"])),
        "realized_mae_champ": float(realized_c["combined"]["mae"]),
        "realized_mae_cand": float(realized_a["combined"]["mae"]),
        "process_mae_champ": float(process_c["combined"]["mae"]),
        "process_mae_cand": float(process_a["combined"]["mae"]),
        "realized_mae_delta": float(realized_c["combined"]["mae"]) - float(realized_a["combined"]["mae"]),
        "process_mae_delta": float(process_c["combined"]["mae"]) - float(process_a["combined"]["mae"]),
        "late_blend_mae_champ": float(evaluate_predictions(late_c, target_column="blended_points")["mae"]),
        "late_blend_mae_cand": float(evaluate_predictions(late, target_column="blended_points")["mae"]),
        "late_realized_mae_champ": float(evaluate_predictions(late_c, target_column="actual_points")["mae"]),
        "late_realized_mae_cand": float(evaluate_predictions(late, target_column="actual_points")["mae"]),
        "late_process_mae_champ": float(evaluate_predictions(late_c, target_column="process_points")["mae"]),
        "late_process_mae_cand": float(evaluate_predictions(late, target_column="process_points")["mae"]),
        "xmins_mae_champ": float((blend_c["combined"].get("minutes_forecast_metrics") or {}).get("mae", float("nan"))),
        "xmins_mae_cand": float((blend_a["combined"].get("minutes_forecast_metrics") or {}).get("mae", float("nan"))),
        "abs_bias_champ": abs(float(blend_c["combined"]["bias"])),
        "abs_bias_cand": abs(float(blend_a["combined"]["bias"])),
        "spearman_champ": float(blend_c["combined"]["spearman"] or float("nan")),
        "spearman_cand": float(blend_a["combined"]["spearman"] or float("nan")),
    }


def _slice_late(frame: pd.DataFrame) -> pd.DataFrame:
    gw = pd.to_numeric(frame["gameweek"], errors="coerce")
    return frame[(gw >= LATE[0]) & (gw <= LATE[1])].copy()


def _position_rows(label: str, champ: pd.DataFrame, cand: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    champ_l, cand_l = _slice_late(champ), _slice_late(cand)
    regret_c = _regret_by_position(champ_l)
    regret_a = _regret_by_position(cand_l)
    for pid, pname in POS.items():
        c = champ_l[champ_l["position_id"] == pid]
        a = cand_l[cand_l["position_id"] == pid]
        row: dict[str, Any] = {
            "label": label,
            "position": pname,
            "position_id": pid,
            "rows": int(len(a)),
            "regret_champ": regret_c.get(pname, 0.0),
            "regret_cand": regret_a.get(pname, 0.0),
        }
        row["regret_delta"] = row["regret_champ"] - row["regret_cand"]
        for target, key in (
            ("blended_points", "blend"),
            ("actual_points", "realized"),
            ("process_points", "process"),
        ):
            mae_c = float((_num(c, "projected_points") - _num(c, target)).abs().mean())
            mae_a = float((_num(a, "projected_points") - _num(a, target)).abs().mean())
            row[f"{key}_mae_champ"] = mae_c
            row[f"{key}_mae_cand"] = mae_a
            row[f"{key}_mae_delta"] = mae_c - mae_a
        rows.append(row)
    # Parts of mean late regret: sum of position attributions.
    rows.append(
        {
            "label": label,
            "position": "ALL",
            "position_id": 0,
            "rows": int(len(cand_l)),
            "regret_champ": sum(regret_c.values()),
            "regret_cand": sum(regret_a.values()),
            "regret_delta": sum(regret_c.values()) - sum(regret_a.values()),
            "blend_mae_champ": float((_num(champ_l, "projected_points") - _num(champ_l, "blended_points")).abs().mean()),
            "blend_mae_cand": float((_num(cand_l, "projected_points") - _num(cand_l, "blended_points")).abs().mean()),
            "blend_mae_delta": float((_num(champ_l, "projected_points") - _num(champ_l, "blended_points")).abs().mean())
            - float((_num(cand_l, "projected_points") - _num(cand_l, "blended_points")).abs().mean()),
            "realized_mae_champ": float((_num(champ_l, "projected_points") - _num(champ_l, "actual_points")).abs().mean()),
            "realized_mae_cand": float((_num(cand_l, "projected_points") - _num(cand_l, "actual_points")).abs().mean()),
            "realized_mae_delta": float((_num(champ_l, "projected_points") - _num(champ_l, "actual_points")).abs().mean())
            - float((_num(cand_l, "projected_points") - _num(cand_l, "actual_points")).abs().mean()),
            "process_mae_champ": float((_num(champ_l, "projected_points") - _num(champ_l, "process_points")).abs().mean()),
            "process_mae_cand": float((_num(cand_l, "projected_points") - _num(cand_l, "process_points")).abs().mean()),
            "process_mae_delta": float((_num(champ_l, "projected_points") - _num(champ_l, "process_points")).abs().mean())
            - float((_num(cand_l, "projected_points") - _num(cand_l, "process_points")).abs().mean()),
        }
    )
    return rows


def _regret_by_position(frame: pd.DataFrame, target: str = "blended_points") -> dict[str, float]:
    """Mean late Decision Regret attributed to top-11 swaps. Positions sum to mean regret."""
    totals = {name: 0.0 for name in POS.values()}
    n_gw = 0
    for _, group in frame.groupby("gameweek"):
        n_gw += 1
        count = min(11, len(group))
        predicted = group.nlargest(count, "projected_points")
        oracle = group.nlargest(count, target)
        pred_ids = set(predicted["player_id"])
        oracle_ids = set(oracle["player_id"])
        only_oracle = oracle[~oracle["player_id"].isin(pred_ids)]
        only_pred = predicted[~predicted["player_id"].isin(oracle_ids)]
        for pname, pid in ((n, i) for i, n in POS.items()):
            gained = float(_num(only_oracle[only_oracle["position_id"] == pid], target).sum())
            lost = float(_num(only_pred[only_pred["position_id"] == pid], target).sum())
            totals[pname] += gained - lost
    if n_gw == 0:
        return totals
    return {name: value / n_gw for name, value in totals.items()}


def _component_rows(label: str, champ: pd.DataFrame, cand: pd.DataFrame) -> list[dict[str, Any]]:
    champ_l, cand_l = _slice_late(champ), _slice_late(cand)
    merged = champ_l[KEY + ["position_id"] + list(LEDGER_COMPONENTS)].merge(
        cand_l[KEY + list(LEDGER_COMPONENTS)],
        on=KEY,
        suffixes=("_champ", "_cand"),
    )
    rows: list[dict[str, Any]] = []
    for comp in LEDGER_COMPONENTS:
        act = f"actual_{comp}"
        if act not in champ_l.columns:
            continue
        both = merged.merge(champ_l[KEY + [act]], on=KEY)
        err_c = pd.to_numeric(both[f"{comp}_champ"], errors="coerce").fillna(0.0) - pd.to_numeric(both[act], errors="coerce").fillna(0.0)
        err_a = pd.to_numeric(both[f"{comp}_cand"], errors="coerce").fillna(0.0) - pd.to_numeric(both[act], errors="coerce").fillna(0.0)
        rows.append(
            {
                "label": label,
                "position": "ALL",
                "component": comp,
                "rows": int(len(both)),
                "mae_champ": float(err_c.abs().mean()),
                "mae_cand": float(err_a.abs().mean()),
                "mae_delta": float(err_c.abs().mean() - err_a.abs().mean()),
                "bias_champ": float(err_c.mean()),
                "bias_cand": float(err_a.mean()),
                "mean_proj_delta_cand_minus_champ": float(
                    (pd.to_numeric(both[f"{comp}_cand"], errors="coerce").fillna(0.0) - pd.to_numeric(both[f"{comp}_champ"], errors="coerce").fillna(0.0)).mean()
                ),
            }
        )
        if comp not in FOCUS:
            continue
        for pid, pname in POS.items():
            sub = both[both["position_id"] == pid]
            if sub.empty:
                continue
            e_c = pd.to_numeric(sub[f"{comp}_champ"], errors="coerce").fillna(0.0) - pd.to_numeric(sub[act], errors="coerce").fillna(0.0)
            e_a = pd.to_numeric(sub[f"{comp}_cand"], errors="coerce").fillna(0.0) - pd.to_numeric(sub[act], errors="coerce").fillna(0.0)
            rows.append(
                {
                    "label": label,
                    "position": pname,
                    "component": comp,
                    "rows": int(len(sub)),
                    "mae_champ": float(e_c.abs().mean()),
                    "mae_cand": float(e_a.abs().mean()),
                    "mae_delta": float(e_c.abs().mean() - e_a.abs().mean()),
                    "bias_champ": float(e_c.mean()),
                    "bias_cand": float(e_a.mean()),
                    "mean_proj_delta_cand_minus_champ": float(
                        (pd.to_numeric(sub[f"{comp}_cand"], errors="coerce").fillna(0.0) - pd.to_numeric(sub[f"{comp}_champ"], errors="coerce").fillna(0.0)).mean()
                    ),
                }
            )
    return rows


def main() -> int:
    SCRATCH.mkdir(parents=True, exist_ok=True)
    champ = _walkforward(CHAMPION)
    goals = _walkforward(GOALS)
    bonus = _walkforward(BONUS)
    quality = [_quality(CHAMPION, champ), _quality(GOALS, goals), _quality(BONUS, bonus)]
    for frame in (champ, goals, bonus):
        if int(frame.duplicated(KEY).sum()) or int(frame["gameweek"].min()) != 1 or int(frame["gameweek"].max()) != 38:
            raise RuntimeError("quality gate failed")
        if len(_keys(frame)) != len(_keys(champ)):
            raise RuntimeError("row-count mismatch across models")
    if _keys(champ).merge(_keys(goals), on=KEY).shape[0] != len(champ):
        raise RuntimeError("champion/goals keys differ")
    if _keys(champ).merge(_keys(bonus), on=KEY).shape[0] != len(champ):
        raise RuntimeError("champion/bonus keys differ")

    goals_bonus = _undo_defence(bonus)
    align = {
        "bonus_unscaled_cs_vs_goals": _align_check(goals, goals_bonus, ["xp_clean_sheet", "xp_conceded", "xp_goals"], "undo vs goals"),
        "goals_vs_bonus_goals": _align_check(goals, bonus, ["xp_goals", "xp_assists", "xp_minutes"], "shared attack/minutes"),
    }
    defence = _apply_scales(goals, k_cs=PROD_CS, k_gc=PROD_GC)
    _quality(DEFENCE, defence)

    configs: list[tuple[str, str, pd.DataFrame, str]] = [
        (GOALS, "layer", goals, "goals weight scale only"),
        (DEFENCE, "layer", defence, "goals + shipped k_cs/k_gc (algebraic)"),
        (BONUS, "layer", bonus, "goals + defence scales + bonus weights/T"),
        ("goals_bonus_no_def", "ablation", goals_bonus, "bonus weights/T; k_cs=k_gc=1"),
        (
            "def_gkp_def_only",
            "ablation",
            _apply_scales(goals_bonus, k_cs=PROD_CS, k_gc=PROD_GC, positions={1, 2}),
            "bonus + prod scales on GKP+DEF only",
        ),
    ]
    for k_cs in REDUCED_K_CS:
        configs.append(
            (
                f"reduced_k_cs_{k_cs:.2f}",
                "ablation",
                _apply_scales(goals_bonus, k_cs=k_cs, k_gc=PROD_GC),
                f"bonus + k_cs={k_cs:.2f} (precommitted) k_gc=prod",
            )
        )

    gate_rows = [_gate_row(label, kind, champ, cand, note=note) for label, kind, cand, note in configs]
    for row in gate_rows:
        flag = "PASS" if row["passed"] else "fail"
        print(
            f"{flag} {row['label']}: segs={row['segment_wins']}/3 "
            f"Δpri={row['combined_primary_delta']:+.4f} late={row['late_delta']:+.4f} "
            f"RmaeΔ={row['realized_mae_delta']:+.4f} PmaeΔ={row['process_mae_delta']:+.4f} | {row['reasons'] or 'ok'}",
            flush=True,
        )

    # Late breakdown for shipped layers + the three named ablation families' primary rows.
    breakdown_labels = {GOALS, DEFENCE, BONUS, "goals_bonus_no_def", "def_gkp_def_only", "reduced_k_cs_1.10"}
    pos_rows: list[dict[str, Any]] = []
    comp_rows: list[dict[str, Any]] = []
    for label, _kind, cand, _note in configs:
        if label not in breakdown_labels:
            continue
        pos_rows.extend(_position_rows(label, champ, cand))
        comp_rows.extend(_component_rows(label, champ, cand))

    gate_frame = pd.DataFrame(gate_rows)
    pos_frame = pd.DataFrame(pos_rows)
    comp_frame = pd.DataFrame(comp_rows)
    gate_frame.to_csv(OUT_GATE, index=False)
    pos_frame.to_csv(OUT_POS, index=False)
    comp_frame.to_csv(OUT_COMP, index=False)

    # Regret identity: ALL position regret_cand must match cand_late_regret.
    identity: list[dict[str, float | str]] = []
    for label, kind, _cand, _note in configs:
        if label not in breakdown_labels:
            continue
        gate = gate_frame.loc[gate_frame["label"] == label].iloc[0]
        all_row = pos_frame[(pos_frame["label"] == label) & (pos_frame["position"] == "ALL")].iloc[0]
        gap = float(all_row["regret_cand"]) - float(gate["cand_late_regret"])
        identity.append({"label": label, "kind": kind, "regret_parts_minus_gate": gap})
        print(f"identity {label}: position-sum regret − gate late regret = {gap:.3e}", flush=True)

    minute_delta = (
        champ[["player_id", "gameweek", "projected_minutes"]]
        .merge(goals[["player_id", "gameweek", "projected_minutes"]], on=KEY, suffixes=("_c", "_g"))
    )
    minute_abs = (
        pd.to_numeric(minute_delta["projected_minutes_g"], errors="coerce").fillna(0.0)
        - pd.to_numeric(minute_delta["projected_minutes_c"], errors="coerce").fillna(0.0)
    ).abs()
    payload = {
        "minutes_forecast_vs_champion": {
            "rows": int(len(minute_abs)),
            "rows_differ": int((minute_abs > 1e-9).sum()),
            "max_abs": float(minute_abs.max()),
            "mean_abs": float(minute_abs.mean()),
        },
        "season": SEASON,
        "seed": SEED,
        "gw": "1-38",
        "late": list(LATE),
        "prod_k_cs": PROD_CS,
        "prod_k_gc": PROD_GC,
        "reduced_k_cs_precommitted": list(REDUCED_K_CS),
        "quality": quality,
        "align_max_abs": align,
        "any_pass": bool(gate_frame["passed"].any()),
        "identity": identity,
        "sample_champion": json.loads(
            champ.head(2)[KEY + ["position_id", "projected_points", "actual_points", "process_points", "blended_points"]].to_json(
                orient="records"
            )
        ),
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT_GATE.name} {OUT_POS.name} {OUT_COMP.name} {OUT_JSON.name}", flush=True)
    print(f"any_pass={payload['any_pass']}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
