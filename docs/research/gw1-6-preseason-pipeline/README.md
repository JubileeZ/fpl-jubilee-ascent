# GW1–6 Preseason Research & Optimization Pipeline (Consolidated Suite)

**Updated**: 2026-08-19T22:22:53+07:00
**Data stamp**: Stage 2 rates 2026-08-18; public FPL bootstrap/fixtures 2026-08-19 (592 players); Champion saves/defcon × defence_multiplier  
**Season**: 2026/27 · horizon GW1–6  
**Status**: Active Master Pipeline  
**Purpose**: End-to-end preseason research — Expected Role rebuild (Stage 1), Prior-Season Seed + Career Individual Rate Event Rates + $xP$ (Stage 2), and canonical GW1 BB + WC4 optimization (Stage 3).  
**Scope**: 20-club role audit (575 contention rows; 234 Draft-eligible); availability-aware Participation State scoring; GW1 Bench Boost + locked GW1-3 + GW4 Wildcard rebuild + 4 banked FTs into GW6.  
**Strategy Core**: **GW1 BB + WC4 Canonical (383.76 xP)**. 15 fit starters score in GW1 Bench Boost (79.24 xP), locked transfers across GW1-3 (201.65 xP), Wildcard rebuild in GW4 (182.11 GW4-6 xP), and 4 banked Free Transfers preserved into GW6 post-international break.
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
│ ├── gw1-6_wc4_summary.csv                               │
│ ├── gw1-6_wc4_simulation.csv                            │
│ ├── gw1-6_select_11.csv                                 │
│ └── gw1-6_user_squad_comparison.csv                     │
└──────────────┬──────────────────────────┬───────────────┘
               │                          │
               ▼                          ▼
┌──────────────────────────┐   ┌────────────────────────────┐
│ Unified DCS rotation     │   │ Ownership Value Explorer   │
│ (standalone topic)       │   │ (standalone; needs Stage 3)│
└──────────────────────────┘   └────────────────────────────┘
```

Standalone (not pipeline stages): [Ownership Value Explorer (GW1–38)](../ownership-value-explorer/ownership-value-explorer.md) · [Unified defensive rotation](../defensive-fixture-rotation/defensive-fixture-rotation.md) — consume Stage 2 rates. Archived GKP/DEF notes: `docs/archive/`.

Shared overlay module: [`availability_priors.py`](availability_priors.py) — Watch $p_{\text{start}}\times0.70$ on GW1–5; `exclude_gw1-5` zeros GW1–5 only.

---

## Strategy Hierarchy & Key Mechanisms

```
Canonical Preseason Strategy Trajectory (GW1 BB + WC4):
┌───────────────────────────────────────────────────────────────────────────────┐
│ GW1: Bench Boost (BB1 79.24 xP; 15 fit starters score, £100.0m spend)         │
│ └─ Captures 15 fit starters with zero bench capital penalty pre-Wildcard      │
├───────────────────────────────────────────────────────────────────────────────┤
│ GW2–3: Locked Pre-WC Squad (61.76 xP in GW2; 60.65 xP in GW3; 0 transfers)    │
│ └─ 201.65 xP Pre-Wildcard sprint; Haaland captain in GW3                         │
├───────────────────────────────────────────────────────────────────────────────┤
│ GW4: Wildcard Rebuild (£98.5m spend, 59.69 xP in GW4)                        │
│ └─ Seed xP rebuild; keepers from `gw1-6_wc4_simulation.csv`                   │
├───────────────────────────────────────────────────────────────────────────────┤
│ GW5: Free Transfer Rolled (gw5_transfers=0; 59.64 xP)                         │
│ └─ Banked FTs preserved through Wildcard under 2026/27 rules                  │
├───────────────────────────────────────────────────────────────────────────────┤
│ GW6: Enter Post-International Break with 4 Banked Free Transfers (62.78 xP)  │
│ └─ 383.76 Total 6-GW xP (`gw1-6_wc4_summary.csv` `total_6gw_xp`)                 │
├───────────────────────────────────────────────────────────────────────────────┤
│ GW7–19: Hold Free Hit & Triple Captain as Emergency / Double GW Reserves      │
└───────────────────────────────────────────────────────────────────────────────┘
```

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
   Then `uv run python docs/research/sync_live_research_figures.py` (CSV cells → note caches).

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

## Master Scenario Summary (Stage 3 Canonical Simulation)

| Scenario ID | Strategy Description | BB Chip | WC Chip | GW1–3 xP | GW4–6 xP | Total 6-GW xP | Pre Spend | Post Spend | ITB GW6 | Banked FTs GW6 |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **S1** | **GW1 BB + WC4 Canonical (Locked GW1-3, Roll GW5)** | **GW1** | **GW4** | **201.65** | **182.11** | **383.76** | £100.0m | £98.5m | £1.5m | **4** |

### Strategic Verdict & Key Decisions

1. **Canonical Strategy Implementation**: **S1 (GW1 BB + WC4 Canonical, 383.76 xP)**. Deploys Bench Boost in GW1 (all 15 players score, 79.24 xP with Haaland captain), locks transfers across GW1–3 sprint (201.65 xP), executes complete Wildcard rebuild in GW4 (182.11 xP across GW4–6), rolls the GW5 free transfer, and enters GW6 post-international break with **4 banked Free Transfers**.
2. **Lineup Certainty & Zero Bench Penalty**: Deploying BB in GW1 completely eliminates bench headache and lineup regret for the season opener, converting bench capital directly into scoring output.
3. **Strategic Agility**: Preserving 4 banked Free Transfers into GW6 provides maximum flexibility to respond to early-season form, injuries, and price swings post-international break.

---

## Verification & Delivery

- Role scrape: `uv run python docs/research/gw1-6-preseason-pipeline/run_pipeline.py`.
- Rates / new player: `uv run python docs/research/gw1-6-preseason-pipeline/refresh_downstream.py`.
- Availability unit tests: `tests/test_availability_priors.py`.
- ADR-0014 rate tests: `tests/test_expected_stats_blend.py`.
