# Task: GW1–5 chip simulation sanity + continuity

**Objective:** Validate GW1–5 chip strategy research sim; fix TC / formation / ITB / XI-aware objective; refresh artifacts; Checkpoint with continuity docs.

**Acceptance:**
- [x] Review sim vs chip-strategy note and projections; identify TC miss, stacked-bench inflation, narrative-only price section
- [x] Patch `run_simulation.py`: force TC Haaland, formation-safe XI, £0.5m ITB, XI-aware MILP (select+start)
- [x] Re-run; refresh CSV + research note Findings
- [x] Self-check in runner; ruff on runner
- [x] Update Work Packet SFDBN + current-state + session-handoff; Checkpoint

**Open (prior packet, unchanged):**
- [ ] Map Expected Role Table → Participation State priors (follow-up)

## Work Packet (SFDBN)

**Status:** GW1–5 chip sim patched and re-run. TC Haaland fires GW3; GW1–3 holds £0.5m ITB; XI-aware objective makes Standard cheap-bench vs BB stacked-bench. Continuity docs updated for Checkpoint.

**Files:**
- `docs/research/gw1-5-chip-simulation/run_simulation.py`
- `docs/research/gw1-5-chip-simulation/gw1-5-chip-simulation.md`
- `data/research/gw1-5-chip-simulation/gw1-5_chip_simulation.csv`
- `task.md`
- `docs/agents/current-state.md`
- `.agents/session-handoff.md`

**Decisions:** Prefer BB1 or BB2 then WC4 on Softmax GW1–5 projections (BB1 345.64, BB2 342.50, Standard 324.03). Enforce £0.5m ITB GW1–3. Research milp ≠ open-fpl-solver; price rises remain qualitative. Expected Role → Participation State wiring still deferred.

**Blocked:** None for this packet. Price-rise dynamics and FT path GW1–3 not in sim.

**Next:** Map Expected Role Table → Participation State priors with availability guard; recheck `watch` / injury overlays before GW1; optional sim extensions (price velocity, FT path) only if drafting needs them.
