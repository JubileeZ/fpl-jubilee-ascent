# Expected Stats GW1–5 Research & Projection Model Directory

**Updated**: 2026-08-01T20:48:00+07:00  
**Status**: Active Research Model (Non-Full-Season Candidate)  
**Scope**: GW1–5 expected stats rates and expected points ($xP$) projection for Nailed & Regular Starters.

---

## Directory & Repository Architecture

Research models created for specific gameweek horizons, pre-season experiments, or temporary draft evaluations (which are not intended as canonical full-season model candidates in `models/`) reside in dedicated subdirectories under `docs/research/<topic-slug>/` for code & notes, and `data/research/<topic-slug>/` for data artifacts.

### Structure
```
docs/research/expected-stats-gw1-5/
├── README.md                    # Architecture & reproduction guide (this file)
├── expected-stats-gw1-5.md      # Durable research note & decision audit
├── build_expected_stats.py      # Reproducible script: computes per-90 rates (50/50 blend + external/fallback)
└── project_expected_points.py  # Reproducible script: projects GW1–5 xP via ParticipationStateHybridModel logic

data/research/expected-stats-gw1-5/
├── expected-stats-gw1-5.csv      # Canonical per-90 rates CSV
└── gw1-5_projections.csv        # Output table: per-GW and 5-GW aggregate xP projections
```

### Companions
- **Machine-Readable Research Rates**: `data/research/expected-stats-gw1-5/expected-stats-gw1-5.csv`
- **Output Projections Table**: `data/research/expected-stats-gw1-5/gw1-5_projections.csv`
- **Source Role Priors**: `data/research/expected-role-gw1-5/expected-role-gw1-5.csv` and `docs/research/expected-role-gw1-5/expected-role-gw1-5.md`

---

## Reproduction Guide

To reproduce or update the expected stats and GW1–5 projections when underlying data or FPL rosters change:

1. **Re-build Per-90 Rates CSV**:
   ```bash
   uv run python docs/research/expected-stats-gw1-5/build_expected_stats.py
   ```
   Outputs: `data/research/expected-stats-gw1-5/expected-stats-gw1-5.csv`

2. **Re-run GW1–5 Points Projection**:
   ```bash
   uv run python docs/research/expected-stats-gw1-5/project_expected_points.py
   ```
   Outputs: `data/research/expected-stats-gw1-5/gw1-5_projections.csv`

3. **Validation & Verification Gate**:
   ```bash
   uv run ruff check .
   uv run pytest
   bash tests/verify.sh
   ```
