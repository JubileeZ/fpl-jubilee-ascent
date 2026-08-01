# Expected Stats GW1–5 Research & Projection Model Directory

**Updated**: 2026-08-02T01:00:00+07:00  
**Status**: Active Research Model (Non-Full-Season Candidate)  
**Scope**: XI Contention Event Rates + Draft Shortlist GW1–5 $xP$ via production hybrid scorer.

---

## Structure
```
docs/research/expected-stats-gw1-5/
├── README.md
├── expected-stats-gw1-5.md
├── build_expected_stats.py      # Code-mapped usable-season rates + external gap fill
└── project_expected_points.py   # ParticipationStateHybridModel.predict + strength mults

data/research/expected-stats-gw1-5/
├── expected-stats-gw1-5.csv     # XI Contention per-90 rates
└── gw1-5_projections.csv        # Nailed+Regular GW1–5 xP
```

---

## Reproduction

```bash
uv run python docs/research/expected-stats-gw1-5/build_expected_stats.py
uv run python docs/research/expected-stats-gw1-5/project_expected_points.py
uv run ruff check docs/research/expected-stats-gw1-5/
```

Grill lock: Permanent Player Code Mapping; Usable Season ≥450 mins; recency 50/50; external only if no usable FPL year; Defcon = CBIT/CBITR, FPL Defcon, or best-guess when partial data (baseline only if no evidence); scoring via `ParticipationStateHybridModel.predict` with attack/defence strength multipliers; Softmax over XI Contention Set.
