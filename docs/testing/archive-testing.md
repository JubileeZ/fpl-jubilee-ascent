# Historical Archive Testing Guide

**Updated**: 2026-08-01T15:48:00+07:00  
**Status**: Active  

---

## Historical Archive Testing Rules

- `data/archive/<season>/processed/` contains historical season data for exploratory backtests, regression testing, and model comparison.
- **Immutability Rule**: Treat `data/archive/` Parquet files as immutable. Regenerate historical data through archive/snapshot tooling; never edit or delete archive files directly.
- **Exploratory Scope**: Archive backtests are exploratory only: terminal player, club, fixture, and availability metadata may not represent the pre-deadline information set.

---

## Example Execution Commands

```bash
# Run exploratory backtest against historical processed season data
uv run python -m commands.backtest participation_state_hybrid --gw_range 1-38 --data_dir data/archive/2025-26/processed
```
