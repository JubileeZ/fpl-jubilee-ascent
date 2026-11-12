# Historical input source pilot

**Updated:** 2026-11-12 (Europe/Copenhagen)  
**Data stamp:** Pinned public files recovered 2026-11-12; attempts/hashes in [audit](readiness_source_pilot_audit.json).  
**Season:** 2025-26; 2024-25 seed dependencies only.  
**Status:** Bounded pilot complete; partial source feasibility; no empirical admission.  
**Purpose:** Establish whether one historical decision date can be reconstructed using information available before its deadline.  
**Scope:** Source feasibility; no Candidate search, performance comparison or empirical activation.

## Decision

Grill-with-docs follow-up Q1–Q4 agreed:

- Finish evaluation readiness before new Candidate search.
- Establish bounded historical source feasibility before broader integration/calibration.
- If historical evidence cannot support valid confirmation, prepare prospective confirmation outside protected sealed data. Protocol/window agreement required before activation.
- First phase: one fixed Development origin, 2025-26 GW2, plus necessary GW1 ownership-anchor and prior-season seed dependencies.

Plain-language goal: verify what a model could have known before one old gameweek. A successful download alone does not establish trustworthy historical inputs.

## Sources

- [Readiness preflight](smoke_gate_preflight.md): retained-source gaps, admission blockers and statistical limitations.
- [Acquisition manifest](acquisition_manifest.csv): GW2 bootstrap/fixture references, hashes and previously recorded deadline.
- [Acquisition implementation](acquire_admission_sources.py): pinned public source locations and existing quarantine behavior.
- [Foundation agreements](backtesting-promotion-foundation.md): Q13 historical limitations, Q15 no fixed minimum gain, Q17 error-control target, Q21 numerical approval, Q26 fresh confirmation.
- [ADR 0066](../../adr/0066-backtesting-and-promotion-foundation.md): existing replay objective and authority.

Source boundary: recovered bytes match prior recorded hashes; source metadata and collector code inspected. Exact capture timing, freshness/eligibility policy and complete replay admission remain unverified.

## Method

### Fixed target and operating limits

- Origin: 2025-26 GW2; recorded deadline 2025-08-22 17:30 UTC. Reverify against hashed bytes. No silent origin substitution if evidence fails.
- Public GitHub metadata/pinned contents from existing `Randdalf/fplcache` and `vaastav/Fantasy-Premier-League` sources only.
- Proposed phase limits accepted through Q4: 30 minutes total execution elapsed; 30 public requests; 10 MiB aggregate downloaded; serial requests; 30 seconds/request; 16 MiB decoded/file. Count failures and redirects; stop at first exhausted cap.
- Limits bound investigation cost; neither measured runtime nor final replay settings.
- Inspect local dependency metadata first. Avoid wholesale acquisition-script execution: preserve existing manifests and append versioned attempts.

### Required checks

1. Retain source URL/revision, raw hashes, retrieval time, timestamp meaning/uncertainty and interrupted attempts. Keep mixed raw payloads quarantined; parse allowlisted input/provenance fields only.
2. Establish pre-deadline lineage for player universe/eligibility, price, club/position and availability. Justify causal reconstructions and disclose limitations; complete endpoint snapshots not universally required under Q13. Unsupported required inputs remain unadmitted.
3. Establish fixtures known at the common issue deadline for GW2–7; distinguish blanks, unknown schedule and missing records.
4. Check GW1 anchor and seed lineage dependencies; identify independent settled-outcome source coverage without comparing performance. Prior-season feature availability does not prove raw seed rows reach model.fit().
5. Classify every required field and unresolved dependency. Git commit time alone does not establish exact capture or independent publication time.

### Boundaries

Zero Candidate/model runs, solver calls, confirmation reruns or sealed 2026-27 GW6+ access. Historical archives, Champion selection, ledger locks, production configuration and empirical admission remain unchanged. No statistical experiments or numerical approval in this phase. Source retrieval requires enforced limits and versioned retention before execution.

## Findings

**Verdict: partial.** Missing retained bytes recoverable; complete historical admission not established. No evidence from this check attributes historical Candidate reversals to a particular bug, rule change or model defect.

[Checks](readiness_source_pilot_checks.csv) cache allowlisted input-field audits. [Audit](readiness_source_pilot_audit.json) records source URLs, hashes, timings, resource use, failed attempts and producer hash. Raw mixed payloads, collector source and full commit metadata quarantined under `data/reports/readiness-source-pilot/v1/`; original acquisition manifest untouched.

- Three data files recovered with exact prior SHA256 matches: GW1 bootstrap, GW2 bootstrap and GW2 fixture snapshot. Three commit-metadata files also recovered. Initial six requests failed sandbox DNS; same-phase retry retained failures and original budgets.
- Final acquisition totals: 17 requests, 945,980 downloaded bytes, 110.46 seconds through last collector retrieval; within agreed limits. Remaining time/requests not used to shop for another origin. Later offline analysis/verification separate from acquisition timing.
- GW1 bootstrap: 685 player records. GW2 bootstrap: 698. Zero duplicate IDs, missing required audited cells, or invalid price/ownership/position rows in either. This is field consistency, not independent proof of complete legal universe or eligibility.
- GW2 payload confirms deadline `2025-08-22T17:30:00Z`. Recorded bootstrap commit `2025-08-22T12:51:15Z` precedes deadline by 4h38m45s. This is commit-to-deadline separation, not measured capture age.
- Fixture snapshot: 60 rows for GW2–7, ten per GW; zero duplicate IDs or missing audited schedule fields. Recorded GitHub-verified commit timestamp precedes GW2 deadline. Completeness relative to official announcement history still unverified.
- Collector at pinned GW2 revision fetches Official bootstrap, then names compressed file using timezone-naive `datetime.today()`. Supports fetch-then-write lineage; filename alone does not certify capture UTC. Bootstrap commits unsigned; signed fixture commit does not attest Official capture time.
- Availability status present; next-round chance null for 541 GW2 players. Null chance retained as unknown, never converted to zero/DNP. Source snapshot does not establish updates made between collection and deadline.

### Required-field disposition

- **Universe/eligibility — partial:** snapshot has player IDs, clubs and positions; removal/eligibility semantics and independent completeness not admitted.
- **Price/club/position — observed, unadmitted:** coherent fields in pinned opening/origin bytes; source-time/freshness policy unresolved.
- **Availability — partial:** status/news/chance input fields observed; nulls legitimate unknowns. Need explicit null/staleness policy and timing evidence.
- **GW2–7 schedule — observed, unadmitted:** populated unique fixture records; official announcement lineage/completeness unresolved.
- **GW1 anchor dependencies — partial:** opening ownership/price/position fields recovered. No anchor optimization; eligibility/freshness and financing contract still require admission.
- **2024-25 seed — unverified:** local processed directory exists. Per-field causal training lineage and raw seed delivery to model.fit() not established; no seed outcome rows inspected.
- **Independent settled outcomes — unassessed:** no new independent completeness/lineage certificate established. Existing ledger reconciliation only establishes arithmetic, not independent source completeness.
- **Shared chip calendar — unassessed:** no causal calendar construction/admission in source pilot.

### Metric definitions

- Player/fixture row count: number of inspected input records; direction descriptive; ideal complete independently verified population, not maximum count.
- Duplicate IDs: row count minus distinct ID count within named population; lower better; ideal zero.
- Missing required cells: null audited ID/team/position/price/ownership/status cells, or null/empty fixture ID/event/teams/kickoff; lower better; ideal zero. Nullable chance/news fields excluded.
- Invalid price/ownership/position rows: any nonfinite/nonpositive price, ownership outside 0–100, or position outside 1–4; lower better; ideal zero. Does not cover all domain validity rules.
- Null next-round chance: count of unknown probability cells; descriptive, not automatic data error or injury/DNP classification.
- Request/byte/elapsed use: all attempted public requests, response-body bytes read, and original acquisition-phase wall time through last fetch; lower cost conditional on evidence quality; upper bounds 30, 10 MiB, 1800 seconds. Failed attempts count; redirects not followed.

## Proposed follow-up

Validation: full suite 1051 passed (three existing constant-input warnings); Ruff clean; pilot runner/tests Pyright zero errors; portable delivery gate 19 passed. Five offline pilot regressions cover source boundaries, byte caps/partial retention, original-budget resume, malformed input quality and outcome exclusion. No verification test makes external HTTP requests. Archive, Champion, Candidate Ledger and original acquisition manifest unchanged.

Keep historical pilot diagnostic. Source gaps identify further evidence/admission work; no failed model verdict or Dead Lever lock follows.

Prepare prospective protocol outside sealed 2026-27 GW6+ data:

1. Identify eligible future window and agree protocol amendment before any evaluation outcomes inspected. No dates silently selected here; inspected 2024-25 cannot supply fresh confirmation.
2. Specify pre-deadline Official bootstrap/fixture captures, receipt UTC, immutable hashes, full eligible universe, price/club/position, availability and issue-known six-GW schedule. Keep raw receipts separate from model inputs.
3. Predefine missing/late capture, unknown availability, schedule-change, eligibility and independent outcome-completeness rules. Required missing evidence yields incomplete/invalid evaluation rather than zero-valued outcomes.
4. Resolve source admission and empirical activation with tests; retain current closed gate until validated. Complete calibration, power/duration and practical harm proposal before freezing finalist, attempt budget and review schedule.
5. Freeze comparison protocol/finalist before confirmation begins; retain Champion and independent continuous shadow paths. No deployment or scheduled capture started by this proposal.

## Completion and next decisions

- **Feasible:** credible causal source path for required inputs and anchor/seed dependencies, identifiable independent outcome coverage. Propose broader coverage; one origin does not establish an admitted season or fresh confirmation.
- **Partial:** recover useful evidence but leave required conditions unresolved; name missing artifacts and next bounded investigation.
- **Blocked:** cannot establish required evidence within limits; retain attempts, name blockers and prepare agreed prospective fallback. No relaxed provenance or origin shopping.

Return a field-by-field evidence report and versioned acquisition attempts, including cap exhaustion. Historical source feasibility cannot make inspected 2024-25 results fresh.

After feasibility: agent prepares justified inference/calibration, power/duration, practical-loss and solver-quality proposals. Preserve intended search-family false-positive target at most 5%, no fixed minimum positive gain, and bounded seasonal losses rather than requiring every season to win. Human approves practical harm limits and protocol before finalist evaluation. Current numerical defaults remain unapproved.

## Risks and unknowns

Missing bytes may be recoverable while timing/eligibility remain unprovable. Two source repositories may not cover required fields. A successful pilot may not generalize across seasons. Prospective confirmation requires calendar time and separately agreed scheduling; engineering completion is not completed validation.

## Agent Prompt

Pilot complete; do not repeat acquisition automatically. Reproduce companions offline with `uv run python docs/research/backtesting-promotion-foundation/readiness_source_pilot.py --export` using retained quarantine summary. Source check implementation/tests: `readiness_source_pilot.py`, `tests/test_readiness_source_pilot.py`. Preserve old attempts/manifests. Any expanded acquisition or prospective protocol activation requires new agreed scope; no automatic Candidate search or empirical admission.
