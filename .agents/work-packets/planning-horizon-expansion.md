# Active Task: Planning Horizon Expansion (10-GW Default, 12-GW Recommended Boundary, 19-GW Half-Season Hard Cap)

- **Status:** In Progress
- **Objective:** Update planning horizon architecture across solver, CLI, skills, domain glossary, and unit tests.
- **Acceptance:** Full test suite passes; MAX_PLANNING_HORIZON == 19; DEFAULT_PLANNING_HORIZON == 10; skills and docs synchronized.
- **Issue/Ticket:** Planning Horizon Expansion

## Work Packet (SFDBN)

- **Status:** Implementing
- **Files:** solver/planning.py, solver/utils.py, commands/solve.py, commands/injury_triage.py, CONTEXT.md, .agents/skills/transfer-planner/SKILL.md, docs/adr/0067-planning-horizon-architecture.md, tests/test_planning.py, tests/test_transfer_plan.py
- **Decisions:** MAX_PLANNING_HORIZON=19, DEFAULT_PLANNING_HORIZON=10, recommended boundary <= 12 GW, advisory warning for H > 12 suggesting --gap 0.002.
- **Blocked:** None
- **Next:** Execute TDD seams: failing tests -> code updates -> passing tests.

## Todo
- [ ] Seam 1: Update test_planning.py for MAX_PLANNING_HORIZON == 19 (Red -> Green)
- [ ] Seam 2: Update test_transfer_plan.py for DEFAULT_PLANNING_HORIZON == 10 (Red -> Green)
- [ ] Seam 3: Update commands/solve.py and commands/injury_triage.py with 10-GW default and >12 GW advisory warning
- [ ] Seam 4: Update .agents/skills/transfer-planner/SKILL.md
- [ ] Seam 5: Update CONTEXT.md and draft ADR 0067
- [ ] Verification: ruff check, pytest, code-review

## Blockers / Notes
- None
