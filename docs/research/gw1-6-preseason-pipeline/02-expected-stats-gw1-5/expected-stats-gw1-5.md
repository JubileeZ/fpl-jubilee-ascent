# Expected Stats & GW1–5 Points Projection Research Note

**Updated**: 2026-08-10T06:45:00+07:00  
**Data stamp**: Expected Role Table 2026-08-10 (351 rows); dual-floor + Defcon-fill grill lock 2026-08-10; archive 2026-07-29  
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

- Expected Role Table + priors: Stage 1 CSV
- Prior-season archive: `data/archive/2025-26/processed/`
- `history_past` season totals: `data/raw/element_summary_{id}.json`
- External research packages (incl. 15 Draft Regular packages 2026-08-10)
- Fixtures / club strengths: `data/processed/fixtures.parquet`, `clubs.parquet`
- Availability overlays: [`availability_priors.py`](../availability_priors.py)

---

## Agent Prompt

```text
Rebuild expected-stats-gw1-5 per 2026-08-10 grill lock:

1. build_expected_stats.py:
   - code map; any-usable floor 450; latest-slot floor 900 (thin 450–899 → older-mean only;
     no ≥900 year → equal-weight all ≥450);
   - Defcon-only fill when usable years lack Defcon evidence (external CBIT / baseline);
   - external packages when zero usable seasons (Draft Regulars packaged).
2. project_expected_points.py → ParticipationStateHybridModel.predict;
   Softmax over full XI Contention; availability_priors overlays.
3. Update Findings; ensure zero Draft on fallback_baseline.
4. Re-run Stage 3 matrix after rate rebuild.
```

---

## Method

### 1. Event Rates (grill lock 2026-08-10)
- **Identity**: Permanent Player Code Mapping (ADR 0004).
- **Window**: 2023/24, 2024/25, 2025/26.
- **Any-usable floor**: minutes ≥ **450**.
- **Latest-slot floor**: minutes ≥ **900**. Years 450–899 may only enter the older-mean half. If no ≥900 year exists → equal-weight all ≥450 usables.
- **Non-Defcon blend**: 50% latest-eligible + 50% mean of other usables (or equal-weight / 100% single).
- **Defcon**: blend only seasons with Defcon evidence; else external `defcon_cbit` package; else Research Position Baseline.
- **Gap fill (full rates)**: external package only if zero Usable Seasons; else Research Position Baseline (position-only; not production Position-Price).

### 2. $xP$ reconstruction
- Feature rows GW1–5 with Expected Role Priors + availability overlays.
- Softmax bonus competitors = full XI Contention; CSV export = Nailed + Regular only.

---

## Findings

### 1. Top Draft Shortlist (GW1–5 aggregate $xP$)

| Rank | Player | Club | Pos | GW1 | GW2 | GW3 | GW4 | GW5 | Total |
|------|--------|------|-----|-----|-----|-----|-----|-----|-------|
| 1 | Haaland | MCI | FWD | 5.40 | 5.31 | 6.75 | 4.07 | 6.71 | **28.24** |
| 2 | Palmer | CHE | MID | 4.82 | 5.94 | 3.06 | 5.99 | 4.77 | **24.58** |
| 3 | Isak | LIV | FWD | 4.44 | 4.45 | 5.47 | 5.45 | 4.38 | **24.19** |
| 4 | Vuskovic | BHA | DEF | 4.69 | 3.66 | 5.72 | 5.66 | 3.75 | **23.48** |
| 5 | Gabriel | ARS | DEF | 5.57 | 4.13 | 4.12 | 4.78 | 4.80 | **23.40** |
| 6 | Muharemović | LEE | DEF | 4.47 | 4.47 | 4.44 | 5.34 | 4.49 | **23.21** |
| 7 | Jacquet | LIV | DEF | 4.23 | 4.23 | 5.04 | 5.03 | 4.23 | **22.76** |
| 8 | O'Reilly | MCI | DEF | 4.27 | 4.24 | 4.95 | 3.60 | 4.94 | **22.00** |
| 9 | Sarr | CRY | MID | 4.34 | 3.44 | 4.36 | 5.34 | 4.28 | **21.76** |
| 10 | Wirtz | LIV | MID | 3.95 | 3.95 | 4.62 | 4.61 | 3.93 | **21.06** |
| 11 | Tarkowski | EVE | DEF | 4.12 | 4.41 | 3.45 | 4.42 | 4.42 | **20.82** |
| 12 | Thiago | BRE | FWD | 4.18 | 4.08 | 4.99 | 4.12 | 3.29 | **20.66** |

Isak rises after dual-floor drops thin 2025/26 (694m) from the latest slot (now older-mean only; latest = 2024/25).

### 2. Rate source mix (351 rows)
- `fpl_recency_50_50`: 187 · `fpl_single_usable_season`: 62 · `external_3season_research`: 37 · `fallback_baseline`: 28 · `fpl_equal_weight_thin_latest`: 14 · plus Defcon-fill variants (21 rows)
- **Zero** Draft (Nailed/Regular) on `fallback_baseline` after 15 Draft Regular packages.

### 3. Softmax
- Unchanged: full XI Contention competitor set (grill Q4 A).

---

## Decision

**Verdict**: Dual-floor + Defcon-only fill + Draft Regular packages approved. Research Position Baseline remains position-only (glossary distinguishes production Position-Price).

**Recommended Action**:
- Tighten best-guess Draft packages when full CBIT/FBref tables land (Rushworth CHA #1 is FBref-anchored; several others are best-guess).
- Optional packages for remaining 28 Rotation/Cameo fallbacks if Softmax rivals matter.

---

## Risks and unknowns

- Several Draft packages are best-guess proxies (labeled in `EXTERNAL_RESEARCH_RATES` notes).
- Equal-weight thin-latest path (`fpl_equal_weight_thin_latest`) still mixes multiple sub-900 seasons.
- Softmax dilution from Rotation/Cameo unchanged by design.

---

## Verification & Delivery

- Unit tests: `tests/test_expected_stats_blend.py`, `tests/test_availability_priors.py`.
- Artifacts under `data/research/gw1-6-preseason-pipeline/02-expected-stats-gw1-5/`.
