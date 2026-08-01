# GW1–5 Chip Strategy Simulation & Price Sensitivity Research Note

**Updated**: 2026-08-01T21:54:00+07:00  
**Data stamp**: Projections CSV 2026-08-01; FPL API element summary 2026-07-29; ParticipationStateHybridModel Softmax rates 2026-08-01  
**Season**: 2026/27 · horizon GW1–5  
**Status**: Active Research Simulation Model  
**Purpose**: Run multi-period solver simulations comparing GW1 Bench Boost (BB1 + WC4) vs GW2 Bench Boost (BB2 + WC4) vs Standard Wildcard (WC4 without early BB) using the updated dynamic Softmax $xP$ projections, and evaluate real-world price-rise blindspots.  
**Scope**: GW1–5 trajectory across 178 eligible starters and 20 Premier League clubs.  
**Related**: [Expected Stats GW1–5](../expected-stats-gw1-5/expected-stats-gw1-5.md) · [FPL First-Half Chip Strategy](../fpl-first-half-chip-strategy/fpl-first-half-chip-strategy.md) · [Projections CSV](../../../data/research/expected-stats-gw1-5/gw1-5_projections.csv)  
**Artifacts**:
- [Simulation Results CSV](../../../data/research/gw1-5-chip-simulation/gw1-5_chip_simulation.csv) — row-level 5-GW simulation trajectory data

---

## Sources

- **Primary Projections Input**: `data/research/expected-stats-gw1-5/gw1-5_projections.csv` (178 eligible starters with dynamic Softmax bonus points).
- **Player Pricing & Metadata**: `data/processed/players.parquet` and `data/processed/clubs.parquet`.
- **Solver Engine**: MILP multi-period squad optimization (`scipy.optimize.milp`).

---

## Agent Prompt

```text
Run 5-Gameweek chip strategy simulations for GW1-5 using gw1-5_projections.csv as input data:

1. Simulate Scenario A: BB1 + WC4 (Bench Boost GW1, Wildcard GW4).
2. Simulate Scenario B: BB2 + WC4 (Bench Boost GW2, Wildcard GW4).
3. Simulate Scenario C: Standard WC4 (No early BB, Wildcard GW4).
4. Evaluate total 5-GW projected points, weekly scores, captaincy, and bench output.
5. Analyze solver blindspots (price rises, ownership velocity, budget squeeze on WC4).
6. Export results to data/research/gw1-5-chip-simulation/gw1-5_chip_simulation.csv.
7. Verify via ruff check and pytest.
```

---

## Method

### 1. Multi-Period Optimization Logic
- **Initial Squad Selection (GW1–3)**: SOLVE 15-player squad under £100.0m cap to maximize GW1–3 $xP$ given the selected BB gameweek (GW1 or GW2).
- **Wildcard Rebuild (GW4)**: SOLVE 15-player squad under £100.0m cap optimized for GW4–5 fixture swings (targeting CHE, ARS, MCI, LIV, MUN).
- **Captaincy**: Highest $xP$ starter assigned 2x multiplier; Triple Captain (TC) applied in GW3 for Haaland vs Coventry (H).

### 2. Price Rise Sensitivity Modeling
Static solver models assume fixed player costs ($P_t = P_0$). In reality, early high-performing assets experience price inflation. We evaluate the budget squeeze risk if target WC4 assets rise in value during GW1–3.

---

## Findings

### 1. 5-Gameweek Trajectory & Point Comparison

| Strategy Scenario | GW1 $xP$ | GW2 $xP$ | GW3 $xP$ | GW4 $xP$ (WC) | GW5 $xP$ | Total 5-GW $xP$ | Net vs No BB |
|---|---|---|---|---|---|---|---|
| **Scenario A: BB1 + WC4** | **82.54** (BB1) | 62.69 | 64.72 (TC3) | 67.21 | 64.64 | **341.80** | **+19.69** |
| **Scenario B: BB2 + WC4** | 62.82 | **79.67** (BB2) | 64.84 (TC3) | 67.21 | 64.64 | **339.18** | **+17.07** |
| **Scenario C: Standard WC4** | 62.82 | 62.60 | 64.84 (TC3) | 67.21 | 64.64 | **322.11** | Baseline |

### 2. Key Strategy Takeaways
- **Early Bench Boost Value**: Executing an early Bench Boost in GW1 or GW2 yields a massive **+17.0 to +19.7 $xP$ gain** over saving the chip.
- **BB1 vs BB2**: Both BB1 (82.54 pts) and BB2 (79.67 pts) are extremely strong. BB2 provides the advantage of having 1 extra week of team news to confirm 100% starter minutes.

---

## Solver Blindspots: Price Rise & Budget Squeeze Analysis

### The Problem: Static Price Assumption
Standard solvers assume players stay at their GW1 prices through GW4. In real FPL:
1. **Target Price Inflation**: Assets like Gyökeres (£7.5m), Vušković (£5.0m), Palmer (£9.5m), and Hill (£5.5m) are heavily owned. If they deliver in GW1–3, their prices will rise by **+£0.1m to +£0.3m each**.
2. **Budget Squeeze on WC4**: By GW4, buying your ideal 15-player WC template might cost **£100.8m to £101.5m**, pricing you out if you hold £0.0m ITB!

### Actionable Mitigation Rules for WC4 Execution
1. **Maintain £0.5m–£1.0m In Bank (ITB)**: Keep £0.5m ITB in your GW1 draft to act as a buffer against target price rises on Wildcard.
2. **Track Ownership Velocity**: Identify key targets expected to rise in price during GW1–3.
3. **Early Wildcard Activation**: Activate WC4 early in the gameweek window (Sunday/Monday post-GW3) to lock in price rises on players you bring in, boosting your squad value.

---

## Decision

**Verdict**: Recommended to execute **BB1 or BB2** followed by **WC4**. Maintain **£0.5m ITB** in GW1 to absorb WC4 price inflation.

---

## Risks and Unknowns

- **Price Rise Velocity**: Actual FPL price changes depend on net transfer volume; unexpected bandwagon shifts could accelerate price changes.
- **Lineup Surprises**: Pre-season starters must be re-verified prior to the GW1 deadline.
