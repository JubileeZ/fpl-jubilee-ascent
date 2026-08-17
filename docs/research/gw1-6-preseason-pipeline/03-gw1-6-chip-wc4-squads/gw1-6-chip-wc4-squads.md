# GW1–6 Chip Strategy & Wildcard Squad Optimization (GW1 BB + WC4)

**Updated**: 2026-08-17T23:00:00+07:00  
**Data stamp**: Stage 2 ADR-0014 rates 2026-08-17 (564 players); projections horizon 6 + availability overlays; FPL API pricing 2026-07-29; Preseason friendlies & Community Shield complete  
**Season**: 2026/27 · horizon GW1–6  
**Status**: Active Research Model  
**Purpose**: Execute the canonical preseason chip trajectory: **GW1 Bench Boost (BB1) + GW4 Wildcard (WC4)** with locked transfers across GW1–3, GW4 Wildcard squad overhaul, and rolled transfers in GW5 to bank 4 Free Transfers into GW6 post-international break.  
**Scope**: 15-player MILP optimal drafts, Bench Boost GW1, GW4 Wildcard Rebuild, FT banking with GW5 roll enforced (4 banked FTs into GW6).  
**Related**: [Preseason Pipeline Master README](../README.md) · [Expected Role](../01-expected-role-gw1-5/expected-role-gw1-5.md) · [Expected Stats](../02-expected-stats-gw1-5/expected-stats-gw1-5.md) · [Ownership Explorer](../../ownership-value-explorer/ownership-value-explorer.md) · [Downstream refresh](../refresh_downstream.py) · [Runner](run_wc4_simulation.py)  
**Artifacts**:
- [Summary CSV](../../../../data/research/gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/gw1-6_wc4_summary.csv)
- [Simulation CSV](../../../../data/research/gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/gw1-6_wc4_simulation.csv)
- [Projections CSV](../../../../data/research/gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/gw1-6_projections.csv)

---

## Sources

- Projections: Stage 3 `gw1-6_projections.csv` (Stage 2 ADR-0014 rates + ParticipationStateHybridModel horizon 6).
- Pricing: FPL API static pricing snapshot (`data/processed/players.parquet`).
- Chip Strategy Authority: FPL Rules 2026/27 (FT banking across Wildcard).

---

## Agent Prompt & Reproducibility Instructions

```text
GW1–6 Chip Strategy & Wildcard Simulation:
uv run python docs/research/gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/run_wc4_simulation.py

Outputs:
- data/research/gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/gw1-6_wc4_summary.csv
- data/research/gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/gw1-6_wc4_simulation.csv
- data/research/gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/gw1-6_projections.csv

Delivery: uv run ruff check . && uv run pytest && bash tests/verify.sh
```

---

## Method

1. **Pre-WC Squad (GW1–3)**: MILP optimization over GW1–3 under £100.0m budget with Bench Boost active in GW1 (all 15 players score). Locked transfers across GW1–3.
2. **Wildcard Squad (GW4–6)**: Complete 15-player squad reset in GW4 under £100.0m budget targeting favorable mid-term fixture swings.
3. **FT Banking**: 0 transfers in GW5 (roll transfer) preserves 4 banked Free Transfers into GW6 post-international break.

---

## Findings

### 1. Canonical Scenario Trajectory (GW1 BB + WC4)

| Gameweek | Phase / Chip | Starting XI xP | Bench xP | Captain | Total GW xP | Transfers | Banked FTs |
| :---: | :--- | :---: | :---: | :--- | :---: | :---: | :---: |
| **GW1** | **Pre-WC (Bench Boost Active)** | 52.50 | 16.97 | Gabriel (5.87 xP) | **75.34** | 0 (Initial) | 1 |
| **GW2** | **Pre-WC (Locked Squad)** | 47.97 | — | Ballard (4.92 xP) | **52.89** | 0 (Roll) | 2 |
| **GW3** | **Pre-WC (Locked Squad)** | 55.56 | — | Haaland (6.31 xP) | **61.87** | 0 (Roll) | 3 |
| **GW1–3 Subtotal** | **Pre-Wildcard Sprint** | **156.03** | **16.97** | — | **190.10** | — | — |
| **GW4** | **Post-WC (Wildcard Active)** | 52.94 | — | Vuskovic (6.15 xP) | **59.09** | WC Active | 3 (Preserved) |
| **GW5** | **Post-WC (Hold Squad)** | 50.76 | — | Haaland (6.28 xP) | **57.04** | 0 (Roll) | 4 |
| **GW6** | **Post-WC (Enter Post-IB)** | 50.42 | — | Gabriel (5.83 xP) | **56.25** | 0 (Roll) | **4 (Max)** |
| **GW4–6 Subtotal** | **Post-Wildcard Rebuild** | **154.12** | — | — | **172.38** | — | — |
| **Total Horizon** | **GW1–6 Preseason Strategy** | **310.15** | **16.97** | — | **362.48** | — | **4 Banked FTs** |

---

### 2. Optimal Squad Rosters

#### Phase 1: GW1 Bench Boost Squad (£100.0m Spend, £0.0m ITB)
- **Goalkeepers**: Trafford (MCI, £5.0m), Sels (NFO, £5.0m)
- **Defenders**: Gabriel (ARS, £8.0m), Vuskovic (BHA, £5.0m), Wieffer (BHA, £5.0m), Ballard (SUN, £5.0m), Maguire (MUN, £5.0m)
- **Midfielders**: Tzolis (ARS, £6.5m), O.Dango (BRE, £6.5m), Schade (BRE, £6.0m), Maeda (IPS, £5.5m), Núñez (IPS, £5.0m)
- **Forwards**: Haaland (MCI, £15.5m), Isak (LIV, £9.0m), Thiago (BRE, £8.0m)

#### Phase 2: GW4 Wildcard Rebuild Squad (£99.0m Spend, £1.0m ITB)
- **Goalkeepers**: Trafford (MCI, £5.0m), Roefs (SUN, £5.0m)
- **Defenders**: Gabriel (ARS, £8.0m), Tarkowski (EVE, £6.0m), Calafiori (ARS, £5.5m), Vuskovic (BHA, £5.0m), Wieffer (BHA, £5.0m)
- **Midfielders**: Enzo (CHE, £7.0m), Tzolis (ARS, £6.5m), Sarr (CRY, £6.5m), Johnson (CRY, £6.0m), Andrews (COV, £4.5m)
- **Forwards**: Haaland (MCI, £15.5m), Isak (LIV, £9.0m), Walle Egeli (IPS, £4.5m)

---

## Decision

**Verdict**: The **GW1 Bench Boost + GW4 Wildcard** strategy achieves **362.48 xP** across GW1–6 while preserving **4 Banked Free Transfers** into GW6 post-international break.
