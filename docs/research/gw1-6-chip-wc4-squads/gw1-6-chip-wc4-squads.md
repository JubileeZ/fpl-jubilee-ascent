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

### 1. GW1 Bench Boost Squad Roster (£99.5m Spend, £0.5m ITB — 1 Liverpool Player)

| Position | Player | Club | Price | Expected Role | GW1 $xP$ | GW1–3 $xP$ | Strategy Role |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
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
| **FWD** | Haaland | MCI | £15.5m | Nailed Starter | 5.54 | 17.89 | Premium FWD |
| **FWD** | Isak | LIV | £9.0m | Nailed Starter | 4.11 | 12.98 | Premium FWD |
| **FWD** | Thiago | BRE | £8.0m | Nailed Starter | 4.18 | 13.30 | Premium FWD |

**Bench Boost GW1 Score**: **74.15 $xP$** (All 15 players score).

---

### 2. GW4 Wildcard Comparison (With Triple Liverpool — 3 LIV Players)

| Metric / Dimension | Option 1: Unconstrained MILP (Triple LIV) | Option 2: Cheap Defense Cap ≤ £31.5m (Triple LIV) | Strategic Takeaway |
| :--- | :---: | :---: | :--- |
| **Triple Liverpool Lineup** | A.Becker (£5.5m) + Gravenberch (£6.0m) + Mac Allister (£5.5m) | **Alexander Isak (£9.0m)** + **Florian Wirtz (£7.5m)** + Mac Allister (£5.5m) | Option 2 starts Isak + Wirtz |
| **GKP + DEF Spend** | £37.5m (O'Reilly £6.5m, Donnarumma £5.5m) | £31.5m (Vuskovic £5m, Kayode £4.5m) | Option 2 saves £6.0m |
| **Formation** | 5-4-1 (5 Defenders starting) | 3-4-3 (3 Defenders starting) | Option 2 focuses on Attack |
| **Attacking XI** | Haaland + Palmer + Sarr + Ndiaye | **Haaland (£15.5m) + Isak (£9.0m) + Palmer (£9.5m) + Wirtz (£7.5m) + João Pedro (£7.5m)** | Powerhouse Attack |
| **GW4–6 XI $xP$** | **149.32 $xP$** | **142.59 $xP$** | **Option 1 is Mathematical Optimum** |

#### Option 2: Recommended GW4 Wildcard Roster (Triple Liverpool)

| Position | Player | Club | Price | Role | GW4–6 $xP$ | Strategy Role |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **GKP** | Leno | FUL | £4.5m | Nailed | 10.88 | Starting GKP |
| **GKP** | Wilson | COV | £4.5m | Regular | 8.23 | Bench GKP |
| **DEF** | Vuskovic | BHA | £5.0m | Nailed | 14.23 | Defense Anchor |
| **DEF** | Ballard | SUN | £5.0m | Nailed | 13.47 | Defense Anchor |
| **DEF** | Kayode | BRE | £4.5m | Nailed | 12.13 | High xA Wingback |
| **DEF** | Thomas | COV | £4.0m | Regular | 9.63 | £4.0m Bench DEF |
| **DEF** | Hughes | HUL | £4.0m | Regular | 10.50 | £4.0m Bench DEF |
| **MID** | Palmer | CHE | £9.5m | Nailed | 15.02 | **Premium MID** |
| **MID** | **Wirtz** | **LIV** | **£7.5m** | **Nailed** | **11.68** | **Liverpool Premium MID** |
| **MID** | Sarr | CRY | £6.5m | Nailed | 13.76 | Mid-Price Attacker |
| **MID** | Ndiaye | EVE | £6.0m | Nailed | 12.55 | Mid-Price Attacker |
| **MID** | **Mac Allister** | **LIV** | **£5.5m** | **Nailed** | **9.46** | **Liverpool Midfield Enabler** |
| **FWD** | Haaland | MCI | £15.5m | Nailed | 14.69 | **Captain / Premium FWD** |
| **FWD** | **Isak** | **LIV** | **£9.0m** | **Nailed** | **11.81** | **Liverpool Premium FWD** |
| **FWD** | João Pedro | CHE | £7.5m | Nailed | 12.37 | Mid-Price FWD |
| **FWD** | Beto | EVE | £5.5m | Regular | 10.33 | Value FWD |

---

### 3. GW5–6 Free Transfer Banking Strategy

1. **GW4 (Wildcard)**: Deploy Option 2 squad above.
2. **GW5 (Hold 0 FTs)**: Make 0 transfers. Roll the free transfer into GW6.
3. **GW6 (Post-International Break)**: Enter GW6 with **2 Free Transfers**.
   - Allows flexible double-transfers to deal with international break injuries or tactical shifts without taking hit penalties (-4).

---

## Decision

**Verdict**: Adopt **GW1 Bench Boost (£99.5m spend)** followed by **GW4 Wildcard Option 2 (Cheap Defense Cap ≤ £31.5m)** and **Bank 2 FTs for GW6**.

**Recommended action**:
- Deploy 15-starter BB1 squad in GW1.
- Activate Wildcard in GW4 using Option 2 roster (Haaland + Bruno Fernandes + Palmer).
- Make 0 transfers in GW5 to bank 2 FTs for GW6 post-international break.
