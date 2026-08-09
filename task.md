# Active Task: Ingest Opta Analyst × Solio Set-Piece Stats & Projections Research

- **Status:** Complete
- **Objective:** Ingest Opta Analyst 2026/27 set-piece research into `docs/research/fpl-set-piece-analysis/` with machine-readable companion CSVs, updated research index, and formalized domain terminology in `CONTEXT.md`.
- **Acceptance:** Research note created with all standard sections; 3 companion CSVs generated; `CONTEXT.md` updated with 4 domain terms; `docs/research/INDEX.md` and `docs/agents/current-state.md` updated; delivery gates green.
- **Issue/Ticket:** Set-piece research ingestion

## Work Packet (SFDBN)

- **Status:** Complete
- **Files:** docs/research/fpl-set-piece-analysis/fpl-set-piece-analysis.md, data/research/fpl-set-piece-analysis/*, docs/research/INDEX.md, CONTEXT.md, docs/agents/current-state.md, task.md
- **Decisions:** Adopted dedicated topic folder `docs/research/fpl-set-piece-analysis/`; created 3 companion CSVs (`corner_takers_2026_27.csv`, `team_set_piece_swing_2025_26.csv`, `player_set_piece_leaders_2025_26.csv`); defined 4 domain glossary terms (`Set-Piece Hierarchy`, `Inswinging Corner Preference`, `Set-Play Target xG`, `Set-Piece Net Swing`).
- **Blocked:** None
- **Next:** Proceed with GW1 squad finalization and operational runs

## Todo
- [x] Extract and audit primary source content from Opta Analyst × Solio
- [x] Formulate and resolve Frontier Round 1 questions via `/grill-with-docs`
- [x] Create companion CSV datasets in `data/research/fpl-set-piece-analysis/`
- [x] Author `docs/research/fpl-set-piece-analysis/fpl-set-piece-analysis.md`
- [x] Update `docs/research/INDEX.md`
- [x] Add domain definitions to `CONTEXT.md`
- [x] Update `docs/agents/current-state.md`
- [x] Run verification checks (ruff, pytest, verify.sh)
- [x] Clean up temporary scratch files

## Blockers / Notes
- None

