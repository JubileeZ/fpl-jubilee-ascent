# Task: Expected Role research (2026/27 mins priors)

**Objective:** Grill domain model for preseason Expected Role taxonomy, then multi-source research all Clubs/Players into a Draft-eligible starter list that seeds Participation State mins priors.

**Acceptance:**
- [x] Confirm Expected Role taxonomy (Nailed / Regular / Rotation / Cameo / Out of Contention); Draft-eligible = Nailed + Regular only
- [x] Lock Expected Role time horizon (early-season band GW1–5)
- [x] Lock numeric prior method: tier-default Expected Role Priors + per-Player overrides
- [x] Lock research coverage: XI Contention Set; Draft Shortlist = Nailed + Regular; Out of Contention as footnotes
- [x] Lock source set + consolidation rules + mandatory Role Evidence (reason + references)
- [x] Lock deliverable artifact format: Research Note + Expected Role Table (CSV/Parquet); code wiring later
- [x] Confirm shared understanding closed; produce Research Note + Expected Role Table for all 20 Clubs
- [ ] Map Expected Role Table → Participation State priors (follow-up after table lands)

## Work Packet (SFDBN)

**Status:** Research complete for current 2026-07-31 evidence stamp. 339-row Expected Role Table + all-20-Club Research Note generated; model wiring deferred.

**Files:**
- `docs/research/expected-role-gw1-5.md`
- `data/research/expected-role-gw1-5.csv`
- `CONTEXT.md`
- `docs/agents/current-state.md`
- `.agents/session-handoff.md`

**Decisions:** 20 Clubs; 339 XI Contention rows; 194 Draft-eligible (92 Nailed + 102 Regular); 98 Rotation; 47 Cameo. Every row carries reason, source labels, conflict rule, confidence, and conditional mins priors. Lacroix → Chelsea and Trafford → Leeds recorded as transfer-aware exceptions against stale API club registration.

**Blocked:** No research blocker. Participation State ingest remains follow-up; current table is fit-player role prior and not calibrated against actual minutes.

**Next:** Review Draft Shortlist; implement/map Expected Role Table → Participation State priors in follow-up task; refresh before GW1 after material transfer, friendly, injury, or press-conference evidence.
