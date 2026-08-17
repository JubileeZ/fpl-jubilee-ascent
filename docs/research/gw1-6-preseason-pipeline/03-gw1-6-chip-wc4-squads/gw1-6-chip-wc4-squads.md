# GW1–6 Chip Strategy & Wildcard Squad Optimization (GW1 BB + WC4)

**Updated**: 2026-08-18T02:45:00+07:00  
**Data stamp**: FPL API refresh 2026-08-18 (590 players); Stage 1 575 rows (name-match fix); Stage 2 ADR-0014 rates; Trafford LEE / Rushworth COV; GW1 deadline 2026-08-21T17:30:00Z  
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
- Pricing: FPL API static pricing snapshot (`data/processed/players.parquet`, 2026-08-18).
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
| **GW1** | **Pre-WC (Bench Boost Active)** | 54.12 | 15.79 | Gabriel (5.91 xP) | **75.82** | 0 (Initial) | 1 |
| **GW2** | **Pre-WC (Locked Squad)** | — | — | B.Fernandes | **53.84** | 0 (Roll) | 2 |
| **GW3** | **Pre-WC (Locked Squad)** | — | — | Vuskovic | **61.18** | 0 (Roll) | 3 |
| **GW1–3 Subtotal** | **Pre-Wildcard Sprint** | — | — | — | **190.84** | — | — |
| **GW4** | **Post-WC (Wildcard Active)** | — | — | Vuskovic | **59.43** | WC Active | 3 (Preserved) |
| **GW5** | **Post-WC (Hold Squad)** | — | — | Haaland | **57.14** | 0 (Roll) | 4 |
| **GW6** | **Post-WC (Enter Post-IB)** | — | — | Gabriel | **56.80** | 0 (Roll) | **4 (Max)** |
| **GW4–6 Subtotal** | **Post-Wildcard Rebuild** | — | — | — | **173.37** | — | — |
| **Total Horizon** | **GW1–6 Preseason Strategy** | — | — | — | **364.21** | — | **4 Banked FTs** |

Captain extra on GW1 is included in Total GW xP (15-man sum 69.91 + Gabriel C 5.91 = 75.82).

### 2. Optimal Squad Rosters

#### Phase 1: GW1 Bench Boost Squad (£100.0m Spend, £0.0m ITB)
- **Goalkeepers**: Raya (ARS, £6.0m), Donnarumma (MCI, £5.5m)
- **Defenders**: Gabriel (ARS, £8.0m), Guéhi (MCI, £6.0m), Vuskovic (BHA, £5.0m), Wieffer (BHA, £5.0m), Ballard (SUN, £5.0m)
- **Midfielders**: B.Fernandes (MUN, £12.0m), Tzolis (ARS, £6.5m), O.Dango (BRE, £6.5m), Schade (BRE, £6.0m), Maeda (IPS, £5.5m)
- **Forwards**: Isak (LIV, £9.0m), Thiago (BRE, £8.0m), Calvert-Lewin (LEE, £6.0m)

Haaland is **not** in the pre-WC 15. Trafford is no longer a City option (LEE after 2026-08-18 API refresh).

#### Phase 2: GW4 Wildcard Rebuild Squad (£100.0m Spend, £0.0m ITB)
- **Goalkeepers**: Raya (ARS, £6.0m), Rushworth (COV, £4.5m)
- **Defenders**: Gabriel (ARS, £8.0m), Tarkowski (EVE, £6.0m), Vuskovic (BHA, £5.0m), Wieffer (BHA, £5.0m), Thiaw (NEW, £5.0m)
- **Midfielders**: Palmer (CHE, £9.5m), Tzolis (ARS, £6.5m), Sarr (CRY, £6.5m), Crooks (HUL, £4.5m), Slater (HUL, £4.5m)
- **Forwards**: Haaland (MCI, £15.5m), Isak (LIV, £9.0m), Walle Egeli (IPS, £4.5m)

---

## Decision

**Verdict**: The **GW1 Bench Boost + GW4 Wildcard** strategy achieves **364.21 xP** across GW1–6 while preserving **4 Banked Free Transfers** into GW6. Wildcard brings Haaland in for GW4–6 (captain GW5, home vs Coventry is GW3 — he is not owned until WC4).
