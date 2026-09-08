# Active Task: Explorer Primary Model job lock

- **Status:** In Progress
- **Objective:** Refresh/Solve exclusive; project selected Primary Model only; serial Dream Team MILP
- **Acceptance:** pytest targeted 37 passed; ruff clean; 409 exclusivity; Champion if model missing/`default`; JS disables both buttons + posts model

## Work Packet (SFDBN)

- **Status:** Code ready. Commit+push. Live dashboard confirm after pull.
- **Files:** `commands/dashboard.py`, `commands/dream_team.py`, `commands/export_dashboard.py`, `dashboard/app.js`, `models/selection.py`, `solver/solver.py`, tests, ADR/CONTEXT/README
- **Decisions:** Default export Champion (or posted Primary). `--models` keeps slate. Refresh vs Solve exclusive (409). HiGHS `parallel=off` `threads=1` for Dream Team. Placeholder `default` maps to Champion.
- **Blocked:** None
- **Next:** After push, Refresh then Solve on one machine; confirm buttons disable together.

## Todo
- [x] Primary-only projection helper
- [x] Exclusive Refresh/Solve API + UI
- [x] Serial Dream Team HiGHS
- [x] Docs + verify
- [x] Review: reject HTML `default` model
- [ ] Confirm Refresh/Solve exclusivity on live dashboard after pull
