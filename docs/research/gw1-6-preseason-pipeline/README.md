# GW1–6 Preseason Research & Optimization Pipeline (Consolidated Suite)

**Updated**: 2026-08-15T13:40:00+07:00  
**Data stamp**: Dual-source role scrape 2026-08-13; Stage 2 Prior-Season Seed + Career Individual Rate (ADR-0014); downstream refresh 2026-08-15; World Cup 2026 fitness audit; FFS + Meerkat accessed 2026-08-13; API pricing 2026-07-29  
**Season**: 2026/27 · horizon GW1–6  
**Status**: Active Master Pipeline  
**Purpose**: End-to-end preseason research — dual-source Expected Role rebuild (Stage 1), Prior-Season Seed + Career Individual Rate Event Rates + $xP$ (Stage 2), and 16-scenario chip exploration with WC4 Opt1 (Stage 3).  
**Scope**: 20-club XI Contention role audit; availability-aware Participation State scoring; exploration matrix (BB1|BB2) × WC4 Opt1 × (FH3|TC3) × (Allow|Ban Haaland pre) × (Allow|Ban B.Fernandes pre).  
**Strategy Core**: **S13 (BB2 + TC3 Haaland + WC4 Opt1, 340.14 xP)** canonical #1 Max EV Target; **S5 (BB1 + TC3 Haaland + WC4 Opt1, 338.88 xP)** canonical #2 Safe Start; **S15 (Ban Haaland Balanced, 339.43 xP)** proves high mathematical flexibility (-0.71 xP). Bank 4 Free Transfers into GW6 post-international break.  
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

## Strategy Hierarchy & Key Mechanisms

```
Canonical Preseason Strategy Trajectory (S13 / S5):
┌───────────────────────────────────────────────────────────────────────────────┐
│ GW1 or GW2: Bench Boost (BB2 Max EV 340.14 xP; BB1 Safe Start 338.88 xP)      │
│ └─ Captures 15 fit starters with zero bench capital penalty pre-Wildcard      │
├───────────────────────────────────────────────────────────────────────────────┤
│ GW3: Triple Captain Erling Haaland (Home vs COV, diff 2, 8.85 xP ceiling)     │
│ └─ S13 generates 66.72 xP in GW3 alone (+7.80 xP over FH3 alternative)        │
├───────────────────────────────────────────────────────────────────────────────┤
│ GW4: Wildcard Option 1 Rebuild (£97.5m spend, £2.5m ITB, 155.37 GW4-6 xP)     │
│ └─ Pivots into ARS (Gabriel, Raya, Tzolis), CHE (Palmer), EVE (Tarkowski)     │
├───────────────────────────────────────────────────────────────────────────────┤
│ GW5: Free Transfer Rolled (gw5_transfers=0)                                   │
│ └─ Banked FTs preserved through WC under 2026/27 rules                        │
├───────────────────────────────────────────────────────────────────────────────┤
│ GW6: Enter Post-International Break with 4 Banked Free Transfers              │
│ └─ Full flexibility to target injuries, deadline transfers, and FUL run      │
├───────────────────────────────────────────────────────────────────────────────┤
│ GW7–19: Hold Free Hit as Emergency / Winter Rotation Reserve                  │
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

| Rank | ID | Strategy Class | BB | Mid chip | Ban H | Ban Bruno | GW1–3 xP | GW4–6 xP | Total xP | Banked FTs GW6 |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | ---: | ---: | ---: | :---: |
| **#1** | **S13** | **Max EV Target (Canonical #1)** | **GW2** | **TC3 (Haaland)** | allow | allow | **184.77** | **155.37** | **340.14** | **4** |
| #2 | S15 | Ban Haaland Pre-Squad | GW2 | TC3 (Vuskovic) | ban | allow | 184.06 | 155.37 | 339.43 | 4 |
| #3 | S14 | Ban Bruno Pre-Squad | GW2 | TC3 (Haaland) | allow | ban | 183.71 | 155.37 | 339.08 | 4 |
| **#4** | **S5** | **Safe Start Target (Canonical #2)**| **GW1** | **TC3 (Haaland)** | allow | allow | **183.51** | **155.37** | **338.88** | **4** |
| #5 | S6 | Ban Bruno Pre-Squad | GW1 | TC3 (Haaland) | allow | ban | 183.38 | 155.37 | 338.75 | 4 |
| #5 | S7 | Ban Haaland Pre-Squad | GW1 | TC3 (Vuskovic) | ban | allow | 183.38 | 155.37 | 338.75 | 4 |
| #7 | S8 | Ban Both Pre-Squad | GW1 | TC3 (Vuskovic) | ban | ban | 180.55 | 155.37 | 335.92 | 4 |
| #8 | S16 | Ban Both Pre-Squad | GW2 | TC3 (Vuskovic) | ban | ban | 180.33 | 155.37 | 335.70 | 4 |
| **#9** | **S9** | **Top FH3 Path** | **GW2** | **FH3** | allow | allow | **176.97** | **155.37** | **332.34** | **4** |
| #9 | S11 | Ban Haaland FH3 Path | GW2 | FH3 | ban | allow | 176.97 | 155.37 | 332.34 | 4 |
| #11 | S1 | BB1 FH3 Allow All | GW1 | FH3 | allow | allow | 176.79 | 155.37 | 332.16 | 4 |
| #11 | S3 | BB1 FH3 Ban Haaland | GW1 | FH3 | ban | allow | 176.79 | 155.37 | 332.16 | 4 |
| #13 | S10 | BB2 FH3 Ban Bruno | GW2 | FH3 | allow | ban | 175.27 | 155.37 | 330.64 | 4 |
| #14 | S2 | BB1 FH3 Ban Bruno | GW1 | FH3 | allow | ban | 174.77 | 155.37 | 330.14 | 4 |
| #15 | S4 | BB1 FH3 Ban Both | GW1 | FH3 | ban | ban | 173.96 | 155.37 | 329.33 | 4 |
| #16 | S12 | BB2 FH3 Ban Both | GW2 | FH3 | ban | ban | 173.93 | 155.37 | 329.30 | 4 |

### Strategic Verdict & Key Decisions

1. **#1 Canonical Strategy Recommendation (Max EV Target)**: **S13 (BB2 + TC3 Haaland + WC4 Opt1, 340.14 xP)**. Deploys Bench Boost in GW2 (capitalizing on COV vs HUL and MUN vs IPS), Triple Captains Haaland in GW3 vs Coventry (diff 2), rebuilds on Wildcard GW4 into high-ceiling ARS/CHE/EVE assets, rolls GW5 transfer, and enters GW6 with **4 banked Free Transfers**.
2. **#2 Safe Start Recommendation (Max Lineup Certainty)**: **S5 (BB1 + TC3 Haaland + WC4 Opt1, 338.88 xP)**. Deploys BB1 for zero lineup risk pre-deadline, follows identical TC3 Haaland and WC4 Opt1 progression, trailing S13 by only 1.26 xP while eliminating GW2 bench rotation uncertainty.
3. **Balanced No-Haaland Structural Route**: **S15 (BB2 + TC3 Vuskovic + WC4 Opt1, 339.43 xP)**. Trailing by only **0.71 xP** (0.2%), proving high mathematical viability and flexibility for managers preferring a balanced premium midfield (Palmer, Bruno Fernandes, Wirtz, Gabriel, Calafiori) over solo Haaland.
4. **Alternative Structural Path (Top FH3)**: **S9 (BB2 + FH3 + WC4 Opt1, 332.34 xP)**. High-midfield pre-squad without Haaland, Free Hit in GW3 to capture Haaland vs COV, then permanent Haaland integration on WC4. Trails S13 by 7.80 xP.
5. **Structural Rules**: Bruno ban is binding across all paths (-1.06 to -4.44 xP). Haaland ban on FH3 is non-binding on allow-Bruno paths (S1=S3, S9=S11). GW4–6 WC Opt1 generates identical **155.37 xP** across all 16 scenarios.

---

## Verification & Delivery

- Role scrape: `uv run python docs/research/gw1-6-preseason-pipeline/run_pipeline.py`.
- Rates / new player: `uv run python docs/research/gw1-6-preseason-pipeline/refresh_downstream.py`.
- Availability unit tests: `tests/test_availability_priors.py`.
- ADR-0014 rate tests: `tests/test_expected_stats_blend.py`.
