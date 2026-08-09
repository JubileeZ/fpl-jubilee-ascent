# Active Task: Refresh GW1–6 Preseason Pipeline & Research Suite

- **Status:** Complete
- **Objective:** Refresh `docs/research/gw1-6-preseason-pipeline/` (Stage 1 role audit, Stage 2 event rates & projections, Stage 3 WC4 3x2 matrix MILP) with 8–9 August transfers and price-bracket research
- **Acceptance:** `refresh_expected_role.py` updated with 8 Aug moves; Stage 1/2/3 CSV companions and markdown docs refreshed; master runner `run_pipeline.py` verified; delivery gates green
- **Issue/Ticket:** Pre-season pipeline maintenance

## Work Packet (SFDBN)

- **Status:** Complete
- **Files:** docs/research/gw1-6-preseason-pipeline/*, docs/research/INDEX.md, docs/agents/current-state.md, task.md
- **Decisions:** Integrated Bruno Guimarães (NEW->ARS £75m Nailed) and Danny Welbeck (BHA->CHE £5m Rotation); regenerated Stage 1 (340 rows), Stage 2 (194 draft shortlist projections), and Stage 3 (3x2 matrix solved: S1 319.81 xP, S2 315.01 xP, S3 314.52 xP, S4 319.15 xP, S5 314.35 xP, S6 313.86 xP); synchronized markdown docs and timestamps
- **Blocked:** None
- **Next:** Proceed with GW1 squad finalization and operational runs

## Todo
- [x] Audit latest 8–9 August transfers against `gw1-6-preseason-pipeline`
- [x] Update `refresh_expected_role.py` with Bruno Guimarães and Danny Welbeck moves
- [x] Execute `run_pipeline.py` to regenerate Stages 1, 2, and 3 CSVs
- [x] Update markdown documentation in Stages 1, 2, 3 and master README
- [x] Sync `docs/research/INDEX.md` and `docs/agents/current-state.md`
- [x] Verify delivery gates (ruff, pytest, verify.sh)
- [x] Clean up `.tmp/agent/` scratch files

## Blockers / Notes
- None
