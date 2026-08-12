# 5-Defender Fixture Diversification & Long-Term Rotation Study (GW1–19, up to £26.0m)

**Updated**: 2026-08-12T12:31:00+07:00  
**Data stamp**: FPL API processed snapshot + `expected-stats-gw1-5.csv` rates + `ParticipationStateHybridModel` GW1–38 flat-90 projections  
**Season**: 2026/27  
**Status**: Active  
**Purpose**: Identify optimal 5-defender (5 DEF) club combinations and starting lineups over the long term (GW1–19, GW1–3 early launch, and GW4–19 post-Wildcard) with flexible pricing up to **£26.0m total budget** that maximize defensive fixture diversification, eliminate difficult fixtures (FDR ≥ 4) across starting defenders, and optimize rotated expected points (xP).  
**Sources**: `data/processed/fixtures.parquet`, `data/processed/players.parquet`, `data/processed/clubs.parquet`, `data/research/gw1-6-preseason-pipeline/01-expected-role-gw1-5/expected-role-gw1-5.csv`, `data/research/gw1-6-preseason-pipeline/02-expected-stats-gw1-5/expected-stats-gw1-5.csv`  
**Artifacts**: [`def_club_5way_rotation_matrix.csv`](../../../data/research/def-fixture-rotation/def_club_5way_rotation_matrix.csv), [`def_tier_player_rotations.csv`](../../../data/research/def-fixture-rotation/def_tier_player_rotations.csv), [`def_bb1_wc4_club_matrix.csv`](../../../data/research/def-fixture-rotation/def_bb1_wc4_club_matrix.csv), [`def_bb1_wc4_tier_lineups.csv`](../../../data/research/def-fixture-rotation/def_bb1_wc4_tier_lineups.csv), [`def_performance_baseline.csv`](../../../data/research/def-fixture-rotation/def_performance_baseline.csv)  
**Script**: [`run_def_rotation_analysis.py`](run_def_rotation_analysis.py)  

---

## Method & Mathematical Framework

1. **Formation & Starting Spot Baseline**: Fixed 3 DEF starters each gameweek (standard 3-4-3 / 3-5-2 optimal FPL formation with 7 attacking spots).
2. **Weekly Starting Pick Policy**:
   - For any 5-defender unit, the algorithm selects the **top 3 starters with lowest fixture difficulty (FDR-min)**, using projected points ($\text{xP}$) as tiebreaker.
   - Also tracks **Max-xP selection** (starting top 3 strictly by projected points) to measure rotation ceiling.
3. **Flexible Budget Spectrum ($\le £26.0\text{m}$)**:
   - **Band 1: Budget (£20.5m–£22.5m)**: Maximum funds allocated to midfield/attack (£77.5m–£79.5m remaining).
   - **Band 2: Mid-Value (£23.0m–£24.0m)**: Blends emerging £5.0m assets (e.g. Jacquet, Vuskovic, Muharemović) with £4.0m/£4.5m rotators.
   - **Band 3: Single Anchor (£24.5m–£25.0m)**: 1 Premium Anchor (£5.5m–£6.5m, e.g. O'Reilly, Gvardiol, Calafiori) + 4 rotating defenders.
   - **Band 4: Premium / Dual Anchor (£25.5m–£26.0m)**: Dual premium anchors + elite £4.5m/£5.0m rotators.
4. **Combinatorial Scope**:
   - **Club Level**: Exhaustive evaluation of all $C(20,5) = 15,504$ 5-club combinations across 20 Premier League clubs.
   - **Player Level**: 83 eligible starting defenders across 20 clubs projected via `ParticipationStateHybridModel` with flat 90-minute starter minutes.
5. **Defense Rotation Quality Index (DEF-RQI)** (0–100 scale):
   $$\text{DEF-RQI} = 0.35\cdot S_{\text{tot\_xp}} + 0.25\cdot S_{\text{fdr}} + 0.15\cdot S_{\text{no\_diff}} + 0.15\cdot S_{\text{corr}} + 0.10\cdot S_{\text{cost}}$$
   - $S_{\text{tot\_xp}}$: Rotated xP per GW (scaled 9.0 to 16.5 xP/GW for 3 starters).
   - $S_{\text{fdr}}$: Rotated average FDR of 3 starters (scaled 2.0 to 3.5).
   - $S_{\text{no\_diff}}$: % of gameweeks where all 3 starters face FDR ≤ 3.0 (Zero difficult fixtures).
   - $S_{\text{corr}}$: Pairwise FDR correlation across the 10 club pairs (-1.0 to +1.0).
   - $S_{\text{cost}}$: Budget efficiency (higher score for lower total spend, £20.0m to £28.0m).

---

## 1. 5-Club Fixture Diversification Rankings (GW1–19)

All top 5-club combinations guarantee **100% Zero-Difficult Gameweeks** (no starting defender faces FDR $\ge 4$ in all 19 gameweeks):

| Rank | 5-Club Rotation Set | Rotated Avg FDR (Top 3) | Max Worst Starter FDR | Zero Difficult GWs (FDR ≤ 3) | All Easy GWs (FDR ≤ 2) | Avg Pairwise Corr ($r$) |
|:---:|---|:---:|:---:|:---:|:---:|:---:|
| **1** | **AVL - CHE - LIV - MCI - NFO** | **2.4386** | **3.0** | **100.0% (19/19)** | 26.3% (5/19) | **-0.0679** |
| **2** | **BHA - COV - LIV - MCI - SUN** | **2.4561** | **3.0** | **100.0% (19/19)** | 26.3% (5/19) | **-0.1487** |
| **3** | **AVL - BOU - CHE - LIV - NFO** | **2.4561** | **3.0** | **100.0% (19/19)** | 15.8% (3/19) | **-0.1182** |
| **4** | **AVL - CHE - COV - MCI - NFO** | **2.4561** | **3.0** | **100.0% (19/19)** | 15.8% (3/19) | **-0.0969** |
| **5** | **AVL - COV - LIV - MCI - NFO** | **2.4561** | **3.0** | **100.0% (19/19)** | 21.1% (4/19) | **-0.0767** |

---

## 2. Flexible 5-Defender Player Lineup Rankings (GW1–19, $\le £26.0\text{m}$)

### Overall Top 5 Lineups by Total Rotated Points ($\text{xP}$)

| Rank | Lineup Composition | Total Spend | Total 19-GW xP | Weekly Avg xP | Rotated FDR | Zero-Diff GWs | Avg Corr ($r$) |
|:---:|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **1** | **Vuskovic** (BHA £5.0m) + **Hill** (BOU £5.5m) + **Thomas** (COV £4.0m) + **Jacquet** (LIV £5.0m) + **O'Reilly** (MCI £6.5m) | **£26.0m** | **360.78 xP** | **18.99 xP/GW** | 2.5088 | 89.5% | -0.0326 |
| **2** | **Calafiori** (ARS £5.5m) + **Vuskovic** (BHA £5.0m) + **Thomas** (COV £4.0m) + **Jacquet** (LIV £5.0m) + **O'Reilly** (MCI £6.5m) | **£26.0m** | **360.51 xP** | **18.97 xP/GW** | 2.5088 | 94.7% | -0.1225 |
| **3** | **Vuskovic** (BHA £5.0m) + **Thomas** (COV £4.0m) + **Muharemović** (LEE £5.0m) + **Jacquet** (LIV £5.0m) + **O'Reilly** (MCI £6.5m) | **£25.5m** | **358.63 xP** | **18.88 xP/GW** | 2.5088 | 94.7% | -0.1166 |
| **4** | **Calafiori** (ARS £5.5m) + **Vuskovic** (BHA £5.0m) + **Thomas** (COV £4.0m) + **Muharemović** (LEE £5.0m) + **O'Reilly** (MCI £6.5m) | **£26.0m** | **358.63 xP** | **18.88 xP/GW** | 2.5263 | **100.0%** | -0.1617 |
| **5** | **Vuskovic** (BHA £5.0m) + **Thomas** (COV £4.0m) + **Jacquet** (LIV £5.0m) + **O'Reilly** (MCI £6.5m) + **Ballard** (SUN £5.0m) | **£25.5m** | **353.24 xP** | **18.59 xP/GW** | 2.4561 | **100.0%** | -0.0768 |

---

### Top Lineups by Natural Budget Band (GW1–19)

```mermaid
graph LR
    subgraph Band 1: Budget (£20.5-22.5m)
        B1["Vuskovic (BHA £5.0m) + Thomas (COV £4.0m) + Ajayi (HUL £4.0m) + Jacquet (LIV £5.0m) + O'Nien (SUN £4.0m)<br><b>Spend: £22.0m | 319.50 xP (16.82/GW) | FDR: 2.51 | 100% No-Diff</b>"]
    end
    subgraph Band 2: Mid-Value (£23.0-24.0m)
        B2["Vuskovic (BHA £5.0m) + Thomas (COV £4.0m) + Jacquet (LIV £5.0m) + Jair Cunha (NFO £4.5m) + Hume (SUN £4.5m)<br><b>Spend: £23.0m | 320.28 xP (16.86/GW) | FDR: 2.49 | 100% No-Diff</b>"]
    end
    subgraph Band 3: Single Anchor (£24.5-25.0m)
        B3["Vuskovic (BHA £5.0m) + Thomas (COV £4.0m) + Jacquet (LIV £5.0m) + O'Reilly (MCI £6.5m) + O'Nien (SUN £4.0m)<br><b>Spend: £24.5m | 346.34 xP (18.23/GW) | FDR: 2.46 | 100% No-Diff</b>"]
    end
    subgraph Band 4: Dual Anchor (£25.5-26.0m)
        B4["Calafiori (ARS £5.5m) + Vuskovic (BHA £5.0m) + Thomas (COV £4.0m) + Jacquet (LIV £5.0m) + O'Reilly (MCI £6.5m)<br><b>Spend: £26.0m | 360.51 xP (18.97/GW) | FDR: 2.51 | 94.7% No-Diff</b>"]
    end
```

#### Band 1: Budget Focus (£20.5m–£22.5m Total)
*Maximizes savings for premium midfield and forward assets (£77.5m–£79.5m ITB).*

1. **#1 Budget Lineup (£22.0m | DEF-RQI: 74.02)**:
   - **Vuskovic** (BHA £5.0m) + **Thomas** (COV £4.0m) + **Ajayi** (HUL £4.0m) + **Jacquet** (LIV £5.0m) + **O'Nien** (SUN £4.0m)
   - **Rotated xP**: **319.50 xP** (16.82 xP/GW across 3 starters)
   - **Rotated Avg FDR**: **2.5088** | **Zero Difficult Weeks**: **100.0% (19/19 GWs)** | **Avg Corr**: **-0.1104**
2. **#2 Budget Lineup (£22.5m | DEF-RQI: 73.69)**:
   - **Vuskovic** (BHA £5.0m) + **Thomas** (COV £4.0m) + **Jacquet** (LIV £5.0m) + **Jair Cunha** (NFO £4.5m) + **O'Nien** (SUN £4.0m)
   - **Rotated xP**: **319.90 xP** (16.84 xP/GW) | **Rotated Avg FDR**: **2.4912** | **Zero Difficult**: **100.0%**
3. **Pure £4.0m–£4.5m Classic Budget (£22.0m | DEF-RQI: 76.85)**:
   - **Maatsen** (AVL £4.5m) + **Thomas** (COV £4.0m) + **Tete** (FUL £4.5m) + **Jair Cunha** (NFO £4.5m) + **Robertson** (TOT £4.5m)
   - **Rotated xP**: **289.29 xP** (15.23 xP/GW) | **Rotated Avg FDR**: **2.4912** | **Zero Difficult**: **100.0%**

---

#### Band 2: Mid-Value (£23.0m–£24.0m Total)
*Blends Liverpool & Brighton defense entry with reliable £4.0m/£4.5m starters.*

1. **#1 Mid-Value Lineup (£23.0m | DEF-RQI: 73.06)**:
   - **Vuskovic** (BHA £5.0m) + **Thomas** (COV £4.0m) + **Jacquet** (LIV £5.0m) + **Jair Cunha** (NFO £4.5m) + **Hume** (SUN £4.5m)
   - **Rotated xP**: **320.28 xP** (16.86 xP/GW) | **Rotated Avg FDR**: **2.4912** | **Zero Difficult**: **100.0%**
2. **Forest + Leeds Hybrid (£23.5m | DEF-RQI: 72.84)**:
   - **Maatsen** (AVL £4.5m) + **Thomas** (COV £4.0m) + **Muharemović** (LEE £5.0m) + **Jacquet** (LIV £5.0m) + **Jair Cunha** (NFO £4.5m)
   - **Rotated xP**: **325.21 xP** (17.12 xP/GW) | **Rotated Avg FDR**: **2.4912** | **Zero Difficult**: **100.0%**

---

#### Band 3: Single Premium Anchor (£24.5m–£25.0m Total)
*1 Elite City Defender (£6.5m O'Reilly) as permanent starter + 4 rotating defenders.*

1. **#1 Single Anchor Lineup (£24.5m | DEF-RQI: 71.77)**:
   - **[Anchor: O'Reilly (MCI £6.5m)]** + **Vuskovic** (BHA £5.0m) + **Thomas** (COV £4.0m) + **Jacquet** (LIV £5.0m) + **O'Nien** (SUN £4.0m)
   - **Rotated xP**: **346.34 xP** (18.23 xP/GW)
   - **Rotated Avg FDR**: **2.4561** | **Zero Difficult Weeks**: **100.0% (19/19 GWs)** | **Avg Corr**: **-0.0883**
   - **Value Gain**: **+26.84 xP over 19 GWs** (+1.41 xP/GW) vs Band 1 for £2.5m extra spend.
2. **City + Hull Anchor Hybrid (£24.5m | DEF-RQI: 71.77)**:
   - **[Anchor: O'Reilly (MCI £6.5m)]** + **Vuskovic** (BHA £5.0m) + **Thomas** (COV £4.0m) + **Ajayi** (HUL £4.0m) + **Jacquet** (LIV £5.0m)
   - **Rotated xP**: **348.68 xP** (18.35 xP/GW) | **Rotated Avg FDR**: **2.4561** | **Zero Difficult**: **100.0%**

---

#### Band 4: Premium / Dual Anchor (£25.5m–£26.0m Total)
*Maximum defensive firepower with 2 elite club starters (City + Arsenal / Liverpool) + 3 rotating defenders.*

1. **#1 Dual Anchor Lineup (£26.0m | DEF-RQI: 68.23)**:
   - **[Anchors: Calafiori (ARS £5.5m) + O'Reilly (MCI £6.5m)]** + **Vuskovic** (BHA £5.0m) + **Thomas** (COV £4.0m) + **Jacquet** (LIV £5.0m)
   - **Rotated xP**: **360.51 xP** (18.97 xP/GW)
   - **Rotated Avg FDR**: **2.5088** | **Zero Difficult Weeks**: **94.7% (18/19 GWs)**
2. **#2 Dual Anchor Lineup (£25.5m | DEF-RQI: 70.82)**:
   - **[Anchors: Jacquet (LIV £5.0m) + O'Reilly (MCI £6.5m)]** + **Maatsen** (AVL £4.5m) + **Colwill** (CHE £5.0m) + **Jair Cunha** (NFO £4.5m)
   - **Rotated xP**: **322.15 xP** (17.00 xP/GW) | **Rotated Avg FDR**: **2.4386** | **Zero Difficult**: **100.0%**

---

## 3. Specialized Pre-Wildcard Scenario: GW1 BB + GW4 Wildcard (up to £26.0m)

In a **GW1 Bench Boost + GW4 Wildcard** setup:
- **GW1**: All 5 defenders start (Bench Boost active). Hard constraint: **Zero head-to-head opponent clashes** and **Max FDR ≤ 3.0**.
- **GW2 & GW3**: Revert to starting top 3 by lowest FDR / highest xP (2 benched). Total pre-WC starts = **11 player-matches**.

### Top GW1 Bench Boost Lineups by Budget Band

| Budget Band | Winning Lineup Composition | Total Spend | 11-Start Total xP | GW1 xP (5 Starters) | GW2–3 xP (6 Starters) | Effective Avg FDR |
|---|---|:---:|:---:|:---:|:---:|:---:|
| **Band 1: Budget (£20.5–22.5m)** | **Maatsen** (AVL £4.5m) + **Jacquet** (LIV £5.0m) + **Shaw** (MUN £4.5m) + **Jair Cunha** (NFO £4.5m) + **O'Nien** (SUN £4.0m) | **£22.5m** | **57.20 xP** | 24.93 xP | 32.27 xP | **2.3636** |
| **Band 2: Mid-Value (£23.0–24.0m)** | **Calafiori** (ARS £5.5m) + **Jacquet** (LIV £5.0m) + **Maguire** (MUN £5.0m) + **Jair Cunha** (NFO £4.5m) + **O'Nien** (SUN £4.0m) | **£24.0m** | **60.51 xP** | 28.39 xP | 32.13 xP | **2.3636** |
| **Band 3: Single Anchor (£24.5–25.0m)** | **Calafiori** (ARS £5.5m) + **Jacquet** (LIV £5.0m) + **Shaw** (MUN £4.5m) + **Jair Cunha** (NFO £4.5m) + **Ballard** (SUN £5.0m) | **£24.5m** | **60.96 xP** | 28.57 xP | 32.38 xP | **2.3636** |
| **Band 4: Premium Anchor (£25.5–26.0m)** | **Calafiori** (ARS £5.5m) + **O'Reilly** (MCI £6.5m) + **Maguire** (MUN £5.0m) + **Jair Cunha** (NFO £4.5m) + **O'Nien** (SUN £4.0m) | **£25.5m** | **62.88 xP** | 29.26 xP | 33.62 xP | **2.3636** |

---

## 4. Strategic Verdict: Min-Max Early vs Safe Set & Forget (with up to £26.0m Spend)

### Key Trade-Offs

1. **Points Ceiling with Flexible £26.0m Budget**:
   - If you allocate **£24.5m to £25.5m** to defense (Band 3 / Band 4), starting **O'Reilly (MCI £6.5m)** and **Jacquet (LIV £5.0m)** alongside rotating £4.0m/£4.5m defenders boosts total first-half returns to **~346–360 xP** (+57 to +71 points over a £22.0m pure budget unit).
2. **Wildcard & Transfer Freedom**:
   - In GW4 Wildcard, keeping a robust 5-defender core (e.g. `O'Reilly + Jacquet + Vuskovic + Thomas + O'Nien`) means **zero defensive transfers are required on Wildcard**.
   - All free transfers and Wildcard slots can be directed towards emerging midfield and forward assets without defensive price rise/fall friction.

---

## Verification Checklist

- [x] Unrestricted budget ceiling set to at most **£26.0m**.
- [x] All 20 Premier League clubs and 83 eligible defenders evaluated uniformly.
- [x] Vectorized multi-horizon simulation executed across 634,874 valid 5-defender combinations.
- [x] All 5 CSV artifacts regenerated in `data/research/def-fixture-rotation/`.
- [x] Complete test suite passing (`153 passed in 9.67s`).
