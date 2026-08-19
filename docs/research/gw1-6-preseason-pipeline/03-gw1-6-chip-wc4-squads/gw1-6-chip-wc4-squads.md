# GW1–6 Chip Strategy & Wildcard Squad Optimization (GW1 BB + WC4)

**Updated**: 2026-08-19T18:15:00+07:00  
**Data stamp**: Stage 2 rates 2026-08-18; public FPL bootstrap/fixtures 2026-08-19 (592 players); Champion scales saves/defcon by defence_multiplier  
**Season**: 2026/27 · horizon GW1–6  
**Status**: Active Research Model  
**Purpose**: Execute the canonical preseason chip trajectory: **GW1 Bench Boost (BB1) + GW4 Wildcard (WC4)** with locked transfers across GW1–3, GW4 Wildcard squad overhaul, and rolled transfers in GW5 to bank 4 Free Transfers into GW6 post-international break.  
**Scope**: 15-player MILP optimal drafts, Bench Boost GW1, GW4 Wildcard Rebuild, FT banking with GW5 roll enforced (4 banked FTs into GW6).  
**Related**: [Preseason Pipeline Master README](../README.md) · [Expected Role](../01-expected-role-gw1-5/expected-role-gw1-5.md) · [Expected Stats](../02-expected-stats-gw1-5/expected-stats-gw1-5.md) · [Ownership Explorer](../../ownership-value-explorer/ownership-value-explorer.md) · [Downstream refresh](../refresh_downstream.py) · [Runner](run_wc4_simulation.py)  
**Artifacts**:
- [Summary CSV](../../../../data/research/gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/gw1-6_wc4_summary.csv)
- [Simulation CSV](../../../../data/research/gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/gw1-6_wc4_simulation.csv)
- [Select-11 plan](../../../../data/research/gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/gw1-6_select_11.csv)
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
- data/research/gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/gw1-6_select_11.csv
- data/research/gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/gw1-6_projections.csv

Delivery: uv run ruff check . && uv run pytest && bash tests/verify.sh
```

---

## Method

1. **Pre-WC Squad (GW1–3)**: MILP optimization over GW1–3 under £100.0m budget with Bench Boost active in GW1 (all 15 players score). Locked transfers across GW1–3.
2. **Wildcard Squad (GW4–6)**: Complete 15-player squad reset in GW4 under £100.0m budget targeting favorable mid-term fixture swings.
3. **FT Banking**: 0 transfers in GW5 (roll transfer) preserves 4 banked Free Transfers into GW6 post-international break.
4. **Select 11**: each GW max-xP legal XI from that week's 15. 1 GKP + 10 outfield; DEF 3–5, MID 2–5, FWD 1–3. GW1 Bench Boost fields all 15. Captain = max xP among those who score (15 on BB, 11 otherwise). Week xP = XI (or 15) + captain extra. Flags in `gw1-6_wc4_simulation.csv`; long form in `gw1-6_select_11.csv`.

---

## Findings

### 1. Canonical Scenario Trajectory (GW1 BB + WC4)

| Gameweek | Phase / Chip | Captain | Total GW xP | Transfers | Banked FTs |
| :---: | :--- | :--- | :---: | :---: | :---: |
| **GW1** | **Pre-WC (Bench Boost Active)** | B.Fernandes | **73.67** | 0 (Initial) | 1 |
| **GW2** | **Pre-WC (Locked Squad)** | B.Fernandes | **53.64** | 0 (Roll) | 2 |
| **GW3** | **Pre-WC (Locked Squad)** | Isak | **59.22** | 0 (Roll) | 3 |
| **GW1–3 Subtotal** | **Pre-Wildcard Sprint** | — | **186.53** | — | — |
| **GW4** | **Post-WC (Wildcard Active)** | Isak | **58.56** | WC Active | 3 (Preserved) |
| **GW5** | **Post-WC (Hold Squad)** | Haaland | **57.14** | 0 (Roll) | 4 |
| **GW6** | **Post-WC (Enter Post-IB)** | Gabriel | **54.38** | 0 (Roll) | **4 (Max)** |
| **GW4–6 Subtotal** | **Post-Wildcard Rebuild** | — | **170.08** | — | — |
| **Total Horizon** | **GW1–6 Preseason Strategy** | — | **356.61** | — | **4 Banked FTs** |

Saves and defcon now scale with `defence_multiplier` (ADR 0005). Totals are FDR-xP (API attack/defence = 0).

### 2. Optimal Squad Rosters

#### Phase 1: GW1 Bench Boost Squad (£99.5m Spend, £0.5m ITB)
- **Goalkeepers**: Donnarumma (MCI, £5.5m), Sels (NFO, £5.0m)
- **Defenders**: Gabriel (ARS, £8.0m), Guéhi (MCI, £6.0m), Calafiori (ARS, £5.5m), Vuskovic (BHA, £5.0m), Wieffer (BHA, £5.0m)
- **Midfielders**: B.Fernandes (MUN, £12.0m), Tzolis (ARS, £6.5m), O.Dango (BRE, £6.5m), Schade (BRE, £6.0m), Maeda (IPS, £5.5m)
- **Forwards**: Isak (LIV, £9.0m), Thiago (BRE, £8.0m), Calvert-Lewin (LEE, £6.0m)

Haaland is **not** in the pre-WC 15.

#### Phase 2: GW4 Wildcard Rebuild Squad (£100.0m Spend, £0.0m ITB)
- **Goalkeepers**: Donnarumma (MCI, £5.5m), Scherpen (IPS, £4.5m)
- **Defenders**: Gabriel (ARS, £8.0m), Calafiori (ARS, £5.5m), Hill (BOU, £5.5m), Vuskovic (BHA, £5.0m), Wieffer (BHA, £5.0m)
- **Midfielders**: Palmer (CHE, £9.5m), Tzolis (ARS, £6.5m), Sarr (CRY, £6.5m), Gomez (BHA, £5.0m), Slater (HUL, £4.5m)
- **Forwards**: Haaland (MCI, £15.5m), Isak (LIV, £9.0m), Walle Egeli (IPS, £4.5m)

### 3. Select 11 plan (GW1–6)

Legal XI from the 15 above. Week xP matches `gw1-6_wc4_summary.csv` (parts sum to 356.61).

#### GW1 Bench Boost — all 15 score — 5-5-3 + 2 GKP — **73.67** — C B.Fernandes

| Pos | XI (xP order) |
|---|---|
| GKP | Donnarumma, Sels |
| DEF | Gabriel, Vuskovic, Calafiori, Wieffer, Guéhi |
| MID | **B.Fernandes (C)**, Tzolis, Maeda, Schade, O.Dango |
| FWD | Isak, Thiago, Calvert-Lewin |

No bench. Formation label `BB-15`.

#### GW2 — 5-3-2 — **53.64** — C B.Fernandes

| Pos | XI | Bench |
|---|---|---|
| GKP | Donnarumma | Sels |
| DEF | Gabriel, Vuskovic, Guéhi, Calafiori, Wieffer | — |
| MID | **B.Fernandes (C)**, Schade, O.Dango | Tzolis, Maeda |
| FWD | Isak, Thiago | Calvert-Lewin |

#### GW3 — 5-3-2 — **59.22** — C Isak

| Pos | XI | Bench |
|---|---|---|
| GKP | Donnarumma | Sels |
| DEF | Vuskovic, Gabriel, Wieffer, Guéhi, Calafiori | — |
| MID | Schade, B.Fernandes, O.Dango | Tzolis, Maeda |
| FWD | **Isak (C)**, Thiago | Calvert-Lewin |

#### GW4 Wildcard — 5-3-2 — **58.56** — C Isak

| Pos | XI | Bench |
|---|---|---|
| GKP | Donnarumma | Scherpen |
| DEF | Vuskovic, Gabriel, Wieffer, Calafiori, Hill | — |
| MID | Palmer, Sarr, Tzolis | Gomez, Slater |
| FWD | **Isak (C)**, Haaland | Walle Egeli |

#### GW5 — 5-3-2 — **57.14** — C Haaland

| Pos | XI | Bench |
|---|---|---|
| GKP | Donnarumma | Scherpen |
| DEF | Gabriel, Vuskovic, Calafiori, Hill, Wieffer | — |
| MID | Palmer, Tzolis, Sarr | Gomez, Slater |
| FWD | **Haaland (C)**, Isak | Walle Egeli |

#### GW6 — 5-3-2 — **54.38** — C Gabriel

| Pos | XI | Bench |
|---|---|---|
| GKP | Donnarumma | Scherpen |
| DEF | **Gabriel (C)**, Vuskovic, Calafiori, Wieffer, Hill | — |
| MID | Tzolis, Palmer, Sarr | Gomez, Slater |
| FWD | Haaland, Isak | Walle Egeli |

---

## Decision

**Verdict**: The **GW1 Bench Boost + GW4 Wildcard** strategy achieves **356.61 xP** across GW1–6 while preserving **4 Banked Free Transfers** into GW6. Wildcard brings Haaland in for GW4–6 (captain GW5). Pre-WC keepers **Donnarumma + Sels** are the MILP 15-man pick, not the DCS GW1–19 pair (**Rushworth + Donnarumma**).

## Risks and unknowns

- Locked GW1–3: no modelled hits if BB1 assets DNP.
- Triple Captain / Free Hit not in live Stage 3 CSV; do not mix frozen S13 340.14 with 356.61.
- Trafford is LEE; Rushworth is COV. City GKP is Donnarumma.

### Metric Definitions & Direction

| Metric | Symbol | Definition / Formula | Direction | Ideal / Benchmark | Description |
|---|---|---|---|---|---|
| **Scenario Expected Points** | `Total xP` | Sum of GW1–6 MILP scores under Canonical Preseason Chip Path | Higher $\uparrow$ | **356.61** (S1) | Only published Stage 3 row. |
| **Select-11 week xP** | XI + C | Started players' xP plus captain extra (BB = all 15) | Higher $\uparrow$ | GW1 **73.67** | `gw1-6_select_11.csv`; matches summary week totals. |
| **Bench Boost Active Score** | `BB Score` | 15-man GW1 sum including captain extra | Higher $\uparrow$ | **73.67** | Live S1 GW1. |
| **Banked Transfer Liquidity** | `Banked FTs` | Free transfers entering GW6 | Higher $\uparrow$ | **4** | GW5 roll enforced. |
