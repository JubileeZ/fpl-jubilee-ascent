# GW1–6 Preseason Research & Optimization Pipeline (Consolidated Suite)

**Updated**: 2026-08-10T06:45:00+07:00  
**Data stamp**: Dual-source role scrape 2026-08-10; Stage 2 dual-floor rates 2026-08-10; FFS + Meerkat accessed 2026-08-10; API pricing 2026-07-29  
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

Shared overlay module: [`availability_priors.py`](availability_priors.py) — Watch $p_{\text{start}}\times0.70$ on GW1–5; `exclude_gw1-5` zeros GW1–5 only.

---

## Agent Prompt

```text
Run parameterized GW1-6 Preseason Pipeline (End-to-End):

1. Stage 1: uv run python docs/research/gw1-6-preseason-pipeline/01-expected-role-gw1-5/refresh_expected_role.py
   - HTTP scrape FFS Team News + FPL Meerkat; inject missing FFS XI players; conflict rules; API + official availability.
2. Stage 2: build_expected_stats.py then project_expected_points.py (availability_priors applied).
3. Stage 3: run_wc4_simulation.py — 16-scenario matrix; WC4 Opt1 only; user_picks + FT banking; summary CSVs.
4. Master: uv run python docs/research/gw1-6-preseason-pipeline/run_pipeline.py
5. Gates: uv run ruff check ., uv run pytest, bash tests/verify.sh
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
| S1 | GW1 | FH3 | allow | allow | 174.83 | 152.43 | **327.26** | 4 |
| S2 | GW1 | FH3 | allow | ban | 174.83 | 152.43 | 327.26 | 4 |
| S3 | GW1 | FH3 | ban | allow | 174.83 | 152.43 | 327.26 | 4 |
| S4 | GW1 | FH3 | ban | ban | 174.83 | 152.43 | 327.26 | 4 |
| S5 | GW1 | TC3 | allow | allow | 183.61 | 152.43 | **336.04** | 4 |
| S6 | GW1 | TC3 | allow | ban | 183.61 | 152.43 | 336.04 | 4 |
| S7 | GW1 | TC3 | ban | allow | 178.87 | 152.43 | 331.30 | 4 |
| S8 | GW1 | TC3 | ban | ban | 178.87 | 152.43 | 331.30 | 4 |
| S9 | GW2 | FH3 | allow | allow | 174.00 | 152.43 | 326.43 | 4 |
| S10 | GW2 | FH3 | allow | ban | 174.00 | 152.43 | 326.43 | 4 |
| S11 | GW2 | FH3 | ban | allow | 173.39 | 152.43 | 325.82 | 4 |
| S12 | GW2 | FH3 | ban | ban | 173.39 | 152.43 | 325.82 | 4 |
| S13 | GW2 | TC3 | allow | allow | 182.87 | 152.43 | 335.30 | 4 |
| S14 | GW2 | TC3 | allow | ban | 182.87 | 152.43 | 335.30 | 4 |
| S15 | GW2 | TC3 | ban | allow | 178.52 | 152.43 | 330.95 | 4 |
| S16 | GW2 | TC3 | ban | ban | 178.52 | 152.43 | 330.95 | 4 |

**Decision rule**: report top FH3 and top TC3 separately (different chip spends).  
**Top FH3**: S1 — 327.26 xP. **Top TC3**: S5 — 336.04 xP (TC on Haaland GW3).

---

## Verification & Delivery

- Master runner verified via `uv run python docs/research/gw1-6-preseason-pipeline/run_pipeline.py`.
- Availability unit tests: `tests/test_availability_priors.py`.
