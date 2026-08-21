# GW1–6 Chip Strategy & Wildcard Squad Optimization (GW1 BB + WC4)

**Updated**: 2026-08-20T17:17:28+07:00
**Data stamp**: Stage 2 rates 2026-08-18; Prior-Season Dual-Vector Seed; FPL API clubs/fixtures 2026-08-19; Champion saves/defcon × defence_multiplier
**Season**: 2026/27 · horizon GW1–6  
**Status**: Archived (2026/27 preseason). Active Research Model  
**Purpose**: Execute the canonical preseason chip trajectory: **GW1 Bench Boost (BB1) + GW4 Wildcard (WC4)** with locked transfers across GW1–3, GW4 Wildcard squad overhaul, and rolled transfers in GW5 to bank 4 Free Transfers into GW6 post-international break.  
**Scope**: 15-player MILP optimal drafts, Bench Boost GW1, GW4 Wildcard Rebuild, FT banking with GW5 roll enforced (4 banked FTs into GW6).  
**Related**: [Preseason Pipeline Master README](../README.md) · [Expected Role](../01-expected-role-gw1-5/expected-role-gw1-5.md) · [Expected Stats](../02-expected-stats-gw1-5/expected-stats-gw1-5.md) · [Ownership Explorer](../../ownership-value-explorer/ownership-value-explorer.md) · [Downstream refresh](../refresh_downstream.py) · [Runner](run_wc4_simulation.py) · [Operational First-Half Plan](../../gw1-19-operational-plan/gw1-19-operational-plan.md)  
**Artifacts**:
- [Summary CSV](gw1-6_wc4_summary.csv)
- [Simulation CSV](gw1-6_wc4_simulation.csv)
- [Select-11 plan](gw1-6_select_11.csv)
- [Projections CSV](gw1-6_projections.csv)

---

## Sources

- Projections: Stage 3 `gw1-6_projections.csv` (Stage 2 ADR-0014 rates + ParticipationStateHybridModel horizon 6).
- Pricing: FPL API static pricing snapshot (`data/processed/players.parquet`, 2026-08-18).
- Chip Strategy Authority: FPL Rules 2026/27 (FT banking across Wildcard).

---

## Agent Prompt & Reproducibility Instructions

```text
GW1–6 Chip Strategy & Wildcard Simulation (Prior-Season Dual-Vector Seed):
uv run python docs/archive/gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/run_wc4_simulation.py

Writes gw1-6_wc4_summary.csv then regenerates note caches via sync_live_research_figures.py.
Identity: docs/archive/gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/gw1-6_wc4_summary.csv total_6gw_xp
```

---

## Method

1. **Pre-WC Squad (GW1–3)**: MILP on Prior-Season Dual-Vector Seed xP over GW1–3 under £100.0m budget with Bench Boost active in GW1 (all 15 players score). Locked transfers across GW1–3.
2. **Wildcard Squad (GW4–6)**: Complete 15-player squad reset in GW4 under £100.0m budget targeting favorable mid-term fixture swings.
3. **FT Banking**: 0 transfers in GW5 (roll transfer) preserves 4 banked Free Transfers into GW6 post-international break.
4. **Select 11**: each GW max-xP legal XI from that week's 15. 1 GKP + 10 outfield; DEF 3–5, MID 2–5, FWD 1–3. GW1 Bench Boost fields all 15. Captain = max xP among those who score (15 on BB, 11 otherwise). Week xP = XI (or 15) + captain extra. Flags in `gw1-6_wc4_simulation.csv`; long form in `gw1-6_select_11.csv`.

---

## Findings

### 1. Canonical Scenario Trajectory (GW1 BB + WC4)

| Gameweek | Phase / Chip | Captain | Total GW xP | Transfers | Banked FTs |
| :---: | :--- | :--- | :---: | :---: | :---: |
| **GW1** | **Pre-WC (Bench Boost Active)** | Haaland | **79.24** | 0 (Initial) | 1 |
| **GW2** | **Pre-WC (Locked Squad)** | Haaland | **61.76** | 0 (Roll) | 2 |
| **GW3** | **Pre-WC (Locked Squad)** | Haaland | **60.65** | 0 (Roll) | 3 |
| **GW1–3 Subtotal** | **Pre-Wildcard Sprint** | — | **201.65** | — | — |
| **GW4** | **Post-WC (Wildcard Active)** | Haaland | **59.69** | WC Active | 3 (Preserved) |
| **GW5** | **Post-WC (Hold Squad)** | Haaland | **59.64** | 0 (Roll) | 4 |
| **GW6** | **Post-WC (Enter Post-IB)** | Haaland | **62.78** | 0 (Roll) | **4 (Max)** |
| **GW4–6 Subtotal** | **Post-Wildcard Rebuild** | — | **182.11** | — | — |
| **Total Horizon** | **GW1–6 Preseason Strategy** | — | **383.76** | — | **4 Banked FTs** |

Saves and defcon scale with `defence_multiplier` (ADR 0005). Totals are Prior-Season Dual-Vector Seed xP (`gw1-6_wc4_summary.csv` `total_6gw_xp`). Production `_fixture_maps` still FDR fallback.

### 2. Optimal Squad Rosters

#### Phase 1: GW1 Bench Boost Squad (£100.0m Spend, £0.0m ITB)
- **Goalkeepers**: Donnarumma (MCI, £5.5m), Verbruggen (BHA, £4.5m)
- **Defenders**: Calafiori (ARS, £5.5m), Gabriel (ARS, £8.0m), Guéhi (MCI, £6.0m), Vuskovic (BHA, £5.0m), Wieffer (BHA, £5.0m)
- **Midfielders**: Maeda (IPS, £5.5m), Schade (BRE, £6.0m), Scott (BOU, £6.0m), Tavernier (BOU, £6.0m), Tzolis (ARS, £6.5m)
- **Forwards**: Calvert-Lewin (LEE, £6.0m), Haaland (MCI, £15.5m), Isak (LIV, £9.0m)

Haaland is in the pre-WC 15.

#### Phase 2: GW4 Wildcard Rebuild Squad (£98.5m Spend, £1.5m ITB)
- **Goalkeepers**: Donnarumma (MCI, £5.5m), Horníček (NEW, £4.5m)
- **Defenders**: Calafiori (ARS, £5.5m), Gabriel (ARS, £8.0m), Guéhi (MCI, £6.0m), Vuskovic (BHA, £5.0m), Wieffer (BHA, £5.0m)
- **Midfielders**: Crooks (HUL, £4.5m), Palacios (FUL, £4.5m), Palmer (CHE, £9.5m), Sarr (CRY, £6.5m), Tzolis (ARS, £6.5m)
- **Forwards**: Haaland (MCI, £15.5m), João Pedro (CHE, £7.5m), Walle Egeli (IPS, £4.5m)

### 3. Select 11 plan (GW1–6)

Legal XI from the 15 above. Week xP matches `gw1-6_wc4_summary.csv` (parts sum to 383.76).

#### GW1 Bench Boost — all 15 score — BB-15 — **79.24** — C Haaland

| Pos | XI (xP order) |
|---|---|
| GKP | Donnarumma, Verbruggen |
| DEF | Gabriel, Vuskovic, Calafiori, Wieffer, Guéhi |
| MID | Tzolis, Tavernier, Schade, Scott, Maeda |
| FWD | **Haaland (C)**, Isak, Calvert-Lewin |

No bench. Formation label `BB-15`.

#### GW2 — 5-3-2 — **61.76** — C Haaland

| Pos | XI | Bench |
|---|---|---|
| GKP | Donnarumma | Calvert-Lewin, Verbruggen, Maeda, Scott |
| DEF | Gabriel, Vuskovic, Calafiori, Wieffer, Guéhi | — |
| MID | Tzolis, Tavernier, Schade | — |
| FWD | **Haaland (C)**, Isak | — |

#### GW3 — 5-3-2 — **60.65** — C Haaland

| Pos | XI | Bench |
|---|---|---|
| GKP | Donnarumma | Calvert-Lewin, Verbruggen, Maeda, Tzolis |
| DEF | Vuskovic, Gabriel, Calafiori, Wieffer, Guéhi | — |
| MID | Tavernier, Schade, Scott | — |
| FWD | **Haaland (C)**, Isak | — |

#### GW4 Wildcard — 5-3-2 — **59.69** — C Haaland

| Pos | XI | Bench |
|---|---|---|
| GKP | Donnarumma | Walle Egeli, Horníček, Crooks, Palacios |
| DEF | Gabriel, Vuskovic, Calafiori, Wieffer, Guéhi | — |
| MID | Tzolis, Palmer, Sarr | — |
| FWD | **Haaland (C)**, João Pedro | — |

#### GW5 — 5-3-2 — **59.64** — C Haaland

| Pos | XI | Bench |
|---|---|---|
| GKP | Donnarumma | Walle Egeli, Horníček, Crooks, Palacios |
| DEF | Gabriel, Calafiori, Guéhi, Vuskovic, Wieffer | — |
| MID | Palmer, Tzolis, Sarr | — |
| FWD | **Haaland (C)**, João Pedro | — |

#### GW6 — 5-3-2 — **62.78** — C Haaland

| Pos | XI | Bench |
|---|---|---|
| GKP | Donnarumma | Walle Egeli, Horníček, Crooks, Palacios |
| DEF | Gabriel, Vuskovic, Calafiori, Wieffer, Guéhi | — |
| MID | Palmer, Tzolis, Sarr | — |
| FWD | **Haaland (C)**, João Pedro | — |

## Decision

**Verdict**: The **GW1 Bench Boost + GW4 Wildcard** strategy achieves **383.76 xP** across GW1–6 (`gw1-6_wc4_summary.csv` `total_6gw_xp`) while preserving **4 Banked Free Transfers** into GW6. Pre-WC keepers **Donnarumma + Verbruggen** are the MILP 15-man pick, not the DCS GW1–19 pair (**Raya (ARS) + Fodder (£4.0m)**). Post-WC keepers **Donnarumma + Horníček**.

## Risks and unknowns

- Locked GW1–3: no modelled hits if BB1 assets DNP.
- Triple Captain / Free Hit not in live Stage 3 CSV; do not mix frozen S13 340.14 with live `total_6gw_xp`.
- Trafford is LEE; Rushworth is COV. City GKP is Donnarumma.

### Metric Definitions & Direction

| Metric | Symbol | Definition / Formula | Direction | Ideal / Benchmark | Description |
|---|---|---|---|---|---|
| **Scenario Expected Points** | `Total xP` | Sum of GW1–6 MILP scores under Canonical Preseason Chip Path | Higher $\uparrow$ | **383.76** (`gw1-6_wc4_summary.csv`) | Only published Stage 3 row. |
| **Select-11 week xP** | XI + C | Started players' xP plus captain extra (BB = all 15) | Higher $\uparrow$ | GW1 **79.24** | `gw1-6_select_11.csv`; matches summary week totals. |
| **Bench Boost Active Score** | `BB Score` | 15-man GW1 sum including captain extra | Higher $\uparrow$ | **79.24** | Live S1 GW1. |
| **Banked Transfer Liquidity** | `Banked FTs` | Free transfers entering GW6 | Higher $\uparrow$ | **4** | GW5 roll enforced. |
