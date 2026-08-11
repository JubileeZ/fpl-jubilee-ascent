# GW1–6 Chip Exploration Matrix (BB × FH3|TC3 × Haaland × Bruno × WC4 Opt1)

**Updated**: 2026-08-12T00:56:00+07:00  
**Data stamp**: Stage 2 dual-floor rates 2026-08-12; projections horizon 6 + availability overlays; FPL API pricing 2026-07-29  
**Season**: 2026/27 · horizon GW1–6  
**Status**: Active Research Model  
**Purpose**: Explore 16 chip/structure paths: (BB1|BB2) × WC4 Opt1 × (FH3|TC3) × (Allow|Ban Haaland in pre squad) × (Allow|Ban B.Fernandes in pre squad). Report top FH3 and top TC3 separately.  
**Scope**: 15-player MILP drafts, Free Hit / Triple Captain GW3, GW4 Wildcard Opt1, reproducible user_picks comparison, FT banking with GW5 roll enforced.  
**Related**: [Preseason Pipeline Master README](../README.md) · [Expected Role](../01-expected-role-gw1-5/expected-role-gw1-5.md) · [Expected Stats](../02-expected-stats-gw1-5/expected-stats-gw1-5.md) · [Runner](run_wc4_simulation.py)  
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
| S1 | GW1 | FH3 | allow | allow | — | 174.99 | 152.41 | **327.40** | 4 |
| S2 | GW1 | FH3 | allow | ban | — | 174.99 | 152.41 | **327.40** | 4 |
| S3 | GW1 | FH3 | ban | allow | — | 174.99 | 152.41 | **327.40** | 4 |
| S4 | GW1 | FH3 | ban | ban | — | 174.99 | 152.41 | **327.40** | 4 |
| S5 | GW1 | TC3 | allow | allow | Haaland | 183.01 | 152.41 | **335.42** | 4 |
| S6 | GW1 | TC3 | allow | ban | Haaland | 183.01 | 152.41 | **335.42** | 4 |
| S7 | GW1 | TC3 | ban | allow | Vuskovic | 178.66 | 152.41 | **331.07** | 4 |
| S8 | GW1 | TC3 | ban | ban | Vuskovic | 178.66 | 152.41 | **331.07** | 4 |
| S9 | GW2 | FH3 | allow | allow | — | 174.54 | 152.41 | **326.95** | 4 |
| S10 | GW2 | FH3 | allow | ban | — | 174.54 | 152.41 | **326.95** | 4 |
| S11 | GW2 | FH3 | ban | allow | — | 173.97 | 152.41 | **326.38** | 4 |
| S12 | GW2 | FH3 | ban | ban | — | 173.97 | 152.41 | **326.38** | 4 |
| S13 | GW2 | TC3 | allow | allow | Haaland | 182.44 | 152.41 | **334.85** | 4 |
| S14 | GW2 | TC3 | allow | ban | Haaland | 182.44 | 152.41 | **334.85** | 4 |
| S15 | GW2 | TC3 | ban | allow | Vuskovic | 178.31 | 152.41 | **330.72** | 4 |
| S16 | GW2 | TC3 | ban | ban | Vuskovic | 178.31 | 152.41 | **330.72** | 4 |

Bruno ban is non-binding. Haaland ban is non-binding on BB1 FH3 paths (S1=S3): Isak-led pre-FH optima naturally omit Haaland in GW1–2 and draft him on FH3 and WC4.

### 2. Top FH3 path (S1)

**GW1–2 Pre-FH (£99.5m, BB1)** — no Haaland  
GKP: Raya, Roefs · DEF: Gabriel, Vuskovic, Muharemović, Ballard, Maguire · MID: Palmer, Bruno G., E.Le Fée, Maeda, Mbeumo · FWD: Isak, Thiago, João Pedro

**GW3 Free Hit (£99.5m)** — Haaland in  
GKP: Donnarumma, Verbruggen · DEF: Vuskovic, Jacquet, Wieffer, O'Reilly, Hill · MID: Wirtz, Schade, Mason-Clark, Tonali, Jensen · FWD: Haaland, Isak, Thiago

**GW4–6 WC Opt1 (£99.5m)**  
GKP: Raya, Verbruggen · DEF: Gabriel, Vuskovic, Muharemović, Tarkowski, Thiaw · MID: Palmer, Sarr, Ndiaye, Crooks, Slater · FWD: Haaland, Isak, Walle Egeli · GW4–6 **152.41**

### 3. Top TC3 path (S5)

**GW1–3 Pre-WC (£100.0m, BB1 + TC Haaland)**  
GKP: Raya, Donnarumma · DEF: Vuskovic, Muharemović, Jacquet, Ballard, Maguire · MID: Sarr, Bruno G., Schade, E.Le Fée, Maeda · FWD: Haaland, Isak, Thiago · Post-WC same Opt1 as S1.

### 4. User squad comparison

| Strategy Path | GW1–3 xP | GW4–6 xP | Total 6-GW xP | Peer MILP Total | Lag vs Peer | Pre-WC Opp Loss | Banked FTs GW6 | User Spend |
|---|---|---|---|---|---|---|---|---|
| User + BB1 + FH3 + WC4 Opt1 | 152.74 | 152.41 | 305.15 | 327.40 | -22.25 | -22.25 | 4 | £100.0m |
| User + BB1 + TC3 + WC4 Opt1 | 154.13 | 152.41 | 306.54 | 335.42 | -28.88 | -28.88 | 4 | £100.0m |
| User + BB2 + FH3 + WC4 Opt1 | 152.69 | 152.41 | 305.10 | 326.95 | -21.85 | -21.85 | 4 | £100.0m |
| User + BB2 + TC3 + WC4 Opt1 | 154.08 | 152.41 | 306.49 | 334.85 | -28.36 | -28.36 | 4 | £100.0m |

---

## Decision

**Verdict**: Dual winners — **S1 FH3 327.40 xP** · **S5 TC3 335.42 xP**. Stage 2 dual-floor gives Isak top-tier prominence; FH3 allows manager to skip Haaland pre-FH and buy him on FH3 and WC4.

**Recommended Action**: Prefer S5 if deploying early Triple Captain in GW3; prefer S1 if banking TC for double gameweeks.

---

## Verification & Delivery

- Runner exports summary / simulation / user comparison CSVs under `data/research/gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/`.
