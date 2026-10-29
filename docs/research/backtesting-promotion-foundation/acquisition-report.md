# Historical admission acquisition

**Updated**: 2026-10-29T20:00:00+07:00  
**Data stamp**: acquisition_manifest.csv (5 retrieved rows)  
**Season**: Multi-season  
**Status**: Active  
**Purpose**: Document historical admission source acquisition and raw file quarantine status for 2023-24, 2024-25, and 2025-26.  
**Scope**: Evaluates raw file manifests and tree inspections only; quarantined from forecast inputs.  
**Artifact**: [acquisition_manifest.csv](acquisition_manifest.csv)  

## Sources

- **Primary**: [Randdalf/fplcache](https://github.com/Randdalf/fplcache) — commits adb4450b, 75750671, 0bb12a87
- **Repository data**: `docs/research/backtesting-promotion-foundation/ownership_snapshot_provenance.csv`

## Method

Scope: 2023-24, 2024-25 and 2025-26. Opening cap 10 MiB; pilot cap 2 MiB. Manifest is current attempt status; append-only `data/reports/replay-admission/v1/retrieval-attempts.jsonl` retains attempt history. Earlier successes reconstructed from manifest; initial sandbox failures lack individual timestamps. A start without completion indicates an interrupted or killed attempt.

## Findings

### Opening latest status: 3/3 retrieved.
- 2023-24 gw01 opening_bootstrap: retrieved_unadmitted; bytes 87680; mixed bootstrap payload; planned opening deadlines only; no per-origin observation or fixture schedule
- 2024-25 gw01 opening_bootstrap: retrieved_unadmitted; bytes 84632; mixed bootstrap payload; planned opening deadlines only; no per-origin observation or fixture schedule
- 2025-26 gw01 opening_bootstrap: retrieved_unadmitted; bytes 106252; mixed bootstrap payload; planned opening deadlines only; no per-origin observation or fixture schedule

### Pilot latest status: 2/2 retrieved.
- 2025-26 gw02 origin_bootstrap_pilot: retrieved_unadmitted; bytes 104780; observed is_next events: [{"id": 2, "deadline_time": "2025-08-22T17:30:00Z"}]
- 2025-26 gw02 fixture_pilot: retrieved_unadmitted; bytes 56644; CSV header: code,event,finished,finished_provisional,id,kickoff_time,minutes,provisional_start_time,started,team_a,team_a_score,team_h,team_h_score,stats,team_h_difficulty,team_a_difficulty,pulse_id; fixture timing/announcement provenance unverified

### Coverage summary
All 114 complete-origin labels remain pending. Opening deadlines are planned deadlines; a pilot bootstrap may record its own next deadline. Git times corroborate chronology, not exact capture or independent publication. Fixture source lineage, schedule completeness and announcement timing unverified. Raw files contain mixed facts and possible outcomes; quarantine, no forecast input. No freshness, eligibility, admission, numerical accuracy or replay feasibility established. No model, solver or outcome comparison.

### Manual tree inspection
Calendar-year paths, not verified origin coverage:
- 2023-2024: 2065 paths, commit adb4450b10e20c9d6b8c709535b70e4ff461ea36; manual metadata inspection; not retained or hashed
- 2024-2025: 2065 paths, commit 75750671281e334174be59217c9dd4a5fef88c9d; manual metadata inspection; not retained or hashed
- 2025-2026: 2054 paths, commit 0bb12a87e5a5c2d35a208800203cd3e7fadbea39; manual metadata inspection; not retained or hashed

## Decision

Quarantine all retrieved raw files. No forecast input until causal admission and provenance verification are complete. Counts and rows derive from `acquisition_manifest.csv` columns `kind`, `status`, `season`, `origin`, `bytes`, `detail`; tree counts derive from `acquisition_tree_inspection.csv` columns `calendar_years`, `path_count`, `tree_commit`, `inspection_method`.

## Risks and unknowns

- Git commit timestamps corroborate publication chronology only; exact API capture timing unverified.
- Fixture announcement timing and schedule completeness unverified.
