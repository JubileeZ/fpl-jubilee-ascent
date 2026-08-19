# Session Handoff (SFDBN)

- **Status:** Ownership Explorer shipped as dashboard view. Spec drift fixed: click-only labels, sortable rank table, Position/Club/Price filter table+charts (xMins floor chart-only), squad controls hidden on explorer tab.
- **Files:** `dashboard/explorer.js`, `dashboard/index.html`, `dashboard/app.js`, `projections/explorer_slice.py`, `commands/export_dashboard.py`, `AGENTS.md`
- **Decisions:** Production Champion + FDR fallback. Dual-Vector research-only. Default First-Half Horizon, All Projection, Projected Rate.
- **Blocked:** None
- **Next:** `uv run python -m commands.dashboard` to compile GW1–38 and open Ownership Explorer.
