# Active Task: Explorer dashboard Refresh and Planning Horizon

- **Status:** Checkpoint
- **Objective:** Ownership Explorer-only dashboard; in-page Dashboard Refresh; Planning Horizon Start–End max 6
- **Acceptance:** pytest, ruff, verify.sh. No Transfer Plan tab. `/api/refresh`. Start/End selects. Clamp max 6.
- **Issue/Ticket:** ADR 0021

## Work Packet (SFDBN)

- **Status:** Landed in this commit
- **Files:** `dashboard/`, `commands/dashboard.py`, `commands/export_dashboard.py`, `commands/solve.py`, `solver/planning.py`, `solver/utils.py`, tests, README, AGENTS.md, CONTEXT, ADR 0021
- **Decisions:** ADR 0021. ADR 0016 Role unchanged. Refresh `--keep-roles` when table missing; Project refuses.
- **Blocked:** None
- **Next:** None
