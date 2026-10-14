# Active Task: decoupled-projection-architecture

- **Status:** In Progress
- **Objective:** Establish decoupled minutes and event rate architecture, document Champion context & gates, and chart Wayfinder Map #159 with 6 child decision tickets.
- **Acceptance:** Research context, proposals, and prompts documented; Wayfinder Map #159 published with sub-issues #160-#165; local manifest generated; verify passes.
- **Issue/Ticket:** [#159](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/159)

## Work Packet (SFDBN)

- **Status:** In Progress
- **Files:** `docs/research/decoupled-projection-architecture/*`, `docs/agents/current-state.md`, `docs/research/INDEX.md`
- **Decisions:** Decouple minutes and event modeling into $M_{\text{mins}}$ and $M_{\text{events}}$; implement 3-tier gating (Tier 1 Standalone Minutes Gate, Tier 2 Oracle Minutes Event Gate, Tier 3 Integrated Gate); chart Wayfinder Map #159 with 6 child issues (#160-#165).
- **Blocked:** None
- **Next:** Implement PR 1 (core interfaces & composite model adapter #160) and PR 2 (oracle minutes walkforward & Tier 2 gate #161).

## Todo
- [x] Document Champion model context and dead levers (`champion_model_context.md`)
- [x] Document backtesting and promotion gate protocol (`backtesting_and_promotion_gate_context.md`)
- [x] Formulate decoupled minutes vs event rate architecture proposal (`decoupled_minutes_event_proposal.md`)
- [x] Prepare specialized agent prompts for external ideation (`agent_prompts_for_ideation.md`)
- [x] Chart and publish Wayfinder Map #159 and 6 child decision issues (#160-#165)
- [ ] Implement PR 1: Core interfaces & CompositeProjectionModel adapter (#160)
- [ ] Implement PR 2: Oracle Minutes walkforward injection & Tier 2 gate (#161)
- [ ] Implement PR 3: Standalone minutes evaluator CLI & Tier 1 gate (#162)
- [ ] Implement PR 4: DecomposedEventChallengerModel candidate rate engine (#163, #164)
- [ ] Verify test suite, bit-for-bit parity, and delivery gate (#165)

## Blockers / Notes
- None
