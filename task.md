# Active Task: GW1–6 Preseason Pipeline Review & Reproducibility Synchronization

- **Status:** Complete
- **Objective:** Review docs/research/gw1-6-preseason-pipeline for season/year integrity, content accuracy, and zero fallback-baseline invariant; add external research packages for newly scraped starters; synchronize all reports, findings, and reproducibility instructions.
- **Acceptance:** Zero Draft Regulars on fallback_baseline; all 3 sub-stage documents and master README synchronized with live 2026/27 scrape data; 20-club markdown tables matching CSV 1:1; 152 unit tests passing; verify.sh green.
- **Issue/Ticket:** GW1–6 Preseason Pipeline `/grill-with-docs` Review

## Work Packet (SFDBN)

- **Status:** Complete
- **Files:** docs/research/gw1-6-preseason-pipeline/**, data/research/gw1-6-preseason-pipeline/**, task.md
- **Decisions:** 
  1. Season 2026/27 verified with 2023-26 multi-season archive window.
  2. Added external research packages for 5 newly injected Draft Regular starters (Touré, Meunier, Walle Egeli, Steur, Moore) in `build_expected_stats.py`, strictly preserving the Zero Draft on `fallback_baseline` invariant.
  3. Re-generated 20-club player markdown tables across all 357 contention rows in `01-expected-role-gw1-5.md`.
  4. Synchronized all xP figures and findings (S1 = 327.40 xP, S5 = 335.42 xP) across `02-expected-stats-gw1-5.md`, `03-gw1-6-chip-wc4-squads.md`, and `README.md`.
  5. Added explicit reproducibility prompts and instructions across all 3 stage research notes and the master README runner.
- **Blocked:** None
- **Next:** Pre-deadline live squad refresh and final solver run.

## Todo
- [x] Season/year validity audit across all pipeline documents and sources
- [x] Identify roster drift and fallback baseline invariant violation for newly injected starters
- [x] Grill Round 1 lock on resolution options (Option A across all frontiers)
- [x] Add external research packages for IDs 461, 541, 321, 462, 523 in `build_expected_stats.py`
- [x] Execute end-to-end master pipeline runner (`run_pipeline.py`)
- [x] Verify zero Draft players on `fallback_baseline`
- [x] Re-generate 20-club player roster markdown tables in `01-expected-role-gw1-5.md`
- [x] Update Stage 2 research note with exact top 12 xP rankings and rate source distributions
- [x] Update Stage 3 research note with exact 16-scenario summary and lineup compositions
- [x] Update Master `README.md` with synced findings and end-to-end reproducibility prompt
- [x] Run delivery gates (`ruff check`, `pytest`, `verify.sh`)

## Blockers / Notes
- None
