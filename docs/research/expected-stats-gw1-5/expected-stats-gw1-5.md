# Expected Stats & GW1–5 Points Projection Research Note

**Updated**: 2026-08-01T20:37:00+07:00  
**Data stamp**: Expected Role Table 2026-08-01; 2025/26 archive 2026-07-29; FPL API elements summary 2026-07-29; European league match logs 2023–2026  
**Season**: 2026/27  
**Status**: Active Research Model (Non-Full-Season Candidate)  
**Purpose**: Compute per-90 event rates (xG, xA, xDEFcon, xSaves, xConceded) using a 50% 2025/26 season + 50% career stats blend across a 3-season window (2023–2026), and project GW1–5 expected points ($xP$) for 193 Nailed & Regular Starters.  
**Scope**: 193 players (90 Nailed Starter, 103 Regular Starter) across all 20 Premier League clubs.  
**Related**: [Expected Role GW1–5](../expected-role-gw1-5/expected-role-gw1-5.md) · [Expected Role Table CSV](../../../data/research/expected-role-gw1-5/expected-role-gw1-5.csv) · [Repo Structure Guide](README.md)  
**Artifacts**:
- [Expected Stats CSV](../../../data/research/expected-stats-gw1-5/expected-stats-gw1-5.csv) — canonical per-90 rates data
- [GW1–5 Projections CSV](../../../data/research/expected-stats-gw1-5/gw1-5_projections.csv) — row-level GW1–5 $xP$ projections

---

## Sources

- **Primary Role Input**: `data/research/expected-role-gw1-5/expected-role-gw1-5.csv` (193 Nailed & Regular Starters, expected role priors, draft availability).
- **2025/26 FPL Performance History**: `data/archive/2025-26/processed/player_performances.parquet` (match-level xG, xA, defensive contributions, saves, goals conceded).
- **3-Season FPL Career History**: `history_past` records (2023/24, 2024/25, 2025/26) from `data/raw/element_summary_{id}.json` across Premier League seasons.
- **European League 3-Season Research**: Primary match logs (FBref/Opta/FotMob) for 16 major overseas transfers (2023–2026 window across Primeira Liga, Bundesliga, Serie A, Ligue 1, Eredivisie, Championship, etc.).
- **Fixture Schedule**: `data/processed/fixtures.parquet` and `data/processed/clubs.parquet` for GW1–5 match schedule and FDR.

---

## Agent Prompt

```text
Build expected stats per-90 rates and project GW1–5 expected points across a 3-season window (2023–2026):

1. Filter data/research/expected-role-gw1-5/expected-role-gw1-5.csv for Nailed Starter and Regular Starter players (193 total).
2. Calculate per-90 rates for xG, xA, xDEFcon (CBIT threshold 10 for D, 12 for M/F), xSaves, and xConceded:
   - 50% 2025/26 season history + 50% 3-season FPL career history when both are available.
   - For foreign transfers and low-sample (<450 mins) players, incorporate 3-season (2023–2026) European league match log research (e.g. Gyökeres, Wirtz, Frimpong, Yeremy, Tel, Thiaw, Lammens, Mukiele, Alderete, Reinildo, Le Fée, Sadiki, Roefs).
   - Apply 2025/26 position baselines if data is absent.
3. Export rates to data/research/expected-stats-gw1-5/expected-stats-gw1-5.csv with rate_source and provenance_note.
4. Run ParticipationStateHybridModel scoring logic against GW1–5 fixtures:
   - Apply availability overrides (exclude_gw1-5, exclude_gw1).
   - Apply FDR difficulty multiplier max(0.2, (6.0 - FDR) / 3.0).
   - Reconstruct points across minutes, goals, assists, clean sheets, conceded penalty, defcon, saves, and bonus.
5. Export projections to data/research/expected-stats-gw1-5/gw1-5_projections.csv.
6. Verify via ruff, pytest, and verify.sh.
```

---

## Method

### 1. Per-90 Event Rates Blending Logic (3-Season Window)
For each player $i$:
- **2025/26 Season Rate**: $R_{\text{2025/26}} = \frac{\sum \text{Events}_{\text{2025/26}}}{\sum \text{Minutes}_{\text{2025/26}}} \times 90$
- **Career Rate (2023–2025)**: $R_{\text{Career}} = \frac{\sum \text{Events}_{\text{2023-2025}}}{\sum \text{Minutes}_{\text{2023-2025}}} \times 90$
- **Blended Rate**: $R_{\text{Blended}} = 0.5 \times R_{\text{2025/26}} + 0.5 \times R_{\text{Career}}$

### 2. Sample Hierarchy & Provenance
- **`fpl_historical_50_50`** (113 players): Both 2025/26 and past 3-season FPL career stats present.
- **`fpl_3season_career_only`** (34 players): 3-season FPL career stats present.
- **`external_3season_research`** (31 players): Sourced via subagent 3-season European league match log research for foreign transfers and low PL sample players.
- **`fallback_baseline`**: 2025/26 Premier League position average applied where no sample exists.

### 3. $xP$ Reconstruction Engine
Following `ParticipationStateHybridModel` (`models/participation_state_hybrid.py`):
- State probabilities ($p_{\text{start}}, p_{\text{sub}}, p_{\text{dnp}}$) and expected minutes ($xMins = p_{\text{start}} \cdot xmins_{\text{start}} + p_{\text{sub}} \cdot xmins_{\text{sub}}$) are drawn from expected role priors.
- Availability exclusions (`exclude_gw1-5`, `exclude_gw1`) set $p_{\text{dnp}} = 1.0$ for covered gameweeks.
- FDR multiplier adjusts attack, clean sheet, and conceded expectations:
  $$\text{FDR Mult} = \max\left(0.2, \frac{6.0 - \text{FDR}}{3.0}\right)$$
- Event points summed using `models/scoring_matrix.py`:
  $$xP = xP_{\text{mins}} + xP_{\text{goals}} + xP_{\text{assists}} + xP_{\text{clean\_sheet}} + xP_{\text{conceded}} + xP_{\text{defcon}} + xP_{\text{saves}} + xP_{\text{bonus}}$$

---

## Findings

### 1. Top Projected Players (GW1–5 Aggregate $xP$, 3-Season Window)

| Rank | Player | Club | Pos | Expected Role | GW1 | GW2 | GW3 | GW4 | GW5 | Total 5-GW $xP$ |
|------|--------|------|-----|---------------|-----|-----|-----|-----|-----|-----------------|
| 1 | Palmer | CHE | MID | Nailed Starter | 5.16 | 6.02 | 3.61 | 6.02 | 5.16 | **25.97** |
| 2 | Isak | LIV | FWD | Nailed Starter | 4.68 | 4.68 | 5.55 | 5.55 | 4.68 | **25.14** |
| 3 | Vuskovic | BHA | DEF | Nailed Starter | 4.64 | 5.01 | 4.46 | 4.46 | 5.01 | **23.59** |
| 4 | Hill | BOU | DEF | Nailed Starter | 5.55 | 4.22 | 4.22 | 4.22 | 4.78 | **22.97** |
| 5 | Konsa | AVL | DEF | Nailed Starter | 4.53 | 4.66 | 4.58 | 4.53 | 4.53 | **22.84** |
| 6 | Sarr | CRY | MID | Nailed Starter | 4.55 | 3.99 | 4.55 | 5.17 | 4.55 | **22.81** |
| 7 | Gabriel | ARS | DEF | Nailed Starter | 4.21 | 4.77 | 4.77 | 4.45 | 4.45 | **22.66** |
| 8 | Donnarumma | MCI | GKP | Nailed Starter | 4.50 | 4.50 | 4.45 | 4.69 | 4.45 | **22.58** |
| 9 | Dalot | MUN | DEF | Nailed Starter | 4.38 | 4.38 | 4.44 | 4.65 | 4.44 | **22.31** |
| 10 | Kroupi.Jr | BOU | MID | Nailed Starter | 3.52 | 4.63 | 4.63 | 4.63 | 4.05 | **21.45** |
| 16 | Gyökeres | ARS | FWD | Regular Starter | 5.28 | 3.54 | 3.54 | 4.41 | 4.41 | **21.18** |

### 2. Availability Impact
- **Saliba (ARS)**: $xP = 0.00$ across GW1–5 due to extended rehabilitation (`exclude_gw1-5`).
- **J.Timber (ARS)**: $xP = 0.00$ in GW1 (`exclude_gw1`), projecting 16.72 $xP$ across GW2–5.

---

## Decision

**Verdict**: Approved for GW1–5 draft planning and target evaluation.

**Recommended Action**:
- Use `data/research/expected-stats-gw1-5/gw1-5_projections.csv` to rank draft shortlist targets.
- Re-run `build_expected_stats.py` and `project_expected_points.py` if injury news or availability overrides update prior to GW1 lock.

---

## Risks and Unknowns

- **Pre-Season Transfer Data**: 3-season European league match log research for foreign transfers (e.g. Gyökeres, Wirtz, Frimpong, Thiaw) provides comprehensive baseline data, but team style shifts at new clubs remain a factor.
- **FDR Sensitivity**: Opponent difficulty multipliers reflect team-level FDR ratings; unexpected lineup shifts can alter clean sheet probabilities.
- **Bonus Point Heuristic**: Expected bonus points use a baseline expectation ($\sim 0.25$ per start); actual match BPS outcomes may fluctuate based on match dynamics.
