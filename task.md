# Active Task: Complete open issue batch

- **Status:** Complete; GitHub issues closed
- **Objective:** Implement remaining #79–#82 features and reconcile all eight open GitHub issues.
- **Acceptance:** Captain/vice report, chip validation, price history/reporting, and tuning controls pass tests; #75/#79–#83/#86/#87 are ready for closure.
- **Issue/Ticket:** #75, #79, #80, #81, #82, #83, #86, #87

## Work Packet (SFDBN)

- **Status:** Implementation complete; final validation and GitHub synchronization pending.
- **Files:** `commands/report.py`, `commands/solve.py`, `commands/run_model.py`, `commands/refresh_data.py`, `commands/price_report.py`, `features/builder.py`, tests, docs
- **Decisions:** Keep explicit CLI behavior; reject unsupported solver overrides; append immutable price snapshots; validate booked chips before solver preparation.
- **Blocked:** None.
- **Next:** Maintenance, real-data validation, or next product request.

## Todo
- [x] Implement #75 archive fallback and #87 FDR report.
- [x] Implement #79 captain/vice, #80 chip validation, #81 price tracking, and #82 tuning surface.
- [x] Run final gate and close GitHub issues.

## Blockers / Notes
- None
