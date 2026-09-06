# Completed Club Fixtures; state shrink 1; Prior-Season Seed is not the live pin

Live `element_summary` rows with 0 minutes before full-time were treated as Did Not Play, Full-Season Explorer built history as-of GW1 (empty), and the latest archive folder was the live pin — so two 90-minute starts could show ~28 xMins. Club Fixtures are finished fixtures only. Incomplete History Rows are not Recorded DNP. This-Season Evidence needs a finished row. Prior-Season Seed is the latest completed Season Archive, never the live pin. Participation State shrink strength is 1; Event Rate shrink stays 4.

**Status:** Accepted. Amends ADR 0022 (missing-history-is-not-DNP now includes Incomplete History Rows) and ADR 0024 (This-Season Evidence is finished rows; Sunday pre-kickoff 0 is not DNP). Full-Season Explorer still exports GW1–38 fixtures; history cutoff is finished rows, not GW1.

**Considered:** xMins = 90 with no shrink after two starts; strength 4 kept; include live 0s as DNP; latest archive folder including live pin. Rejected: two 90s should move toward 90 without dropping the pool; rate shrink was not the bug; Sunday not-played-yet is not DNP; live pin is this season, not prior.

**Consequences:** Ownership Explorer and `run_model` pass `history_before_gw=39` so finished Saturday rows in the live Gameweek count. Backtest/walk-forward keep deadline `history_before_target`. João Pedro-style two finished 90s vs this-season FWD £7.7m land ~72 xMins, not 27.9.
