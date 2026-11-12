# Active Task: Offline input evidence contracts

- **Status:** In Progress
- **Objective:** Implement agreed Q7 input contracts, offline validation and retained GW2 assessment; preserve closed empirical authority.
- **Acceptance:** Field-specific blockers from retained bytes; receipt contract with offline tests; full checks and two-axis review; commit current branch.
- **Issue/Ticket:** User-approved Q5/Q7; spec below.

## Work Packet (SFDBN)

- **Status:** Contracts and retained assessment implemented; focused/type checks pass; full suite running; review pending.
- **Files:** `backtesting/input_evidence.py`, retained-pilot adapter/report, offline tests; prior uncommitted source-pilot delivery included in checkpoint.
- **Decisions:** Public test seams already agreed: input contract validation, missing/uncertain evidence handling, retained-pilot assessment, future raw receipt retention. No arbitrary freshness limits; empirical promotion remains disabled. Justified reconstruction allowed with supported bounds; unknown timestamps stay unknown.
- **Blocked:** Historical provenance/coverage and numerical approval unresolved; blockers must appear in report rather than stop contract implementation.
- **Next:** Finish full suite, checkpoint current branch, review against `48a9c708`, resolve findings, final delivery checkpoint.

## Todo

- [x] Contracts, offline source/player/schedule validation and immutable receipt fixtures.
- [x] Retained pilot adapter, field report and lineage trace.
- [ ] Full validation and independent Standards/Spec review.
- [ ] Commit delivery, delete finished packet.

## Blockers / Notes

Spec: each required input retains source identity/hash, timing evidence/uncertainty, reconstruction basis, missing/coverage/lineage evidence and limitations. Apply to pinned 2025-26 GW2 plus GW1 anchor/seed dependencies without source expansion. Receipt-only offline retention distinct from existing verified-forecast capture. No scheduling, empirical admission activation, Candidate search, future-window selection, sealed data, Champion/archive/ledger modification. Future freshness/eligibility rules, practical harm limits, calibrated inference and fresh-confirmation window remain separate approval items.

Review baseline `48a9c70862197f2bf14199ffbf2a19a5cfb3f62b` includes prior authorized uncommitted source pilot; review both delivery and new contracts. TDD skill seam confirmation satisfied by Q7 agreement; no additional permission round for implementation details.
