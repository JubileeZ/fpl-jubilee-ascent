# Research Index & Guidelines

**Updated**: 2026-08-04T23:40:00+07:00  
**Status**: Active research directory authority  

---

## Active Research Index

- **FPL 2026/27 Pre-Season Source Directory**:
  - [Pre-Season Source Directory](fpl-preseason-guide/fpl-preseason-guide.md)
  - [Budget Goalkeepers](fpl-preseason-guide/fpl-budget-goalkeepers.md)
  - [£5.0m+ Goalkeepers](fpl-preseason-guide/fpl-5-0m-goalkeepers.md)
  - [£5.0m Defenders](fpl-preseason-guide/fpl-5-0m-defenders.md)
  - [£4.5m Defenders](fpl-preseason-guide/fpl-4-5m-defenders.md)
  - [£4.0m Defenders](fpl-preseason-guide/fpl-4-0m-defenders.md)
  - [£5.5m+ Defenders](fpl-preseason-guide/fpl-5-5m-defenders.md)
  - [£4.5m Midfielders](fpl-preseason-guide/fpl-4-5m-midfielders.md)
  - [£7.5m+ Midfielders](fpl-preseason-guide/fpl-7-5m-midfielders.md)
  - [£6.0m–£6.5m Forwards](fpl-preseason-guide/fpl-6-0m-6-5m-forwards.md)
  - [Confirmed Summer Transfers](fpl-preseason-guide/fpl-summer-transfers.md)

- **Role & Chip Strategy Models**:
  - [Expected Role GW1–5](expected-role-gw1-5/expected-role-gw1-5.md) · [CSV Companion](../../data/research/expected-role-gw1-5/expected-role-gw1-5.csv)
  - [Expected Stats & GW1–5 Projections](expected-stats-gw1-5/expected-stats-gw1-5.md) · [CSV Companion](../../data/research/expected-stats-gw1-5/expected-stats-gw1-5.csv) · [GW1–5 Projections](../../data/research/expected-stats-gw1-5/gw1-5_projections.csv)
  - [FPL First-Half Chip Strategy](fpl-first-half-chip-strategy/fpl-first-half-chip-strategy.md)
  - [GW1–5 Chip Strategy Simulation & Price Sensitivity](gw1-5-chip-simulation/gw1-5-chip-simulation.md) · [CSV Companion](../../data/research/gw1-5-chip-simulation/gw1-5_chip_simulation.csv)
  - [GW1–6 Chip & GW4 Wildcard Squad Optimization](gw1-6-chip-wc4-squads/gw1-6-chip-wc4-squads.md) · [CSV Companion](../../data/research/gw1-6-chip-wc4-squads/gw1-6_wc4_simulation.csv) · [GW1–6 Projections](../../data/research/gw1-6-chip-wc4-squads/gw1-6_projections.csv)
  - [Starter Goalkeeper Fixture Rotation & FDR Correlation](gkp-fixture-rotation/gkp-fixture-rotation.md) · [CSV Companion](../../data/research/gkp-fixture-rotation/gkp_rotation_matrix.csv) · [Baseline Rates](../../data/research/gkp-fixture-rotation/gkp_performance_baseline.csv)

---

## Research Conventions & Standards

- **Mandatory Subfolders**: All research documentation and data files MUST be organized in topic subfolders under `docs/research/<topic-slug>/` and `data/research/<topic-slug>/`. No loose standalone files are permitted directly in the root of `docs/research/` (except `INDEX.md`) or `data/research/`.
- **Non-Full-Season Model Subfolders**: Research models created for specific gameweek horizons or temporary draft evaluations (which are not canonical full-season model candidates in `models/`) are stored in `docs/research/<topic-slug>/` containing `<topic-slug>.md`, `README.md`, `build_*.py`, and `project_*.py`, with output CSVs stored in `data/research/<topic-slug>/`.
- **Filename Convention**: Use stable topic slugs (`fpl-budget-goalkeepers.md`); no date prefixes. Copy `docs/research/template/research-note.md` to start a new note.
- **Required Sections**: Every research note MUST include: `Updated`, `Data stamp`, `Season`, `Purpose`, `Sources`, `Agent Prompt`, `Method`, `Findings`, `Decision`, and `Risks and unknowns`.
- **Data Timestamps**:
  - `Updated` = ISO 8601 timestamp with timezone of last note revision.
  - `Data stamp` = freshness or evidence cutoff of underlying source data.
  - Do not add duplicate `Last update` fields.
- **Machine-Readable Companions**: Store row-level data under `data/research/<topic-slug>/<file>.csv`; link companion in note header under `Artifact`.
- **Evidence Separation**: Keep `Source synthesis` strictly separate from `Project interpretation`. Label unvalidated source claims.
- **Reproducible Agent Prompt**: Identify inputs, refresh/recheck steps, stable output path, and scratch cleanup in `Agent Prompt`.
