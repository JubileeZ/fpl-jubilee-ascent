# Operational Zero-Availability Hard DNP Exception

**Status**: Accepted (2026-10-05)

Enforces immediate next-gameweek hard DNP (`p_dnp = 1.0`, `0.0` projected minutes, `0.0` projected points) in live operational runs for players with confirmed zero availability or red-flagged statuses (`status in {"i", "s", "u", "n"}` or `chance_of_playing <= 0.0`), while strictly preserving point-in-time backtest isolation (ADR 0010, ADR 0046).

## Context & Problem

ADR 0010 defined the Participation State contract and established that players with `chance_of_playing <= 0.0` for the immediate next gameweek (`is_immediate_next_gw == True`) receive a hard DNP override. To prevent post-hoc injury knowledge from contaminating historical backtest evaluations, this override was explicitly guarded by `has_availability_snapshot == True`.

In live operational environments (such as `commands.refresh_data`, `commands.dashboard`, and `commands.solve`), features are constructed from the active FPL `bootstrap-static` elements API (`as_of_gw is None`), meaning `has_availability_snapshot` is `False`. Because of this guard, red-flagged assets (injured `'i'`, suspended `'s'`, unavailable `'u'`, or ineligible to face parent club `'n'`) bypassed the hard DNP override in live runs, receiving Bayesian prior appearance minutes (20–60 minutes) and nonzero expected points.

## Decision

1. **Model Participation State Override (`models/participation_state_hybrid.py`)**:
   For the immediate next gameweek (`is_immediate_next_gw == True`):
   - In snapshot-backed runs (`has_availability_snapshot == True`): enforce hard DNP when `chance_of_playing <= 0.0` (ADR 0010).
   - In operational live runs (`has_availability_snapshot == False`): enforce hard DNP when `chance_of_playing <= 0.0` or `status.lower() in {"i", "s", "u", "n"}`.
   - When triggered, set `p_dnp = 1.0`, `p_start = 0.0`, and `p_sub_in = 0.0`, yielding `0.0` projected minutes and `0.0` projected points.

2. **Operational Feature Contract Masking (`features/builder.py`)**:
   In live operational runs (`as_of_gw is None` and `"status" in df_feat.columns`), mask `chance_of_playing` to `0.0` for all players with status in `{"i", "s", "u", "n"}`.

3. **Historical Backtest Preservation**:
   For retrospective backtests (`as_of_gw is not None`), `TERMINAL_PLAYER_COLUMNS` (including `status`) remain stripped unless an immutable point-in-time availability snapshot exists. Historical evaluations cannot leak future availability data.

## Consequences

- Live transfer plans and decision tree planner pitches zero out confirmed non-starters/injured/suspended players for the target GW.
- Backtest evaluators and promotion gates remain identical and leak-free.
