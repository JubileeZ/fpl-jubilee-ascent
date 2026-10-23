# Active Task: live-season-pin-gw7-refresh

- **Status:** In Progress
- **Objective:** Update Official 2026-27 Season Pin with latest Gameweek 7 content hash, player statistics, and price history snapshots.
- **Acceptance:**
  - `data/archive/2026-27/official_content_hash`, `players.parquet`, `price_history.parquet`, and `raw/bootstrap_static.json` updated.
  - `uv run ruff check .`, `uv run pytest`, and `bash tests/verify.sh` pass.
- **Issue/Ticket:** N/A

## Work Packet (SFDBN)

- **Status:** In Progress
- **Files:** `data/archive/2026-27/official_content_hash`, `data/archive/2026-27/processed/players.parquet`, `data/archive/2026-27/processed/price_history.parquet`, `data/archive/2026-27/raw/bootstrap_static.json`
- **Decisions:** Commit and push official live season archive content hash update per user authorization.
- **Blocked:** None
- **Next:** Push to `origin/main`.

## Todo
- [x] Verify data refresh and squad state accuracy
- [x] Run `uv run ruff check .`
- [x] Run `bash tests/verify.sh`
- [ ] Run `uv run pytest` and verify all tests pass
- [ ] Stage changes and commit
- [ ] Push to `origin/main`

## Blockers / Notes
- None
