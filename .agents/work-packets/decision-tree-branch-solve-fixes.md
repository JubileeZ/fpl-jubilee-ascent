# Active Task: decision-tree-branch-solve-fixes

- **Status:** In Progress
- **Objective:** Fix branch solve model resolution, node serialization key mismatch, parent node state inheritance, risk preset limits, and live operational 0% availability.
- **Acceptance:** Tests pass, ruff check clean, Map #143 child tickets unblocked and verifiable.
- **Issue/Ticket:** [Issue #143](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/143)

## Work Packet (SFDBN)

- **Status:** Implemented and verified across all 6 child tickets (#144-#149) and 4 manager archetypes; committing checkpoint.
- **Files:** commands/dashboard.py, solver/transfer_plan.py, commands/solve.py, features/builder.py, models/participation_state_hybrid.py, dashboard/src/components/, CONTEXT.md, tests/test_dashboard.py, tests/test_participation_state_hybrid.py.
- **Decisions:** Default to Champion on unspecified datasource; parent node state inherited on branch solves; risk presets enforce hit limits (Safe 0, Default 1, Optimistic 1, High Risk 2); live 0% availability zeroed next GW via ADR 0056; pseudo-variance replaced with deterministic comparisons; inline canvas chip booking with store propagation.
- **Blocked:** None.
- **Next:** Push commit to origin/main.

## Todo
- [x] #144 Fix branch solve model resolution and node serialization key mismatch
- [x] #145 Inherit parent node squad and bank state in branch optimization solves
- [x] #146 Enforce risk preset weekly hit limits and align domain terminology
- [x] #147 Implement operational zero-availability hard DNP exception (ADR 0056)
- [x] #148 Refactor Plans Evaluation Suite to honest deterministic metrics
- [x] #149 Add chip selection controls to decision canvas and fix drawer FT budget
- [ ] Push commit to origin/main

## Blockers / Notes
- None
