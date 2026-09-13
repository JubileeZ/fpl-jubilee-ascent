# Transfer Plan Start binds to open deadline; Explorer retains live start

When Gameweek deadline passes (`is_current=True`, `finished=False`), transfers for live Gameweek are locked. Executable Transfer Plan (`commands.solve`) must start from upcoming open deadline (`is_next=True`), not live week. Ownership Explorer (`commands.dashboard`) retains ability to view and slice from earliest unfinished Gameweek for in-play player evaluation and Dream Team overlay. Unified CLI resolver `resolve_default_target_gw` in `solver/planning.py` synchronizes `run_model`, `solve`, and `report`.

**Status:** Accepted. Clarifies and bounds solver clause in ADR 0021.

**Considered:** Lock Transfer Plan to earliest unfinished and zero-out transfers; force Ownership Explorer to drop live week; keep independent CLI fallbacks. Rejected: zeroing live transfers wastes a horizon step; Explorer needs in-play view; independent fallbacks caused silent zero-padding divergence between `run_model` (GW5) and `solve` (GW4).

**Consequences:** `commands.solve` and `commands.run_model` default to `is_next` (or earliest unfinished if `is_next` absent). `commands.report` accepts `--target_gw` and strictly validates requested points columns. `projections.exporter.pad_solver_csv_horizon` warns on injected zeroes.
