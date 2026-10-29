# Evaluation protocol v1: migration boundary

Phase 0 contract only; no promotion authority. Existing canon and ADRs remain authoritative until approved migration. Numerical thresholds, weights, statistical protection and approval references unapproved. `null` weight means unapproved. Declaration validation proves neither approval, causal admission, statistical validity nor Pass.

## Migration ownership

| Entry point | Legacy behavior | Migration owner |
|---|---|---|
| `commands.backtest`, `backtesting.walkforward`, `commands.compare_models` | Projection evaluation | Phase 3 forecasts; Phase 6 guards |
| `commands.transfer_plan_walkforward`, `backtesting.walkforward_solve` | Strategic ranking | Phases 2–7 replay/policy |
| `.agents/skills/explore-candidate/smoke.py` | Exploratory Candidate screen | Phase 11 promotion boundary |
| `commands.evaluate_model_promotion`, `backtesting.model_evaluation`, `backtesting.promotion` | Gate; explicit `--apply` writes selection | Phase 11 manual adoption |
| `.github/workflows/evaluate_model_promotion.yml` | Recommendation; read-only token; no `--apply` | Phase 11 evidence |
| `commands.measure_champion_bias`, existing monitoring | Diagnostics | Phase 10 live monitoring |
| `models.selection.save_model_selection`, promotion CLI `--apply` | Explicit legacy config writes | Phase 11 adoption; Phase 13 authority |

No new contract wired into legacy promotion. Explicit legacy CLI write remains until Phase 11; not new-protocol adoption.

## Declaration and identity

Version 1 rejects unknown fields. Declaration: development/confirmation/live windows, scored deadlines and weights, issue cutoff, clipped six-GW horizon, native rules, one anchor, Strategic settings, shared chip calendar, quality policy, forecast guards, statistical procedure, approval references. Text identifies specifications; no semantic verification. Freeze requires human approval.

Identity: lowercase SHA256 digests for model source closure, dirty source, parameters/training/seed, input manifests, feature/scoring code, forecast schema, anchor, rules/calendar, solver binary/version/options, evaluation/statistics implementation, protocol. `material_digest` hashes sorted named raw bytes with length prefixes and version domain separator. Callers supply complete closure and dirty bytes. Closure discovery, material retention and verification remain integration work. Model name insufficient.

Result: identity, timezone-aware timestamps, execution status, separate scientific verdict, reasons, evidence completeness, limitations. Pass and demonstrated Fail require complete execution and evidence. Invalid denotes contract/causal/data failure; Inconclusive denotes insufficient evidence. Complete execution alone proves neither scientific validity nor Pass.

## Bundle v1

Each slot: distinct relative JSON file, SHA256 checksum, `version: 1`, exact fields below. References identify retained artifacts; structural checks do not resolve references or establish semantic correctness. `null` allowed for individual pending fields only when bundle `evidence_complete` is false. Completeness flag does not establish Pass; future integration must bind it to the result and perform substantive checks.

| Slot | Required fields |
|---|---|
| `source_admission` | nonempty `source_manifest_refs`, `admission_manifest_refs` lists |
| `forecasts` | nonempty `forecast_ids` list |
| `initial_state` | `state_ref` |
| `deadline_states_actions` | nonempty `deadline_records`: `deadline`, `pre_state_ref`, `post_state_ref`, `actions_ref` |
| `solver_certificate` | nonempty `certificate_refs` list |
| `scores` | finite numeric `gross`, `hits`, `net` |
| `guard_metrics` | `metrics_ref` |
| `uncertainty` | `analysis_ref` |
| `registry_references` | nonempty `registry_refs` list |
| `human_decisions` | nonempty `decision_refs` list |

Reference strings nonempty. Required artifacts must contain forecast IDs, pre/post state, actions, solver details, gross/hit/net ledger, guard metrics, uncertainty and decisions. No semantic validation, score reconciliation, per-deadline coverage, causal verification or approval inference in Phase 0.

## Execution manifests

Calibration and implementation verification: exclusive-create file per unique attempt ID; version, kind, execution status, creation time, result digest. Preserve failed/interrupted attempts separately; no Candidate confirmation classification. Exclusive creation prevents accidental overwrite, not privileged tampering. Interrupted write may leave truncated file; retain as evidence and use new attempt ID. No atomic publication guarantee. Candidate registry and confirmation allocation remain later phases.
