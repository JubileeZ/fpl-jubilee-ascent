# Active Task: Explorer Table Component Metrics & Inspection UX

- **Status:** In Progress
- **Objective:** Curate Explorer table with sortable component metrics (xP GI, xP Goals, xP Assists, xP CS, xP DefCon), view presets (Overview, Attacking, Defensive, All), hidden ID column, and clean top Action Bar for player inspection without unwanted modal popups.
- **Acceptance:** Table sorts on component points; ID hidden; View Presets switch column sets; clicking player highlights row and updates Action Bar with 1-click Inspect Details button; tests and ruff pass.
- **Issue/Ticket:** UI/UX table component metrics & inspection upgrade

## Work Packet (SFDBN)

- **Status:** In Progress
- **Files:** `dashboard/explorer.py`, `dashboard/streamlit_dashboard.py`, `tests/test_streamlit_dashboard.py`
- **Decisions:** 
  - Expose component points (xp_goals, xp_assists, xp_gi, xp_clean_sheet, xp_defcon, etc.) as sortable columns in Explorer table.
  - Implement 4 View Presets via `st.segmented_control`: Overview, Attacking, Defensive, All Components.
  - Hide internal `ID` and `Bubble Size` columns from table view.
  - Decouple row click from immediate modal popup; provide sticky Action Bar directly above table with player summary, `🔍 Inspect Details`, and watchlist toggle.
  - Remove redundant 600-item dropdown underneath the table.
- **Blocked:** None
- **Next:** User review and acceptance

## Todo
- [x] Add `xp_gi` calculation to `player_slice` in `dashboard/explorer.py`
- [x] Implement View Presets and curated column mappings in `dashboard/streamlit_dashboard.py`
- [x] Update `select_explorer_player` and add Action Bar above the table
- [x] Remove old dropdown and button below the table
- [x] Add unit tests for view presets, component columns, and Action Bar in `tests/test_streamlit_dashboard.py`
- [x] Run ruff check and pytest
- [ ] User review and acceptance in dashboard

## Blockers / Notes
- None
