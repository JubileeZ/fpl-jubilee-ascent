# Planning Horizon cap is 10

`--horizon 10` was clamped to 6 with no warning, so Transfer Plans stopped at Start+5. Cap is now 10 (End ≤ min(Start+9, 38)); default length stays 6. Trade-off: longer MILP vs fixture-run planning. Full-Season Window stays 38.

**Status:** Accepted. Supersedes ADR 0021 max-length-6 clause only.

**Considered:** Cap 38; keep 6; default 10. Rejected: 38 is Full-Season / too large for MILP; 6 blocked the CLI the README already showed; default 10 would change Explorer/solve without an opt-in.
