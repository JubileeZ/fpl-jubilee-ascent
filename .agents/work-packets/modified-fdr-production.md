# Active Task: Production Modified FDR

- **Status:** Implemented, uncommitted
- **Objective:** Official Fixture Difficulty stays on `fixtures.parquet`. Feature Contract, Champion xP, FDR report, and backtests use Modified FDR.
- **Acceptance:** `uv run pytest tests/test_modified_fdr.py tests/test_fdr_report.py tests/test_model.py tests/test_fixture_contract.py` pass. Home official 2 → difficulty 1.75; away official 5 → 5.25; missing official → 3.0.
- **Issue/Ticket:** grill Q1–Q6 2026-08-26

## Work Packet (SFDBN)

- **Status:** Code + docs in working tree
- **Files:** `features/fdr.py`, `features/builder.py`, `commands/fdr_report.py`, `dashboard/plan.js`, ADR 0019, CONTEXT, tests
- **Decisions:** ±0.25 overlay; no clamp; blanks 3.0; derive not overwrite parquet; backtests included
- **Blocked:** None
- **Next:** Delete this packet after the code commit

## Todo
- [x] `features/fdr.py` + `_fixture_maps` + `fdr_report`
- [x] Tests
- [x] ADR 0019, labels, data dictionary, current-state
- [x] ruff; FDR/model tests pass
- [ ] Delete this packet after the code commit

## Blockers / Notes
- Grill: Q1 docs-only mapping; Q2 ±0.25; Q3 replace scoring everywhere; Q4 derive; Q5 backtests; Q6 unclipped, blanks 3.0
