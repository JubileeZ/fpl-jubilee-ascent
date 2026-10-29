# Foundation preflight and calibration proposal

**Updated**: 2026-10-29T13:36:20+07:00\
**Status**: Proposed; prepared for review, not executed.\
**Authority**: [Agreed policy direction Q1-Q28](backtesting-promotion-foundation.md), refined after independent/subagent review.\
**Purpose**: Establish whether available evidence and replay machinery can support policy; propose defensible numerical settings before testing finalists.

## Scope and order

### 1. Map data and replay feasibility

Inspect historical schemas/provenance and relevant code. Produce per-season applicability/coverage matrix for prices, club membership, fixture schedule known at deadline, player universe/availability, outcomes/components, financial state, and native scoring/transfer/chip rules.

Trace future-first-row/terminal fallbacks, missing-results-as-zero substitutions, skipped deadlines, unconstrained solver fallbacks, and missing required gate metrics. Distinguish verified behavior, unmeasured impact, and required correction.

Classify each proposed input/window: usable, usable with disclosed limitations, or invalid/unavailable. Do not silently substitute data or move window because result unfavorable. Keep sealed 2026-27 evidence excluded.

For Q28, admit one highest-owned feasible GW1 reference per season from verified ownership/price/club/position/eligibility snapshot. Metadata coverage and three public sample contents already checked in [ownership feasibility report](ownership-anchor-feasibility.md); commit/capture-time admission and freshness remain. Raw ownership percentage plus feasibility constraints defines initial squad, independently of evaluated models. No mandatory multi-archetype panel.

Record issue deadline and future target GW/fixture for each horizon forecast. All targets use history/schedule known at common issue deadline; distinguish blank fixture, unknown schedule, missing forecast, and absent outcome. Native rules govern projected point conversion as well as observed scores/accounting.

**Completion:** Each required field has provenance and pre-deadline availability decision; blockers to valid replay identified. Unsupported data prevents performance claims, not methodology documentation.

### 2. Specify replay-accounting contract

Trace squad, bank, acquisition/selling prices, free transfers, hits, captain/vice, bench substitutions, chips/temporary restoration, and season transitions. Define deterministic offline examples with known expected outcomes and invariant checks required before trusting full replay.

Lock common fifteen at GW1 deadline, evaluate GW1 lineup/captain, start transfers GW2 using native rules, and preserve independent states afterward. Unlimited preseason redrafting must not discard anchor. Initial bank equals total capital minus squad spending; never add full budget on top of owned fifteen.

Review current helper behavior; identify minimum corrections needed. Proposed research-only harness must not claim existing replay trustworthy merely because it returns points. Any implementation fixes receive explicit scope in follow-up plan.

**Completion:** State-transition/scoring contract, known gaps, and concrete verification cases documented. Invalid engine cannot generate promotion evidence.

### 3. Run bounded development-only cost probe after review

Use Champion only, no new Candidate lever. Select deadline problems before inspecting outcomes, spanning ordinary, constrained-budget, transfer-heavy, and chip-enabled cases where valid construction possible. Match agreed six-GW Strategic policy and native rules.

Initial proposed execution envelope: at most 20 optimizer calls, at most 30 seconds per call, one solver thread, serial execution. Stop initial probe after 20 minutes total elapsed, including features/projections. These are proposed safety/workload limits, not measured runtime or adopted final-gate settings.

Use paired identical-input problems to contrast current exact-target setting with explicitly recorded approximate targets. Actual trial tolerance values belong in profiling manifest before execution; they are probes, not adopted policy thresholds. Record all attempts, including timeouts and infeasible problems.

Record machine/runtime/solver versions, model/data/protocol identities, construction/feature/fit/projection/solver times, memory where available, termination status, feasible objective/bound/gap, selected decisions, cache keys/hits, and interruptions. No external HTTP in verification fixtures; no live authentication.

**Completion:** Measured cost report or explicit infeasibility report. Timed-out calls are censored timings, not proof full solves complete within cap. Do not extrapolate precise overnight runtime from predominantly unfinished jobs. Widening probe budget requires review.

### 4. Prepare statistical and product-tolerance proposal

Use development-only evidence and controlled synthetic/null examples to examine calendar dependence, correlated starting states, bootstrap implementation, repeated-search accounting, and behavior under known zero/positive/negative effects. No tuning against confirmation or sealed outcomes.

Specify estimand, unit of comparison, season/state weights, uncertainty assumptions, confidence/decision method, and attempt-family definition. Test edge cases: missing data, inactive periods, incomplete seasons, unequal coverage, and repeated reviews.

Assess whether method can justify agreed 5% family-wise target. Simulation success is diagnostic, not proof of validity for football histories. If assumptions/evidence insufficient, state limitation and design fresh prospective protocol; do not label ordinary positive bootstrap fraction calibrated significance.

Propose material-loss and projection-error tolerances with explicit units and practical implications. Human chooses harm tolerance; observed noise informs feasibility/power, not what harm is acceptable. Assess component availability before declaring mandatory metrics. No limits adjusted after finalist result.

**Completion:** Numerical proposal plus uncertainty/power limitations, submitted for human approval before freeze. No Candidate Pass/Fail or Champion adoption generated by calibration.

## Deliverables for protocol approval

- Data coverage/applicability matrix and replay correctness gaps.
- Measured runtime/quality/cache report or explicit blockers; distinguish assumptions from measurements.
- Verified highest-owned feasible opening anchor per admitted season, deterministic ties, initial finances/GW1 lock, season weights and continuous scored windows. Extra archetypes optional sensitivity only.
- One causal shared chip calendar and exact frozen Strategic settings/native rules.
- Solver-quality tolerance, timeout handling, final evaluation budget, and resumability identity.
- Total/minutes/component metrics, coverage rules, material-loss tolerances, and evidence outcomes.
- Statistical method/search registry, its assumptions, and limitations relative to 5% target.
- Fresh confirmation and live-review proposal: fixed registration/review rules, freeze, future data access, and manual adoption/rollback. Existing sealed protocol not changed implicitly.
- Legacy-verdict audit using recorded evidence only; specific reopening requests separately identified. No locked lever reruns.
- Follow-up implementation plan, verification requirements, and proposed ADR/glossary changes.

## Boundaries

Preflight produces feasibility and calibration evidence. Operational model selection, promotion workflow/gates, historical archives, and Candidate Ledger locks require separate reviewed implementation scope. No automatic adoption, unsealing, or broad retesting follows from accepting this plan.

Policy summary and full rationale remain in [foundation reference](backtesting-promotion-foundation.md). Existing operational Eval canon remains current until formal protocol adoption.
