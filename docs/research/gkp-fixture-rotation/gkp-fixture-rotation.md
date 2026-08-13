# Starter Goalkeeper Fixture Rotation & FDR Correlation Study

**Updated**: 2026-08-14T01:30:00+07:00  
**Data stamp**: Stage 2 ADR-0014 rates 2026-08-14; FPL API processed snapshot; ParticipationStateHybridModel GW1–38 flat-90 projections  
**Season**: 2026/27  
**Purpose**: Identify pairs of **genuine starting goalkeepers** (Nailed Starter or Regular Starter) costing <= £9.5m combined with the highest horizon-matched rotated expected points under FDR-min weekly picks, negative FDR correlation, and lowest rotated average FDR.  
**Related**: [Expected Stats (Stage 2)](../gw1-6-preseason-pipeline/02-expected-stats-gw1-5/expected-stats-gw1-5.md) · [DEF rotation](../def-fixture-rotation/def-fixture-rotation.md) · [Downstream refresh](../gw1-6-preseason-pipeline/refresh_downstream.py)  
**Sources**: `data/processed/fixtures.parquet`, `data/processed/players.parquet`, `data/processed/clubs.parquet`, `data/research/gw1-6-preseason-pipeline/01-expected-role-gw1-5/expected-role-gw1-5.csv`, `data/research/gw1-6-preseason-pipeline/02-expected-stats-gw1-5/expected-stats-gw1-5.csv`  
**Artifacts**: [`gkp_rotation_matrix.csv`](../../../data/research/gkp-fixture-rotation/gkp_rotation_matrix.csv), [`gkp_performance_baseline.csv`](../../../data/research/gkp-fixture-rotation/gkp_performance_baseline.csv)  
**Script**: [`run_gkp_rotation_analysis.py`](run_gkp_rotation_analysis.py)

---

## Agent Prompt & Reproducibility Instructions

```text
Refresh starter GKP fixture rotation (consumes Stage 2 rates):

1. Prefer full downstream after a rate / new-player change:
   uv run python docs/research/gw1-6-preseason-pipeline/refresh_downstream.py
   This topic only:
   uv run python docs/research/gkp-fixture-rotation/run_gkp_rotation_analysis.py
2. Rank Nailed/Regular pairs, different clubs, combined cost <= £9.5m.
   Flat-90 ParticipationStateHybridModel GW1-38. FDR-min pick. Horizon-matched RQI.
   Promoted proxy tag: COV, HUL, IPS.
3. Update baseline + four ranking tables in gkp-fixture-rotation.md from CSVs.
4. Historical 2025/26 backtest section is archive-based — do not overwrite from Stage 2.
5. Verification: uv run pytest tests/test_gkp_fixture_rotation.py
```

Evaluate all genuine starter goalkeeper pairs (Nailed Starter or Regular Starter) from different clubs with combined cost <= £9.5m. Project weekly xP via `ParticipationStateHybridModel` over GW1–38 with **forced flat starter minutes** (p_start=1, xmins=90). Rank by Points-Heavy RQI using **horizon-matched** FDR-min rotated xP (not GW1–6 capped). Also report max(xP) upper bound. Tag promoted proxies (Rushworth/COV, Scherpen/IPS). Present overall and PL-proven top 10 for GW1–6 and full season; matrix retains gw1_10 and gw1_19.

---

## Starter Goalkeeper Filter & Baseline Metrics

True active 2-keeper rotation requires both keepers to be genuine starters. Non-playing £4.0m backups excluded.

### Goalkeeper Performance Baseline (Scorer Rates)

Authority = `expected-stats-gw1-5.csv` inputs consumed by the hybrid scorer (`per90_saves`, `per90_goals_conceded`). Clean sheets are **derived** inside the model from GC λ × defence multiplier — not a separate CS/90 column. Historical CS/xGC display rates retired from this table.

| Goalkeeper | Club | Price | Expected Role | Saves / 90 | GC / 90 | Usable Mins | Data Source / Note |
|---|---|---|---|---|---|---|---|
| **Trafford** | LEE | £5.0m | Nailed Starter | **3.7857** | **1.4737** | 0m FPL | Older FPL 2023/24 (2520m) + LEE dest GC 1.474 |
| **Pope** | NEW | £5.0m | Regular Starter | **3.3154** | **1.4156** | 2416m | Prior-Season Seed 2025/26 |
| **Sels** | NFO | £5.0m | Nailed Starter | **3.2058** | **1.3161** | 2667m | Prior-Season Seed 2025/26 |
| **Roefs** | SUN | £5.0m | Nailed Starter | **3.1143** | **1.3143** | 3150m | Prior-Season Seed 2025/26 |
| **Rushworth** ⚠️ | COV | £4.5m | Regular Starter | **3.1100** | **1.3750** | 0m FPL | Career 2023/24 CHA Swansea; dest GC COV=1.375 |
| **Martinez** | AVL | £5.0m | Nailed Starter | **3.0159** | **1.2381** | 2835m | Prior-Season Seed 2025/26 |
| **Kelleher** | BRE | £5.0m | Nailed Starter | **2.9459** | **1.3243** | 3330m | Prior-Season Seed 2025/26 |
| **Sánchez** | CHE | £5.0m | Nailed Starter | **2.9013** | **1.4507** | 3040m | Prior-Season Seed 2025/26 |
| **Petrović** | BOU | £4.5m | Nailed Starter | **2.8684** | **1.4211** | 3420m | Prior-Season Seed 2025/26 |
| **Henderson** | CRY | £5.0m | Nailed Starter | **2.8649** | **1.3784** | 3330m | Prior-Season Seed 2025/26 |
| **Verbruggen** | BHA | £4.5m | Nailed Starter | **2.7895** | **1.2105** | 3420m | Prior-Season Seed 2025/26 |
| **Pickford** | EVE | £5.5m | Nailed Starter | **2.6316** | **1.3158** | 3420m | Prior-Season Seed 2025/26 |
| **Leno** | FUL | £4.5m | Nailed Starter | **2.5789** | **1.3421** | 3420m | Prior-Season Seed 2025/26 |
| **Lammens** | MUN | £5.0m | Nailed Starter | **2.4688** | **1.2188** | 2880m | Prior-Season Seed 2025/26 |
| **Donnarumma** | MCI | £5.5m | Nailed Starter | **2.2941** | **0.8529** | 3060m | Prior-Season Seed 2025/26 |
| **A.Becker** | LIV | £5.5m | Nailed Starter | **2.1923** | **1.1923** | 2340m | Prior-Season Seed 2025/26 |
| **Scherpen** ⚠️ | IPS | £4.5m | Regular Starter | **1.9000** | **1.3750** | 0m FPL | Career Union SG 2025/26 1.90 saves/90; dest GC IPS=1.375 |
| **Raya** | ARS | £6.0m | Nailed Starter | **1.6216** | **0.7027** | 3330m | Prior-Season Seed 2025/26 |
| **Kinsky** | TOT | £4.5m | Regular Starter | **1.4286** | **1.0000** | 630m | Prior-Season Seed 2025/26 (thin 630m) |

*⚠️ Promoted Proxy: COV / HUL / IPS. Wilson and Butland dropped from starter baseline; COV #1 is Rushworth. Scherpen RQI can look high vs FDR complementarity — PL-proven tables exclude him.*

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
*🔥 **£9.0m** = double £4.5m. `⚠️` = promoted proxy (COV/HUL/IPS).*

| Rank | GKP 1 (Club, Price) | GKP 1 Baseline (Saves/90 \| GC/90) | GKP 2 (Club, Price) | GKP 2 Baseline (Saves/90 \| GC/90) | Total Price | RQI Score | GW1–6 Rotated $xP$ (FDR-min) | max(xP) Δ | FDR Corr ($r$) | Rot Avg FDR | Easy GWs ($\le 2$) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **1** | **Kinsky** (TOT £4.5m) | 1.429 \| 1.000 | **Scherpen** (IPS £4.5m) | 1.900 \| 1.375 | 🔥 **£9.0m** ⚠️ | **88.74 / 100** | **35.94 $xP$** | 0.00 | **-0.7071** | **2.50** | 3 / 6 (50.0%) |
| **2** | **Rushworth** (COV £4.5m) | 3.110 \| 1.375 | **Lammens** (MUN £5.0m) | 2.469 \| 1.219 | **£9.5m** ⚠️ | **87.89 / 100** | **38.53 $xP$** | 0.00 | **-0.5941** | **2.33** | 4 / 6 (66.7%) |
| **3** | **Verbruggen** (BHA £4.5m) | 2.789 \| 1.211 | **Lammens** (MUN £5.0m) | 2.469 \| 1.219 | **£9.5m** | **87.89 / 100** | **38.77 $xP$** | 0.00 | **-0.5941** | **2.33** | 4 / 6 (66.7%) |
| **4** | **Petrović** (BOU £4.5m) | 2.868 \| 1.421 | **Scherpen** (IPS £4.5m) | 1.900 \| 1.375 | 🔥 **£9.0m** ⚠️ | **87.10 / 100** | **34.04 $xP$** | 0.00 | **-0.8216** | **2.67** | 2 / 6 (33.3%) |
| **5** | **Trafford** (LEE £5.0m) | 3.786 \| 1.474 | **Scherpen** (IPS £4.5m) | 1.900 \| 1.375 | **£9.5m** ⚠️ | **86.95 / 100** | **35.77 $xP$** | 0.00 | **-0.5000** | **2.33** | 4 / 6 (66.7%) |
| **6** | **Verbruggen** (BHA £4.5m) | 2.789 \| 1.211 | **Kinsky** (TOT £4.5m) | 1.429 \| 1.000 | 🔥 **£9.0m** | **85.20 / 100** | **36.29 $xP$** | 0.39 | **-0.3536** | **2.50** | 3 / 6 (50.0%) |
| **7** | **Rushworth** (COV £4.5m) | 3.110 \| 1.375 | **Kinsky** (TOT £4.5m) | 1.429 \| 1.000 | 🔥 **£9.0m** ⚠️ | **85.20 / 100** | **35.75 $xP$** | 0.55 | **-0.3536** | **2.50** | 3 / 6 (50.0%) |
| **8** | **Kelleher** (BRE £5.0m) | 2.946 \| 1.324 | **Scherpen** (IPS £4.5m) | 1.900 \| 1.375 | **£9.5m** ⚠️ | **85.11 / 100** | **36.01 $xP$** | 0.00 | **-0.5941** | **2.50** | 3 / 6 (50.0%) |
| **9** | **Verbruggen** (BHA £4.5m) | 2.789 \| 1.211 | **Pope** (NEW £5.0m) | 3.315 \| 1.416 | **£9.5m** | **84.92 / 100** | **38.73 $xP$** | 0.00 | **-0.2970** | **2.33** | 4 / 6 (66.7%) |
| **10** | **Rushworth** (COV £4.5m) | 3.110 \| 1.375 | **Pope** (NEW £5.0m) | 3.315 \| 1.416 | **£9.5m** ⚠️ | **84.92 / 100** | **38.34 $xP$** | 0.00 | **-0.2970** | **2.33** | 4 / 6 (66.7%) |

Overall #1 is FDR complementarity (Kinsky+Scherpen), not points. Prefer PL-proven #1 for a points-sensible pair.

#### **1.2 GW1–6 Top 10 PL-Proven Pairs (Excluding Promoted Proxies)**

| Rank | GKP 1 (Club, Price) | GKP 1 Baseline (Saves/90 \| GC/90) | GKP 2 (Club, Price) | GKP 2 Baseline (Saves/90 \| GC/90) | Total Price | RQI Score | GW1–6 Rotated $xP$ (FDR-min) | max(xP) Δ | FDR Corr ($r$) | Rot Avg FDR | Easy GWs ($\le 2$) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **1** | **Verbruggen** (BHA £4.5m) | 2.789 \| 1.211 | **Lammens** (MUN £5.0m) | 2.469 \| 1.219 | **£9.5m** | **87.89 / 100** | **38.77 $xP$** | 0.00 | **-0.5941** | **2.33** | 4 / 6 (66.7%) |
| **2** | **Verbruggen** (BHA £4.5m) | 2.789 \| 1.211 | **Kinsky** (TOT £4.5m) | 1.429 \| 1.000 | 🔥 **£9.0m** | **85.20 / 100** | **36.29 $xP$** | 0.39 | **-0.3536** | **2.50** | 3 / 6 (50.0%) |
| **3** | **Verbruggen** (BHA £4.5m) | 2.789 \| 1.211 | **Pope** (NEW £5.0m) | 3.315 \| 1.416 | **£9.5m** | **84.92 / 100** | **38.73 $xP$** | 0.00 | **-0.2970** | **2.33** | 4 / 6 (66.7%) |
| **4** | **Petrović** (BOU £4.5m) | 2.868 \| 1.421 | **Sels** (NFO £5.0m) | 3.206 \| 1.316 | **£9.5m** | **84.60 / 100** | **37.33 $xP$** | 0.00 | **-0.8216** | **2.67** | 2 / 6 (33.3%) |
| **5** | **Verbruggen** (BHA £4.5m) | 2.789 \| 1.211 | **Roefs** (SUN £5.0m) | 3.114 \| 1.314 | **£9.5m** | **83.61 / 100** | **37.85 $xP$** | 0.00 | **0.0000** | **2.33** | 5 / 6 (83.3%) |
| **6** | **Pope** (NEW £5.0m) | 3.315 \| 1.416 | **Kinsky** (TOT £4.5m) | 1.429 \| 1.000 | **£9.5m** | **83.37 / 100** | **38.15 $xP$** | 0.50 | **-0.4201** | **2.50** | 3 / 6 (50.0%) |
| **7** | **Verbruggen** (BHA £4.5m) | 2.789 \| 1.211 | **Sels** (NFO £5.0m) | 3.206 \| 1.316 | **£9.5m** | **83.34 / 100** | **37.63 $xP$** | 1.19 | **-0.2500** | **2.50** | 4 / 6 (66.7%) |
| **8** | **Verbruggen** (BHA £4.5m) | 2.789 \| 1.211 | **Sánchez** (CHE £5.0m) | 2.901 \| 1.451 | **£9.5m** | **83.25 / 100** | **36.16 $xP$** | 0.25 | **-0.4082** | **2.50** | 3 / 6 (50.0%) |
| **9** | **Leno** (FUL £4.5m) | 2.579 \| 1.342 | **Kinsky** (TOT £4.5m) | 1.429 \| 1.000 | 🔥 **£9.0m** | **82.76 / 100** | **35.91 $xP$** | 0.15 | **-0.3873** | **2.67** | 2 / 6 (33.3%) |
| **10** | **Sels** (NFO £5.0m) | 3.206 \| 1.316 | **Kinsky** (TOT £4.5m) | 1.429 \| 1.000 | **£9.5m** | **82.70 / 100** | **38.50 $xP$** | 0.00 | **-0.3536** | **2.50** | 3 / 6 (50.0%) |

---

### 2. Full Season Horizon (GW1–38, Horizon-Matched Rotated xP)

#### **2.1 Full Season Top 10 Overall Pairs**

| Rank | GKP 1 (Club, Price) | GKP 1 Baseline (Saves/90 \| GC/90) | GKP 2 (Club, Price) | GKP 2 Baseline (Saves/90 \| GC/90) | Total Price | RQI Score | Full Season Rotated $xP$ (FDR-min) | max(xP) Δ | FDR Corr ($r$) | Rot Avg FDR | Easy GWs ($\le 2$) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **1** | **Verbruggen** (BHA £4.5m) | 2.789 \| 1.211 | **Lammens** (MUN £5.0m) | 2.469 \| 1.219 | **£9.5m** | **83.87 / 100** | **232.35 $xP$** | 4.01 | **-0.4170** | **2.50** | 21 / 38 (55.3%) |
| **2** | **Rushworth** (COV £4.5m) | 3.110 \| 1.375 | **Lammens** (MUN £5.0m) | 2.469 \| 1.219 | **£9.5m** ⚠️ | **83.87 / 100** | **229.99 $xP$** | 4.93 | **-0.4170** | **2.50** | 21 / 38 (55.3%) |
| **3** | **Leno** (FUL £4.5m) | 2.579 \| 1.342 | **Kinsky** (TOT £4.5m) | 1.429 \| 1.000 | 🔥 **£9.0m** | **83.75 / 100** | **232.64 $xP$** | 2.13 | **-0.2254** | **2.53** | 19 / 38 (50.0%) |
| **4** | **Sels** (NFO £5.0m) | 3.206 \| 1.316 | **Kinsky** (TOT £4.5m) | 1.429 \| 1.000 | **£9.5m** | **83.58 / 100** | **240.72 $xP$** | 1.90 | **-0.3981** | **2.47** | 20 / 38 (52.6%) |
| **5** | **Petrović** (BOU £4.5m) | 2.868 \| 1.421 | **Sels** (NFO £5.0m) | 3.206 \| 1.316 | **£9.5m** | **83.23 / 100** | **239.23 $xP$** | 2.00 | **-0.3623** | **2.47** | 20 / 38 (52.6%) |
| **6** | **Kinsky** (TOT £4.5m) | 1.429 \| 1.000 | **Roefs** (SUN £5.0m) | 3.114 \| 1.314 | **£9.5m** | **82.78 / 100** | **240.20 $xP$** | 0.96 | **-0.3352** | **2.50** | 20 / 38 (52.6%) |
| **7** | **Rushworth** (COV £4.5m) | 3.110 \| 1.375 | **Roefs** (SUN £5.0m) | 3.114 \| 1.314 | **£9.5m** ⚠️ | **82.70 / 100** | **228.07 $xP$** | 4.11 | **-0.3451** | **2.53** | 20 / 38 (52.6%) |
| **8** | **Verbruggen** (BHA £4.5m) | 2.789 \| 1.211 | **Roefs** (SUN £5.0m) | 3.114 \| 1.314 | **£9.5m** | **82.70 / 100** | **231.15 $xP$** | 3.15 | **-0.3451** | **2.53** | 20 / 38 (52.6%) |
| **9** | **Petrović** (BOU £4.5m) | 2.868 \| 1.421 | **Lammens** (MUN £5.0m) | 2.469 \| 1.219 | **£9.5m** | **82.57 / 100** | **236.55 $xP$** | 0.88 | **-0.2971** | **2.47** | 20 / 38 (52.6%) |
| **10** | **Martinez** (AVL £5.0m) | 3.016 \| 1.238 | **Leno** (FUL £4.5m) | 2.579 \| 1.342 | **£9.5m** | **82.00 / 100** | **240.19 $xP$** | 1.62 | **-0.3007** | **2.53** | 19 / 38 (50.0%) |

#### **2.2 Full Season Top 10 PL-Proven Pairs (Excluding Promoted Proxies)**

| Rank | GKP 1 (Club, Price) | GKP 1 Baseline (Saves/90 \| GC/90) | GKP 2 (Club, Price) | GKP 2 Baseline (Saves/90 \| GC/90) | Total Price | RQI Score | Full Season Rotated $xP$ (FDR-min) | max(xP) Δ | FDR Corr ($r$) | Rot Avg FDR | Easy GWs ($\le 2$) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **1** | **Verbruggen** (BHA £4.5m) | 2.789 \| 1.211 | **Lammens** (MUN £5.0m) | 2.469 \| 1.219 | **£9.5m** | **83.87 / 100** | **232.35 $xP$** | 4.01 | **-0.4170** | **2.50** | 21 / 38 (55.3%) |
| **2** | **Leno** (FUL £4.5m) | 2.579 \| 1.342 | **Kinsky** (TOT £4.5m) | 1.429 \| 1.000 | 🔥 **£9.0m** | **83.75 / 100** | **232.64 $xP$** | 2.13 | **-0.2254** | **2.53** | 19 / 38 (50.0%) |
| **3** | **Sels** (NFO £5.0m) | 3.206 \| 1.316 | **Kinsky** (TOT £4.5m) | 1.429 \| 1.000 | **£9.5m** | **83.58 / 100** | **240.72 $xP$** | 1.90 | **-0.3981** | **2.47** | 20 / 38 (52.6%) |
| **4** | **Petrović** (BOU £4.5m) | 2.868 \| 1.421 | **Sels** (NFO £5.0m) | 3.206 \| 1.316 | **£9.5m** | **83.23 / 100** | **239.23 $xP$** | 2.00 | **-0.3623** | **2.47** | 20 / 38 (52.6%) |
| **5** | **Kinsky** (TOT £4.5m) | 1.429 \| 1.000 | **Roefs** (SUN £5.0m) | 3.114 \| 1.314 | **£9.5m** | **82.78 / 100** | **240.20 $xP$** | 0.96 | **-0.3352** | **2.50** | 20 / 38 (52.6%) |
| **6** | **Verbruggen** (BHA £4.5m) | 2.789 \| 1.211 | **Roefs** (SUN £5.0m) | 3.114 \| 1.314 | **£9.5m** | **82.70 / 100** | **231.15 $xP$** | 3.15 | **-0.3451** | **2.53** | 20 / 38 (52.6%) |
| **7** | **Petrović** (BOU £4.5m) | 2.868 \| 1.421 | **Lammens** (MUN £5.0m) | 2.469 \| 1.219 | **£9.5m** | **82.57 / 100** | **236.55 $xP$** | 0.88 | **-0.2971** | **2.47** | 20 / 38 (52.6%) |
| **8** | **Martinez** (AVL £5.0m) | 3.016 \| 1.238 | **Leno** (FUL £4.5m) | 2.579 \| 1.342 | **£9.5m** | **82.00 / 100** | **240.19 $xP$** | 1.62 | **-0.3007** | **2.53** | 19 / 38 (50.0%) |
| **9** | **Sánchez** (CHE £5.0m) | 2.901 \| 1.451 | **Leno** (FUL £4.5m) | 2.579 \| 1.342 | **£9.5m** | **81.53 / 100** | **230.89 $xP$** | 2.64 | **-0.2275** | **2.53** | 20 / 38 (52.6%) |
| **10** | **Henderson** (CRY £5.0m) | 2.865 \| 1.378 | **Leno** (FUL £4.5m) | 2.579 \| 1.342 | **£9.5m** | **81.35 / 100** | **231.37 $xP$** | 2.22 | **-0.2620** | **2.53** | 18 / 38 (47.4%) |

---

### 3. Top Pairings by Budget Tier & Risk Category

#### **Tier A: Premier League Proven Rotation Pairs (£9.5m)**
- **Verbruggen (BHA £4.5m) + Lammens (MUN £5.0m)**: PL-proven #1 on both GW1–6 (**RQI 87.89**, **38.77 $xP$**) and full season (**RQI 83.87**, **232.35 $xP$** FDR-min; max(xP) Δ **4.01**). Strong negative full-season FDR corr ($r = -0.417$).
- **Sels (NFO £5.0m) + Kinsky (TOT £4.5m)**: Highest PL-proven full-season points (**240.72 $xP$**) at RQI **83.58**.

#### **Tier B: £9.0m Budget Pairs (Double £4.5m)**
- **Leno (FUL £4.5m) + Kinsky (TOT £4.5m)**: Top PL-proven £9.0m full-season pair (**RQI 83.75**, **232.64 $xP$**).
- **Kinsky + Scherpen** / **Rushworth** pairs: overall RQI leaders tagged `⚠️ Promoted Proxy` — do not treat as PL-proven.

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
- Promoted proxy rates (Rushworth/COV, Scherpen/IPS) are career + destination GC; Scherpen 1.90 saves/90 inflates RQI via FDR, not shot-stopping.
- FDR pick ≠ strength-multiplier scorer; intentional dual scale.
- DGW/BGW handled only as fixture-map rows present in processed fixtures.
