# Active Task: ADR 0069 SeasonLifecycle, 2026-27 SeasonRules, and Randdalf/fplcache GW1-38 Ingestion

- **Status:** In Progress
- **Objective:** Implement ADR 0069 SeasonLifecycle config/guards, verify 2026-27 SeasonRules and <gw fit isolation, and build quarantined Randdalf/fplcache GW1-38 ingestion + settled outcome reconciliation.
- **Acceptance:** Green unit/regression tests across all 3 seams, `uv run ruff check .`, `uv run pytest`, `bash tests/verify.sh`, two-axis code review, tracked manifest/docs updated, and issue #185 resolved on GitHub.
- **Issue/Ticket:** https://github.com/JubileeZ/fpl-jubilee-ascent/issues/185

## Work Packet (SFDBN)

- **Status:** In Progress (All 3 seams verified; awaiting Checkpoint commit)
- **Files:** config/season_lifecycle.json, backtesting/season_rules.py, backtesting/data_admission.py, backtesting/confirmation_registry.py, backtesting/live_capture.py, backtesting/input_evidence.py, backtesting/forecast_inputs.py, backtesting/forecast_store.py, backtesting/promotion_evidence.py, backtesting/input_pilot.py, backtesting/walkforward.py, projections/explorer_slice.py, .agents/skills/ideate-candidate/generate_prompt.py, .agents/skills/ideate-candidate/SKILL.md, docs/rules/scoring-rules-2026-27.md, docs/rules/README.md, backtesting/fplcache_ingest.py, commands/ingest_fplcache.py, config/fplcache_2026_27_manifest.json, docs/agents/current-state.md, ROADMAP.md
- **Decisions:** Three user-confirmed deep seams: (1) glossary-aligned `SeasonLifecycle` policy (`active_validation`/`development`/`historical_filter`/`prior_seed_only`/`sealed`) in `backtesting/season_rules.py`, (2) `native-2026-27-v1` `SeasonRules` (`two_chip_sets`, `afcon_gw15_topup`), (3) `ingest_season_fplcache` with `FplCachePort` composing `input_evidence` + `admission_fixtures` + in-window transfer settlement reconciliation.
- **Blocked:** None
- **Next:** Commit changes at user Checkpoint (delete this packet upon commit).

## Todo
- [x] Step 1: SeasonLifecycle config, policy guards, and tests (Seam 1)
- [x] Step 2: 2026-27 SeasonRules, docs, and `< gw` fit isolation (Seam 2)
- [x] Step 3: Randdalf/fplcache GW1-38 ingestion, outcome reconciliation, and manifest (Seam 3)
- [x] Step 4: Full ruff, pytest, verify.sh, and two-axis review + fixes
- [ ] Step 5: User Checkpoint commit (delete work packet on commit)

## Blockers / Notes
- None
