# Active Task: Explorer Assume 90

- **Status:** Landed in this commit
- **Objective:** Global Assume 90 toolbar toggle next to Y-axis; all Players 90 mins per existing GW
- **Acceptance:** Checkbox `explorer-assume-90`; rate equals per_gameweek on single fixtures; pytest
- **Issue/Ticket:** ADR 0022 view-only overlay; not Feature Contract

## Work Packet (SFDBN)

- **Status:** Landed
- **Files:** `projections/explorer_slice.py`, `dashboard/explorer.js`, `dashboard/index.html`, tests, CONTEXT, README, ADR 0021/0022, current-state
- **Decisions:** Toolbar checkbox next to Projected Rate / xP per Gameweek. Blank GW stays 0. Not Feature Contract / xmins_cap.
- **Blocked:** None
- **Next:** None
