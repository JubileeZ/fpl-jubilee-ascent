# GW1–6 Preseason Research & Optimization Pipeline (Consolidated Suite)

**Updated**: 2026-08-13T03:35:00+07:00  
**Data stamp**: Dual-source role scrape 2026-08-13; Stage 2 dual-floor rates 2026-08-13; FFS + Meerkat accessed 2026-08-13; API pricing 2026-07-29  
**Season**: 2026/27 · horizon GW1–6  
**Status**: Active Master Pipeline  
**Purpose**: End-to-end preseason research — dual-source Expected Role rebuild (Stage 1), dual-floor Event Rates + $xP$ (Stage 2), and 16-scenario chip exploration with WC4 Opt1 (Stage 3).  
**Scope**: 20-club XI Contention role audit; availability-aware Participation State scoring; exploration matrix (BB1|BB2) × WC4 Opt1 × (FH3|TC3) × (Allow|Ban Haaland pre) × (Allow|Ban B.Fernandes pre).  
**Pipeline Runner**: [`run_pipeline.py`](run_pipeline.py)

---

## Pipeline Lineage & Data Contracts

```
┌─────────────────────────────────────────────────────────┐
│ FFS Team News + FPL Meerkat + transfers + API overlays  │
└────────────────────────────┬────────────────────────────┘
                             │  refresh_expected_role.py (HTTP scrape)
                             ▼
┌─────────────────────────────────────────────────────────┐
│ Stage 1: 01-expected-role-gw1-5/                        │
│ └── expected-role-gw1-5.csv (XI Contention + injects)   │
└────────────────────────────┬────────────────────────────┘
                             │  build_expected_stats.py & project_expected_points.py
                             ▼
┌─────────────────────────────────────────────────────────┐
│ Stage 2: 02-expected-stats-gw1-5/                        │
│ ├── expected-stats-gw1-5.csv                            │
│ └── gw1-5_projections.csv                               │
└────────────────────────────┬────────────────────────────┘
                             │  generate_gw1_6_projections() + run_wc4_simulation.py
                             ▼
┌─────────────────────────────────────────────────────────┐
│ Stage 3: 03-gw1-6-chip-wc4-squads/                      │
│ ├── gw1-6_projections.csv                               │
│ ├── gw1-6_wc4_summary.csv (16 scenarios)                │
│ ├── gw1-6_wc4_simulation.csv                            │
│ └── gw1-6_user_squad_comparison.csv                     │
└─────────────────────────────────────────────────────────┘
```

Standalone (not a pipeline stage): [Ownership Value Explorer (GW1–38)](../ownership-value-explorer/ownership-value-explorer.md) — consumes Stage 2 rates.

Shared overlay module: [`availability_priors.py`](availability_priors.py) — Watch $p_{\text{start}}\times0.70$ on GW1–5; `exclude_gw1-5` zeros GW1–5 only.

---

## Agent Prompt & Master Reproducibility Instructions

```text
Run parameterized GW1-6 Preseason Pipeline (End-to-End Execution):

1. Execute Master Pipeline Runner:
   uv run python docs/research/gw1-6-preseason-pipeline/run_pipeline.py

   Under the hood, this executes the complete 3-stage sequence:
   - Stage 1: docs/research/gw1-6-preseason-pipeline/01-expected-role-gw1-5/refresh_expected_role.py
     * HTTP scrape FFS Team News (https://www.fantasyfootballscout.co.uk/team-news) and FPL Meerkat (https://fpl.page/article/fpl-gw1-predicted-lineups-2627).
     * Injects missing starters from data/processed/players.parquet.
     * Applies conflict rules and official club availability overlays.
     * Writes data/research/gw1-6-preseason-pipeline/01-expected-role-gw1-5/expected-role-gw1-5.csv.
   - Stage 2: docs/research/gw1-6-preseason-pipeline/02-expected-stats-gw1-5/build_expected_stats.py & project_expected_points.py
     * Builds dual-floor usable-season event rates (any >=450m, latest >=900m) + Defcon fill.
     * Evaluates ParticipationStateHybridModel across horizon 5 with Softmax bonus over 357 XI Contention.
     * Enforces Zero Draft on fallback_baseline invariant via external research packages.
     * Writes expected-stats-gw1-5.csv and gw1-5_projections.csv.
   - Stage 3: docs/research/gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/run_wc4_simulation.py
     * Generates 6-GW projections and solves 16-scenario optimization matrix with FT banking (4 banked FTs into GW6).
     * Compares user squad and writes gw1-6_wc4_summary.csv, gw1-6_wc4_simulation.csv, gw1-6_user_squad_comparison.csv.

2. Run Delivery & Linting Gates:
   uv run ruff check .
   uv run pytest
   bash tests/verify.sh
```

---

## Sub-Stage Directories

1. [**01-expected-role-gw1-5**](01-expected-role-gw1-5/expected-role-gw1-5.md)
2. [**02-expected-stats-gw1-5**](02-expected-stats-gw1-5/expected-stats-gw1-5.md)
3. [**03-gw1-6-chip-wc4-squads**](03-gw1-6-chip-wc4-squads/gw1-6-chip-wc4-squads.md)

---

## Master Scenario Summary (Stage 3 — 16 exploration paths)

| ID | BB | Mid chip | Ban H | Ban Bruno | GW1–3 xP | GW4–6 xP | Total | Banked FTs GW6 |
| :--- | :---: | :---: | :---: | :---: | ---: | ---: | ---: | :---: |
| S1 | GW1 | FH3 | allow | allow | 176.16 | 152.06 | **328.22** | 4 |
| S2 | GW1 | FH3 | allow | ban | 174.53 | 152.06 | 326.59 | 4 |
| S3 | GW1 | FH3 | ban | allow | 176.16 | 152.06 | **328.22** | 4 |
| S4 | GW1 | FH3 | ban | ban | 174.53 | 152.06 | 326.59 | 4 |
| S5 | GW1 | TC3 | allow | allow | 182.95 | 152.06 | **335.01** | 4 |
| S6 | GW1 | TC3 | allow | ban | 182.77 | 152.06 | 334.83 | 4 |
| S7 | GW1 | TC3 | ban | allow | 180.52 | 152.06 | 332.58 | 4 |
| S8 | GW1 | TC3 | ban | ban | 178.28 | 152.06 | 330.34 | 4 |
| S9 | GW2 | FH3 | allow | allow | 175.88 | 152.06 | 327.94 | 4 |
| S10 | GW2 | FH3 | allow | ban | 173.75 | 152.06 | 325.81 | 4 |
| S11 | GW2 | FH3 | ban | allow | 175.88 | 152.06 | 327.94 | 4 |
| S12 | GW2 | FH3 | ban | ban | 173.25 | 152.06 | 325.31 | 4 |
| S13 | GW2 | TC3 | allow | allow | 182.45 | 152.06 | 334.51 | 4 |
| S14 | GW2 | TC3 | allow | ban | 182.22 | 152.06 | 334.28 | 4 |
| S15 | GW2 | TC3 | ban | allow | 180.82 | 152.06 | 332.88 | 4 |
| S16 | GW2 | TC3 | ban | ban | 177.97 | 152.06 | 330.03 | 4 |

**Decision rule**: report top FH3 and top TC3 separately (different chip spends).  
**Top FH3**: S1 — **328.22** xP. **Top TC3**: S5 — **335.01** xP (TC on Haaland GW3). Bruno ban binding (~1.6 xP FH3).

---

## Verification & Delivery

- Master runner verified via `uv run python docs/research/gw1-6-preseason-pipeline/run_pipeline.py`.
- Availability unit tests: `tests/test_availability_priors.py`.
- Dual-floor blend unit tests: `tests/test_expected_stats_blend.py`.
