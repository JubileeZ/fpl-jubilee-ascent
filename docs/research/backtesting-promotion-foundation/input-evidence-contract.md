# Offline input evidence contract

**Updated:** 2026-11-12T12:17:22+00:00
**Data stamp:** Retained source pilot; no new retrieval. Source/producer hashes in [assessment](input_evidence_assessment.json).
**Season:** 2025-26 GW2; GW1 anchor and prior-season dependencies.
**Status:** Delivered and independently reviewed; empirical admission remains closed.
**Purpose:** Report which input claims pass offline contract checks and which required evidence remains missing.
**Scope:** User-approved Q5/Q7 contracts, offline validation, retained-pilot assessment and future raw receipt format. No Candidate search, scheduling, native replay, empirical activation or new confirmation window.

## Sources

- [Source pilot](readiness-source-pilot.md), [retained acquisition audit](readiness_source_pilot_audit.json).
- [Foundation agreements](backtesting-promotion-foundation.md): Q13 justified historical reconstruction; Q17 error target; Q21 numerical approval.
- [ADR 0066](../../adr/0066-backtesting-and-promotion-foundation.md), [operator workflow](../../testing/operator-workflow.md).
- Implementation: `backtesting/input_evidence.py`, `backtesting/input_pilot.py`.

## Decision

Q5: define/test field-specific input acceptance before calibration. Q7: implement contracts and offline pilot assessment now; preserve justified historical reconstruction with explicit limitations. Source-age limits, eligibility/freshness policy, practical harm limits and fresh-confirmation window remain future approval items. No arbitrary numerical default adopted.

No glossary change or new ADR: existing domain policy retained; diagnostic implementation has no new adoption authority.

[Delivery/reviews](../../testing/input-evidence-delivery.md): full suite and regression validation complete; Standards and Spec re-reviews zero remaining findings.

## Method

`SourceEvidence` retains raw bytes/hash, source ID/reference chain, timing basis and optional capture/publication bounds. Unknown time remains null. A recorded Git commit is supporting evidence, not automatically a capture timestamp. Explicit bounded reconstruction can pass contract checks without an exact capture time when supplied bounds, references, coverage and an approved field policy support it.

`assess_field` produces diagnostic `supported`, `unresolved` or `invalid`; these are not Four-Way Scientific Verdicts. Supported means supplied claim checks passed, **not independent certification of references or empirical admission**. Every result retains `promotion_authority=false`. Existing `require_admitted`/`require_input`, forecast generation and promotion evaluator untouched; these diagnostics cannot issue their capability objects.

- Missing source, coverage/lineage reference, capture/publication bounds or approved freshness policy: unresolved.
- Capture interval crossing decision cutoff: unresolved; definitely post-cutoff capture: invalid.
- Reversed/naive timestamps, hash mismatch, malformed contents or outcome source used as input: invalid.
- Policy age uses earliest possible capture to avoid silently assuming the freshest interpretation. A stale interval remains unresolved. A no-age-limit policy requires an explicit approved reference; no such policy adopted here.
- Player checks: unique positive IDs, valid club/position, finite positive integer price, availability status, chance range when present. Null probability remains unknown. Opening-anchor ownership separately required/range-checked.
- Schedule checks: fixture IDs/teams, aware kickoff, horizon coverage; missing week not interpreted as blank. Explicit blank declarations are claims requiring independent coverage evidence before empirical use.

Pilot adapter validates fixed unsealed scope before reading raw source files, checks retained hashes before parsing, inspects allowlisted input fields and confirms opening/GW2 deadlines. Source/call metadata and code hashes retained. Archive outcome values not read; raw mixed payload outcome fields never enter assessment output or model inputs.

## Findings

Field dispositions: [input_evidence_fields.csv](input_evidence_fields.csv), columns `name`, `source_id`, `status`, `reasons`, `limitations`. All required groups remain unresolved with current evidence; no malformed audited input forces an invalid group. This is an explicit blocker inventory, not proof history is unusable.

Population/quality companions: `input_evidence_assessment.json` `metrics` retains opening/current player rows, horizon fixture rows and null next-round chance. Values derive retained bytes; no new performance comparison. Required evidence includes eligible universe, price/club/position, availability, fixtures, opening anchor, historical performance, prior-season training, settled outcomes and shared chip calendar.

### Seed lineage trace

- `backtesting/walkforward.py`: passes resolved seed directory to feature builder; `model.fit(history_before_target(df_perf, ...))` receives current-season pre-target history.
- `features/builder.py`: reads prior-season metadata/performance/fixtures for seeded feature construction; seed existence alone does not certify their source-time/identity mapping.
- `backtesting/forecast_adapter.py`: stages verified synthetic seed tables for features; calls fit on current history. `forecast_inputs.verify_training_bundle` validates retained synthetic closure, not empirical admission.
- Existing behavior not changed. Empirical raw training-source lineage remains unresolved; do not claim prior-season raw rows reach fit because feature seeding exists. Code hashes retained in assessment; no model execution performed for this trace.

## Future receipt contract

`retain_receipt` records caller-supplied bytes at current local UTC, declared Official endpoint and deadline, hash/size, scope and late flag. Source-side capture time remains unknown; receipt UTC is local retention time, not attestation that Official supplied these bytes. No HTTP collector, auth, scheduling or model generation occurs. Raw endpoint/season metadata are declarations; consumer still needs independent causal admission.

Content-addressed raw bytes and exclusive receipt manifests prevent overwrite; loader rechecks manifest identity and raw hash/size. Late receipts retained and flagged rather than backdated. Sealed 2026-27 GW6+ scope and protected storage rejected. Receipt retention itself grants no forecast/promotion authority and does not add future native-season rule support.

## Metric definitions

- Field status: contract disposition under supplied evidence; categorical, no numerical ranking. Ideal supported requirements plus separate verified empirical admission.
- Player/fixture row counts: inspected records in named population; descriptive. Ideal independently complete coverage, not maximum count.
- Null next-round chance: unknown probability cells; descriptive, not automatic DNP or defect. No zero imputation.
- Source/hash checks: identity equality of retained bytes; ideal exact match. Hash equality supplies integrity, not historical timing.

## Risks and unknowns

Evidence references are claims requiring review; a nonempty reference is not proof. Exact empirical eligibility/freshness/coverage rules still need evidence-backed approval. All current pilot groups unresolved; source availability alone insufficient. Current bootstrap/fixture schema checks do not establish all Official semantics or historical announcement completeness. Freshness, calibration and confirmation remain independent blockers.

## Agent Prompt

Reproduce offline: `uv run python -m backtesting.input_pilot`. Requires retained `data/reports/readiness-source-pilot/v1`; no automatic reacquisition. Writes companions beside this note. Validate with `tests/test_input_evidence.py`, `tests/test_input_pilot_assessment.py`, existing admission tests and source-pilot regressions. Never manufacture timing bounds or mark coverage verified from a matching checksum alone. No Candidate runs, sealed access or empirical activation.
