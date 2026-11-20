"""CLI to tune and certify ADR 0070 sparse Champion confirmation and Early-Harm."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from clients.env_loader import configure_utf8_stdio, load_env

load_env()
configure_utf8_stdio()

from backtesting.evaluation_protocol import validate_protocol
from backtesting.sparse_certification import (
    DEFAULT_NUM_SIMULATIONS,
    certify_sparse_confirmation,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "docs" / "research" / "sparse-confirmation-certification"

_BOUND_METRICS = (
    "false_slate_pass",
    "false_null_ever_pass",
    "correct_confirmation_by_gw38",
    "confirm_gw15",
    "confirm_gw30",
    "confirm_gw38",
    "terminal_false_exclusion",
    "statistical_false_exclusion_flag",
    "gw1_4_false_exclusion",
    "harmful_terminal_exclusion",
    "harmful_statistical_flag",
    "harmful_gw1_4_exclusion",
    "harmful_any_detected",
)


def _flatten_scenario_rows(run_role: str, run_payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for scenario in run_payload["scenarios"]:
        row: dict[str, Any] = {
            "run_role": run_role,
            "seed": run_payload["seed"],
            "statistical_early_harm_mode": run_payload["statistical_early_harm_mode"],
            "num_simulations": run_payload["num_simulations"],
            "scenario_id": scenario["scenario_id"],
            "category": scenario["category"],
            "slate_size": scenario["slate_size"],
            "dependence_regime": scenario["dependence_regime"],
            "safeguards_pass_from_gw": scenario["safeguards_pass_from_gw"],
            "is_primary_power": scenario["is_primary_power"],
            "has_null_finalist": scenario["has_null_finalist"],
            "has_improving_finalist": scenario["has_improving_finalist"],
            "has_non_harmful_finalist": scenario["has_non_harmful_finalist"],
            "has_harmful_finalist": scenario["has_harmful_finalist"],
        }
        for metric in _BOUND_METRICS:
            stats_dict = scenario[metric]
            row[f"{metric}_k"] = stats_dict["k"]
            row[f"{metric}_n"] = stats_dict["n"]
            row[f"{metric}_rate"] = f"{stats_dict['rate']:.6f}"
            row[f"{metric}_lower95"] = f"{stats_dict['lower_95']:.6f}"
            row[f"{metric}_upper95"] = f"{stats_dict['upper_95']:.6f}"
        rows.append(row)
    return rows


def _build_v2_protocol_declaration(result: dict[str, Any]) -> dict[str, Any] | None:
    cfg = result.get("certified_protocol_config")
    if not result["certified"] or not isinstance(cfg, dict):
        return None
    declaration = {
        "version": 2,
        "windows": [
            {
                "season": cfg.get("confirmation_season", "2026-27"),
                "role": "live",
                "weight": 1.0,
                "scored_deadlines": list(range(1, 39)),
            }
        ],
        "issue_cutoff": "deadline",
        "horizon": 6,
        "season_end_clipping": True,
        "native_rules": "native-2026-27-v1",
        "anchor": "neutral-gw1-opening-anchor",
        "strategic_settings": "adr0065-strategic",
        "chip_calendar": "shared-causal-calendar",
        "quality_policy": "certified-zero-gap",
        "forecast_guards": "s1-derived-15-guards",
        "statistical_procedure": "kendall-pw-hac-v2",
        "approval_references": ["ADR-0070-SPARSE-CERT-201"],
        "look_schedule": [15, 30, 38],
        "calibrated_superiority_alphas": cfg["calibrated_superiority_alphas"],
        "gw1_4_material_loss_limit": cfg["gw1_4_material_loss_limit"],
        "completed_segments": {
            str(cp): [[int(lo), int(hi)] for lo, hi in pairs]
            for cp, pairs in cfg["completed_segments"].items()
        }
        if cfg.get("completed_segments")
        else {
            "15": [[1, 4]],
            "30": [[1, 4], [5, 19]],
            "38": [[1, 4], [5, 19], [20, 38]],
        },
        "statistical_early_harm_mode": cfg["statistical_early_harm_mode"],
        "unused_alpha_policy": "discard",
        "expiry_rules": {
            "timezone": "UTC",
            "gw38_expiry_hours_after_last_kickoff": float(cfg["gw38_expiry_hours_after_last_kickoff"]),
        },
        "certification_digest": result["certification_digest"],
        "statistical_protocol_hash": result["statistical_protocol_hash"],
    }
    validate_protocol(declaration)
    return declaration


def _render_research_note(result: dict[str, Any], summary_rows: list[dict[str, Any]]) -> str:
    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
    today = now_iso[:10]
    tuning = result["tuning"]
    alphas = tuning["calibrated_superiority_alphas"]
    parity = result["parity_check"]
    primary = result["primary_run"]
    p_gates = primary["gates"]
    fallback = result["fallback_run"]
    f_gates = fallback["gates"] if fallback is not None else None
    active_run_role = "fallback_advisory" if result["certified_mode"] == "advisory" else "primary_enforced"
    active_rows = [r for r in summary_rows if r["run_role"] == active_run_role]
    if not active_rows:
        active_rows = [r for r in summary_rows if r["run_role"] == "primary_enforced"]

    lines: list[str] = [
        "# Sparse Champion Confirmation & Statistical Early-Harm Certification",
        "",
        f"**Updated**: {now_iso}  ",
        f"**Data stamp**: Synthetic 38-GW paths (`N={primary['num_simulations']:,}`/scenario; `2026-27` untouched) — {today}  ",
        "**Season**: Synthetic Multi-Slate (`M=1`, `M=2`, 38 GWs)  ",
        f"**Status**: {'Active — Certified' if result['certified'] else 'Active — Certification Blocked'}  ",
        "**Purpose**: Calibrate and certify ADR 0070 sparse (`GW15`/`GW30`/`GW38`) confirmation thresholds, GW1–4 net-points material-loss floor, and statistical Early-Harm mode across shared-Champion correlated paths without accessing `2026-27` outcomes.  ",
        "**Scope**: Preregistered synthetic certification (`seed=20101` tuning, `seed=20102` primary held-out, `seed=20103` predeclared advisory fallback); excludes live `2026-27` validation outcomes and MILP replay execution.  ",
        "**Related**: [ADR 0070](../../adr/0070-weekly-planner-selection-and-champion-adoption.md) · [Implementation Spec](../../product/champion-adoption-implementation.md) · Issue [#201](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/201)  ",
        "**Artifact**: [certification_summary.csv](certification_summary.csv) · [certification_result.json](certification_result.json) · [preregistration_manifest.json](preregistration_manifest.json) · [parity_check.json](parity_check.json)",
        "",
        "## Sources",
        "",
        "- **Repository code**: `backtesting/sparse_certification.py`, `backtesting/evidence_statistics.py`, `backtesting/promotion_evidence.py`, `backtesting/evaluation_protocol.py`",
        "- **Specifications**: `docs/adr/0070-weekly-planner-selection-and-champion-adoption.md`, `docs/product/champion-adoption-implementation.md`, issues `#195`, `#196`, `#201`",
        "- **Scale reference**: `docs/research/backtesting-promotion-foundation/smoke_gate_calibration.csv` (`4.0` pts/GW paired differential SD) & `docs/adr/0069-annual-rolling-validation-and-dual-tier-promotion.md` (`18.56` pts/GW Champion dispersion)",
        "",
        "**Source boundary**: Simulation-only certification on independent non-live synthetic seeds (`20101`, `20102`, `20103`). Zero `2026-27` outcomes inspected or used. Live Champion adoption additionally requires empirical admission, frozen slate registration, and explicit human approval.",
        "",
        "## Agent Prompt",
        "",
        "```text",
        "Full redo docs/research/sparse-confirmation-certification/sparse-confirmation-certification.md",
        "",
        "1. Re-run: uv run python -m commands.certify_sparse_confirmation",
        "2. Inspect parity_check.json (max_abs_numeric_diff <= 1e-10, binary_agreement_rate == 1.0).",
        "3. Read certification_summary.csv columns: false_null_ever_pass_upper95, correct_confirmation_by_gw38_lower95, terminal_false_exclusion_upper95, statistical_false_exclusion_flag_upper95.",
        "4. Read certification_result.json fields: certified, certified_mode, certification_digest, statistical_protocol_hash.",
        "5. Never use 2026-27 outcomes or alter preregistered seeds (20101, 20102, 20103).",
        "```",
        "",
        "## Method",
        "",
        "**Method type**: Preregistered Monte Carlo calibration and held-out certification with vectorized-vs-scalar numerical parity verification.",
        "",
        "**Inputs**:",
        "- `backtesting/sparse_certification.py` (`build_preregistration_manifest`, `verify_vectorized_vs_scalar_parity`, `tune_sparse_protocol`, `certify_sparse_confirmation`)",
        f"- Tuning seed `{tuning['tuning_seed']}`, held-out primary seed `{primary['seed']}`, predeclared advisory fallback seed `{result['manifest']['fallback_seed']}`",
        "",
        "**Procedure**:",
        "1. Pin evaluator file hashes, simulator config, scenario grid, seeds, acceptance bounds, and retry budget (`max_retries=0` primary, `1` predeclared advisory fallback) in `preregistration_manifest.json`.",
        f"2. Verify vectorized NumPy Kendall-PW + Bartlett HAC + Early-Harm + GW1–4 evaluator parity against scalar `run_kendall_pw_hac_test` & `evaluate_early_harm_fallback` across `{parity['num_prefixes_checked']}` prefixes (`{parity['edge_cases_checked']}` edge cases).",
        f"3. Calibrate `M=1`/`M=2` per-look superiority alphas (`GW15`/`GW30`/`GW38`) and `gw1_4_material_loss_limit` (FPL net points on `sigma_delta={tuning['fpl_delta_sd_per_gw']:.1f}` pts/GW scale) strictly on `seed={tuning['tuning_seed']}`.",
        f"4. Evaluate all {len(primary['scenarios'])} scenarios on held-out `seed={primary['seed']}` (`statistical_early_harm_mode=\"enforced\"`, `N={primary['num_simulations']:,}`).",
        "5. Execute predeclared `statistical_early_harm_mode=\"advisory\"` fallback on untouched `seed=20103` only if statistical Early-Harm fails its `<= 5%` false terminal exclusion gate while false full pass `<= 5%` and GW38 power `>= 1/3` both hold.",
        "",
        "### Metric Definitions & Direction",
        "",
        "| Metric | Symbol | Definition / Formula | Direction | Ideal / Benchmark | Description |",
        "|---|---|---|---|---|---|",
        "| **False Full Pass Upper 95%** | `false_null_ever_pass_upper95` | One-sided 95% Clopper-Pearson upper bound on `k/N` where any true-null finalist clears full pass across registered looks | Lower $\\downarrow$ | `<= 0.05` | Strong family-wise false-promotion error control across `M <= 2` and `(15,30,38)` |",
        "| **Primary GW38 Confirmation Lower 95%** | `correct_confirmation_by_gw38_lower95` | One-sided 95% Clopper-Pearson lower bound on cumulative `+0.40` SD confirmation by GW38 in primary mixed-null `M=2` scenario | Higher $\\uparrow$ | `>= 0.3333` (`1/3`) | Minimum required detection power for genuine `+0.40` SD improvement |",
        "| **Terminal False Exclusion Upper 95%** | `terminal_false_exclusion_upper95` | One-sided 95% Clopper-Pearson upper bound on slates where >=1 non-harmful finalist is terminally excluded | Lower $\\downarrow$ | `<= 0.05` | Protects non-harmful finalists from irreversible mid-season exclusion |",
        "| **Statistical Harm Flag Upper 95%** | `statistical_false_exclusion_flag_upper95` | One-sided 95% Clopper-Pearson upper bound on slates where >=1 non-harmful finalist triggers cumulative or completed-segment statistical Early-Harm (`p_harm <= 0.025`) | Lower $\\downarrow$ | `<= 0.05` (enforced gate) / Diagnostic (advisory) | Measures statistical Early-Harm false-flag rate driving enforced vs advisory separation |",
        "| **Harmful Detection Rate** | `harmful_any_detected_rate` | Share of harmful scenarios flagged by statistical Early-Harm or excluded by GW1–4 floor | Higher $\\uparrow$ | Maximized | Diagnostics on `-0.40`/`-0.60`/`-0.80` SD & severe GW1–4 collapse |",
        "",
        "**Validation boundary**: Synthetic AR(1) + Gaussian/Student-$t(5)$ + scheduled GW15/19/30/34 shock model with shared Champion noise (`rho_champ=0.50`). Real FPL replay transitions may exhibit non-stationary transfer-state coupling beyond AR(1) + shocks.",
        "",
        "## Project interpretation",
        "",
        "### Calibrated Parameters (from `seed=20101`)",
        "",
        f"- **Calibrated `gw1_4_material_loss_limit`**: `{tuning['gw1_4_material_loss_limit']:.1f}` net FPL points (on `{tuning['fpl_delta_sd_per_gw']:.1f}` pts/GW scale)",
        f"- **`M=1` calibrated superiority alphas** (`scale={tuning['m1_scale_factor']:.4f}`): GW15=`{alphas['1']['15']:.8f}`, GW30=`{alphas['1']['30']:.8f}`, GW38=`{alphas['1']['38']:.8f}`",
        f"- **`M=2` calibrated superiority alphas** (`scale={tuning['m2_scale_factor']:.4f}`): GW15=`{alphas['2']['15']:.8f}`, GW30=`{alphas['2']['30']:.8f}`, GW38=`{alphas['2']['38']:.8f}`",
        "",
        "## Findings",
        "",
        "### Parity Check (`parity_check.json`)",
        "",
        f"- Prefixes checked: `{parity['num_prefixes_checked']}` (`{parity['edge_cases_checked']}` edge cases) — `max_abs_numeric_diff={parity['max_abs_numeric_diff']:.3e}`, `binary_agreement_rate={parity['binary_agreement_rate']:.4f}`, `passed={parity['passed']}`.",
        "",
        f"### Primary Enforced Run (`seed={primary['seed']}`)",
        "",
        f"- Worst null-containing false full pass upper 95%: `{p_gates['worst_false_full_pass_upper_95']:.6f}` (`ok={p_gates['false_full_pass_ok']}`)",
        f"- Primary `+0.40` SD GW38 confirmation lower 95%: `{p_gates['primary_gw38_power_lower_95']:.6f}` (`ok={p_gates['primary_gw38_power_ok']}`)",
        f"- Worst non-harmful statistical Early-Harm false exclusion upper 95%: `{p_gates['worst_statistical_false_exclusion_upper_95']:.6f}` (`ok={p_gates['statistical_false_exclusion_ok']}`)",
    ]

    if fallback is not None and f_gates is not None:
        lines.extend(
            [
                "",
                f"### Predeclared Advisory Fallback Run (`seed={fallback['seed']}`)",
                "",
                f"- Triggered because enforced statistical Early-Harm exceeded `0.05` false exclusion (`{p_gates['worst_statistical_false_exclusion_upper_95']:.6f}`) while false full pass and GW38 power held.",
                f"- Worst null-containing false full pass upper 95%: `{f_gates['worst_false_full_pass_upper_95']:.6f}` (`ok={f_gates['false_full_pass_ok']}`)",
                f"- Primary `+0.40` SD GW38 confirmation lower 95%: `{f_gates['primary_gw38_power_lower_95']:.6f}` (`ok={f_gates['primary_gw38_power_ok']}`)",
                f"- Worst non-harmful terminal false exclusion (GW1–4 floor only) upper 95%: `{f_gates['worst_terminal_false_exclusion_upper_95']:.6f}` (`ok={f_gates['terminal_false_exclusion_ok']}`)",
            ]
        )

    lines.extend(
        [
            "",
            f"### Scenario Results (`{active_run_role}` — `certification_summary.csv`)",
            "",
            "| Scenario | Slate | Regime | Guards GW | False Pass (k/N, upper95) | GW38 Power (k/N, lower95) | Term Excl (k/N, upper95) | Stat Harm Flag (k/N, upper95) | Harm Det (k/N) |",
            "|---|---:|---|---:|---|---|---|---|---|",
        ]
    )
    for row in active_rows:
        fp = f"{row['false_null_ever_pass_k']}/{row['false_null_ever_pass_n']} ({row['false_null_ever_pass_upper95']})" if row["has_null_finalist"] else "n/a"
        pw = f"{row['correct_confirmation_by_gw38_k']}/{row['correct_confirmation_by_gw38_n']} ({row['correct_confirmation_by_gw38_lower95']})" if row["has_improving_finalist"] else "n/a"
        te = f"{row['terminal_false_exclusion_k']}/{row['terminal_false_exclusion_n']} ({row['terminal_false_exclusion_upper95']})" if row["has_non_harmful_finalist"] else "n/a"
        sf = f"{row['statistical_false_exclusion_flag_k']}/{row['statistical_false_exclusion_flag_n']} ({row['statistical_false_exclusion_flag_upper95']})" if row["has_non_harmful_finalist"] else "n/a"
        hd = f"{row['harmful_any_detected_k']}/{row['harmful_any_detected_n']} ({row['harmful_any_detected_rate']})" if row["has_harmful_finalist"] else "n/a"
        lines.append(
            f"| `{row['scenario_id']}` | {row['slate_size']} | {row['dependence_regime']} | {row['safeguards_pass_from_gw']} | {fp} | {pw} | {te} | {sf} | {hd} |"
        )

    lines.extend(
        [
            "",
            "## Decision",
            "",
            f"**Verdict**: `certified={result['certified']}`, `certified_mode={result['certified_mode']}`, `certification_seed={result['certification_seed']}`, `live_adoption_blocked={result['live_adoption_blocked']}` (`certification_digest={result['certification_digest']}`).",
            "",
            "**Recommended action**:",
            "- Freeze calibrated `v2.0` protocol (`statistical_protocol_hash=" + str(result["statistical_protocol_hash"]) + "`) with `certification_digest` bound prior to any prospective slate access.",
            "- Retain `GW15`/`GW30`/`GW38` sparse confirmation cadence (weekly expansion remains gated on paired speed and power criteria).",
            "",
            "## Risks and unknowns",
            "",
            "- Realized 6-GW rolling MILP transfer trajectories can exhibit non-AR(1) chip-week or price-lock jumps not captured by Gaussian/Student-$t(5)$ innovations.",
            "- Synthetic certification does not authorize live Champion adoption on its own; empirical admission, frozen slate registration, pilot acceptance, and explicit human approval remain mandatory.",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Tune and certify ADR 0070 sparse confirmation protocol.")
    parser.add_argument("--n-sims", type=int, default=DEFAULT_NUM_SIMULATIONS, help="Simulations per scenario (default: 20000)")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Output research topic directory")
    args = parser.parse_args(argv)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    result = certify_sparse_confirmation(num_simulations=int(args.n_sims))
    v2_declaration = _build_v2_protocol_declaration(result)

    manifest_path = out_dir / "preregistration_manifest.json"
    manifest_path.write_text(json.dumps(result["manifest"], indent=2, sort_keys=True) + "\n", encoding="utf-8")

    parity_path = out_dir / "parity_check.json"
    parity_path.write_text(json.dumps(result["parity_check"], indent=2, sort_keys=True) + "\n", encoding="utf-8")

    summary_rows = _flatten_scenario_rows("primary_enforced", result["primary_run"])
    if result["fallback_run"] is not None:
        summary_rows.extend(_flatten_scenario_rows("fallback_advisory", result["fallback_run"]))

    csv_path = out_dir / "certification_summary.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary_rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(summary_rows)

    result_payload = {
        "manifest_digest": result["manifest_digest"],
        "certification_digest": result["certification_digest"],
        "statistical_protocol_hash": result["statistical_protocol_hash"],
        "certified": result["certified"],
        "certified_mode": result["certified_mode"],
        "certification_seed": result["certification_seed"],
        "retries_used": result["retries_used"],
        "live_adoption_blocked": result["live_adoption_blocked"],
        "tuning": result["tuning"],
        "primary_run": result["primary_run"],
        "fallback_run": result["fallback_run"],
        "certified_protocol_config": result["certified_protocol_config"],
        "evaluation_protocol_v2_declaration": v2_declaration,
    }
    res_path = out_dir / "certification_result.json"
    res_path.write_text(json.dumps(result_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    note_path = out_dir / "sparse-confirmation-certification.md"
    note_path.write_text(_render_research_note(result, summary_rows), encoding="utf-8")

    print(
        f"Sparse confirmation certification complete: certified={result['certified']}, "
        f"mode={result['certified_mode']}, seed={result['certification_seed']}, "
        f"digest={result['certification_digest']}"
    )


if __name__ == "__main__":
    main()
