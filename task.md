# Transfer Plan tab (dashboard + solver export)

**Objective:** Third dashboard tab Transfer Plan: Champion MILP over next 6 GWs, chip calendar + Re-solve, per-GW ledger and read-only pitch, undiscounted xP + labeled Solver Objective. Product Score World only.

**Acceptance:** `solution.json` is JSON-safe Transfer Plan. `commands.solve` and dashboard `--horizon` default 6. Tab shows weeks, chips, transfers, pitch. POST Re-solve with Booked Chips. Header Primary Model does not change the plan.

## Seams (TDD)

- `solver.transfer_plan.serialize_transfer_plan` — JSON-safe plan from solver solution
- `solver.utils.DEFAULT_PLANNING_HORIZON` / `load_settings` template — default 6
- `commands.solve.execute_transfer_plan` — writes `data/solution.json`; Champion datasource
- `commands.export_dashboard.build_dashboard_dataset` — embeds `transfer_plan`

## Work Packet (SFDBN)

- **Status:** Implemented. Uncommitted. Tests green for transfer-plan / solve / dashboard / tuning.
- **Files:** `solver/transfer_plan.py`; `solver/utils.py`; `commands/solve.py`; `commands/dashboard.py`; `commands/export_dashboard.py`; `dashboard/*`; `CONTEXT.md`; `docs/adr/0017-transfer-plan-dashboard.md`; `README.md`; `tests/test_transfer_plan.py`; `task.md`
- **Decisions:** Third tab. Viewer + Re-solve. User Squad or preseason. Horizon default 6. Champion + Official FDR. No Canonical CSV. Chip calendar. Ledger + GW pitch. One drop.
- **Blocked:** none
- **Next:**
  - [x] Serialize Transfer Plan (JSON-safe)
  - [x] Default Planning Horizon 6
  - [x] CLI + dashboard embed + POST Re-solve
  - [x] Transfer Plan tab UI
  - [x] ADR 0017 + README
  - [ ] User: `uv run python -m commands.dashboard` then Re-solve on Transfer Plan tab
