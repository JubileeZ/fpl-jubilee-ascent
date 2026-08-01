# Research Index & Guidelines

**Updated**: 2026-08-01T15:48:00+07:00  
**Status**: Active research directory authority  

---

## Active Research Index

- **FPL 2026/27 Pre-Season Source Directory**:
  - [Pre-Season Source Directory](fpl-preseason-guide.md)
  - [Budget Goalkeepers](fpl-budget-goalkeepers.md)
  - [£5.0m+ Goalkeepers](fpl-5-0m-goalkeepers.md)
  - [£5.0m Defenders](fpl-5-0m-defenders.md)
  - [£4.5m Defenders](fpl-4-5m-defenders.md)
  - [£4.0m Defenders](fpl-4-0m-defenders.md)
  - [£4.5m Midfielders](fpl-4-5m-midfielders.md)
  - [£6.0m–£6.5m Forwards](fpl-6-0m-6-5m-forwards.md)
  - [Confirmed Summer Transfers](fpl-summer-transfers.md)

- **Role & Chip Strategy Models**:
  - [Expected Role GW1–5](expected-role-gw1-5.md) · [CSV Companion](../../data/research/expected-role-gw1-5.csv)
  - [FPL First-Half Chip Strategy](fpl-first-half-chip-strategy.md)

---

## Research Conventions & Standards

- **Durable Documentation**: Keep project-relevant research notes in `docs/research/<topic-slug>.md`.
- **Filename Convention**: Use stable topic slugs (`fpl-budget-goalkeepers.md`); no date prefixes. Copy `docs/research/template/research-note.md` to start a new note.
- **Required Sections**: Every research note MUST include: `Updated`, `Data stamp`, `Season`, `Purpose`, `Sources`, `Agent Prompt`, `Method`, `Findings`, `Decision`, and `Risks and unknowns`.
- **Data Timestamps**:
  - `Updated` = ISO 8601 timestamp with timezone of last note revision.
  - `Data stamp` = freshness or evidence cutoff of underlying source data.
  - Do not add duplicate `Last update` fields.
- **Machine-Readable Companions**: Store row-level data under `data/research/<topic-slug>.*`; link companion in note header under `Artifact`.
- **Evidence Separation**: Keep `Source synthesis` strictly separate from `Project interpretation`. Label unvalidated source claims.
- **Reproducible Agent Prompt**: Identify inputs, refresh/recheck steps, stable output path, and scratch cleanup in `Agent Prompt`.
