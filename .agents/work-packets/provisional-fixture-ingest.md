# Active Task: provisional-fixture-ingest

- **Status:** In Progress
- **Objective:** Allow full-time provisionally finished matches (`finished_provisional == True`) into dashboard actuals, feature builder completed rows, and model fitting mid-gameweek.
- **Acceptance:**
  1. `fixtures.parquet` retains `finished_provisional`.
  2. `features/builder.py` recognizes fixtures as completed when `finished == True` or `finished_provisional == True`.
  3. `commands/export_dashboard.py` `_load_player_actuals` accumulates actuals over all completed Club Fixtures without requiring the entire Gameweek to be finished, and scopes to registered club when fixture clubs exist.
  4. Live `model.fit()` in `export_dashboard.py` and `run_model.py` receives completed Club Fixtures aligning with `build_features()`.
  5. `streamlit_dashboard.py` uses completed Club Fixtures as the `mins / GW` denominator in the Reality Check table and guards against falsy zero fixtures.
  6. Mid-gameweek feature building passes `immediate_next_gw=target_start` so ADR 0056 hard DNP zeros confirmed non-starters on upcoming deadline (GW8) and preserves ADR 0052 CLI/Dashboard parity.
  7. `player_history` excludes unplayed provisional fixtures.
  8. Domain glossary in `CONTEXT.md` and `docs/adr/0026-completed-club-fixtures-state-shrink.md` reflect updated definitions in telegraphic style.
  9. All tests pass, Ruff clean, `tests/verify.sh` passes.
- **Issue/Ticket:** User Request 2026-10-19 (Q1 B, Q2, Q3, Q4)

## Work Packet (SFDBN)

- **Status:** In Progress
- **Files:**
  - `features/processor.py`
  - `docs/data_dictionary.md`
  - `features/builder.py`
  - `commands/export_dashboard.py`
  - `commands/run_model.py`
  - `dashboard/planner_service.py`
  - `dashboard/streamlit_dashboard.py`
  - `CONTEXT.md`
  - `docs/adr/0026-completed-club-fixtures-state-shrink.md`
  - `docs/agents/current-state.md`
  - `tests/test_provisional_fixtures.py`
- **Decisions:**
  - Full-time matches (`finished | finished_provisional`) are completed Club Fixtures. In-play and pre-kickoff matches are Incomplete History Rows.
  - Underlying Actuals accumulate over completed Club Fixtures, removing whole-Gameweek gate and scoping to current club when fixture clubs exist.
  - Live `model.fit()` receives `completed_performance_rows` matching `build_features` history.
  - Mid-gameweek feature export passes `immediate_next_gw=target_start` so ADR 0056 hard DNP zeros confirmed non-starters on upcoming deadline (GW8) and preserves ADR 0052 CLI/Dashboard parity.
  - `player_history` filters unplayed fixtures before slicing last-6 matches.
- **Blocked:** None
- **Next:** Commit and push.

## Todo
- [x] Create unit tests in `tests/test_provisional_fixtures.py` (TDD)
- [x] Update `features/processor.py` and `docs/data_dictionary.md` to retain `finished_provisional`
- [x] Update `features/builder.py` completion helper across `completed_performance_rows`, `_finished_fixture_gameweeks`, and `point_in_time_players`
- [x] Support `immediate_next_gw` in `build_features` to fix ADR 0056 & ADR 0052 parity on upcoming target GW
- [x] Update `commands/export_dashboard.py` and `commands/run_model.py` for actuals and live `model.fit()`
- [x] Update `dashboard/planner_service.py` to filter unplayed fixtures in `player_history`
- [x] Update `dashboard/streamlit_dashboard.py` Reality Check denominator and falsy fallback
- [x] Update `CONTEXT.md` glossary and `docs/adr/0026-completed-club-fixtures-state-shrink.md` in telegraphic style
- [x] Re-process data/raw and re-export dashboard
- [x] Run `ruff check .`, `pytest`, `tests/verify.sh`
- [ ] Monitor user feedback and live usage on dashboard

## Blockers / Notes
- None
