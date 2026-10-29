# Active Task: Backtesting and promotion foundation

- **Status:** In Progress
- **Objective:** Implement temporary implementation_plan.md phase by phase; preserve Q1-Q28 and manual scientific approvals.
- **Acceptance:** Verified infrastructure and per-phase commits; no push; plan deleted only after delivery acceptance.
- **Issue/Ticket:** implementation_plan.md; docs/research/backtesting-promotion-foundation/backtesting-promotion-foundation.md

## Work Packet (SFDBN)

- **Status:** Phase 0 committed `a96af707`; Phase 1 synthetic engineering accepted by both reviewers. Final 61 focused passes, lint/type clean; full checkpoint 753 passes plus accepted existing timing failure. Phase 2 next.
- **Files:** implementation_plan.md; backtesting/evaluation_protocol.py; backtesting/data_admission.py; backtesting/admission_fixtures.py; focused tests; foundation research companions; durable tracking.
- **Decisions:** Exactly three fresh agents per phase: `phase_NN_implement` (GPT-6.1 Terra Medium), `phase_NN_review_standards` + `phase_NN_review_spec` (GPT-6.1 Sol xhigh). Current Phase 1 team uses `phase_01_*`; prior reused names retired. Current branch main; local phase commits, no push. Numerical freeze, adoption, rollback and sealed-data amendments retain explicit approval barriers.
- **Blocked:** Empirical admission and numerical protocol still unapproved. User accepted existing timing-only test exception for phase commits; no test weakening.
- **Next:** Commit reviewed Phase 1 engineering checkpoint; retain explicit empirical/native/adapter follow-through. Create fresh `phase_02_implement`, `phase_02_review_standards`, `phase_02_review_spec` team; implement native state/scoring contracts. No push.

## Todo
- [x] Complete Phase 0 contracts, tests and review; 14 focused passes, type/Ruff clean, 29 portable gate passes; full suite 705 passes plus accepted existing timing exception.
- [x] Complete reviewed Phase 1 synthetic engineering checkpoint; 61 focused passes, lint/type clean, 753 full-checkpoint passes plus accepted timing exception. Empirical/native/adapter follow-through retained explicitly in plan.
- [ ] Implement subsequent phases in dependency order; preserve approval barriers.
- [ ] Final validation, cleanup, plan deletion and confirmation.

## Blockers / Notes
- Preserve existing conversation-owned research artifacts. No real HTTP in tests; no sealed/archive mutations.
- Checkpoint B acquisition scope explicitly approved by user 2026-10-29: immutable public input snapshots and separately held finalized outcome/component packages for 2023-24, 2024-25, 2025-26. Excludes entire 2026-27, archive edits, model comparisons, solver runs. Approval not empirical admission or numerical freeze.
