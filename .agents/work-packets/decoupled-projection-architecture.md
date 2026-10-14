# Active Task: decoupled-projection-architecture

- **Status:** In Progress
- **Objective:** Establish decoupled minutes and event rate architecture, document Champion context & gates, and chart Wayfinder Map #159 with 6 child decision tickets.
- **Acceptance:** Research context, proposals, and prompts documented; Wayfinder Map #159 published with sub-issues #160-#165; local manifest generated; verify passes.
- **Issue/Ticket:** [#159](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/159)

## Work Packet (SFDBN)

- **Status:** In Progress
- **Files:** `docs/research/decoupled-projection-architecture/*`, `docs/agents/current-state.md`, `docs/research/INDEX.md`, `.agents/handoff-pointer`
- **Decisions:** Decouple minutes and event modeling into $M_{\text{mins}}$ and $M_{\text{events}}$; implement 3-tier gating; chart Wayfinder Map #159; resolved #160 (interfaces & dynamic resolution; validated via subagent audit with remediated bit-for-bit parity across 13 components); resolved #161 (Tier 2 Oracle Event Gate: triple join key on (player_id, gameweek_id, fixture_id), blended points target, Formation XI delta > 0, block bootstrap $P \ge 0.60$, playable pool relative bias tolerance (+0.02 pts), captaincy regret guardrail (+0.15 pts/GW); verified via prototype_oracle_gate.py and oracle_gate_demo.html).
- **Blocked:** None
- **Next:** Wayfinder Ticket #162 (Standalone minutes evaluator CLI & Tier 1 gate).

## Todo
- [x] Document Champion model context and dead levers (`champion_model_context.md`)
- [x] Document backtesting and promotion gate protocol (`backtesting_and_promotion_gate_context.md`)
- [x] Formulate decoupled minutes vs event rate architecture proposal (`decoupled_minutes_event_proposal.md`)
- [x] Prepare specialized agent prompts for external ideation (`agent_prompts_for_ideation.md`)
- [x] Chart and publish Wayfinder Map #159 and 6 child decision issues (#160-#165)
- [x] Resolve Issue #160: Core interfaces & CompositeProjectionModel architecture (prototype verified, audit validated)
- [x] Resolve Issue #161: Oracle Minutes walkforward injection & Tier 2 gate (prototype verified, closed)
- [ ] Resolve Issue #162: Standalone minutes evaluator CLI & Tier 1 gate
- [ ] Resolve Issue #163: Open-Play vs. Set-Piece xG decomposition and Aerial Target Prior
- [ ] Resolve Issue #164: LOO Teammate Finishing Multiplier and Shot-Volume GK Saves
- [ ] Resolve Issue #165: Test fixtures, backward compatibility verification, and delivery gate

## Blockers / Notes
- Map #159 sub-issues: 2/6 (33%) resolved. Closed #160, #161. Next: #162.

