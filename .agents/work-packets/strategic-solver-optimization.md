# Active Task: strategic-solver-optimization

- **Status:** In Progress
- **Objective:** Implement Strategic Solver Optimization view, native HiGHS MILP variance constraints, ADR 0061, transfer-planner skill alignment, and --xmins-override integration
- **Acceptance:** Full test suite passes, verify.sh clean, ruff clean, all 5 strategic variance constraints verified with automated tests, CLI and dashboard operational
- **Issue/Ticket:** Strategic Solver Optimization (#166)

## Work Packet (SFDBN)

- **Status:** In Progress
- **Files:**
  - `.agents/handoff-pointer`
  - `.agents/skills/transfer-planner/SKILL.md`
  - `CONTEXT.md`
  - `commands/dashboard.py`
  - `commands/solve.py`
  - `commands/transfer_plan_scenarios.py`
  - `dashboard/plan.js`
  - `dashboard/planner.py`
  - `dashboard/planner_service.py`
  - `dashboard/streamlit_planner.py`
  - `docs/adr/0061-strategic-variance-scenario-and-unconstrained-rename.md`
  - `docs/agents/current-state.md`
  - `solver/scenarios.py`
  - `solver/solver.py`
  - `solver/transfer_plan.py`
  - `tests/test_dashboard.py`
  - `tests/test_solve.py`
  - `tests/test_strategic_solver.py`
  - `tests/test_streamlit_planner.py`
  - `tests/test_transfer_plan_scenarios.py`
- **Decisions:**
  - ADR 0061 replaces Conservative with Strategic and renames Optimal to Unconstrained.
  - Retire former Conservative heuristics (flagged bans and single-match missed starter locks) in favor of 5 quantitative MILP variance constraints.
  - Implement native continuous slack variables and objective penalties in HiGHS MILP.
  - Propagate --xmins-override end-to-end to single-arm and 3-arm scenarios.
- **Blocked:** None
- **Next:** Stage work packet and commit changes.

## Todo
- [x] Record ADR 0061 and update CONTEXT.md
- [x] Update solver/scenarios.py with ARM_STRATEGIC, ARM_UNCONSTRAINED, ARM_NO_HIT and DEFAULT_STRATEGIC_OPTIONS
- [x] Implement HiGHS MILP strategic constraints and strategic_audit in solver/solver.py and solver/transfer_plan.py
- [x] Wire CLI flags and xmins_override in commands/solve.py and commands/transfer_plan_scenarios.py
- [x] Update dashboard/planner.py, dashboard/planner_service.py, and dashboard/streamlit_planner.py
- [x] Update .agents/skills/transfer-planner/SKILL.md
- [x] Create tests/test_strategic_solver.py and update existing scenario/planner/solve tests
- [x] Verify ruff, pytest, and verify.sh
- [ ] Monitor user feedback and live usage in Streamlit Transfer Planner

## Blockers / Notes
- None
