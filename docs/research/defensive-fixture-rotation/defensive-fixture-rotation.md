# Defensive Architecture, Strategy & Fixture Rotation (Unified GKP & DEF)

**Updated**: 2026-08-18T15:05:00+07:00  
**Data stamp**: FPL API refresh 2026-08-18 (590 players; Trafford LEE, Rushworth COV); Stage 1 575 rows; Stage 2 ADR-0014 rates; CSVs re-audited 2026-08-18 vs `gkp_strategy_comparison.csv` / `def_club_partitions_matrix.csv` / backline CSVs  
**Season**: 2026/27  
**Status**: Active defensive authority. Supersedes archived `docs/archive/gkp-fixture-rotation/` and `docs/archive/def-fixture-rotation/`.  
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
1. **GKP Strategy Formal Proof**: Quantitative comparison of **Active 2-GKP Rotation** (£9.0m–£10.0m) vs **Budget Set & Forget** (£8.5m) vs **Premium Set & Forget** (£9.5m–£10.0m) across multiple planning horizons, accounting for empirical outfield opportunity cost ($\gamma = 0.2944\text{ xP/£1.0m/GW}$).
2. **Multi-Club (2 to 5 Unique Teams) 5-DEF Combinations**: Full permutation analysis of club schedules enforcing a strict **Max 2 DEF per club** limit across all 20 clubs for robust defensive diversification.
3. **Flexible 5-DEF Player Lineups**: Evaluation of candidate defender quintets across four natural budget tiers (£20.5m–£26.0m total spend) utilizing individual player attacking threat, defensive contributions (DefCon), and auto-sub safety expected value.
4. **Full Backline (2 GKP + 5 DEF) Simulation across Horizons**: Optimization of full 7-asset defensive squads for the canonical **GW1 Bench Boost (BB1) + GW4 Wildcard (WC4)** strategy:
   - **GW1–3 (Pre-Wildcard Sprint)**: GW1 Bench Boost (all 7 assets active, zero head-to-head clashes) + GW2–3 optimal rotation (1 GKP + 3 DEF).
   - **GW4–19 (Post-Wildcard First Half)**: Optimal 1 GKP + 3 DEF starters over 16 Gameweeks.
   - **GW1–19 (Full First-Half Benchmark)**: Continuous season-long defensive core evaluation.

---

## Sources

- FPL 2026/27 Official Fixture Calendar (`data/processed/fixtures.parquet`).
- 575-player Stage 2 Event Rates & Points Projections (`expected-stats-gw1-5.csv`; Draft shortlist export 234 rows).
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

1. **Hybrid Event-Rate Projection Grid**: Projections are generated via `ParticipationStateHybridModel` with 90 flat starter minutes across GW1–38 for 21 starting Goalkeepers and 93 starting Defenders. Club identity from live `players.parquet` after 2026-08-18 refresh (Trafford = LEE, Rushworth = COV).
2. **Two-Factor Composite Ranking Model (DCS)**:
   Every combination is ranked by a balanced **Defensive Composite Score (DCS - 0 to 100)**:
   $$\text{DCS} = 0.60 \times S_{\text{Score}} + 0.40 \times S_{\text{Risk}}$$
   - **Factor 1: Opportunity-Cost Adjusted Score ($S_{\text{Score}}$)**:
     $$\text{OC-Score} = \frac{\text{Rotated xP}}{N} - \gamma \times (\text{Total Spend} - \text{Floor})$$
     *(Where $\gamma = 0.2944\text{ xP/£1.0m/GW}$ empirical outfield slope; GKP floor = £8.5m, DEF floor = £20.0m, Backline floor = £28.5m).*
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
| **Fixture Overlap Index** | `FOI` | $\frac{1}{T}\sum (1 - p_{\text{cs1}})(1 - p_{\text{cs2}})$ | Lower $\downarrow$ | **$< 0.50$** | Joint clean-sheet failure probability for a GKP pair. Risk diagnostic, not the ranking metric. |

---

## Findings

### Section 1: Goalkeeper Strategy Quantitative Proof

Comparing the three core goalkeeping archetypes across different planning horizons:

#### 1. Full First Half (GW1–19)

| Strategy Archetype | Top Exemplar Pairing | Spend | Total xP (19 GW) | xP / GW | Net OC-Score | DCS | Rot FDR | Zero-Diff % |
|---|---|---|---|---|---|---|---|---|
| **Active 2-GKP Rotation** | **Rushworth (COV) + Donnarumma (MCI)** | **£10.0m** | **127.13** | **6.69** | **6.25** | **89.33** | **2.42** | **100.0%** |
| **Active 2-GKP Rotation** | **Leno (FUL) + Donnarumma (MCI)** | **£10.0m** | **126.53** | **6.66** | **6.22** | **87.50** | **2.47** | **94.7%** |
| **Active 2-GKP Rotation** | **Scherpen (IPS) + Donnarumma (MCI)** | **£10.0m** | **125.37** | **6.60** | **6.16** | **87.26** | **2.47** | **100.0%** |
| **Active 2-GKP Rotation** | **Verbruggen (BHA) + Donnarumma (MCI)** | **£10.0m** | **127.10** | **6.69** | **6.25** | **86.64** | **2.58** | **94.7%** |
| **Dual Budget Rotation** | **Verbruggen (BHA) + Rushworth (COV)** | **£9.0m** | **118.19** | **6.22** | **6.07** | **84.54** | **2.53** | **94.7%** |
| **Premium Set & Forget** | Donnarumma (MCI) + Fodder (£4.0m) | £9.5m | 125.37 | 6.60 | 6.30 | 76.53 | 2.95 | 73.7% |
| **Mid-Value Set & Forget** | Martinez (AVL) + Fodder (£4.0m) | £9.0m | 115.58 | 6.08 | 5.94 | 70.23 | 2.95 | 73.7% |
| **Budget Set & Forget** | Verbruggen (BHA) + Fodder (£4.0m) | £8.5m | 112.31 | 5.91 | 5.91 | 68.82 | 3.05 | 73.7% |

#### 2. Pre-Wildcard Sprint with GW1 Bench Boost (GW1–3 BB1)

| Strategy Archetype | Top Exemplar Pairing | Spend | Total xP (GW1–3) | Net OC-Score | DCS | GW1–3 Avg FDR |
|---|---|---|---|---|---|---|
| **Mid-Value Set & Forget** | **Lammens (MUN) + Fodder (£4.0m)** | **£9.0m** | **19.27** | **6.28** | **87.05** | **2.33** |
| **Premium Set & Forget** | Donnarumma (MCI) + Fodder (£4.0m) | £9.5m | 20.25 | 6.46 | 87.03 | 2.67 |
| **Mid-Value Set & Forget** | Roefs (SUN) + Fodder (£4.0m) | £9.0m | 19.26 | 6.27 | 87.00 | 2.33 |
| **Active 2-GKP Rotation (BB1)** | **Kelleher (BRE) + Roefs (SUN)** | **£10.0m** | **25.89** | **8.19** | **84.33** | **2.25** |
| **Active 2-GKP Rotation (BB1)** | **Kelleher (BRE) + Lammens (MUN)** | **£10.0m** | **25.86** | **8.18** | **84.33** | **2.25** |
| **Active 2-GKP Rotation (BB1)** | **Verbruggen (BHA) + Roefs (SUN)** | **£9.5m** | **26.08** | **8.40** | **83.93** | **2.25** |
| **Budget Set & Forget** | Kinsky (TOT) + Fodder (£4.0m) | £8.5m | 17.18 | 5.73 | 74.53 | 2.67 |

> **Key Goalkeeper Finding**:
> - **In GW1–3 Bench Boost**: DCS ranks cheaper S&F first (`Lammens + Fodder` **87.05**, `Donnarumma + Fodder` **87.03**) because $\gamma = 0.2944$ taxes the extra £1.5m. Active 2-GKP still wins raw points (**25.89–26.08 xP vs 19.27 xP**). Trafford is **Leeds** (GW1 Forest A).
> - **In GW1–19 Long-Term**: Active rotation (`Rushworth + Donnarumma` **127.13 xP**, DCS **89.33**) holds FDR **2.42** vs **2.95–3.05** S&F, with **100% Zero-Diff**. City's #1 is Donnarumma, not Trafford.

---

### Section 2: Multi-Club (2 to 5 Unique Teams) 5-DEF Combinations

Enforcing the strict **Max 2 DEF per club** rule across all 20 clubs generates 153,216 valid club combinations.

#### Top 5-DEF Club Combinations (GW1–19 Benchmark)

| Rank | Clubs Multiset | Pattern | Unique Clubs | Rot Avg FDR | Zero-Diff % | All-Easy % | Avg Correlation $r$ | Key Synergy |
|---|---|---|---|---|---|---|---|---|
| **1** | **`AVL-CHE-LIV-MCI-NFO`** | **1+1+1+1+1** | **5** | **2.4386** | **100.0%** | **26.3%** | **-0.0679** | Elite Big-6 rotation with 0 difficult weeks |
| **2** | **`BHA-COV-LIV-MCI-SUN`** | **1+1+1+1+1** | **5** | **2.4561** | **100.0%** | **26.3%** | **-0.1487** | Promoted enablers perfectly offsetting Man City |
| **3** | **`AVL-BOU-CHE-LIV-NFO`** | **1+1+1+1+1** | **5** | **2.4561** | **100.0%** | **15.8%** | **-0.1182** | Negative FDR correlation across all 19 GWs |
| **4** | **`AVL-CHE-COV-MCI-NFO`** | **1+1+1+1+1** | **5** | **2.4561** | **100.0%** | **15.8%** | **-0.0969** | High clean sheet ceiling + low cost |
| **5** | **`AVL-COV-LIV-MCI-NFO`** | **1+1+1+1+1** | **5** | **2.4561** | **100.0%** | **21.1%** | **-0.0767** | Strong home fixture alternating |

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
| **Band 1: Budget (£20.5m–£22.5m)** | **£22.5m** | **Calafiori (ARS) + Vuskovic (BHA) + Thomas (COV) + Mendy (HUL) + O'Nien (SUN)** | **80.84** | **17.93** | **18.67** | **2.56** | **100.0%** |
| **Band 2: Mid-Value (£23.0m–£24.0m)** | **£24.0m** | **Calafiori (ARS) + Vuskovic (BHA) + Thomas (COV) + Gvardiol (MCI) + O'Nien (SUN)** | **83.96** | **18.39** | **19.56** | **2.51** | **100.0%** |
| **Band 3: Single Anchor (£24.5m–£25.0m)** | **£25.0m** | **Calafiori (ARS) + Vuskovic (BHA) + Thomas (COV) + O'Reilly (MCI) + O'Nien (SUN)** | **84.26** | **18.44** | **19.91** | **2.51** | **100.0%** |
| **Band 4: Dual Anchor (£25.5m–£26.0m)** | **£26.0m** | **Calafiori (ARS) + Vuskovic (BHA) + Thomas (COV) + Muharemović (LEE) + O'Reilly (MCI)** | **84.12** | **18.45** | **20.22** | **2.53** | **100.0%** |

---

### Section 4: Full Backline Simulation (2 GKP + 5 DEF)

Combining top Goalkeeper structures with 5-Defender quintets into complete 7-player backlines:

#### 1. GW1–3 Pre-Wildcard Sprint (GW1 Bench Boost)

*Structure: 7 active starters in GW1 (0 head-to-head clashes); 1 GKP + 3 DEF starters in GW2 & GW3.*

| Rank | GKP Unit | 5-DEF Quintet | Spend | DCS | Net OC-Score | Total xP (GW1–3) | Effective FDR |
|---|---|---|---|---|---|---|---|
| **1** | **Lammens (MUN) + Fodder** | **Calafiori + Vuskovic + Thomas + O'Reilly + O'Nien** | **£34.0m** | **84.36** | **24.90** | **79.55** | **2.33** |
| **2** | **Roefs (SUN) + Fodder** | **Calafiori + Vuskovic + Thomas + O'Reilly + O'Nien** | **£34.0m** | **84.35** | **24.89** | **79.54** | **2.33** |
| **3** | **Donnarumma (MCI) + Fodder** | **Calafiori + Vuskovic + Thomas + O'Reilly + O'Nien** | **£34.5m** | **84.29** | **25.08** | **80.53** | **2.42** |
| **4** | **Lammens (MUN) + Fodder** | **Calafiori + Vuskovic + O'Reilly + O'Nien + Ballard** | **£35.0m** | **83.85** | **24.61** | **79.58** | **2.25** |
| **5** | **Lammens (MUN) + Fodder** | **Calafiori + Vuskovic + Thomas + Gvardiol + O'Nien** | **£33.0m** | **83.84** | **24.77** | **78.27** | **2.33** |

#### 2. GW4–19 Post-Wildcard (WC4 Reset)

*Structure: 1 GKP + 3 DEF starters across 16 Gameweeks.*

| Rank | GKP Unit | 5-DEF Quintet | Spend | DCS | Net OC-Score | Total xP (GW4–19) | Rot FDR |
|---|---|---|---|---|---|---|---|
| **1** | **Rushworth (COV) + Donnarumma (MCI)** | **Calafiori + Vuskovic + Thomas + Muharemović + Gvardiol** | **£35.0m** | **83.50** | **24.70** | **425.80** | **2.50** |
| **2** | **Rushworth (COV) + Donnarumma (MCI)** | **Calafiori + Vuskovic + Thomas + Muharemović + O'Reilly** | **£36.0m** | **83.50** | **24.70** | **430.51** | **2.50** |
| **3** | **Verbruggen (BHA) + Sels (NFO)** | **Calafiori + Vuskovic + Thomas + Muharemović + Gvardiol** | **£34.5m** | **83.42** | **24.54** | **420.84** | **2.50** |
| **4** | **Verbruggen (BHA) + Sels (NFO)** | **Calafiori + Vuskovic + Thomas + Muharemović + O'Reilly** | **£35.5m** | **83.42** | **24.54** | **425.55** | **2.50** |
| **5** | **Rushworth (COV) + Donnarumma (MCI)** | **Calafiori + Vuskovic + Hill + Thomas + Muharemović** | **£35.0m** | **83.32** | **24.68** | **425.47** | **2.50** |

---

---

### Section 5: 2025/26 GKP backtest (archive, not a 2026/27 forecast)

Moved from archived GKP note. Source: `data/archive/2025-26/processed/` via `docs/archive/gkp-fixture-rotation/run_historical_backtest.py`. Regular starters = ≥25 starts. Absolute 2026/27 hybrid xP (~230+ season) is a flat-90 upper bound; use this table for strategy value, not for this season's score forecast.

| Strategy Category | n | Avg Spend (incl. bench) | Avg 38-GW Pts | vs Premium S&F |
|---|---:|---:|---:|---:|
| Premium S&F (£5.5m+) | 3 | £9.80m | 144.0 | baseline |
| Solo £4.5m Budget S&F | 3 | £8.60m | 119.7 | −24.3 |
| All regular FDR pairs | 45 | £9.30m | 126.8 | −17.2 |
| Top 5 FDR pairs | 5 | £9.52m | 152.0 | +8.0 |
| All regular hindsight pairs | 45 | £9.30m | 168.4 | +24.4 |

Average FDR pair (+7.1 vs budget S&F) does not beat reinvesting £0.5m+ into outfield. Top-5 pairs did beat premium S&F. Matches DCS: S&F wins GW1–3 when $\gamma$ taxes the second starter; active rotation wins GW1–19 when complementarity is real.

---

### Section 6: Zero-diff + clean-sheet gate (club overlay)

Unordered 5-club sets. Filter 19/19 zero-diff. Sort all-easy desc, then `avg_fdr_corr` asc. CS gate: ≥2 CS-core (elite ARS/MCI + strong LIV/BHA/MUN/AVL) and ≤1 promoted (COV/HUL/IPS). Companions remain under `data/archive/def-fixture-rotation/` (`def_club_cs_priors.csv`, `def_gw1_19_zero_diff_cs_picks.csv`). Builder: `docs/archive/def-fixture-rotation/build_zero_diff_cs_picks.py`.

Does **not** replace §2 FDR-min #1 `AVL-CHE-LIV-MCI-NFO` (rot FDR **2.4386**, 100% zero-diff, 26.3% all-easy, $r = -0.0679$).

Start-here PICK (CS gate + fixture walk): `ARS-COV-LIV-MCI-SUN` · `AVL-CHE-LIV-MCI-NFO` · `BHA-COV-LIV-MCI-SUN`.

BB2 11-start overlays are historical (Canonical Preseason Chip Path is BB1). See archive.

---

## Decision

1. **GW1 Bench Boost (BB1) Goalkeeper Architecture**:
   - DCS ranks **Lammens / Roefs / Donnarumma + £4.0m fodder** first (DCS **84.36 / 84.35 / 84.29**, GW1–3 backline xP **79.55 / 79.54 / 80.53**). Active 2-GKP still leads raw backline xP (`Verbruggen + Roefs` **86.64 xP**, DCS **81.70**).
   - Canonical Preseason Chip Path keepers (**Raya + Donnarumma**) are the Stage 3 MILP 15-man pick, not this DCS ranking.
   - Do not draft Trafford as a City keeper. Live FPL: **LEE**, GW1 **Forest (A)**.
2. **Defensive Lineup Structure (GW1–3 BB1)**:
   - Anchor **Calafiori (ARS)** + **Vuskovic (BHA)** + **Thomas (COV)** + City enabler (**O'Reilly / Gvardiol**) + **O'Nien (SUN)**. Club-level FDR-min #1 remains `AVL-CHE-LIV-MCI-NFO`.
3. **GW4 Wildcard Pivot**:
   - **Rushworth (COV) + Donnarumma (MCI)** with **Calafiori + Vuskovic + Thomas + Muharemović + Gvardiol** (**425.80 xP**, DCS **83.50**) or **O'Reilly** (**430.51 xP**, same DCS). Rot FDR **2.50**. This is a Defensive Rotation Set, not a reprint of the Stage 3 15.

---

## Risks and unknowns

1. **Newcastle and Hull #1 splits**: Pope and Horníček both Regular; Tzolakis Regular vs injured Butland. FFS single-source — GW1 team sheets can flip the GKP pool.
2. **Rushworth (COV) Regular**: FFS XI only; Coventry vs Arsenal GW1 is FDR 5. Pairing with Donnarumma is a first-half construct, not a GW1 BB pick.
3. **Thin career packages**: 13 newly Draft-eligible outfield players sit on dest-GC position baselines (not FBref). GKP Tzolakis 1.72 sv/90 and Horníček 2.25 sv/90 are FootyMetrics/FootyStats 2025/26.
4. **Outfield capital**: $\gamma = 0.2944$ now taxes extra GKP spend harder than 0.2627. If Salah + Haaland + Saka need the £0.5m, S&F Lammens + fodder remains the DCS winner.
