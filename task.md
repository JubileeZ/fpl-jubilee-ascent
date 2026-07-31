# Task: Expected Role research (2026/27 mins priors)

**Objective:** Grill domain model for preseason Expected Role taxonomy, then multi-source research all Clubs/Players into a Draft-eligible starter list that seeds Participation State mins priors.

**Acceptance:**
- [x] Confirm Expected Role taxonomy (Nailed / Regular / Rotation / Cameo / Out of Contention); Draft-eligible = Nailed + Regular only
- [ ] Lock Expected Role time horizon (GW1 vs early-season band vs full season)
- [ ] Lock output schema (P(Start), mins if Start, P(Sub-in), mins if Sub-in) + source consolidation rules
- [ ] Multi-source research note + per-Club Draft-eligible starter list
- [ ] Map Expected Role defaults → Participation State priors for mins projection

## Work Packet (SFDBN)

**Status:** Grilling in progress. Q1 confirmed; Expected Role glossary written to `CONTEXT.md`. Awaiting Q2 (horizon).

**Files:**
- `CONTEXT.md` (Expected Role + five role terms)
- `docs/agents/current-state.md` (continuity)
- `.agents/session-handoff.md` (continuity)
- `task.md` (this packet)

**Decisions:**
- Canonical term = Expected Role (not first-team / importance / lineup status)
- Five values: Nailed Starter, Regular Starter, Rotation, Cameo, Out of Contention
- Draft-eligible = Nailed Starter + Regular Starter only
- Expected Role seeds Participation State priors; does not replace Participation State
- Source seed: [fpl.page GW1 predicted lineups](https://fpl.page/article/fpl-gw1-predicted-lineups-2627); more sources TBD after grill

**Blocked:** Shared understanding incomplete — horizon, output schema, consolidation rules still open.

**Next:** User answers Q2 (horizon). Continue grill one question at a time; do not start full research until grill closes.
