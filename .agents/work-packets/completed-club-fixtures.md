# Active Task: Completed Club Fixtures xMins

- **Status:** Landed in this commit
- **Objective:** Finished fixtures only as Club Fixtures; live/future 0 not DNP; Prior-Season Seed skips live pin; state shrink strength 1
- **Acceptance:** Two finished 90s ignore live 0; unfinished-only hist is Cold-Start; seed picker skips 2026-27; Full-Season GW1 window sees finished starts; João Pedro archive xMins ~72
- **Issue/Ticket:** ADR 0026

## Work Packet (SFDBN)

- **Status:** Landed
- **Files:** `features/builder.py`, `commands/dashboard.py`, `commands/export_dashboard.py`, `commands/run_model.py`, `tests/test_club_fixture_shrinkage.py`, CONTEXT, ADR 0022/0024/0026, current-state
- **Decisions:** Incomplete History Row not DNP. Seed = latest completed season. State strength 1; rate strength 4. Full-Season export uses `history_before_gw=39`.
- **Blocked:** None
- **Next:** None
