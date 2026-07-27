# 0011: Multi-Model Dashboard Comparison and Selection

## Context

The engine supports multiple projection models (Champion model `participation_state_hybrid` and Candidate models like `metrics_component_hybrid`). Evaluating relative projection behaviors, component distributions, and MILP squad selection across models requires side-by-side comparative inspection in the interactive web dashboard without sacrificing single-model clarity.

## Decision

Extend the dashboard data contract and web UI to support multi-model projection exports and side-by-side table comparisons.

1. **Export Engine Scope**: `commands.dashboard` / `commands.export_dashboard` bundle projections for Champion and Candidate models defined in `config/model_selection.json` (overridable via `--models` CLI flag) into `dashboard_data.json`.
2. **Primary Model & Comparison Selection**: Frontend controls allow setting a **Primary Model** (defaulting to Champion) and toggling optional **Compare Models**.
   - Primary Model drives pitch xP summaries, bench metrics, squad rule validation, and default MILP squad loading.
   - Secondary Compare Models append side-by-side table columns (`xP [Candidate]`, `Diff xP`).
3. **Solver Alignment**: `dashboard_data.json` records `solution_model_name` metadata. If Primary Model matches `solution_model_name`, MILP squad is loaded directly; if different, UI surfaces solver model badge and enables top-xP auto-fill for the selected Primary Model.

## Consequences

- Dashboard JSON data contract schema updated to group projection metrics per model under `player.models[model_name]`.
- User can toggle between clean single-model view and multi-model side-by-side comparison matrix.
- MILP optimization remains strictly single-model per run while enabling visual comparison against candidate model projections.
