# Active Task: Planning Horizon cap 10

- **Status:** Done
- **Objective:** Raise Planning Horizon max length from 6 to 10; default length stays 6
- **Acceptance:** `clamp_planning_horizon(10)==10`, `clamp_planning_horizon(11)==10`; `solve --horizon 10` keeps 10; pytest + ruff + verify.sh
- **Issue/Ticket:** none

## Work Packet (SFDBN)

- **Status:** Done. ruff pass; pytest 314; verify.sh 107/0.
- **Files:** `solver/planning.py`, `commands/solve.py`, `dashboard/app.js`, tests, CONTEXT, ADR 0021/0029, README
- **Decisions:** Default length 6. Cap 10. Full-Season still 38. CLI warns when clamped.
- **Blocked:** none
- **Next:** Commit when asked; delete this packet in that Checkpoint.

## Todo
- [x] `MAX_PLANNING_HORIZON = 10`
- [x] Tests, dashboard JS, glossary/ADR/README
- [x] ruff, pytest, verify.sh
