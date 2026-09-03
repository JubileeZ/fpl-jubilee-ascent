# First-Half GKP Rotation Pairs (GW1–19)

**Updated**: 2026-09-04T00:50:54+07:00  
**Data stamp**: 2026-09-04 (FPL API bootstrap-static + fixtures; GW2 complete, GW3 next)  
**Season**: 2026/27  
**Status**: Active  
**Purpose**: Rank starting goalkeeper rotation pairs across GW1–19 using Modified FDR, after Emiliano Martínez moved to Chelsea, and answer which partner fits Raya plus whether any £4.5 pair covers 100% of weeks at Modified FDR $\le 2.25$.  
**Scope**: GW 1–19 fixtures (190 matches); 20 current starting goalkeepers; Modified FDR ($\pm 0.25$ home/away); live FPL prices; coverage metric `pct_gw_mod_le_2_25`.  
**Related**: [`INDEX.md`](../INDEX.md) · [First-Half Chip Strategy](../fpl-first-half-chip-strategy/fpl-first-half-chip-strategy.md)  
**Artifact**: [gkp_rotation_pairs_summary.csv](gkp_rotation_pairs_summary.csv) `total_mod_fdr` / `pct_gw_mod_le_2_25` · [raya_rotation_partners.csv](raya_rotation_partners.csv) `total_mod_fdr` · [starting_gkps_gw1_19.csv](starting_gkps_gw1_19.csv) · [gw1_19_rotation_schedule_picks.csv](gw1_19_rotation_schedule_picks.csv)

---

## Sources

- **Primary (transfer)**: [Emiliano Martínez finally gets his Villa exit with £7.5m move to Chelsea — Press Association / The Guardian](https://www.theguardian.com/football/2026/aug/30/emiliano-martinez-aston-villa-exit-move-chelsea) — published 2026-08-30; accessed 2026-09-04; role: Chelsea signing; Sánchez to be displaced as No. 1.
- **Primary (transfer, independent)**: [Martinez 'delighted' to join Blues — BBC Sport](https://www.bbc.com/sport/football/articles/cm2rv0pxl2go) — published 2026-08-30; accessed 2026-09-04; role: fee, contract, same-day debut vs Brighton.
- **Primary (lineup)**: [2pm team news: Martinez debut — Fantasy Football Scout](https://www.fantasyfootballscout.co.uk/2026/08/30/2pm-team-news-martinez-debut-james-wilson-dango-benched) — published 2026-08-30; accessed 2026-09-04; role: Chelsea XI GW2, Martínez started, Sánchez omitted from matchday squad.
- **Repository data**: FPL `bootstrap-static` + `fixtures` fetched 2026-09-04; `data/processed/fixtures.parquet` FDR ticks (0 mismatches vs live API across 380 fixtures). Live `now_cost` overlay in `runner.py`.

**Source boundary**: Starting shirts for GW3–19 are inferred from GW1–2 FPL minutes plus the Martínez transfer. Official Fixture Difficulty ticks are unchanged vs the 2026-08-22 parquet. Club Modified FDR does not move when a keeper changes clubs.

---

## Agent Prompt

```text
Full redo docs/research/gkp-fdr-rotation-gw1-19/gkp-fdr-rotation-gw1-19.md

1. Confirm Chelsea starter from live FPL bootstrap (club_id + minutes) plus current lineup source. Martínez CHE after 2026-08-30 transfer; Sánchez not in the 20-club set (Como loan).
2. Run `uv run python docs/research/gkp-fdr-rotation-gw1-19/runner.py` (live bootstrap prices; fixtures.parquet FDR).
3. Verify companions: starting_gkps_gw1_19.csv, gkp_rotation_pairs_summary.csv, raya_rotation_partners.csv, gw1_19_rotation_schedule_picks.csv.
4. Refresh price-tier top-10s from exact `combined_cost`. Rank Raya partners on `raya_rotation_partners.csv` `total_mod_fdr`. Report `pct_gw_mod_le_2_25` for £4.5 partners; 100% = 19/19.
5. Keep companions in this folder. Scratch only under .tmp/agent/; delete before finish.
```

---

## Method

**Method type**: Empirical combinatorial rotation on Modified FDR.

**Inputs**:
- 20 starting Premier League goalkeepers; live FPL `now_cost` from bootstrap-static.
- 190 first-half matches (GW1–19) from `fixtures.parquet` (FDR ticks identical to live API on 2026-09-04).

**Procedure**:
1. Map each club to its designated starting goalkeeper and live purchase cost.
2. Gameweek Modified FDR for club $i$ in GW $g$:
   $$\text{Mod FDR}_i(g) = \begin{cases} \text{Base FDR} - 0.25 & \text{if Home} \\ \text{Base FDR} + 0.25 & \text{if Away} \end{cases}$$
3. For every unique pair $(A, B)$ (190 pairs), weekly rotated FDR $= \min(\text{Mod FDR}_A(g), \text{Mod FDR}_B(g))$.
4. Sum across GW1–19 for `total_mod_fdr` / `total_base_fdr`. Count weeks with rotated Mod FDR $\le 2.25$ → `n_gw_mod_le_2_25` / `pct_gw_mod_le_2_25`.
5. Rank Raya’s 19 partners by ascending `total_mod_fdr`. Treat £4.5 as live `now_cost == 4.5` (Tzolakis is £4.6 and is excluded from that set).

**Definitions and assumptions**:
- $\le 2.25$ means official FDR 2 away (2.25) or official FDR $\le 2$ home (1.75 or lower). Official FDR 3 home is 2.75 and **fails** this test.
- Chelsea’s GW1–19 Modified FDR sequence is a **club** property. Martínez replacing Sánchez does not change CHE pair totals; it changes the FPL asset name and keeps £5.0m.

### Metric Definitions & Direction

| Metric | Symbol | Definition / Formula | Direction | Ideal / Benchmark | Description |
|---|---|---|---|---|---|
| **Total Modified FDR** | `total_mod_fdr` | $\sum_{g=1}^{19} \min(\text{Mod FDR}_A(g), \text{Mod FDR}_B(g))$ | Lower is better $\downarrow$ | **$\le 44.00$** | Cumulative rotated fixture difficulty with home/away weighting. |
| **Average Modified FDR** | `avg_mod_fdr` | $\frac{\text{total\_mod\_fdr}}{19}$ | Lower is better $\downarrow$ | **$\le 2.30$ / GW** | Mean difficulty of the started goalkeeper each gameweek. |
| **Total Base FDR** | `total_base_fdr` | $\sum_{g=1}^{19} \min(\text{Base FDR}_A(g), \text{Base FDR}_B(g))$ | Lower is better $\downarrow$ | **$\le 46.00$** | Unmodified official FPL FDR sum under weekly best-fixture rotation. |
| **Combined Cost** | `combined_cost` | $\text{Cost}_A + \text{Cost}_B$ | Context-dependent | **£9.0m – £9.5m** | Combined squad budget for both keepers. Live tenths (Tzolakis £4.6). |
| **Easy-week coverage** | `pct_gw_mod_le_2_25` | $100 \times n(\text{rotated Mod FDR} \le 2.25) / 19$ | Higher is better $\uparrow$ | **$100\%$ (19/19)** | Share of GW1–19 where the started keeper faces only FDR 1–2 (away FDR 2 still counts). |

**Validation boundary**: FDR ticks validated live vs parquet (0 mismatches). Starter list uses GW1–2 minutes plus transfer news; not a remaining-horizon minutes model. Coverage threshold is strict; a 2.75 week is a miss.

---

## Source synthesis

### Main claims

- Guardian / BBC (2026-08-30): Martínez joined Chelsea from Aston Villa for £7.5m on a three-year deal and was signed to displace Robert Sánchez.
- FFS (2026-08-30): Chelsea XI vs Brighton listed Martínez; Sánchez dropped from the matchday squad.
- FPL API (2026-09-04): Martínez `club_id=6` (CHE), £5.0m, 90 minutes / 1 start (GW2). Sánchez status `u`, news “Has joined Como on loan for the rest of the season”, £4.9m. Suzuki 90 minutes / 1 start (GW2) after Bizot started GW1. Tzolakis £4.6 (was £4.5 at the 22 Aug snapshot).
- Live fixture `team_h_difficulty` / `team_a_difficulty` match `data/processed/fixtures.parquet` on all 380 rows.

### Source rationale

- Rotate **Chelsea’s** remaining first-half fixtures with Martínez as the CHE shirt, not Sánchez.
- Keep Suzuki as the AVL shirt (signed No. 1; started GW2).
- Price the £4.5 question on live `now_cost == 4.5` (six keepers). Tzolakis is a £4.6 Hull starter, not a £4.5 partner.

---

## Project interpretation

### Decision rules

- **Raya partner (minimize `total_mod_fdr`)**: Donnarumma (MCI, £5.5m) — `raya_rotation_partners.csv` rank 1, `total_mod_fdr` **44.75**.
- **Raya + £4.5**: Kinsky (TOT) — rank 2 overall, `total_mod_fdr` **45.25**, closest £4.5 coverage **10/19** $\le 2.25$.
- **100% weeks $\le 2.25$**: no pair in the 190-set reaches 19/19. Do not pick a £4.5 (or any) pair on that constraint; it is infeasible on this schedule.
- **Martínez vs Sánchez**: CHE pair `total_mod_fdr` values are unchanged. Only the name and Sánchez’s exit from the starter pool change.

### Practical implications

- Holding Raya does not create a green-every-week £4.5 rotation. Best case is 10 easy weeks with Kinsky, or 11 with Donnarumma at £11.5m combined.
- League-wide closest coverage is 12/19 (63.2%), including Martínez + Donnarumma and Petrović + Alisson.

---

## Findings

### 1. Standalone Goalkeeper Baseline (GW1–19)

From [`starting_gkps_gw1_19.csv`](starting_gkps_gw1_19.csv). CHE row is Martínez; club FDR identical to the old Sánchez row.

| Club | Starting GKP | Cost | Home/Away | Base FDR | Mod FDR | Avg Mod FDR |
|:---|:---|:---:|:---:|:---:|:---:|:---:|
| **LIV** | Alisson (`A.Becker`) | £5.5m | 10H / 9A | 55.0 | 54.75 | 2.88 |
| **AVL** | Suzuki | £5.0m | 10H / 9A | 56.0 | 55.75 | 2.93 |
| **MCI** | Donnarumma | £5.5m | 10H / 9A | 56.0 | 55.75 | 2.93 |
| **CHE** | Martinez | £5.0m | 10H / 9A | 57.0 | 56.75 | 2.99 |
| **TOT** | Kinsky | £4.5m | 10H / 9A | 57.0 | 56.75 | 2.99 |
| **NFO** | Sels | £5.0m | 9H / 10A | 57.0 | 57.25 | 3.01 |
| **BOU** | Petrović | £4.5m | 10H / 9A | 58.0 | 57.75 | 3.04 |
| **BRE** | Kelleher | £5.0m | 10H / 9A | 58.0 | 57.75 | 3.04 |
| **COV** | Rushworth | £4.5m | 10H / 9A | 58.0 | 57.75 | 3.04 |
| **NEW** | Horníček | £5.0m | 10H / 9A | 58.0 | 57.75 | 3.04 |
| **ARS** | Raya | £6.0m | 9H / 10A | 58.0 | 58.25 | 3.07 |
| **MUN** | Lammens | £5.0m | 9H / 10A | 58.0 | 58.25 | 3.07 |
| **SUN** | Roefs | £5.0m | 9H / 10A | 58.0 | 58.25 | 3.07 |
| **BHA** | Verbruggen | £4.5m | 9H / 10A | 58.0 | 58.25 | 3.07 |
| **IPS** | Scherpen | £4.5m | 9H / 10A | 59.0 | 59.25 | 3.12 |
| **EVE** | Pickford | £5.5m | 9H / 10A | 59.0 | 59.25 | 3.12 |
| **CRY** | Henderson | £5.0m | 9H / 10A | 59.0 | 59.25 | 3.12 |
| **FUL** | Leno | £4.5m | 9H / 10A | 59.0 | 59.25 | 3.12 |
| **HUL** | Tzolakis | £4.6m | 10H / 9A | 60.0 | 59.75 | 3.15 |
| **LEE** | Trafford | £5.0m | 9H / 10A | 60.0 | 60.25 | 3.17 |

Live price bands among starters: **£4.5m (6)** Petrović, Verbruggen, Rushworth, Leno, Scherpen, Kinsky; **£4.6m (1)** Tzolakis; **£5.0m (9)** Suzuki, Kelleher, Martinez, Henderson, Trafford, Lammens, Horníček, Sels, Roefs; **£5.5m (3)** Pickford, Alisson, Donnarumma; **£6.0m (1)** Raya.

### 2. Best pair with Raya

From [`raya_rotation_partners.csv`](raya_rotation_partners.csv) `total_mod_fdr` (lower $\downarrow$):

| Rank | Partner | Cost | Combined | Total Mod FDR | Avg | $\le 2.25$ | Max week |
|:---:|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **1** | **Donnarumma** (MCI) | £5.5m | £11.5m | **44.75** | 2.36 | 11/19 (57.9%) | 3.75 |
| **2** | **Kinsky** (TOT) | £4.5m | £10.5m | **45.25** | 2.38 | 10/19 (52.6%) | 3.75 |
| **3** | **Petrović** (BOU) | £4.5m | £10.5m | **45.75** | 2.41 | 9/19 (47.4%) | 3.25 |
| 4 | Trafford (LEE) | £5.0m | £11.0m | 46.75 | 2.46 | 9/19 | 3.25 |
| 5 | Suzuki (AVL) | £5.0m | £11.0m | 47.25 | 2.49 | 10/19 | 3.75 |
| 6 | Alisson (LIV) | £5.5m | £11.5m | 47.25 | 2.49 | 10/19 | 3.75 |
| 7 | Rushworth (COV) | £4.5m | £10.5m | 47.25 | 2.49 | 9/19 | 3.75 |
| 8 | **Martinez** (CHE) | £5.0m | £11.0m | 48.25 | 2.54 | 9/19 | 3.75 |

Martínez is a weak Raya complement (rank 8). Same CHE fixtures that previously listed Sánchez.

### 3. Raya + £4.5 and the 100% $\le 2.25$ test

**No pair — Raya+£4.5, any £4.5-inclusive pair, or any of the 190 pairs — reaches 19/19 weeks with rotated Mod FDR $\le 2.25$.** Max coverage in the whole set is **12/19 (63.2%)**.

£4.5 partners with Raya, from `raya_rotation_partners.csv` `partner_cost == 4.5`:

| Rank (all Raya) | Partner | Total Mod FDR | $\le 2.25$ | Closest-to-100% gap | Max week |
|:---:|:---|:---:|:---:|:---:|:---:|
| **2** | **Kinsky** (TOT) | **45.25** | **10/19 (52.6%)** | 9 weeks over | 3.75 |
| 3 | Petrović (BOU) | 45.75 | 9/19 (47.4%) | 10 over | 3.25 |
| 7 | Rushworth (COV) | 47.25 | 9/19 | 10 over | 3.75 |
| 12 | Verbruggen (BHA) | 49.75 | 9/19 | 10 over | 4.25 |
| 17 | Leno (FUL) | 51.25 | 7/19 | 12 over | 4.25 |
| 19 | Scherpen (IPS) | 52.25 | 7/19 | 12 over | 4.25 |

Tzolakis (HUL, **£4.6m**) is not in this set: 8/19 (42.1%), `total_mod_fdr` 48.75.

Closest £4.5 partner on **both** FDR sum and coverage is **Kinsky**. Closest coverage among all pairs that include a £4.5 keeper: Petrović + Alisson and Petrović + Martinez at **12/19** (Petrović + Martinez has a 5.25 spike). Closest coverage overall (any price): Martinez + Donnarumma, Donnarumma + Roefs, Alisson + Donnarumma, Petrović + Alisson, Suzuki + Sels, Petrović + Martinez — all **12/19**.

Kinsky weeks **over** 2.25 with Raya (from [`gw1_19_rotation_schedule_picks.csv`](gw1_19_rotation_schedule_picks.csv)): GW3 3.25, GW4 2.75, GW5 2.75, GW8 2.75, GW9 2.75, GW12 3.25, GW14 3.25, GW16 3.75, GW17 2.75.

### 4. Top Rotation Pairs by Price Bracket

From [`gkp_rotation_pairs_summary.csv`](gkp_rotation_pairs_summary.csv). Brackets use **exact** `combined_cost`. Sánchez rows are now Martínez. Tzolakis £4.6 pairs sit in 9.1 / 9.6 / 10.1 / 10.6 and are omitted from these £x.0 / £x.5 tables.

#### £9.0m Bracket (£4.5m + £4.5m; 15 pairs)

| Rank | Pair | Total Mod FDR | Total Base FDR | Avg Mod FDR | $\le 2.25$ |
|:---:|:---|:---:|:---:|:---:|:---:|
| **1** | **Petrović** (BOU) + **Scherpen** (IPS) | **45.25** | 48.0 | 2.38 | 9/19 |
| **2** | **Verbruggen** (BHA) + **Rushworth** (COV) | **45.25** | 48.0 | 2.38 | 10/19 |
| **3** | **Leno** (FUL) + **Kinsky** (TOT) | **45.75** | 47.0 | 2.41 | 10/19 |
| **4** | **Rushworth** (COV) + **Leno** (FUL) | **46.25** | 49.0 | 2.43 | 9/19 |
| **5** | **Verbruggen** (BHA) + **Kinsky** (TOT) | **46.75** | 49.0 | 2.46 | 10/19 |
| **6** | **Petrović** (BOU) + **Leno** (FUL) | **46.75** | 50.0 | 2.46 | 9/19 |
| **7** | **Petrović** (BOU) + **Rushworth** (COV) | **47.25** | 49.0 | 2.49 | 10/19 |
| **8** | **Petrović** (BOU) + **Verbruggen** (BHA) | **47.75** | 49.0 | 2.51 | 10/19 |
| **9** | **Petrović** (BOU) + **Kinsky** (TOT) | **47.75** | 49.0 | 2.51 | 10/19 |
| **10** | **Rushworth** (COV) + **Kinsky** (TOT) | **47.75** | 49.0 | 2.51 | 10/19 |

#### £9.5m Bracket (£5.0m + £4.5m)

| Rank | Pair | Total Mod FDR | Total Base FDR | Avg Mod FDR | $\le 2.25$ |
|:---:|:---|:---:|:---:|:---:|:---:|
| **1** | **Sels** (NFO) + **Kinsky** (TOT) | **43.75** | 46.0 | 2.30 | 11/19 |
| **2** | **Kinsky** (TOT) + **Roefs** (SUN) | **44.25** | 46.0 | 2.33 | 11/19 |
| **3** | **Petrović** (BOU) + **Roefs** (SUN) | **44.75** | 47.0 | 2.36 | 11/19 |
| **4** | **Rushworth** (COV) + **Sels** (NFO) | **44.75** | 48.0 | 2.36 | 10/19 |
| **5** | **Rushworth** (COV) + **Trafford** (LEE) | **45.25** | 48.0 | 2.38 | 10/19 |
| **6** | **Suzuki** (AVL) + **Rushworth** (COV) | **45.75** | 46.0 | 2.41 | 11/19 |
| **7** | **Suzuki** (AVL) + **Petrović** (BOU) | **45.75** | 47.0 | 2.41 | 11/19 |
| **8** | **Petrović** (BOU) + **Sels** (NFO) | **45.75** | 47.0 | 2.41 | 10/19 |
| **9** | **Martinez** (CHE) + **Scherpen** (IPS) | **45.75** | 47.0 | 2.41 | 11/19 |
| **10** | **Petrović** (BOU) + **Lammens** (MUN) | **45.75** | 48.0 | 2.41 | 9/19 |

#### £10.0m Bracket (£5.0m + £5.0m / £5.5m + £4.5m)

| Rank | Pair | Total Mod FDR | Total Base FDR | Avg Mod FDR | $\le 2.25$ |
|:---:|:---|:---:|:---:|:---:|:---:|
| **1** | **Rushworth** (COV) + **Donnarumma** (MCI) | **43.25** | 46.0 | 2.28 | 11/19 |
| **2** | **Scherpen** (IPS) + **Donnarumma** (MCI) | **44.25** | 47.0 | 2.33 | 10/19 |
| **3** | **Petrović** (BOU) + **Alisson** (LIV) | **44.75** | 46.0 | 2.36 | **12/19** |
| **4** | **Suzuki** (AVL) + **Trafford** (LEE) | **45.25** | 47.0 | 2.38 | 10/19 |
| **5** | **Leno** (FUL) + **Donnarumma** (MCI) | **45.25** | 47.0 | 2.38 | 11/19 |
| **6** | **Rushworth** (COV) + **Pickford** (EVE) | **45.25** | 48.0 | 2.38 | 10/19 |
| **7** | **Martinez** (CHE) + **Sels** (NFO) | **45.75** | 46.0 | 2.41 | 11/19 |
| **8** | **Suzuki** (AVL) + **Sels** (NFO) | **45.75** | 47.0 | 2.41 | **12/19** |
| **9** | **Martinez** (CHE) + **Horníček** (NEW) | **45.75** | 47.0 | 2.41 | 10/19 |
| **10** | **Pickford** (EVE) + **Kinsky** (TOT) | **45.75** | 47.0 | 2.41 | 11/19 |

#### £10.5m Bracket (£5.5m + £5.0m / £6.0m + £4.5m)

| Rank | Pair | Total Mod FDR | Total Base FDR | Avg Mod FDR | $\le 2.25$ |
|:---:|:---|:---:|:---:|:---:|:---:|
| **1** | **Donnarumma** (MCI) + **Lammens** (MUN) | **43.25** | 47.0 | 2.28 | 11/19 |
| **2** | **Martinez** (CHE) + **Donnarumma** (MCI) | **43.75** | 46.0 | 2.30 | **12/19** |
| **3** | **Donnarumma** (MCI) + **Roefs** (SUN) | **43.75** | 46.0 | 2.30 | **12/19** |
| **4** | **Raya** (ARS) + **Kinsky** (TOT) | **45.25** | 48.0 | 2.38 | 10/19 |
| **5** | **Henderson** (CRY) + **Donnarumma** (MCI) | **45.25** | 48.0 | 2.38 | 10/19 |
| **6** | **Trafford** (LEE) + **Donnarumma** (MCI) | **45.25** | 48.0 | 2.38 | 11/19 |
| **7** | **Raya** (ARS) + **Petrović** (BOU) | **45.75** | 48.0 | 2.41 | 9/19 |
| **8** | **Suzuki** (AVL) + **Donnarumma** (MCI) | **45.75** | 48.0 | 2.41 | 10/19 |
| **9** | **Alisson** (LIV) + **Lammens** (MUN) | **45.75** | 48.0 | 2.41 | 11/19 |
| **10** | **Donnarumma** (MCI) + **Horníček** (NEW) | **46.25** | 47.0 | 2.43 | 10/19 |

#### £11.0m Bracket (£5.5m + £5.5m / £6.0m + £5.0m)

| Rank | Pair | Total Mod FDR | Total Base FDR | Avg Mod FDR | $\le 2.25$ |
|:---:|:---|:---:|:---:|:---:|:---:|
| **1** | **Alisson** (LIV) + **Donnarumma** (MCI) | **43.75** | 46.0 | 2.30 | **12/19** |
| **2** | **Pickford** (EVE) + **Alisson** (LIV) | **45.25** | 47.0 | 2.38 | 11/19 |
| **3** | **Pickford** (EVE) + **Donnarumma** (MCI) | **46.25** | 48.0 | 2.43 | 11/19 |
| **4** | **Raya** (ARS) + **Trafford** (LEE) | **46.75** | 48.0 | 2.46 | 9/19 |
| **5** | **Raya** (ARS) + **Suzuki** (AVL) | **47.25** | 49.0 | 2.49 | 10/19 |
| **6** | **Raya** (ARS) + **Martinez** (CHE) | **48.25** | 50.0 | 2.54 | 9/19 |
| **7** | **Raya** (ARS) + **Kelleher** (BRE) | **48.75** | 49.0 | 2.57 | 9/19 |
| **8** | **Raya** (ARS) + **Horníček** (NEW) | **49.25** | 50.0 | 2.59 | 7/19 |
| **9** | **Raya** (ARS) + **Henderson** (CRY) | **49.75** | 50.0 | 2.62 | 8/19 |
| **10** | **Raya** (ARS) + **Roefs** (SUN) | **50.25** | 50.0 | 2.65 | 7/19 |

#### £11.5m Bracket (£6.0m + £5.5m)

| Rank | Pair | Total Mod FDR | Total Base FDR | Avg Mod FDR | $\le 2.25$ |
|:---:|:---|:---:|:---:|:---:|:---:|
| **1** | **Raya** (ARS) + **Donnarumma** (MCI) | **44.75** | 47.0 | 2.36 | 11/19 |
| **2** | **Raya** (ARS) + **Alisson** (LIV) | **47.25** | 48.0 | 2.49 | 10/19 |
| **3** | **Raya** (ARS) + **Pickford** (EVE) | **51.25** | 52.0 | 2.70 | 7/19 |

### 5. Gameweek 1–19 Weekly Picks (Raya pairs + £9.5m leader)

From [`gw1_19_rotation_schedule_picks.csv`](gw1_19_rotation_schedule_picks.csv). Bold = rotated Mod FDR $\le 2.25$.

| GW | Raya + Donnarumma [£11.5m] | Raya + Kinsky [£10.5m] | Sels + Kinsky [£9.5m] |
|:---:|:---|:---|:---|
| **1** | **Raya vs COV (H, 1.75)** | **Raya vs COV (H, 1.75)** | **Sels vs LEE (H, 1.75)** |
| **2** | Donnarumma @ CRY (A, 3.25) | **Kinsky vs NEW (H, 1.75)** | **Kinsky vs NEW (H, 1.75)** |
| **3** | **Donnarumma vs COV (H, 1.75)** | Kinsky @ NFO (A, 3.25) | Sels vs TOT (H, 2.75) |
| **4** | Raya @ SUN (A, 3.25) | Kinsky vs EVE (H, 2.75) | Kinsky vs EVE (H, 2.75) |
| **5** | **Donnarumma vs SUN (H, 1.75)** | Kinsky vs AVL (H, 2.75) | **Sels vs COV (H, 1.75)** |
| **6** | **Raya vs LEE (H, 1.75)** | **Raya vs LEE (H, 1.75)** | Sels @ CRY (A, 3.25) |
| **7** | **Donnarumma vs IPS (H, 1.75)** | **Kinsky vs COV (H, 1.75)** | **Kinsky vs COV (H, 1.75)** |
| **8** | Raya vs EVE (H, 2.75) | Raya vs EVE (H, 2.75) | **Sels @ IPS (A, 2.25)** |
| **9** | **Donnarumma vs BHA (H, 1.75)** | Kinsky vs CRY (H, 2.75) | Kinsky vs CRY (H, 2.75) |
| **10** | **Raya vs HUL (H, 1.75)** | **Raya vs HUL (H, 1.75)** | Kinsky @ LEE (A, 3.25) |
| **11** | **Donnarumma vs FUL (H, 1.75)** | **Kinsky vs IPS (H, 1.75)** | **Kinsky vs IPS (H, 1.75)** |
| **12** | Raya vs MCI (H, 3.75) | Kinsky @ SUN (A, 3.25) | Kinsky @ SUN (A, 3.25) |
| **13** | **Donnarumma vs LEE (H, 1.75)** | **Kinsky vs FUL (H, 1.75)** | **Kinsky vs FUL (H, 1.75)** |
| **14** | Raya @ TOT (A, 3.25) | Raya @ TOT (A, 3.25) | **Sels vs BHA (H, 1.75)** |
| **15** | Raya vs BOU (H, 2.75) | **Kinsky @ HUL (A, 2.25)** | **Kinsky @ HUL (A, 2.25)** |
| **16** | **Donnarumma vs HUL (H, 1.75)** | Raya vs MUN (H, 3.75) | Sels vs EVE (H, 2.75) |
| **17** | Raya @ CRY (A, 3.25) | Kinsky vs BOU (H, 2.75) | Kinsky vs BOU (H, 2.75) |
| **18** | Raya @ FUL (A, 3.25) | **Kinsky vs BHA (H, 1.75)** | **Kinsky vs BHA (H, 1.75)** |
| **19** | **Raya vs IPS (H, 1.75)** | **Raya vs IPS (H, 1.75)** | **Sels vs FUL (H, 1.75)** |

The prior note’s “unbroken GW1–6 home run” for Sels + Kinsky is **not** in this fixture file (GW3 is 2.75, GW6 is Sels away 3.25). Pair still leads the £9.5m `total_mod_fdr` table.

---

## Decision

**Verdict**: Best Raya partner on `total_mod_fdr` is **Donnarumma (MCI, £5.5m)** at **44.75**. Best £4.5 partner is **Kinsky (TOT)** at **45.25** and **10/19** weeks $\le 2.25$. **No** £4.5 pair (and no pair at any price) hits 100% $\le 2.25$; closest in the league is **12/19**. Martínez-to-Chelsea does not change CHE Modified FDR; it replaces Sánchez’s name at £5.0m and is a poor Raya complement (`total_mod_fdr` 48.25).

**Recommended action**:
- Keep Raya + Kinsky if the second keeper must be £4.5; accept nine weeks at 2.75–3.75.
- Spend up to Donnarumma only if the extra £1.0m vs Kinsky is worth 0.50 total Mod FDR and one extra easy week (11/19 vs 10/19).
- Do not hunt a 19/19 green rotation on this GW1–19 grid.

**Trigger / kill switch**:
- Martínez loses the CHE shirt, or Kinsky loses the TOT shirt.
- FPL `now_cost` moves a listed £4.5 starter off 4.5 (already happened to Tzolakis → 4.6).
- Fixture postponements in GW1–19.

---

## Risks and unknowns

1. **Shirt risk**: Martínez has one Premier League start (GW2). Suzuki started only GW2 after Bizot’s GW1. Horníček has both Newcastle starts; Pope is unused.
2. **Threshold strictness**: $\le 2.25$ ignores FDR 3 home (2.75). Relaxing to $\le 2.75$ still yields no 19/19 pair (max 17/19, Donnarumma + Lammens). Not a recommendation to change the user’s threshold.
3. **Price tenths**: Tzolakis £4.6 drops him out of exact £9.0m 4.5+4.5 pairs (15 pairs remain, not 21).
4. **Blanks/doubles**: Any GW1–19 postponement invalidates weekly mins.

## Refresh checklist

- [x] `Updated` uses ISO 8601 timestamp with timezone.
- [x] `Data stamp` identifies current evidence cutoff.
- [x] `Season` and scope remain accurate.
- [x] Source URLs, publication dates, and access dates checked.
- [x] Source synthesis and Project interpretation remain separate.
- [x] Unvalidated claims labeled (remaining-horizon shirts).
- [x] Agent Prompt remains runnable and points to stable slug.
- [x] Scratch files removed from `.tmp/agent/`.
