# Active Task: Backtesting and promotion foundation

- **Status:** In Progress
- **Objective:** Implement temporary implementation_plan.md phase by phase; preserve Q1-Q28 and manual scientific approvals.
- **Acceptance:** Verified infrastructure and per-phase commits; no push; plan deleted only after delivery acceptance.
- **Issue/Ticket:** implementation_plan.md; docs/research/backtesting-promotion-foundation/backtesting-promotion-foundation.md

## Work Packet (SFDBN)

- **Status:** Phase 0 committed `a96af707`; Phase 1 committed `d4536c42`. Phase 2 accepted by both named reviewers; 139 focused and 772 full-suite passed, Ruff/new-core types clean. Phase 3 next; empirical follow-through explicit.
- **Files:** implementation_plan.md; proposed backtesting/replay_state.py and season_rules.py; models/scoring_matrix.py and scoring callers; native state/rule tests and documentation; durable tracking.
- **Decisions:** Exactly three fresh agents per phase: `phase_NN_implement` (GPT-6.1 Terra Medium), `phase_NN_review_standards` + `phase_NN_review_spec` (GPT-6.1 Sol xhigh). Current team `phase_02_*`; Phase 1 team completed, prior reused names retired. Current branch main; local phase commits, no push. Numerical freeze, adoption, rollback and sealed-data amendments retain explicit approval barriers.
- **Blocked:** Empirical admission and numerical protocol still unapproved. User accepted existing timing-only test exception for phase commits; no test weakening.
- **Next:** Portable gate/final diff and Phase 2 local commit; then fresh `phase_03_implement`, `phase_03_review_standards`, `phase_03_review_spec` team for causal issue-by-target forecasts/store. No push.

## Todo
- [x] Complete Phase 0 contracts, tests and review; 14 focused passes, type/Ruff clean, 29 portable gate passes; full suite 705 passes plus accepted existing timing exception.
- [x] Complete reviewed Phase 1 synthetic engineering checkpoint; 61 focused passes, lint/type clean, 753 full-checkpoint passes plus accepted timing exception. Empirical/native/adapter follow-through retained explicitly in plan.
- [x] Complete scoped Phase 2 native state/scoring checkpoint; both reviews accepted, 139 focused and 772 full-suite passes, Ruff/new-core types clean. Causal calendar/source adapters and empirical applicability remain explicit.
- [ ] Implement subsequent phases in dependency order; preserve approval barriers.
- [ ] Final validation, cleanup, plan deletion and confirmation.

## Blockers / Notes
- Preserve existing conversation-owned research artifacts. No real HTTP in tests; no sealed/archive mutations.
- Checkpoint B acquisition scope explicitly approved by user 2026-10-29: immutable public input snapshots and separately held finalized outcome/component packages for 2023-24, 2024-25, 2025-26. Excludes entire 2026-27, archive edits, model comparisons, solver runs. Approval not empirical admission or numerical freeze.
