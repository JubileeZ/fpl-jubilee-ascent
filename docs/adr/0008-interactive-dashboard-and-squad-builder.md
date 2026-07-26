# 0008: Interactive Dashboard and Squad Builder

## Context

Analyzing projection details, event component breakdowns (`xG Pts`, `xA Pts`, `xCS Pts`, `xDefcon Pts`, `xBonus`), historical rates (`Pts/Start`, `Pts/90`, `ICT/90`), and manually testing custom 15-player lineup combinations requires an interactive visual interface alongside the automated MILP solver.

## Decision

Implement a standalone zero-dependency web interface in `dashboard/` (`index.html`, `styles.css`, `app.js`) backed by a Python CLI command (`commands.dashboard`).

1. `commands.dashboard` compiles a `Dashboard Data Contract` (`data/dashboard_data.json`) merging player metadata, historical rates, and multi-gameweek event component projections.
2. Serves the web interface via Python standard library `http.server` on `http://localhost:8000`.
3. Frontend provides a searchable, sortable player table, metric filters, horizon selector, and an interactive 15-player pitch/bench squad builder with drag-and-drop support, FPL rule validation (budget, club caps, formation), and MILP optimal squad import.

## Consequences

- No external web framework dependencies (Streamlit/Dash) added to python project.
- Frontend rendering is decoupled from model calculations via the clean JSON data contract.
- Allows real-time manual squad manipulation and component inspection.
- CLI command `uv run python -m commands.dashboard` serves as single entry point for UI generation and serving.
