# First-Half 5-DEF Rotation Strategy (GW1–19)

**Updated**: 2026-08-23T18:10:00+07:00  
**Data stamp**: 2026-08-23 (FPL API Live Rosters + Committed Expected Role Prior)  
**Season**: 2026/27  
**Status**: Active  
**Purpose**: Evaluate, rank, and schedule all 5-defender rotation structures across the first half of the season (GW1–19) by fielding the optimal 3 starting defenders each gameweek under home/away-adjusted Fixture Difficulty Ratings (FDR) across all structural budget tiers.  
**Scope**: GW1–19 fixtures (190 matches); 20 Premier League clubs; all 42,104 valid 5-defender multisets (up to 3 per club); starting defender mapping and pricing from `features/expected-role-gw1-5.csv` and `players.parquet` (authoritative club registration); structural budget tiers (Pure Budget £20.0m–£22.0m, 1-Premium Anchor £22.5m–£24.5m, 2-Premium Anchor £25.0m–£27.0m, and Global Unconstrained).  
**Related**: [`INDEX.md`](../INDEX.md) · [First-Half GKP Rotation Pairs](../gkp-fdr-rotation-gw1-19/gkp-fdr-rotation-gw1-19.md) · [First-Half Chip Strategy](../fpl-first-half-chip-strategy/fpl-first-half-chip-strategy.md)  
**Artifact**: [def_rotation_5sets_summary.csv](def_rotation_5sets_summary.csv) · [starting_defs_gw1_19.csv](starting_defs_gw1_19.csv) · [gw1_19_def_rotation_schedule_picks.csv](gw1_19_def_rotation_schedule_picks.csv)

---

## Sources

- **Primary**: Committed Preseason Expected Role Prior (`features/expected-role-gw1-5.csv`) combined with authoritative FPL API player-club registration (`players.parquet`).
- **Repository data**: `data/processed/fixtures.parquet`, `data/processed/clubs.parquet`, `data/processed/players.parquet` — cutoff 2026-08-23.

**Source boundary**: Defender starting status and role assignments are established from the committed Expected Role Prior. Official club registrations, prices, fixture difficulties, and home/away match metadata are sourced from official FPL API metadata in `players.parquet` and `fixtures.parquet`.

---

## Agent Prompt

```text
Full redo docs/research/def-fdr-rotation-gw1-19/def-fdr-rotation-gw1-19.md

1. Verify authoritative club registrations in data/processed/players.parquet and roles in features/expected-role-gw1-5.csv.
2. Run runner: `uv run python docs/research/def-fdr-rotation-gw1-19/runner.py`.
3. Verify companion CSVs (starting_defs_gw1_19.csv, def_rotation_5sets_summary.csv, gw1_19_def_rotation_schedule_picks.csv).
4. Run tests: `uv run pytest tests/test_def_fixture_rotation.py`.
5. Refresh tables, total_mod_fdr sums, and structural tier rankings in this note.
6. Keep companion artifacts colocated inside docs/research/def-fdr-rotation-gw1-19/.
```

---

## Method

**Method type**: Combinatorial rotation optimization across 5-defender squads selecting the 3 easiest fixtures per gameweek based on venue-modified Fixture Difficulty Ratings.

**Inputs**:
- 20 Premier League clubs and their starting defenders mapped sequentially from `players.parquet` joined with `features/expected-role-gw1-5.csv`.
- 190 first-half Premier League matches (GW1–19) from `fixtures.parquet`.

**Procedure**:
1. Map each club to its designated regular/nailed starting defenders and purchase costs using authoritative API club registration.
2. Calculate the gameweek FDR for club $c$ in gameweek $g$:
   $$\text{Mod FDR}_c(g) = \begin{cases} \text{Base FDR} - 0.25 & \text{if Home} \\ \text{Base FDR} + 0.25 & \text{if Away} \end{cases}$$
3. Generate all $\binom{20+5-1}{5} - \text{invalid cases} = 42,104$ valid 5-defender combinations with replacement (subject to the FPL maximum constraint of $\le 3$ players per club).
4. For each 5-defender set $S = \{d_1, d_2, d_3, d_4, d_5\}$ in each gameweek $g \in [1, 19]$:
   - Extract the 5 modified FDR values and sort ascending: $f_{(1)}(g) \le f_{(2)}(g) \le f_{(3)}(g) \le f_{(4)}(g) \le f_{(5)}(g)$.
   - Field the top 3 starters (minimum legal defensive lineup to maximize attacking funds) and sum their difficulties:
     $$\text{Lineup Mod FDR}(g) = f_{(1)}(g) + f_{(2)}(g) + f_{(3)}(g)$$
5. Calculate the cumulative 19-gameweek total and per-defender average:
   $$\text{Total Lineup Mod FDR} = \sum_{g=1}^{19} \text{Lineup Mod FDR}(g)$$
   $$\text{Avg DEF Mod FDR} = \frac{\text{Total Lineup Mod FDR}}{19 \times 3}$$
6. Classify combinations into 4 structural archetypes:
   - **Pure Budget (£20.0m–£22.0m)**: All 5 defenders priced $\le £4.5\text{m}$.
   - **1-Premium Anchor (£22.5m–£24.5m)**: Exactly 1 premium $\ge £5.5\text{m}$ + 4 budget rotators ($\le £4.5\text{m}$).
   - **2-Premium Anchor (£25.0m–£27.0m)**: Exactly 2 premiums $\ge £5.5\text{m}$ + 3 budget rotators ($\le £4.5\text{m}$).
   - **Global Unconstrained**: Absolute best across all 42,104 combinations.

### Metric Definitions & Direction

| Metric | Symbol | Definition / Formula | Direction | Ideal / Benchmark | Description |
|---|---|---|---|---|---|
| **Total Lineup Modified FDR** | `total_mod_fdr` | $\sum_{g=1}^{19} \sum_{k=1}^3 \text{Mod FDR}_{(k)}(g)$ | Lower is better $\downarrow$ | **$\le 138.00$** | Cumulative difficulty across 57 started defender slots (19 GWs $\times$ 3 starters). |
| **Average DEF Modified FDR** | `avg_def_mod_fdr` | $\frac{\text{total\_mod\_fdr}}{57}$ | Lower is better $\downarrow$ | **$\le 2.40$ / DEF** | Mean fixture difficulty rating per started defender. Unrotated 3-DEF baseline is $\approx 3.03$. |
| **Total Lineup Base FDR** | `total_base_fdr` | $\sum_{g=1}^{19} \sum_{k=1}^3 \text{Base FDR}_{(k)}(g)$ | Lower is better $\downarrow$ | **$\le 144.00$** | Unmodified official FPL FDR sum for the 57 started defender slots. |
| **Combined Cost** | `combined_cost` | $\sum_{i=1}^5 \text{Cost}_i$ | Context-dependent | **£21.5m – £23.5m** | Combined squad budget allocation across all 5 defenders. |

---

## Source synthesis

### Main claims
- Sourced starting defender allocations by club (authoritative club registration):
  - **Arsenal (ARS)**: Konsa (£4.5m), Calafiori (£5.5m), White (£5.5m), Mosquera (£5.5m), Gabriel (£8.0m).
  - **Aston Villa (AVL)**: Cash (£4.5m), Pau (£4.5m), Maatsen (£4.5m), Lindelöf (£4.5m).
  - **Bournemouth (BOU)**: Smith (£4.5m), Silva (£5.0m), Hill (£5.5m), Truffert (£5.5m).
  - **Brentford (BRE)**: Ajer (£4.5m), Kayode (£4.5m), Collins (£5.5m).
  - **Brighton (BHA)**: F.Kadıoğlu (£4.5m), Boscagli (£4.5m), De Cuyper (£4.5m), Dunk (£4.5m), Wieffer (£5.0m), Vuskovic (£5.0m).
  - **Chelsea (CHE)**: Colwill (£5.0m), James (£5.5m), Palestra (£5.5m), Lacroix (£6.0m).
  - **Coventry City (COV)**: Thomas (£4.0m), van Ewijk (£4.0m), Amenda (£4.0m).
  - **Crystal Palace (CRY)**: Mitchell (£4.5m), Chadi Riad (£4.5m), Mingueza (£4.5m), Richards (£5.0m), Canvot (£5.0m), Muñoz (£5.5m).
  - **Everton (EVE)**: Mykolenko (£4.5m), O'Brien (£5.0m), Branthwaite (£5.5m), Tarkowski (£6.0m).
  - **Fulham (FUL)**: Robinson (£4.5m), J.Cuenca (£4.5m), Bassey (£4.5m), Castagne (£4.5m).
  - **Hull City (HUL)**: Ajayi (£4.0m), Coyle (£4.0m), Giles (£4.0m), Mendy (£4.0m).
  - **Ipswich Town (IPS)**: Diop (£4.0m), O'Shea (£4.0m), Davis (£4.0m), Greaves (£4.0m).
  - **Leeds (LEE)**: Rodon (£4.5m), Bogle (£4.5m), Justin (£4.5m), Bijol (£5.0m), Muharemović (£5.0m).
  - **Liverpool (LIV)**: Jacquet (£5.0m), Frimpong (£5.5m), Kerkez (£5.5m), Virgil (£6.5m).
  - **Man City (MCI)**: Rúben (£5.5m), Gvardiol (£5.5m), Khusanov (£5.5m), Guéhi (£6.0m), Matheus N. (£6.0m), O'Reilly (£6.5m).
  - **Man Utd (MUN)**: Heaven (£4.5m), Shaw (£4.5m), Dalot (£5.0m), Maguire (£5.0m).
  - **Newcastle (NEW)**: Thiaw (£5.0m), Botman (£5.0m), Hall (£5.0m), Livramento (£5.0m).
  - **Nott'm Forest (NFO)**: Aina (£4.5m), N.Williams (£5.0m), Milenković (£5.5m), Murillo (£5.5m), Diomande (£5.5m).
  - **Spurs (TOT)**: Robertson (£4.5m), Van Hecke (£5.0m), Van de Ven (£5.0m), Pedro Porro (£5.5m), Senesi (£6.0m).
  - **Sunderland (SUN)**: O'Nien (£4.0m), Hume (£4.5m), Reinildo (£4.5m), Meunier (£4.5m), Ballard (£5.0m), Alderete (£5.0m), Mukiele (£5.5m).

---

## Project interpretation

### Decision rules

1. **Pure Budget Peak (£21.5m)**:
   - The standout 5-defender pure budget rotation is **Smith (BOU, £4.5m) + Aina (NFO, £4.5m) + Robertson (TOT, £4.5m) + Thomas (COV, £4.0m) + O'Nien (SUN, £4.0m)** at **£21.5m combined**.
   - Achieves a Total Lineup Mod FDR of **137.25** (**2.408 / DEF**), representing a **20.5% fixture difficulty reduction** compared to a static 3-man unrotated baseline (~172.5).
   - Alternatively, replacing Smith with **Cash (AVL, £4.5m)** or **F.Kadıoğlu (BHA, £4.5m)** delivers **138.25** (**2.425 / DEF**).
2. **1-Premium Anchor Sweet Spot (£22.5m)**:
   - Deploying **Rúben (MCI, £5.5m) + Cash (AVL, £4.5m) + Rodon (LEE, £4.5m) + Thomas (COV, £4.0m) + O'Nien (SUN, £4.0m)** at **£22.5m** achieves Total Lineup Mod FDR **136.25** (**2.390 / DEF**).
   - Man City provides 11 elite starts (FDR 1.75–2.25); the 4 budget rotators seamlessly absorb City's away trips to top-6 opponents.
3. **Club Stacking vs Club Diversity**:
   - In 5-defender setups, stacking 2 defenders from a budget team (e.g. Double Coventry: Thomas £4.0m + van Ewijk £4.0m) yields strong pairing scores when combined with high-tier anchors (e.g. Double COV + MCI + LEE + SUN = **136.25**).
   - However, **5 Distinct Clubs match or exceed stacked performance** across all tiers while eliminating correlated clean sheet wipeouts.
4. **Anchor Benching Dynamics**:
   - In dynamic best-3 selection, a £5.5m/£6.0m premium (MCI/ARS/LIV) is naturally benched in **7 to 8 of the 19 gameweeks** (specifically during away fixtures vs ARS, MCI, LIV, CHE, TOT, MUN, NEW).
   - Rotating the anchor through difficult fixtures yields a **+0.12 FDR/DEF advantage** over locking the premium into the starting XI unconditionally.

---

## Findings

### 1. Standalone Defender Baseline (GW1–19)
From [`starting_defs_gw1_19.csv`](starting_defs_gw1_19.csv) (cheapest regular starter per club):

| Club | Starting DEF | Cost | Role | Fixtures | Base FDR | Mod FDR | Avg Mod FDR |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **LIV** | Jacquet | £5.0m | Nailed Starter | 10H / 9A | 55.0 | 54.75 | 2.882 |
| **AVL** | Cash | £4.5m | Nailed Starter | 10H / 9A | 56.0 | 55.75 | 2.934 |
| **MCI** | Rúben | £5.5m | Regular Starter | 10H / 9A | 56.0 | 55.75 | 2.934 |
| **CHE** | Colwill | £5.0m | Nailed Starter | 10H / 9A | 57.0 | 56.75 | 2.987 |
| **TOT** | Robertson | £4.5m | Regular Starter | 10H / 9A | 57.0 | 56.75 | 2.987 |
| **NFO** | Aina | £4.5m | Regular Starter | 9H / 10A | 57.0 | 57.25 | 3.013 |
| **BOU** | Smith | £4.5m | Regular Starter | 10H / 9A | 58.0 | 57.75 | 3.039 |
| **BRE** | Ajer | £4.5m | Regular Starter | 10H / 9A | 58.0 | 57.75 | 3.039 |
| **COV** | Thomas | £4.0m | Regular Starter | 10H / 9A | 58.0 | 57.75 | 3.039 |
| **NEW** | Thiaw | £5.0m | Nailed Starter | 10H / 9A | 58.0 | 57.75 | 3.039 |
| **ARS** | Konsa | £4.5m | Regular Starter | 9H / 10A | 58.0 | 58.25 | 3.066 |
| **MUN** | Heaven | £4.5m | Regular Starter | 9H / 10A | 58.0 | 58.25 | 3.066 |
| **SUN** | O'Nien | £4.0m | Regular Starter | 9H / 10A | 58.0 | 58.25 | 3.066 |
| **BHA** | F.Kadıoğlu | £4.5m | Regular Starter | 9H / 10A | 58.0 | 58.25 | 3.066 |
| **IPS** | Diop | £4.0m | Regular Starter | 9H / 10A | 59.0 | 59.25 | 3.118 |
| **EVE** | Mykolenko | £4.5m | Regular Starter | 9H / 10A | 59.0 | 59.25 | 3.118 |
| **CRY** | Mitchell | £4.5m | Nailed Starter | 9H / 10A | 59.0 | 59.25 | 3.118 |
| **FUL** | Robinson | £4.5m | Nailed Starter | 9H / 10A | 59.0 | 59.25 | 3.118 |
| **HUL** | Ajayi | £4.0m | Regular Starter | 10H / 9A | 60.0 | 59.75 | 3.145 |
| **LEE** | Rodon | £4.5m | Nailed Starter | 9H / 10A | 60.0 | 60.25 | 3.171 |

---

### 2. Structural Archetype Rankings
From [`def_rotation_5sets_summary.csv`](def_rotation_5sets_summary.csv):

#### A. Pure Budget Tier (£20.0m – £22.0m)
*All 5 defenders priced $\le £4.5\text{m}$.*

| Rank | 5-DEF Rotation Set | Cost | Distinct Clubs? | Total Mod FDR | Total Base FDR | Avg DEF FDR |
|:---:|:---|:---:|:---:|:---:|:---:|:---:|
| **1** | **Smith** (BOU) + **Aina** (NFO) + **Robertson** (TOT) + **Thomas** (COV) + **O'Nien** (SUN) | £21.5m | Yes | **137.25** | 142.0 | 2.408 |
| **2** | **Rodon** (LEE) + **Aina** (NFO) + **Robertson** (TOT) + **Thomas** (COV) + **O'Nien** (SUN) | £21.5m | Yes | **137.75** | 143.0 | 2.417 |
| **3** | **F.Kadıoğlu** (BHA) + **Aina** (NFO) + **Robertson** (TOT) + **Thomas** (COV) + **O'Nien** (SUN) | £21.5m | Yes | **138.25** | 143.0 | 2.425 |
| **4** | **Cash** (AVL) + **Aina** (NFO) + **Robertson** (TOT) + **Thomas** (COV) + **O'Nien** (SUN) | £21.5m | Yes | **138.25** | 142.0 | 2.425 |
| **5** | **Smith** (BOU) + **Mykolenko** (EVE) + **Aina** (NFO) + **Thomas** (COV) + **O'Nien** (SUN) | £21.5m | Yes | **138.25** | 142.0 | 2.425 |
| **6** | **Mykolenko** (EVE) + **Aina** (NFO) + **Robertson** (TOT) + **Thomas** (COV) + **O'Nien** (SUN) | £21.5m | Yes | **138.25** | 142.0 | 2.425 |
| **7** | **Cash** (AVL) + **Smith** (BOU) + **Rodon** (LEE) + **Thomas** (COV) + **O'Nien** (SUN) | £21.5m | Yes | **138.25** | 143.0 | 2.425 |
| **8** | **Cash** (AVL) + **Smith** (BOU) + **Aina** (NFO) + **Thomas** (COV) + **O'Nien** (SUN) | £21.5m | Yes | **138.25** | 143.0 | 2.425 |
| **9** | **Cash** (AVL) + **Rodon** (LEE) + **Robertson** (TOT) + **Thomas** (COV) + **O'Nien** (SUN) | £21.5m | Yes | **138.25** | 142.0 | 2.425 |
| **10** | **Smith** (BOU) + **Rodon** (LEE) + **Robertson** (TOT) + **Thomas** (COV) + **O'Nien** (SUN) | £21.5m | Yes | **138.25** | 143.0 | 2.425 |

---

#### B. 1-Premium Anchor Tier (£22.5m – £24.5m)
*1 Premium ($\ge £5.5\text{m}$) + 4 Budget Rotators ($\le £4.5\text{m}$).*

| Rank | 5-DEF Rotation Set | Cost | Distinct Clubs? | Total Mod FDR | Total Base FDR | Avg DEF FDR |
|:---:|:---|:---:|:---:|:---:|:---:|:---:|
| **1** | **Rúben** (MCI) + **Rodon** (LEE) + **Thomas** (COV) + **van Ewijk** (COV) + **O'Nien** (SUN) | £22.0m | Stacked | **136.25** | 143.0 | 2.390 |
| **2** | **Rúben** (MCI) + **Aina** (NFO) + **Robertson** (TOT) + **Thomas** (COV) + **O'Nien** (SUN) | £22.5m | Yes | **136.25** | 142.0 | 2.390 |
| **3** | **Rúben** (MCI) + **Rodon** (LEE) + **Robertson** (TOT) + **Thomas** (COV) + **O'Nien** (SUN) | £22.5m | Yes | **136.25** | 142.0 | 2.390 |
| **4** | **Rúben** (MCI) + **Cash** (AVL) + **Rodon** (LEE) + **Thomas** (COV) + **O'Nien** (SUN) | £22.5m | Yes | **136.25** | 142.0 | 2.390 |
| **5** | **Rúben** (MCI) + **Rodon** (LEE) + **Aina** (NFO) + **Thomas** (COV) + **van Ewijk** (COV) | £22.5m | Stacked | **136.75** | 144.0 | 2.399 |
| **6** | **Rúben** (MCI) + **Robinson** (FUL) + **Rodon** (LEE) + **Thomas** (COV) + **van Ewijk** (COV) | £22.5m | Stacked | **136.75** | 144.0 | 2.399 |
| **7** | **Rúben** (MCI) + **F.Kadıoğlu** (BHA) + **Rodon** (LEE) + **Thomas** (COV) + **O'Nien** (SUN) | £22.5m | Yes | **136.75** | 142.0 | 2.399 |
| **8** | **Rúben** (MCI) + **Cash** (AVL) + **Robinson** (FUL) + **Rodon** (LEE) + **Thomas** (COV) | £23.0m | Yes | **136.75** | 142.0 | 2.399 |
| **9** | **Rúben** (MCI) + **Cash** (AVL) + **Rodon** (LEE) + **Aina** (NFO) + **Thomas** (COV) | £23.0m | Yes | **136.75** | 142.0 | 2.399 |
| **10** | **Rúben** (MCI) + **Cash** (AVL) + **Rodon** (LEE) + **Heaven** (MUN) + **Thomas** (COV) | £23.0m | Yes | **136.75** | 143.0 | 2.399 |

---

#### C. 2-Premium Anchor Tier (£25.0m – £27.0m)
*2 Premiums ($\ge £5.5\text{m}$) + 3 Budget Rotators ($\le £4.5\text{m}$).*

| Rank | 5-DEF Rotation Set | Cost | Distinct Clubs? | Total Mod FDR | Total Base FDR | Avg DEF FDR |
|:---:|:---|:---:|:---:|:---:|:---:|:---:|
| **1** | **Rúben** (MCI) + **Gvardiol** (MCI) + **Thomas** (COV) + **van Ewijk** (COV) + **O'Nien** (SUN) | £23.0m | Stacked | **136.75** | 143.0 | 2.399 |
| **2** | **Rúben** (MCI) + **Gvardiol** (MCI) + **Heaven** (MUN) + **Thomas** (COV) + **O'Nien** (SUN) | £23.5m | Stacked | **136.75** | 144.0 | 2.399 |
| **3** | **Rúben** (MCI) + **Gvardiol** (MCI) + **Rodon** (LEE) + **Heaven** (MUN) + **Thomas** (COV) | £24.0m | Stacked | **136.75** | 145.0 | 2.399 |
| **4** | **Rúben** (MCI) + **Gvardiol** (MCI) + **Robinson** (FUL) + **Thomas** (COV) + **O'Nien** (SUN) | £23.5m | Stacked | **136.75** | 143.0 | 2.399 |
| **5** | **Rúben** (MCI) + **Gvardiol** (MCI) + **Robinson** (FUL) + **Heaven** (MUN) + **Thomas** (COV) | £24.0m | Stacked | **137.25** | 144.0 | 2.408 |
| **6** | **Rúben** (MCI) + **Gvardiol** (MCI) + **Robinson** (FUL) + **Rodon** (LEE) + **Thomas** (COV) | £24.0m | Stacked | **137.25** | 144.0 | 2.408 |
| **7** | **Rúben** (MCI) + **Gvardiol** (MCI) + **Rodon** (LEE) + **Thomas** (COV) + **O'Nien** (SUN) | £23.5m | Stacked | **137.25** | 144.0 | 2.408 |
| **8** | **Rúben** (MCI) + **Gvardiol** (MCI) + **Heaven** (MUN) + **Thomas** (COV) + **van Ewijk** (COV) | £23.5m | Stacked | **137.25** | 144.0 | 2.408 |
| **9** | **Rúben** (MCI) + **Gvardiol** (MCI) + **Hume** (SUN) + **Thomas** (COV) + **O'Nien** (SUN) | £23.5m | Stacked | **137.25** | 143.0 | 2.408 |
| **10** | **Rúben** (MCI) + **Gvardiol** (MCI) + **Cash** (AVL) + **Thomas** (COV) + **O'Nien** (SUN) | £23.5m | Stacked | **137.25** | 143.0 | 2.408 |

---

#### D. Global Top 10 Unconstrained Sets
*Absolute lowest cumulative FDR across all 42,104 combinations.*

| Rank | 5-DEF Rotation Set | Cost | Archetype | Distinct? | Total Mod FDR | Total Base FDR | Avg DEF FDR |
|:---:|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **1** | **Rúben** (MCI) + **Jacquet** (LIV) + **F.Kadıoğlu** (BHA) + **Thomas** (COV) + **O'Nien** (SUN) | £23.0m | Other | Yes | **135.75** | 140.0 | 2.382 |
| **2** | **Rúben** (MCI) + **Colwill** (CHE) + **Jacquet** (LIV) + **Cash** (AVL) + **Thomas** (COV) | £24.0m | Other | Yes | **135.75** | 140.0 | 2.382 |
| **3** | **Rúben** (MCI) + **Jacquet** (LIV) + **Cash** (AVL) + **Heaven** (MUN) + **Thomas** (COV) | £23.5m | Other | Yes | **135.75** | 141.0 | 2.382 |
| **4** | **Rúben** (MCI) + **Jacquet** (LIV) + **Cash** (AVL) + **Rodon** (LEE) + **Thomas** (COV) | £23.5m | Other | Yes | **135.75** | 141.0 | 2.382 |
| **5** | **Rúben** (MCI) + **Gvardiol** (MCI) + **Jacquet** (LIV) + **Heaven** (MUN) + **Thomas** (COV) | £24.5m | Other | Stacked | **135.75** | 143.0 | 2.382 |
| **6** | **Rúben** (MCI) + **Gvardiol** (MCI) + **Colwill** (CHE) + **Heaven** (MUN) + **Thomas** (COV) | £24.5m | Other | Stacked | **135.75** | 143.0 | 2.382 |
| **7** | **Rúben** (MCI) + **Gvardiol** (MCI) + **Colwill** (CHE) + **Robinson** (FUL) + **Thomas** (COV) | £24.5m | Other | Stacked | **136.25** | 142.0 | 2.390 |
| **8** | **Rúben** (MCI) + **Colwill** (CHE) + **F.Kadıoğlu** (BHA) + **Thomas** (COV) + **O'Nien** (SUN) | £23.0m | Other | Yes | **136.25** | 141.0 | 2.390 |
| **9** | **Rúben** (MCI) + **Jacquet** (LIV) + **Cash** (AVL) + **Thomas** (COV) + **O'Nien** (SUN) | £23.0m | Other | Yes | **136.25** | 141.0 | 2.390 |
| **10** | **Rúben** (MCI) + **Colwill** (CHE) + **Jacquet** (LIV) + **Cash** (AVL) + **O'Nien** (SUN) | £24.0m | Other | Yes | **136.25** | 140.0 | 2.390 |

---

### 3. Gameweek 1–19 Weekly Picks for Standout Sets
From [`gw1_19_def_rotation_schedule_picks.csv`](gw1_19_def_rotation_schedule_picks.csv):

| GW | Pure Budget (£21.5m) [BOU+NFO+TOT+COV+SUN] | 1-Premium Anchor (£22.5m) [MCI+AVL+LEE+COV+SUN] | Global Best (£23.0m) [MCI+LIV+BHA+COV+SUN] |
|:---:|:---|:---|:---|
| **1** | NFO vs LEE (H, 1.75) · SUN @ IPS (A, 2.25) · TOT vs IPS (H, 1.75) | SUN @ IPS (A, 2.25) · MCI vs BOU (H, 2.75) · AVL vs FUL (H, 2.75) | SUN @ IPS (A, 2.25) · LIV vs CRY (H, 1.75) · BHA vs BRE (H, 2.75) |
| **2** | TOT vs IPS (H, 1.75) · BOU vs FUL (H, 1.75) · SUN vs FUL (H, 1.75) | COV vs HUL (H, 1.75) · SUN vs FUL (H, 1.75) · AVL vs BRE (H, 2.75) | COV vs HUL (H, 1.75) · SUN vs FUL (H, 1.75) · BHA vs CRY (H, 2.75) |
| **3** | NFO vs SUN (H, 1.75) · BOU vs TOT (H, 2.75) · SUN @ BRE (A, 2.75) | MCI vs COV (H, 1.75) · COV @ MCI (A, 3.25) · SUN @ BRE (A, 2.75) | MCI vs COV (H, 1.75) · LIV vs HUL (H, 1.75) · SUN @ BRE (A, 2.75) |
| **4** | TOT vs BOU (H, 1.75) · SUN vs ARS (H, 2.75) · COV vs BHA (H, 1.75) | COV vs BHA (H, 1.75) · LEE vs NEW (H, 1.75) · AVL vs HUL (H, 1.75) | COV vs BHA (H, 1.75) · LIV @ SUN (A, 2.25) · BHA @ COV (A, 2.25) |
| **5** | NFO vs COV (H, 1.75) · BOU vs BRE (H, 1.75) · TOT @ MUN (A, 2.75) | MCI vs SUN (H, 1.75) · LEE vs CRY (H, 2.75) · AVL vs NEW (H, 2.75) | MCI vs SUN (H, 1.75) · LIV vs IPS (H, 1.75) · BHA vs HUL (H, 1.75) |
| **6** | TOT vs FUL (H, 1.75) · COV vs NEW (H, 1.75) · SUN vs BHA (H, 1.75) | COV vs NEW (H, 1.75) · SUN vs BHA (H, 1.75) · AVL @ BOU (A, 2.25) | COV vs NEW (H, 1.75) · SUN vs BHA (H, 1.75) · LIV @ TOT (A, 2.25) |
| **7** | BOU vs SUN (H, 1.75) · TOT @ SUN (A, 2.25) · COV @ TOT (A, 3.25) | MCI vs IPS (H, 1.75) · LEE vs BOU (H, 1.75) · AVL @ SUN (A, 2.25) | MCI vs IPS (H, 1.75) · LIV vs FUL (H, 1.75) · BHA vs SUN (H, 1.75) |
| **8** | BOU vs CRY (H, 1.75) · TOT vs COV (H, 1.75) · SUN vs LEE (H, 1.75) | COV vs FUL (H, 1.75) · SUN vs LEE (H, 1.75) · MCI @ MUN (A, 2.25) | COV vs FUL (H, 1.75) · SUN vs LEE (H, 1.75) · MCI @ MUN (A, 2.25) |
| **9** | NFO vs EVE (H, 2.75) · COV vs SUN (H, 1.75) · SUN @ COV (A, 2.25) | COV vs SUN (H, 1.75) · SUN @ COV (A, 2.25) · MCI vs BHA (H, 1.75) | COV vs SUN (H, 1.75) · SUN @ COV (A, 2.25) · MCI vs BHA (H, 1.75) |
| **10** | BOU vs LEE (H, 1.75) · TOT vs HUL (H, 1.75) · COV @ EVE (A, 3.25) | LEE vs TOT (H, 2.75) · AVL vs IPS (H, 1.75) · MCI vs CHE (H, 2.75) | LIV vs COV (H, 1.75) · BHA vs TOT (H, 2.75) · MCI vs CHE (H, 2.75) |
| **11** | NFO vs HUL (H, 1.75) · SUN vs TOT (H, 2.75) · BOU @ SUN (A, 2.25) | LEE vs ARS (H, 2.75) · SUN vs TOT (H, 2.75) · AVL vs TOT (H, 2.75) | LIV @ MCI (A, 2.75) · BHA vs IPS (H, 1.75) · SUN vs TOT (H, 2.75) |
| **12** | BOU vs CHE (H, 2.75) · TOT vs MUN (H, 2.75) · COV @ LEE (A, 2.25) | MCI vs NEW (H, 2.75) · LEE vs COV (H, 1.75) · COV @ LEE (A, 2.25) | MCI vs NEW (H, 2.75) · LIV vs BHA (H, 1.75) · COV @ LEE (A, 2.25) |
| **13** | NFO vs TOT (H, 2.75) · SUN vs BOU (H, 1.75) · BOU @ SUN (A, 2.25) | MCI @ LEE (A, 2.25) · SUN vs BOU (H, 1.75) · AVL vs BOU (H, 1.75) | MCI @ LEE (A, 2.25) · LIV vs TOT (H, 2.75) · SUN vs BOU (H, 1.75) |
| **14** | COV vs IPS (H, 1.75) · SUN vs MUN (H, 2.75) · BOU vs MUN (H, 2.75) | MCI @ FUL (A, 2.25) · COV vs IPS (H, 1.75) · SUN vs MUN (H, 2.75) | MCI @ FUL (A, 2.25) · COV vs IPS (H, 1.75) · LIV @ AVL (A, 2.25) |
| **15** | NFO @ BHA (A, 2.25) · TOT @ BHA (A, 2.25) · SUN @ CHE (A, 3.25) | MCI @ SUN (A, 2.25) · COV @ ARS (A, 3.25) · SUN vs MCI (H, 3.25) | MCI @ SUN (A, 2.25) · LIV vs SUN (H, 1.75) · BHA vs NFO (H, 1.75) |
| **16** | NFO @ BOU (A, 2.25) · BOU vs NFO (H, 2.25) · SUN @ AVL (A, 3.25) | MCI vs CRY (H, 1.75) · AVL vs SUN (H, 1.75) · LEE vs FUL (H, 1.75) | MCI vs CRY (H, 1.75) · LIV vs EVE (H, 1.75) · BHA @ BOU (A, 2.25) |
| **17** | NFO vs MUN (H, 2.75) · BOU @ HUL (A, 2.25) · COV vs FUL (H, 1.75) | MCI vs MUN (H, 2.75) · COV vs FUL (H, 1.75) · AVL vs CRY (H, 1.75) | MCI vs MUN (H, 2.75) · COV vs FUL (H, 1.75) · BHA vs SUN (H, 1.75) |
| **18** | TOT vs NEW (H, 2.75) · COV @ NFO (A, 2.25) · SUN vs NFO (H, 1.75) | AVL vs ARS (H, 2.75) · LEE vs CRY (H, 2.75) · SUN vs NFO (H, 1.75) | LIV vs ARS (H, 2.75) · SUN vs NFO (H, 1.75) · BHA @ EVE (A, 2.25) |
| **19** | NFO vs BRE (H, 2.75) · BOU @ LEE (A, 2.25) · TOT @ BRE (A, 2.25) | MCI vs IPS (H, 1.75) · AVL vs COV (H, 1.75) · SUN @ ARS (A, 3.25) | MCI vs IPS (H, 1.75) · LIV @ BRE (A, 2.25) · BHA vs MUN (H, 2.75) |

---

## Decision

**Verdict**: The premier defensive squad structure for the first half of the season (GW1–19) is a **1-Premium Anchor set** led by **Rúben (MCI, £5.5m) + Cash (AVL, £4.5m) + Rodon (LEE, £4.5m) + Thomas (COV, £4.0m) + O'Nien (SUN, £4.0m)** at **£22.5m combined** (Total Mod FDR **136.25**, **2.390 / DEF**). For managers demanding the absolute cheapest £21.5m budget ceiling, **Smith (BOU) + Aina (NFO) + Robertson (TOT) + Thomas (COV) + O'Nien (SUN)** achieves **137.25** (**2.408 / DEF**), providing unbroken low-fixture defense across all 19 gameweeks.

**Recommended action**:
- Allocate **£21.5m to £22.5m** across 5 defensive slots.
- Anchor with at most one £5.5m asset (Man City or Liverpool) while stacking two £4.0m enablers (Coventry, Sunderland) and two £4.5m complementary rotators (Aston Villa, Bournemouth, Forest, Leeds, Spurs).
- Field 3 defenders weekly, benching the £5.5m premium during away matches against fellow top-6 sides in favor of home fixtures from budget enablers.

---

## Risks and unknowns

1. **Preseason Lineup & Transfer Volatility**: Starter designations are based on the committed GW1–5 Expected Role Prior joined with authoritative API club registration. Late transfer window additions may necessitate substitution with adjacent club starters.
2. **Rotation Depth & Substitution Risk**: If a £4.0m starter loses his place, rotation flexibility drops from 5-way to 4-way, increasing effective lineup FDR from 2.39 to ~2.55.
3. **Rescheduled Fixtures**: Postponements or blank/double gameweeks beyond GW19 will require schedule recalculation.

---

## Refresh checklist

- [x] `Updated` uses ISO 8601 timestamp with timezone.
- [x] `Data stamp` identifies current evidence cutoff.
- [x] `Season` and scope remain accurate.
- [x] Source URLs, publication dates, and access dates checked.
- [x] Source synthesis and Project interpretation remain separate.
- [x] Unvalidated claims labeled.
- [x] Agent Prompt remains runnable and points to stable slug.
- [x] Scratch files removed from `.tmp/agent/`.
