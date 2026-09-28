# Active Task: Prune prior-season element summaries

- **Status:** Done
- **Objective:** Stop prior-season `element_summary_*.json` leaking into live `player_performances` / 2026-27 pin.
- **Acceptance:** `prune_stale_element_summaries` tests pass; refresh + pin call it; both raw dirs 667 summaries; pytest green.
- **Issue/Ticket:** follow-up to `4a7caec`

## Work Packet (SFDBN)

- **Status:** Done; delete packet next Checkpoint.
- **Files:** `features/season_archive.py`, `commands/refresh_data.py`, `tests/test_snapshot_season.py`, `tests/test_refresh_data.py`, `data/archive/2026-27/raw`, `official_content_hash`
- **Decisions:** prune by bootstrap ids (no-op without elements); pin prunes own raw, refresh prunes `data/raw`.
- **Blocked:** None
- **Next:** Delete this packet.
