# Expected Stats & GW1–5 Points Projection Research Note

**Updated**: 2026-08-13T03:30:00+07:00  
**Data stamp**: Expected Role Table 2026-08-13 (357 rows); dual-floor + Defcon-fill grill lock 2026-08-12; archive 2026-07-29  
**Season**: 2026/27  
**Status**: Active Research Model (Non-Full-Season Candidate)  
**Purpose**: Build Event Rates for XI Contention Set via Permanent Player Code Mapping + dual-floor usable-season blend; project GW1–5 $xP$ through `ParticipationStateHybridModel.predict` with Draft Availability overlays.  
**Scope**: XI Contention rates; Draft Shortlist projections export (Nailed + Regular). Softmax bonus over full XI Contention.  
**Related**: [Expected Role GW1–5](../01-expected-role-gw1-5/expected-role-gw1-5.md) · [Preseason Pipeline Master README](../README.md) · ADR 0004 · ADR 0005  
**Artifacts**:
- [Expected Stats CSV](../../../data/research/gw1-6-preseason-pipeline/02-expected-stats-gw1-5/expected-stats-gw1-5.csv)
- [GW1–5 Projections CSV](../../../data/research/gw1-6-preseason-pipeline/02-expected-stats-gw1-5/gw1-5_projections.csv)

---

## Sources

- Expected Role Table + priors: Stage 1 CSV (`data/research/gw1-6-preseason-pipeline/01-expected-role-gw1-5/expected-role-gw1-5.csv`)
- Prior-season archive: `data/archive/2025-26/processed/`
- `history_past` season totals: `data/raw/element_summary_{id}.json`
- External research packages (42 research packages for foreign transfers and Draft Regulars)
- Fixtures / club strengths: `data/processed/fixtures.parquet`, `clubs.parquet`
- Availability overlays: [`availability_priors.py`](../availability_priors.py)

---

## Agent Prompt & Reproducibility Instructions

```text
Run parameterized GW1-5 Expected Stats & Projections (Stage 2):

1. Command: uv run python docs/research/gw1-6-preseason-pipeline/02-expected-stats-gw1-5/build_expected_stats.py
   - Apply Permanent Player Code Mapping (ADR 0004) across seasons 2023/24, 2024/25, 2025/26.
   - Dual-floor usable-season blend:
     * Any-usable floor: minutes >= 450.
     * Latest-slot floor: minutes >= 900 (thin 450–899 mins enter older-mean only; if no >=900 year, equal-weight all >=450).
   - Defcon-only fill: blend seasons with Defcon evidence; else external CBIT package; else Research Position Baseline.
   - External packages for foreign arrivals and Draft Regulars (Zero Draft on fallback_baseline invariant).
   - Export CSV to data/research/gw1-6-preseason-pipeline/02-expected-stats-gw1-5/expected-stats-gw1-5.csv.
2. Command: uv run python docs/research/gw1-6-preseason-pipeline/02-expected-stats-gw1-5/project_expected_points.py
   - Build feature frame with Expected Role priors and availability overlays (Watch 0.70x, Exclude GW1-5).
   - Predict xP via ParticipationStateHybridModel across horizon 5 with Softmax bonus over 357 XI Contention.
   - Export Draft Shortlist (Nailed + Regular) to data/research/gw1-6-preseason-pipeline/02-expected-stats-gw1-5/gw1-5_projections.csv.
3. Verification: uv run pytest tests/test_expected_stats_blend.py, uv run ruff check .
```

---

## Method

### 1. Event Rates (grill lock 2026-08-10 / refreshed 2026-08-12)
- **Identity**: Permanent Player Code Mapping (ADR 0004).
- **Window**: 2023/24, 2024/25, 2025/26.
- **Any-usable floor**: minutes ≥ **450**.
- **Latest-slot floor**: minutes ≥ **900**. Years 450–899 may only enter the older-mean half. If no ≥900 year exists → equal-weight all ≥450 usables.
- **Non-Defcon blend**: 50% latest-eligible + 50% mean of other usables (or equal-weight / 100% single).
- **Defcon**: blend only seasons with Defcon evidence; else external `defcon_cbit` package; else Research Position Baseline.
- **Gap fill (full rates)**: external package only if zero Usable Seasons; else Research Position Baseline (position-only; not production Position-Price).
- **Zero Draft on Fallback Baseline Invariant**: All Draft Regulars / Nailed Starters without archive minutes must have external research packages in `EXTERNAL_RESEARCH_RATES`.

### 2. $xP$ reconstruction
- Feature rows GW1–5 with Expected Role Priors + availability overlays.
- Softmax bonus over full 357 XI Contention; CSV export = Nailed + Regular only (227 rows).

---

## Findings

### 1. Top Draft Shortlist (GW1–5 aggregate $xP$)

| Rank | Player | Club | Pos | GW1 | GW2 | GW3 | GW4 | GW5 | Total |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Haaland | MCI | FWD | 5.38 | 5.28 | 6.72 | 4.02 | 6.68 | **28.09** |
| 2 | B.Fernandes | MUN | MID | 5.82 | 5.74 | 4.76 | 3.88 | 4.80 | **24.99** |
| 3 | Palmer | CHE | MID | 4.83 | 5.91 | 3.05 | 6.00 | 4.78 | **24.57** |
| 4 | Isak | LIV | FWD | 4.40 | 4.39 | 5.37 | 5.37 | 4.34 | **23.86** |
| 5 | Vuskovic | BHA | DEF | 4.66 | 3.65 | 5.70 | 5.65 | 3.72 | **23.39** |
| 6 | Gabriel | ARS | DEF | 5.55 | 4.12 | 4.11 | 4.76 | 4.76 | **23.30** |
| 7 | Muharemović | LEE | DEF | 4.47 | 4.46 | 4.42 | 5.37 | 4.48 | **23.20** |
| 8 | Jacquet | LIV | DEF | 4.21 | 4.21 | 5.01 | 5.01 | 4.19 | **22.63** |
| 9 | O'Reilly | MCI | DEF | 4.26 | 4.24 | 4.94 | 3.59 | 4.93 | **21.96** |
| 10 | Sarr | CRY | MID | 4.33 | 3.43 | 4.37 | 5.29 | 4.29 | **21.70** |
| 11 | Wieffer | BHA | DEF | 4.29 | 3.42 | 5.20 | 5.17 | 3.48 | **21.56** |
| 12 | Virgil | LIV | DEF | 3.90 | 3.90 | 4.72 | 4.72 | 3.88 | **21.12** |
| 13 | Wirtz | LIV | MID | 3.93 | 3.92 | 4.56 | 4.56 | 3.89 | **20.87** |
| 14 | Tarkowski | EVE | DEF | 4.12 | 4.11 | 3.43 | 4.13 | 5.01 | **20.79** |
| 15 | Hill | BOU | DEF | 3.30 | 4.48 | 4.50 | 4.46 | 3.82 | **20.57** |

Identity match fix (2026-08-13): B.Fernandes now #2 (was unmatched vs FFS "Bruno Fernandes"; Bruno G. no longer occupies MUN). Virgil #12 (was Rotation because "Van Dijk" missed web_name "Virgil"). Bruno G. is ARS Rotation — not in Draft Shortlist. Softmax competitor set still 357; export is 227 Nailed+Regular.

### 2. Rate source mix (357 rows)
- `fpl_recency_50_50`: 189 · `fpl_single_usable_season`: 62 · `external_3season_research`: 42 · `fallback_baseline`: 26 · `fpl_equal_weight_thin_latest`: 15 · plus Defcon-fill variants (23 rows)
- **Zero** Draft (Nailed/Regular) on `fallback_baseline` (all 26 fallback_baseline rows are bench Rotation/Cameo).

### 3. Softmax
- Full XI Contention competitor set (357 players) evaluated for realistic baseline bonus allocation.

---

## Decision

**Verdict**: Dual-floor + Defcon-only fill + 42 external research packages strictly preserve zero Draft players on fallback baseline.

**Recommended Action**:
- Maintain external research packages in sync with any live FFS predicted XI modifications.

---

## Verification & Delivery

- Unit tests: `tests/test_expected_stats_blend.py`, `tests/test_availability_priors.py`.
- Artifacts under `data/research/gw1-6-preseason-pipeline/02-expected-stats-gw1-5/`.
