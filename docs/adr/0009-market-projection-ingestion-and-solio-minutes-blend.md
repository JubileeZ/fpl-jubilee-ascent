# 9. Market Projection Ingestion and Solio Minutes Blend

Date: 2026-07-26

## Status

Accepted

## Context

The engine previously relied on historical rolling 3-GW minutes (`avg_mins_3gw`) and position-price fallbacks for expected minutes (`xMins`). During cold-start (GW1–4) or for new signings, players with zero 3-GW history (such as Alexander Isak, Dominic Solanke, or newly transferred players) received low minute estimates unless manually overridden via `availability_overrides.csv`.

Solio Analytics provides an unauthenticated, 4-hour refreshed public API (`https://fpl.solioanalytics.com/api/data/latest.json`) incorporating efficient sports betting market odds for expected minutes (`solio_xmins`) and expected points (`solio_xp`).

## Decision

1. **Ingestion & Archiving**:
   - Ingest live Solio Analytics data via `commands/fetch_solio.py` to `data/solio_latest.parquet` (and `solio_raw.json`).
   - Freeze one pre-deadline snapshot per gameweek to `data/archive/solio/solio_gw{GW}.parquet` to preserve historical market projections for walk-forward backtesting.

2. **Feature & Model Pipeline Integration**:
   - Add `solio_xmins` and `solio_xp` as canonical features in `features/builder.py`.
   - **Cold-Start Guard (GW1–4 or 0 historical starts)**: Use `solio_xmins` as the primary baseline expected minutes prior when historical starts are 0.
   - **Established Starters ($\ge 3$ starts)**: Blend historical 3-GW actual minutes (60%) with `solio_xmins` (40%).

3. **Cross-Check Reporting**:
   - Maintain `uv run python -m commands.fetch_solio` to generate cross-check comparisons between local component model projections (`metrics_component_hybrid`) and market-odds projections (`solio`).

## Consequences

- Resolves cold-start minute underestimations for key starters in GW1–4 without needing manual CSV overrides for every player.
- Preserves walk-forward backtesting capability through frozen gameweek Parquet archives.
- Maintains single source of truth while allowing cross-model diagnostic comparisons.
