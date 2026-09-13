# Active Task: Transfer Plan Start binds to open deadline

- **Status:** Done
- **Objective:** Bind Transfer Plan Start to open deadline (is_next) instead of live in-play gameweek
- **Acceptance:** uv run pytest 320 passed; commands.solve, commands.run_model, commands.report unified under resolve_default_target_gw; ADR 0031
- **Issue/Ticket:** ADR 0031

## Work Packet (SFDBN)

- **Status:** Gates green; ready to commit
- **Files:** solver/planning.py, commands/solve.py, commands/run_model.py, commands/report.py, projections/exporter.py, CONTEXT.md, docs/adr/0031-transfer-plan-start-open-deadline.md, tests/test_planning.py, tests/test_report.py
- **Decisions:** Executable Transfer Plan starts at is_next (GW5), not live in-play week. Ownership Explorer retains live in-play start. Report accepts --target_gw and validates columns.
- **Blocked:** none
- **Next:** none

## Todo
Completed this session. Checkpoint record for commit-gate.

## Blockers / Notes
- None
