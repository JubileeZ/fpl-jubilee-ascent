# GW1–6 Early Chip & GW4 Wildcard Squad Optimization

**Updated**: 2026-08-02T13:20:00+07:00  
**Data stamp**: Projections CSV 2026-08-02 (ParticipationStateHybridModel horizon 6); FPL API player pricing 2026-07-29  
**Season**: 2026/27 · horizon GW1–6  
**Status**: Active Research Model  
**Purpose**: Provide exact squad lists for GW1 Bench Boost (BB1) under £99.5m, compare GW4 Wildcard squad design strategies (Unconstrained MILP vs Cheap-Defense Cap ≤ £31.5m), and detail the GW5–6 Free Transfer roll-over strategy for post-international break flexibility.  
**Scope**: 15-player squad optimization across GW1–6, pricing constraints, position caps, and free transfer banking into GW6.  
**Related**: [GW1–5 Chip Strategy Simulation](../gw1-5-chip-simulation/gw1-5-chip-simulation.md) · [Expected Stats GW1–5](../expected-stats-gw1-5/expected-stats-gw1-5.md) · [Simulation Runner](run_wc4_simulation.py)  
**Artifacts**:
- [Squad Simulation CSV](../../../data/research/gw1-6-chip-wc4-squads/gw1-6_wc4_simulation.csv) — row-level squad rosters and projections across GW1–6
- [Projections CSV](../../../data/research/gw1-6-chip-wc4-squads/gw1-6_projections.csv) — GW1–6 player-level $xP$ and $xMins$

---

## Sources

- **Primary Projections Input**: `data/research/gw1-6-chip-wc4-squads/gw1-6_projections.csv` (ParticipationStateHybridModel 6-GW horizon).
- **Player Pricing & Metadata**: `data/processed/players.parquet` and `data/processed/clubs.parquet`.
- **Optimization Runner**: `docs/research/gw1-6-chip-wc4-squads/run_wc4_simulation.py` (scipy MILP).

---

## Agent Prompt

```text
Run GW1-6 chip and GW4 Wildcard optimization study:

1. Generate GW1-6 hybrid model projections across eligible starters.
2. Solve GW1 Bench Boost draft (£99.5m spend, £0.5m ITB) returning exact 15-player squad list.
3. Solve GW4 Wildcard Option 1: Unconstrained MILP optimization.
4. Solve GW4 Wildcard Option 2: Cheap Defense Cap (GKP + 5 DEF <= £31.5m, leaving >= £68.5m for 5 MID + 3 FWD).
5. Compare GW4-6 XI xP, team composition, premium MID/FWD flexibility, and GW5-6 FT banking strategy.
6. Export data/research/gw1-6-chip-wc4-squads/gw1-6_wc4_simulation.csv.
7. Run ruff check and verify delivery gates before finishing.
```

---

## Method

1. **GW1 BB1 Draft MILP**:
   - Budget cap: £99.5m (holding £0.5m ITB for WC4 flexibility).
   - Objective: Maximize 15-player $xP$ in GW1 + XI $xP$ in GW2–3.
2. **GW4 Wildcard Comparison**:
   - **Option 1 (Unconstrained)**: MILP solves squad under £100.0m for GW4–6 with no defensive cap.
   - **Option 2 (Cheap-Defense Cap ≤ £31.5m)**: MILP caps GKP (2) + DEF (5) spend at ≤ £31.5m total, forcing £68.5m+ into 5 MID + 3 FWD.
3. **GW5–6 Roll-Over Strategy**:
   - Make 0 transfers in GW5 to bank 2 Free Transfers for GW6 (post-September international break).

---

## Findings

### 1. Scenario Summary & Multi-Strategy Comparison Across GW1–6

| Dimension / Metric | Scenario 1: GW1 BB1 Optimized Draft | Scenario 2: User Live Pre-Draft Squad | Scenario 3: WC4 Option 1 (Unconstrained) | Scenario 4: WC4 Option 2 (Cheap Defense ≤ £31.5m) |
| :--- | :---: | :---: | :---: | :---: |
| **Strategy Purpose** | Maximize GW1 BB1 score | Current FPL API Pre-Draft | Maximize GW4–6 raw xP | Balance attack & structure |
| **GW1 Bench Boost (15-Player) $xP$** | **74.15 $xP$** | **66.89 $xP$** (-7.26 vs BB1) | N/A (WC in GW4) | N/A (WC in GW4) |
| **GW4–6 Starting XI $xP$** | 134.50 $xP$ | 130.20 $xP$ | **149.32 $xP$** | **142.59 $xP$** |
| **Defensive Spend (GKP + 5 DEF)** | £37.0m | £30.0m | £37.5m (Heavy DEF) | **£31.5m** (Cheap DEF) |
| **Attacking Spend (5 MID + 3 FWD)** | £62.5m | £40.5m | £62.5m | **£68.5m+** (Powerhouse) |
| **Triple Liverpool (3 LIV) Assets** | Isak (£9.0m) | Kelleher (£5.0m) | Alisson + Gravenberch + Mac Allister | **Isak (£9.0m) + Wirtz (£7.5m) + Mac Allister (£5.5m)** |
| **Premium Attackers** | Haaland + Isak + Thiago | Mount | Haaland + Palmer | **Haaland + Palmer + Isak + Wirtz** |
| **Primary Formation** | 3-4-3 | 4-5-1 | 5-4-1 / 4-5-1 | **3-4-3 / 3-5-2** |
| **ITB Remaining** | £0.5m | £29.5m | £0.0m | **£1.0m** |

---

### 2. Detailed Roster Breakdowns by Scenario

#### Scenario 1: GW1 Bench Boost Squad Roster (£99.5m Spend, £0.5m ITB — 1 Liverpool Player: Isak)

| Position | Player | Club | Price | Expected Role | GW1 $xP$ | GW1–3 $xP$ | Strategy Role |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **GKP** | Donnarumma | MCI | £5.5m | Nailed Starter | 4.02 | 12.56 | Starting GKP |
| **GKP** | Lammens | MUN | £5.0m | Nailed Starter | 4.21 | 11.86 | Bench GKP (BB1) |
| **DEF** | O'Reilly | MCI | £6.5m | Regular Starter | 4.31 | 13.58 | Premium DEF Anchor |
| **DEF** | Vuskovic | BHA | £5.0m | Nailed Starter | 4.71 | 14.20 | Value DEF |
| **DEF** | Ballard | SUN | £5.0m | Nailed Starter | 4.97 | 13.93 | Value DEF |
| **DEF** | Alderete | SUN | £5.0m | Nailed Starter | 4.73 | 13.31 | Value DEF |
| **DEF** | Maguire | MUN | £5.0m | Nailed Starter | 4.32 | 12.04 | Value DEF |
| **MID** | Sarr | CRY | £6.5m | Nailed Starter | 4.38 | 12.29 | Mid-Price MID |
| **MID** | Ndiaye | EVE | £6.0m | Nailed Starter | 3.97 | 11.40 | Mid-Price MID |
| **MID** | Schade | BRE | £6.0m | Nailed Starter | 4.03 | 12.74 | Mid-Price MID |
| **MID** | E.Le Fée | SUN | £6.0m | Nailed Starter | 4.41 | 12.62 | Mid-Price MID |
| **MID** | Maeda | IPS | £5.5m | Regular Starter | 4.64 | 10.90 | Mid-Price MID |
| **FWD** | Haaland | MCI | £15.5m | Nailed Starter | 5.54 | 17.89 | Captain / Premium FWD |
| **FWD** | **Isak** | **LIV** | **£9.0m** | **Nailed Starter** | **4.11** | **12.98** | **Liverpool Premium FWD** |
| **FWD** | Thiago | BRE | £8.0m | Nailed Starter | 4.18 | 13.30 | Premium FWD |

**Bench Boost GW1 Score**: **74.15 $xP$** (All 15 players score).

---

#### Scenario 2: User Live Pre-Draft Squad (FPL Manager Entry 822158)

| Position | Player | Club | Price | GW1 $xP$ | GW1–3 $xP$ | GW4–6 $xP$ | Status & Comparison |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **GKP** | Kelleher | BRE | £5.0m | 5.02 | 15.66 | 12.97 | Starting GKP |
| **DEF** | J.Timber | ARS | £6.5m | 5.88 | 15.19 | 16.12 | Premium DEF |
| **DEF** | Hall | NEW | £5.0m | 4.38 | 13.57 | 15.17 | Value DEF |
| **DEF** | Tete | FUL | £4.5m | 4.33 | 15.02 | 14.60 | Value DEF |
| **DEF** | Acheampong | CHE | £4.5m | 4.89 | 14.35 | 14.83 | Enabler |
| **DEF** | Aznou | EVE | £4.0m | 5.34 | 14.52 | 16.23 | £4.0m Enabler |
| **MID** | Sangaré | NFO | £5.0m | 5.11 | 14.78 | 14.78 | Value MID |
| **MID** | Mount | MUN | £5.5m | 4.72 | 13.92 | 14.13 | Mid-Price MID |
| **MID** | Burns | IPS | £5.0m | 5.11 | 13.99 | 13.89 | Value MID |
| **MID** | Adli | BOU | £5.0m | 4.61 | 12.95 | 12.86 | Value MID |
| **MID** | Carvalho | BRE | £5.0m | 4.42 | 13.45 | 11.86 | Value MID |
| **MID** | Matazo | HUL | £4.5m | 4.14 | 14.17 | 12.29 | £4.5m Enabler |
| **MID** | J.Murphy | NEW | £6.0m | 4.24 | 12.58 | 13.21 | Mid-Price MID |
| **FWD** | Ferguson | BHA | £5.0m | 4.68 | 13.42 | 13.48 | Value FWD |

- **User Squad GW1 Bench Boost (15 Players)**: **66.89 $xP$** (lacks Haaland / Palmer premiums; **-7.26 $xP$ behind BB1 draft**).
- **User Squad GW4–6 Starting XI**: **130.20 $xP$** (**-12.39 $xP$ behind Cheap Defense WC4**).

---

#### Scenario 3: GW4 Wildcard Option 1 — Unconstrained MILP (Triple Liverpool)

| Position | Player | Club | Price | Role | GW4–6 $xP$ | Strategy Role |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **GKP** | Raya | ARS | £6.0m | Nailed | 12.51 | Starting GKP |
| **GKP** | **A.Becker** | **LIV** | **£5.5m** | **Nailed** | **10.85** | **Liverpool GKP (Triple LIV)** |
| **DEF** | Gabriel | ARS | £8.0m | Nailed | 14.35 | Premium DEF |
| **DEF** | O'Reilly | MCI | £6.5m | Regular | 13.58 | Premium DEF |
| **DEF** | Lacroix | CHE | £6.0m | Nailed | 13.01 | Premium DEF |
| **DEF** | Vuskovic | BHA | £5.0m | Nailed | 14.08 | Value DEF |
| **DEF** | Thiaw | NEW | £5.0m | Nailed | 13.41 | Value DEF |
| **MID** | Palmer | CHE | £9.5m | Nailed | 15.62 | **Premium MID** |
| **MID** | Sarr | CRY | £6.5m | Nailed | 14.14 | Mid-Price MID |
| **MID** | **Gravenberch** | **LIV** | **£6.0m** | **Nailed** | **9.04** | **Liverpool MID (Triple LIV)** |
| **MID** | Ndiaye | EVE | £6.0m | Nailed | 13.23 | Mid-Price MID |
| **MID** | **Mac Allister** | **LIV** | **£5.5m** | **Nailed** | **9.58** | **Liverpool MID (Triple LIV)** |
| **FWD** | Haaland | MCI | £15.5m | Nailed | 15.08 | **Captain / Premium FWD** |
| **FWD** | Wright | COV | £5.5m | Regular | 11.60 | Enabler FWD |
| **FWD** | McBurnie | HUL | £5.5m | Regular | 8.78 | Enabler FWD |

- **GW4–6 Starting XI $xP$**: **149.32 $xP$** (Mathematical maximum).
- **Structure**: 5-4-1 / 4-5-1 heavy defensive structure. GKP + 5 DEF spend = **£37.5m**. Misses Isak & Wirtz.

---

#### Scenario 4: GW4 Wildcard Option 2 — Cheap-Defense Cap ≤ £31.5m (Triple Liverpool)

| Position | Player | Club | Price | Role | GW4–6 $xP$ | Strategy Role |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **GKP** | Leno | FUL | £4.5m | Nailed | 10.88 | Starting GKP |
| **GKP** | Wilson | COV | £4.5m | Regular | 8.23 | Bench GKP |
| **DEF** | Vuskovic | BHA | £5.0m | Nailed | 14.23 | Defense Anchor |
| **DEF** | Ballard | SUN | £5.0m | Nailed | 13.47 | Defense Anchor |
| **DEF** | Kayode | BRE | £4.5m | Nailed | 12.13 | High $xA$ Wingback |
| **DEF** | Thomas | COV | £4.0m | Regular | 9.63 | £4.0m Bench DEF |
| **DEF** | Hughes | HUL | £4.0m | Regular | 10.50 | £4.0m Bench DEF |
| **MID** | **Palmer** | CHE | £9.5m | Nailed | 15.02 | **Premium MID** |
| **MID** | **Wirtz** | **LIV** | **£7.5m** | **Nailed** | **11.68** | **Liverpool Premium MID** |
| **MID** | Sarr | CRY | £6.5m | Nailed | 13.76 | Mid-Price Attacker |
| **MID** | Ndiaye | EVE | £6.0m | Nailed | 12.55 | Mid-Price Attacker |
| **MID** | **Mac Allister** | **LIV** | **£5.5m** | **Nailed** | **9.46** | **Liverpool Midfield Enabler** |
| **FWD** | **Haaland** | MCI | £15.5m | Nailed | 14.69 | **Captain / Premium FWD** |
| **FWD** | **Isak** | **LIV** | **£9.0m** | **Nailed** | **11.81** | **Liverpool Premium FWD** |
| **FWD** | João Pedro | CHE | £7.5m | Nailed | 12.37 | Mid-Price FWD |
| **FWD** | Beto | EVE | £5.5m | Regular | 10.33 | Value FWD |

- **GW4–6 Starting XI $xP$**: **142.59 $xP$**.
- **Structure**: 3-4-3 / 3-5-2 attacking structure. GKP + 5 DEF spend = **£31.5m** (saves £6.0m). Unlocks **Haaland + Isak + Palmer + Wirtz + João Pedro** + **£1.0m ITB**.

---

### 3. GW5–6 Free Transfer Banking Strategy

1. **GW4 (Wildcard)**: Deploy Scenario 4 (Option 2 Cheap-Defense WC4 squad).
2. **GW5 (Hold 0 FTs)**: Make 0 transfers. Roll the free transfer into GW6.
3. **GW6 (Post-International Break)**: Enter GW6 with **2 Free Transfers**.
   - Allows flexible double-transfers to deal with international break injuries or tactical shifts without taking hit penalties (-4).

---

## Decision

**Verdict**: Adopt **Scenario 1 (GW1 Bench Boost £99.5m draft)** followed by **Scenario 4 (GW4 Wildcard Option 2 Cheap-Defense Cap ≤ £31.5m)** and **Bank 2 FTs into GW6**.

**Recommended Action**:
1. Upgrade current pre-draft squad to Scenario 1 roster before GW1 deadline (+7.26 $xP$ gain in GW1 BB1).
2. Execute Wildcard in GW4 using Scenario 4 Cheap-Defense roster (Haaland + Isak + Palmer + Wirtz + Mac Allister).
3. Bank free transfer in GW5 to enter GW6 with 2 FTs after the international break.
