# Must Transfer Plan Scenarios are Optimal vs No Hit

Must arms on the Transfer Plan Surface compare Hit policy, not Start transfer-count pins. **Optimal** keeps live Hits (`weekly_hit_limit=1`, `hit_cost=4`, no Start pin). **No Hit** sets `weekly_hit_limit=0` for the whole Transfer Plan Horizon (Free Transfers only). Always rank both by Σ Expected GW Score; never drop a feasible arm. Roll and 1 FT are retired as Must arms. CLI `commands.solve` stays Hit-allowed (same as Optimal). ADR 0033 still stands: No Hit is a compare arm, not a ban of live Hits as the sole path. Supersedes the Roll / 1 FT / Optimal arm set named in ADR 0034.

**Status:** Accepted.

**Considered:** Keep Roll / 1 FT / Optimal; rename Optimal to Unconstrained; hide No Hit when Optimal takes zero Hits; flip CLI default to `weekly_hit_limit=0`. Rejected: Start-count pins do not answer Hit-or-not; Unconstrained collides with Starting Shape research vocab; domination hide loses the compare; CLI flip would silently change single-plan solves.

**Consequences:** `solver/scenarios.py` arms = `optimal` / `no_hit`. Dashboard pending labels and product docs follow. ADR 0034 peer-tab decision unchanged; its Scenario arm list points here.
