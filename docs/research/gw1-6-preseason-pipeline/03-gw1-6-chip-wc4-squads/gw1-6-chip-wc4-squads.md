# GW1–6 Chip Exploration Matrix (BB × FH3|TC3 × Haaland × Bruno × WC4 Opt1)

**Updated**: 2026-08-14T01:30:00+07:00  
**Data stamp**: Stage 2 ADR-0014 rates 2026-08-14; projections horizon 6 + availability overlays; FPL API pricing 2026-07-29  
**Season**: 2026/27 · horizon GW1–6  
**Status**: Active Research Model  
**Purpose**: Explore 16 chip/structure paths: (BB1|BB2) × WC4 Opt1 × (FH3|TC3) × (Allow|Ban Haaland in pre squad) × (Allow|Ban B.Fernandes in pre squad). Report top FH3 and top TC3 separately.  
**Scope**: 15-player MILP drafts, Free Hit / Triple Captain GW3, GW4 Wildcard Opt1, reproducible user_picks comparison, FT banking with GW5 roll enforced.  
**Related**: [Preseason Pipeline Master README](../README.md) · [Expected Role](../01-expected-role-gw1-5/expected-role-gw1-5.md) · [Expected Stats](../02-expected-stats-gw1-5/expected-stats-gw1-5.md) · [Ownership Explorer](../../ownership-value-explorer/ownership-value-explorer.md) · [Downstream refresh](../refresh_downstream.py) · [Runner](run_wc4_simulation.py)  
**Artifacts**:
- [Summary CSV](../../../data/research/gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/gw1-6_wc4_summary.csv)
- [Simulation CSV](../../../data/research/gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/gw1-6_wc4_simulation.csv)
- [User comparison CSV](../../../data/research/gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/gw1-6_user_squad_comparison.csv)
- [Projections CSV](../../../data/research/gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/gw1-6_projections.csv)

---

## Sources

- Projections: Stage 3 `gw1-6_projections.csv` (Stage 2 ADR-0014 rates; `availability_priors.py`).
- Pricing: `data/processed/players.parquet`, `clubs.parquet`.
- User squad: `data/processed/user_picks.parquet` (0 xP stubs if outside XI Contention).

---

## Agent Prompt & Reproducibility Instructions

```text
Run parameterized GW1-6 Chip Exploration Matrix & Wildcard Optimization (Stage 3):

1. Prerequisite: Stage 2 CSVs on current rates. After a new Draft career package
   or Stage 2 rebuild, prefer:
   uv run python docs/research/gw1-6-preseason-pipeline/refresh_downstream.py
   (also refreshes GKP / DEF / ownership). Stage 3 only:
   uv run python docs/research/gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/run_wc4_simulation.py
   - Generates 6-GW projections (gw1-6_projections.csv) via ParticipationStateHybridModel.
   - Solves 16-scenario exploration matrix via SciPy MILP:
     * BB Timing: GW1 vs GW2 Bench Boost
     * Mid Chip: GW3 Free Hit (FH3) vs GW3 Triple Captain (TC3)
     * Structural Bans: Allow vs Ban Haaland in GW1-3 pre-chip squad; Allow vs Ban Bruno Fernandes
     * Wildcard: GW4 Wildcard Option 1 (maximize GW4-6 XI xP <= £100.0m)
   - Enforces transfer rules: rolls GW2/GW3/GW5, banks 4 Free Transfers into GW6 post-international break.
   - Compares with current user_picks.parquet.
   - Exports summary, simulation, and user comparison CSVs.
2. Update Findings and summary tables in gw1-6-chip-wc4-squads.md and the master README table.
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

### 1. Summary table (all 16) — ADR-0014 rates

| ID | BB | Mid | Ban H | Ban Bruno | TC | GW1–3 | GW4–6 | Total | FTs |
| :--- | :---: | :---: | :---: | :---: | :---: | ---: | ---: | ---: | :---: |
| S1 | GW1 | FH3 | allow | allow | — | 176.79 | 155.37 | 332.16 | 4 |
| S2 | GW1 | FH3 | allow | ban | — | 174.77 | 155.37 | 330.14 | 4 |
| S3 | GW1 | FH3 | ban | allow | — | 176.79 | 155.37 | 332.16 | 4 |
| S4 | GW1 | FH3 | ban | ban | — | 173.96 | 155.37 | 329.33 | 4 |
| S5 | GW1 | TC3 | allow | allow | Haaland | 183.51 | 155.37 | 338.88 | 4 |
| S6 | GW1 | TC3 | allow | ban | Haaland | 183.38 | 155.37 | 338.75 | 4 |
| S7 | GW1 | TC3 | ban | allow | Vuskovic | 183.38 | 155.37 | 338.75 | 4 |
| S8 | GW1 | TC3 | ban | ban | Vuskovic | 180.55 | 155.37 | 335.92 | 4 |
| S9 | GW2 | FH3 | allow | allow | — | 176.97 | 155.37 | **332.34** | 4 |
| S10 | GW2 | FH3 | allow | ban | — | 175.27 | 155.37 | 330.64 | 4 |
| S11 | GW2 | FH3 | ban | allow | — | 176.97 | 155.37 | **332.34** | 4 |
| S12 | GW2 | FH3 | ban | ban | — | 173.93 | 155.37 | 329.30 | 4 |
| S13 | GW2 | TC3 | allow | allow | Haaland | 184.77 | 155.37 | **340.14** | 4 |
| S14 | GW2 | TC3 | allow | ban | Haaland | 183.71 | 155.37 | 339.08 | 4 |
| S15 | GW2 | TC3 | ban | allow | Vuskovic | 184.06 | 155.37 | 339.43 | 4 |
| S16 | GW2 | TC3 | ban | ban | Vuskovic | 180.33 | 155.37 | 335.70 | 4 |

Bruno ban is binding. Haaland ban non-binding on FH3 allow-Bruno paths (S1=S3, S9=S11). GW4–6 Opt1 is shared: **155.37**.

### 2. Top FH3 path (S9)

**GW1–2 Pre-FH (£98.0m, BB2)** — no Haaland  
GKP: Lammens, Roefs · DEF: Gabriel, Calafiori, Vuskovic, Maguire, Ballard · MID: B.Fernandes, Palmer, Wirtz, Tzolis, E.Le Fée · FWD: João Pedro, Wright, Thomas-Asante

**GW3 Free Hit (£97.5m)** — Haaland in  
GKP: Donnarumma, Scherpen · DEF: Virgil, O'Reilly, Vuskovic, Wieffer, Davis · MID: Wirtz, O.Dango, Schade, Crooks, Slater · FWD: Haaland, Thiago, Watkins

**GW4–6 WC Opt1 (£97.5m)**  
GKP: Raya, Kinsky · DEF: Gabriel, Tarkowski, Vuskovic, Wieffer, Thiaw · MID: Palmer, Tzolis, Sarr, Ndiaye, Slater · FWD: Haaland, Thomas-Asante, Walle Egeli · GW4–6 **155.37**

### 3. Top TC3 path (S13)

**GW1–3 Pre-WC (£100.0m, BB2 + TC Haaland)**  
GKP: Donnarumma, Roefs · DEF: Calafiori, Vuskovic, Wieffer, Maguire, Ballard · MID: B.Fernandes, Wirtz, O.Dango, Schade, E.Le Fée · FWD: Haaland, Wright, Thomas-Asante · Post-WC same Opt1 as S9.

### 4. User squad comparison

| Strategy Path | GW1–3 xP | GW4–6 xP | Total 6-GW xP | Peer MILP Total | Lag vs Peer | Pre-WC Opp Loss | Banked FTs GW6 | User Spend |
|---|---|---|---|---|---|---|---|---|
| User + BB1 + FH3 + WC4 Opt1 | 157.86 | 155.37 | 313.23 | 332.16 | -18.93 | -18.93 | 4 | £100.0m |
| User + BB1 + TC3 + WC4 Opt1 | 158.57 | 155.37 | 313.94 | 338.88 | -24.94 | -24.94 | 4 | £100.0m |
| User + BB2 + FH3 + WC4 Opt1 | 157.27 | 155.37 | 312.64 | 332.34 | -19.70 | -19.70 | 4 | £100.0m |
| User + BB2 + TC3 + WC4 Opt1 | 157.98 | 155.37 | 313.35 | 340.14 | -26.79 | -26.79 | 4 | £100.0m |

---

## Decision

**Verdict**: Dual winners — **S9 FH3 332.34 xP** · **S13 TC3 340.14 xP**. BB2 now beats BB1 on both chip types after ADR-0014 rates.

**Recommended Action**: Prefer S13 if deploying early Triple Captain in GW3; prefer S9 if banking TC for double gameweeks.

---

## Verification & Delivery

- Runner exports summary / simulation / user comparison CSVs under `data/research/gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/`.
- Full downstream: `uv run python docs/research/gw1-6-preseason-pipeline/refresh_downstream.py`.
