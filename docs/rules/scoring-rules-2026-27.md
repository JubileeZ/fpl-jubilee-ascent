# FPL scoring rules — 2026/27

Authoritative source: Official `2026/27` FPL `bootstrap-static` (`chips`, `game_settings`, `game_config`, `element_types`, `events`) in `data/archive/2026-27/raw/bootstrap_static.json` and [Premier League — FPL](https://www.premierleague.com/en/news).

Verified: 2026-11-15 (`rules_id`: `native-2026-27-v1`).

## Rules used by scoring matrix & replay

- Minutes: 1 point up to 60 minutes; 2 points at 60 minutes or more.
- Goals: GK 10, DEF 6, MID 5, FWD 4.
- Assists: 3 points.
- Clean sheets: GK/DEF 4, MID 1, FWD 0; eligibility requires at least 60 minutes.
- Saves: 1 point per 3 goalkeeper saves.
- Penalty saves: 5 points.
- Defensive contributions: DEF 2 points at 10 CBIT; MID/FWD 2 points at 12 CBIRT; GK ineligible.
- Goals conceded: GK/DEF -1 point per 2 goals conceded.
- Penalty misses: -2 points.
- Yellow cards: -1 point.
- Red cards: -3 points.
- Own goals: -2 points.
- Bonus: 1–3 points through the match-level Bonus Points System (`bps` live tracking starts at 20 minutes and removes the `-1` tackled penalty in 2026/27 upstream; awarded bonus points remain 1–3).
- Positions: 4 player positions (`GKP`, `DEF`, `MID`, `FWD`); Assistant Manager chip inactive (`mng_*` scoring weights = 0).
- Chips: Two full sets of four chips (`wildcard`, `free_hit`, `bench_boost`, `triple_captain`) across `GW1–19` (first half) and `GW20–38` (second half); `wildcard` and `free_hit` start at `GW2`.
- Free transfers: Bank rollover cap `5` (`max_extra_free_transfers = 4`), `preserve_chip_transfers = True` across `wildcard` and `free_hit`, no GW15 AFCON 5-FT top-up.

Model treats thresholded events as probability or count-distribution expectations; never applies `floor` to fractional expected counts.
