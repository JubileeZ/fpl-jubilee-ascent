# Two-tab dashboard: Transfer Plan and Ownership Explorer

Product UI is Transfer Plan plus Ownership Explorer. Interactive Squad Builder is not a tab. Planning Horizon is 1–5 gameweeks (default 5) from FPL `is_next`. Transfer Plan is the only 15-player surface: User Squad when present, else preseason draft. Force Keep / Force Ban attach to that week’s scoring 15. Booked Chip pins a week; Enabled Chip must be placed once in its Chip Set. Explorer ranks the Planning Horizon only and adds view-only Mix vs Mix (same size, 1–5). Model Champion and Official Fixture Difficulty remain the solver scores (ADR 0009).

**Status:** Accepted. Supersedes ADR 0008 (Squad Builder as product UI) and ADR 0017 (third tab; default horizon 6; keep Squad Builder). ADR 0011 Compare Models overlay retired; Primary Model still selects Ownership Explorer ranking.

**Considered:** Keep Squad Builder as a sandbox 15; horizon 6; lock/ban as projection edits; solver invents chips by default; Mix writes Keep/Ban; Season Window / Score Mode in product Explorer; Solio xP ingest. Rejected: sandbox 15 duplicated the plan; 6 exceeded the 1–5 product clock; deadline-passed GW is outside the horizon, not locked; chips default none enabled; Mix is an argument against the plan, not a solve input; Season Window stays research; Solio stays out (0009).

**Consequences:** `solver.planning` clamps horizon and maps Booked/Enabled/Keep/Ban. `user_chips.parquet` feeds Available Chips per Chip Set. Dashboard JSON explorer key is `planning_horizon`. Re-solve POST sends `enabled_chips`, `force_keep`, `force_ban`. Infeasible Keep/Ban or illegal chip pairing fails the solve.
