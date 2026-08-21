# Expected Stats & GW1–5 Points Projection Research Note

**Updated**: 2026-08-19T13:45:00+07:00  
**Data stamp**: Expected Role Table 2026-08-18 (575 rows); Prior-Season Seed + Career Individual Rate + Destination Team Concede Rate (ADR-0014); public fixtures 2026-08-19; Champion saves/defcon × defence_multiplier; Stage 2 rate rebuild skipped (element summaries <100)  
**Season**: 2026/27  
**Status**: Archived (2026/27 preseason). Active Research Model (Non-Full-Season Candidate)  
**Purpose**: Build Event Rates for XI Contention via Prior-Season Seed (>=900 mins), Career Individual Rate, and Destination Team Concede Rate; project GW1–5 $xP$ through `ParticipationStateHybridModel.predict` with Draft Availability overlays.  
**Scope**: 575 player rates; Draft Shortlist projections export (Nailed + Regular, 234 rows). Softmax bonus over full 575 players.  
**Related**: [Expected Role GW1–5](../01-expected-role-gw1-5/expected-role-gw1-5.md) · [Preseason Pipeline Master README](../README.md) · [Downstream refresh](../refresh_downstream.py) · ADR 0003 · ADR 0004 · ADR 0005 · ADR 0014  
**Artifacts**:
- [Expected Stats CSV](expected-stats-gw1-5.csv)
- [GW1–5 Projections CSV](gw1-5_projections.csv)

---

## Sources

- Expected Role Table + priors: Stage 1 CSV (`docs/archive/gw1-6-preseason-pipeline/01-expected-role-gw1-5/expected-role-gw1-5.csv`)
- Prior-Season Seed archive: `data/archive/2025-26/processed/`
- `history_past` older FPL seasons: `data/raw/element_summary_{id}.json`
- Career Individual Rate packages (32 Draft newcomers, last completed senior league season)
- Fixtures / club strengths: `data/processed/fixtures.parquet`, `clubs.parquet`; Destination Team Concede Rate from 2025/26 finished fixtures
- Availability overlays: [`availability_priors.py`](../availability_priors.py)

---

## Agent Prompt & Reproducibility Instructions

```text
Run parameterized GW1-5 Expected Stats & Projections (Stage 2):

1. Command: uv run python docs/archive/gw1-6-preseason-pipeline/02-expected-stats-gw1-5/build_expected_stats.py
   - Prior-Season Seed: 2025/26 FPL archive via Player Code Mapping (ADR 0004); minutes >= 900.
   - No seed: Career Individual Rate (xG/xA/Defcon/saves) from last-season package, else most recent older FPL history_past >= 900.
   - No seed GC/CS: Destination Team Concede Rate (2025/26 PL GC/game; COV/HUL/IPS → league avg 1.375).
   - Thin career samples (<900m) shrink toward Research Position Baseline.
   - Zero Draft on fallback_baseline (SystemExit lists names).
   - Export CSV to docs/archive/gw1-6-preseason-pipeline/02-expected-stats-gw1-5/expected-stats-gw1-5.csv.
2. Command: uv run python docs/archive/gw1-6-preseason-pipeline/02-expected-stats-gw1-5/project_expected_points.py
   - Build feature frame with Expected Role priors and availability overlays (Watch 0.70x, Exclude GW1-5).
   - Predict xP via ParticipationStateHybridModel across horizon 5 with Softmax bonus over 575 players.
   - Export Draft Shortlist (Nailed + Regular) to docs/archive/gw1-6-preseason-pipeline/02-expected-stats-gw1-5/gw1-5_projections.csv.
3. After rate or new-player package change, refresh consumers:
   uv run python docs/archive/gw1-6-preseason-pipeline/refresh_downstream.py
4. Verification: uv run pytest tests/test_expected_stats_blend.py, uv run ruff check .
```

---

## Method

### 1. Event Rates (ADR-0014, 2026-08-14)
- **Identity**: Permanent Player Code Mapping (ADR 0004).
- **Returning Players**: Prior-Season Seed only (2025/26, ≥900 mins). No 3-year dual-floor blend. Club-changers with a seed keep player-level GC/CS.
- **No seed**: Career Individual Rate for xG/xA/Defcon/saves; Destination Team Concede Rate for GC/CS.
- **Promoted Clubs** (COV, HUL, IPS): league-average 2025/26 PL GC/game (1.375), not Championship GC.
- **Thin career sample**: minutes < 900 shrink linearly toward Research Position Baseline (Dowman).
- **Zero Draft on Fallback Baseline Invariant**: Nailed/Regular never sit on `fallback_baseline`. Builder raises `SystemExit` listing names.

### New Draft player
When Stage 1 injects a Nailed/Regular with no Prior-Season Seed:
1. Last completed senior league season: xG, xA, Defcon, saves. Omit GC.
2. Add `{player_id: {xg, xa, saves, defcon, defcon_cbit, minutes?, note}}` to `CAREER_INDIVIDUAL_RATES` in `build_expected_stats.py`.
3. `uv run python docs/archive/gw1-6-preseason-pipeline/refresh_downstream.py`.
Thin samples (`minutes` < 900) shrink toward Research Position Baseline. Club-changers with a 2025/26 seed keep that seed — do not add them here.

### 2. $xP$ reconstruction
- Feature rows GW1–5 with Expected Role Priors + availability overlays.
- Softmax bonus over full 575 players; CSV export = Nailed + Regular only (**234** rows).
- Appearance blend 3→8 unchanged; GW1 weight = 0 (Cold-Start).

### Metric Definitions & Direction

| Metric | Symbol | Definition / Formula | Direction | Ideal / Benchmark | Description |
|---|---|---|---|---|---|
| **Expected Goals per 90** | `xG/90` | Expected non-penalty goals per 90 minutes | Higher is better $\uparrow$ | **$> 0.40$** (FWD/MID) / **$> 0.10$** (DEF) | Primary goal threat generator. |
| **Expected Assists per 90** | `xA/90` | Expected assisted goals per 90 minutes | Higher is better $\uparrow$ | **$> 0.25$** (Playmaker) / **$> 0.15$** (Attacking FB) | Primary creative opportunity generator. |
| **Goals Conceded per 90** | `GC/90` | Projected goals conceded per match | Lower is better $\downarrow$ | **$< 1.10$** (Elite Defense) / **$< 1.35$** (Mid-table) | Directly determines Poisson clean-sheet probability ($e^{-\lambda}$). |
| **Saves per 90** | `Saves/90` | Goalkeeper saves projected per 90 minutes | Higher is better $\uparrow$ | **$\ge 3.20$** (Volume keeper) | Generates baseline save points ($+1\text{ pt per 3 saves}$) and BPS accumulation. |
| **Defensive Contribution** | `Defcon` | Tackle/interception baseline event rate per 90 | Higher is better $\uparrow$ | **$> 2.00$** (Elite ball-winner) | Informs BPS baseline for defensive midfielders and center-backs. |
| **Expected Points per GW** | `xP` | `ParticipationStateHybridModel.predict` output | Higher is better $\uparrow$ | **$\ge 5.0\text{ xP/GW}$** (Starters) / **$\ge 6.5\text{ xP/GW}$** (Captains) | Comprehensive projection integrating role, rates, opponents, and bonus distribution. |

---

## Findings

### 1. Top Draft Shortlist (GW1–5 aggregate $xP$)

| Rank | Player | Club | Pos | GW1 | GW2 | GW3 | GW4 | GW5 | Total |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Haaland | MCI | FWD | 5.02 | 4.97 | 6.41 | 3.82 | 6.33 | **26.54** |
| 2 | Isak | LIV | FWD | 4.74 | 4.71 | 5.89 | 5.92 | 4.64 | **25.91** |
| 3 | Gabriel | ARS | DEF | 5.38 | 5.01 | 4.97 | 5.13 | 5.13 | **25.63** |
| 4 | Vuskovic | BHA | DEF | 5.20 | 4.49 | 5.54 | 5.53 | 4.55 | **25.31** |
| 5 | B.Fernandes | MUN | MID | 5.48 | 5.39 | 4.69 | 4.19 | 4.73 | **24.49** |
| 6 | Wieffer | BHA | DEF | 4.69 | 4.18 | 4.89 | 4.88 | 4.23 | **22.86** |
| 7 | Palmer | CHE | MID | 4.44 | 5.25 | 3.43 | 5.31 | 4.40 | **22.83** |
| 8 | Calafiori | ARS | DEF | 5.02 | 4.23 | 4.21 | 4.54 | 4.54 | **22.54** |
| 9 | Guéhi | MCI | DEF | 4.31 | 4.29 | 4.77 | 4.02 | 4.75 | **22.15** |
| 10 | Muharemović | LEE | DEF | 4.30 | 4.27 | 4.25 | 4.65 | 4.28 | **21.74** |
| 11 | Hill | BOU | DEF | 3.94 | 4.44 | 4.47 | 4.43 | 4.24 | **21.52** |
| 12 | Sarr | CRY | MID | 4.25 | 3.55 | 4.27 | 5.10 | 4.21 | **21.37** |
| 13 | Tzolis | ARS | MID | 5.25 | 3.64 | 3.61 | 4.30 | 4.30 | **21.11** |
| 14 | James | CHE | DEF | 4.03 | 4.63 | 3.39 | 4.65 | 4.01 | **20.72** |
| 15 | Schade | BRE | MID | 4.14 | 4.08 | 4.79 | 4.10 | 3.58 | **20.70** |

### 2. Rate source mix (575 rows)
- `prior_season_seed`: 252 · `+defcon_baseline_fill`: 17 · `+defcon_external_fill`: 2
- `career_individual+destination_gc`: 126 · `career_fpl_prior_year+destination_gc`: 53
- `fallback_baseline+destination_gc`: 125 (Rotation/Cameo/Out of Contention only)
- **Zero** Draft (Nailed/Regular) on fallback.

### 3. Softmax
- Full 575 player competitor set evaluated for realistic baseline bonus allocation.

---

## Decision

**Verdict**: ADR-0014 rate split is live. Returning Players use 2025/26 only. Newcomers use last-season career attack/Defcon plus destination-club GC/CS. Dual-floor 50/50 retired.

**Recommended Action**:
- New Draft / rate change → `CAREER_INDIVIDUAL_RATES` then `refresh_downstream.py`.
- Role scrape still `run_pipeline.py` (HTTP).

---

## Verification & Delivery

- Unit tests: `tests/test_expected_stats_blend.py`, `tests/test_availability_priors.py`.
- Artifacts under `docs/archive/gw1-6-preseason-pipeline/02-expected-stats-gw1-5/`.
