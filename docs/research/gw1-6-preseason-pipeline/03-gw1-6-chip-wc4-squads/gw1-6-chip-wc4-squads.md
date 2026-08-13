# GW1–6 Chip Exploration Matrix (BB × FH3|TC3 × Haaland × Bruno × WC4 Opt1)

**Updated**: 2026-08-13T03:35:00+07:00  
**Data stamp**: Stage 2 dual-floor rates 2026-08-13; projections horizon 6 + availability overlays; FPL API pricing 2026-07-29  
**Season**: 2026/27 · horizon GW1–6  
**Status**: Active Research Model  
**Purpose**: Explore 16 chip/structure paths: (BB1|BB2) × WC4 Opt1 × (FH3|TC3) × (Allow|Ban Haaland in pre squad) × (Allow|Ban B.Fernandes in pre squad). Report top FH3 and top TC3 separately.  
**Scope**: 15-player MILP drafts, Free Hit / Triple Captain GW3, GW4 Wildcard Opt1, reproducible user_picks comparison, FT banking with GW5 roll enforced.  
**Related**: [Preseason Pipeline Master README](../README.md) · [Expected Role](../01-expected-role-gw1-5/expected-role-gw1-5.md) · [Expected Stats](../02-expected-stats-gw1-5/expected-stats-gw1-5.md) · [Ownership Explorer](../../ownership-value-explorer/ownership-value-explorer.md) · [Runner](run_wc4_simulation.py)  
**Artifacts**:
- [Summary CSV](../../../data/research/gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/gw1-6_wc4_summary.csv)
- [Simulation CSV](../../../data/research/gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/gw1-6_wc4_simulation.csv)
- [User comparison CSV](../../../data/research/gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/gw1-6_user_squad_comparison.csv)
- [Projections CSV](../../../data/research/gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/gw1-6_projections.csv)

---

## Sources

- Projections: Stage 3 `gw1-6_projections.csv` (Stage 2 dual-floor rates; `availability_priors.py`).
- Pricing: `data/processed/players.parquet`, `clubs.parquet`.
- User squad: `data/processed/user_picks.parquet` (0 xP stubs if outside XI Contention).

---

## Agent Prompt & Reproducibility Instructions

```text
Run parameterized GW1-6 Chip Exploration Matrix & Wildcard Optimization (Stage 3):

1. Command: uv run python docs/research/gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/run_wc4_simulation.py
   - Generates 6-GW projections (gw1-6_projections.csv) via ParticipationStateHybridModel.
   - Solves 16-scenario exploration matrix via SciPy MILP:
     * BB Timing: GW1 vs GW2 Bench Boost
     * Mid Chip: GW3 Free Hit (FH3) vs GW3 Triple Captain (TC3)
     * Structural Bans: Allow vs Ban Haaland in GW1-3 pre-chip squad; Allow vs Ban Bruno Fernandes
     * Wildcard: GW4 Wildcard Option 1 (maximize GW4-6 XI xP <= £100.0m)
   - Enforces transfer rules: rolls GW2/GW3/GW5, banks 4 Free Transfers into GW6 post-international break.
   - Compares with current user_picks.parquet.
   - Exports summary, simulation, and user comparison CSVs.
2. Update Findings and summary tables in gw1-6-chip-wc4-squads.md.
3. Verification: uv run pytest, uv run ruff check .
```

---

## Method

1. **Pre-chip draft**: MILP ≤£100.0m, min 1 LIV; optional Haaland / B.Fernandes bans.
2. **WC4 Opt1**: Maximize GW4–6 XI xP ≤£100.0m; ≤3/club.
3. **FT banking**: rolls GW2/GW3/GW5; `gw5_transfers=0`; `banked_fts_gw6` computed (4).
4. **User comparison**: `user_picks` vs allow/allow peer.

---

## Findings

### 1. Summary table (all 16) — post Stage 2 dual-floor rebuild

| ID | BB | Mid | Ban H | Ban Bruno | TC | GW1–3 | GW4–6 | Total | FTs |
| :--- | :---: | :---: | :---: | :---: | :---: | ---: | ---: | ---: | :---: |
| S1 | GW1 | FH3 | allow | allow | — | 176.16 | 152.06 | **328.22** | 4 |
| S2 | GW1 | FH3 | allow | ban | — | 174.53 | 152.06 | 326.59 | 4 |
| S3 | GW1 | FH3 | ban | allow | — | 176.16 | 152.06 | **328.22** | 4 |
| S4 | GW1 | FH3 | ban | ban | — | 174.53 | 152.06 | 326.59 | 4 |
| S5 | GW1 | TC3 | allow | allow | Haaland | 182.95 | 152.06 | **335.01** | 4 |
| S6 | GW1 | TC3 | allow | ban | Haaland | 182.77 | 152.06 | 334.83 | 4 |
| S7 | GW1 | TC3 | ban | allow | Vuskovic | 180.52 | 152.06 | 332.58 | 4 |
| S8 | GW1 | TC3 | ban | ban | Vuskovic | 178.28 | 152.06 | 330.34 | 4 |
| S9 | GW2 | FH3 | allow | allow | — | 175.88 | 152.06 | 327.94 | 4 |
| S10 | GW2 | FH3 | allow | ban | — | 173.75 | 152.06 | 325.81 | 4 |
| S11 | GW2 | FH3 | ban | allow | — | 175.88 | 152.06 | 327.94 | 4 |
| S12 | GW2 | FH3 | ban | ban | — | 173.25 | 152.06 | 325.31 | 4 |
| S13 | GW2 | TC3 | allow | allow | Haaland | 182.45 | 152.06 | 334.51 | 4 |
| S14 | GW2 | TC3 | allow | ban | Haaland | 182.22 | 152.06 | 334.28 | 4 |
| S15 | GW2 | TC3 | ban | allow | Vuskovic | 180.82 | 152.06 | 332.88 | 4 |
| S16 | GW2 | TC3 | ban | ban | Vuskovic | 177.97 | 152.06 | 330.03 | 4 |

Bruno ban is binding (~1.6 xP on FH3 paths): solver now drafts **B.Fernandes (MUN)** not Bruno G. Haaland ban remains non-binding on BB1 FH3 paths (S1=S3).

### 2. Top FH3 path (S1)

**GW1–2 Pre-FH (£100.0m, BB1)** — no Haaland  
GKP: Lammens, Roefs · DEF: Gabriel, Muharemović, Jacquet, Ballard, Maguire · MID: B.Fernandes, Palmer, Sarr, E.Le Fée, Maeda · FWD: Isak, João Pedro, Calvert-Lewin

**GW3 Free Hit (£97.0m)** — Haaland in  
GKP: Donnarumma, Petrović · DEF: Vuskovic, Jacquet, Wieffer, O'Reilly, Virgil · MID: O.Dango, Schade, Dominguez, Crooks, Slater · FWD: Haaland, Isak, Thiago

**GW4–6 WC Opt1 (£99.5m)**  
GKP: Raya, Petrović · DEF: Gabriel, Vuskovic, Muharemović, Tarkowski, Thiaw · MID: Palmer, Sarr, Ndiaye, Crooks, Slater · FWD: Haaland, Isak, Walle Egeli · GW4–6 **152.06**

### 3. Top TC3 path (S5)

**GW1–3 Pre-WC (£100.0m, BB1 + TC Haaland)**  
GKP: Donnarumma, Scherpen · DEF: Vuskovic, Muharemović, Jacquet, Ballard, Maguire · MID: B.Fernandes, O.Dango, Schade, E.Le Fée, Maeda · FWD: Haaland, Isak, Walle Egeli · Post-WC same Opt1 as S1.

### 4. User squad comparison

| Strategy Path | GW1–3 xP | GW4–6 xP | Total 6-GW xP | Peer MILP Total | Lag vs Peer | Pre-WC Opp Loss | Banked FTs GW6 | User Spend |
|---|---|---|---|---|---|---|---|---|
| User + BB1 + FH3 + WC4 Opt1 | 161.09 | 152.06 | 313.15 | 328.22 | -15.07 | -15.07 | 4 | £100.0m |
| User + BB1 + TC3 + WC4 Opt1 | 163.99 | 152.06 | 316.05 | 335.01 | -18.96 | -18.96 | 4 | £100.0m |
| User + BB2 + FH3 + WC4 Opt1 | 160.10 | 152.06 | 312.16 | 327.94 | -15.78 | -15.78 | 4 | £100.0m |
| User + BB2 + TC3 + WC4 Opt1 | 163.00 | 152.06 | 315.06 | 334.51 | -19.45 | -19.45 | 4 | £100.0m |

---

## Decision

**Verdict**: Dual winners — **S1 FH3 328.22 xP** · **S5 TC3 335.01 xP**. B.Fernandes is in both pre-chip XIs; Bruno G. (ARS Rotation) is not.

**Recommended Action**: Prefer S5 if deploying early Triple Captain in GW3; prefer S1 if banking TC for double gameweeks.

---

## Verification & Delivery

- Runner exports summary / simulation / user comparison CSVs under `data/research/gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/`.
