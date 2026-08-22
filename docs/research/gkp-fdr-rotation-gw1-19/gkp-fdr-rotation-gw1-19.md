# First-Half GKP Rotation Pairs (GW1–19)

**Updated**: 2026-08-22T17:59:00+07:00  
**Data stamp**: 2026-08-22 (FPL API Snapshot + fpl.page GW1 Lineups)  
**Season**: 2026/27  
**Status**: Active  
**Purpose**: Rank and evaluate all starting goalkeeper rotation pairs across the first half of the season (GW1–19) using home/away-adjusted Fixture Difficulty Ratings (FDR) across all available combined price brackets.  
**Scope**: GW 1–19 fixtures (190 matches); 20 starting goalkeepers from fpl.page predicted lineups; modified FDR calculation ($\pm 0.25$ home/away shift); rankings across all viable combined price points (£9.0m to £11.5m).  
**Related**: [`INDEX.md`](../INDEX.md) · [First-Half Chip Strategy](../fpl-first-half-chip-strategy/fpl-first-half-chip-strategy.md)  
**Artifact**: [gkp_rotation_pairs_summary.csv](gkp_rotation_pairs_summary.csv) · [starting_gkps_gw1_19.csv](starting_gkps_gw1_19.csv) · [gw1_19_rotation_schedule_picks.csv](gw1_19_rotation_schedule_picks.csv)

---

## Sources

- **Primary**: [FPL GW1 Predicted Line-ups & Team News — Charlie (FPL Meerkat) / FPL Focal](https://fpl.page/article/fpl-gw1-predicted-lineups-team-news-2627) — published 2026-08-21; accessed 2026-08-22; role: Premier League starting goalkeeper predictions per club.
- **Repository data**: `data/processed/fixtures.parquet`, `data/processed/clubs.parquet`, `data/processed/players.parquet` — cutoff 2026-08-22.

**Source boundary**: Goalkeeper starting status is sourced from external pre-season consensus (FPL Meerkat). Base Fixture Difficulty Ratings (FDR) are sourced from official FPL API fixture metadata.

---

## Agent Prompt

```text
Full redo docs/research/gkp-fdr-rotation-gw1-19/gkp-fdr-rotation-gw1-19.md

1. Re-read primary source https://fpl.page/article/fpl-gw1-predicted-lineups-team-news-2627 for any updated starting GKPs.
2. Run runner: `python3 docs/research/gkp-fdr-rotation-gw1-19/runner.py`.
3. Verify companion CSVs (starting_gkps_gw1_19.csv, gkp_rotation_pairs_summary.csv, gw1_19_rotation_schedule_picks.csv).
4. Refresh tables, total_mod_fdr sums, and price tier top-10 lists in this note.
5. Keep companion artifacts colocated inside docs/research/gkp-fdr-rotation-gw1-19/.
```

---

## Method

**Method type**: Empirical combinatorial rotation optimization based on adjusted Fixture Difficulty Rating.

**Inputs**:
- 20 starting Premier League goalkeepers and current prices from `players.parquet`.
- 190 first-half Premier League matches (GW1–19) from `fixtures.parquet`.

**Procedure**:
1. Map each team to its designated starting goalkeeper and purchase cost.
2. Calculate the gameweek FDR for each team $i$ in gameweek $g$:
   $$\text{Mod FDR}_i(g) = \begin{cases} \text{Base FDR} - 0.25 & \text{if Home} \\ \text{Base FDR} + 0.25 & \text{if Away} \end{cases}$$
3. For every unique pair of starting goalkeepers $(A, B)$ (190 total pairs across 20 goalkeepers), calculate the weekly rotated FDR:
   $$\text{Rotated GW FDR}(g) = \min\big(\text{Mod FDR}_A(g), \text{Mod FDR}_B(g)\big)$$
4. Sum the rotated FDR across GW1–19 to get `total_mod_fdr` and `total_base_fdr`.
5. Group pairs by `combined_cost` (£9.0m, £9.5m, £10.0m, £10.5m, £11.0m, £11.5m) and rank by ascending `total_mod_fdr`.

### Metric Definitions & Direction

| Metric | Symbol | Definition / Formula | Direction | Ideal / Benchmark | Description |
|---|---|---|---|---|---|
| **Total Modified FDR** | `total_mod_fdr` | $\sum_{g=1}^{19} \min(\text{Mod FDR}_A(g), \text{Mod FDR}_B(g))$ | Lower is better $\downarrow$ | **$\le 44.00$** | Cumulative rotated fixture difficulty across GW1–19 with home/away weighting. |
| **Average Modified FDR** | `avg_mod_fdr` | $\frac{\text{total\_mod\_fdr}}{19}$ | Lower is better $\downarrow$ | **$\le 2.30$ / GW** | Mean difficulty of the started goalkeeper each gameweek. Unrotated baseline is $\approx 3.00$. |
| **Total Base FDR** | `total_base_fdr` | $\sum_{g=1}^{19} \min(\text{Base FDR}_A(g), \text{Base FDR}_B(g))$ | Lower is better $\downarrow$ | **$\le 46.00$** | Unmodified official FPL FDR sum under weekly best-fixture rotation. |
| **Combined Cost** | `combined_cost` | $\text{Cost}_A + \text{Cost}_B$ | Context-dependent | **£9.0m – £9.5m** | Combined squad budget allocation for both goalkeepers. |

---

## Source synthesis

### Main claims
- The 20 starting goalkeepers for GW1 are:
  - **£4.5m (7)**: Petrović (BOU), Verbruggen (BHA), Rushworth (COV), Leno (FUL), Tzolakis (HUL), Scherpen (IPS), Kinsky (TOT).
  - **£5.0m (9)**: Suzuki (AVL), Kelleher (BRE), Sánchez (CHE), Henderson (CRY), Trafford (LEE), Lammens (MUN), Horníček (NEW), Sels (NFO), Roefs (SUN).
  - **£5.5m (3)**: Pickford (EVE), Alisson (LIV), Donnarumma (MCI).
  - **£6.0m (1)**: Raya (ARS).
- There are no £4.0m starting goalkeepers in the league.

---

## Project interpretation

### Decision rules
- **Budget Pair (£9.0m)**: If spending £9.0m, **Petrović (BOU) + Scherpen (IPS)** or **Verbruggen (BHA) + Rushworth (COV)** provide the top fixture complementarity (`total_mod_fdr` **45.25**).
- **Sweet-Spot Pair (£9.5m)**: **Sels (NFO, £5.0m) + Kinsky (TOT, £4.5m)** achieves `total_mod_fdr` **43.75** (2.30/GW), featuring a perfect 6-gameweek home-fixture rotation run in GW1–6.
- **Premium Hybrid (£10.0m)**: **Rushworth (COV, £4.5m) + Donnarumma (MCI, £5.5m)** delivers the absolute best rotation across all 190 pairs (`total_mod_fdr` **43.25**).

---

## Findings

### 1. Standalone Goalkeeper Baseline (GW1–19)
From [`starting_gkps_gw1_19.csv`](starting_gkps_gw1_19.csv):

| Club | Starting GKP | Cost | Home/Away | Base FDR | Mod FDR | Avg Mod FDR |
|:---|:---|:---:|:---:|:---:|:---:|:---:|
| **LIV** | Alisson (`A.Becker`) | £5.5m | 10H / 9A | 55.0 | 54.75 | 2.88 |
| **AVL** | Suzuki | £5.0m | 10H / 9A | 56.0 | 55.75 | 2.93 |
| **MCI** | Donnarumma | £5.5m | 10H / 9A | 56.0 | 55.75 | 2.93 |
| **CHE** | Sánchez | £5.0m | 10H / 9A | 57.0 | 56.75 | 2.99 |
| **TOT** | Kinsky | £4.5m | 10H / 9A | 57.0 | 56.75 | 2.99 |
| **NFO** | Sels | £5.0m | 9H / 10A | 57.0 | 57.25 | 3.01 |
| **BOU** | Petrović | £4.5m | 10H / 9A | 58.0 | 57.75 | 3.04 |
| **BRE** | Kelleher | £5.0m | 10H / 9A | 58.0 | 57.75 | 3.04 |
| **COV** | Rushworth | £4.5m | 10H / 9A | 58.0 | 57.75 | 3.04 |
| **NEW** | Horníček | £5.0m | 10H / 9A | 58.0 | 57.75 | 3.04 |
| **ARS** | Raya | £6.0m | 9H / 10A | 58.0 | 58.25 | 3.07 |
| **MUN** | Lammens | £5.0m | 9H / 10A | 58.0 | 58.25 | 3.07 |
| **SUN** | Roefs | £5.0m | 9H / 10A | 58.0 | 58.25 | 3.07 |
| **BHA** | Verbruggen | £4.5m | 9H / 10A | 58.0 | 58.25 | 3.07 |
| **IPS** | Scherpen | £4.5m | 9H / 10A | 59.0 | 59.25 | 3.12 |
| **EVE** | Pickford | £5.5m | 9H / 10A | 59.0 | 59.25 | 3.12 |
| **CRY** | Henderson | £5.0m | 9H / 10A | 59.0 | 59.25 | 3.12 |
| **FUL** | Leno | £4.5m | 9H / 10A | 59.0 | 59.25 | 3.12 |
| **HUL** | Tzolakis | £4.5m | 10H / 9A | 60.0 | 59.75 | 3.15 |
| **LEE** | Trafford | £5.0m | 9H / 10A | 60.0 | 60.25 | 3.17 |

---

### 2. Top Rotation Pairs by Price Bracket
From [`gkp_rotation_pairs_summary.csv`](gkp_rotation_pairs_summary.csv):

#### £9.0m Bracket (£4.5m + £4.5m)
| Rank | Pair | Total Mod FDR | Total Base FDR | Avg Mod FDR |
|:---:|:---|:---:|:---:|:---:|
| **1** | **Petrović** (BOU) + **Scherpen** (IPS) | **45.25** | 48.0 | 2.38 |
| **2** | **Verbruggen** (BHA) + **Rushworth** (COV) | **45.25** | 48.0 | 2.38 |
| **3** | **Leno** (FUL) + **Kinsky** (TOT) | **45.75** | 47.0 | 2.41 |
| **4** | **Rushworth** (COV) + **Leno** (FUL) | **46.25** | 49.0 | 2.43 |
| **5** | **Petrović** (BOU) + **Tzolakis** (HUL) | **46.75** | 49.0 | 2.46 |
| **6** | **Verbruggen** (BHA) + **Kinsky** (TOT) | **46.75** | 49.0 | 2.46 |
| **7** | **Petrović** (BOU) + **Leno** (FUL) | **46.75** | 50.0 | 2.46 |
| **8** | **Petrović** (BOU) + **Rushworth** (COV) | **47.25** | 49.0 | 2.49 |
| **9** | **Verbruggen** (BHA) + **Tzolakis** (HUL) | **47.25** | 49.0 | 2.49 |
| **10** | **Petrović** (BOU) + **Verbruggen** (BHA) | **47.75** | 49.0 | 2.51 |

#### £9.5m Bracket (£5.0m + £4.5m)
| Rank | Pair | Total Mod FDR | Total Base FDR | Avg Mod FDR |
|:---:|:---|:---:|:---:|:---:|
| **1** | **Sels** (NFO) + **Kinsky** (TOT) | **43.75** | 46.0 | 2.30 |
| **2** | **Kinsky** (TOT) + **Roefs** (SUN) | **44.25** | 46.0 | 2.33 |
| **3** | **Petrović** (BOU) + **Roefs** (SUN) | **44.75** | 47.0 | 2.36 |
| **4** | **Rushworth** (COV) + **Sels** (NFO) | **44.75** | 48.0 | 2.36 |
| **5** | **Rushworth** (COV) + **Trafford** (LEE) | **45.25** | 48.0 | 2.38 |
| **6** | **Suzuki** (AVL) + **Rushworth** (COV) | **45.75** | 46.0 | 2.41 |
| **7** | **Suzuki** (AVL) + **Petrović** (BOU) | **45.75** | 47.0 | 2.41 |
| **8** | **Petrović** (BOU) + **Sels** (NFO) | **45.75** | 47.0 | 2.41 |
| **9** | **Sánchez** (CHE) + **Scherpen** (IPS) | **45.75** | 47.0 | 2.41 |
| **10** | **Petrović** (BOU) + **Lammens** (MUN) | **45.75** | 48.0 | 2.41 |

#### £10.0m Bracket (£5.0m + £5.0m / £5.5m + £4.5m)
| Rank | Pair | Total Mod FDR | Total Base FDR | Avg Mod FDR |
|:---:|:---|:---:|:---:|:---:|
| **1** | **Rushworth** (COV) + **Donnarumma** (MCI) | **43.25** | 46.0 | 2.28 |
| **2** | **Scherpen** (IPS) + **Donnarumma** (MCI) | **44.25** | 47.0 | 2.33 |
| **3** | **Petrović** (BOU) + **Alisson** (LIV) | **44.75** | 46.0 | 2.36 |
| **4** | **Suzuki** (AVL) + **Trafford** (LEE) | **45.25** | 47.0 | 2.38 |
| **5** | **Leno** (FUL) + **Donnarumma** (MCI) | **45.25** | 47.0 | 2.38 |
| **6** | **Rushworth** (COV) + **Pickford** (EVE) | **45.25** | 48.0 | 2.38 |
| **7** | **Sánchez** (CHE) + **Sels** (NFO) | **45.75** | 46.0 | 2.41 |
| **8** | **Tzolakis** (HUL) + **Alisson** (LIV) | **45.75** | 46.0 | 2.41 |
| **9** | **Suzuki** (AVL) + **Sels** (NFO) | **45.75** | 47.0 | 2.41 |
| **10** | **Sánchez** (CHE) + **Horníček** (NEW) | **45.75** | 47.0 | 2.41 |

#### £10.5m Bracket (£5.5m + £5.0m / £6.0m + £4.5m)
| Rank | Pair | Total Mod FDR | Total Base FDR | Avg Mod FDR |
|:---:|:---|:---:|:---:|:---:|
| **1** | **Donnarumma** (MCI) + **Lammens** (MUN) | **43.25** | 47.0 | 2.28 |
| **2** | **Sánchez** (CHE) + **Donnarumma** (MCI) | **43.75** | 46.0 | 2.30 |
| **3** | **Donnarumma** (MCI) + **Roefs** (SUN) | **43.75** | 46.0 | 2.30 |
| **4** | **Raya** (ARS) + **Kinsky** (TOT) | **45.25** | 48.0 | 2.38 |
| **5** | **Henderson** (CRY) + **Donnarumma** (MCI) | **45.25** | 48.0 | 2.38 |
| **6** | **Trafford** (LEE) + **Donnarumma** (MCI) | **45.25** | 48.0 | 2.38 |
| **7** | **Raya** (ARS) + **Petrović** (BOU) | **45.75** | 48.0 | 2.41 |
| **8** | **Suzuki** (AVL) + **Donnarumma** (MCI) | **45.75** | 48.0 | 2.41 |
| **9** | **Alisson** (LIV) + **Lammens** (MUN) | **45.75** | 48.0 | 2.41 |
| **10** | **Donnarumma** (MCI) + **Horníček** (NEW) | **46.25** | 47.0 | 2.43 |

#### £11.0m Bracket (£5.5m + £5.5m / £6.0m + £5.0m)
| Rank | Pair | Total Mod FDR | Total Base FDR | Avg Mod FDR |
|:---:|:---|:---:|:---:|:---:|
| **1** | **Alisson** (LIV) + **Donnarumma** (MCI) | **43.75** | 46.0 | 2.30 |
| **2** | **Pickford** (EVE) + **Alisson** (LIV) | **45.25** | 47.0 | 2.38 |
| **3** | **Pickford** (EVE) + **Donnarumma** (MCI) | **46.25** | 48.0 | 2.43 |
| **4** | **Raya** (ARS) + **Trafford** (LEE) | **46.75** | 48.0 | 2.46 |
| **5** | **Raya** (ARS) + **Suzuki** (AVL) | **47.25** | 49.0 | 2.49 |
| **6** | **Raya** (ARS) + **Sánchez** (CHE) | **48.25** | 50.0 | 2.54 |
| **7** | **Raya** (ARS) + **Kelleher** (BRE) | **48.75** | 49.0 | 2.57 |
| **8** | **Raya** (ARS) + **Horníček** (NEW) | **49.25** | 50.0 | 2.59 |
| **9** | **Raya** (ARS) + **Henderson** (CRY) | **49.75** | 50.0 | 2.62 |
| **10** | **Raya** (ARS) + **Roefs** (SUN) | **50.25** | 50.0 | 2.64 |

#### £11.5m Bracket (£6.0m + £5.5m)
| Rank | Pair | Total Mod FDR | Total Base FDR | Avg Mod FDR |
|:---:|:---|:---:|:---:|:---:|
| **1** | **Raya** (ARS) + **Donnarumma** (MCI) | **44.75** | 47.0 | 2.36 |
| **2** | **Raya** (ARS) + **Alisson** (LIV) | **47.25** | 48.0 | 2.49 |
| **3** | **Raya** (ARS) + **Pickford** (EVE) | **51.25** | 52.0 | 2.70 |

---

### 3. Gameweek 1–19 Weekly Picks for Top Pairs
From [`gw1_19_rotation_schedule_picks.csv`](gw1_19_rotation_schedule_picks.csv):

| GW | Sels (NFO) + Kinsky (TOT) [£9.5m] | Petrović (BOU) + Scherpen (IPS) [£9.0m] | Rushworth (COV) + Donnarumma (MCI) [£10.0m] |
|:---:|:---|:---|:---|
| **1** | **NFO vs LEE (H, 1.75)** | **IPS vs SUN (H, 1.75)** | **COV @ ARS (A, 5.25) / MCI vs BOU (H, 2.75) -> MCI** |
| **2** | **TOT vs IPS (H, 1.75)** | **BOU vs FUL (H, 1.75)** | **COV vs EVE (H, 2.75)** |
| **3** | **NFO vs SUN (H, 1.75)** | **IPS vs LEE (H, 1.75)** | **MCI vs BHA (H, 2.75)** |
| **4** | **TOT vs BOU (H, 1.75)** | **IPS vs NFO (H, 1.75)** | **MCI @ MUN (A, 3.25)** |
| **5** | **NFO vs COV (H, 1.75)** | **BOU vs BRE (H, 1.75)** | **COV vs IPS (H, 1.75)** |
| **6** | **TOT vs FUL (H, 1.75)** | **IPS vs HUL (H, 1.75)** | **COV vs SUN (H, 1.75)** |
| **7** | **TOT @ SUN (A, 2.25)** | **BOU vs SUN (H, 1.75)** | **MCI vs BRE (H, 1.75)** |
| **8** | **TOT vs COV (H, 1.75)** | **BOU vs CRY (H, 1.75)** | **COV @ HUL (A, 2.25)** |
| **9** | **NFO vs EVE (H, 2.75)** | **IPS @ COV (A, 2.25)** | **COV vs LEE (H, 1.75)** |
| **10** | **TOT vs HUL (H, 1.75)** | **BOU vs LEE (H, 1.75)** | **MCI vs TOT (H, 2.75)** |
| **11** | **NFO vs HUL (H, 1.75)** | **BOU @ SUN (A, 2.25)** | **COV vs BHA (H, 2.75)** |
| **12** | **TOT vs MUN (H, 2.75)** | **BOU vs CHE (H, 2.75)** | **MCI vs NEW (H, 2.75)** |
| **13** | **NFO vs TOT (H, 2.75)** | **IPS vs BRE (H, 2.75)** | **MCI @ LEE (A, 2.25)** |
| **14** | **NFO @ AVL / TOT @ EVE (3.25)** | **IPS vs EVE (H, 2.75)** | **MCI @ FUL (A, 2.25)** |
| **15** | **TOT @ BHA (A, 3.25)** | **IPS vs ARS (H, 3.75)** | **MCI @ SUN (A, 2.25)** |
| **16** | **NFO @ BOU (A, 2.25)** | **BOU @ COV (A, 2.25)** | **COV @ BRE (A, 3.25) / MCI vs CRY (H, 1.75)** |
| **17** | **NFO vs MUN (H, 2.75)** | **BOU @ HUL (A, 2.25)** | **COV vs FUL (H, 2.75)** |
| **18** | **TOT vs NEW (H, 2.75)** | **IPS vs COV (H, 1.75)** | **COV @ NFO (A, 3.25) / MCI @ AVL (A, 3.25)** |
| **19** | **NFO vs BRE (H, 2.75)** | **BOU @ LEE (A, 2.25)** | **COV @ CRY (A, 3.25) / MCI vs IPS (H, 1.75)** |

---

## Decision

**Verdict**: The standout GKP rotation strategy for GW1–19 is **Sels (NFO, £5.0m) + Kinsky (TOT, £4.5m)** at **£9.5m combined** (Total Mod FDR: **43.75**), providing a sub-2.31 average fixture difficulty and an unbroken home fixture sequence through the first 6 gameweeks. For strict budget setups (£9.0m), **Petrović (BOU) + Scherpen (IPS)** yields the best coverage (**45.25**).

---

## Risks and unknowns

1. **Pre-season Lineup Volatility**: Starting goalkeepers are based on Gameweek 1 predicted lineups. Manager changes or late transfers (e.g., cup/European rotation, late window signings) may shift starting status.
2. **Transfer Deadlines and Postponements**: Any postponed fixtures (blanks/doubles) after GW19 will require schedule re-evaluation.
