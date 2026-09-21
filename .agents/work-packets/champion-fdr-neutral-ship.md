# Active Task: Ship Champion rename + FDR neutral fallback

- **Status:** Committing rename cleanup
- **Objective:** Land ADR 0037–0039 path; no retired Dual-Vector product name
- **Acceptance:** Unknown Primary → Champion; `catalog_models` in export; Process Points missing cols safe; suite green
- **Issue/Ticket:** ADR 0037 · 0038 · 0039

## Work Packet (SFDBN)

- **Status:** Ready to commit
- **Files:** `models/__init__.py`, `commands/dashboard.py`, `commands/export_dashboard.py`, `dashboard/app.js`, `backtesting/process_points.py`, tests, docs
- **Decisions:** No retired-name aliases; stale Primary → Champion; UI filters via `catalog_models`
- **Blocked:** None
- **Next:** Soft-reload dashboard after pull

## Todo
- [x] FDR fallback + ADR 0037–0039 (prior commit)
- [x] Drop alias; unknown Primary → Champion; catalog_models
- [x] Process Points missing-column fillna fix
- [x] Full pytest green
- [ ] Soft-reload dashboard UI (user)
