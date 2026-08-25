# Active Task: Transfer Plan Walk-Forward 2025-26 First-Half

- **Status:** In Progress
- **Objective:** Implement confirmed First-Half Transfer Plan Walk-Forward protocol (ADR 0019)
- **Acceptance:** Tests at listed seams pass; CLI refuses without 2024-25 seed; research note + companions exist
- **Issue/Ticket:** Grill protocol 2026-08-26 (no GitHub issue)

## Work Packet (SFDBN)

- **Status:** Implementing
- **Files:** `backtesting/strategy_policy.py`, `backtesting/transfer_plan_walkforward.py`, `commands/transfer_plan_walkforward.py`, `docs/adr/0019-transfer-plan-walk-forward-first-half.md`, `docs/research/tp-walkforward-gw1-19-2025-26/`
- **Decisions:** Seams below. 2024-25 live API ingest impossible; `--from-raw-dir` is ingest path. Ranking CSV blocked until that archive exists. Occupancy companion is diagnostic only.
- **Blocked:** `data/archive/2024-25/processed` absent
- **Next:** Wire MILP `solve_week` adapter (horizon 5 clip GW19, chips off, `weekly_hit_limit=0`, per-GW `price`, `minutes_prior_source=seed_state`); run OAT ranking after 2024-25 ingest

## Seams under test

1. `backtesting.strategy_policy` — tilt scores, DNP exception, Transfer Target locks, Locked Starting Shape bounds, FT bank, OAT arm catalog
2. `backtesting.transfer_plan_walkforward` — score deadline week Realized Points; require Prior-Season Seed; run arms with injected solver (no HTTP)
3. `features.builder.build_features(..., minutes_prior_source="seed_state")` — Cold-Start minutes from seed, no Expected Role Table
4. `commands.snapshot_season` — process local raw into `data/archive/<season>/processed`

## Todo
- [x] ADR 0019
- [x] Policy + walk-forward engine + tests
- [x] seed_state minutes prior
- [x] CLI + snapshot --from-raw-dir
- [x] Research note + occupancy companion
- [ ] MILP walk-forward loop once 2024-25 archive exists (horizon-5, chips off, Hits infeasible, per-GW price, seed_state features)
