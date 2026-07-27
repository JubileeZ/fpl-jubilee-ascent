# Map Player Identity Across Seasons using Permanent FPL Code

## Context

In Fantasy Premier League API, the element `id` field is a transient integer assigned sequentially each season (1 to ~600). The same player (e.g. Meslier) has `id = 339` in 2025/26 and `id = 3` in 2026/27. Matching prior-season player performance by `player_id` caused stats to be silently associated with the wrong player across seasons. The FPL API provides a permanent player identifier in the `code` field (e.g. 154561 for Raya) which remains constant across seasons.

## Decision

1. **Preserve Permanent Player Code**: Include `code` field in `players.parquet` schema across all season archives and live data processing ([features/processor.py](../../features/processor.py)).
2. **Permanent Code Lookup**: When querying Prior-Season Seed stats in [features/builder.py](../../features/builder.py), map the current player's `code` to the archive season's `id` for `_compute_player_rates`.
3. **Position Reclassification Handling**: FPL `code` is 100% 1-to-1 and permanent per real-world footballer, robust to position changes across seasons (e.g. 10 players in 2026/27 changed position between DEF, MID, and FWD, such as Marmoush, Georginio, Lewis-Skelly, Dorgu).
4. **Fallback Matching**: If `code` is unavailable in legacy datasets, fall back to matching by `(first_name, second_name)` without constraining `position_id` so position reclassifications do not break fallback resolution.

## Consequences

- 454 out of 558 current players (81.4%) match their exact prior-season historical performance rates during Cold-Start.
- 10 players with position reclassifications across seasons (e.g. MID -> FWD or DEF -> MID) retain their exact individual prior-season event rates.
- Prevents cross-season statistical corruption when element IDs shift between seasons.
- Requires `code` field in `players.parquet` Parquet schema.
