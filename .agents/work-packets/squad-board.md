# Active Task: Squad Board on Ownership Explorer

- **Status:** In Progress
- **Objective:** Draw User Squad + ephemeral Squad What-If + Component Profile on Ownership Explorer
- **Acceptance:** Dashboard Data Contract has ITB/Selling Price/FT; board shows owned 15; What-If deltas; Mix not drawn; `uv run ruff check .`, `uv run pytest`, `bash tests/verify.sh`
- **Issue/Ticket:** ADR 0027

## Work Packet (SFDBN)

- **Status:** Implementing
- **Files:** `projections/squad_board.py`, `commands/export_dashboard.py`, `dashboard/squad.js`, `dashboard/index.html`, `dashboard/explorer.js`, `dashboard/app.js`, `CONTEXT.md`, `docs/adr/0027-squad-board-on-ownership-explorer.md`
- **Decisions:** This-Season Evidence is on (GW1–2 finished); Champion xP is this-season shrinkage. Squad Board per ADR 0027.
- **Blocked:** None
- **Next:** User Refresh + drag-drop smoke in browser

## Todo
- [x] Export ITB / selling price / xp_* 
- [x] Squad What-If scoring module
- [x] Squad Board UI; remove Mix
- [ ] User Refresh + drag-drop smoke in browser

## Blockers / Notes
- Live 2026-27: finished GW1–2; completed performance rows 1325; Prior-Season Seed is 2025-26 archive only during Cold-Start (ended).
