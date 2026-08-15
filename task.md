# Task Work Packet

## Work Packet (SFDBN)

- **Status:** Complete / Verified
- **Files:** `data/archive/solio/solio_gw1.parquet`, `data/solio_raw.json`, `data/solio_projections.csv`, `data/event_rate_hybrid.csv`, `data/expert_template_hybrid.csv`, `.cursor/rules/read-agents-md.md`, `solver/.cache/http_cache.json`, `data/reports/promotion_evidence/`, `tmp/`, `task.md`
- **Decisions:** Removed deprecated Solio archive and data files (ADR 0009), removed obsolete experimental model projection CSVs, deleted redundant `.cursor/rules/read-agents-md.md`, removed 160 historical promotion test run logs, purged solver HTTP cache, and removed empty root `tmp/` folder.
- **Blocked:** None.
- **Next:** Propose commit or await user instruction.
- **Objective:** Audit all folders, identify obsolete/transient files, and perform confirmed cleanup.
- **Acceptance:**
  - [x] Comprehensive folder-by-folder audit completed
  - [x] Obsolete & deprecated files removed (Solio artifacts, old model CSVs, duplicate rule)
  - [x] Transient test/solver run artifacts purged (`promotion_evidence/`, `solver/.cache/`)
  - [x] All 170 unit tests, ruff linting, and gate verification passing

