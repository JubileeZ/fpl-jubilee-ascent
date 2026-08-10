# 5-Defender Fixture Diversification & Long-Term Rotation Study (GW1–19)

**Updated**: 2026-08-10T11:40:00+07:00  
**Data stamp**: FPL API processed snapshot + `expected-stats-gw1-5.csv` rates + `ParticipationStateHybridModel` GW1–38 flat-90 projections  
**Season**: 2026/27  
**Status**: Active  
**Purpose**: Identify optimal 5-defender (5 DEF) club combinations and starting lineups over the long term (GW1–19, with GW1–3 early launch and GW4–19 post-Wildcard sub-horizons) that maximize defensive fixture diversification, eliminate difficult fixtures (FDR $\ge 4$) across starting defenders, and optimize rotated expected points ($xP$) across multiple budget tiers.  
**Sources**: `data/processed/fixtures.parquet`, `data/processed/players.parquet`, `data/processed/clubs.parquet`, `data/research/gw1-6-preseason-pipeline/01-expected-role-gw1-5/expected-role-gw1-5.csv`, `data/research/gw1-6-preseason-pipeline/02-expected-stats-gw1-5/expected-stats-gw1-5.csv`  
**Artifacts**: [`def_club_5way_rotation_matrix.csv`](../../../data/research/def-fixture-rotation/def_club_5way_rotation_matrix.csv), [`def_tier_player_rotations.csv`](../../../data/research/def-fixture-rotation/def_tier_player_rotations.csv), [`def_bb1_wc4_club_matrix.csv`](../../../data/research/def-fixture-rotation/def_bb1_wc4_club_matrix.csv), [`def_bb1_wc4_tier_lineups.csv`](../../../data/research/def-fixture-rotation/def_bb1_wc4_tier_lineups.csv), [`def_performance_baseline.csv`](../../../data/research/def-fixture-rotation/def_performance_baseline.csv)  
**Script**: [`run_def_rotation_analysis.py`](run_def_rotation_analysis.py)  

---

## Agent Prompt & Risk Audit

```text
Full redo docs/research/def-fixture-rotation/def-fixture-rotation.md

1. Re-read fixture schedule and expected defender rates from data/research/gw1-6-preseason-pipeline/02-expected-stats-gw1-5/.
2. Run combinatorial simulation over all 15,504 5-club sets across GW1–3, GW4–19, GW1–19, and full season.
3. Simulate multi-tier player combinations across Tier 1 (Pure Budget £21.5m–£22.5m), Tier 2 (1 Anchor + 4 Budget £23.5m–£24.5m), and Tier 3 (2 Anchors + 3 Budget £25.5m–£26.5m).
4. Compute Points-Heavy DEF-RQI combining rotated xP, rotated FDR, zero difficult weeks guarantee, pairwise correlation, and budget efficiency.
5. Provide separate Overall and PL-Proven (0 promoted proxies) rankings.
6. Record durable findings in docs/research/def-fixture-rotation/ and data/research/def-fixture-rotation/.
```

---

## Method & Mathematical Framework

1. **Formation & Starting Spot Baseline**: Fixed 3 DEF starters each gameweek (standard 3-4-3 / 3-5-2 optimal FPL formation with 7 attacking spots).
2. **Weekly Starting Pick Rules**:
   - **Tier 1 (Pure Budget Rotation, 5x £4.0m–£4.5m)**: Select top 3 defenders with lowest fixture difficulty (FDR-min; hybrid $xP$ tiebreak).
   - **Tier 2 (1 Premium Anchor £5.5m–£6.5m + 4 Budget £4.0m–£4.5m)**: Premium Anchor starts 100% of gameweeks; top 2 budget defenders rotate into the remaining 2 starting spots by lowest FDR.
   - **Tier 3 (2 Premium Anchors £5.5m–£6.5m + 3 Budget £4.0m–£4.5m)**: Both Anchors start 100% of gameweeks; top 1 budget defender rotates into the 3rd starting spot by lowest FDR.
3. **Combinatorial Scope**:
   - **Club Level**: Exhaustive evaluation of all $\binom{20}{5} = 15,504$ possible 5-club combinations.
   - **Player Level**: 81 eligible Nailed/Regular starting defenders across 20 clubs projected via `ParticipationStateHybridModel` with flat 90-minute starter minutes.
4. **Horizons Evaluated**:
   - **GW1–3**: Early-season launch window (Pre-Wildcard / Bench Boost evaluation).
   - **GW4–19**: Post-early Wildcard / sustained winter campaign (16 gameweeks).
   - **GW1–19**: Full first half of the season (19 gameweeks).
   - **Full Season (GW1–38)**: Long-term full-season context.
5. **Defense Rotation Quality Index (DEF-RQI)** (0–100 scale):
   $$\text{DEF-RQI} = 0.35 \cdot S_{\text{tot\_xp}} + 0.25 \cdot S_{\text{fdr}} + 0.15 \cdot S_{\text{no\_diff}} + 0.15 \cdot S_{\text{corr}} + 0.10 \cdot S_{\text{cost}}$$
   - $S_{\text{tot\_xp}}$: Rotated $xP$ per GW (scaled $9.0$ to $16.5$ $xP$/GW for 3 starters).
   - $S_{\text{fdr}}$: Rotated average FDR of 3 starters (scaled $2.0$ to $3.5$).
   - $S_{\text{no\_diff}}$: % of gameweeks where all 3 starters face FDR $\le 3.0$ (Zero difficult fixtures).
   - $S_{\text{corr}}$: Pairwise FDR correlation across the 10 club pairs ($-1.0$ to $+1.0$).
   - $S_{\text{cost}}$: Budget efficiency (higher score for lower total spend, £20.0m to £28.0m).

---

## Findings

### 1. 5-Club Fixture Diversification (GW1–19 Long-Term)

Evaluating all 15,504 combinations reveals that optimal 5-club schedules can achieve an average rotated starting FDR as low as **2.4386** and guarantee that **100% of gameweeks have zero difficult fixtures** (max worst starter FDR $\le 3.0$).

#### **1.1 GW1–19 Top 10 PL-Proven 5-Club Rotations (0 Promoted Clubs)**

| Rank | 5-Club Rotation Set | Rotated Avg FDR (Top 3) | Max Worst Starter FDR | Zero Difficult GWs (FDR $\le 3$) | All Easy GWs (FDR $\le 2$) | Avg Pairwise Corr ($r$) |
|:---:|---|:---:|:---:|:---:|:---:|:---:|
| **1** | **AVL - CHE - LIV - MCI - NFO** | **2.4386** | **3.0** | **100.0% (19/19)** | 26.3% (5/19) | **-0.0679** |
| **2** | **AVL - BOU - CHE - LIV - NFO** | **2.4561** | **3.0** | **100.0% (19/19)** | 15.8% (3/19) | **-0.1182** |
| **3** | **AVL - CHE - LIV - MCI - NEW** | **2.4737** | **3.0** | **100.0% (19/19)** | 21.1% (4/19) | **-0.1733** |
| **4** | **CHE - LIV - MCI - NEW - NFO** | **2.4737** | **3.0** | **100.0% (19/19)** | 15.8% (3/19) | **-0.1327** |
| **5** | **AVL - CHE - LEE - LIV - NFO** | **2.4737** | **3.0** | **100.0% (19/19)** | 15.8% (3/19) | **-0.1091** |
| **6** | **BOU - CHE - EVE - LIV - NFO** | **2.4737** | **3.0** | **100.0% (19/19)** | 21.1% (4/19) | **-0.0968** |
| **7** | **CHE - IPS - LIV - MCI - NFO** | **2.4737** | **3.0** | **100.0% (19/19)** | 10.5% (2/19) | **-0.0705** |
| **8** | **AVL - LIV - MCI - NEW - NFO** | **2.4737** | **3.0** | **100.0% (19/19)** | 21.1% (4/19) | **-0.0580** |
| **9** | **AVL - CHE - IPS - LIV - MCI** | **2.4737** | 4.0 | 94.7% (18/19) | 31.6% (6/19) | **-0.0997** |
| **10** | **AVL - CHE - LIV - NFO - TOT** | **2.4737** | 4.0 | 94.7% (18/19) | 26.3% (5/19) | **-0.0978** |

#### **1.2 GW1–19 Top 5 Overall Combinations (Including Promoted Proxies)**

| Rank | 5-Club Rotation Set | Rotated Avg FDR | Max Worst Starter | Zero Difficult GWs | All Easy GWs | Avg Corr ($r$) | Promoted Clubs |
|:---:|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **1** | **AVL - CHE - LIV - MCI - NFO** | **2.4386** | **3.0** | **100.0%** | 26.3% | -0.0679 | 0 |
| **2** | **BHA - COV - LIV - MCI - SUN** ⚠️ | **2.4561** | **3.0** | **100.0%** | 26.3% | **-0.1487** | 2 (COV, SUN) |
| **3** | **AVL - BOU - CHE - LIV - NFO** | **2.4561** | **3.0** | **100.0%** | 15.8% | -0.1182 | 0 |
| **4** | **AVL - CHE - COV - MCI - NFO** ⚠️ | **2.4561** | **3.0** | **100.0%** | 15.8% | -0.0969 | 1 (COV) |
| **5** | **AVL - COV - LIV - MCI - NFO** ⚠️ | **2.4561** | **3.0** | **100.0%** | 21.1% | -0.0767 | 1 (COV) |

---

### 2. Horizon Dynamics: Early Launch (GW1–3) vs Sustained Run (GW4–19)

- **GW1–3 (Early Launch Window)**:
  - Top combinations achieve a rotated average FDR of **2.2222** with 33.3% all-easy weeks and 100% zero-difficult fixtures.
  - Leading sets feature Aston Villa (`AVL`), Man United (`MUN`), Sunderland (`SUN`), Hull (`HUL`), and Brighton (`BHA`).
  - Best PL-Proven GW1–3 set: **AVL - BHA - BRE - LIV - MUN** (Rotated Avg FDR: **2.3333**, 100% No Difficult weeks).
- **GW4–19 (Post-Wildcard / Sustained Winter Run)**:
  - Top combinations achieve a rotated average FDR of **2.4375** with 100% zero-difficult weeks.
  - Dominant core: **Chelsea (`CHE`) + Liverpool (`LIV`) + Nott'm Forest (`NFO`) + Aston Villa (`AVL`) / Bournemouth (`BOU`)**.

---

### 3. Multi-Tier Player Lineup Recommendations (GW1–19)

#### **Tier 1: Pure Budget 5-Way Rotation (£21.5m–£22.5m Total)**
*All 5 defenders cost £4.0m–£4.5m. Weekly pick starts best 3 by lowest FDR.*

1. **Top Promoted-Inclusive Lineup (£22.0m | DEF-RQI: 76.92)**:
   - **Maatsen** (AVL £4.5m) + **Thomas** (COV £4.0m) ⚠️ + **Tete** (FUL £4.5m) + **Jair Cunha** (NFO £4.5m) + **Robertson** (TOT £4.5m)
   - **Rotated $xP$**: **289.57 $xP$** (15.24 $xP$/GW across 3 starters)
   - **Rotated Avg FDR**: **2.4912**
   - **Zero Difficult Weeks**: **100.0% (19/19 GWs with all 3 starters FDR $\le 3$)**
   - **Pairwise FDR Correlation**: **-0.1315**
2. **Top PL-Proven Budget Lineup (£22.5m | DEF-RQI: 72.62)**:
   - **Maatsen** (AVL £4.5m) + **Ajer** (BRE £4.5m) + **Tete** (FUL £4.5m) + **Jair Cunha** (NFO £4.5m) + **Robertson** (TOT £4.5m)
   - **Rotated $xP$**: **275.45 $xP$** (14.50 $xP$/GW)
   - **Rotated Avg FDR**: **2.5088**
   - **Zero Difficult Weeks**: **100.0% (19/19 GWs)**
   - **Pairwise FDR Correlation**: **-0.1423**
3. **High-Ceiling Alternative (£22.5m | DEF-RQI: 70.84)**:
   - **Maatsen** (AVL £4.5m) + **De Cuyper** (BHA £4.5m) + **Tete** (FUL £4.5m) + **Jair Cunha** (NFO £4.5m) + **Robertson** (TOT £4.5m)
   - **Rotated $xP$**: **277.86 $xP$** (boosted by De Cuyper's 0.26 per90 xA)

---

#### **Tier 2: 1 Premium Anchor + 4 Budget Defenders (£23.5m–£24.5m Total)**
*1 Premium defender (£5.5m–£6.5m) starts 100% of gameweeks; best 2 of 4 budget defenders rotate into remaining 2 spots.*

1. **Top PL-Proven Anchor Lineup (£24.5m | DEF-RQI: 73.96)**:
   - **[Anchor: O'Reilly (MCI £6.5m)]** + **Maatsen** (AVL £4.5m) + **Tete** (FUL £4.5m) + **Jair Cunha** (NFO £4.5m) + **Robertson** (TOT £4.5m)
   - **Rotated $xP$**: **313.54 $xP$** (16.50 $xP$/GW)
   - **Rotated Avg FDR**: **2.5789**
   - **Value Gain**: **+38.09 $xP$ over 19 gameweeks** (+2.00 $xP$/GW) compared to Tier 1 for just £2.0m additional spend.
2. **Top Promoted-Inclusive Anchor Lineup (£24.0m | DEF-RQI: 74.92)**:
   - **[Anchor: O'Reilly (MCI £6.5m)]** + **Maatsen** (AVL £4.5m) + **Hato** (CHE £4.5m) + **Thomas** (COV £4.0m) ⚠️ + **Jair Cunha** (NFO £4.5m)
   - **Rotated $xP$**: **313.63 $xP$** (16.51 $xP$/GW) | Rotated Avg FDR: **2.5614**

---

#### **Tier 3: 2 Premium Anchors + 3 Budget Defenders (£25.0m–£26.5m Total)**
*2 Premium defenders start 100% of gameweeks; best 1 of 3 budget defenders rotates into the 3rd spot.*

1. **Top PL-Proven Dual Anchor Lineup (£25.0m | DEF-RQI: 68.84)**:
   - **[Anchors: Hill (BOU £5.5m) + O'Reilly (MCI £6.5m)]** + **Tete** (FUL £4.5m) + **Greaves** (IPS £4.0m) + **Bogle** (LEE £4.5m)
   - **Rotated $xP$**: **313.69 $xP$** (16.51 $xP$/GW) | Rotated Avg FDR: **2.7544**
2. **High-Ceiling Dual Anchor Lineup (£25.0m | DEF-RQI: 68.54)**:
   - **[Anchors: Hill (BOU £5.5m) + O'Reilly (MCI £6.5m)]** + **De Cuyper** (BHA £4.5m) + **Tete** (FUL £4.5m) + **Greaves** (IPS £4.0m)
   - **Rotated $xP$**: **321.78 $xP$** (16.94 $xP$/GW)

---

## Decision & Team Selection Verdict

**Verdict**: The mathematically optimal long-term 5-defender strategy for GW1–19 is **Tier 1 (Pure Budget Rotation at £22.5m)** for managers seeking maximum funds in midfield/attack, or **Tier 2 (1 Premium Anchor + 4 Budget at £24.5m)** for the highest points-per-million efficiency.

### **Recommended 5 DEF Lineups for Your Team**:

1. **Option 1: Ultimate Value 5-Way Budget Rotation (£22.5m Total Spend)**:
   - **Maatsen** (Aston Villa, £4.5m)
   - **Jair Cunha** (Nott'm Forest, £4.5m)
   - **Tete** (Fulham, £4.5m)
   - **Robertson** (Spurs, £4.5m)
   - **Ajer** (Brentford, £4.5m) *(or **Bobby Thomas**, Coventry £4.0m to bank £0.5m ITB)*
   - **Performance**: Rotates to an average starting FDR of **2.5088** across GW1–19, delivers **275.45 $xP$** (14.50 $xP$/GW across 3 starters), and ensures you **NEVER have to start a defender facing FDR $\ge 4$** in all 19 gameweeks.

2. **Option 2: High-Performance Anchor + Rotation (£24.5m Total Spend)**:
   - **O'Reilly / Gvardiol** (Man City, £6.5m / £5.5m) — *Every-week Starter*
   - **Maatsen** (Aston Villa, £4.5m) — *Rotational Starter*
   - **Jair Cunha** (Nott'm Forest, £4.5m) — *Rotational Starter*
   - **Tete** (Fulham, £4.5m) — *Rotational Starter*
   - **Robertson** (Spurs, £4.5m) — *Rotational Starter*
   - **Performance**: Boosts total defensive return to **313.54 $xP$** (+38.1 points over the first half) with an elite 16.50 $xP$/GW average while preserving smooth fixture rotation for the other 2 defensive spots.

---

## Special Scenario: GW1 Bench Boost (BB1) + GW4 Wildcard (WC4) Pre-Wildcard Defense

**Context**: In a **GW1 Bench Boost + GW4 Wildcard** strategy:
- **GW1**: All 5 defenders are active and contribute points (Bench Boost).
  - *Hard Constraint*: **Zero Opponent Clashes in GW1** (no two defenders face each other in the same match to prevent clean sheet cannibalization).
  - *Fixture Ceiling*: **Max FDR $\le 3.0$ across all 5 DEF in GW1** (100% avoid difficult fixtures FDR 4 or 5).
- **GW2 & GW3**: Revert to standard 3-DEF starting rotation (top 3 by FDR-min / hybrid $xP$; 2 benched).
- **GW4**: Full squad overhaul on Wildcard. Total pre-WC defensive sample = **11 started player-matches** (5 in GW1 + 3 in GW2 + 3 in GW3).

---

### 1. Non-Clashing 5-Club Combinations (GW1 BB + GW2–3 3-DEF Rotation)

Out of 15,504 possible 5-club combinations, **8,064 sets have zero GW1 head-to-head matches**, and exactly **1,683 sets satisfy the strict GW1 max FDR $\le 3.0$ ceiling**.

#### **Top 5 PL-Proven 5-Club Rotations (0 Promoted Clubs)**

| Rank | 5-Club Combination | GW1 Avg FDR (5 Starters) | GW1 Max FDR | GW2–3 Rotated Avg FDR (3 Starters) | 11-Start Effective Avg FDR | Zero GW1 Clashes |
|:---:|---|:---:|:---:|:---:|:---:|:---:|
| **1** | **ARS - BRE - CHE - MUN - NFO** | **2.40** | **3.0** | **2.50** | **2.4545** | ✅ Zero Clashes |
| **2** | **ARS - BRE - IPS - LIV - MUN** | **2.40** | **3.0** | **2.50** | **2.4545** | ✅ Zero Clashes |
| **3** | **ARS - BRE - IPS - MCI - MUN** | **2.40** | **3.0** | **2.50** | **2.4545** | ✅ Zero Clashes |
| **4** | **ARS - BRE - LIV - MUN - NFO** | **2.40** | **3.0** | **2.50** | **2.4545** | ✅ Zero Clashes |
| **5** | **ARS - CHE - LIV - MUN - NFO** | **2.40** | **3.0** | **2.50** | **2.4545** | ✅ Zero Clashes |

*All 5 clubs in the winning set have easy GW1 fixtures: Arsenal (H vs COV, FDR 2), Man Utd (A vs HUL, FDR 2), Nott'm Forest (H vs LEE, FDR 2), Brentford (H vs TOT, FDR 3), Chelsea (A vs FUL, FDR 3).*

#### **Top 3 Overall 5-Club Rotations (Including Promoted Proxies)**

| Rank | 5-Club Combination | GW1 Avg FDR | GW1 Max FDR | GW2–3 Rot Avg FDR | Effective Avg FDR | Promoted Clubs |
|:---:|---|:---:|:---:|:---:|:---:|:---:|
| **1** | **ARS - BRE - MUN - NFO - SUN** ⚠️ | **2.20** | **3.0** | **2.50** | **2.3636** | 1 (SUN) |
| **2** | **ARS - CHE - MUN - NFO - SUN** ⚠️ | **2.20** | **3.0** | **2.50** | **2.3636** | 1 (SUN) |
| **3** | **ARS - AVL - BRE - MUN - SUN** ⚠️ | **2.40** | **3.0** | **2.33** | **2.3636** | 1 (SUN) |

---

### 2. Pre-Wildcard (GW1–3) Player Lineup Rankings

#### **Tier 1: Pure Budget BB1 Rotation (£21.5m–£22.5m Total Spend)**
*Maximizes starting budget for Salah, Haaland, Saka, and Palmer in GW1–3.*

1. **Top PL-Proven Budget Lineup (£22.0m | BB-RQI: 65.16)**:
   - **Maatsen** (AVL £4.5m) + **Greaves** (IPS £4.0m) + **Shaw** (MUN £4.5m) + **Jair Cunha** (NFO £4.5m) + **Robertson** (TOT £4.5m)
   - **Total 3-GW Effective $xP$ (11 Starts)**: **52.05 $xP$**
     - *GW1 (All 5 DEF on BB)*: **23.15 $xP$** (4.63 $xP$/defender; 0 clashes; FDRs: 3, 2, 2, 2, 3)
     - *GW2–3 (Top 3 DEF)*: **28.90 $xP$** (4.82 $xP$/starter)
   - **Effective Avg FDR**: **2.5455** (100% FDR $\le 3.0$ across all 11 started player-matches!)
   - **Spend**: Only **£22.0m**, leaving **£78.0m ITB** for midfield and attack.
2. **Top Promoted-Hybrid Budget Lineup (£22.5m | BB-RQI: 71.46)**:
   - **Maatsen** (AVL £4.5m) + **Shaw** (MUN £4.5m) + **Jair Cunha** (NFO £4.5m) + **Hume** (SUN £4.5m) ⚠️ + **Robertson** (TOT £4.5m)
   - **Total 3-GW Effective $xP$**: **54.13 $xP$** (GW1: **23.98 $xP$** with 2.20 avg FDR; GW2–3: **30.15 $xP$**).

---

#### **Tier 2: 1 Premium Anchor + 4 Budget Defenders (£23.5m–£24.5m Total Spend)**
*1 Premium Anchor (e.g. Man City defender) starts all 3 GWs; top 4 budget defenders all start GW1, then rotate for 2 spots in GW2/GW3.*

1. **Top PL-Proven Anchor Lineup (£24.5m | BB-RQI: 76.02)**:
   - **[Anchor: O'Reilly / Gvardiol (MCI £6.5m/£5.5m)]** + **Maatsen** (AVL £4.5m) + **Shaw** (MUN £4.5m) + **Jair Cunha** (NFO £4.5m) + **Robertson** (TOT £4.5m)
   - **Total 3-GW Effective $xP$ (11 Starts)**: **59.82 $xP$**
     - *GW1 (All 5 DEF on BB)*: **25.32 $xP$** (5.06 $xP$/defender)
     - *GW2–3 (Anchor + Top 2 Budget)*: **34.50 $xP$** (5.75 $xP$/starter)
   - **Effective Avg FDR**: **2.4545** (100% FDR $\le 3.0$)
   - **Point Gain**: **+7.77 $xP$ boost** over 3 gameweeks vs pure budget for £2.5m spend.

---

### **BB1 + WC4 Final Defensive Recommendation**:

- **If prioritizing maximum funds for Haaland + Salah + Saka in GW1–3**: Select the **£22.0m PL-Proven Budget Lineup**:
  `Maatsen (AVL £4.5m) + Greaves (IPS £4.0m) + Shaw (MUN £4.5m) + Jair Cunha (NFO £4.5m) + Robertson (TOT £4.5m)`
  *(Zero clashes in GW1, 2.54 effective FDR, 52.05 total xP across 11 appearances).*
- **If prioritizing defensive ceiling with 1 Man City starter**: Select the **£24.5m Anchor Lineup**:
  `[Anchor: O'Reilly/Gvardiol (MCI £6.5m/£5.5m)] + Maatsen (AVL £4.5m) + Shaw (MUN £4.5m) + Jair Cunha (NFO £4.5m) + Robertson (TOT £4.5m)`
  *(Zero clashes in GW1, 59.82 total xP).*

---

## Risks and Unknowns

1. **Starting Role Volatility**: Players like Maatsen, Robertson, and Hato face rotational competition; monitor pre-season starting XI announcements.
2. **Promoted Team Defensive Conceded Rates**: Coventry and Sunderland defenders offer cheap £4.0m entries and strong fixture pairing, but may concede higher expected goals per match than established mid-table teams.
3. **Manager Tactical Switches**: Changes in defensive structure (e.g. back-3 vs back-4) may alter per90 defensive contribution baseline rates.

---

## Refresh Checklist

- [x] `Updated` uses ISO 8601 timestamp with timezone (`2026-08-10T12:45:00+07:00`).
- [x] `Data stamp` identifies current evidence cutoff.
- [x] Full combinatorial simulation executed across all 15,504 combinations.
- [x] Specialized BB1 + WC4 simulation executed with non-clashing GW1 filters.
- [x] Machine-readable CSV companions written to `data/research/def-fixture-rotation/`.
- [x] Dual reporting for Overall vs PL-Proven selections.

