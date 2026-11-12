# Smoke repair and promotion-readiness preflight

**Updated:** 2026-11-12 (Europe/Copenhagen)
**Data stamp:** Immutable processed archives 2023-24/2024-25/2025-26; input hashes in smoke_gate_audit.json; retained synthetic probe metadata and frozen statistical kernel hash.
**Status:** Bounded preflight complete; empirical promotion readiness blocked; numerical approval pending.
**Authority:** User-selected Option B; eight synthetic solver probes permitted. ADR 0066 policy retained.
**Scope:** Stored historical evidence/outcomes, synthetic solver fixtures and controlled statistical examples. No Candidate runs, confirmation reruns, sealed outcomes, archive changes or Champion adoption.

## Decision

Measurement/provenance repairs delivered. Preserve Champion and existing acceptance policy. Empirical activation, fresh confirmation and approved numerical settings require separate evidence-backed scope. No new Candidate lever or retrospective Dead Lever reopening authorized.

## Measurement repair

Tier 2 now receives explicit biases from one Champion-anchored playable pool. Missing/non-finite required metrics and inconsistent populations stop as invalid. Synthetic integration example: whole-population bias approximately zero for both models, candidate playable-pool bias +0.50 points; corrected screen rejects it.
Separate v2 files retain queued attempts and every completed stage, including oracle success followed by integrated failure. Oracle segments unassessed. Content-addressed manifests retain paired evaluation frames, weekly regret scores and pool metrics. Resume verifies complete identity and artifact hashes. Diagnostic completion remains separate from promotion execution, which is not run.
Legacy CSVs and Candidate Ledger locks retained. Source/data/protocol changes invalidate reuse. Smoke remains legacy default scoring; recording data season does not claim native scoring injection.

## Historical evidence and data quality

[Historical pairs](smoke_gate_historical_pairs.csv): 14 paired comparisons, 11 distinct models; 3 confirmation passes, 10 negative confirmation deltas, 1 positive rejection. Pairing preserves file, model, Champion and GW range. Mixed protocols/repeated models prevent interpreting counts as independent generalization trials.
[Data quality](smoke_gate_data_quality.csv): no duplicate inspected table keys, unparseable required numeric cells or missing referenced player/fixture IDs. Negative player points retained as legitimate outcomes. 2024-25 Assistant Manager elements excluded from player ledger audit; no native Assistant Manager benchmark implied.
[Outcome reconciliation](smoke_gate_outcomes.csv): native component totals reconcile exactly across three archives. This verifies outcome arithmetic only. Older seasons lack defensive-contribution inputs and award no native defensive-contribution points; a current-rule reconstruction cannot silently treat unavailable actions as measured zeros.
[Source retention](smoke_gate_source_retention.csv): acquisition manifest records 5 retrieved-but-unadmitted sources and 114 missing rows; 0 recorded raw paths currently present locally. Retrieval history does not establish presently available bytes.
[Readiness matrix](smoke_gate_readiness.csv): original inventory has 1368 unverified bookkeeping rows, not that many independent missing source packages. 2023-24 is seed-only; no full 2023-24 replay required. GW1 ownership/price admission distinct from per-origin inputs and settled outcomes.

## Admission blockers

Empirical admission deliberately closed: `backtesting/data_admission.py` rejects non-synthetic origin readiness and `require_admitted` accepts only admitted synthetic packages. `commands/profile_transfer_replay.py` accepts synthetic diagnostic manifests only. Filling inventories alone cannot activate empirical authority.
Historical universe/eligibility, deadline prices/club membership, issue-time six-GW schedules, availability and independent outcome completeness remain unadmitted. Frozen archive presence and exact scoring reconciliation do not certify pre-deadline information. Builder warm seeding does not imply prior raw rows reach model.fit().
Registry machinery cannot make previously inspected 2024-25 outcomes fresh. Source reacquisition/admission, empirical activation, a causal shared chip calendar and a registered fresh-evidence plan remain prerequisites.

## Bounded solver diagnostic

[Probe summary](smoke_gate_probe_summary.csv), [timings](smoke_gate_probe_timings.csv) and [environment](smoke_gate_probe_environment.json): 8 actual optimizer calls on four artificial native problems; target gaps 0 and 0.02; 8 optimal results, 0 censored. Experiment elapsed 0.6602 seconds. All paired immediate-action digests matched and achieved gaps were zero.
Artificial pool contains 17-19 players with fixed fabricated projections. Profiles measure neither Champion feature/fit/projection cost nor empirical season runtime. Assembly/scoring and cache/resume costs unmeasured; companion cells blank. All solves reached exact optimum, so probes do not establish acceptable approximation or material speed benefit. No final solver tolerance adopted.
Bound: eight calls total, 30-second solver limit, one thread, serial; parent process enforces 1,200-second worker timeout. Per-call progress retained under `data/reports/smoke-gate-preflight/`; exclusive start marker prevents accidental probe repetition.

## Statistical diagnostic

[Calibration companion](smoke_gate_calibration.csv): 200 independent trajectory replicates per configuration, two 38-GW seasons, synthetic stationary Gaussian AR(1) deltas with marginal SD 4 points/GW; means 0 or +0.5; correlations 0, 0.4, 0.8; family budgets 1 or 5. Shared random numbers across configurations permit sensitivity comparison; configurations are not independent experiments. Existing stored-score kernel used with L=5 and 1,000 draws; seed and kernel/config hashes retained.
Significance-component rejection requires positive estimate and (`p_value_superiority <= adjusted_alpha` or lower two-sided CI > 0). Projection guards, registration and empirical admission omitted, so this is not complete-gate false-positive probability or empirical FWER.

- Null, rho=0, M=1: 17/200 rejections (8.5%); Wilson 95% interval [5.4%, 13.2%].
- Null, rho=0.4, M=1: 20/200 rejections (10.0%); Wilson 95% interval [6.6%, 14.9%].
- Null, rho=0.8, M=1: 42/200 rejections (21.0%); Wilson 95% interval [15.9%, 27.2%].

Current settings do not establish a calibrated 5% significance component in these examples. Bonferroni allocation alone cannot repair invalid component inference. No threshold, block length or harm margin tuned from these results; confirmation and sealed evidence excluded. Proposed next numerical work: calibrate a defensible null/inference procedure on development and preregistered synthetic sensitivity cases, assess power, then submit practical harm margins and solver tolerances for human approval before finalist evaluation.

## Metric definitions

- Regret delta: Champion weekly lineup regret minus candidate regret, points/GW. Higher better; ideal positive on applicable integrated comparison. Oracle and integrated deltas separate estimands.
- Playable-pool signed bias: mean(projected points minus chosen target), common mask Champion xP >= 2 or actual minutes >= 30. Magnitude lower better; ideal zero. Existing oracle cap min(abs(Champion bias)+0.02, 0.20), retained without new calibration claim.
- Ledger mismatch count: player-fixture rows where abs(native total minus component sum) > 1e-9. Lower better; ideal zero.
- Rejection rate: synthetic significance-component rejections / trajectory replicates. Under null lower better, nominal benchmark <= 0.05/M; under positive effect higher means greater detection power. Wilson interval describes Monte Carlo uncertainty, not real-football uncertainty.
- Solve runtime: certificate-reported seconds; lower better conditional on quality. Feasibility/optimal status and measured objective gap accompany runtime; synthetic timing has no empirical runtime benchmark.

## Reproduction

```bash
uv run python docs/research/backtesting-promotion-foundation/smoke_gate_preflight.py --calibrate
# Initial authorized probe only; refuses an existing start marker:
uv run python docs/research/backtesting-promotion-foundation/smoke_gate_preflight.py --run-probes
```

Runner refreshes companions and this note; default mode audits retained inputs and summarizes existing probes without solver calls. Archive hashes in `smoke_gate_audit.json`. Source/authority references: [ADR 0066](../../adr/0066-backtesting-and-promotion-foundation.md), [operator workflow](../../testing/operator-workflow.md), [preflight proposal](preflight-plan.md), `backtesting/promotion.py`, `backtesting/smoke_diagnostics.py`, `backtesting/data_admission.py`, `backtesting/evidence_statistics.py`.

## Agent Prompt

Refresh retained-input audit with runner; preserve historical CSVs and locks. Regenerate note caches from `smoke_gate_summary.csv` count columns, `smoke_gate_probe_summary.csv` actual_calls/optimal_calls/censored_calls/elapsed_seconds, and `smoke_gate_calibration.csv` superiority_rejections/simulations/per_attempt_rejection_rate/wilson95_lower/wilson95_upper. Source metadata in adjacent companions; missing empirical evidence remains unassessed. Re-running solver probes requires new authorization and budget; calibration remains synthetic and unapproved. Never access sealed outcomes or reinterpret old confirmation as fresh.
