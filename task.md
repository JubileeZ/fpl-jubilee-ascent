# Task: GW1–5 research rebuild + chip sim

**Objective:** Rebuild expected-stats GW1–5 per grill lock; external research packages; best-guess Defcon; chip sim XI-aware (no TC); Checkpoint + push.

**Acceptance:**
- [x] Grill lock: code map, usable seasons, 50/50 blend, attack/defence mults, ParticipationStateHybridModel.predict
- [x] External research packages for Draft fallback players + CBIT/CBITR upgrades
- [x] Best-guess Defcon for 7 partial-source players (else baseline)
- [x] Chip sim: formation-safe XI, £0.5m ITB, XI-aware MILP; TC removed
- [x] Rebuild CSVs + research notes
- [x] Continuity SFDBN + Checkpoint + push

**Open (follow-up):**
- [ ] Re-run chip sim on latest projections (sim still on pre-rebuild projections)
- [ ] Map Expected Role Table → Participation State priors

## Work Packet (SFDBN)

**Status:** Expected-stats grill-lock rebuild complete. Draft Nailed/Regular: zero on fallback_baseline. Best-guess Defcon applied to Vuskovic, Amenda, Wright, Ömür, Matusiwa, Maeda, Emersonn. Chip sim TC removed; BB1 341.61 / BB2 338.47 / Standard 320.62 (pre-projection-rebuild run). Checkpoint pending this session.

**Files:**
- `docs/research/expected-stats-gw1-5/build_expected_stats.py`
- `docs/research/expected-stats-gw1-5/project_expected_points.py`
- `docs/research/expected-stats-gw1-5/expected-stats-gw1-5.md`
- `data/research/expected-stats-gw1-5/*.csv`
- `docs/research/gw1-5-chip-simulation/run_simulation.py`
- `docs/research/gw1-5-chip-simulation/gw1-5-chip-simulation.md`
- `CONTEXT.md`
- `task.md`, `docs/agents/current-state.md`, `.agents/session-handoff.md`

**Decisions:** 50/50 recency blend; external only if zero usable FPL seasons; Defcon = CBIT/CBITR/FPL or best-guess when partial data; baseline only when no evidence. Chip sim: auto-captain only, no TC. Early BB + WC4 preferred on Softmax projections.

**Blocked:** None.

**Next:** Re-run chip sim on refreshed projections; Expected Role → Participation State priors; optional Isak usable-season floor / Gyökeres source review.
