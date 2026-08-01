# GW1–5 Chip Simulation Directory

**Updated**: 2026-08-02T01:10:00+07:00  
**Status**: Active Research Simulation (not production solver)  
**Scope**: BB1/BB2/WC4 path comparison on GW1–5 projections; XI-aware MILP; £0.5m ITB; no TC.

---

## Structure

```
docs/research/gw1-5-chip-simulation/
├── README.md
├── gw1-5-chip-simulation.md
└── run_simulation.py

data/research/gw1-5-chip-simulation/
└── gw1-5_chip_simulation.csv
```

---

## Reproduction

```bash
# Refresh projections first (expected-stats grill-lock)
uv run python docs/research/expected-stats-gw1-5/build_expected_stats.py
uv run python docs/research/expected-stats-gw1-5/project_expected_points.py

# Then sim (updates CSV + note Findings manually)
uv run python docs/research/gw1-5-chip-simulation/run_simulation.py
uv run ruff check docs/research/gw1-5-chip-simulation/
```

**Input**: `data/research/expected-stats-gw1-5/gw1-5_projections.csv`  
**Related**: [Expected Stats GW1–5](../expected-stats-gw1-5/expected-stats-gw1-5.md) · [First-Half Chip Strategy](../fpl-first-half-chip-strategy/fpl-first-half-chip-strategy.md)
