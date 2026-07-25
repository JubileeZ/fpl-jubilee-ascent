# 0006: Fixture-first projection contract

## Context

FPL players can have zero, one, or multiple fixtures in a gameweek. The former
contract labelled fixture rows as gameweek rows and cloned the target fixture
through the planning horizon. That could duplicate double-gameweek outcomes and
make future weeks inherit the wrong opponent.

## Decision

Use one canonical long-format Feature and Projection Contract row per
`player_id` and `fixture_id`. Include `gameweek_id` on every row. Use `fixture_id
== -1` for a blank-gameweek player row.

Aggregate fixture projections by `(player_id, gameweek_id)` only at the solver
CSV/export and headline evaluation boundaries.

## Consequences

- Double-gameweek points and minutes add correctly.
- Each horizon gameweek carries its own opponent and home/away context.
- Fixture-level calibration and joins remain possible.
- Consumers that need solver input must use the explicit aggregation boundary.
