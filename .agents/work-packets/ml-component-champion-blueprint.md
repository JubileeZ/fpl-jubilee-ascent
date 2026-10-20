# Active Task: ml-component-champion-blueprint

- **Objective:** Design, mathematically specify, and document the complete zero-leakage ML Component Champion Model Candidate (`ml_component_challenger`) with decoupled $M_{\text{mins}}$ and $M_{\text{events}}$ architecture, two-track ML benchmark, and 3-tier gating protocol without altering production model code.
- **Acceptance:** Full implementation blueprint written to `docs/research/ml-component-champion-blueprint/ml-component-champion-blueprint.md`, registered in `docs/research/INDEX.md`, `CONTEXT.md` updated with new domain terms, research layout and suite tests passing, and ready for future execution.
- **Issue/Ticket:** [Decoupled Minutes & Event Architecture Map #159](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/159)

## Work Packet (SFDBN)

- **Status:** In Progress
- **Files:** `CONTEXT.md`, `docs/research/INDEX.md`, `docs/research/ml-component-champion-blueprint/ml-component-champion-blueprint.md`, `docs/agents/current-state.md`
- **Decisions:** Decoupled 3-head $M_{\text{mins}}$ + 4-group $M_{\text{events}}$ architecture; 5 rare/discipline components frozen at Champion priors; Track 1 (Ridge/Spline) vs Track 2 (GBDT) benchmark; offset residual learning on Empirical Bayes priors; single expanding-window `models/ml_panel_features.py` with in-memory club ID reconstruction, strictly lagged $g-1$ market features, zero file reads, and no terminal columns; sequential ablation ladder across Tier 1, Tier 2, and Tier 3 gates.
- **Blocked:** None
- **Next:** When authorized to implement, execute Step 1 (`models/ml_panel_features.py` and `tests/test_ml_panel_leakage.py`) following the Agent Prompt in `docs/research/ml-component-champion-blueprint/ml-component-champion-blueprint.md`.

## Todo
- [x] Grilling Round 1: Architecture, scope, model family, residual learning, ledger policy, deliverable format
- [x] Grilling Round 2: Zero-leakage causal panel builder, 3-head $M_{\text{mins}}$ spec, 4-group $M_{\text{events}}$ spec, cold-start fallback & sequential ablation ladder
- [x] Write comprehensive, self-contained implementation blueprint to `docs/research/ml-component-champion-blueprint/ml-component-champion-blueprint.md`
- [x] Update `CONTEXT.md` with resolved domain terms and index note in `docs/research/INDEX.md`
- [ ] Phase 1: Implement `models/ml_panel_features.py` and unit tests in `tests/test_ml_panel_leakage.py`
- [ ] Phase 2: Implement and evaluate $M_{\text{mins}}$ heads on Tier 1 Standalone Minutes Gate
- [ ] Phase 3: Implement and evaluate $M_{\text{events}}$ heads on Tier 2 Standalone Oracle Event Gate
- [ ] Phase 4: Greedy forward stack into `models/ml_component_challenger.py` and run Tier 3 Integrated Promotion Gate (`dev` + `confirm`)

## Blockers / Notes
- None
