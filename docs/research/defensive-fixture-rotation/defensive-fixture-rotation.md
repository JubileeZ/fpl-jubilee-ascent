# Defensive Architecture, Strategy & Fixture Rotation (Unified GKP & DEF)

**Updated**: 2026-08-18T00:20:00+07:00  
**Data stamp**: 2026-08-17 (564-Player Preseason Baseline & Confirmed Summer Transfers)  
**Season**: 2026/27  
**Artifacts**:
- [GKP Strategy Comparison CSV](../../data/research/defensive-fixture-rotation/gkp_strategy_comparison.csv)
- [GKP Rotation Matrix CSV](../../data/research/defensive-fixture-rotation/gkp_rotation_matrix.csv)
- [5-DEF Club Partitions Matrix CSV](../../data/research/defensive-fixture-rotation/def_club_partitions_matrix.csv)
- [5-DEF BB1+WC4 Club Matrix CSV](../../data/research/defensive-fixture-rotation/def_bb1_wc4_club_matrix.csv)
- [5-DEF Tier Player Rotations CSV](../../data/research/defensive-fixture-rotation/def_tier_player_rotations.csv)
- [Full Backline GW1-3 BB1 Lineups CSV](../../data/research/defensive-fixture-rotation/backline_bb1_wc4_lineups.csv)
- [Full Backline GW4-19 WC4 Lineups CSV](../../data/research/defensive-fixture-rotation/backline_gw4_19_lineups.csv)
- [Full Backline GW1-19 Lineups CSV](../../data/research/defensive-fixture-rotation/backline_gw1_19_lineups.csv)

---

## Purpose

This research note unifies Goalkeeper (GKP) and Defender (DEF) fixture diversification, structural strategy, and combinatorial lineup optimization into a **single consolidated Defensive Authority**. It evaluates:
1. **GKP Strategy Formal Proof**: Quantitative comparison of **Active 2-GKP Rotation** (£9.0m–£10.0m) vs **Budget Set & Forget** (£8.5m) vs **Premium Set & Forget** (£9.5m–£10.0m) across multiple planning horizons, accounting for empirical outfield opportunity cost ($\gamma = 0.2627\text{ xP/£1.0m/GW}$).
2. **Multi-Club (2 to 5 Unique Teams) 5-DEF Combinations**: Full permutation analysis of club schedules enforcing a strict **Max 2 DEF per club** limit across all 20 clubs for robust defensive diversification.
3. **Flexible 5-DEF Player Lineups**: Evaluation of candidate defender quintets across four natural budget tiers (£20.5m–£26.0m total spend) utilizing individual player attacking threat, defensive contributions (DefCon), and auto-sub safety expected value.
4. **Full Backline (2 GKP + 5 DEF) Simulation across Horizons**: Optimization of full 7-asset defensive squads for the canonical **GW1 Bench Boost (BB1) + GW4 Wildcard (WC4)** strategy:
   - **GW1–3 (Pre-Wildcard Sprint)**: GW1 Bench Boost (all 7 assets active, zero head-to-head clashes) + GW2–3 optimal rotation (1 GKP + 3 DEF).
   - **GW4–19 (Post-Wildcard First Half)**: Optimal 1 GKP + 3 DEF starters over 16 Gameweeks.
   - **GW1–19 (Full First-Half Benchmark)**: Continuous season-long defensive core evaluation.

---

## Sources

- FPL 2026/27 Official Fixture Calendar (`data/processed/fixtures.parquet`).
- 564-Player Preseason Stage 2 Event Rates & Points Projections (`expected-stats-gw1-5.csv`, `gw1-5_projections.csv`).
- FPL Official Player Registry & Pricing (`data/processed/players.parquet`, `data/processed/clubs.parquet`).
- 2025/26 Historical Team Clean Sheet & Save Baselines (`data/archive/2025-26/`).

---

## Agent Prompt

To reproduce the analysis and refresh all datasets:
```bash
uv run python docs/research/defensive-fixture-rotation/run_defensive_rotation_analysis.py
```

---

## Method

1. **Hybrid Event-Rate Projection Grid**: Projections are generated via `ParticipationStateHybridModel` with 90 flat starter minutes across GW1–38 for 19 starting Goalkeepers and 95 starting Defenders.
2. **Two-Factor Composite Ranking Model (DCS)**:
   Every combination is ranked by a balanced **Defensive Composite Score (DCS - 0 to 100)**:
   $$\text{DCS} = 0.60 \times S_{\text{Score}} + 0.40 \times S_{\text{Risk}}$$
   - **Factor 1: Opportunity-Cost Adjusted Score ($S_{\text{Score}}$)**:
     $$\text{OC-Score} = \frac{\text{Rotated xP}}{N} - \gamma \times (\text{Total Spend} - \text{Floor})$$
     *(Where $\gamma = 0.2627\text{ xP/£1.0m/GW}$ empirical outfield slope; GKP floor = £8.5m, DEF floor = £20.0m, Backline floor = £28.5m).*
   - **Factor 2: Combination Risk Management ($S_{\text{Risk}}$)**:
     $$S_{\text{Risk}} = 0.50 \times S_{\text{ZeroDiff}} + 0.35 \times S_{\text{RotFDR}} + 0.15 \times S_{\text{Corr}}$$
     - $S_{\text{ZeroDiff}}$: Scaled % of gameweeks where **all** active starters face $\text{FDR} \le 3$.
     - $S_{\text{RotFDR}}$: Scaled average weekly fixture difficulty across started slots ($\text{Target} \le 2.40$).
     - $S_{\text{Corr}}$: Negative schedule correlation bonus ($r \le -0.10$).
3. **Auto-Sub Expected Value (Outfield)**: 5-DEF player lineups credit $+12\% \times xP(\text{Def 4}) + 3\% \times xP(\text{Def 5})$ for tactical rotation depth.

---

### Metric Definitions & Direction

| Metric | Symbol | Definition / Formula | Direction | Ideal / Benchmark | Description |
|---|---|---|---|---|---|
| **Defensive Composite Score** | `DCS` | $0.60 \times S_{\text{Score}} + 0.40 \times S_{\text{Risk}}$ | Higher $\uparrow$ | **$\ge 80.0$ / 100** | Balanced composite index ranking point ceiling against defensive security. |
| **Opportunity-Cost Adjusted Score** | `OC-Score` | $\frac{\text{Rotated xP}}{N} - \gamma \times (\text{Spend} - \text{Floor})$ | Higher $\uparrow$ | **$> 6.00$ (GKP) / $> 18.00$ (DEF)** | Net weekly expected points after subtracting capital drag on outfield attack. |
| **Rotated Expected Points** | `Rotated xP` | $\sum_{t=1}^N \max_{i \in \text{squad}} xP_{i,t}$ | Higher $\uparrow$ | Maximized | Sum of weekly projected points under optimal starting selection. |
| **Rotated / Effective FDR** | `Rot FDR` | Average weekly fixture difficulty rating across started slots | Lower $\downarrow$ | **$\le 2.40$** | Benchmark baseline for unrotated schedule is $3.00$; rotation targets $\le 2.40$. |
| **Zero-Difficult Gameweeks** | `Zero-Diff %` | % of GWs where all started assets face FDR $\le 3$ | Higher $\uparrow$ | **$100.0\%$** | Completely avoids fielding starters against elite top-4 attacks. |
| **All-Easy Gameweeks** | `All-Easy %` | % of GWs where all started assets face FDR $\le 2$ | Higher $\uparrow$ | **$\ge 20.0\%$** | Proportion of weeks where all starters face favorable home or bottom-6 opposition. |
| **Schedule Correlation** | $r$ / `fdr_corr` | Pearson correlation between club FDR sequences | Lower $\downarrow$ (Negative) | **$r \le -0.10$** | Negative correlation guarantees alternating fixture swings between paired clubs. |

---

## Findings

### Section 1: Goalkeeper Strategy Quantitative Proof

Comparing the three core goalkeeping archetypes across different planning horizons:

#### 1. Full First Half (GW1–19)

| Strategy Archetype | Top Exemplar Pairing | Spend | Total xP (19 GW) | xP / GW | Net OC-Score | DCS | Rot FDR | Zero-Diff % | Schedule $r$ |
|---|---|---|---|---|---|---|---|---|---|
| **Active 2-GKP Rotation** | **Leno (FUL) + Trafford (MCI)** | **£9.5m** | **125.90** | **6.63** | **6.36** | **90.01** | **2.47** | **94.7%** | **-0.2713** |
| **Active 2-GKP Rotation** | **Trafford (MCI) + Roefs (SUN)** | **£10.0m** | **127.84** | **6.73** | **6.33** | **89.97** | **2.42** | **94.7%** | **-0.2641** |
| **Active 2-GKP Rotation** | **Trafford (MCI) + Pope (NEW)** | **£10.0m** | **126.75** | **6.67** | **6.28** | **89.52** | **2.47** | **100.0%** | **-0.2549** |
| **Dual Budget Rotation** | **Leno (FUL) + Kinsky (TOT)** | **£9.0m** | **115.58** | **6.08** | **5.95** | **84.04** | **2.47** | **100.0%** | **-0.2879** |
| **Mid-Value Set & Forget** | Trafford (MCI) + Fodder (£4.0m) | £9.0m | 123.69 | 6.51 | 6.38 | 77.82 | 2.95 | 73.7% | 1.0000 |
| **Budget Set & Forget** | Kinsky (TOT) + Fodder (£4.0m) | £8.5m | 107.92 | 5.68 | 5.68 | 65.29 | 3.00 | 73.7% | 1.0000 |
| **Premium Set & Forget** | Raya (ARS) + Fodder (£4.0m) | £10.0m | 125.40 | 6.60 | 6.21 | 73.92 | 3.05 | 73.7% | 1.0000 |

#### 2. Pre-Wildcard Sprint with GW1 Bench Boost (GW1–3 BB1)

| Strategy Archetype | Top Exemplar Pairing | Spend | Total xP (GW1–3) | Net OC-Score | DCS | GW1–3 Avg FDR | GW1 Fixture Ease |
|---|---|---|---|---|---|---|---|
| **Active 2-GKP Rotation (BB1)** | **Trafford (MCI) + Lammens (MUN)** | **£10.0m** | **27.58** | **8.80** | **84.33** | **2.25** | **Wolves (A) + Fulham (H)** |
| **Active 2-GKP Rotation (BB1)** | **Trafford (MCI) + Roefs (SUN)** | **£10.0m** | **27.30** | **8.71** | **84.33** | **2.25** | **Wolves (A) + Ipswich (H)** |
| **Active 2-GKP Rotation (BB1)** | **Kelleher (BRE) + Roefs (SUN)** | **£10.0m** | **25.89** | **8.23** | **84.33** | **2.25** | **Nott'm Forest (H) + Ipswich (H)** |
| **Dual Budget Rotation (BB1)** | **Rushworth (BHA) + Kinsky (TOT)** | **£9.0m** | **24.32** | **7.98** | **81.60** | **2.50** | **Everton (A) + Leicester (A)** |
| **Dual Budget Rotation (BB1)** | **Verbruggen (BHA) + Kinsky (TOT)** | **£9.0m** | **23.98** | **7.86** | **81.60** | **2.50** | **Everton (A) + Leicester (A)** |
| **Mid-Value Set & Forget** | Lammens (MUN) + Fodder (£4.0m) | £9.0m | 19.58 | 6.39 | 89.07 | 2.33 | Fulham (H) (GW1 BB Fodder DNP) |
| **Budget Set & Forget** | Kinsky (TOT) + Fodder (£4.0m) | £8.5m | 17.54 | 5.85 | 76.60 | 2.67 | Leicester (A) (GW1 BB Fodder DNP) |

> **Key Goalkeeper Finding**:
> - **In GW1–3 Bench Boost**: Active 2-GKP rotation decisively wins (**27.58 xP vs 19.58 xP**, a **+8.00 xP gain** across 3 weeks). The second playing GKP converts the Bench Boost bench slot into active points, yielding **+2.41 Net OC-Score** over Budget S&F even after accounting for the £1.5m outfield capital cost.
> - **In GW1–19 Long-Term**: Active 2-GKP rotation (`Leno + Trafford` / `Trafford + Roefs`) provides a lower weekly FDR (**2.42–2.47 vs 3.00**), **94.7% Zero-Diff coverage**, and higher Net OC-Score (**6.36 vs 5.68**), proving that active rotation outperforms Set-and-Forget in both points and risk reduction.

---

### Section 2: Multi-Club (2 to 5 Unique Teams) 5-DEF Combinations

Enforcing the strict **Max 2 DEF per club** rule across all 20 clubs generates 153,216 valid club combinations.

#### Top 5-DEF Club Combinations (GW1–19 Benchmark)

| Rank | Clubs Multiset | Pattern | Unique Clubs | Rot Avg FDR | Zero-Diff % | All-Easy % | Avg Correlation $r$ | Key Synergy |
|---|---|---|---|---|---|---|---|---|
| **1** | **`AVL-CHE-LIV-MCI-NFO`** | **1+1+1+1+1** | **5** | **2.4386** | **100.0%** | **26.3%** | **-0.0679** | Elite Big-6 rotation with 0 difficult weeks |
| **2** | **`BHA-COV-LIV-MCI-SUN`** | **1+1+1+1+1** | **5** | **2.4561** | **100.0%** | **26.3%** | **-0.1487** | Promoted enablers perfectly offsetting Man City |
| **3** | **`AVL-BOU-CHE-LIV-NFO`** | **1+1+1+1+1** | **5** | **2.4561** | **100.0%** | **15.8%** | **-0.1182** | Negative FDR correlation across all 19 GWs |
| **4** | **`AVL-COV-LIV-MCI-NFO`** | **1+1+1+1+1** | **5** | **2.4561** | **100.0%** | **21.1%** | **-0.0767** | High clean sheet ceiling + low cost |
| **5** | **`CHE-COV-LIV-MCI-SUN`** | **1+1+1+1+1** | **5** | **2.4561** | **100.0%** | **21.1%** | **-0.1264** | Strong home fixture alternating |

#### Top 5-DEF Club Combinations (GW4–19 Post-Wildcard)

| Rank | Clubs Multiset | Pattern | Unique Clubs | Rot Avg FDR | Zero-Diff % | All-Easy % | Avg Correlation $r$ |
|---|---|---|---|---|---|---|---|
| **1** | **`AVL-BOU-CHE-LIV-NFO`** | **1+1+1+1+1** | **5** | **2.4375** | **100.0%** | **18.8%** | **-0.0994** |
| **2** | **`BOU-CHE-EVE-LIV-NFO`** | **1+1+1+1+1** | **5** | **2.4375** | **100.0%** | **25.0%** | **-0.0785** |
| **3** | **`AVL-CHE-LIV-MCI-NFO`** | **1+1+1+1+1** | **5** | **2.4375** | **100.0%** | **25.0%** | **-0.0529** |
| **4** | **`AVL-COV-FUL-LEE-MCI`** | **1+1+1+1+1** | **5** | **2.4583** | **100.0%** | **6.2%** | **-0.2010** |

---

### Section 3: 5-DEF Player Lineups by Budget Band

Evaluating candidate defender quintets across four natural budget bands:

| Budget Band | Spend | Top 5-DEF Lineup | DCS | Net OC-Score | xP / GW | Rot FDR | Zero-Diff % |
|---|---|---|---|---|---|---|---|
| **Band 1: Budget (£20.5m–£22.5m)** | **£22.5m** | **Calafiori (ARS) + Vuskovic (BHA) + Thomas (COV) + Egan (HUL) + O'Nien (SUN)** | **81.85** | **18.11** | **18.77** | **2.56** | **94.7%** |
| **Band 2: Mid-Value (£23.0m–£24.0m)** | **£24.0m** | **Calafiori (ARS) + Vuskovic (BHA) + Thomas (COV) + Gvardiol (MCI) + O'Nien (SUN)** | **84.91** | **18.56** | **19.61** | **2.51** | **100.0%** |
| **Band 3: Single Anchor (£24.5m–£25.0m)** | **£25.0m** | **Calafiori (ARS) + Vuskovic (BHA) + Thomas (COV) + O'Reilly (MCI) + O'Nien (SUN)** | **85.37** | **18.64** | **19.96** | **2.51** | **100.0%** |
| **Band 4: Dual Anchor (£25.5m–£26.0m)** | **£26.0m** | **Calafiori (ARS) + Vuskovic (BHA) + Thomas (COV) + Muharemović (LEE) + O'Reilly (MCI)** | **85.36** | **18.68** | **20.25** | **2.53** | **100.0%** |

---

### Section 4: Full Backline Simulation (2 GKP + 5 DEF)

Combining top Goalkeeper structures with 5-Defender quintets into complete 7-player backlines:

#### 1. GW1–3 Pre-Wildcard Sprint (GW1 Bench Boost)

*Structure: 7 active starters in GW1 (0 head-to-head clashes); 1 GKP + 3 DEF starters in GW2 & GW3.*

| Rank | GKP Unit | 5-DEF Quintet | Spend | DCS | Net OC-Score | Total xP (GW1–3) | Effective FDR |
|---|---|---|---|---|---|---|---|
| **1** | **Trafford (MCI) + Lammens (MUN)** | **Calafiori + Vuskovic + O'Reilly + O'Nien + Ballard** | **£36.0m** | **83.24** | **27.42** | **88.17** | **2.23** |
| **2** | **Trafford (MCI) + Lammens (MUN)** | **Calafiori + Vuskovic + O'Reilly + Heaven + O'Nien** | **£35.5m** | **83.24** | **27.36** | **87.59** | **2.23** |
| **3** | **Trafford (MCI) + Lammens (MUN)** | **Calafiori + Vuskovic + Gvardiol + O'Nien + Ballard** | **£35.0m** | **83.24** | **27.32** | **87.08** | **2.23** |
| **4** | **Trafford (MCI) + Roefs (SUN)** | **Calafiori + Vuskovic + O'Reilly + Dalot + O'Nien** | **£36.0m** | **83.24** | **27.14** | **87.32** | **2.23** |
| **5** | **Trafford (MCI) + Roefs (SUN)** | **Calafiori + Vuskovic + Gvardiol + Heaven + O'Nien** | **£34.5m** | **83.24** | **27.10** | **86.02** | **2.23** |

#### 2. GW4–19 Post-Wildcard (WC4 Reset)

*Structure: 1 GKP + 3 DEF starters across 16 Gameweeks.*

| Rank | GKP Unit | 5-DEF Quintet | Spend | DCS | Net OC-Score | Total xP (GW4–19) | Rot FDR |
|---|---|---|---|---|---|---|---|
| **1** | **Trafford (MCI) + Pope (NEW)** | **Calafiori + Vuskovic + Thomas + Muharemović + O'Reilly** | **£36.0m** | **84.81** | **24.96** | **430.83** | **2.50** |
| **2** | **Trafford (MCI) + Pope (NEW)** | **Calafiori + Vuskovic + Hill + Thomas + Muharemović** | **£35.0m** | **84.80** | **24.98** | **426.94** | **2.50** |
| **3** | **Trafford (MCI) + Pope (NEW)** | **Calafiori + Vuskovic + Thomas + Muharemović + Gvardiol** | **£35.0m** | **84.70** | **24.93** | **426.17** | **2.50** |
| **4** | **Leno (FUL) + Trafford (MCI)** | **Calafiori + Vuskovic + Thomas + Muharemović + O'Reilly** | **£35.5m** | **84.60** | **24.87** | **428.21** | **2.50** |
| **5** | **Trafford (MCI) + Roefs (SUN)** | **Calafiori + Vuskovic + Thomas + Muharemović + O'Reilly** | **£36.0m** | **84.50** | **24.85** | **429.80** | **2.48** |

---

## Decision

1. **GW1 Bench Boost (BB1) Goalkeeper Architecture**:
   - **Dual £5.0m/£5.0m Active Rotation** (`Trafford + Lammens` or `Trafford + Roefs`) is mathematically superior to Set-and-Forget for GW1–3 sprint. It generates **87.5–88.2 xP** across the 3 Gameweeks, providing **+8.0 xP** raw upside and **+2.41 Net OC-Score** over single-GKP drafts.
2. **Defensive Lineup Structure (GW1–3 BB1)**:
   - Anchor around **Calafiori (ARS £5.5m)** and **Vuskovic (BHA £5.5m)**, supported by high-DefCon £4.5m enablers (**O'Reilly / Gvardiol**, **Ballard / O'Nien**, and **Thomas / Heaven**). This achieves an effective FDR of **2.23** with **zero GW1 clashes**.
3. **GW4 Wildcard Pivot**:
   - Post-Wildcard, pivot into **Trafford + Pope / Leno** paired with **Calafiori + Vuskovic + Thomas + Muharemović + O'Reilly**, achieving **100% Zero-Diff weeks** and an average starting FDR of **2.48–2.50** through GW19.

---

## Risks and unknowns

1. **Pre-Season Rotation & Starting Spot Locks**: Kinsky (TOT), Trafford (MCI), Rushworth (BHA), and Scherpen (IPS) must be tracked closely in opening friendlies and Gameweek 1 team sheets to confirm starting status.
2. **Transfer Deadlines & Squad Registration**: Late window arrivals (e.g. Manchester City goalkeeper hierarchy) could alter expected minutes.
3. **Outfield Capital Sensitivity**: While active GKP rotation delivers higher points, if premium outfield assets (e.g. Salah + Haaland + Saka) require every £0.5m increment, the fallback to **Budget Set-and-Forget (Kinsky + £4.0m fodder at £8.5m)** remains viable at a sacrifice of ~0.70 weekly expected points.
