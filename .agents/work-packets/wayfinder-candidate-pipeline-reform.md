# Active Task: Wayfinder Map — Candidate Pipeline Reform & ADR 0064 Baseline Alignment

- **Status:** In Progress
- **Objective:** Codify Inert Prototype domain concept in CONTEXT.md and author Wayfinder Map (`wayfinder-tickets.json` + `wayfinder-implementation-plan.md`) for candidate pipeline reform, Champion reset to `def_xg_shrink_challenger`, tiered gating (`--tier auto`), `EXT-09`/`EXT-11` fixes, and Track A/B exploration.
- **Acceptance:** `CONTEXT.md` updated with `Inert Prototype`; `docs/research/candidate-ideation/wayfinder-tickets.json` and `docs/research/candidate-ideation/wayfinder-implementation-plan.md` written and verified; `uv run ruff check .` and `uv run pytest tests/test_candidate_ledger.py` pass.
- **Issue/Ticket:** Wayfinder Map (`docs/research/candidate-ideation/wayfinder-tickets.json`)

## Work Packet (SFDBN)

- **Status:** In Progress — grill complete (Q1–Q8 settled); writing domain glossary and Wayfinder Map artifacts.
- **Files:** `CONTEXT.md`, `docs/research/candidate-ideation/wayfinder-tickets.json`, `docs/research/candidate-ideation/wayfinder-implementation-plan.md`, `.agents/work-packets/wayfinder-candidate-pipeline-reform.md`
- **Decisions:**
  1. Revert `config/model_selection.json` `champion` to `def_xg_shrink_challenger` (aligning with ADR 0064).
  2. Define `Inert Prototype` in `CONTEXT.md`; enforce `InertPrototypeError` (`INERT FAIL`, exit 2) in `smoke.py` when $\mathcal{G}_{\text{active}} = \emptyset$ or ($\max_{\mathcal{M}} |\Delta \hat{y}| < 0.01$ and `combined_delta == 0.0`); reclassify `EXT-09` and `EXT-11` from `dead` to `open`.
  3. Wire `oracle_minutes` into `backtesting/walkforward.py` + `evaluate_oracle_event_gate` into `backtesting/promotion.py` under ADR 0064 ($L=5$ MBB, £83.5m Constrained XI, $P_{\text{screen}} \ge 0.65$) and add `--tier {1,2,3,auto}` to `smoke.py`.
  4. Execute Track A 6-variant ablation of `MLComponentChallengerModel` heads and Track B 38-GW budget-enabler ideation on `def_xg_shrink_challenger`.
- **Blocked:** None
- **Next:** Execute T1–T6 in `docs/research/candidate-ideation/wayfinder-implementation-plan.md`.

## Todo
- [x] Complete 2-round grill (Q1–Q8)
- [x] Add `Inert Prototype` to `CONTEXT.md`
- [x] Write `docs/research/candidate-ideation/wayfinder-tickets.json`
- [x] Write `docs/research/candidate-ideation/wayfinder-implementation-plan.md`
- [ ] Execute Tickets T1–T6 per `docs/research/candidate-ideation/wayfinder-implementation-plan.md`

## Blockers / Notes
- None
