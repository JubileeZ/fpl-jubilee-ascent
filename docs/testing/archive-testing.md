# Historical Archive Testing Guide

**Updated**: 2026-08-01T15:48:00+07:00  
**Status**: Active  

---

## Historical Archive Testing Rules

- `data/archive/<season>/processed/` contains historical season data for exploratory backtests, regression testing, and model comparison.
- CLI model names: [docs/model_name.md](../model_name.md).
- **Immutability Rule**: Treat `data/archive/` Parquet files as immutable. Regenerate historical data through archive/snapshot tooling; never edit or delete archive files directly.
- **Exploratory Scope**: Archive backtests are exploratory only: terminal player, club, fixture, and availability metadata may not represent the pre-deadline information set.
- **Eval target**: `--eval_target realized|process|blend` (blend = 50/50 Blended Eval Target, ADR 0044). Promotion primary is blend; Realized Points + Process Points stay reported guardrails. Champion Signed Bias gate migrates to blend at next window; current companion still Realized.

---

## Example Execution Commands

```bash
# Run exploratory backtest against historical processed season data
uv run python -m commands.backtest participation_state_hybrid --gw_range 1-38 --data_dir data/archive/2025-26/processed

# Same window scored vs Process Points (finish-luck reduced on goals/assists)
uv run python -m commands.backtest calibrated_matchup_hybrid --gw_range 1-38 --data_dir data/archive/2025-26/processed --seed_season 2024-25 --eval_target process

# Same window scored vs 50/50 Blended Eval Target (promotion primary; ADR 0044)
uv run python -m commands.backtest calibrated_matchup_hybrid --gw_range 1-38 --data_dir data/archive/2025-26/processed --seed_season 2024-25 --eval_target blend
```
