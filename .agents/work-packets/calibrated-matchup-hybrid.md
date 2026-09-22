# Active Task: Calibrated Matchup Share & Champion Rename

- **Status:** In Progress
- **Objective:** Implement Calibrated Matchup Share fixture scaling and adopt calibrated_matchup_hybrid as Champion
- **Acceptance:** Process MAE <= neutral; easy fixture bias dampened; champion renamed cleanly without aliases; 392 tests passing; verify gate green
- **Issue/Ticket:** ADR 0040, ADR 0041

## Work Packet (SFDBN)

- **Status:** Implemented and verified; committing Checkpoint
- **Files:** features/matchup_share.py, features/builder.py, models/calibrated_matchup_hybrid.py, config/model_selection.json, docs, tests
- **Decisions:** s=0.40 additive delta shrinkage; beta=4.0 Bayesian positional priors; decoupled saves/defcon; model-only penalty threat isolation; rename champion to calibrated_matchup_hybrid with zero aliases per ADR 0041
- **Blocked:** None
- **Next:** Push to remote

## Todo
- [x] Implement calibrated matchup share in features/matchup_share.py
- [x] Run 2025-26 calibration sweep and verify Process MAE beats neutral
- [x] Create models/calibrated_matchup_hybrid.py and remove retired model
- [x] Update config/model_selection.json and docs/model_name.md
- [x] Update CONTEXT.md, README.md, current-state.md, and ADRs 0040/0041
- [x] Update all active test suites and assertions
- [ ] Push commit to origin/main
