# Active Task: Typed contracts and Champion signed bias

- **Status:** Complete
- **Objective:** Workstream 2: runtime Operational Dataset + Feature/Projection Contract column checks. Workstream 3: measure Champion signed bias on 2025-26 GW1–38 (2026-27 sanity); no calibration layer.
- **Acceptance:** `process_directory` / `build_features` / projections fail on missing required columns; `code` retained in players dictionary; committed Champion bias CSV for 2025-26; pytest + ruff + verify green.
- **Issue/Ticket:** ADR 0032 later workstreams; ADR 0033

## Work Packet (SFDBN)

- **Status:** Complete
- **Files:** `features/contracts.py`, `features/processor.py`, `features/builder.py`, `backtesting/walkforward.py`, `commands/measure_champion_bias.py`, `docs/data_dictionary.md`, `docs/research/champion-signed-bias-2025-26/`
- **Decisions:** Column frozensets + `ContractError`, not pydantic/SQL. Bias report is a research topic companion (`signed_bias` column). Hash/pin unchanged. No calibration layer.
- **Blocked:** None
- **Next:** none

## Seams
- `features.contracts.require_columns` / `assert_operational_table` / `assert_feature_contract` / `assert_projection_contract`
- `process_directory` after parquet write
- `build_features` return
- `run_walkforward_backtest` after `predict`
- `commands.measure_champion_bias` writes companion CSV
- colocated `docs/research/champion-signed-bias-2025-26/runner.py`

## Todo
- Operational + Feature + Projection contracts
- Dictionary keeps Player `code`
- Champion signed-bias measurement 2025-26 + 2026-27 sanity
