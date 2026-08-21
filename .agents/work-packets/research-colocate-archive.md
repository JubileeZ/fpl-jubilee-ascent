# Active Task: research-colocate-archive

- **Status:** Checkpointed
- **Objective:** Colocate research companions with topic notes; archive 2026/27 preseason research; encode layout in AGENTS.md + test so companions never land under `data/`.
- **Acceptance:** `data/research/` absent. `data/archive/` children match `YYYY-YY` only. Preseason topics under `docs/archive/<topic>/` with CSVs beside notes. `docs/research/` = INDEX + template. Layout test + ruff + `bash tests/verify.sh`.
- **Issue/Ticket:**

## Work Packet (SFDBN)

- **Status:** Checkpointed
- **Files:** `docs/research/INDEX.md`; `docs/archive/`; `AGENTS.md`; `features/expected_role_prior.py`; `commands/refresh_data.py`; `commands/export_dashboard.py`; `tests/test_research_layout.py`; `.cursor/rules/research-layout.mdc`; `.gitignore`
- **Decisions:** Companions live in the topic folder (`docs/research/<slug>/` live, `docs/archive/<slug>/` archived). `data/archive/` = season ingest only. Production Expected Role Prior reads archived Stage 1 CSV. Dated diary `current-state-research-log.md` keeps historical `data/research/` paths.
- **Blocked:** none
- **Next:** Packet may be deleted on a follow-up commit (first land needed the file staged).
