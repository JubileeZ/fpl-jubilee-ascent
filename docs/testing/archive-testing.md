# Historical Archive Testing Guide

**Updated**: 2026-09-25T22:20:00+07:00  
**Status**: Active  

---

## Historical Archive Testing Rules

- `data/archive/<season>/processed/` contains historical season data for exploratory backtests, regression testing, and model comparison.
- CLI model names: [docs/model_name.md](../model_name.md).
- **Immutability Rule**: Treat `data/archive/` Parquet files as immutable. Regenerate historical data through archive/snapshot tooling; never edit or delete archive files directly.
- **Exploratory Scope**: Archive backtests are exploratory only: terminal player, club, fixture, and availability metadata may not represent the pre-deadline information set.
- **Point-in-time guard (ADR 0046)**: as-of builds without snapshot take price/club from pre-target performance rows and drop `TERMINAL_PLAYER_COLUMNS` (`features/builder.py`). Residual terminal inputs: club strength (GW1 only), fixture FDR, player universe (all season players listed from GW1). Guard tests: `tests/test_feature_leakage.py`.
- **Holdout & Gating (ADR 0046, 0047, 0064, 0066)**: 2025-26 = development season; 2024-25 = confirmation season (warm-seeded with 2023-24 archive under ADR 0064; registered in immutable attempt registry under ADR 0066); 2026-27 GW6+ sealed holdout (strictly protected; no backtests, tuning, or exploration).
- **Promotion Primary (ADR 0066)**: Actual native-season net FPL points under independent 6-GW rolling Strategic transfer plan replay from neutral GW1 ownership anchor. Paired non-wrapping Moving Block Bootstrap ($L=5$) with search-wide family-wise error control ($\text{FWER} \le 0.05$ via Bonferroni/Holm).
- **Eval target**: `--eval_target realized|process|blend` (blend = 50/50 Blended Eval Target, ADR 0044). Retained as an exploratory and diagnostic screen; does not grant promotion.
- **Scientific Verdicts & Adoption (ADR 0066)**: Four-way verdicts (`pass`, `fail`, `inconclusive`, `invalid`). Inconclusive routes to fresh confirmation; execution defects stop as invalid. Adoption requires verified empirical evidence, finalized registered confirmation, exact approved bundle hash and expected Champion; commands in [operator workflow](operator-workflow.md). Bonferroni implemented with fixed attempt budget; sequential Holm unsupported. Empirical calibration/approval remains required; infrastructure tests do not establish the FWER target.
- **Eval canon**: [docs/research/INDEX.md](../research/INDEX.md) **Eval canon** — promotion primary vs diagnostic targets vs Event Component gap (`mse_share`). Component-gap runner: `docs/research/champion-component-gap/runner.py`.

---

## Example Execution Commands

```bash
# Run exploratory single-gameweek backtest against historical processed season data
uv run python -m commands.backtest participation_state_hybrid --gw_range 1-38 --data_dir data/archive/2025-26/processed

# Diagnostic evaluation scored vs 50/50 Blended Eval Target (ADR 0044, ADR 0066 diagnostic)
uv run python -m commands.backtest calibrated_matchup_hybrid --gw_range 1-38 --data_dir data/archive/2025-26/processed --seed_season 2024-25 --eval_target blend

# Event Component gap companion (mse_share + twins)
uv run python docs/research/champion-component-gap/runner.py

# Final recommendation from retained admitted rolling replay evidence (ADR 0066)
uv run python -m commands.evaluate_model_promotion --evidence_request data/reports/my-evaluation/request.json

# Manual Champion adoption from verified evidence bundle (ADR 0066)
uv run python -m commands.evaluate_model_promotion --adopt <bundle_path> --approval_ref "RFC-2026-10-29" --expected_champion <champion> --bundle_hash <approved_hash>
```
