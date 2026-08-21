# Active Task: dashboard-transfer-plan-re-solve

- **Status:** Implemented. Live Champion CSV has GW1–38. Click Re-solve on running dashboard (process started before ensure). Not committed.
- **Objective:** Transfer Plan tab Re-solve works after `commands.dashboard` without a matching 6-GW Champion CSV. Invalid `data/solution.json` does not break GET `/api/transfer-plan`.
- **Acceptance:** `solver_csv_covers_horizon` is false for GW1–5 CSV at horizon 6. `write_solver_projection_csvs` emits `6_Pts`. `pad_solver_csv_horizon` adds missing week columns. `load_transfer_plan_document` returns None for truncated/legacy JSON. Live Champion CSV covers GW6. `uv run pytest tests/test_transfer_plan.py` plus ruff.
- **Issue/Ticket:**

## Seams (TDD)

- `projections.exporter.solver_csv_covers_horizon` / `write_solver_projection_csvs` / `pad_solver_csv_horizon`
- `commands.dashboard.ensure_solver_projection_csv` / `run_dashboard_transfer_plan`
- `commands.solve.execute_transfer_plan`
- `commands.export_dashboard.load_transfer_plan_document`

## Work Packet (SFDBN)

- **Status:** Implemented. Live Champion CSV has GW1–38. Click Re-solve on running dashboard (process started before ensure). Not committed.
- **Files:** `projections/exporter.py`; `commands/dashboard.py`; `commands/solve.py`; `commands/export_dashboard.py`; `dashboard/app.js`; `dashboard/explorer.js`; `dashboard/index.html`; `tests/test_transfer_plan.py`; `docs/agents/current-state.md`
- **Decisions:** Export writes solver CSVs from Full-Season Window preds. Re-solve rebuilds Champion CSV when `{week}_Pts` missing. `execute_transfer_plan` pads missing week columns. GET 404 for non-plan JSON. Isolate explorer/plan init so tab listeners still bind.
- **Blocked:** none
- **Next:** User: Transfer Plan → Re-solve (minutes). Header Champion linear_baseline is stub until Re-solve succeeds.

## Todo
- [x] Reproduce: 5-GW CSV vs horizon 6; truncated solution.json
- [x] Tests + CSV write/ensure/pad + GET 404
- [x] Write GW6+ columns from dashboard JSON into live solver CSVs
- [ ] User: Transfer Plan → Re-solve (minutes). Header Champion linear_baseline is stub until Re-solve succeeds.
- [ ] Commit if wanted
