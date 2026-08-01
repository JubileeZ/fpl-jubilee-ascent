# GW1–5 Chip Strategy Simulation & Price Sensitivity Research Note

**Updated**: 2026-08-01T23:50:00+07:00  
**Data stamp**: Projections CSV 2026-08-01; FPL API element summary 2026-07-29; ParticipationStateHybridModel Softmax rates 2026-08-01  
**Season**: 2026/27 · horizon GW1–5  
**Status**: Active Research Simulation Model  
**Purpose**: Run multi-period solver simulations comparing GW1 Bench Boost (BB1 + WC4) vs GW2 Bench Boost (BB2 + WC4) vs Standard Wildcard (WC4 without early BB) using Softmax $xP$ projections; enforce £0.5m ITB on GW1–3 drafts.  
**Scope**: GW1–5 trajectory across 178 eligible starters and 20 Premier League clubs. No Triple Captain in this sim.  
**Related**: [Expected Stats GW1–5](../expected-stats-gw1-5/expected-stats-gw1-5.md) · [FPL First-Half Chip Strategy](../fpl-first-half-chip-strategy/fpl-first-half-chip-strategy.md) · [Projections CSV](../../../data/research/expected-stats-gw1-5/gw1-5_projections.csv)  
**Artifacts**:
- [Simulation Results CSV](../../../data/research/gw1-5-chip-simulation/gw1-5_chip_simulation.csv) — row-level 5-GW simulation trajectory data
- [Runner](run_simulation.py) — XI-aware MILP + formation-safe evaluation

---

## Sources

- **Primary Projections Input**: `data/research/expected-stats-gw1-5/gw1-5_projections.csv` (178 eligible starters with dynamic Softmax bonus points).
- **Player Pricing & Metadata**: `data/processed/players.parquet` and `data/processed/clubs.parquet`.
- **Solver Engine**: Custom `scipy.optimize.milp` research sim (not vendored open-fpl-solver). Select + start binaries; formation-safe XI eval.

---

## Agent Prompt

```text
Run 5-Gameweek chip strategy simulations for GW1-5 using gw1-5_projections.csv:

1. Scenario A: BB1 + WC4 (Bench Boost GW1, Wildcard GW4).
2. Scenario B: BB2 + WC4 (Bench Boost GW2, Wildcard GW4).
3. Scenario C: Standard WC4 (No early BB, Wildcard GW4).
4. XI-aware objective: non-BB weeks score start XI only; BB week scores all 15.
5. GW1–3 budget ≤ £99.5m (£0.5m ITB); captain = top XI xP (2×); no TC.
6. Export data/research/gw1-5-chip-simulation/gw1-5_chip_simulation.csv.
7. Run self_check in run_simulation.py; ruff check runner.
```

---

## Method

### 1. Multi-Period Optimization Logic
- **Initial Squad (GW1–3)**: MILP select ($x$) + start ($y$) under £99.5m. Objective weights GW1–3 $xP$; BB gameweek counts all 15 ($x$), other weeks count XI only ($y`). Valid XI: 1 GKP, DEF 3–5, MID 2–5, FWD 1–3.
- **Wildcard Rebuild (GW4)**: Same XI-aware MILP under £100.0m for GW4–5 (ITB buffer already held GW1–3).
- **Evaluation**: Formation-safe XI picker excludes 2nd GKP from fill slots. Captain = top XI $xP$ (2×). No forced players; no Triple Captain.
- **Locked path**: No FT/hits GW1–3; squad swaps only at WC4. Static prices (no rise model in MILP).

### 2. Price Rise Sensitivity
Static costs ($P_t = P_0$). £0.5m ITB enforced on GW1–3 drafts as buffer against WC4 target inflation. Rise magnitudes remain qualitative (ownership velocity not simulated).

---

## Findings

### 1. 5-Gameweek Trajectory & Point Comparison

| Strategy Scenario | GW1 $xP$ | GW2 $xP$ | GW3 $xP$ | GW4 $xP$ (WC) | GW5 $xP$ | Total 5-GW $xP$ | Net vs No BB | ITB |
|---|---|---|---|---|---|---|---|---|
| **Scenario A: BB1 + WC4** | **84.24** (BB1) | 62.38 | 63.91 | 67.16 | 63.92 | **341.61** | **+20.99** | £0.5m |
| **Scenario B: BB2 + WC4** | 62.82 | **80.77** (BB2) | 63.80 | 67.16 | 63.92 | **338.47** | **+17.85** | £0.5m |
| **Scenario C: Standard WC4** | 64.81 | 61.83 | 62.90 | 67.16 | 63.92 | **320.62** | Baseline | £0.5m |

### 2. Key Strategy Takeaways
- **Early BB still wins**: Planning BB1/BB2 and packing a strong bench beats XI-only Standard by **+17.9 to +21.0 $xP$** over five GWs (same WC4 path; auto-captain).
- **BB1 vs BB2**: BB1 total slightly ahead on these projections. BB2 still buys one extra week of team news (not modeled).
- **Captain**: Auto top-XI (typically Gyökeres/Palmer/Isak by GW). TC out of scope here — see first-half chip strategy note separately.
- **Standard builds cheaper bench**: Without BB in objective, bench is weaker than BB-optimized squads — fairer chip comparison than all-15 stacked baseline.
- **Within-squad BB delta** (same BB1 squad, BB on vs off GW1) remains ~**+18.6 $xP$** when bench is intentionally strong.

### 3. Solver Blindspots
- No price-rise dynamics; ITB is a fixed buffer only.
- No FT path GW1–3; WC4 identical across scenarios.
- Captaincy in objective omitted (applied at eval only).
- Research milp ≠ production open-fpl-solver.

### Actionable Mitigation Rules for WC4 Execution
1. **Keep £0.5m ITB** in GW1 draft (enforced in sim).
2. **Track ownership velocity** on WC4 targets.
3. **Activate WC early** in GW4 window to lock rises on inbound players.

---

## Decision

**Verdict**: Prefer **BB1 or BB2** then **WC4**. Hold **£0.5m ITB** through GW1–3. TC timing left to separate chip-strategy note — not part of this sim.

---

## Risks and Unknowns

- **Price Rise Velocity**: Net transfers can move targets faster than £0.5m buffer.
- **Lineup Surprises**: Pre-season starters must re-verify before GW1 deadline.
- **BB magnitude**: Early-BB edge assumes willing to fund playable bench; weak-bench drafts shrink the gap toward Standard.
