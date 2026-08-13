# Expected Stats & GW1–5 Points Projection Research Note

**Updated**: 2026-08-14T01:30:00+07:00  
**Data stamp**: Expected Role Table 2026-08-13 (357 rows); Prior-Season Seed + Career Individual Rate + Destination Team Concede Rate (ADR-0014); downstream consumers refreshed 2026-08-14; archive 2026-07-29  
**Season**: 2026/27  
**Status**: Active Research Model (Non-Full-Season Candidate)  
**Purpose**: Build Event Rates for XI Contention Set via Prior-Season Seed, Career Individual Rate, and Destination Team Concede Rate; project GW1–5 $xP$ through `ParticipationStateHybridModel.predict` with Draft Availability overlays.  
**Scope**: XI Contention rates; Draft Shortlist projections export (Nailed + Regular). Softmax bonus over full XI Contention.  
**Related**: [Expected Role GW1–5](../01-expected-role-gw1-5/expected-role-gw1-5.md) · [Preseason Pipeline Master README](../README.md) · [Downstream refresh](../refresh_downstream.py) · ADR 0003 · ADR 0004 · ADR 0005 · ADR 0014  
**Artifacts**:
- [Expected Stats CSV](../../../data/research/gw1-6-preseason-pipeline/02-expected-stats-gw1-5/expected-stats-gw1-5.csv)
- [GW1–5 Projections CSV](../../../data/research/gw1-6-preseason-pipeline/02-expected-stats-gw1-5/gw1-5_projections.csv)

---

## Sources

- Expected Role Table + priors: Stage 1 CSV (`data/research/gw1-6-preseason-pipeline/01-expected-role-gw1-5/expected-role-gw1-5.csv`)
- Prior-Season Seed archive: `data/archive/2025-26/processed/`
- `history_past` older FPL seasons: `data/raw/element_summary_{id}.json`
- Career Individual Rate packages (32 Draft newcomers, last completed senior league season)
- Fixtures / club strengths: `data/processed/fixtures.parquet`, `clubs.parquet`; Destination Team Concede Rate from 2025/26 finished fixtures
- Availability overlays: [`availability_priors.py`](../availability_priors.py)

---

## Agent Prompt & Reproducibility Instructions

```text
Run parameterized GW1-5 Expected Stats & Projections (Stage 2):

1. Command: uv run python docs/research/gw1-6-preseason-pipeline/02-expected-stats-gw1-5/build_expected_stats.py
   - Prior-Season Seed: 2025/26 FPL archive via Player Code Mapping (ADR 0004); minutes >= 450.
   - No seed: Career Individual Rate (xG/xA/Defcon/saves) from last-season package, else most recent older FPL history_past >= 450.
   - No seed GC/CS: Destination Team Concede Rate (2025/26 PL GC/game; COV/HUL/IPS → league avg 1.375).
   - Thin career samples (<450m) shrink toward Research Position Baseline.
   - Zero Draft on fallback_baseline (SystemExit lists names).
   - Export CSV to data/research/gw1-6-preseason-pipeline/02-expected-stats-gw1-5/expected-stats-gw1-5.csv.
2. Command: uv run python docs/research/gw1-6-preseason-pipeline/02-expected-stats-gw1-5/project_expected_points.py
   - Build feature frame with Expected Role priors and availability overlays (Watch 0.70x, Exclude GW1-5).
   - Predict xP via ParticipationStateHybridModel across horizon 5 with Softmax bonus over 357 XI Contention.
   - Export Draft Shortlist (Nailed + Regular) to data/research/gw1-6-preseason-pipeline/02-expected-stats-gw1-5/gw1-5_projections.csv.
3. After rate or new-player package change, refresh consumers:
   uv run python docs/research/gw1-6-preseason-pipeline/refresh_downstream.py
4. Verification: uv run pytest tests/test_expected_stats_blend.py, uv run ruff check .
```

---

## Method

### 1. Event Rates (ADR-0014, 2026-08-14)
- **Identity**: Permanent Player Code Mapping (ADR 0004).
- **Returning Players**: Prior-Season Seed only (2025/26, ≥450 mins). No 3-year dual-floor blend. Club-changers with a seed keep player-level GC/CS.
- **No seed**: Career Individual Rate for xG/xA/Defcon/saves; Destination Team Concede Rate for GC/CS.
- **Promoted Clubs** (COV, HUL, IPS): league-average 2025/26 PL GC/game (1.375), not Championship GC.
- **Thin career sample**: minutes < 450 shrink linearly toward Research Position Baseline (Dowman).
- **Zero Draft on Fallback Baseline Invariant**: Nailed/Regular never sit on `fallback_baseline`. Builder raises `SystemExit` listing names.

### New Draft player
When Stage 1 injects a Nailed/Regular with no Prior-Season Seed:
1. Last completed senior league season: xG, xA, Defcon, saves. Omit GC.
2. Add `{player_id: {xg, xa, saves, defcon, defcon_cbit, minutes?, note}}` to `CAREER_INDIVIDUAL_RATES` in `build_expected_stats.py`.
3. `uv run python docs/research/gw1-6-preseason-pipeline/refresh_downstream.py`.
Thin samples (`minutes` < 450) shrink toward Research Position Baseline. Club-changers with a 2025/26 seed keep that seed — do not add them here.

### 2. $xP$ reconstruction
- Feature rows GW1–5 with Expected Role Priors + availability overlays.
- Softmax bonus over full 357 XI Contention; CSV export = Nailed + Regular only (227 rows).
- Appearance blend 3→8 unchanged; GW1 weight = 0 (Cold-Start).

---

## Findings

### 1. Top Draft Shortlist (GW1–5 aggregate $xP$)

| Rank | Player | Club | Pos | GW1 | GW2 | GW3 | GW4 | GW5 | Total |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Haaland | MCI | FWD | 5.18 | 5.07 | 6.44 | 3.90 | 6.40 | **26.98** |
| 2 | Vuskovic | BHA | DEF | 5.21 | 4.13 | 6.27 | 6.21 | 4.16 | **25.98** |
| 3 | Gabriel | ARS | DEF | 5.88 | 4.55 | 4.54 | 5.15 | 5.15 | **25.27** |
| 4 | B.Fernandes | MUN | MID | 5.90 | 5.82 | 4.79 | 3.84 | 4.82 | **25.17** |
| 5 | Wieffer | BHA | DEF | 4.70 | 3.83 | 5.58 | 5.54 | 3.86 | **23.51** |
| 6 | Palmer | CHE | MID | 4.53 | 5.45 | 2.96 | 5.54 | 4.48 | **22.96** |
| 7 | Muharemović | LEE | DEF | 4.30 | 4.29 | 4.25 | 5.33 | 4.30 | **22.47** |
| 8 | Calafiori | ARS | DEF | 5.08 | 4.08 | 4.07 | 4.55 | 4.55 | **22.33** |
| 9 | Sarr | CRY | MID | 4.31 | 3.41 | 4.34 | 5.22 | 4.25 | **21.52** |
| 10 | Wirtz | LIV | MID | 3.98 | 3.97 | 4.65 | 4.66 | 3.94 | **21.20** |
| 11 | Virgil | LIV | DEF | 3.88 | 3.87 | 4.76 | 4.77 | 3.85 | **21.13** |
| 12 | Van Hecke | TOT | DEF | 3.98 | 4.92 | 4.03 | 4.01 | 4.01 | **20.96** |
| 13 | Tzolis | ARS | MID | 5.27 | 3.53 | 3.52 | 4.32 | 4.32 | **20.95** |
| 14 | Schade | BRE | MID | 4.18 | 4.12 | 4.92 | 4.15 | 3.40 | **20.76** |
| 15 | Maguire | MUN | DEF | 4.77 | 4.73 | 3.95 | 3.27 | 3.97 | **20.69** |

Isak **16.78** (was ~23.9 on 3-year blend): 2025/26 seed is 694m with low xG — Prior-Season Seed, not injury-year replacement by 2024/25. Jacquet **19.73** (career Rennes + LIV dest GC 1.395). Tzolis **20.95** (Club Brugge career + ARS dest GC 0.711).

### 2. Rate source mix (357 rows)
- `prior_season_seed`: 252 · `+defcon_baseline_fill`: 16 · `+defcon_external_fill`: 2
- `career_individual+destination_gc`: 32 · `career_fpl_prior_year+destination_gc`: 20 · `external_3season_research+destination_gc`: 10
- `fallback_baseline+destination_gc`: 25 (Rotation/Cameo only)
- **Zero** Draft (Nailed/Regular) on fallback.

### 3. Softmax
- Full XI Contention competitor set (357 players) evaluated for realistic baseline bonus allocation.

---

## Decision

**Verdict**: ADR-0014 rate split is live. Returning Players use 2025/26 only. Newcomers use last-season career attack/Defcon plus destination-club GC/CS. Dual-floor 50/50 retired.

**Recommended Action**:
- New Draft / rate change → `CAREER_INDIVIDUAL_RATES` then `refresh_downstream.py`.
- Role scrape still `run_pipeline.py` (HTTP).

---

## Verification & Delivery

- Unit tests: `tests/test_expected_stats_blend.py`, `tests/test_availability_priors.py`.
- Artifacts under `data/research/gw1-6-preseason-pipeline/02-expected-stats-gw1-5/`.
