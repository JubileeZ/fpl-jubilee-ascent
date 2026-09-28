# Point-in-time backtest features, statistical promotion gate, sealed holdout

**Amended by ADR 0049**: bootstrap bar 0.95 → 0.60 (both promotion seasons); minimum effect 1% → none (delta > 0).

Archive `players.parquet` holds season-end values; backtests without Availability Snapshot now build as-of metadata: price (`now_cost`) and club from each player's last pre-target performance row (first recorded row when none), and season-total / availability / set-piece-order columns (`TERMINAL_PLAYER_COLUMNS`) dropped; any as-of build caps history at `as_of_gw` (no whole-season fallback when deadline missing). Live projections unchanged.

Historical Promotion Gate primary stays Blended `top_11_regret` (amends ADR 0044 wording; Eval canon Blended MAE line was wrong). Pass now also needs combined delta ≥ 1% of Champion regret, circular block-bootstrap (3-GW blocks, 20k draws, seed 0) P(delta > 0) ≥ 0.95 on per-GW paired regret deltas, and guardrails within tolerance: xMins / Realized / Process MAE ≤ Champion × 1.01, |bias| ≤ Champion + 0.01, Spearman ≥ Champion − 0.005. Segment majority (≥2/3) unchanged.

2026-27 GW6+ sealed holdout: no tuning, smoke, or ablation touches it; one gate run per Candidate after 2025-26 selection frozen; every run logged in Candidate Ledger. 2025-26 = development season. **Amended by ADR 0047**: promotion = PASS 2025-26 + 2024-25 confirmation; holdout = post-promotion check.

**Considered Options**: iid GW bootstrap — rejected (ignores GW autocorrelation); Diebold-Mariano with HLN correction — deferred (bootstrap already paired, no normality assumption); White Reality Check / SPA across smoke variants — deferred (needs all variant loss series stored); constrained valid-XI regret — deferred (product-aligned but new metric needs its own validation); 2024-25 second gate season — deferred (no 2023-24 seed, no defcon column, no deadlines); FPL-Core-Insights availability history — deferred (single-maintainer source, snapshot timing unverified).
