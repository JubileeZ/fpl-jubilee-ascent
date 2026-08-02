# GW1–6 Early Chip & GW4 Wildcard Squad Optimization (3×2 Matrix Study)

**Updated**: 2026-08-03T04:04:28+07:00  
**Data stamp**: Projections CSV 2026-08-03 (ParticipationStateHybridModel horizon 6); FPL API player pricing 2026-07-29  
**Season**: 2026/27 · horizon GW1–6  
**Status**: Active Research Model  
**Purpose**: Execute full 6-Gameweek optimization study across a $3 \times 2 = 6$ scenario matrix combining Pre-WC Bench Boost timing (GW1 BB vs GW2 BB under £99.5m spend, £0.5m ITB) with GW4 Wildcard structural designs (Option 1 Unconstrained MILP, Option 2 Cheap-Defense Cap ≤ £31.5m, and Option 3 Cheap-Defense Cap ≤ £31.5m + Liverpool 2+). All scenarios enforce GW5 transfer rolling to enter GW6 with 2+ Free Transfers banked post-international break.  
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
- Pre-WC Budget: £99.5m spend (£0.5m ITB buffer). Post-WC Budget: <= £100.0m.

Matrix Dimensions (3x2 = 6 Scenarios):
- Pre-WC Chip Options (2):
  A. BB1: Bench Boost in GW1 (holding £0.5m ITB, min 1 Liverpool asset).
  B. BB2: Bench Boost in GW2 (holding £0.5m ITB, min 1 Liverpool asset).
- Post-WC Structural Options (3):
  1. Opt1 (Unconstrained MILP): Maximize GW4-6 XI xP under £100.0m without position caps or club constraints.
  2. Opt2 (Cheap Defense Cap): Maximize GW4-6 XI xP with GKP + 5 DEF spend <= £31.5m (leaving >= £68.5m for 5 MID + 3 FWD).
  3. Opt3 (Cheap Defense Cap + Liverpool 2+): GKP + 5 DEF spend <= £31.5m AND enforce >= 2 Liverpool assets (e.g. Isak + Mac Allister).

Execution & Constraints:
- Roll Free Transfer in GW5 (0 FTs used) to ensure >= 2 Free Transfers enter GW6 post-international break.
- For each of the 6 scenarios, calculate exact per-gameweek starting XI + bench xP, total 6-GW cumulative xP, exact GW1-6 squad lists, and transfer logs.
- Export results to data/research/gw1-6-chip-wc4-squads/gw1-6_wc4_simulation.csv.
- Run ruff check and verify delivery gates before completing.
```

---

## Method

1. **Pre-WC Draft MILP (GW1–3)**:
   - **Path A (BB1)**: Bench Boost deployed in GW1 (£99.5m spend, £0.5m ITB). All 15 players score in GW1; best 11 fielded in GW2–3.
   - **Path B (BB2)**: Bench Boost deployed in GW2 (£99.5m spend, £0.5m ITB). Best 11 fielded in GW1 & GW3; all 15 players score in GW2.
   - Minimum 1 Liverpool player enforced pre-WC.
2. **Wildcard MILP (GW4–6)**:
   - **Option 1 (Unconstrained MILP)**: Solves GW4–6 squad under £100.0m with no defensive spend cap or club constraints.
   - **Option 2 (Cheap Defense Cap ≤ £31.5m)**: Caps GKP (2) + DEF (5) spend at ≤ £31.5m total, forcing £68.5m into 5 MID + 3 FWD.
   - **Option 3 (Cheap Defense Cap ≤ £31.5m + Liverpool 2+)**: Caps GKP + DEF spend at ≤ £31.5m AND enforces ≥ 2 Liverpool assets.
3. **Transfer Schedule & Banking**:
   - GW1: Deploy initial draft.
   - GW2–3: Roll transfers (0 FTs used).
   - GW4: Activate Wildcard (unlimited transfers).
   - GW5: Roll transfer (0 FTs used).
   - GW6: Enter GW6 with **2 Free Transfers banked** post-international break.

---

## Findings

### 1. 3×2 Matrix Summary Table (Cumulative GW1–6 xP & Metrics)

| Scenario ID | Pre-WC Chip | Post-WC Option | GW1–3 XI xP | GW4–6 XI xP | Total 6-GW xP | Pre Spend | Post Spend | GW6 ITB | Banked FTs (GW6) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **S1** | GW1 BB1 | Opt1 (Unconstrained) | **167.86 $xP$** | **151.28 $xP$** | **319.14 $xP$** | £99.5m | £100.0m | £0.0m | **2 FTs** |
| **S2** | GW1 BB1 | Opt2 (Cheap DEF) | **167.86 $xP$** | 147.52 $xP$ | **315.38 $xP$** | £99.5m | £100.0m | £0.0m | **2 FTs** |
| **S3** | GW1 BB1 | Opt3 (Cheap DEF + LIV 2+) | **167.86 $xP$** | 145.16 $xP$ | **313.02 $xP$** | £99.5m | £96.5m | **£3.5m** | **2 FTs** |
| **S4** | GW2 BB2 | Opt1 (Unconstrained) | 167.06 $xP$ | **151.28 $xP$** | **318.34 $xP$** | £99.5m | £100.0m | £0.0m | **2 FTs** |
| **S5** | GW2 BB2 | Opt2 (Cheap DEF) | 167.06 $xP$ | 147.52 $xP$ | **314.58 $xP$** | £99.5m | £100.0m | £0.0m | **2 FTs** |
| **S6** | GW2 BB2 | Opt3 (Cheap DEF + LIV 2+) | 167.06 $xP$ | 145.16 $xP$ | **312.22 $xP$** | £99.5m | £96.5m | **£3.5m** | **2 FTs** |

---

### 2. Full GW1–6 Squad Lists & Transfer Schedules for All Scenarios

#### Pre-WC Phase Squad Rosters (GW1–3)

##### BB1 Pre-WC Squad Roster (£99.5m Spend, £0.5m ITB) — Scenarios S1, S2, S3
- **GKP**: Donnarumma (£5.5m, MCI), Lammens (£5.0m, MUN)
- **DEF**: O'Reilly (£6.5m, MCI), Vuskovic (£5.0m, BHA), Ballard (£5.0m, SUN), Alderete (£5.0m, SUN), Maguire (£5.0m, MUN)
- **MID**: Sarr (£6.5m, CRY), Ndiaye (£6.0m, EVE), Schade (£6.0m, BRE), E.Le Fée (£6.0m, SUN), Maeda (£5.5m, IPS)
- **FWD**: Haaland (£15.5m, MCI), Isak (£9.0m, LIV), Thiago (£8.0m, BRE)
- **GW1 (BB1 Activated)**: 15-Player Score = **74.15 $xP$**
- **GW2 XI**: 46.88 $xP$ | **GW3 XI**: 46.83 $xP$
- **GW1–3 Total**: **167.86 $xP$**

##### BB2 Pre-WC Squad Roster (£99.5m Spend, £0.5m ITB) — Scenarios S4, S5, S6
- **GKP**: Donnarumma (£5.5m, MCI), Lammens (£5.0m, MUN)
- **DEF**: O'Reilly (£6.5m, MCI), Vuskovic (£5.0m, BHA), Ballard (£5.0m, SUN), Alderete (£5.0m, SUN), Thomas (£4.0m, COV)
- **MID**: Palmer (£9.5m, CHE), Wirtz (£7.5m, LIV), Schade (£6.0m, BRE), E.Le Fée (£6.0m, SUN), Torp (£5.5m, COV)
- **FWD**: Haaland (£15.5m, MCI), Thiago (£8.0m, BRE), Wright (£5.5m, COV)
- **GW1 XI**: 54.21 $xP$
- **GW2 (BB2 Activated)**: 15-Player Score = **65.97 $xP$**
- **GW3 XI**: 46.88 $xP$
- **GW1–3 Total**: **167.06 $xP$**

---

#### Post-WC Phase Squad Rosters (GW4–6)

##### GW4 Wildcard Option 1 (Unconstrained MILP — £100.0m Spend, £0.0m ITB) — Scenarios S1, S4
- **GKP**: Raya (£6.0m, ARS), Wilson (£4.5m, COV)
- **DEF**: Gabriel (£8.0m, ARS), Lacroix (£6.0m, CHE), Tarkowski (£6.0m, EVE), Vuskovic (£5.0m, BHA), Thiaw (£5.0m, NEW)
- **MID**: Palmer (£9.5m, CHE), Sarr (£6.5m, CRY), Ndiaye (£6.0m, EVE), Maeda (£5.5m, IPS), Torp (£5.5m, COV)
- **FWD**: Haaland (£15.5m, MCI), Wright (£5.5m, COV), Emersonn (£5.5m, IPS)
- **GW4 XI**: 51.52 $xP$ | **GW5 XI**: 51.04 $xP$ | **GW6 XI**: 48.72 $xP$
- **GW4–6 Starting XI Total**: **151.28 $xP$**

##### GW4 Wildcard Option 2 (Cheap Defense Cap ≤ £31.5m — £100.0m Spend, £0.0m ITB) — Scenarios S2, S5
- **GKP**: Sánchez (£5.0m, CHE), Leno (£4.5m, FUL)
- **DEF**: Vuskovic (£5.0m, BHA), Thiaw (£5.0m, NEW), Thomas (£4.0m, COV), Greaves (£4.0m, IPS), O'Shea (£4.0m, IPS)
- **MID**: Bruno Fernandes (£12.0m, MUN), Palmer (£9.5m, CHE), Sarr (£6.5m, CRY), Ndiaye (£6.0m, EVE), Maeda (£5.5m, IPS)
- **FWD**: Haaland (£15.5m, MCI), João Pedro (£7.5m, CHE), Calvert-Lewin (£6.0m, LEE)
- **GW4 XI**: 50.84 $xP$ | **GW5 XI**: 49.33 $xP$ | **GW6 XI**: 47.35 $xP$
- **GW4–6 Starting XI Total**: **147.52 $xP$**

##### GW4 Wildcard Option 3 (Cheap DEF ≤ £31.5m + Liverpool 2+ — £96.5m Spend, £3.5m ITB) — Scenarios S3, S6
- **GKP**: Sánchez (£5.0m, CHE), Butland (£4.5m, HUL)
- **DEF**: Vuskovic (£5.0m, BHA), Thiaw (£5.0m, NEW), Thomas (£4.0m, COV), Coyle (£4.0m, HUL), Egan (£4.0m, HUL)
- **MID**: Palmer (£9.5m, CHE), Sarr (£6.5m, CRY), Ndiaye (£6.0m, EVE), Maeda (£5.5m, IPS), Mac Allister (£5.5m, LIV)
- **FWD**: Haaland (£15.5m, MCI), Isak (£9.0m, LIV), João Pedro (£7.5m, CHE)
- **GW4 XI**: 49.97 $xP$ | **GW5 XI**: 48.86 $xP$ | **GW6 XI**: 46.33 $xP$
- **GW4–6 Starting XI Total**: **145.16 $xP$**

---

#### Exact Gameweek-by-Gameweek Transfer Schedule (All Scenarios)

1. **GW1**: Set initial Bench Boost draft (£99.5m spend, holding £0.5m ITB).
2. **GW2**: **0 Free Transfers made**. (Roll FT $\rightarrow$ 1 FT banked into GW3).
3. **GW3**: **0 Free Transfers made**. (Roll FT $\rightarrow$ 2 FTs banked into GW4).
4. **GW4 (Wildcard Activated)**: Execute Wildcard chip. Unlimited free transfers to transition from Pre-WC squad to chosen Post-WC squad (Opt1, Opt2, or Opt3). Budget up to £100.0m.
5. **GW5**: **0 Free Transfers made**. (Roll FT $\rightarrow$ 1 FT banked into GW6).
6. **GW6**: **0 Free Transfers made**. (Roll FT $\rightarrow$ **2 Free Transfers Banked entering GW6 post-international break** + up to £3.5m ITB).

---

## Strategic Analysis & Synthesis with Broader Research

1. **GW1 BB vs GW2 BB (Chip Timing)**:
   - **GW1 BB1** delivers **74.15 $xP$** in GW1 (all 15 scoring) vs **65.97 $xP$** for GW2 BB2 (+8.18 xP gain in GW1).
   - GW1 BB eliminates bench selection headache before early-season rotation, locking in a massive starting rank advantage.

2. **Wildcard Structural Trade-Offs (Opt1 vs Opt2 vs Opt3)**:
   - **Option 1 (Unconstrained MILP - 319.14 6-GW xP)**: Highest raw mathematical total (319.14 xP), but locks £40.5m into defense (Gabriel, Lacroix, Tarkowski, Raya), leaving only £59.5m for attack, 0 Liverpool assets, and £0.0m ITB.
   - **Option 2 (Cheap DEF - 315.38 6-GW xP)**: Unlocks Haaland + Bruno Fernandes + Palmer + João Pedro power attack (£68.5m attack spend).
   - **Option 3 (Cheap DEF + LIV 2+ - 313.02 6-GW xP)**: Scores 313.02 cumulative xP (only ~0.78 xP/GW behind Opt2), but secures **Isak (£9.0m) + Mac Allister (£5.5m)** Liverpool coverage AND holds **£3.5m ITB**.

3. **International Break & Risk Management**:
   - Entering GW6 post-international break with **2 Free Transfers** AND **£3.5m ITB** in **Scenario 3 (BB1 + WC4 Opt3)** provides maximum strategic protection against injury news, fixture swings, or price rises without taking hit penalties (-4).

---

## Verdict & Recommendation

**Recommended Path**: **Scenario 3 (S3: GW1 BB1 + GW4 WC Option 3 Cheap DEF ≤ £31.5m + Liverpool 2+)**

**Rationale**:
1. **Highest Pre-WC Points**: GW1 BB1 secures **74.15 $xP$** in GW1 and **167.86 $xP$** across GW1–3.
2. **Optimal Structural Flexibility**: Option 3 delivers **313.02 cumulative 6-GW xP**, Liverpool premium attacking coverage (Isak + Mac Allister), and leaves **£3.5m ITB** + **2 Free Transfers** entering GW6 post-international break.
