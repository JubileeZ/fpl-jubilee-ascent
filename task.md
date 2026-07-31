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
- [x] Consolidate AGENTS.md Docs & Research rules, data/research convention, active index, and archive guidance
- [ ] Map Expected Role Table → Participation State priors (follow-up after table lands)

## Work Packet (SFDBN)

**Status:** AGENTS.md documentation-policy consolidation complete; final gates passed. Expected Role artifacts remain canonical and linked; model wiring deferred.

**Files:**
- `AGENTS.md` (consolidated Docs & Research policy + active index)
- `docs/research/expected-role-gw1-5.md` (human-readable Research Note; links canonical CSV)
- `data/research/expected-role-gw1-5.csv` (canonical row-level table)
- `CONTEXT.md`
- `docs/agents/current-state.md`
- `.agents/session-handoff.md`

**Decisions:** Docs & Research is single policy section; `data/research/<topic-slug>.*` holds machine-readable companions; research-note header links `Artifact`; Active research index limited to three topics; archive immutability rules live under Historical Archive Testing. Expected Role artifact remains 339 rows: 193 fit-role Draft-eligible (90 Nailed + 103 Regular), 99 Rotation, 47 Cameo; current availability overlay unchanged.

**Blocked:** No research blocker. Participation State ingest/availability guard remains follow-up; current `p_*` fields are fit-player role priors and not unconditional current-GW probabilities.

**Next:** Use only `draft_availability=eligible` for current Draft; recheck `watch` rows before final selection; implement/map Expected Role Table → Participation State priors with availability guard; refresh before GW1 after material transfer, friendly, injury, or press-conference evidence.
