# Task: FFS pre-season guide recheck & transfer register refresh

**Objective:** Recheck Fantasy Football Scout pre-season guide children for source updates; refresh stale notes.

**Acceptance:**
- [x] Playwright recheck all 10 price-bracket child source URLs
- [x] Refresh `fpl-summer-transfers.md` through 4 August (9 new moves + Bamba backfill)
- [x] Update `fpl-preseason-guide.md` index (guide modified 2026-08-04; Scout Picks link noted out-of-scope)
- [x] Bump `docs/research/INDEX.md` timestamp
- [x] Pre-commit gates green

## Work Packet (SFDBN)

- **Status:** Complete. Ten price-bracket children unchanged; transfers + guide index refreshed. Ready to checkpoint.
- **Files:** `docs/research/fpl-preseason-guide/fpl-summer-transfers.md`; `fpl-preseason-guide.md`; `docs/research/INDEX.md`; `task.md`; `docs/agents/current-state.md`; `.agents/session-handoff.md`
- **Decisions:** GW1 Scout Picks preview (2026-08-04) out of core scope — no dedicated child note. 10 new/backfilled transfer entries pending `expected-role-gw1-5` cross-check.
- **Blocked:** None.
- **Next:** Cross-check Aug transfers against `expected-role-gw1-5`; delete `task.md` when closed.

