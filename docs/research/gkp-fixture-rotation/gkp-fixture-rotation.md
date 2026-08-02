# Starter Goalkeeper Fixture Rotation & FDR Correlation Study

**Updated**: 2026-08-03T04:57:00+07:00  
**Data stamp**: FPL API processed snapshot + `expected-role-gw1-5.csv` domain audit  
**Season**: 2026/27  
**Purpose**: Identify pairs of **genuine starting goalkeepers** (Nailed Starter or Regular Starter in `expected-role-gw1-5.csv`) costing <= £9.5m combined with the highest negative FDR correlation and lowest rotated average FDR to enable weekly fixture swapping.  
**Sources**: `data/processed/fixtures.parquet`, `data/processed/players.parquet`, `data/processed/clubs.parquet`, `data/research/expected-role-gw1-5/expected-role-gw1-5.csv`  
**Artifact**: [`gkp_rotation_matrix.csv`](../../../data/research/gkp-fixture-rotation/gkp_rotation_matrix.csv)  
**Script**: [`run_gkp_rotation_analysis.py`](run_gkp_rotation_analysis.py)  

---

## Agent Prompt

Evaluate all genuine starter goalkeeper pairs (Nailed Starter or Regular Starter in `expected-role-gw1-5.csv`) from different clubs with a total combined cost <= £9.5m. Compute weekly Fixture Difficulty Rating (FDR) Pearson correlations and rotated effective FDR values across multiple planning horizons (GW1–6, GW1–10, GW1–19, Full Season GW1–38). Exclude backup/rotation keepers (£4.0m non-playing bench fodder like Dubravka, Palmer, Steele, Dovin) who do not feature regularly. Present top complementary rotation pairs by budget tier.

---

## Starter Goalkeeper Filter

To execute a **true active 2-keeper fixture rotation**, both goalkeepers in the pair must be genuine starters for their respective clubs. Non-playing £4.0m backup goalkeepers (e.g. Dubravka at Spurs, Steele at Brighton, Dovin at Coventry, Palmer at Ipswich) are excluded from the rotation candidate pool because they do not offer playing minutes when rotated on to the pitch.

### Genuine Starting Goalkeepers (£4.5m–£5.5m)
* **£4.5m Starters**: Verbruggen (BHA, Nailed), Petrović (BOU, Nailed), Leno (FUL, Nailed), Kinsky (TOT, Regular), Wilson (COV, Regular), Butland (HUL, Regular).
* **£5.0m Starters**: Sels (NFO, Nailed), Lammens (MUN, Nailed), Roefs (SUN, Nailed), Martinez (AVL, Nailed), Kelleher (BRE, Nailed), Henderson (CRY, Nailed), Pope (NEW, Regular), Sánchez (CHE, Nailed).
* **£5.5m Starters**: Pickford (EVE, Nailed), Donnarumma (MCI, Nailed), A. Becker (LIV, Nailed).

---

## Method

1. **Goalkeeper Selection**: Filtered strictly for `Nailed Starter` or `Regular Starter` in `expected-role-gw1-5.csv`.
2. **FDR Matrix Construction**: Built a Club × Gameweek matrix containing weekly defense FDR ratings (1 = easiest, 5 = hardest).
3. **Correlation & Rotation Metrics**:
   - **FDR Correlation ($r$)**: Pearson correlation coefficient between the two clubs' weekly FDR sequences. Strong negative correlation ($r < -0.30$) indicates when one keeper has a tough fixture, the other has an easy fixture.
   - **Rotated Average FDR**: Average of $\min(\text{FDR}_1, \text{FDR}_2)$ across all gameweeks in the horizon.
   - **FDR Gain**: Difference between the best single keeper's unrotated average FDR and the rotated pair's average FDR.
   - **Easy Gameweeks**: Number of gameweeks in which the rotated pair provides an FDR $\le 2$ fixture.

---

## Findings

### 1. Overall Top Genuine Rotation Pairs (Full Season GW1–38)

| GKP 1 (Club, Role, Price) | GKP 2 (Club, Role, Price) | Total Price | FDR Corr ($r$) | Rotated Avg FDR | FDR Gain | Easy GWs ($\le 2$) |
|---|---|---|---|---|---|---|
| **Verbruggen** (BHA, Nailed, £4.5m) | **Butland** (HUL, Regular, £4.5m) | **£9.0m** | **-0.4325** | **2.5526** | +0.45 | 18 / 38 (47%) |
| **Verbruggen** (BHA, Nailed, £4.5m) | **Lammens** (MUN, Nailed, £5.0m) | **£9.5m** | **-0.4170** | **2.5000** | +0.50 | 21 / 38 (55%) |
| **Sels** (NFO, Nailed, £5.0m) | **Kinsky** (TOT, Regular, £4.5m) | **£9.5m** | **-0.3981** | **2.4737** | +0.58 | 20 / 38 (53%) |
| **Petrović** (BOU, Nailed, £4.5m) | **Sels** (NFO, Nailed, £5.0m) | **£9.5m** | **-0.3623** | **2.4737** | +0.58 | 20 / 38 (53%) |
| **Verbruggen** (BHA, Nailed, £4.5m) | **Roefs** (SUN, Nailed, £5.0m) | **£9.5m** | **-0.3451** | **2.5263** | +0.55 | 20 / 38 (53%) |
| **Kinsky** (TOT, Regular, £4.5m) | **Roefs** (SUN, Nailed, £5.0m) | **£9.5m** | **-0.3352** | **2.5000** | +0.55 | 20 / 38 (53%) |

---

### 2. Opening Horizon (GW1–10 Early Season Peak Correlation)

| Rank | Genuine Starter Pair | Total Price | GW1-10 FDR Corr | Rotated Avg FDR | Easy GWs (FDR $\le 2$) |
|---|---|---|---|---|---|
| 1 | **Petrović** (BOU £4.5m) + **Sels** (NFO £5.0m) | **£9.5m** | **-0.7618** | **2.40** | 6 / 10 |
| 2 | **Verbruggen** (BHA £4.5m) + **Butland** (HUL £4.5m) | **£9.0m** | **-0.5863** | **2.60** | 4 / 10 |
| 3 | **Sels** (NFO £5.0m) + **Kinsky** (TOT £4.5m) | **£9.5m** | **-0.5710** | **2.50** | 5 / 10 |
| 4 | **Henderson** (CRY £5.0m) + **Kinsky** (TOT £4.5m) | **£9.5m** | **-0.5000** | **2.60** | 4 / 10 |
| 5 | **Petrović** (BOU £4.5m) + **Lammens** (MUN £5.0m) | **£9.5m** | **-0.4841** | **2.50** | 5 / 10 |

---

### 3. Top Pairings by Budget Tier

#### **Tier A: £9.0m Budget (Two £4.5m Genuine Starters)**
- **Verbruggen (BHA £4.5m) + Butland (HUL £4.5m)**: Best overall £9.0m genuine starter pair. Full-season correlation **-0.4325** (GW1-10: **-0.5863**). Rotated average FDR of **2.55**.
- **Verbruggen (BHA £4.5m) + Wilson (COV £4.5m)**: GW1-10 correlation **-0.4598**, rotated average FDR **2.40** (6 easy fixtures in GW1-10).
- **Leno (FUL £4.5m) + Kinsky (TOT £4.5m)**: Rotated average FDR of **2.47** over GW1–19.

#### **Tier B: £9.5m Budget (£5.0m + £4.5m Genuine Starters)**
- **Petrović (BOU £4.5m) + Sels (NFO £5.0m)**: Absolute #1 overall opening rotation pair. FDR correlation **-0.7618** (GW1-10) and **-0.8216** (GW1-6). Gives an FDR $\le 2$ fixture in 6 of first 10 gameweeks.
- **Verbruggen (BHA £4.5m) + Lammens (MUN £5.0m)**: Outstanding long-term rotation ($r = -0.4170$ full season). 21 easy fixtures (55% of full season).
- **Sels (NFO £5.0m) + Kinsky (TOT £4.5m)**: Most consistent long-term pair ($r = -0.3981$ full season, $r = -0.5710$ GW1-10). Rotated FDR **2.47**.
- **Kinsky (TOT £4.5m) + Roefs (SUN £5.0m)**: Strong first-half correlation ($r = -0.4148$ GW1-19). Rotated FDR **2.42**.

---

## Decision & Practical Recommendation

1. **If allocating £9.5m**: Select **Petrović (£4.5m, BOU)** + **Sels (£5.0m, NFO)** for the best early-season rotation, or **Verbruggen (£4.5m, BHA)** + **Lammens (£5.0m, MUN)** for full-season coverage.
2. **If allocating £9.0m**: Select **Verbruggen (£4.5m, BHA)** + **Butland (£4.5m, HUL)** or **Verbruggen (£4.5m, BHA)** + **Wilson (£4.5m, COV)**.
3. **Avoid £8.0m pseudo-rotations**: £4.0m keepers (Dubravka, Palmer, Dovin, Phillips, Steele) are non-playing backups and cannot be rotated actively on the pitch.

---

## Risks and Unknowns

- **Promoted Club Starter Performance**: Butland (Hull) and Wilson (Coventry) are starting keepers for promoted teams whose clean sheet volume may be lower despite easy FDR fixtures.
- **Manager Lineup Changes**: Pre-season friendly evidence should be rechecked before GW1 deadline to confirm Kinsky vs Vicario / Austin at Spurs.
