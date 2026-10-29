# Blended eval target as promotion primary

**Status**: Superseded by [ADR 0066](0066-backtesting-and-promotion-foundation.md) (Blended Eval Target retained as supporting diagnostic; primary promotion metric is rolling transfer plan net score).

Backtests and the Historical Promotion Gate score Gameweek Projection against the mean of Realized Points and Process Points (50/50, all positions; ADR 0038), reducing finish luck on goals/assists without discarding official outcomes. Realized Points and Process Points stay reported guardrails; a Candidate must hold both while winning the blend. Current provisional Champion keeps status, re-evaluated on blend at next window.

**Considered Options**: position-aware weights — rejected (numbers unjustified today; position splits already guardrail-report); straight replace without guardrails — rejected (hides single-target regressions); Process-only primary — rejected (discards official scoring reality).
