# Operational First-Half Plan (research playbook)

**Objective:** Record locked GW1–19 user playbook as sibling research topic: same pre-WC 15, First-Half WC4 rebuild, BB1+WC4+FH12+TC17, bank-state FT hurdles, frozen XI (no greedy FT CSV).

**Acceptance:** `operational_summary.csv` `frozen_19gw_xi_xp` is path identity. Note + exporter + CSVs under `docs/research/gw1-19-operational-plan/` and `data/research/gw1-19-operational-plan/`. INDEX / CONTEXT / current-state point at it. Tests cover frozen 15s vs First-Half WC4 IDs and no Tavernier after WC.

## Seams (TDD)

- `docs.research.gw1-19-operational-plan.export_operational_plan` — frozen 15 XI CSVs
- `tests/test_operational_first_half_plan.py` — identity, squad match, hurdle table

## Work Packet (SFDBN)

- **Status:** Implemented. Ready to commit.
- **Files:** `docs/research/gw1-19-operational-plan/*`; `data/research/gw1-19-operational-plan/*`; `tests/test_operational_first_half_plan.py`; `docs/research/INDEX.md`; `CONTEXT.md`; `docs/agents/current-state.md`; sibling Related pointers; `task.md`
- **Decisions:** New topic (not overwrite Canonical or First-Half). Bank-state FT hurdles. FH12 15 rebuild at deadline. Identity `frozen_19gw_xi_xp`.
- **Blocked:** none
- **Next:**
  - [x] Export frozen XI CSVs
  - [x] Research note + INDEX + glossary term
  - [x] Tests
  - [ ] User: copy pre-WC 15 into FPL app before GW1 deadline
