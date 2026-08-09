# GW1–6 Chip Exploration Matrix (BB × FH3|TC3 × Haaland × Bruno × WC4 Opt1)

**Updated**: 2026-08-10T06:45:00+07:00  
**Data stamp**: Stage 2 dual-floor rates 2026-08-10; projections horizon 6 + availability overlays; FPL API pricing 2026-07-29  
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

## Agent Prompt

```text
Run GW1-6 exploration matrix after Stage 2 rebuild.
Matrix (16): BB × (FH3|TC3) × Haaland ban × Bruno ban × WC4 Opt1.
Ban = pre squad only; FH3/WC4 may include banned players; TC3 = 3× best GW3 XI xP.
Export summary + simulation + user comparison CSVs; update Findings from CSV.
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
| S1 | GW1 | FH3 | allow | allow | — | 174.83 | 152.43 | **327.26** | 4 |
| S2 | GW1 | FH3 | allow | ban | — | 174.83 | 152.43 | 327.26 | 4 |
| S3 | GW1 | FH3 | ban | allow | — | 174.83 | 152.43 | 327.26 | 4 |
| S4 | GW1 | FH3 | ban | ban | — | 174.83 | 152.43 | 327.26 | 4 |
| S5 | GW1 | TC3 | allow | allow | Haaland | 183.61 | 152.43 | **336.04** | 4 |
| S6 | GW1 | TC3 | allow | ban | Haaland | 183.61 | 152.43 | 336.04 | 4 |
| S7 | GW1 | TC3 | ban | allow | Vuskovic | 178.87 | 152.43 | 331.30 | 4 |
| S8 | GW1 | TC3 | ban | ban | Vuskovic | 178.87 | 152.43 | 331.30 | 4 |
| S9 | GW2 | FH3 | allow | allow | — | 174.00 | 152.43 | 326.43 | 4 |
| S10 | GW2 | FH3 | allow | ban | — | 174.00 | 152.43 | 326.43 | 4 |
| S11 | GW2 | FH3 | ban | allow | — | 173.39 | 152.43 | 325.82 | 4 |
| S12 | GW2 | FH3 | ban | ban | — | 173.39 | 152.43 | 325.82 | 4 |
| S13 | GW2 | TC3 | allow | allow | Haaland | 182.87 | 152.43 | 335.30 | 4 |
| S14 | GW2 | TC3 | allow | ban | Haaland | 182.87 | 152.43 | 335.30 | 4 |
| S15 | GW2 | TC3 | ban | allow | Vuskovic | 178.52 | 152.43 | 330.95 | 4 |
| S16 | GW2 | TC3 | ban | ban | Vuskovic | 178.52 | 152.43 | 330.95 | 4 |

Bruno ban non-binding. Haaland ban non-binding on BB1 FH3 paths (S1=S3): Isak-led pre-FH optima omit Haaland anyway after dual-floor Isak uplift.

### 2. Top FH3 path (S1)

**GW1–2 Pre-FH (£99.0m, BB1)** — no Haaland  
GKP: Raya, Lammens · DEF: Gabriel, Muharemović, Ballard, Alderete, Maguire · MID: Palmer, Mbeumo, Sarr, E.Le Fée, Maeda · FWD: Isak, Thiago, João Pedro

**GW3 Free Hit (£98.5m)** — Haaland in  
GKP: Donnarumma, Perri · DEF: O'Reilly, Hill, Vuskovic, Jacquet, Cash · MID: Wirtz, Schade, Tel, Lukić, Lavia · FWD: Haaland, Isak, Thiago

**GW4–6 WC Opt1 (£100.0m)**  
GKP: Raya, Perri · DEF: Gabriel, Tarkowski, Vuskovic, Muharemović, Thiaw · MID: Palmer, Sarr, Ndiaye, Crooks, Slater · FWD: Haaland, Isak, Thomas-Asante · GW4–6 **152.43**

### 3. Top TC3 path (S5)

**GW1–3 Pre-WC (£100.0m, BB1 + TC Haaland)**  
GKP: Donnarumma, Lammens · DEF: Vuskovic, Muharemović, Jacquet, Ballard, Alderete · MID: Palmer, Schade, E.Le Fée, Maeda, Gomez · FWD: Haaland, Isak, Thiago · Post-WC same Opt1 as S1.

### 4. User squad comparison

Lag still large (8/15 picks stubbed 0 xP). Refresh `user_picks` before personal decisions.

---

## Decision

**Verdict**: Dual winners — **S1 FH3 327.26 xP** · **S5 TC3 336.04 xP**. Stage 2 dual-floor raised Isak; FH3 optima can skip Haaland pre-FH and buy him on FH3/WC4.

**Recommended Action**: Prefer S5 if early TC acceptable; S1 if banking TC. Re-run after authenticated squad refresh.

---

## Risks and unknowns

- TC vs FH not fungible.
- Packaged Draft Regulars (Crooks, Thomas-Asante, Slater) now appear in WC Opt1 — sensitive to best-guess package quality.
- User comparison degraded by stale picks.

---

## Verification & Delivery

- Runner exports summary / simulation / user comparison CSVs under `data/research/gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/`.
