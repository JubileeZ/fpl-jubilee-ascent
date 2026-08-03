# Starter Goalkeeper Fixture Rotation & FDR Correlation Study

**Updated**: 2026-08-03T16:01:14+07:00  
**Data stamp**: FPL API processed snapshot + `expected-stats-gw1-5.csv` rates + ParticipationStateHybridModel GW1–38 flat-90 projections  
**Season**: 2026/27  
**Purpose**: Identify pairs of **genuine starting goalkeepers** (Nailed Starter or Regular Starter) costing <= £9.5m combined with the highest horizon-matched rotated expected points under FDR-min weekly picks, negative FDR correlation, and lowest rotated average FDR.  
**Sources**: `data/processed/fixtures.parquet`, `data/processed/players.parquet`, `data/processed/clubs.parquet`, `data/research/expected-role-gw1-5/expected-role-gw1-5.csv`, `data/research/expected-stats-gw1-5/expected-stats-gw1-5.csv`  
**Artifacts**: [`gkp_rotation_matrix.csv`](../../../data/research/gkp-fixture-rotation/gkp_rotation_matrix.csv), [`gkp_performance_baseline.csv`](../../../data/research/gkp-fixture-rotation/gkp_performance_baseline.csv)  
**Script**: [`run_gkp_rotation_analysis.py`](run_gkp_rotation_analysis.py)

---

## Agent Prompt & Risk Audit

Evaluate all genuine starter goalkeeper pairs (Nailed Starter or Regular Starter) from different clubs with combined cost <= £9.5m. Project weekly xP via `ParticipationStateHybridModel` over GW1–38 with **forced flat starter minutes** (p_start=1, xmins=90). Rank by Points-Heavy RQI using **horizon-matched** FDR-min rotated xP (not GW1–6 capped). Also report max(xP) upper bound. Tag promoted proxies (Wilson/COV, Butland/HUL). Present overall and PL-proven top 10 for GW1–6 and full season; matrix retains gw1_10 and gw1_19.

---

## Starter Goalkeeper Filter & Baseline Metrics

True active 2-keeper rotation requires both keepers to be genuine starters. Non-playing £4.0m backups excluded.

### Goalkeeper Performance Baseline (Scorer Rates)

Authority = `expected-stats-gw1-5.csv` inputs consumed by the hybrid scorer (`per90_saves`, `per90_goals_conceded`). Clean sheets are **derived** inside the model from GC λ × defence multiplier — not a separate CS/90 column. Historical CS/xGC display rates retired from this table.

| Goalkeeper | Club | Price | Expected Role | Saves / 90 | GC / 90 | Usable Mins | Data Source / Note |
|---|---|---|---|---|---|---|---|
| **Pope** | NEW | £5.0m | Regular Starter | **3.1627** | **1.2879** | 6281m | 50% 2025/26 (2416m) + 50% mean older usable [2023/24,2024/25] |
| **Petrović** | BOU | £4.5m | Nailed Starter | **3.1336** | **1.5716** | 5406m | 50% 2025/26 (3420m) + 50% mean older usable [2023/24] |
| **Roefs** | SUN | £5.0m | Nailed Starter | **3.1143** | **1.3143** | 3150m | 100% usable season 2025/26 (3150 mins) |
| **Sánchez** | CHE | £5.0m | Nailed Starter | **3.0250** | **1.3835** | 7353m | 50% 2025/26 (3040m) + 50% mean older usable [2023/24,2024/25] |
| **Sels** | NFO | £5.0m | Nailed Starter | **2.9705** | **1.3825** | 7527m | 50% 2025/26 (2667m) + 50% mean older usable [2023/24,2024/25] |
| **Henderson** | CRY | £5.0m | Nailed Starter | **2.9222** | **1.4414** | 8370m | 50% 2025/26 (3330m) + 50% mean older usable [2023/24,2024/25] |
| **Martinez** | AVL | £5.0m | Nailed Starter | **2.9211** | **1.3082** | 9045m | 50% 2025/26 (2835m) + 50% mean older usable [2023/24,2024/25] |
| **Pickford** | EVE | £5.5m | Nailed Starter | **2.9145** | **1.2829** | 10260m | 50% 2025/26 (3420m) + 50% mean older usable [2023/24,2024/25] |
| **Leno** | FUL | £4.5m | Nailed Starter | **2.8947** | **1.4276** | 10260m | 50% 2025/26 (3420m) + 50% mean older usable [2023/24,2024/25] |
| **Kelleher** | BRE | £5.0m | Nailed Starter | **2.8480** | **1.2372** | 5130m | 50% 2025/26 (3330m) + 50% mean older usable [2023/24,2024/25] |
| **Verbruggen** | BHA | £4.5m | Nailed Starter | **2.8005** | **1.3414** | 8550m | 50% 2025/26 (3420m) + 50% mean older usable [2023/24,2024/25] |
| **Kinsky** | TOT | £4.5m | Regular Starter | **2.7143** | **1.4167** | 1170m | 50% 2025/26 (630m) + 50% mean older usable [2024/25] |
| **A.Becker** | LIV | £5.5m | Nailed Starter | **2.5370** | **1.1242** | 7368m | 50% 2025/26 (2340m) + 50% mean older usable [2023/24,2024/25] |
| **Lammens** | MUN | £5.0m | Nailed Starter | **2.4688** | **1.2188** | 2880m | 100% usable season 2025/26 (2880 mins) |
| **Butland** ⚠️ | HUL | £4.5m | Regular Starter | **2.3330** | **1.0100** | 0m | External SPFL 2023-26: Jack Butland Rangers proxy (no Hull mins yet); mins~9180 |
| **Donnarumma** | MCI | £5.5m | Nailed Starter | **2.2941** | **0.8529** | 3060m | 100% usable season 2025/26 (3060 mins) |
| **Wilson** ⚠️ | COV | £4.5m | Regular Starter | **2.2500** | **1.0700** | 0m | External: Coventry GKP saves |
| **Raya** | ARS | £6.0m | Nailed Starter | **1.7360** | **0.7625** | 9630m | 50% 2025/26 (3330m) + 50% mean older usable [2023/24,2024/25] |

*⚠️ Promoted Proxy: Wilson/Butland use external Championship/SPFL rate packages (`usable_mins_total` = 0 in FPL archives).*

---

## Method

1. **Goalkeeper Selection**: Nailed Starter or Regular Starter (role CSV ∩ expected-stats).
2. **Projection**: `ParticipationStateHybridModel.predict` on Feature-Contract-like rows for GW1–38; attack/defence strength multipliers from `_fixture_maps`. Minutes forced flat (90 start / fit) for this study — Regular/promoted risk stays as tags, not minutes haircuts.
3. **Weekly pick (primary)**: FDR-min (easier defence FDR; home wins ties) — matches 2025/26 historical backtest rule.
4. **Weekly pick (footnote)**: max(xP) each GW → `tot_rot_xp_maxxp` and `maxxp_delta`.
5. **Horizons**: gw1_6, gw1_10, gw1_19, full_season — each uses **its own** rotated xP sum (no GW1–6 reuse).
6. **Points-Heavy RQI** (0–100):
   $$\text{RQI} = 0.40 \cdot S_{\text{tot_xp}} + 0.20 \cdot S_{\text{fdr}} + 0.20 \cdot S_{\text{corr}} + 0.10 \cdot S_{\text{easy}} + 0.10 \cdot S_{\text{cost}}$$
   $S_{\text{tot_xp}}$ from **rotated xP / GW** on a 2.5–4.2 scale. Caveat: flat-90 hybrid GKP xP/GW often exceeds 4.2 → $S_{\text{tot_xp}}$ saturates; rank differentiation shifts toward FDR/corr/ease/cost.

---

## Findings

### 1. GW1–6 Early Season Peak Rotation Pairs

#### **1.1 GW1–6 Top 10 Overall Pairs**
*🔥 **£9.0m** = double £4.5m. `⚠️` = promoted proxy.*

| Rank | GKP 1 (Club, Price) | GKP 1 Baseline (Saves/90 \| GC/90) | GKP 2 (Club, Price) | GKP 2 Baseline (Saves/90 \| GC/90) | Total Price | RQI Score | GW1–6 Rotated $xP$ (FDR-min) | max(xP) Δ | FDR Corr ($r$) | Rot Avg FDR | Easy GWs ($\le 2$) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **1** | **Wilson** (COV £4.5m) | 2.250 \| 1.070 | **Sels** (NFO £5.0m) | 2.970 \| 1.383 | **£9.5m** ⚠️ | **90.79 / 100** | **39.30 $xP$** | 0.00 | **-0.6076** | **2.17** | 5 / 6 (83.3%) |
| **2** | **Martinez** (AVL £5.0m) | 2.921 \| 1.308 | **Wilson** (COV £4.5m) | 2.250 \| 1.070 | **£9.5m** ⚠️ | **88.39 / 100** | **38.26 $xP$** | 0.06 | **-0.6445** | **2.33** | 4 / 6 (66.7%) |
| **3** | **Verbruggen** (BHA £4.5m) | 2.800 \| 1.341 | **Lammens** (MUN £5.0m) | 2.469 \| 1.219 | **£9.5m** | **87.89 / 100** | **38.77 $xP$** | 0.00 | **-0.5941** | **2.33** | 4 / 6 (66.7%) |
| **4** | **Kelleher** (BRE £5.0m) | 2.848 \| 1.237 | **Wilson** (COV £4.5m) | 2.250 \| 1.070 | **£9.5m** ⚠️ | **87.66 / 100** | **38.50 $xP$** | 0.00 | **-0.5716** | **2.33** | 4 / 6 (66.7%) |
| **5** | **Verbruggen** (BHA £4.5m) | 2.800 \| 1.341 | **Butland** (HUL £4.5m) | 2.333 \| 1.010 | 🔥 **£9.0m** ⚠️ | **87.61 / 100** | **37.97 $xP$** | 0.00 | **-0.5941** | **2.50** | 3 / 6 (50.0%) |
| **6** | **Verbruggen** (BHA £4.5m) | 2.800 \| 1.341 | **Wilson** (COV £4.5m) | 2.250 \| 1.070 | 🔥 **£9.0m** ⚠️ | **87.49 / 100** | **38.53 $xP$** | 0.00 | **-0.3038** | **2.33** | 4 / 6 (66.7%) |
| **7** | **Wilson** (COV £4.5m) | 2.250 \| 1.070 | **Lammens** (MUN £5.0m) | 2.469 \| 1.219 | **£9.5m** ⚠️ | **85.26 / 100** | **38.31 $xP$** | 0.36 | **-0.3309** | **2.33** | 4 / 6 (66.7%) |
| **8** | **Verbruggen** (BHA £4.5m) | 2.800 \| 1.341 | **Kinsky** (TOT £4.5m) | 2.714 \| 1.417 | 🔥 **£9.0m** | **85.20 / 100** | **36.60 $xP$** | 0.00 | **-0.3536** | **2.50** | 3 / 6 (50.0%) |
| **9** | **Verbruggen** (BHA £4.5m) | 2.800 \| 1.341 | **Pope** (NEW £5.0m) | 3.163 \| 1.288 | **£9.5m** | **84.92 / 100** | **38.59 $xP$** | 0.00 | **-0.2970** | **2.33** | 4 / 6 (66.7%) |
| **10** | **Henderson** (CRY £5.0m) | 2.922 \| 1.441 | **Butland** (HUL £4.5m) | 2.333 \| 1.010 | **£9.5m** ⚠️ | **84.79 / 100** | **36.96 $xP$** | 0.44 | **-0.8402** | **2.67** | 2 / 6 (33.3%) |

#### **1.2 GW1–6 Top 10 PL-Proven Pairs (Excluding Promoted Proxies)**

| Rank | GKP 1 (Club, Price) | GKP 1 Baseline (Saves/90 \| GC/90) | GKP 2 (Club, Price) | GKP 2 Baseline (Saves/90 \| GC/90) | Total Price | RQI Score | GW1–6 Rotated $xP$ (FDR-min) | max(xP) Δ | FDR Corr ($r$) | Rot Avg FDR | Easy GWs ($\le 2$) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **1** | **Verbruggen** (BHA £4.5m) | 2.800 \| 1.341 | **Lammens** (MUN £5.0m) | 2.469 \| 1.219 | **£9.5m** | **87.89 / 100** | **38.77 $xP$** | 0.00 | **-0.5941** | **2.33** | 4 / 6 (66.7%) |
| **2** | **Verbruggen** (BHA £4.5m) | 2.800 \| 1.341 | **Kinsky** (TOT £4.5m) | 2.714 \| 1.417 | 🔥 **£9.0m** | **85.20 / 100** | **36.60 $xP$** | 0.00 | **-0.3536** | **2.50** | 3 / 6 (50.0%) |
| **3** | **Verbruggen** (BHA £4.5m) | 2.800 \| 1.341 | **Pope** (NEW £5.0m) | 3.163 \| 1.288 | **£9.5m** | **84.92 / 100** | **38.59 $xP$** | 0.00 | **-0.2970** | **2.33** | 4 / 6 (66.7%) |
| **4** | **Petrović** (BOU £4.5m) | 3.134 \| 1.572 | **Sels** (NFO £5.0m) | 2.970 \| 1.383 | **£9.5m** | **84.60 / 100** | **35.90 $xP$** | 0.00 | **-0.8216** | **2.67** | 2 / 6 (33.3%) |
| **5** | **Verbruggen** (BHA £4.5m) | 2.800 \| 1.341 | **Roefs** (SUN £5.0m) | 3.114 \| 1.314 | **£9.5m** | **83.61 / 100** | **39.09 $xP$** | 0.00 | **0.0000** | **2.33** | 5 / 6 (83.3%) |
| **6** | **Pope** (NEW £5.0m) | 3.163 \| 1.288 | **Kinsky** (TOT £4.5m) | 2.714 \| 1.417 | **£9.5m** | **83.37 / 100** | **36.90 $xP$** | 0.90 | **-0.4201** | **2.50** | 3 / 6 (50.0%) |
| **7** | **Verbruggen** (BHA £4.5m) | 2.800 \| 1.341 | **Sels** (NFO £5.0m) | 2.970 \| 1.383 | **£9.5m** | **83.34 / 100** | **37.58 $xP$** | 0.20 | **-0.2500** | **2.50** | 4 / 6 (66.7%) |
| **8** | **Verbruggen** (BHA £4.5m) | 2.800 \| 1.341 | **Sánchez** (CHE £5.0m) | 3.025 \| 1.383 | **£9.5m** | **83.25 / 100** | **37.40 $xP$** | 0.09 | **-0.4082** | **2.50** | 3 / 6 (50.0%) |
| **9** | **Leno** (FUL £4.5m) | 2.895 \| 1.428 | **Kinsky** (TOT £4.5m) | 2.714 \| 1.417 | 🔥 **£9.0m** | **82.76 / 100** | **35.39 $xP$** | 0.00 | **-0.3873** | **2.67** | 2 / 6 (33.3%) |
| **10** | **Sels** (NFO £5.0m) | 2.970 \| 1.383 | **Kinsky** (TOT £4.5m) | 2.714 \| 1.417 | **£9.5m** | **82.70 / 100** | **36.86 $xP$** | 0.00 | **-0.3536** | **2.50** | 3 / 6 (50.0%) |

---

### 2. Full Season Horizon (GW1–38, Horizon-Matched Rotated xP)

#### **2.1 Full Season Top 10 Overall Pairs**

| Rank | GKP 1 (Club, Price) | GKP 1 Baseline (Saves/90 \| GC/90) | GKP 2 (Club, Price) | GKP 2 Baseline (Saves/90 \| GC/90) | Total Price | RQI Score | Full Season Rotated $xP$ (FDR-min) | max(xP) Δ | FDR Corr ($r$) | Rot Avg FDR | Easy GWs ($\le 2$) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **1** | **Verbruggen** (BHA £4.5m) | 2.800 \| 1.341 | **Butland** (HUL £4.5m) | 2.333 \| 1.010 | 🔥 **£9.0m** ⚠️ | **85.38 / 100** | **238.40 $xP$** | 2.79 | **-0.4325** | **2.55** | 18 / 38 (47.4%) |
| **2** | **Verbruggen** (BHA £4.5m) | 2.800 \| 1.341 | **Lammens** (MUN £5.0m) | 2.469 \| 1.219 | **£9.5m** | **83.87 / 100** | **236.96 $xP$** | 1.85 | **-0.4170** | **2.50** | 21 / 38 (55.3%) |
| **3** | **Leno** (FUL £4.5m) | 2.895 \| 1.428 | **Kinsky** (TOT £4.5m) | 2.714 \| 1.417 | 🔥 **£9.0m** | **83.75 / 100** | **229.74 $xP$** | 0.05 | **-0.2254** | **2.53** | 19 / 38 (50.0%) |
| **4** | **Sels** (NFO £5.0m) | 2.970 \| 1.383 | **Kinsky** (TOT £4.5m) | 2.714 \| 1.417 | **£9.5m** | **83.58 / 100** | **233.68 $xP$** | 1.17 | **-0.3981** | **2.47** | 20 / 38 (52.6%) |
| **5** | **Petrović** (BOU £4.5m) | 3.134 \| 1.572 | **Butland** (HUL £4.5m) | 2.333 \| 1.010 | 🔥 **£9.0m** ⚠️ | **83.27 / 100** | **234.85 $xP$** | 3.95 | **-0.1951** | **2.55** | 19 / 38 (50.0%) |
| **6** | **Petrović** (BOU £4.5m) | 3.134 \| 1.572 | **Sels** (NFO £5.0m) | 2.970 \| 1.383 | **£9.5m** | **83.23 / 100** | **232.45 $xP$** | 1.14 | **-0.3623** | **2.47** | 20 / 38 (52.6%) |
| **7** | **Kinsky** (TOT £4.5m) | 2.714 \| 1.417 | **Roefs** (SUN £5.0m) | 3.114 \| 1.314 | **£9.5m** | **82.78 / 100** | **235.47 $xP$** | 1.50 | **-0.3352** | **2.50** | 20 / 38 (52.6%) |
| **8** | **Verbruggen** (BHA £4.5m) | 2.800 \| 1.341 | **Roefs** (SUN £5.0m) | 3.114 \| 1.314 | **£9.5m** | **82.70 / 100** | **236.61 $xP$** | 1.51 | **-0.3451** | **2.53** | 20 / 38 (52.6%) |
| **9** | **Petrović** (BOU £4.5m) | 3.134 \| 1.572 | **Lammens** (MUN £5.0m) | 2.469 \| 1.219 | **£9.5m** | **82.57 / 100** | **234.02 $xP$** | 1.92 | **-0.2971** | **2.47** | 20 / 38 (52.6%) |
| **10** | **Verbruggen** (BHA £4.5m) | 2.800 \| 1.341 | **Wilson** (COV £4.5m) | 2.250 \| 1.070 | 🔥 **£9.0m** ⚠️ | **82.35 / 100** | **235.43 $xP$** | 0.92 | **-0.1649** | **2.61** | 18 / 38 (47.4%) |

#### **2.2 Full Season Top 10 PL-Proven Pairs (Excluding Promoted Proxies)**

| Rank | GKP 1 (Club, Price) | GKP 1 Baseline (Saves/90 \| GC/90) | GKP 2 (Club, Price) | GKP 2 Baseline (Saves/90 \| GC/90) | Total Price | RQI Score | Full Season Rotated $xP$ (FDR-min) | max(xP) Δ | FDR Corr ($r$) | Rot Avg FDR | Easy GWs ($\le 2$) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **1** | **Verbruggen** (BHA £4.5m) | 2.800 \| 1.341 | **Lammens** (MUN £5.0m) | 2.469 \| 1.219 | **£9.5m** | **83.87 / 100** | **236.96 $xP$** | 1.85 | **-0.4170** | **2.50** | 21 / 38 (55.3%) |
| **2** | **Leno** (FUL £4.5m) | 2.895 \| 1.428 | **Kinsky** (TOT £4.5m) | 2.714 \| 1.417 | 🔥 **£9.0m** | **83.75 / 100** | **229.74 $xP$** | 0.05 | **-0.2254** | **2.53** | 19 / 38 (50.0%) |
| **3** | **Sels** (NFO £5.0m) | 2.970 \| 1.383 | **Kinsky** (TOT £4.5m) | 2.714 \| 1.417 | **£9.5m** | **83.58 / 100** | **233.68 $xP$** | 1.17 | **-0.3981** | **2.47** | 20 / 38 (52.6%) |
| **4** | **Petrović** (BOU £4.5m) | 3.134 \| 1.572 | **Sels** (NFO £5.0m) | 2.970 \| 1.383 | **£9.5m** | **83.23 / 100** | **232.45 $xP$** | 1.14 | **-0.3623** | **2.47** | 20 / 38 (52.6%) |
| **5** | **Kinsky** (TOT £4.5m) | 2.714 \| 1.417 | **Roefs** (SUN £5.0m) | 3.114 \| 1.314 | **£9.5m** | **82.78 / 100** | **235.47 $xP$** | 1.50 | **-0.3352** | **2.50** | 20 / 38 (52.6%) |
| **6** | **Verbruggen** (BHA £4.5m) | 2.800 \| 1.341 | **Roefs** (SUN £5.0m) | 3.114 \| 1.314 | **£9.5m** | **82.70 / 100** | **236.61 $xP$** | 1.51 | **-0.3451** | **2.53** | 20 / 38 (52.6%) |
| **7** | **Petrović** (BOU £4.5m) | 3.134 \| 1.572 | **Lammens** (MUN £5.0m) | 2.469 \| 1.219 | **£9.5m** | **82.57 / 100** | **234.02 $xP$** | 1.92 | **-0.2971** | **2.47** | 20 / 38 (52.6%) |
| **8** | **Martinez** (AVL £5.0m) | 2.921 \| 1.308 | **Leno** (FUL £4.5m) | 2.895 \| 1.428 | **£9.5m** | **82.00 / 100** | **236.42 $xP$** | 0.62 | **-0.3007** | **2.53** | 19 / 38 (50.0%) |
| **9** | **Sánchez** (CHE £5.0m) | 3.025 \| 1.383 | **Leno** (FUL £4.5m) | 2.895 \| 1.428 | **£9.5m** | **81.53 / 100** | **233.13 $xP$** | 1.83 | **-0.2275** | **2.53** | 20 / 38 (52.6%) |
| **10** | **Henderson** (CRY £5.0m) | 2.922 \| 1.441 | **Leno** (FUL £4.5m) | 2.895 \| 1.428 | **£9.5m** | **81.35 / 100** | **229.89 $xP$** | 1.02 | **-0.2620** | **2.53** | 18 / 38 (47.4%) |

---

### 3. Top Pairings by Budget Tier & Risk Category

#### **Tier A: Premier League Proven Rotation Pairs (£9.5m)**
- **Verbruggen (BHA £4.5m) + Lammens (MUN £5.0m)**: PL-proven #1 on both GW1–6 (**RQI 87.89**, **38.77 $xP$**) and full season (**RQI 83.87**, **236.96 $xP$** FDR-min; max(xP) Δ **1.85**). Strong negative full-season FDR corr ($r = -0.417$).
- **Verbruggen (BHA £4.5m) + Roefs (SUN £5.0m)**: High full-season points (**236.61 $xP$**) with solid RQI (**82.70**).

#### **Tier B: £9.0m Budget Pairs (Double £4.5m)**
- **Leno (FUL £4.5m) + Kinsky (TOT £4.5m)**: Top PL-proven £9.0m full-season pair (**RQI 83.75**, **229.74 $xP$**); tiny max(xP) gap (**0.05**).
- **Verbruggen (BHA £4.5m) + Butland (HUL £4.5m)**: Top overall £9.0m full season (**RQI 85.38**), tagged `⚠️ Promoted Proxy`.

---

## 2025/26 Historical Retrospective Backtest (Empirical Proof)

**Data Source**: `data/archive/2025-26/processed/` (38 Gameweeks)  
**Script**: [`run_historical_backtest.py`](run_historical_backtest.py)  
**Artifacts**: [`historical_single_gkps_2025_26.csv`](../../../data/research/gkp-fixture-rotation/historical_single_gkps_2025_26.csv), [`historical_pair_rotations_2025_26.csv`](../../../data/research/gkp-fixture-rotation/historical_pair_rotations_2025_26.csv)

### 1. Revised Strategy Comparison & Category Averages (Regular Starters)

To eliminate non-playing bench fodder noise and single-player outlier skew, filter strictly for **regular starting goalkeepers** (starts $\ge 25$) at the start of the 2025/26 season:

| Strategy Category | Filtering Criteria | Sample Size | Avg Total Price (Incl. Bench) | Avg 38-GW Pts | Avg Pts / £1.0m | Diff vs Premium Avg |
|---|---|---|---|---|---|---|
| **All Premiums S&F (£5.5m+)** | Raya (£6.2m, 162), Pickford (£5.6m, 135), Donnarumma (£5.6m, 135) | n=3 | **£9.80m** | **144.0 pts** | **14.69** | Baseline |
| **All Solo £4.5m Budget S&F** | Verbruggen (£4.6m, 130), Petrović (£4.6m, 124), Sels (£4.6m, 105) | n=3 | **£8.60m** | **119.7 pts** | **13.91** | **-24.3 pts** |
| **All Regular Pair Rotations (FDR)** | All 45 valid regular starter pairs (cost $\le$ £9.6m) under FDR rule | n=45 | **£9.30m** | **126.8 pts** | **13.64** | **-17.2 pts** |
| **Top 5 Regular Pair Rotations (FDR)** | Top 5 FDR pairs (Verbruggen+Leno, Martinez+Verbruggen, Kelleher+Roefs, etc.) | n=5 | **£9.52m** | **152.0 pts** | **15.97** | **+8.0 pts** |
| **All Regular Pair Rotations (Hindsight)** | All 45 valid regular starter pairs under ex-post hindsight best rule | n=45 | **£9.30m** | **168.4 pts** | **18.11** | **+24.4 pts** |

---

### 2. Key Insights from Revised Regular Starter Filtering

1. **All Regular Pair Rotations Average (126.8 pts at £9.3m)**:
   - Across **all 45 regular starter rotation pairs**, FDR rotation averaged **126.8 pts**.
   - Compared to **Solo £4.5m Budget S&F (119.7 pts at £8.6m)**, active FDR pair rotation added **+7.1 pts across the entire season** (+0.19 pts/GW) while costing **+£0.7m more**.
   - Compared to **Premium S&F (144.0 pts at £9.8m)**, average pair rotation trailed premiums by **-17.2 pts**.

2. **Top 5 Regular Pair Rotations (152.0 pts at £9.5m)**:
   - If a manager successfully identified a **Top 5 pre-season rotation pair**, pre-deadline FDR rotation averaged **152.0 pts**, outscoring Premium S&F average (**144.0 pts**) by **+8.0 pts** over 38 weeks.
   - Picking an average pair yielded 126.8 pts.

---

### 3. Key Empirical Insights & Outlier Trade-Off Analysis

1. **Controlling for Outliers (Top 3 Premium Avg = 144.0 pts)**:
   - Top 3 Pre-Deadline FDR Pair Rotations averaged **147.3 pts** (£9.4m) → modest **+3.3 pts** vs average premium S&F.

2. **Solo Budget S&F vs Pair Rotation (£0.5m + roster slot)**:
   - Top 3 Pair Rotation (**147.3 pts at £9.4m**) vs Top 3 Solo Budget (**136.7 pts at £8.9m**) → **+10.6 pts** for **+£0.5m** and a 2nd active bench slot.
   - Reinvesting **+£0.5m** into outfield usually beats that margin.

**Forward vs backtest caveat**: Flat-90 hybrid season totals (~230+ $xP$) are **optimistic minutes upper bounds**, not calibrated to realized 2025/26 ~120–150 pt outcomes. Use rankings for pair complementarity; use historical section for absolute strategy value.

---

## Decision & Practical Recommendation

1. **Strategy 1: Premium Set & Forget (Raya £6.0m + £4.0m Bench = £10.0m)** — best overall points / least operational drag when budget allows.
2. **Strategy 2: Solo Budget Set & Forget (£4.5m–£5.0m + £4.0m Bench)** — best value; frees £ for outfield.
3. **Active 2-Keeper Pair Rotation** — only if locking a top-decile complementary pair (e.g. Verbruggen+Lammens) *and* accepting bench/slot cost; historical average pair underperforms solo budget after opportunity cost.
4. **Method note**: Forward RQI now uses horizon-matched FDR-min rotated xP from the hybrid scorer; do not compare absolute season $xP$ totals to historical points without the minutes caveat above.

---

## Risks and unknowns

- Flat-90 minutes ignore injury / glove-share (Pope, Kinsky, promoted Regulars).
- $S_{\text{tot_xp}}$ saturation on 2.5–4.2 scale under hybrid flat-90.
- Promoted proxy rates (Wilson, Butland) external / thin.
- FDR pick ≠ strength-multiplier scorer; intentional dual scale.
- DGW/BGW handled only as fixture-map rows present in processed fixtures.
