# GW1–6 Preseason Research & Optimization Pipeline (Consolidated Suite)

**Updated**: 2026-08-09T18:15:00+07:00  
**Data stamp**: Projections CSV 2026-08-09; Expected Role Table 2026-08-09; FFS transfers through 2026-08-08; API player pricing 2026-07-29  
**Season**: 2026/27 · horizon GW1–6  
**Status**: Active Master Pipeline  
**Purpose**: Consolidate the 3-stage preseason research pipeline — transforming raw source evidence & transfer registers into player expected roles (Stage 1), generating empirical expected stats & points projections (Stage 2), and solving full 6-Gameweek chip & Wildcard squad optimizations (Stage 3).  
**Scope**: End-to-end 20-club player role audit, feature event-rate calculation, $xP$ points projection, and 3x2 matrix MILP squad optimization across GW1–6.  
**Pipeline Runner**: [`run_pipeline.py`](run_pipeline.py) — executes Stage 1 ➔ Stage 2 ➔ Stage 3 end-to-end.

---

## Pipeline Lineage & Data Contracts

```
┌─────────────────────────────────────────────────────────┐
│ External Sources & Transfers Register                   │
│ (FFS Team News, FPL Meerkat, Transfers, Official News)  │
└────────────────────────────┬────────────────────────────┘
                             │  ingested by refresh_expected_role.py
                             ▼
┌─────────────────────────────────────────────────────────┐
│ Stage 1: 01-expected-role-gw1-5/                        │
│ └── expected-role-gw1-5.csv (340 XI Contention Rows)    │
└────────────────────────────┬────────────────────────────┘
                             │  ingested by build_expected_stats.py & project_expected_points.py
                             ▼
┌─────────────────────────────────────────────────────────┐
│ Stage 2: 02-expected-stats-gw1-5/                        │
│ ├── expected-stats-gw1-5.csv                            │
│ └── gw1-5_projections.csv / gw1-6_projections.csv       │
└────────────────────────────┬────────────────────────────┘
                             │  ingested by run_wc4_simulation.py
                             ▼
┌─────────────────────────────────────────────────────────┐
│ Stage 3: 03-gw1-6-chip-wc4-squads/                      │
│ └── gw1-6_wc4_simulation.csv (3x2 Matrix Optimization) │
└─────────────────────────────────────────────────────────┘
```

---

## Agent Prompt (Parameterized for Reproducible End-to-End Pipeline Redo)

```text
Run parameterized GW1-6 Preseason Pipeline (End-to-End Execution):

1. Execute Stage 1 (Player Role & Availability Refresh):
   - Command: uv run python docs/research/gw1-6-preseason-pipeline/01-expected-role-gw1-5/refresh_expected_role.py
   - Input: Scraped line-up predictions (FFS Team News, FPL Meerkat), summer transfer register (fpl-summer-transfers.md), official club fitness updates.
   - Output: data/research/gw1-6-preseason-pipeline/01-expected-role-gw1-5/expected-role-gw1-5.csv (340 rows).

2. Execute Stage 2 (Expected Stats & Points Projections):
   - Script 2A: build_expected_stats.py -> outputs expected-stats-gw1-5.csv.
   - Script 2B: project_expected_points.py -> scores ParticipationStateHybridModel across 20 clubs.
   - Output: data/research/gw1-6-preseason-pipeline/02-expected-stats-gw1-5/gw1-5_projections.csv.

3. Execute Stage 3 (GW1-6 Chip & WC4 Wildcard Squad Optimization):
   - Command: run_wc4_simulation.py -> solves 3x2 matrix (Pre-WC BB1 vs BB2; Post-WC Opt1 Unconstrained, Opt2 Cheap DEF <= £32m, Opt3 Cheap DEF + LIV 2+).
   - Output: data/research/gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/gw1-6_wc4_simulation.csv.

4. Run Master Pipeline Script:
   - Command: uv run python docs/research/gw1-6-preseason-pipeline/run_pipeline.py
   - Verifies all 3 stages run sequentially and syncs CSV artifacts across pipeline directories.

5. Verify Pre-Commit Delivery Gates:
   - Run: uv run ruff check ., uv run pytest, bash tests/verify.sh before completion.
```

---

## Sub-Stage Directories

1. [**01-expected-role-gw1-5**](01-expected-role-gw1-5/expected-role-gw1-5.md): 20-Club Expected Role Audit & Draft Availability priors.
2. [**02-expected-stats-gw1-5**](02-expected-stats-gw1-5/expected-stats-gw1-5.md): Player Event Rates & $xP$ projections.
3. [**03-gw1-6-chip-wc4-squads**](03-gw1-6-chip-wc4-squads/gw1-6-chip-wc4-squads.md): Strategic GW1–6 chip & GW4 Wildcard squad optimization.

---

## Master Scenario Summary Table (Stage 3 Optimization Output)

| Scenario ID | Pre-WC Chip | FH Chip | Post-WC Option | GW1–3 XI xP | GW4–6 XI xP | Total 6-GW xP | Pre Spend | Post Spend | GW6 ITB | Banked FTs (GW6) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **S1** | GW1 BB1 | — | Opt1 (Unconstrained) | **167.96 $xP$** | **151.85 $xP$** | **319.81 $xP$** | £100.0m | £100.0m | £0.0m | **2 FTs** |
| **S2** | GW1 BB1 | — | Opt2 (Cheap DEF $\le$32m) | **167.96 $xP$** | 147.05 $xP$ | **315.01 $xP$** | £100.0m | £100.0m | £0.0m | **2 FTs** |
| **S3** | GW1 BB1 | — | Opt3 (Cheap DEF $\le$32m + LIV 2+) | **167.96 $xP$** | 146.56 $xP$ | **314.52 $xP$** | £100.0m | £97.0m | **£3.0m** | **2 FTs** |
| **S4** | GW2 BB2 | — | Opt1 (Unconstrained) | 167.30 $xP$ | **151.85 $xP$** | **319.15 $xP$** | £100.0m | £100.0m | £0.0m | **2 FTs** |
| **S5** | GW2 BB2 | — | Opt2 (Cheap DEF $\le$32m) | 167.30 $xP$ | 147.05 $xP$ | **314.35 $xP$** | £100.0m | £100.0m | £0.0m | **2 FTs** |
| **S6** | GW2 BB2 | — | Opt3 (Cheap DEF $\le$32m + LIV 2+) | 167.30 $xP$ | 146.56 $xP$ | **313.86 $xP$** | £100.0m | £97.0m | **£3.0m** | **2 FTs** |
| **S7** | GW1 BB1 | **GW3 FH** | Opt1 (Unconstrained) | **174.11 $xP$** | **151.85 $xP$** | **325.96 $xP$** | £100.0m | £100.0m | £0.0m | **2 FTs** |
| **S8** | GW1 BB1 | **GW3 FH** | Opt2 (Cheap DEF $\le$32m) | **174.11 $xP$** | 147.05 $xP$ | **321.16 $xP$** | £100.0m | £100.0m | £0.0m | **2 FTs** |
| **S9** | GW1 BB1 | **GW3 FH** | Opt3 (Cheap DEF $\le$32m + LIV 2+) | **174.11 $xP$** | 146.56 $xP$ | **320.67 $xP$** | £100.0m | £97.0m | **£3.0m** | **2 FTs** |
| **S10** | GW2 BB2 | **GW3 FH** | Opt3 (Cheap DEF $\le$32m + LIV 2+) | 173.36 $xP$ | 146.56 $xP$ | **319.92 $xP$** | £100.0m | £97.0m | **£3.0m** | **2 FTs** |
| **S11** | None (Std) | **GW3 FH** | Opt3 (Cheap DEF $\le$32m + LIV 2+) | 157.93 $xP$ | 146.56 $xP$ | **304.49 $xP$** | £100.0m | £97.0m | **£3.0m** | **2 FTs** |

---

## Verification & Delivery

- Master runner verified via `uv run python docs/research/gw1-6-preseason-pipeline/run_pipeline.py`.
- Delivery checks (`uv run ruff check .`, `uv run pytest`, `bash tests/verify.sh`) passed cleanly.
