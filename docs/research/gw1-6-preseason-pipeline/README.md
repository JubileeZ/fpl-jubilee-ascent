# GW1–6 Preseason Research & Optimization Pipeline (Consolidated Suite)

**Updated**: 2026-08-14T01:30:00+07:00  
**Data stamp**: Dual-source role scrape 2026-08-13; Stage 2 Prior-Season Seed + Career Individual Rate (ADR-0014); downstream refresh 2026-08-14; FFS + Meerkat accessed 2026-08-13; API pricing 2026-07-29  
**Season**: 2026/27 · horizon GW1–6  
**Status**: Active Master Pipeline  
**Purpose**: End-to-end preseason research — dual-source Expected Role rebuild (Stage 1), Prior-Season Seed + Career Individual Rate Event Rates + $xP$ (Stage 2), and 16-scenario chip exploration with WC4 Opt1 (Stage 3).  
**Scope**: 20-club XI Contention role audit; availability-aware Participation State scoring; exploration matrix (BB1|BB2) × WC4 Opt1 × (FH3|TC3) × (Allow|Ban Haaland pre) × (Allow|Ban B.Fernandes pre).  
**Pipeline Runner**: [`run_pipeline.py`](run_pipeline.py) (includes Stage 1 HTTP scrape)  
**Downstream refresh**: [`refresh_downstream.py`](refresh_downstream.py) (skip scrape; rates → Stage 3 / GKP / DEF / ownership)

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
                             │  CAREER_INDIVIDUAL_RATES if new Draft, no seed
                             │  build_expected_stats.py & project_expected_points.py
                             ▼
┌─────────────────────────────────────────────────────────┐
│ Stage 2: 02-expected-stats-gw1-5/                        │
│ ├── expected-stats-gw1-5.csv                            │
│ └── gw1-5_projections.csv                               │
└────────────────────────────┬────────────────────────────┘
                             │  refresh_downstream.py (or Stage 3 only)
                             ▼
┌─────────────────────────────────────────────────────────┐
│ Stage 3: 03-gw1-6-chip-wc4-squads/                      │
│ ├── gw1-6_projections.csv                               │
│ ├── gw1-6_wc4_summary.csv (16 scenarios)                │
│ ├── gw1-6_wc4_simulation.csv                            │
│ └── gw1-6_user_squad_comparison.csv                     │
└──────────────┬──────────────────────────┬───────────────┘
               │                          │
               ▼                          ▼
┌──────────────────────────┐   ┌────────────────────────────┐
│ GKP / DEF rotation notes │   │ Ownership Value Explorer   │
│ (standalone topics)      │   │ (standalone; needs Stage 3)│
└──────────────────────────┘   └────────────────────────────┘
```

Standalone (not pipeline stages): [Ownership Value Explorer (GW1–38)](../ownership-value-explorer/ownership-value-explorer.md) · [GKP rotation](../gkp-fixture-rotation/gkp-fixture-rotation.md) · [DEF rotation](../def-fixture-rotation/def-fixture-rotation.md) — all consume Stage 2 rates.

Shared overlay module: [`availability_priors.py`](availability_priors.py) — Watch $p_{\text{start}}\times0.70$ on GW1–5; `exclude_gw1-5` zeros GW1–5 only.

---

## Which runner

| Situation | Command |
| --- | --- |
| Roles changed (FFS/Meerkat XI, new starter inject) | `uv run python docs/research/gw1-6-preseason-pipeline/run_pipeline.py` (HTTP). Then add a career package if Stage 2 fail-closes. |
| Rates / career packages changed; roles unchanged | `uv run python docs/research/gw1-6-preseason-pipeline/refresh_downstream.py` |
| Single topic only | That topic's Agent Prompt command |

`run_pipeline.py` does **not** fold GKP/DEF combinatorics (slow). `refresh_downstream.py` does.

---

## New Draft player (the update path)

When Stage 1 injects a Nailed/Regular with **no Prior-Season Seed** (foreign signing, promoted, rookie):

1. Look up last completed senior **league** season xG/xA/Defcon/saves (omit GC).
2. Add `{player_id: {xg, xa, saves, defcon, defcon_cbit, minutes?, note}}` to `CAREER_INDIVIDUAL_RATES` in [`02-expected-stats-gw1-5/build_expected_stats.py`](02-expected-stats-gw1-5/build_expected_stats.py).
3. Run `refresh_downstream.py` (or `run_pipeline.py` if roles also changed).
4. Stage 2 **fail-closes** if any Nailed/Regular still sits on `fallback_baseline`. Rotation/Cameo fallback is allowed.

Club-changers who already have a 2025/26 PL seed keep that seed (including player GC). Do not add them here.

---

## Agent Prompt & Master Reproducibility Instructions

```text
GW1-6 Preseason Pipeline — pick the runner:

A. Roles changed (HTTP scrape):
   uv run python docs/research/gw1-6-preseason-pipeline/run_pipeline.py
   If Stage 2 exits on Draft fallback, add CAREER_INDIVIDUAL_RATES then re-run
   refresh_downstream.py (skip a second scrape).

B. Rates / new-player packages only (no scrape):
   uv run python docs/research/gw1-6-preseason-pipeline/refresh_downstream.py
   Order: Stage 2 → Stage 3 → GKP rotation → DEF rotation (incl. WC4 bridges)
   → ownership explorer.
   Then update Findings tables in Stage 3 / GKP / DEF / ownership notes from CSVs.

Stage 2 rules (ADR-0014): Prior-Season Seed 2025/26 >=450m; else Career Individual
Rate + Destination Team Concede Rate. Zero Draft on fallback_baseline.

Delivery: uv run ruff check . && uv run pytest && bash tests/verify.sh
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
| S1 | GW1 | FH3 | allow | allow | 176.79 | 155.37 | 332.16 | 4 |
| S2 | GW1 | FH3 | allow | ban | 174.77 | 155.37 | 330.14 | 4 |
| S3 | GW1 | FH3 | ban | allow | 176.79 | 155.37 | 332.16 | 4 |
| S4 | GW1 | FH3 | ban | ban | 173.96 | 155.37 | 329.33 | 4 |
| S5 | GW1 | TC3 | allow | allow | 183.51 | 155.37 | 338.88 | 4 |
| S6 | GW1 | TC3 | allow | ban | 183.38 | 155.37 | 338.75 | 4 |
| S7 | GW1 | TC3 | ban | allow | 183.38 | 155.37 | 338.75 | 4 |
| S8 | GW1 | TC3 | ban | ban | 180.55 | 155.37 | 335.92 | 4 |
| S9 | GW2 | FH3 | allow | allow | 176.97 | 155.37 | **332.34** | 4 |
| S10 | GW2 | FH3 | allow | ban | 175.27 | 155.37 | 330.64 | 4 |
| S11 | GW2 | FH3 | ban | allow | 176.97 | 155.37 | **332.34** | 4 |
| S12 | GW2 | FH3 | ban | ban | 173.93 | 155.37 | 329.30 | 4 |
| S13 | GW2 | TC3 | allow | allow | 184.77 | 155.37 | **340.14** | 4 |
| S14 | GW2 | TC3 | allow | ban | 183.71 | 155.37 | 339.08 | 4 |
| S15 | GW2 | TC3 | ban | allow | 184.06 | 155.37 | 339.43 | 4 |
| S16 | GW2 | TC3 | ban | ban | 180.33 | 155.37 | 335.70 | 4 |

**Decision rule**: report top FH3 and top TC3 separately (different chip spends).  
**Top FH3**: S9 — **332.34** xP. **Top TC3**: S13 — **340.14** xP (TC on Haaland GW3). Bruno ban binding. Haaland ban non-binding on FH3 allow-Bruno paths (S1=S3, S9=S11).

---

## Verification & Delivery

- Role scrape: `uv run python docs/research/gw1-6-preseason-pipeline/run_pipeline.py`.
- Rates / new player: `uv run python docs/research/gw1-6-preseason-pipeline/refresh_downstream.py`.
- Availability unit tests: `tests/test_availability_priors.py`.
- ADR-0014 rate tests: `tests/test_expected_stats_blend.py`.
