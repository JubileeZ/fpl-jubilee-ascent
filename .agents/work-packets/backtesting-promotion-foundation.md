# Active Task: Backtesting and promotion foundation

- **Status:** In Progress
- **Objective:** Implement temporary implementation_plan.md phase by phase; preserve Q1-Q28 and manual scientific approvals.
- **Acceptance:** Verified infrastructure and per-phase commits; no push; plan deleted only after delivery acceptance.
- **Issue/Ticket:** implementation_plan.md; docs/research/backtesting-promotion-foundation/backtesting-promotion-foundation.md

## Work Packet (SFDBN)

- **Status:** Phase 0 reviewed/verified; Phase 1 engineering active.
- **Files:** implementation_plan.md; backtesting/evaluation_protocol.py; related tests/workflow; durable tracking.
- **Decisions:** Terra Medium implements sequential phases; Sol xhigh reviews. Current branch main; no push. Numerical freeze, adoption, rollback and sealed-data amendments retain explicit approval barriers.
- **Blocked:** Empirical admission/calibration approvals pending. User accepted existing timing-only test exception for phase commits; no test weakening.
- **Next:** Commit Phase 0 on main, no push; implement/review Phase 1 admission.

## Todo
- [x] Complete Phase 0 contracts, tests and review; 14 focused passes, type/Ruff clean, 29 portable gate passes; full suite 705 passes plus accepted existing timing exception.
- [ ] Implement subsequent phases in dependency order; preserve approval barriers.
- [ ] Final validation, cleanup, plan deletion and confirmation.

## Blockers / Notes
- Preserve existing conversation-owned research artifacts. No real HTTP in tests; no sealed/archive mutations.
