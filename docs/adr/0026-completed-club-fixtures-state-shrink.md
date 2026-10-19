# Completed Club Fixtures; state shrink 1; Prior-Season Seed is not the live pin

Live `element_summary` 0-min rows before full-time treated as Did Not Play; Full-Season Explorer built history as-of GW1 (empty); latest archive folder was live pin — two 90-min starts showed ~28 xMins. Club Fixtures: full-time fixtures only (`finished == True` or `finished_provisional == True`). Incomplete History Rows (pre-kickoff or in-play) not Recorded DNP. This-Season Evidence requires completed row. Prior-Season Seed: latest completed Season Archive, never live pin. Participation State shrink strength 1; Event Rate shrink 4.

**Status:** Accepted. Amends ADR 0022 (missing history not DNP includes Incomplete History Rows) and ADR 0024 (This-Season Evidence is completed rows; Sunday pre-kickoff 0 not DNP). Full-Season Explorer exports GW1–38 fixtures; history cutoff: completed rows, not GW1.

**Considered:** xMins = 90 with no shrink after two starts; strength 4 kept; include live 0s as DNP; latest archive folder including live pin. Rejected: two 90s should move toward 90 without dropping the pool; rate shrink was not the bug; Sunday not-played-yet is not DNP; live pin is this season, not prior.

**Consequences:** Ownership Explorer and `run_model` pass `history_before_gw=39`: completed Saturday/Sunday rows (`finished_provisional == True`) in live Gameweek count. Backtest/walk-forward keep deadline `history_before_target`. João Pedro-style two finished 90s vs this-season FWD £7.7m land ~72 xMins, not 27.9. Trailing Start Window (ADR 0035) lifts three-Start streaks after early DNP/sub.
