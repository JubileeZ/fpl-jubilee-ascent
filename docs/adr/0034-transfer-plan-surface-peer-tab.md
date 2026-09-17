# Transfer Plan Surface is a peer dashboard tab

Product UI is Ownership Explorer **and** Transfer Plan Surface as peer tabs (prototype variant A). Transfer Plan remains the MILP result object (`commands.solve` → `data/solution.json`); Transfer Plan Surface is the view that ranks Transfer Plan Scenarios (Roll / 1 FT / Optimal) by horizon sum of Expected GW Score. Read-only plan XI; does not load into Squad What-If. Squad What-If and Dream Team stay on Ownership Explorer only. Supersedes ADR 0021 / ADR 0027 “Transfer Plan stays CLI, not a tab” for product UI. ADR 0021 Planning Horizon Start–End, Dashboard Refresh, and Primary Model for Explorer still stand. Must+Should UI implements this boundary.

**Status:** Accepted. Implemented.

**Considered:** Keep Transfer Plan CLI-only (ADR 0021/0027); plan-dock beside Explorer (prototype B); scenario-stack document without peer tab (prototype C); load plan into Squad What-If; replace Dream Team with the plan. Rejected: CLI-only hides Must ranked scenarios; dock/stack lost as Must layout; What-If is a sandbox, not the plan; Dream Team is a frozen guide 15, not a transfer sequence.

**Consequences:** Glossary splits Transfer Plan (object) vs Transfer Plan Surface (view). Dashboard Data Contract stays Explorer-facing; plan JSON stays separate. ADR 0018 two-tab history is not restored wholesale — peer tabs return with Scenario ranking and Expected GW Score, not the old tab’s behavior.
