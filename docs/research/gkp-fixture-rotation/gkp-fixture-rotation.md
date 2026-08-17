# Starter Goalkeeper Fixture Rotation & FDR Correlation Study

> [!NOTE]
> **Consolidated & Superseded**: This standalone goalkeeper research note has been consolidated into the unified authority: [**Defensive Architecture, Strategy & Fixture Rotation (Unified GKP & DEF)**](../defensive-fixture-rotation/defensive-fixture-rotation.md). Please refer to the unified note for the latest 564-player baseline, two-factor DCS scoring, and integrated GW1 BB + WC4 backline simulations.

**Updated**: 2026-08-18T00:20:00+07:00  
**Data stamp**: Stage 2 ADR-0014 rates 2026-08-14; FPL API processed snapshot; ParticipationStateHybridModel GW1–38 flat-90 projections  
**Season**: 2026/27  
**Purpose**: Identify pairs of **genuine starting goalkeepers** (Nailed Starter or Regular Starter) costing <= £9.5m combined with the highest horizon-matched rotated expected points under FDR-min weekly picks, negative FDR correlation, and lowest rotated average FDR.  
**Related**: [Unified Defensive Rotation](../defensive-fixture-rotation/defensive-fixture-rotation.md) · [Expected Stats (Stage 2)](../gw1-6-preseason-pipeline/02-expected-stats-gw1-5/expected-stats-gw1-5.md) · [First-Half Chip Strategy](../fpl-first-half-chip-strategy/fpl-first-half-chip-strategy.md) · [Downstream refresh](../gw1-6-preseason-pipeline/refresh_downstream.py)  
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
2. **Projection**: `ParticipationStateHybridModel.predict` on Feature-Contract-like rows for GW1–38; attack/defence strength multipliers from `_fixture_maps`. Minutes forced flat (90 start / fit) for this study.
3. **Weekly pick (primary)**: **Unconditional $\max(xP)$** — starters selected solely on projected points (shot-stopping baseline + Poisson clean sheets + defcon).
4. **Schedule Diversification**: **Fixture Overlap Index (FOI)** measuring joint clean-sheet failure risk ($\text{FOI} = \frac{1}{T}\sum (1 - p_{\text{cs1}})(1 - p_{\text{cs2}})$).
5. **Opportunity-Cost Adjusted Net Value (OC-RQI)**:
   $$\text{OC-RQI} = \frac{\text{Rotated xP}}{N} - \gamma \times (\text{Total Spend} - £8.5\text{m})$$
   Where $\gamma \approx 0.24-0.25\text{ xP/£1.0m/GW}$ is the empirical outfield slope estimated via OLS across drafted outfield assets from Stage 2.
6. **Recalibrated Non-Saturating RQI** (0–100):
   $$\text{RQI} = 0.50 \cdot S_{\text{xp}} + 0.20 \cdot S_{\text{foi}} + 0.15 \cdot S_{\text{fdr}} + 0.15 \cdot S_{\text{cost}}$$
   $S_{\text{xp}}$ evaluated on a wide $3.0-7.5\text{ xP/GW}$ range to eliminate saturation.

### Metric Definitions & Direction

| Metric | Symbol | Definition / Formula | Direction | Ideal / Benchmark | Description |
|---|---|---|---|---|---|
| **Opportunity-Cost Adjusted RQI** | `OC-RQI` | $\frac{\text{Rotated xP}}{N} - \gamma \times (\text{Total Spend} - £8.5\text{m})$ | Higher is better $\uparrow$ | **$> 6.10$** (GW1–6) / **$> 6.00$** (GW1–38) | Net weekly expected points after deducting empirical outfield shadow price ($\gamma \approx 0.25/\text{£1.0m/GW}$). Prevents overpaying for marginal GKP gains. |
| **Rotation Quality Index** | `RQI` | $0.50 S_{\text{xp}} + 0.20 S_{\text{foi}} + 0.15 S_{\text{fdr}} + 0.15 S_{\text{cost}}$ | Higher is better $\uparrow$ | **$\ge 66.0$ / 100** | Multi-attribute score balancing points output ($50\%$), fixture non-overlap ($20\%$), schedule ease ($15\%$), and budget tier ($15\%$). |
| **Rotated Expected Points** | `Rotated xP` | $\sum_{t=1}^N \max(xP_{1,t}, xP_{2,t})$ | Higher is better $\uparrow$ | **$\ge 38.5\text{ xP}$** (GW1–6) / **$\ge 235\text{ xP}$** (GW1–38) | Horizon-total projected points under the weekly $\max(xP)$ starting decision rule. |
| **Expected Clean Sheets** | `Exp CS` | $\sum_{t=1}^N e^{-\lambda_{i^*,t}}$ | Higher is better $\uparrow$ | **$\ge 2.20$** (GW1–6) / **$\ge 14.50$** (GW1–38) | Poisson clean-sheet expectation for the selected weekly starter. |
| **Fixture Overlap Index** | `FOI` | $\frac{1}{T}\sum (1 - p_{\text{cs1}})(1 - p_{\text{cs2}})$ | Lower is better $\downarrow$ | **$< 0.50$** (Min $\approx 0.44$) | Joint clean-sheet failure risk. Lower values indicate stronger schedule diversification where both keepers rarely fail together. |
| **FDR Selection Loss** | `FDR Loss` | $\sum \text{FDR}(\max xP) - \sum \text{FDR}(\min \text{FDR})$ | Lower is better $\downarrow$ | **$0.00$** | Difference between the FDR of the $\max(xP)$ starter vs the minimum FDR available. $0.00$ means points and fixture ease align perfectly. |
| **Schedule Correlation** | $r$ | $\text{Pearson } r(\text{FDR}_1, \text{FDR}_2)$ | Lower is better $\downarrow$ (Negative) | **$r \le -0.10$** | Linear correlation between the two clubs' 38-GW FDR schedules. Negative correlation guarantees complementary fixture runs. |

---

## Findings

### 1. GW1–6 Early Season Peak Rotation Pairs

#### **1.1 GW1–6 Top 10 Overall Pairs**
*🔥 **£9.0m** = double £4.5m. `⚠️` = promoted proxy (COV/HUL/IPS).*

| Rank | GKP 1 (Club, Price) | GKP 1 Rates (Saves / GC) | GKP 2 (Club, Price) | GKP 2 Rates (Saves / GC) | Total Price | OC-RQI | Rotated xP (max) | Exp CS | FOI | FDR Loss | RQI Score |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **1** | **Verbruggen** (BHA £4.5m) | 2.79 / 1.21 | **Sels** (NFO £5.0m) | 3.21 / 1.32 | **£9.5m** | **6.227** | **38.82 xP** | 2.17 | 0.4862 | 1.19 | 66.33 / 100 |
| **2** | **Verbruggen** (BHA £4.5m) | 2.79 / 1.21 | **Lammens** (MUN £5.0m) | 2.47 / 1.22 | **£9.5m** | **6.219** | **38.77 xP** | 2.37 | 0.4549 | 0.00 | 67.70 / 100 |
| **3** | **Verbruggen** (BHA £4.5m) | 2.79 / 1.21 | **Pope** (NEW £5.0m) | 3.32 / 1.42 | **£9.5m** | **6.212** | **38.73 xP** | 2.21 | 0.4931 | 0.00 | 66.86 / 100 |
| **4** | **Pope** (NEW £5.0m) | 3.32 / 1.42 | **Kinsky** (TOT £4.5m) | 1.43 / 1.00 | **£9.5m** | **6.199** | **38.65 xP** | 2.15 | 0.4497 | 0.50 | 66.75 / 100 |
| **5** | **Rushworth** (COV £4.5m) | 3.11 / 1.38 | **Sels** (NFO £5.0m) | 3.21 / 1.32 | **£9.5m** ⚠️ | **6.185** | **38.57 xP** | 2.07 | 0.5174 | 1.47 | 65.24 / 100 |
| **6** | **Rushworth** (COV £4.5m) | 3.11 / 1.38 | **Lammens** (MUN £5.0m) | 2.47 / 1.22 | **£9.5m** ⚠️ | **6.179** | **38.53 xP** | 2.28 | 0.4843 | 0.00 | 66.67 / 100 |
| **7** | **Sels** (NFO £5.0m) | 3.21 / 1.32 | **Kinsky** (TOT £4.5m) | 1.43 / 1.00 | **£9.5m** | **6.174** | **38.50 xP** | 2.25 | 0.4442 | 0.00 | 66.58 / 100 |
| **8** | **Rushworth** (COV £4.5m) | 3.11 / 1.38 | **Pope** (NEW £5.0m) | 3.32 / 1.42 | **£9.5m** ⚠️ | **6.147** | **38.34 xP** | 2.07 | 0.5248 | 0.00 | 65.50 / 100 |
| **9** | **Pope** (NEW £5.0m) | 3.32 / 1.42 | **Scherpen** (IPS £4.5m) | 1.90 / 1.38 | **£9.5m** ⚠️ | **6.124** | **38.20 xP** | 1.91 | 0.5284 | 1.03 | 64.34 / 100 |
| **10** | **Verbruggen** (BHA £4.5m) | 2.79 / 1.21 | **Roefs** (SUN £5.0m) | 3.11 / 1.31 | **£9.5m** | **6.065** | **37.85 xP** | 2.34 | 0.4768 | 0.00 | 65.56 / 100 |

#### **1.2 GW1–6 Top 10 PL-Proven Pairs (Excluding Promoted Proxies)**

| Rank | GKP 1 (Club, Price) | GKP 1 Rates (Saves / GC) | GKP 2 (Club, Price) | GKP 2 Rates (Saves / GC) | Total Price | OC-RQI | Rotated xP (max) | Exp CS | FOI | FDR Loss | RQI Score |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **1** | **Verbruggen** (BHA £4.5m) | 2.79 / 1.21 | **Sels** (NFO £5.0m) | 3.21 / 1.32 | **£9.5m** | **6.227** | **38.82 xP** | 2.17 | 0.4862 | 1.19 | 66.33 / 100 |
| **2** | **Verbruggen** (BHA £4.5m) | 2.79 / 1.21 | **Lammens** (MUN £5.0m) | 2.47 / 1.22 | **£9.5m** | **6.219** | **38.77 xP** | 2.37 | 0.4549 | 0.00 | 67.70 / 100 |
| **3** | **Verbruggen** (BHA £4.5m) | 2.79 / 1.21 | **Pope** (NEW £5.0m) | 3.32 / 1.42 | **£9.5m** | **6.212** | **38.73 xP** | 2.21 | 0.4931 | 0.00 | 66.86 / 100 |
| **4** | **Pope** (NEW £5.0m) | 3.32 / 1.42 | **Kinsky** (TOT £4.5m) | 1.43 / 1.00 | **£9.5m** | **6.199** | **38.65 xP** | 2.15 | 0.4497 | 0.50 | 66.75 / 100 |
| **5** | **Sels** (NFO £5.0m) | 3.21 / 1.32 | **Kinsky** (TOT £4.5m) | 1.43 / 1.00 | **£9.5m** | **6.174** | **38.50 xP** | 2.25 | 0.4442 | 0.00 | 66.58 / 100 |
| **6** | **Verbruggen** (BHA £4.5m) | 2.79 / 1.21 | **Roefs** (SUN £5.0m) | 3.11 / 1.31 | **£9.5m** | **6.065** | **37.85 xP** | 2.34 | 0.4768 | 0.00 | 65.56 / 100 |
| **7** | **Martinez** (AVL £5.0m) | 3.02 / 1.24 | **Kinsky** (TOT £4.5m) | 1.43 / 1.00 | **£9.5m** | **6.004** | **37.48 xP** | 2.19 | 0.4363 | 0.58 | 64.01 / 100 |
| **8** | **Leno** (FUL £4.5m) | 2.58 / 1.34 | **Sels** (NFO £5.0m) | 3.21 / 1.32 | **£9.5m** | **5.999** | **37.45 xP** | 1.94 | 0.5410 | 0.69 | 61.87 / 100 |
| **9** | **Verbruggen** (BHA £4.5m) | 2.79 / 1.21 | **Kinsky** (TOT £4.5m) | 1.43 / 1.00 | 🔥 **£9.0m** | **5.992** | **36.68 xP** | 2.44 | 0.4261 | 0.39 | 68.57 / 100 |
| **10** | **Petrović** (BOU £4.5m) | 2.87 / 1.42 | **Pope** (NEW £5.0m) | 3.32 / 1.42 | **£9.5m** | **5.987** | **37.38 xP** | 1.66 | 0.5884 | 0.95 | 59.95 / 100 |

---

### 2. Full Season Horizon (GW1–38, Horizon-Matched Rotated xP)

#### **2.1 Full Season Top 10 Overall Pairs**

| Rank | GKP 1 (Club, Price) | GKP 1 Rates (Saves / GC) | GKP 2 (Club, Price) | GKP 2 Rates (Saves / GC) | Total Price | OC-RQI | Rotated xP (max) | Exp CS | FOI | FDR Loss | RQI Score |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **1** | **Sels** (NFO £5.0m) | 3.21 / 1.32 | **Kinsky** (TOT £4.5m) | 1.43 / 1.00 | **£9.5m** | **6.142** | **242.62 xP** | 14.52 | 0.4457 | 1.90 | 66.33 / 100 |
| **2** | **Martinez** (AVL £5.0m) | 3.02 / 1.24 | **Leno** (FUL £4.5m) | 2.58 / 1.34 | **£9.5m** | **6.121** | **241.82 xP** | 13.29 | 0.5062 | 1.62 | 64.62 / 100 |
| **3** | **Petrović** (BOU £4.5m) | 2.87 / 1.42 | **Sels** (NFO £5.0m) | 3.21 / 1.32 | **£9.5m** | **6.105** | **241.23 xP** | 12.65 | 0.5336 | 2.00 | 64.16 / 100 |
| **4** | **Kinsky** (TOT £4.5m) | 1.43 / 1.00 | **Roefs** (SUN £5.0m) | 3.11 / 1.31 | **£9.5m** | **6.103** | **241.16 xP** | 14.72 | 0.4481 | 0.96 | 65.72 / 100 |
| **5** | **Martinez** (AVL £5.0m) | 3.02 / 1.24 | **Petrović** (BOU £4.5m) | 2.87 / 1.42 | **£9.5m** | **6.073** | **240.00 xP** | 12.76 | 0.5186 | 1.63 | 63.71 / 100 |
| **6** | **Martinez** (AVL £5.0m) | 3.02 / 1.24 | **Kinsky** (TOT £4.5m) | 1.43 / 1.00 | **£9.5m** | **6.070** | **239.87 xP** | 14.13 | 0.4375 | 1.21 | 64.76 / 100 |
| **7** | **Leno** (FUL £4.5m) | 2.58 / 1.34 | **Kinsky** (TOT £4.5m) | 1.43 / 1.00 | 🔥 **£9.0m** | **6.057** | **234.77 xP** | 15.27 | 0.4538 | 2.13 | 68.61 / 100 |
| **8** | **Lammens** (MUN £5.0m) | 2.47 / 1.22 | **Kinsky** (TOT £4.5m) | 1.43 / 1.00 | **£9.5m** | **6.037** | **238.63 xP** | 15.12 | 0.4289 | 0.73 | 65.10 / 100 |
| **9** | **Leno** (FUL £4.5m) | 2.58 / 1.34 | **Sels** (NFO £5.0m) | 3.21 / 1.32 | **£9.5m** | **6.031** | **238.39 xP** | 12.69 | 0.5243 | 2.33 | 63.12 / 100 |
| **10** | **Kelleher** (BRE £5.0m) | 2.95 / 1.32 | **Kinsky** (TOT £4.5m) | 1.43 / 1.00 | **£9.5m** | **6.016** | **237.85 xP** | 14.24 | 0.4510 | 4.83 | 64.04 / 100 |

#### **2.2 Full Season Top 10 PL-Proven Pairs (Excluding Promoted Proxies)**

| Rank | GKP 1 (Club, Price) | GKP 1 Rates (Saves / GC) | GKP 2 (Club, Price) | GKP 2 Rates (Saves / GC) | Total Price | OC-RQI | Rotated xP (max) | Exp CS | FOI | FDR Loss | RQI Score |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **1** | **Sels** (NFO £5.0m) | 3.21 / 1.32 | **Kinsky** (TOT £4.5m) | 1.43 / 1.00 | **£9.5m** | **6.142** | **242.62 xP** | 14.52 | 0.4457 | 1.90 | 66.33 / 100 |
| **2** | **Martinez** (AVL £5.0m) | 3.02 / 1.24 | **Leno** (FUL £4.5m) | 2.58 / 1.34 | **£9.5m** | **6.121** | **241.82 xP** | 13.29 | 0.5062 | 1.62 | 64.62 / 100 |
| **3** | **Petrović** (BOU £4.5m) | 2.87 / 1.42 | **Sels** (NFO £5.0m) | 3.21 / 1.32 | **£9.5m** | **6.105** | **241.23 xP** | 12.65 | 0.5336 | 2.00 | 64.16 / 100 |
| **4** | **Kinsky** (TOT £4.5m) | 1.43 / 1.00 | **Roefs** (SUN £5.0m) | 3.11 / 1.31 | **£9.5m** | **6.103** | **241.16 xP** | 14.72 | 0.4481 | 0.96 | 65.72 / 100 |
| **5** | **Martinez** (AVL £5.0m) | 3.02 / 1.24 | **Petrović** (BOU £4.5m) | 2.87 / 1.42 | **£9.5m** | **6.073** | **240.00 xP** | 12.76 | 0.5186 | 1.63 | 63.71 / 100 |
| **6** | **Martinez** (AVL £5.0m) | 3.02 / 1.24 | **Kinsky** (TOT £4.5m) | 1.43 / 1.00 | **£9.5m** | **6.070** | **239.87 xP** | 14.13 | 0.4375 | 1.21 | 64.76 / 100 |
| **7** | **Leno** (FUL £4.5m) | 2.58 / 1.34 | **Kinsky** (TOT £4.5m) | 1.43 / 1.00 | 🔥 **£9.0m** | **6.057** | **234.77 xP** | 15.27 | 0.4538 | 2.13 | 68.61 / 100 |
| **8** | **Lammens** (MUN £5.0m) | 2.47 / 1.22 | **Kinsky** (TOT £4.5m) | 1.43 / 1.00 | **£9.5m** | **6.037** | **238.63 xP** | 15.12 | 0.4289 | 0.73 | 65.10 / 100 |
| **9** | **Leno** (FUL £4.5m) | 2.58 / 1.34 | **Sels** (NFO £5.0m) | 3.21 / 1.32 | **£9.5m** | **6.031** | **238.39 xP** | 12.69 | 0.5243 | 2.33 | 63.12 / 100 |
| **10** | **Kelleher** (BRE £5.0m) | 2.95 / 1.32 | **Kinsky** (TOT £4.5m) | 1.43 / 1.00 | **£9.5m** | **6.016** | **237.85 xP** | 14.24 | 0.4510 | 4.83 | 64.04 / 100 |

---

### 3. Top Pairings by Budget Tier & Risk Category

#### **Tier A: Premier League Proven Rotation Pairs (£9.5m)**
- **Verbruggen (BHA £4.5m) + Sels (NFO £5.0m)**: GW1–6 leader under OC-RQI (**6.227**, **38.82 xP**, **2.17 Exp CS**). Note that following max(xP) saves **+1.19 xP** vs legacy FDR-min picks.
- **Verbruggen (BHA £4.5m) + Lammens (MUN £5.0m)**: Premier clean-sheet pairing (**2.37 Exp CS**, **38.77 xP**, FOI **0.4549**).
- **Sels (NFO £5.0m) + Kinsky (TOT £4.5m)**: Full-season champion (**OC-RQI 6.142**, **242.62 xP**, **14.52 Exp CS**).

#### **Tier B: £9.0m Budget Pairs (Double £4.5m)**
- **Verbruggen (BHA £4.5m) + Kinsky (TOT £4.5m)**: Highest GW1–6 budget pair (**36.68 xP**, **2.44 Exp CS**, **RQI 68.57**).
- **Leno (FUL £4.5m) + Kinsky (TOT £4.5m)**: Full-season £9.0m benchmark (**OC-RQI 6.057**, **234.77 xP**, **15.27 Exp CS**). Saves £0.5m with zero sacrifice in clean-sheet coverage.

---

## Pre-WC Bench Boost Pairings vs Post-WC4 Structural Archetypes

Strategic linkage: [First-Half Chip Strategy](../fpl-first-half-chip-strategy/fpl-first-half-chip-strategy.md) establishes **BB2 + TC3 (Haaland) + WC4 Opt1** (Scenario S13, **340.14 xP**) as repo baseline. Decouples goalkeeper planning into two distinct structural phases:

```
Pre-WC Sprint (GW1–3)                       Post-WC4 Horizon (GW4–19 / Full Season)
┌────────────────────────────────────────┐  Wildcard  ┌────────────────────────────────────────┐
│ Dual Active Starters (BB Enabler)      │ ─────────> │ Choose Archetype A or Archetype B      │
│ • £5.0m+£4.5m / £5.5m+£5.0m / £4.5m+£4.5m│    GW4    │ A: Premium/Mid Starter + £4.0m Fodder  │
│ • Target GW2 BB home/easy fixtures     │            │ B: Active 2-GKP Rotation (£9.0m–£9.5m) │
└────────────────────────────────────────┘            └────────────────────────────────────────┘
```

---

### 1. Pre-WC (GW1–3 Sprint): Dual Active Starters for Bench Boost

Bench Boost deployment in GW2 (or GW1) requires **two genuine starting goalkeepers**. Non-playing £4.0m backups strictly forfeit 4–8 chip points during the sprint.

#### Top Pre-WC GKP Pairings (GW1–3 Sprint Evaluation):

| Pair | Price Tier | GW1 xP (Best) | GW2 GKP1 xP | GW2 GKP2 xP | GW2 BB Combined | GW3 xP (Best) | GW1–3 Sprint EV (BB2) | Key Matchup Strengths & Fixture Profile |
|---|---|---|---|---|---|---|---|---|
| **Donnarumma** (MCI £5.5m) + **Roefs** (SUN £5.0m) | £10.5m (S13 Winner) | 6.74 (SUN vs IPS) | 5.97 (MCI @ CRY) | 6.75 (SUN vs FUL) | **12.71 xP** | 7.05 (MCI vs COV) | **26.50 xP** | S13 MILP choice. GW2: SUN home vs FUL (diff 2) + MCI away vs CRY. GW3: MCI home vs promoted COV (diff 2). Max raw points ceiling. |
| **Lammens** (MUN £5.0m) + **Roefs** (SUN £5.0m) | £10.0m (S9 Winner) | 7.04 (MUN @ HUL) | 6.72 (MUN vs IPS) | 6.75 (SUN vs FUL) | **13.47 xP** | 5.82 (MUN @ EVE) | **26.32 xP** | S9 FH3 choice. GW2: Dual home vs promoted/relegation tier (MUN vs IPS diff 2 + SUN vs FUL diff 2). Highest GW2 BB sum. |
| **Verbruggen** (BHA £4.5m) + **Lammens** (MUN £5.0m) | **£9.5m** (PL-Proven #1) | 7.04 (MUN @ HUL) | 4.70 (BHA @ CHE) | 6.72 (MUN vs IPS) | **11.42 xP** | 6.66 (BHA vs LEE) | **25.12 xP** | Top budget-preserving PL pair. GW1: MUN away @ HUL (diff 2). GW2: MUN home vs IPS (diff 2). GW3: BHA home vs LEE (diff 2). Zero tough fixtures started. |
| **Rushworth** (COV £4.5m) + **Lammens** (MUN £5.0m) | **£9.5m** ⚠️ (Promoted/PL) | 7.04 (MUN @ HUL) | 4.57 (COV vs HUL) | 6.72 (MUN vs IPS) | **11.29 xP** | 6.54 (COV @ MCI saves) | **24.86 xP** | GW2 dual home clash: COV vs HUL (diff 2) + MUN vs IPS (diff 2). High save-volume upside for Rushworth GW3 @ MCI. |
| **Petrović** (BOU £4.5m) + **Scherpen** (IPS £4.5m) | 🔥 **£9.0m** ⚠️ (Double £4.5m) | 6.03 (IPS vs SUN) | 5.60 (BOU vs EVE) | 4.58 (IPS @ MUN) | **10.18 xP** | 5.55 (BOU @ NEW) | **21.76 xP** | Lowest cost starter pair. Unlocks £1.0m–£1.5m outfield budget pre-WC. GW1: IPS home vs SUN. GW2: BOU home vs EVE. |
| **Verbruggen** (BHA £4.5m) + **Kinsky** (TOT £4.5m) | 🔥 **£9.0m** (PL Double £4.5m) | 5.77 (TOT @ BRE) | 4.70 (BHA @ CHE) | 6.54 (TOT vs NEW) | **11.24 xP** | 6.66 (BHA vs LEE) | **23.67 xP** | Best PL-proven £9.0m pair. GW2: TOT home vs NEW (6.54 xP). GW3: BHA home vs LEE (6.66 xP). |

---

### 2. Post-WC4 (GW4–19 / Full Season): Structural Archetypes

GW4 Wildcard wipes pre-season squad constraints, resetting goalkeeper architecture. Two structural paths:

#### **Archetype A: Single Starter + £4.0m Non-Playing Fodder (Budget Liberation — Recommended)**
- **Structure**: Single premium or mid starter (£5.0m–£6.0m, e.g. **Raya £6.0m ARS** or **Donnarumma £5.5m MCI**) + £4.0m non-playing reserve (e.g. Dennis/Fabianski stubs). Total GKP spend: £8.5m–£10.0m.
- **Budget dynamic**: Frees **£0.5m–£1.0m** vs active 2-GKP rotation. Reinvests capital directly into premium outfield core (**Haaland £15.5m**, **Palmer £9.5m**, **Gabriel £8.0m**, **Sarr £6.5m**, **Tzolis £6.5m** per MILP WC4 Opt1).
- **Outfield dividend**: Outfield points per £1.0m and captaincy leverage outpace modest GKP rotation deltas (+7.1 pts full season / +0.19 pts/GW).
- **Operational benefit**: Zero bench selection error; eliminates points benched on double-digit hauls.

#### **Archetype B: Active 2-GKP Rotation (£9.0m–£9.5m / Continuous Coverage)**
- **Structure**: Retain two active £4.5m–£5.0m starting goalkeepers (e.g. **Verbruggen £4.5m + Lammens £5.0m** at £9.5m, **Leno £4.5m + Kinsky £4.5m** at £9.0m, or MILP Opt1 draft **Raya £6.0m + Kinsky £4.5m** at £10.5m).
- **Fixture agility**: Enables weekly FDR-min targeting across GW4–19 (dodging top-6 attack encounters).
- **Opportunity cost**: £0.5m–£1.0m idle capital tied on bench. Viable only when committed to top-5 RQI complementary pairing (e.g. Verbruggen+Lammens, $r = -0.417$, 55.3% easy fixtures).

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

1. **Pre-WC Phase (GW1–3 BB Sprint)**: Deploy active starter pair (Donnarumma+Roefs £10.5m for max EV / S13; Verbruggen+Lammens £9.5m for PL-proven balance; Petrović+Scherpen £9.0m for budget ceiling). Both goalkeepers must start to capture GW2 Bench Boost returns.
2. **Post-WC Phase (GW4–19 / Full Season Archetypes)**:
   - **Archetype A (Recommended Default)**: Pivot to Starter + £4.0m Fodder (e.g. Raya £6.0m / Donnarumma £5.5m + £4.0m). Reallocates £0.5m–£1.0m to outfield premiums (Haaland/Palmer/Saka/Gabriel) per MILP WC4 Opt1.
   - **Archetype B (Alternative)**: Retain £9.0m–£9.5m active rotation (Verbruggen+Lammens, Leno+Kinsky) only when targeting specific fixture swing coverage and accepting bench capital drag.
3. **Historical Reality Check**: 2025/26 archive backtest confirms unrotated premium S&F (144.0 pts) and solo budget S&F (119.7 pts) beat average pair rotation (126.8 pts) after accounting for £0.5m+ outfield reinvestment.
4. **Method note**: Forward RQI uses horizon-matched hybrid xP under forced flat-90 starter minutes; rankings indicate pair complementarity, not absolute realized score levels.

---

## Risks and unknowns

- Flat-90 minutes ignore injury / glove-share (Pope, Kinsky, promoted Regulars).
- $S_{\text{tot_xp}}$ saturation on 2.5–4.2 scale under hybrid flat-90.
- Promoted proxy rates (Rushworth/COV, Scherpen/IPS) are career + destination GC; Scherpen 1.90 saves/90 inflates RQI via FDR, not shot-stopping.
- FDR pick ≠ strength-multiplier scorer; intentional dual scale.
- DGW/BGW handled only as fixture-map rows present in processed fixtures.
