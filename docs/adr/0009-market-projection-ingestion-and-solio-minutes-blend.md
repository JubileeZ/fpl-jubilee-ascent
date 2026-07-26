# 9. Market Projection Ingestion and Solio Points Integration (DEPRECATED)

Date: 2026-07-26

## Status

Deprecated / Superseded

## Context

Audited Solio Analytics unauthenticated public API (`https://fpl.solioanalytics.com/api/data/latest.json`) for market projections and expected minutes ($xMins$).

### Structural API Deficiencies (Reason for Deprecation)
1. **Top-N Payload Truncation**: Public API endpoint returns top-30 summary feed (`topProjected`), not full ~600 player pool.
2. **Leaderboard Truncation (Missing Data vs Zero)**: Sub-lists (`topGoals`, `topAssists`, `topBonus`, `topDefCon`, `bestCleanSheets`) are top-10/15 leaderboards. Non-leaderboard assets receive `event_pts = 0`, treating missing leaderboard data as zero event threat.
3. **Severe Inversion Saturation**: Residual $xP$ inversion caused 90.0% clip rate ($P_{\ge 60} \ge 1.0$) across pool, destroying minute-variance signal (89 vs 80 vs 65 mins).

## Decision

1. **Complete Pipeline Removal**:
   - Removed Solio pipeline integration from `features/builder.py`.
   - Removed 24/7 serverless GitHub Action workflow (`.github/workflows/fetch_solio.yml`).
   - Deprecated `commands/fetch_solio.py` and Solio ingestion steps.

2. **Minute Model Single Source of Truth**:
   - Retain local 2-State Empirical Bayes Mixture Model ($N_{\text{starts}}$, $avg\_mins\_3gw$, league starter shrinkage $E_{\text{league}} = 78.0$) for continuous minute estimations.

## Consequences

- Eliminates partial-population bias and top-N summary truncation artifacts from feature pipeline.
- Removes unused background GitHub Action workflow.
- Keeps model engine strictly grounded in official FPL API availability snapshots and local empirical Bayes mixture models.

