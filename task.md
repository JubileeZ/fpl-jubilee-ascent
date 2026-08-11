# Active Task: Full-Season Ownership Value Explorer

- **Status:** Complete
- **Objective:** Move ownership explorer out of GW1–6 pipeline Stage 4 into standalone full-season (GW1–38) research topic with horizon toggle.
- **Acceptance:** Standalone `docs/research/ownership-value-explorer/`; season projections + interactive HTML; Stage 4 removed from pipeline; unit test + ruff + verify green.
- **Issue/Ticket:** Ownership Value Explorer (full season)

## Work Packet (SFDBN)

- **Status:** Complete
- **Files:** docs/research/ownership-value-explorer/**, data/research/ownership-value-explorer/**, gw1-6-preseason-pipeline run_pipeline/README/INDEX, tests/test_ownership_value_explorer.py, task.md, current-state.md
- **Decisions:**
  1. Separate from GW1–6 pipeline (season scope ≠ chip-window Stage).
  2. Default horizon GW1–38; HTML toggle retains GW1–6.
  3. Rates from Stage 2 expected-stats + availability priors + ParticipationStateHybridModel.
  4. X = ownership % (not EO); size = avg xMins; floor default 45.
- **Blocked:** None
- **Next:** Browse HTML for draft differentials; optional EO feed later.

## Todo
- [x] project_season_points.py (GW1–38)
- [x] plot_ownership_value_explorer.py with horizon toggle
- [x] Remove pipeline Stage 4 + old 04 folders
- [x] INDEX / README / tests / gates

## Blockers / Notes
- Needs Stage 2 CSV present before rebuild.
