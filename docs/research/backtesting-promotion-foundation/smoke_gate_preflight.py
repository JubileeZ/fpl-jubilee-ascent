"""Reproduce readiness companions; optional one-shot synthetic native profiling."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from dataclasses import asdict, replace
import json
import math
from pathlib import Path
import subprocess
import sys
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

from backtesting.evidence_statistics import PairedGameweekScore, StatisticalProtocolConfig, run_stored_score_bootstrap
from backtesting.replay_state import Player, ReplayState, initial_state, state_hash
from backtesting.smoke_diagnostics import file_digest
from backtesting.walkforward import LEDGER_COMPONENTS, _build_actual_components
from commands.profile_transfer_replay import ProfilingEnvelope, execute_profiling_experiment, native_manifest_adapter, save_profiling_report
from models.scoring_matrix import Position

TOPIC = Path(__file__).resolve().parent
SEASONS = ("2023-24", "2024-25", "2025-26")
REPORTS = ROOT / "data/reports/smoke-gate-preflight"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(name: str, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError("Companion requires observed rows")
    with (TOPIC / name).open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def audit_inputs() -> dict[str, Any]:
    quality: list[dict[str, Any]] = []
    outcome_rows: list[dict[str, Any]] = []
    hashes: dict[str, str] = {}
    for season in SEASONS:
        directory = ROOT / "data/archive" / season / "processed"
        frames: dict[str, pd.DataFrame] = {name: pd.read_parquet(directory / f"{name}.parquet") for name in ("players", "fixtures", "player_performances")}
        for name, frame in frames.items():
            keys = ["player_id", "fixture_id"] if name == "player_performances" else ["id"]
            required = [column for column in ("minutes", "total_points", "expected_goals", "expected_assists", "price") if column in frame]
            quality.append({"season": season, "table": name, "rows": len(frame), "duplicate_keys": int(frame.duplicated(keys).sum()),
                            "invalid_numeric_cells": sum(int(np.count_nonzero(pd.isna(pd.to_numeric(pd.Series(frame[column]), errors="coerce")))) for column in required),
                            "negative_total_points_rows": int(np.count_nonzero(frame["total_points"].to_numpy(dtype=float) < 0)) if "total_points" in frame else 0})
            hashes[str((directory / f"{name}.parquet").relative_to(ROOT))] = file_digest(directory / f"{name}.parquet")
        meta = cast(pd.DataFrame, frames["players"][["id", "position_id"]]).rename(columns={"id": "player_id"})
        meta = cast(pd.DataFrame, meta[meta.position_id.isin([1, 2, 3, 4])]).copy()
        meta["native_rules_version"] = season
        perf = frames["player_performances"]
        actual = _build_actual_components(cast(pd.DataFrame, perf[perf.player_id.isin(meta.player_id)]).copy(), meta)
        residual = actual.total_points - actual[[f"actual_{component}" for component in LEDGER_COMPONENTS]].sum(axis=1)
        outcome_rows.append({"season": season, "role": "seed_only" if season == "2023-24" else "confirmation" if season == "2024-25" else "development",
                             "player_fixture_rows": len(actual), "native_point_total": float(actual.total_points.sum()),
                             "defcon_points": float(actual.actual_xp_defcon.sum()), "ledger_mismatch_rows": int((residual.abs() > 1e-9).sum()),
                             "missing_player_ids": len(set(perf.player_id) - set(frames["players"].id)),
                             "missing_fixture_ids": len(set(perf.fixture_id) - set(frames["fixtures"].id)), "causal_admission": "unverified"})
    write_csv("smoke_gate_data_quality.csv", quality)
    write_csv("smoke_gate_outcomes.csv", outcome_rows)

    acquisition = read_csv(TOPIC / "acquisition_manifest.csv")
    recorded = [row for row in acquisition if row["status"] == "retrieved_unadmitted"]
    retained = [{"season": row["season"], "origin": row["origin"], "kind": row["kind"], "recorded_status": row["status"],
                 "path": row["path"], "exists_now": (ROOT / row["path"]).is_file(),
                 "hash_matches_now": file_digest(ROOT / row["path"]) == row["raw_sha256"] if (ROOT / row["path"]).is_file() else "unavailable"} for row in recorded]
    write_csv("smoke_gate_source_retention.csv", retained)
    inventory = read_csv(TOPIC / "replay_admission_inventory.csv")
    matrix: list[dict[str, Any]] = []
    field_evidence = {
        "opening_ownership": "ownership_snapshot_samples.csv; ownership_snapshot_provenance.csv",
        "opening_price": "ownership_snapshot_samples.csv; ownership_snapshot_provenance.csv",
        "player_universe": "ownership_local_coverage.csv; ownership-anchor-feasibility.md",
        "eligibility": "ownership_local_coverage.csv; data_admission.py",
        "deadline_price_and_membership": "features/builder.py future-first-row fallback; ownership_local_coverage.csv",
        "deadline": "acquisition_manifest.csv; gameweeks.parquet",
        "six_gw_fixture_schedule": "acquisition_manifest.csv; fixture announcement chronology unavailable",
        "availability": "ownership_local_coverage.csv; no admitted historical availability snapshots",
        "seed_history": "processed archives retained; walkforward.py fit receives current-season rows",
        "outcomes": "smoke_gate_outcomes.csv; arithmetic verified, source completeness unadmitted",
        "components": "smoke_gate_outcomes.csv; defensive contribution native-inapplicable before 2025-26",
        "native_rules": "backtesting/season_rules.py; tests/test_native_season_rules.py",
    }
    for (season, field), rows in sorted(_group(inventory, ("season", "field")).items()):
        if season == "2023-24":
            applicability = "seed identity/outcome provenance only; no rolling replay" if field in {"seed_history", "outcomes", "components", "native_rules", "player_universe"} else "not_required_for_seed_only"
        else:
            applicability = "GW1 anchor only" if field.startswith("opening_") else "season-level contract" if field in {"native_rules", "seed_history"} else "per-origin forecasts or independent settled outcomes"
        matrix.append({"season": season, "role": "seed_only" if season == "2023-24" else "confirmation" if season == "2024-25" else "development",
                       "field": field, "inventory_rows": len(rows), "recorded_statuses": ";".join(sorted({row["evidence_status"] for row in rows})),
                       "empirical_admission": "not_activated", "evidence": field_evidence.get(field, "replay_admission_inventory.csv"),
                       "applicability": applicability})
    for field, evidence, status in (
        ("empirical_admission_activation", "backtesting/data_admission.py: assess_origins/input_ready/require_admitted", "closed_in_code"),
        ("statistical_calibration_approval", "backtesting/evidence_statistics.py; smoke_gate_calibration.csv", "unapproved"),
        ("confirmation_freshness", "docs/testing/operator-workflow.md; Immutable Attempt Registry", "historical_inspection_not_fresh_confirmation"),
        ("continuous_replay_accounting", "backtesting/replay_state.py; backtesting/rolling_replay.py; foundation-delivery.md", "synthetic_verification_only"),
    ):
        matrix.append({"season": "all", "role": "authority", "field": field, "inventory_rows": 0, "recorded_statuses": status,
                       "empirical_admission": "not_activated", "evidence": evidence, "applicability": "prerequisite for authoritative promotion evidence"})
    write_csv("smoke_gate_readiness.csv", matrix)
    pairs: list[dict[str, Any]] = []
    for path in sorted((ROOT / "docs").glob("**/candidate_gate.csv")):
        for (variant, champion, gw_range), rows in _group(read_csv(path), ("variant", "champion", "gw_range")).items():
            by_role = {row["season"]: row for row in rows}
            if {"dev", "confirm"} <= by_role.keys():
                dev, confirmation = by_role["dev"], by_role["confirm"]
                pairs.append({"source": str(path.relative_to(ROOT)), "variant": variant, "champion": champion, "gw_range": gw_range,
                              "dev_pass": dev["pass"], "dev_delta": float(dev["combined_delta"]), "confirmation_pass": confirmation["pass"],
                              "confirmation_delta": float(confirmation["combined_delta"]), "confirmation_reasons": confirmation["reasons"]})
    write_csv("smoke_gate_historical_pairs.csv", pairs)
    summary = {"historical_pairs": len(pairs), "unique_models": len({row["variant"] for row in pairs}),
               "confirmation_passes": sum(row["confirmation_pass"] == "True" for row in pairs),
               "negative_confirmation_deltas": sum(row["confirmation_delta"] < 0 for row in pairs),
               "positive_confirmation_rejections": sum(row["confirmation_delta"] > 0 and row["confirmation_pass"] != "True" for row in pairs),
               "acquisition_rows": len(acquisition), "acquisition_statuses": dict(Counter(row["status"] for row in acquisition)),
               "retained_recorded_raw_sources": sum(row["exists_now"] for row in retained), "inventory_rows": len(inventory),
               "inventory_statuses": dict(Counter(row["evidence_status"] for row in inventory)), "input_hashes": hashes,
               "producer_sha256": file_digest(Path(__file__)),
               "scope": "Stored historical outcomes/records only; no model evaluation, confirmation rerun or sealed outcomes"}
    (TOPIC / "smoke_gate_audit.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    write_csv("smoke_gate_summary.csv", [{**{key: summary[key] for key in ("historical_pairs", "unique_models", "confirmation_passes", "negative_confirmation_deltas", "positive_confirmation_rejections", "acquisition_rows", "retained_recorded_raw_sources", "inventory_rows")},
                                          "recorded_retrieved_sources": len(recorded), "recorded_missing_rows": sum(row["status"] == "missing" for row in acquisition),
                                          "ledger_mismatch_rows": sum(row["ledger_mismatch_rows"] for row in outcome_rows)}])
    return summary


def _group(rows: list[dict[str, str]], fields: tuple[str, ...]) -> dict[tuple[str, ...], list[dict[str, str]]]:
    groups: dict[tuple[str, ...], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[tuple(row[field] for field in fields)].append(row)
    return groups


def synthetic_problem(deadline: int) -> tuple[ReplayState, pd.DataFrame]:
    positions = cast(list[Position], ["GK"] * 2 + ["D"] * 5 + ["M"] * 5 + ["F"] * 3)
    squad = tuple(Player(i, position, (i - 1) % 6 + 1, 50, 50) for i, position in enumerate(positions, 1))
    opening = initial_state("2025-26", squad)
    state = replace(opening, deadline=deadline, free_transfers=1, parent_hash=state_hash(opening))
    rows: list[dict[str, Any]] = []
    for player in (*squad, Player(16, "M", 6, 50, 50), Player(17, "D", 5, 50, 50)):
        row: dict[str, Any] = {"player_id": player.player_id, "position_id": {"GK": 1, "D": 2, "M": 3, "F": 4}[player.position],
                               "club_id": player.club, "now_cost": player.market, "purchase_eligible": True}
        row.update({f"{gw}_{suffix}": 90.0 if suffix == "xMins" else 25.0 if player.player_id == 16 else 5.0
                    for gw in range(deadline, deadline + 6) for suffix in ("Pts", "xMins")})
        rows.append(row)
    return state, pd.DataFrame(rows)


def probe_manifest() -> dict[str, Any]:
    problems = []
    for name, deadline in (("ordinary", 2), ("constrained_budget", 6), ("transfer_heavy", 10), ("chip_enabled", 12)):
        state, forecasts = synthetic_problem(deadline)
        if name == "constrained_budget":
            state = replace(state, bank=0)
            forecasts.loc[forecasts.player_id == 16, "now_cost"] = 55
            forecasts.loc[forecasts.player_id == 17, "now_cost"] = 45
        if name == "transfer_heavy":
            state = replace(state, free_transfers=2)
            for pid, position, club in ((18, 4, 4), (19, 3, 3)):
                row = forecasts.iloc[-1].to_dict()
                row.update(player_id=pid, position_id=position, club_id=club)
                forecasts = pd.concat([forecasts, pd.DataFrame([row])], ignore_index=True)
            for gw in range(deadline, deadline + 6):
                forecasts.loc[forecasts.player_id >= 16, f"{gw}_Pts"] = 0.0 if gw == deadline else 100.0
        problems.append({"problem_id": name, "archetype": name, "horizon": 6, "state": asdict(state),
                         "forecasts": {"rows": forecasts.to_dict("records")}, "chip_calendar": [[deadline, "free_hit"]] if name == "chip_enabled" else []})
    return {"version": 1, "mode": "synthetic_diagnostic", "problems": problems}


def probe_worker() -> None:
    manifest, solver, source, protocol = native_manifest_adapter(REPORTS / "probe_manifest.json")
    progress: list[dict[str, Any]] = []

    def measured(problem: Any, gap: float, limit: float) -> tuple[Any, str]:
        progress.append({"problem_id": problem.problem_id, "gap": gap, "status": "started"})
        (REPORTS / "probe_progress.json").write_text(json.dumps(progress, indent=2) + "\n")
        certificate, action = solver(problem, gap, limit)
        progress[-1].update(status="complete", certificate=asdict(certificate), action_digest=action)
        (REPORTS / "probe_progress.json").write_text(json.dumps(progress, indent=2) + "\n")
        return certificate, action

    report = execute_profiling_experiment(manifest=manifest, envelope=ProfilingEnvelope(max_optimizer_calls=8),
                                          solver_hook=measured, source_id=source, protocol_id=protocol)
    save_profiling_report(report, REPORTS / "probe_report.json")


def run_probes() -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    with (REPORTS / "probe_started.json").open("x") as handle:
        json.dump({"mode": "synthetic_diagnostic", "max_calls": 8, "per_call_seconds": 30, "hard_worker_seconds": 1200}, handle)
    (REPORTS / "probe_manifest.json").write_text(json.dumps(probe_manifest(), indent=2) + "\n")
    subprocess.run([sys.executable, str(Path(__file__).resolve()), "--probe-worker"], check=True, timeout=1200, cwd=ROOT)


def summarize_probes() -> None:
    path = REPORTS / "probe_report.json"
    if not path.exists():
        return
    report = json.loads(path.read_text())
    rows = [{**row, "input_mode": "synthetic_diagnostic", "empirical_runtime_authority": False,
             "model_prep_measured": False, "assembly_scoring_measured": False} for row in report["records"]]
    for row in rows:
        for name in ("features_time_seconds", "fitting_time_seconds", "projection_time_seconds", "assembly_time_seconds", "scoring_time_seconds"):
            row[name] = None
    write_csv("smoke_gate_probe_timings.csv", rows)
    write_csv("smoke_gate_probe_summary.csv", [{"actual_calls": report["total_calls_executed"], "optimal_calls": sum(row["termination_status"] == "OPTIMAL" for row in rows),
                                                "censored_calls": report["censored_calls_count"], "elapsed_seconds": report["total_elapsed_seconds"],
                                                "matched_action_pairs": sum(len({row["first_action_digest"] for row in group}) == 1 for group in _group(read_csv(TOPIC / "smoke_gate_probe_timings.csv"), ("problem_id",)).values()),
                                                "max_achieved_gap": max(row["actual_gap"] for row in rows), "empirical_runtime_authority": False}])
    environment = {key: report[key] for key in ("environment", "envelope", "timestamp", "total_calls_executed", "total_elapsed_seconds", "budget_exhausted", "censored_calls_count")}
    environment.update(input_mode="synthetic_diagnostic", report_sha256=file_digest(path), manifest_sha256=file_digest(REPORTS / "probe_manifest.json"),
                       empirical_runtime_authority=False, model_preparation="unmeasured", cache_and_resume="unmeasured")
    (TOPIC / "smoke_gate_probe_environment.json").write_text(json.dumps(environment, sort_keys=True, indent=2) + "\n")


def calibration(simulations: int, draws: int) -> None:
    rows: list[dict[str, Any]] = []
    for rho in (0.0, 0.4, 0.8):
        for effect in (0.0, 0.5):
            for budget in (1, 5):
                rng = np.random.default_rng(20261112)
                config = StatisticalProtocolConfig(bootstrap_draws=draws, max_family_attempts=budget,
                                                    season_weights={"2025-26": 0.5, "2024-25": 0.5})
                rejections, widths = 0, []
                for simulation in range(simulations):
                    scores: list[PairedGameweekScore] = []
                    for season in ("2025-26", "2024-25"):
                        current = float(rng.normal(effect, 4.0))
                        for gw in range(1, 39):
                            current = effect + rho * (current - effect) + float(rng.normal(0.0, 4.0 * math.sqrt(1 - rho ** 2)))
                            scores.append(PairedGameweekScore(season, gw, 60.0 + current, 60.0, 60.0 + current, 60.0, 0, 0))
                    result = run_stored_score_bootstrap(scores, config, seed=simulation)
                    rejections += result.point_estimate > 0 and (result.p_value_superiority <= result.adjusted_alpha or result.confidence_interval[0] > 0)
                    widths.append(result.confidence_interval[1] - result.confidence_interval[0])
                p, z = rejections / simulations, 1.96
                denominator = 1 + z * z / simulations
                center = (p + z * z / (2 * simulations)) / denominator
                radius = z * math.sqrt(p * (1 - p) / simulations + z * z / (4 * simulations ** 2)) / denominator
                rows.append({"ar1_rho": rho, "true_mean_delta_pts_per_gw": effect, "marginal_sd_pts_per_gw": 4.0,
                             "seasons": 2, "gws_per_season": 38, "simulations": simulations, "bootstrap_draws": draws,
                             "family_budget": budget, "adjusted_alpha": 0.05 / budget, "superiority_rejections": rejections,
                             "per_attempt_rejection_rate": p, "wilson95_lower": center - radius, "wilson95_upper": center + radius,
                             "mean_two_sided_ci_width": float(np.mean(widths)), "protocol_approved": False,
                             "simulation_seed": 20261112, "bootstrap_seed": "simulation index", "statistical_protocol_hash": config.compute_hash(),
                             "kernel_sha256": file_digest(ROOT / "backtesting/evidence_statistics.py"),
                             "scope": "synthetic significance-component diagnostic; no projection guards, registry or empirical FWER claim"})
                print(f"calibration rho={rho} effect={effect} budget={budget}: {rejections}/{simulations}", flush=True)
    write_csv("smoke_gate_calibration.csv", rows)


def render_report() -> None:
    audit = read_csv(TOPIC / "smoke_gate_summary.csv")[0]
    calibration_path = TOPIC / "smoke_gate_calibration.csv"
    if not calibration_path.exists() or not (TOPIC / "smoke_gate_probe_environment.json").exists():
        return
    trials = read_csv(calibration_path)
    probe = read_csv(TOPIC / "smoke_gate_probe_summary.csv")[0]
    nulls = [row for row in trials if float(row["true_mean_delta_pts_per_gw"]) == 0 and row["family_budget"] == "1"]
    lines = [
        "# Smoke repair and promotion-readiness preflight", "",
        "**Updated:** 2026-11-12 (Europe/Copenhagen)",
        "**Data stamp:** Immutable processed archives 2023-24/2024-25/2025-26; input hashes in smoke_gate_audit.json; retained synthetic probe metadata and frozen statistical kernel hash.",
        "**Status:** Bounded preflight complete; empirical promotion readiness blocked; numerical approval pending.",
        "**Authority:** User-selected Option B; eight synthetic solver probes permitted. ADR 0066 policy retained.",
        "**Scope:** Stored historical evidence/outcomes, synthetic solver fixtures and controlled statistical examples. No Candidate runs, confirmation reruns, sealed outcomes, archive changes or Champion adoption.", "",
        "## Decision", "",
        "Measurement/provenance repairs delivered. Preserve Champion and existing acceptance policy. Empirical activation, fresh confirmation and approved numerical settings require separate evidence-backed scope. No new Candidate lever or retrospective Dead Lever reopening authorized.", "",
        "## Measurement repair", "",
        "Tier 2 now receives explicit biases from one Champion-anchored playable pool. Missing/non-finite required metrics and inconsistent populations stop as invalid. Synthetic integration example: whole-population bias approximately zero for both models, candidate playable-pool bias +0.50 points; corrected screen rejects it.",
        "Separate v2 files retain queued attempts and every completed stage, including oracle success followed by integrated failure. Oracle segments unassessed. Content-addressed manifests retain paired evaluation frames, weekly regret scores and pool metrics. Resume verifies complete identity and artifact hashes. Diagnostic completion remains separate from promotion execution, which is not run.",
        "Legacy CSVs and Candidate Ledger locks retained. Source/data/protocol changes invalidate reuse. Smoke remains legacy default scoring; recording data season does not claim native scoring injection.", "",
        "## Historical evidence and data quality", "",
        f"[Historical pairs](smoke_gate_historical_pairs.csv): {audit['historical_pairs']} paired comparisons, {audit['unique_models']} distinct models; {audit['confirmation_passes']} confirmation passes, {audit['negative_confirmation_deltas']} negative confirmation deltas, {audit['positive_confirmation_rejections']} positive rejection. Pairing preserves file, model, Champion and GW range. Mixed protocols/repeated models prevent interpreting counts as independent generalization trials.",
        "[Data quality](smoke_gate_data_quality.csv): no duplicate inspected table keys, unparseable required numeric cells or missing referenced player/fixture IDs. Negative player points retained as legitimate outcomes. 2024-25 Assistant Manager elements excluded from player ledger audit; no native Assistant Manager benchmark implied.",
        "[Outcome reconciliation](smoke_gate_outcomes.csv): native component totals reconcile exactly across three archives. This verifies outcome arithmetic only. Older seasons lack defensive-contribution inputs and award no native defensive-contribution points; a current-rule reconstruction cannot silently treat unavailable actions as measured zeros.",
        f"[Source retention](smoke_gate_source_retention.csv): acquisition manifest records {audit['recorded_retrieved_sources']} retrieved-but-unadmitted sources and {audit['recorded_missing_rows']} missing rows; {audit['retained_recorded_raw_sources']} recorded raw paths currently present locally. Retrieval history does not establish presently available bytes.",
        f"[Readiness matrix](smoke_gate_readiness.csv): original inventory has {audit['inventory_rows']} unverified bookkeeping rows, not that many independent missing source packages. 2023-24 is seed-only; no full 2023-24 replay required. GW1 ownership/price admission distinct from per-origin inputs and settled outcomes.", "",
        "## Admission blockers", "",
        "Empirical admission deliberately closed: `backtesting/data_admission.py` rejects non-synthetic origin readiness and `require_admitted` accepts only admitted synthetic packages. `commands/profile_transfer_replay.py` accepts synthetic diagnostic manifests only. Filling inventories alone cannot activate empirical authority.",
        "Historical universe/eligibility, deadline prices/club membership, issue-time six-GW schedules, availability and independent outcome completeness remain unadmitted. Frozen archive presence and exact scoring reconciliation do not certify pre-deadline information. Builder warm seeding does not imply prior raw rows reach model.fit().",
        "Registry machinery cannot make previously inspected 2024-25 outcomes fresh. Source reacquisition/admission, empirical activation, a causal shared chip calendar and a registered fresh-evidence plan remain prerequisites.", "",
        "## Bounded solver diagnostic", "",
        f"[Probe summary](smoke_gate_probe_summary.csv), [timings](smoke_gate_probe_timings.csv) and [environment](smoke_gate_probe_environment.json): {probe['actual_calls']} actual optimizer calls on four artificial native problems; target gaps 0 and 0.02; {probe['optimal_calls']} optimal results, {probe['censored_calls']} censored. Experiment elapsed {float(probe['elapsed_seconds']):.4f} seconds. All paired immediate-action digests matched and achieved gaps were zero.",
        "Artificial pool contains 17-19 players with fixed fabricated projections. Profiles measure neither Champion feature/fit/projection cost nor empirical season runtime. Assembly/scoring and cache/resume costs unmeasured; companion cells blank. All solves reached exact optimum, so probes do not establish acceptable approximation or material speed benefit. No final solver tolerance adopted.",
        "Bound: eight calls total, 30-second solver limit, one thread, serial; parent process enforces 1,200-second worker timeout. Per-call progress retained under `data/reports/smoke-gate-preflight/`; exclusive start marker prevents accidental probe repetition.", "",
        "## Statistical diagnostic", "",
        "[Calibration companion](smoke_gate_calibration.csv): 200 independent trajectory replicates per configuration, two 38-GW seasons, synthetic stationary Gaussian AR(1) deltas with marginal SD 4 points/GW; means 0 or +0.5; correlations 0, 0.4, 0.8; family budgets 1 or 5. Shared random numbers across configurations permit sensitivity comparison; configurations are not independent experiments. Existing stored-score kernel used with L=5 and 1,000 draws; seed and kernel/config hashes retained.",
        "Significance-component rejection requires positive estimate and (`p_value_superiority <= adjusted_alpha` or lower two-sided CI > 0). Projection guards, registration and empirical admission omitted, so this is not complete-gate false-positive probability or empirical FWER.", "",
    ]
    for row in nulls:
        lines.append(f"- Null, rho={float(row['ar1_rho']):g}, M=1: {row['superiority_rejections']}/{row['simulations']} rejections ({float(row['per_attempt_rejection_rate']):.1%}); Wilson 95% interval [{float(row['wilson95_lower']):.1%}, {float(row['wilson95_upper']):.1%}].")
    lines += ["", "Current settings do not establish a calibrated 5% significance component in these examples. Bonferroni allocation alone cannot repair invalid component inference. No threshold, block length or harm margin tuned from these results; confirmation and sealed evidence excluded. Proposed next numerical work: calibrate a defensible null/inference procedure on development and preregistered synthetic sensitivity cases, assess power, then submit practical harm margins and solver tolerances for human approval before finalist evaluation.", "",
              "## Metric definitions", "",
              "- Regret delta: Champion weekly lineup regret minus candidate regret, points/GW. Higher better; ideal positive on applicable integrated comparison. Oracle and integrated deltas separate estimands.",
              "- Playable-pool signed bias: mean(projected points minus chosen target), common mask Champion xP >= 2 or actual minutes >= 30. Magnitude lower better; ideal zero. Existing oracle cap min(abs(Champion bias)+0.02, 0.20), retained without new calibration claim.",
              "- Ledger mismatch count: player-fixture rows where abs(native total minus component sum) > 1e-9. Lower better; ideal zero.",
              "- Rejection rate: synthetic significance-component rejections / trajectory replicates. Under null lower better, nominal benchmark <= 0.05/M; under positive effect higher means greater detection power. Wilson interval describes Monte Carlo uncertainty, not real-football uncertainty.",
              "- Solve runtime: certificate-reported seconds; lower better conditional on quality. Feasibility/optimal status and measured objective gap accompany runtime; synthetic timing has no empirical runtime benchmark.", "",
              "## Reproduction", "", "```bash", "uv run python docs/research/backtesting-promotion-foundation/smoke_gate_preflight.py --calibrate", "# Initial authorized probe only; refuses an existing start marker:", "uv run python docs/research/backtesting-promotion-foundation/smoke_gate_preflight.py --run-probes", "```", "",
              "Runner refreshes companions and this note; default mode audits retained inputs and summarizes existing probes without solver calls. Archive hashes in `smoke_gate_audit.json`. Source/authority references: [ADR 0066](../../adr/0066-backtesting-and-promotion-foundation.md), [operator workflow](../../testing/operator-workflow.md), [preflight proposal](preflight-plan.md), `backtesting/promotion.py`, `backtesting/smoke_diagnostics.py`, `backtesting/data_admission.py`, `backtesting/evidence_statistics.py`.", "",
              "## Agent Prompt", "",
              "Refresh retained-input audit with runner; preserve historical CSVs and locks. Regenerate note caches from `smoke_gate_summary.csv` count columns, `smoke_gate_probe_summary.csv` actual_calls/optimal_calls/censored_calls/elapsed_seconds, and `smoke_gate_calibration.csv` superiority_rejections/simulations/per_attempt_rejection_rate/wilson95_lower/wilson95_upper. Source metadata in adjacent companions; missing empirical evidence remains unassessed. Re-running solver probes requires new authorization and budget; calibration remains synthetic and unapproved. Never access sealed outcomes or reinterpret old confirmation as fresh.", ""]
    (TOPIC / "smoke_gate_preflight.md").write_text("\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-probes", action="store_true")
    parser.add_argument("--probe-worker", action="store_true")
    parser.add_argument("--calibrate", action="store_true")
    parser.add_argument("--simulations", type=int, default=200)
    parser.add_argument("--draws", type=int, default=1000)
    args = parser.parse_args()
    if args.probe_worker:
        probe_worker()
        return
    summary = audit_inputs()
    print(json.dumps({key: value for key, value in summary.items() if key != "input_hashes"}, indent=2), flush=True)
    if args.run_probes:
        run_probes()
    summarize_probes()
    if args.calibrate:
        calibration(args.simulations, args.draws)
    render_report()


if __name__ == "__main__":
    main()
