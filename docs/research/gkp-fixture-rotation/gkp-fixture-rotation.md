# Starter Goalkeeper Fixture Rotation & FDR Correlation Study

**Updated**: 2026-08-03T11:02:00+07:00  
**Data stamp**: FPL API processed snapshot + `expected-role-gw1-5.csv` domain audit + Points-Heavy RQI Recalibration  
**Season**: 2026/27  
**Purpose**: Identify pairs of **genuine starting goalkeepers** (Nailed Starter or Regular Starter in `expected-role-gw1-5.csv`) costing <= £9.5m combined with the highest total rotated expected points, negative FDR correlation, and lowest rotated average FDR to enable weekly fixture swapping.  
**Sources**: `data/processed/fixtures.parquet`, `data/processed/players.parquet`, `data/processed/clubs.parquet`, `data/research/expected-role-gw1-5/expected-role-gw1-5.csv`, `data/research/gw1-6-chip-wc4-squads/gw1-6_projections.csv`  
**Artifact**: [`gkp_rotation_matrix.csv`](../../../data/research/gkp-fixture-rotation/gkp_rotation_matrix.csv)  
**Script**: [`run_gkp_rotation_analysis.py`](run_gkp_rotation_analysis.py)  

---

## Agent Prompt & Risk Audit

Evaluate all genuine starter goalkeeper pairs (Nailed Starter or Regular Starter in `expected-role-gw1-5.csv`) from different clubs with a total combined cost <= £9.5m. Compute weekly Fixture Difficulty Rating (FDR) Pearson correlations, rotated effective FDR values, and total rotated expected points ($\text{tot\_rot\_xp}$) across multiple planning horizons (GW1–6, GW1–10, GW1–19, Full Season GW1–38). Exclude backup/rotation keepers (£4.0m non-playing bench fodder like Dubravka, Palmer, Steele, Dovin). Tag newly promoted team keepers (Wilson/COV, Butland/HUL) with `⚠️ Promoted Proxy` due to external data uncertainty. Present both overall and PL-proven top 10 rotation pairs.

---

## Starter Goalkeeper Filter & Baseline Metrics

To execute a **true active 2-keeper fixture rotation**, both goalkeepers in the pair must be genuine starters for their respective clubs. Non-playing £4.0m backup goalkeepers (e.g. Dubravka at Spurs, Steele at Brighton, Dovin at Coventry, Palmer at Ipswich) are excluded from the rotation candidate pool.

### Genuine Starting Goalkeepers (£4.5m–£5.5m)
* **£4.5m Starters**: Verbruggen (BHA, Nailed), Petrović (BOU, Nailed), Leno (FUL, Nailed), Kinsky (TOT, Regular), Wilson (COV, Regular, ⚠️ Promoted Proxy), Butland (HUL, Regular, ⚠️ Promoted Proxy).
* **£5.0m Starters**: Sels (NFO, Nailed), Lammens (MUN, Nailed), Roefs (SUN, Nailed), Martinez (AVL, Nailed), Kelleher (BRE, Nailed), Henderson (CRY, Nailed), Pope (NEW, Regular), Sánchez (CHE, Nailed).
* **£5.5m Starters**: Pickford (EVE, Nailed), Donnarumma (MCI, Nailed), A. Becker (LIV, Nailed).

### Goalkeeper Performance Baseline (Per 90 Clean Sheets & xGC)

| Goalkeeper | Club | Price | Expected Role | Total CS | CS / 90 | GC / 90 | xGC / 90 | Total xGC | Minutes | Data Source / Note |
|---|---|---|---|---|---|---|---|---|---|---|
| **Raya** | ARS | £6.0m | Nailed Starter | 19 | **0.5135** | 0.7027 | **0.7625** | 27.56 | 3,330m | 50% 2025/26 + 50% older mean |
| **Donnarumma** | MCI | £5.5m | Nailed Starter | 15 | **0.4412** | 0.8529 | **0.8529** | 38.50 | 3,060m | 100% 2025/26 |
| **A. Becker** | LIV | £5.5m | Nailed Starter | 8 | **0.3077** | 1.1923 | **1.1242** | 29.58 | 2,340m | 50% 2025/26 + 50% older mean |
| **Henderson** | CRY | £5.0m | Nailed Starter | 11 | **0.2973** | 1.3784 | **1.4414** | 51.40 | 3,330m | 50% 2025/26 + 50% older mean |
| **Petrović** | BOU | £4.5m | Nailed Starter | 11 | **0.2895** | 1.4211 | **1.5716** | 56.72 | 3,420m | 50% 2025/26 + 50% older mean |
| **Pickford** | EVE | £5.5m | Nailed Starter | 11 | **0.2895** | 1.3158 | **1.2829** | 56.24 | 3,420m | 50% 2025/26 + 50% older mean |
| **Roefs** | SUN | £5.0m | Nailed Starter | 10 | **0.2857** | 1.3143 | **1.3143** | 50.05 | 3,150m | 100% 2025/26 |
| **Kinsky** | TOT | £4.5m | Regular Starter | 2 | **0.2857** | 1.0000 | **1.4167** | 5.55 | 630m | 50% 2025/26 + 50% older mean |
| **Kelleher** | BRE | £5.0m | Nailed Starter | 10 | **0.2703** | 1.3243 | **1.2372** | 53.48 | 3,330m | 50% 2025/26 + 50% older mean |
| **Sánchez** | CHE | £5.0m | Nailed Starter | 9 | **0.2664** | 1.4507 | **1.3835** | 48.64 | 3,040m | 50% 2025/26 + 50% older mean |
| **Verbruggen** | BHA | £4.5m | Nailed Starter | 10 | **0.2632** | 1.2105 | **1.3414** | 49.06 | 3,420m | 50% 2025/26 + 50% older mean |
| **Pope** | NEW | £5.0m | Regular Starter | 7 | **0.2608** | 1.4156 | **1.2879** | 32.89 | 2,416m | 50% 2025/26 + 50% older mean |
| **Lammens** | MUN | £5.0m | Nailed Starter | 8 | **0.2500** | 1.2188 | **1.2188** | 39.25 | 2,880m | 100% 2025/26 |
| **Leno** | FUL | £4.5m | Nailed Starter | 9 | **0.2368** | 1.3421 | **1.4276** | 52.73 | 3,420m | 50% 2025/26 + 50% older mean |
| **Sels** | NFO | £5.0m | Nailed Starter | 7 | **0.2362** | 1.3161 | **1.3825** | 45.12 | 2,667m | 50% 2025/26 + 50% older mean |
| **Martinez** | AVL | £5.0m | Nailed Starter | 7 | **0.2222** | 1.2381 | **1.3082** | 42.92 | 2,835m | 50% 2025/26 + 50% older mean |
| **Butland** | HUL | £4.5m | Regular Starter | 0 | **0.0000\*** | 1.0100 | **1.0100** | 0.00 | 0m | External Rangers SPFL proxy |
| **Wilson** | COV | £4.5m | Regular Starter | 0 | **0.0000\*** | 1.0700 | **1.0700** | 0.00 | 0m | External Coventry Championship proxy |

*\*Note: Newly promoted goalkeepers Butland and Wilson have 0 Premier League minutes in the processed FPL dataset; their expected goals conceded per 90 (xGC / 90) rates of 1.0100 and 1.0700 are derived from domain proxy data.*

---

## Method & RQI Formula Recalibration

1. **Goalkeeper Selection**: Filtered strictly for `Nailed Starter` or `Regular Starter` in `expected-role-gw1-5.csv`.
2. **FDR Matrix Construction**: Built a Club × Gameweek matrix containing weekly defense FDR ratings (1 = easiest, 5 = hardest).
3. **Points-Heavy Rotation Quality Index (RQI)**:
   - Evaluates total rotated points ($\text{tot\_rot\_xp}$) rather than relative gain ($\Delta xP$), preventing volatile lower-tier keepers from artificially dominating scores.
   - Component weights: **40% Total Rotated Points**, **20% Rotated FDR Ease**, **20% FDR Pearson Correlation**, **10% Easy GWs ($\le 2$)**, **10% Budget Efficiency**:
     $$\text{RQI} = 0.40 \cdot S_{\text{tot\_xp}} + 0.20 \cdot S_{\text{fdr}} + 0.20 \cdot S_{\text{corr}} + 0.10 \cdot S_{\text{easy}} + 0.10 \cdot S_{\text{cost}}$$

---

## Findings

### 1. GW1–6 Early Season Peak Rotation Pairs

#### **1.1 GW1–6 Top 10 Overall Pairs**
*🔥 **£9.0m** indicates double £4.5m budget tier. `⚠️ Promoted Proxy` indicates external Championship/SPFL data source.*

| Rank | GKP 1 (Club, Price) | GKP 1 Baseline (CS/90 \| GC/90 \| xGC/90) | GKP 2 (Club, Price) | GKP 2 Baseline (CS/90 \| GC/90 \| xGC/90) | Total Price | RQI Score | GW1–6 Rotated $xP$ | FDR Corr ($r$) | Rot Avg FDR | Easy GWs ($\le 2$) |
|---|---|---|---|---|---|---|---|---|---|---|
| **1** | **Verbruggen** (BHA £4.5m) | 0.263 \| 1.211 \| 1.341 | **Lammens** (MUN £5.0m) | 0.250 \| 1.219 \| 1.219 | **£9.5m** | **81.14 / 100** | **23.48 $xP$** | **-0.5941** | **2.33** | 4 / 6 (66.7%) |
| **2** | **Wilson** (COV £4.5m) | 0.000* \| 1.070 \| 1.070 | **Sels** (NFO £5.0m) | 0.236 \| 1.316 \| 1.383 | **£9.5m** ⚠️ | **79.27 / 100** | **22.26 $xP$** | **-0.6076** | **2.17** | 5 / 6 (83.3%) |
| **3** | **Verbruggen** (BHA £4.5m) | 0.263 \| 1.211 \| 1.341 | **Roefs** (SUN £5.0m) | 0.286 \| 1.314 \| 1.314 | **£9.5m** | **77.10 / 100** | **23.54 $xP$** | **0.0000** | **2.33** | 5 / 6 (83.3%) |
| **4** | **Martinez** (AVL £5.0m) | 0.222 \| 1.238 \| 1.308 | **Wilson** (COV £4.5m) | 0.000* \| 1.070 \| 1.070 | **£9.5m** ⚠️ | **75.10 / 100** | **21.81 $xP$** | **-0.6445** | **2.33** | 4 / 6 (66.7%) |
| **5** | **Wilson** (COV £4.5m) | 0.000* \| 1.070 \| 1.070 | **Lammens** (MUN £5.0m) | 0.250 \| 1.219 \| 1.219 | **£9.5m** ⚠️ | **74.59 / 100** | **22.48 $xP$** | **-0.3309** | **2.33** | 4 / 6 (66.7%) |
| **6** | **Verbruggen** (BHA £4.5m) | 0.263 \| 1.211 \| 1.341 | **Butland** (HUL £4.5m) | 0.000* \| 1.010 \| 1.010 | 🔥 **£9.0m** ⚠️ | **73.57 / 100** | **21.62 $xP$** | **-0.5941** | **2.50** | 3 / 6 (50.0%) |
| **7** | **Verbruggen** (BHA £4.5m) | 0.263 \| 1.211 \| 1.341 | **Wilson** (COV £4.5m) | 0.000* \| 1.070 \| 1.070 | 🔥 **£9.0m** ⚠️ | **73.44 / 100** | **21.62 $xP$** | **-0.3038** | **2.33** | 4 / 6 (66.7%) |
| **8** | **Wilson** (COV £4.5m) | 0.000* \| 1.070 \| 1.070 | **Roefs** (SUN £5.0m) | 0.286 \| 1.314 \| 1.314 | **£9.5m** ⚠️ | **72.90 / 100** | **22.62 $xP$** | **-0.1074** | **2.33** | 4 / 6 (66.7%) |
| **9** | **Kelleher** (BRE £5.0m) | 0.270 \| 1.324 \| 1.237 | **Wilson** (COV £4.5m) | 0.000* \| 1.070 \| 1.070 | **£9.5m** ⚠️ | **72.64 / 100** | **21.37 $xP$** | **-0.5716** | **2.33** | 4 / 6 (66.7%) |
| **10** | **Verbruggen** (BHA £4.5m) | 0.263 \| 1.211 \| 1.341 | **Sels** (NFO £5.0m) | 0.236 \| 1.316 \| 1.383 | **£9.5m** | **72.31 / 100** | **22.39 $xP$** | **-0.2500** | **2.50** | 4 / 6 (66.7%) |

#### **1.2 GW1–6 Top 10 PL-Proven Pairs (Excluding Promoted Proxies)**

| Rank | GKP 1 (Club, Price) | GKP 1 Baseline (CS/90 \| GC/90 \| xGC/90) | GKP 2 (Club, Price) | GKP 2 Baseline (CS/90 \| GC/90 \| xGC/90) | Total Price | RQI Score | GW1–6 Rotated $xP$ | FDR Corr ($r$) | Rot Avg FDR | Easy GWs ($\le 2$) |
|---|---|---|---|---|---|---|---|---|---|---|
| **1** | **Verbruggen** (BHA £4.5m) | 0.263 \| 1.211 \| 1.341 | **Lammens** (MUN £5.0m) | 0.250 \| 1.219 \| 1.219 | **£9.5m** | **81.14 / 100** | **23.48 $xP$** | **-0.5941** | **2.33** | 4 / 6 (66.7%) |
| **2** | **Verbruggen** (BHA £4.5m) | 0.263 \| 1.211 \| 1.341 | **Roefs** (SUN £5.0m) | 0.286 \| 1.314 \| 1.314 | **£9.5m** | **77.10 / 100** | **23.54 $xP$** | **0.0000** | **2.33** | 5 / 6 (83.3%) |
| **3** | **Verbruggen** (BHA £4.5m) | 0.263 \| 1.211 \| 1.341 | **Sels** (NFO £5.0m) | 0.236 \| 1.316 \| 1.383 | **£9.5m** | **72.31 / 100** | **22.39 $xP$** | **-0.2500** | **2.50** | 4 / 6 (66.7%) |
| **4** | **Verbruggen** (BHA £4.5m) | 0.263 \| 1.211 \| 1.341 | **Sánchez** (CHE £5.0m) | 0.266 \| 1.451 \| 1.383 | **£9.5m** | **71.64 / 100** | **22.24 $xP$** | **-0.4082** | **2.50** | 3 / 6 (50.0%) |
| **5** | **Verbruggen** (BHA £4.5m) | 0.263 \| 1.211 \| 1.341 | **Pope** (NEW £5.0m) | 0.261 \| 1.416 \| 1.288 | **£9.5m** | **71.58 / 100** | **21.80 $xP$** | **-0.2970** | **2.33** | 4 / 6 (66.7%) |
| **6** | **Sánchez** (CHE £5.0m) | 0.266 \| 1.451 \| 1.383 | **Leno** (FUL £4.5m) | 0.237 \| 1.342 \| 1.428 | **£9.5m** | **69.48 / 100** | **22.16 $xP$** | **-0.2236** | **2.50** | 3 / 6 (50.0%) |
| **7** | **Petrović** (BOU £4.5m) | 0.289 \| 1.421 \| 1.572 | **Sels** (NFO £5.0m) | 0.236 \| 1.316 \| 1.383 | **£9.5m** | **68.64 / 100** | **21.13 $xP$** | **-0.8216** | **2.67** | 2 / 6 (33.3%) |
| **8** | **Verbruggen** (BHA £4.5m) | 0.263 \| 1.211 \| 1.341 | **Kinsky** (TOT £4.5m) | 0.286 \| 1.000 \| 1.417 | 🔥 **£9.0m** | **67.99 / 100** | **20.81 $xP$** | **-0.3536** | **2.50** | 3 / 6 (50.0%) |
| **9** | **Petrović** (BOU £4.5m) | 0.289 \| 1.421 \| 1.572 | **Lammens** (MUN £5.0m) | 0.250 \| 1.219 \| 1.219 | **£9.5m** | **67.90 / 100** | **21.93 $xP$** | **-0.4339** | **2.67** | 2 / 6 (33.3%) |
| **10** | **Leno** (FUL £4.5m) | 0.237 \| 1.342 \| 1.428 | **Sels** (NFO £5.0m) | 0.236 \| 1.316 \| 1.383 | **£9.5m** | **66.72 / 100** | **21.61 $xP$** | **-0.2739** | **2.67** | 3 / 6 (50.0%) |

---

### 2. Full Season Horizon (GW1–38 Horizon Recalibrated RQI)

#### **2.1 Full Season Top 10 Overall Pairs**

| Rank | GKP 1 (Club, Price) | GKP 1 Baseline (CS/90 \| GC/90 \| xGC/90) | GKP 2 (Club, Price) | GKP 2 Baseline (CS/90 \| GC/90 \| xGC/90) | Total Price | RQI Score | Full Season Rotated $xP$ | FDR Corr ($r$) | Rot Avg FDR | Easy GWs ($\le 2$) |
|---|---|---|---|---|---|---|---|---|---|---|
| **1** | **Verbruggen** (BHA £4.5m) | 0.263 \| 1.211 \| 1.341 | **Lammens** (MUN £5.0m) | 0.250 \| 1.219 \| 1.219 | **£9.5m** | **77.12 / 100** | **23.48 $xP$** | **-0.4170** | **2.50** | 21 / 38 (55.3%) |
| **2** | **Verbruggen** (BHA £4.5m) | 0.263 \| 1.211 \| 1.341 | **Roefs** (SUN £5.0m) | 0.286 \| 1.314 \| 1.314 | **£9.5m** | **76.20 / 100** | **23.54 $xP$** | **-0.3451** | **2.53** | 20 / 38 (52.6%) |
| **3** | **Verbruggen** (BHA £4.5m) | 0.263 \| 1.211 \| 1.341 | **Butland** (HUL £4.5m) | 0.000* \| 1.010 \| 1.010 | 🔥 **£9.0m** ⚠️ | **71.34 / 100** | **21.62 $xP$** | **-0.4325** | **2.55** | 18 / 38 (47.4%) |
| **4** | **Verbruggen** (BHA £4.5m) | 0.263 \| 1.211 \| 1.341 | **Sels** (NFO £5.0m) | 0.236 \| 1.316 \| 1.383 | **£9.5m** | **70.12 / 100** | **22.39 $xP$** | **-0.1888** | **2.53** | 20 / 38 (52.6%) |
| **5** | **Petrović** (BOU £4.5m) | 0.289 \| 1.421 \| 1.572 | **Lammens** (MUN £5.0m) | 0.250 \| 1.219 \| 1.219 | **£9.5m** | **69.75 / 100** | **21.93 $xP$** | **-0.2971** | **2.47** | 20 / 38 (52.6%) |
| **6** | **Sánchez** (CHE £5.0m) | 0.266 \| 1.451 \| 1.383 | **Leno** (FUL £4.5m) | 0.237 \| 1.342 \| 1.428 | **£9.5m** | **69.61 / 100** | **22.16 $xP$** | **-0.2275** | **2.53** | 20 / 38 (52.6%) |
| **7** | **Wilson** (COV £4.5m) | 0.000* \| 1.070 \| 1.070 | **Lammens** (MUN £5.0m) | 0.250 \| 1.219 \| 1.219 | **£9.5m** ⚠️ | **69.56 / 100** | **22.48 $xP$** | **-0.1939** | **2.55** | 17 / 38 (44.7%) |
| **8** | **Wilson** (COV £4.5m) | 0.000* \| 1.070 \| 1.070 | **Sels** (NFO £5.0m) | 0.236 \| 1.316 \| 1.383 | **£9.5m** ⚠️ | **68.91 / 100** | **22.26 $xP$** | **-0.2325** | **2.58** | 17 / 38 (44.7%) |
| **9** | **Kinsky** (TOT £4.5m) | 0.286 \| 1.000 \| 1.417 | **Roefs** (SUN £5.0m) | 0.286 \| 1.314 \| 1.314 | **£9.5m** | **68.90 / 100** | **21.66 $xP$** | **-0.3352** | **2.50** | 20 / 38 (52.6%) |
| **10** | **Martinez** (AVL £5.0m) | 0.222 \| 1.238 \| 1.308 | **Leno** (FUL £4.5m) | 0.237 \| 1.342 \| 1.428 | **£9.5m** | **68.82 / 100** | **21.84 $xP$** | **-0.3007** | **2.53** | 19 / 38 (50.0%) |

#### **2.2 Full Season Top 10 PL-Proven Pairs (Excluding Promoted Proxies)**

| Rank | GKP 1 (Club, Price) | GKP 1 Baseline (CS/90 \| GC/90 \| xGC/90) | GKP 2 (Club, Price) | GKP 2 Baseline (CS/90 \| GC/90 \| xGC/90) | Total Price | RQI Score | Full Season Rotated $xP$ | FDR Corr ($r$) | Rot Avg FDR | Easy GWs ($\le 2$) |
|---|---|---|---|---|---|---|---|---|---|---|
| **1** | **Verbruggen** (BHA £4.5m) | 0.263 \| 1.211 \| 1.341 | **Lammens** (MUN £5.0m) | 0.250 \| 1.219 \| 1.219 | **£9.5m** | **77.12 / 100** | **23.48 $xP$** | **-0.4170** | **2.50** | 21 / 38 (55.3%) |
| **2** | **Verbruggen** (BHA £4.5m) | 0.263 \| 1.211 \| 1.341 | **Roefs** (SUN £5.0m) | 0.286 \| 1.314 \| 1.314 | **£9.5m** | **76.20 / 100** | **23.54 $xP$** | **-0.3451** | **2.53** | 20 / 38 (52.6%) |
| **3** | **Verbruggen** (BHA £4.5m) | 0.263 \| 1.211 \| 1.341 | **Sels** (NFO £5.0m) | 0.236 \| 1.316 \| 1.383 | **£9.5m** | **70.12 / 100** | **22.39 $xP$** | **-0.1888** | **2.53** | 20 / 38 (52.6%) |
| **4** | **Petrović** (BOU £4.5m) | 0.289 \| 1.421 \| 1.572 | **Lammens** (MUN £5.0m) | 0.250 \| 1.219 \| 1.219 | **£9.5m** | **69.75 / 100** | **21.93 $xP$** | **-0.2971** | **2.47** | 20 / 38 (52.6%) |
| **5** | **Sánchez** (CHE £5.0m) | 0.266 \| 1.451 \| 1.383 | **Leno** (FUL £4.5m) | 0.237 \| 1.342 \| 1.428 | **£9.5m** | **69.61 / 100** | **22.16 $xP$** | **-0.2275** | **2.53** | 20 / 38 (52.6%) |
| **6** | **Kinsky** (TOT £4.5m) | 0.286 \| 1.000 \| 1.417 | **Roefs** (SUN £5.0m) | 0.286 \| 1.314 \| 1.314 | **£9.5m** | **68.90 / 100** | **21.66 $xP$** | **-0.3352** | **2.50** | 20 / 38 (52.6%) |
| **7** | **Martinez** (AVL £5.0m) | 0.222 \| 1.238 \| 1.308 | **Leno** (FUL £4.5m) | 0.237 \| 1.342 \| 1.428 | **£9.5m** | **68.82 / 100** | **21.84 $xP$** | **-0.3007** | **2.53** | 19 / 38 (50.0%) |
| **8** | **Sels** (NFO £5.0m) | 0.236 \| 1.316 \| 1.383 | **Kinsky** (TOT £4.5m) | 0.286 \| 1.000 \| 1.417 | **£9.5m** | **67.31 / 100** | **21.05 $xP$** | **-0.3981** | **2.47** | 20 / 38 (52.6%) |
| **9** | **Petrović** (BOU £4.5m) | 0.289 \| 1.421 \| 1.572 | **Sels** (NFO £5.0m) | 0.236 \| 1.316 \| 1.383 | **£9.5m** | **67.27 / 100** | **21.13 $xP$** | **-0.3623** | **2.47** | 20 / 38 (52.6%) |
| **10** | **Verbruggen** (BHA £4.5m) | 0.263 \| 1.211 \| 1.341 | **Sánchez** (CHE £5.0m) | 0.266 \| 1.451 \| 1.383 | **£9.5m** | **66.89 / 100** | **22.24 $xP$** | **-0.0379** | **2.58** | 17 / 38 (44.7%) |

---

### 3. Top Pairings by Budget Tier & Risk Category

#### **Tier A: Premier League Proven Rotation Pairs (£9.5m)**
- **Verbruggen (BHA £4.5m) + Lammens (MUN £5.0m)**: **Absolute #1 Overall Pair** (**RQI 81.14** in GW1–6; **77.12** full season). Combines top 6GW total points (**23.48 $xP$**) with strong negative correlation ($r = -0.5941$).
- **Verbruggen (BHA £4.5m) + Roefs (SUN £5.0m)**: **Highest Points Output Pair** (**23.54 $xP$** over GW1–6; **RQI 77.10** GW1–6; **76.20** full season).

#### **Tier B: £9.0m Budget Pairs (Double £4.5m)**
- **Verbruggen (BHA £4.5m) + Kinsky (TOT £4.5m)**: Top **PL-Proven £9.0m pair** (**RQI 67.99** in GW1–6). Rotated $xP$ reaches **20.81 $xP$** with $r = -0.3536$.
- **Verbruggen (BHA £4.5m) + Butland (HUL £4.5m)**: Top overall £9.0m pair (**RQI 73.57** GW1–6; **71.34** full season), but tagged with `⚠️ Promoted Proxy`.

---

## Decision & Practical Recommendation

1. **For Risk-Averse Managers (£9.5m Budget)**: Select **Verbruggen (£4.5m, BHA)** + **Lammens (£5.0m, MUN)** (**RQI 81.14**) or **Verbruggen (£4.5m, BHA)** + **Roefs (£5.0m, SUN)** (**RQI 77.10**). Both pairs provide PL-proven defensive foundations with top expected points output.
2. **For Budget-Constrained Managers (£9.0m Budget)**: Select **Verbruggen (£4.5m, BHA)** + **Kinsky (£4.5m, TOT)** (**RQI 67.99**, PL-Proven), or **Verbruggen (£4.5m, BHA)** + **Butland (£4.5m, HUL)** (**RQI 73.57**, ⚠️ Promoted Proxy).
3. **Avoid Unproven Promoted Pairs as Primary Strategy**: Keepers like Wilson (Coventry) have spiky Championship proxy projections that create high FDR gains, but carry unproven Premier League clean sheet risk.
