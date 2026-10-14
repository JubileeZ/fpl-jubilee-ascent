# Active Task: decoupled-projection-architecture

- **Status:** In Progress
- **Objective:** Establish decoupled minutes and event rate architecture, document Champion context & gates, and chart Wayfinder Map #159 with 6 child decision tickets.
- **Acceptance:** Research context, proposals, and prompts documented; Wayfinder Map #159 published with sub-issues #160-#165; local manifest generated; verify passes.
- **Issue/Ticket:** [#159](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/159)

## Work Packet (SFDBN)

- **Status:** In Progress
- **Files:** `docs/research/decoupled-projection-architecture/*`, `docs/agents/current-state.md`, `docs/research/INDEX.md`, `.agents/handoff-pointer`
- **Decisions:** Decouple minutes and event modeling into $M_{\text{mins}}$ and $M_{\text{events}}$; implement 3-tier gating; chart Wayfinder Map #159; resolved #160 (interfaces & dynamic resolution; validated via subagent audit with remediated bit-for-bit parity across 13 components); resolved #161 (Tier 2 Oracle Event Gate: triple join key on (player_id, gameweek_id, fixture_id), blended points target, Formation XI delta > 0, block bootstrap $P \ge 0.60$, playable pool relative bias tolerance (+0.02 pts), captaincy regret guardrail (+0.15 pts/GW); verified via prototype_oracle_gate.py and oracle_gate_demo.html); resolved #162 (Tier 1 Standalone Minutes Gate: commands/evaluate_minutes CLI, active pool MAE/RMSE primary, 3-way multiclass participation Brier score, 60+ min starter discrimination ROC-AUC/Recall/Precision, Tier 1 gate requiring Δ_MAE > 0, bootstrap P >= 0.60, Brier non-regression, starter recall tolerance; validated via subagent audit with IEEE 754 NaN guards, symmetric active pool mask, BaseMinutesModel polymorphism, point-in-time features; verified via prototype_minutes_gate.py, minutes_gate_demo.html, and 18 tests in test_decoupled_models.py); resolved #163 (rejected heuristic Open-Play vs. Set-Piece xG decomposition; official FPL API lacks Opta shot-type tags; synthetic split ruled out of scope to prevent ungrounded optimizer traps; retain Champion unified xG shrinkage K=2400 DEF, K=360 ATK); resolved #164 (calibrated LOO assist finishing with exponential decay omega=0.95^ΔGW, min 3 fixtures, active pool ratio centering, bounded [0.88, 1.15]; opponent shot-volume threat and danger xG/threat GK save intensity bounded [0.70, 1.45]; modular ablation toggles; verified via prototype_event_challenger.py, event_calibration_demo.html, and 4 unit tests).
- **Blocked:** None
- **Next:** Wayfinder Ticket #165 (Test fixtures, backward compatibility verification, and delivery gate).

## Todo
- [x] Document Champion model context and dead levers (`champion_model_context.md`)
- [x] Document backtesting and promotion gate protocol (`backtesting_and_promotion_gate_context.md`)
- [x] Formulate decoupled minutes vs event rate architecture proposal (`decoupled_minutes_event_proposal.md`)
- [x] Prepare specialized agent prompts for external ideation (`agent_prompts_for_ideation.md`)
- [x] Chart and publish Wayfinder Map #159 and 6 child decision issues (#160-#165)
- [x] Resolve Issue #160: Core interfaces & CompositeProjectionModel architecture (prototype verified, audit validated)
- [x] Resolve Issue #161: Oracle Minutes walkforward injection & Tier 2 gate (prototype verified, closed)
- [x] Resolve Issue #162: Standalone minutes evaluator CLI & Tier 1 gate
- [x] Resolve Issue #163: Open-Play vs. Set-Piece xG decomposition and Aerial Target Prior (rejected; ruled out of scope)
- [x] Resolve Issue #164: LOO Teammate Finishing Multiplier and Shot-Volume GK Saves
- [ ] Resolve Issue #165: Test fixtures, backward compatibility verification, and delivery gate

## Blockers / Notes
- Map #159 sub-issues: 5/6 (83.3%) resolved. Closed #160, #161, #162, #163, #164. Next: #165.

