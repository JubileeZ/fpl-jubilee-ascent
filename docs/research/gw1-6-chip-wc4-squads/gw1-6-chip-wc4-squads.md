# GW1–6 Early Chip & GW4 Wildcard Squad Optimization (3×2 Matrix Study)

**Updated**: 2026-08-03T04:20:20+07:00  
**Data stamp**: Projections CSV 2026-08-03 (ParticipationStateHybridModel horizon 6); FPL API player pricing 2026-07-29  
**Season**: 2026/27 · horizon GW1–6  
**Status**: Active Research Model  
**Purpose**: Execute full 6-Gameweek optimization study across a $3 \times 2 = 6$ scenario matrix combining Pre-WC Bench Boost timing (GW1 BB vs GW2 BB under $\le$ £100.0m spend) with GW4 Wildcard structural designs (Option 1 Unconstrained MILP, Option 2 Cheap-Defense Cap $\le$ £32.0m, and Option 3 Cheap-Defense Cap $\le$ £32.0m + Liverpool 2+). All scenarios enforce GW5 transfer rolling to enter GW6 with 2+ Free Transfers banked post-international break.  
**Scope**: End-to-end 15-player squad optimization, starting XI selection, transfer schedules, Liverpool asset constraints, ITB buffer management, and international break risk strategy across GW1–6.  
**Related**: [GW1–5 Chip Strategy Simulation](../gw1-5-chip-simulation/gw1-5-chip-simulation.md) · [Expected Stats GW1–5](../expected-stats-gw1-5/expected-stats-gw1-5.md) · [Simulation Runner](run_wc4_simulation.py)  
**Artifacts**:
- [Squad Simulation CSV](../../../data/research/gw1-6-chip-wc4-squads/gw1-6_wc4_simulation.csv) — row-level squad rosters, phase labels, and per-GW $xP$ across all 6 scenarios
- [Projections CSV](../../../data/research/gw1-6-chip-wc4-squads/gw1-6_projections.csv) — GW1–6 player-level $xP$ and $xMins$

---

## Sources

- **Primary Projections Input**: `data/research/gw1-6-chip-wc4-squads/gw1-6_projections.csv` (ParticipationStateHybridModel 6-GW horizon).
- **Player Pricing & Metadata**: `data/processed/players.parquet` and `data/processed/clubs.parquet`.
- **Optimization Runner**: `docs/research/gw1-6-chip-wc4-squads/run_wc4_simulation.py` (scipy MILP).

---

## Agent Prompt (Parameterized for Future Re-Analysis)

```text
Run parameterized GW1-6 chip & GW4 Wildcard 3x2 matrix optimization study:

Inputs & Horizon:
- Input Projections: data/research/gw1-6-chip-wc4-squads/gw1-6_projections.csv (ParticipationStateHybridModel, horizon GW1-6).
- Price & Metadata: data/processed/players.parquet, data/processed/clubs.parquet.
- User Active Squad: data/processed/user_picks.parquet.
- Pre-WC Budget: <= £100.0m. Post-WC Budget: <= £100.0m.

Matrix Dimensions (3x2 = 6 Scenarios):
- Pre-WC Chip Options (2):
  A. BB1: Bench Boost in GW1 (spend <= £100.0m, min 1 Liverpool asset).
  B. BB2: Bench Boost in GW2 (spend <= £100.0m, min 1 Liverpool asset).
- Post-WC Structural Options (3):
  1. Opt1 (Unconstrained MILP): Maximize GW4-6 XI xP under £100.0m without position caps or club constraints.
  2. Opt2 (Cheap Defense Cap): Maximize GW4-6 XI xP with GKP + 5 DEF spend <= £32.0m (leaving >= £68.0m for 5 MID + 3 FWD).
  3. Opt3 (Cheap Defense Cap + Liverpool 2+): GKP + 5 DEF spend <= £32.0m AND enforce >= 2 Liverpool assets (e.g. Isak + Mac Allister).

User Squad Evolution & Comparison:
- Ingest data/processed/user_picks.parquet and project 6-GW xP for user's starting squad under GW1 BB and GW2 BB.
- Calculate GW4 Wildcard evolution strategy (transitioning user squad to Option 1 / Option 3 Wildcard) and measure exact GW1-3 Pre-WC opportunity loss.
- Compare Sticking Strategy (No Wildcard) vs Evolving Strategy (GW4 Wildcard).

Execution & Constraints:
- Maintain AT LEAST 2 Free Transfers banked entering GW6 post-international break (allows using 1-2 FTs across GW2-3 or GW5).
- For each of the 6 scenarios and user squad evolution paths, calculate exact per-gameweek starting XI + bench xP, total 6-GW cumulative xP, exact GW1-6 squad lists, and transfer logs.
- Export results to data/research/gw1-6-chip-wc4-squads/gw1-6_wc4_simulation.csv.
- Run ruff check and verify delivery gates before completing.
```

---

## Method

1. **Pre-WC Draft MILP (GW1–3)**:
   - **Path A (BB1)**: Bench Boost deployed in GW1 (£100.0m spend). All 15 players score in GW1; best 11 fielded in GW2–3.
   - **Path B (BB2)**: Bench Boost deployed in GW2 (£100.0m spend). Best 11 fielded in GW1 & GW3; all 15 players score in GW2.
   - Minimum 1 Liverpool player enforced pre-WC.
2. **Wildcard MILP (GW4–6)**:
   - **Option 1 (Unconstrained MILP)**: Solves GW4–6 squad under £100.0m with no defensive spend cap or club constraints.
   - **Option 2 (Cheap Defense Cap ≤ £32.0m)**: Caps GKP (2) + DEF (5) spend at ≤ £32.0m total, forcing £68.0m into 5 MID + 3 FWD.
   - **Option 3 (Cheap Defense Cap ≤ £32.0m + Liverpool 2+)**: Caps GKP + DEF spend at ≤ £32.0m AND enforces ≥ 2 Liverpool assets.
3. **Transfer Schedule & Flexible Banking Policy**:
   - GW1: Deploy initial draft.
   - GW2–3: Roll or spend 1 FT (e.g. tactical/injury move). Up to 2–3 FTs accumulated entering GW4.
   - GW4: Activate Wildcard (unlimited transfers; preserves accumulated FTs).
   - GW5: Roll or spend 1 FT.
   - GW6: Enter GW6 with **at least 2 Free Transfers banked** (up to 4–5 FTs if fully rolled) post-international break.

---

## Findings

### 1. 3×2 Matrix Summary Table (Cumulative GW1–6 xP & Metrics)

| Scenario ID | Pre-WC Chip | Post-WC Option | GW1–3 XI xP | GW4–6 XI xP | Total 6-GW xP | Pre Spend | Post Spend | GW6 ITB | Banked FTs (GW6) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **S1** | GW1 BB1 | Opt1 (Unconstrained) | **167.93 $xP$** | **151.28 $xP$** | **319.21 $xP$** | £100.0m | £100.0m | £0.0m | **2 FTs** |
| **S2** | GW1 BB1 | Opt2 (Cheap DEF $\le$32m) | **167.93 $xP$** | 146.95 $xP$ | **314.88 $xP$** | £100.0m | £100.0m | £0.0m | **2 FTs** |
| **S3** | GW1 BB1 | Opt3 (Cheap DEF $\le$32m + LIV 2+) | **167.93 $xP$** | 146.44 $xP$ | **314.37 $xP$** | £100.0m | £97.0m | **£3.0m** | **2 FTs** |
| **S4** | GW2 BB2 | Opt1 (Unconstrained) | 167.42 $xP$ | **151.28 $xP$** | **318.70 $xP$** | £100.0m | £100.0m | £0.0m | **2 FTs** |
| **S5** | GW2 BB2 | Opt2 (Cheap DEF $\le$32m) | 167.42 $xP$ | 146.95 $xP$ | **314.37 $xP$** | £100.0m | £100.0m | £0.0m | **2 FTs** |
| **S6** | GW2 BB2 | Opt3 (Cheap DEF $\le$32m + LIV 2+) | 167.42 $xP$ | 146.44 $xP$ | **313.86 $xP$** | £100.0m | £97.0m | **£3.0m** | **2 FTs** |

---

## 2. Full GW1–6 Squad Lists & Transfer Schedules for All Scenarios

### Pre-WC Phase Squad Rosters (GW1–3)

##### BB1 Pre-WC Squad Roster (£100.0m Spend) — Scenarios S1, S2, S3
- **GKP**: Donnarumma (£5.5m, MCI), Lammens (£5.0m, MUN)
- **DEF**: O'Reilly (£6.5m, MCI), Hill (£5.5m, BOU), Vuskovic (£5.0m, BHA), Ballard (£5.0m, SUN), Alderete (£5.0m, SUN)
- **MID**: Sarr (£6.5m, CRY), Ndiaye (£6.0m, EVE), Schade (£6.0m, BRE), E.Le Fée (£6.0m, SUN), Maeda (£5.5m, IPS)
- **FWD**: Haaland (£15.5m, MCI), Isak (£9.0m, LIV), Thiago (£8.0m, BRE)
- **GW1 (BB1 Activated)**: 15-Player Score = **65.54 $xP$**
- **GW2 XI**: 48.76 $xP$ | **GW3 XI**: 53.63 $xP$
- **GW1–3 Total**: **167.93 $xP$**

##### BB2 Pre-WC Squad Roster (£100.0m Spend) — Scenarios S4, S5, S6
- **GKP**: Donnarumma (£5.5m, MCI), Lammens (£5.0m, MUN)
- **DEF**: O'Reilly (£6.5m, MCI), Mukiele (£5.5m, SUN), Vuskovic (£5.0m, BHA), Ballard (£5.0m, SUN), Alderete (£5.0m, SUN)
- **MID**: Palmer (£9.5m, CHE), Wirtz (£7.5m, LIV), Schade (£6.0m, BRE), Torp (£5.5m, COV), Belloumi (£5.0m, HUL)
- **FWD**: Haaland (£15.5m, MCI), Thiago (£8.0m, BRE), Wright (£5.5m, COV)
- **GW1 XI**: 50.23 $xP$
- **GW2 (BB2 Activated)**: 15-Player Score = **65.84 $xP$**
- **GW3 XI**: 51.35 $xP$
- **GW1–3 Total**: **167.42 $xP$**

---

### Post-WC Phase Squad Rosters (GW4–6)

##### GW4 Wildcard Option 1 (Unconstrained MILP — £100.0m Spend, £0.0m ITB) — Scenarios S1, S4
- **GKP**: Raya (£6.0m, ARS), Wilson (£4.5m, COV)
- **DEF**: Gabriel (£8.0m, ARS), Lacroix (£6.0m, CHE), Tarkowski (£6.0m, EVE), Vuskovic (£5.0m, BHA), Thiaw (£5.0m, NEW)
- **MID**: Palmer (£9.5m, CHE), Sarr (£6.5m, CRY), Ndiaye (£6.0m, EVE), Maeda (£5.5m, IPS), Torp (£5.5m, COV)
- **FWD**: Haaland (£15.5m, MCI), Wright (£5.5m, COV), Emersonn (£5.5m, IPS)
- **GW4 XI**: 50.31 $xP$ | **GW5 XI**: 50.31 $xP$ | **GW6 XI**: 50.66 $xP$
- **GW4–6 Starting XI Total**: **151.28 $xP$**

##### GW4 Wildcard Option 2 (Cheap Defense Cap ≤ £32.0m — £100.0m Spend, £0.0m ITB) — Scenarios S2, S5
- **GKP**: Pickford (£5.5m, EVE), Butland (£4.5m, HUL) — *£10.0m GKP spend*
- **DEF**: Vuskovic (£5.0m, BHA), Thiaw (£5.0m, NEW), Thomas (£4.0m, COV), Coyle (£4.0m, HUL), Greaves (£4.0m, IPS) — *£22.0m DEF spend (Total DEF Cap = £32.0m)*
- **MID**: Bruno Fernandes (£12.0m, MUN), Palmer (£9.5m, CHE), Sarr (£6.5m, CRY), Ndiaye (£6.0m, EVE), Maeda (£5.5m, IPS) — *£39.5m MID spend*
- **FWD**: Haaland (£15.5m, MCI), João Pedro (£7.5m, CHE), McBurnie (£5.5m, HUL) — *£28.5m FWD spend*
- **GW4 XI**: 50.84 $xP$ | **GW5 XI**: 49.33 $xP$ | **GW6 XI**: 46.78 $xP$
- **GW4–6 Starting XI Total**: **146.95 $xP$**

##### GW4 Wildcard Option 3 (Cheap DEF ≤ £32.0m + Liverpool 2+ — £97.0m Spend, £3.0m ITB) — Scenarios S3, S6
- **GKP**: Pickford (£5.5m, EVE), Butland (£4.5m, HUL) — *£10.0m GKP spend*
- **DEF**: Vuskovic (£5.0m, BHA), Thiaw (£5.0m, NEW), Thomas (£4.0m, COV), Coyle (£4.0m, HUL), Greaves (£4.0m, IPS) — *£22.0m DEF spend (Total DEF Cap = £32.0m)*
- **MID**: Palmer (£9.5m, CHE), Sarr (£6.5m, CRY), Ndiaye (£6.0m, EVE), Maeda (£5.5m, IPS), Mac Allister (£5.5m, LIV) — *£33.0m MID spend*
- **FWD**: Haaland (£15.5m, MCI), Isak (£9.0m, LIV), João Pedro (£7.5m, CHE) — *£32.0m FWD spend*
- **GW4 XI**: 50.84 $xP$ | **GW5 XI**: 49.33 $xP$ | **GW6 XI**: 46.27 $xP$
- **GW4–6 Starting XI Total**: **146.44 $xP$**

---

### 3. User Current Squad Comparison (Sticking Strategy vs GW4 Wildcard Evolution)

| Squad Strategy | Pre-WC Chip | GW1–3 xP | GW4–6 xP | Total 6-GW xP | 6-GW xP Lag vs Rec (S3) | Pre-WC Opp. Loss |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Recommended MILP (S3: BB1 + WC4 Opt3)** | GW1 BB | **167.93 $xP$** | **146.44 $xP$** | **314.37 $xP$** | Baseline | Baseline |
| **Top Raw MILP (S1: BB1 + WC4 Opt1)** | GW1 BB | **167.93 $xP$** | **151.28 $xP$** | **319.21 $xP$** | +4.84 $xP$ | Baseline |
| **User Squad Evolved (GW1 BB + GW4 WC Opt1)** | GW1 BB | **146.83 $xP$** | **151.28 $xP$** | **298.11 $xP$** | **-16.26 $xP$** | **-21.10 $xP$** |
| **User Squad Evolved (GW1 BB + 1 FT GW2 + GW4 WC Opt3)** | GW1 BB | **146.66 $xP$** | **146.44 $xP$** | **293.10 $xP$** | **-21.27 $xP$** | **-21.27 $xP$** |
| **User Squad Evolved (GW1 BB + GW4 WC Opt3)** | GW1 BB | **146.83 $xP$** | **146.44 $xP$** | **293.27 $xP$** | **-21.10 $xP$** | **-21.10 $xP$** |
| **User Squad Sticking (GW1 BB + No Wildcard)** | GW1 BB | **146.83 $xP$** | **125.05 $xP$** | **271.88 $xP$** | **-42.49 $xP$** | **-21.10 $xP$** |
| **User Squad Sticking (No BB + No Wildcard)** | None | **138.11 $xP$** | **125.05 $xP$** | **268.16 $xP$** | **-51.21 $xP$** | **-29.82 $xP$** |

#### User Current Squad Composition (£100.0m Spend)
- **GKP**: Kinsky (£4.5m, TOT), Verbruggen (£4.5m, BHA) — *£9.0m GKP spend*
- **DEF**: Ballard (£5.0m, SUN), Thomas (£4.0m, COV), Shaw (£4.5m, MUN), Mitchell (£4.5m, CRY), N.Williams (£5.0m, NFO) — *£23.0m DEF spend*
- **MID**: Ampadu (£5.5m, LEE), Szoboszlai (£7.0m, LIV), Bruno Fernandes (£12.0m, MUN), Mbeumo (£8.0m, MUN), Xhaka (£5.5m, SUN) — *£38.0m MID spend*
- **FWD**: Haaland (£15.5m, MCI), Isak (£9.0m, LIV), Georginio (£5.5m, BHA) — *£30.0m FWD spend*

#### Opportunity Loss & Risk/Reward Assessment
1. **Confined Pre-WC Opportunity Loss**: Because the GW4 Wildcard fully resets the squad roster, the opportunity loss of starting with your actual refreshed squad is **strictly confined to GW1–3**. You give up **21.10 $xP$** without transfers across GW1–3 (scoring 146.83 xP vs MILP 167.93 xP).
2. **Post-WC Equity Recovery**: Once GW4 arrives, executing the Wildcard completely recovers 100% of post-WC equity (yielding **146.44 $xP$** in Opt 3 or **151.28 $xP$** in Opt 1), eliminating any ongoing structural drag.
3. **Is it Worth the Risk?**:
   - **Low to Moderate Risk**: Giving up ~21.1 points over GW1–3 (~7.0 xP/GW) is a manageable deficit if you want to preserve your current squad composition entering GW1.
   - **High Sticking Penalty**: Sticking with your refreshed current squad into GW4–6 without a Wildcard doubles the total 6-GW deficit to **-42.49 $xP$** (or **-51.21 $xP$** without BB), making the GW4 Wildcard evolution step critical.

---

### Gameweek-by-Gameweek Transfer Schedule & FT Banking Flexibility

1. **GW1**: Set initial Bench Boost draft ($\le$ £100.0m spend).
2. **GW2**: **0 to 1 Free Transfer made**. *(Optional 1 FT can be used, e.g. O'Shea $\rightarrow$ Hughes £4.0m, or roll FT $\rightarrow$ 1 FT banked into GW3).*
3. **GW3**: **0 to 1 Free Transfer made**. *(Roll or use 1 FT. Accumulate 2+ FTs entering GW4).*
4. **GW4 (Wildcard Activated)**: Execute Wildcard chip. Unlimited free transfers to transition from Pre-WC squad to chosen Post-WC squad (Opt1, Opt2, or Opt3). Accumulated FTs preserved.
5. **GW5**: **0 to 1 Free Transfer made**. *(Roll or spend 1 FT).*
6. **GW6**: **Enter GW6 post-international break with at least 2 Free Transfers banked** (and up to £3.0m ITB in Option 3).

---

## Strategic Analysis & Synthesis with Broader Research

1. **GW1 BB vs GW2 BB (Chip Timing)**:
   - **GW1 BB1** delivers **65.54 $xP$** in GW1 (all 15 scoring) vs **50.23 $xP$** for GW2 BB2 GW1 XI (+15.31 xP gain in GW1). Overall GW1–3 total reaches **167.93 $xP$** for BB1 vs **167.42 $xP$** for BB2 (+0.51 xP advantage for BB1).
   - GW1 BB eliminates bench selection headache before early-season rotation, locking in a massive starting rank advantage.

2. **Wildcard Structural Trade-Offs (Opt1 vs Opt2 vs Opt3 under ≤ £32.0m DEF Cap)**:
   - **Option 1 (Unconstrained MILP - 319.21 6-GW xP)**: Highest raw mathematical total (319.21 xP), but locks £40.5m into defense (Gabriel, Lacroix, Tarkowski, Raya), leaving only £59.5m for attack, 0 Liverpool assets, and £0.0m ITB.
   - **Option 2 (Cheap DEF ≤32.0m - 314.88 6-GW xP)**: Unlocks Haaland + Bruno Fernandes + Palmer + João Pedro power attack (£68.0m attack spend).
   - **Option 3 (Cheap DEF ≤32.0m + LIV 2+ - 314.37 6-GW xP)**: Scores **314.37 cumulative xP** (up +1.28 xP from 31.5m cap!), secures **Isak (£9.0m) + Mac Allister (£5.5m)** Liverpool coverage AND holds **£3.0m ITB**.

3. **International Break & Risk Management**:
   - Entering GW6 post-international break with **2 Free Transfers** AND **£3.0m ITB** in **Scenario 3 (BB1 + WC4 Opt3)** provides maximum strategic protection against injury news, fixture swings, or price rises without taking hit penalties (-4).

---

## Verdict & Recommendation

**Recommended Path**: **Scenario 3 (S3: GW1 BB1 + GW4 WC Option 3 Cheap DEF ≤ £32.0m + Liverpool 2+)**

**Rationale**:
1. **Highest Pre-WC Points**: GW1 BB1 secures **65.54 $xP$** in GW1 and **167.93 $xP$** across GW1–3 under full £100.0m budget.
2. **Optimal Structural Flexibility**: Option 3 delivers **314.37 cumulative 6-GW xP** (+1.28 xP higher under £32.0m cap), Liverpool premium attacking coverage (Isak + Mac Allister), Pickford (£5.5m) in goal, and leaves **£3.0m ITB** + **2 Free Transfers** entering GW6 post-international break.
