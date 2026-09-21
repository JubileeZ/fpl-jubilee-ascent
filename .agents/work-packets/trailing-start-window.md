# Active Task: Trailing Start Window

- **Status:** In Progress — product default shipped; Rate Recency Candidate deferred
- **Objective:** Fix Club Fixture xMins under-trust after trailing Starts (Konsa-class) without Role.
- **Acceptance:** Default Feature Contract \(K=3,w=0.9\); Q6 scenarios; 2025-26 minutes MAE improves; ADR 0035 + glossary; tests green.
- **Issue/Ticket:** Grill session (no GitHub issue)

## Work Packet (SFDBN)

- **Status:** Trailing Start Window default on. Eval A/B done. Docs ADR 0035.
- **Files:** `features/builder.py`, `backtesting/walkforward.py`, `tests/test_trailing_start_window.py`, `docs/adr/0035-trailing-start-window.md`, `CONTEXT.md`, `docs/agents/current-state.md`, README / data_dictionary / ADR status lines
- **Decisions:** Data-only; \(K=3\); any non-Start breaks; blend \(w=0.90\); no global prior/recency retune; state only; ship Feature Contract after 2025-26 minutes MAE win (accept small xP MAE / minutes-bias trade).
- **Blocked:** none
- **Next:** Separate packet — Rate Recency Candidate grill (Event Rate decay / coach-tactics hypothesis)

## Todo

- [x] Grill Q1–Q14
- [x] Implement Trailing Start Window + unit tests
- [x] Walk-forward A/B 2025-26 + 2026-27 sanity
- [x] Enable Feature Contract default; ADR 0035; glossary
- [x] Verify lint/tests; update remaining docs
- [ ] Deferred: Rate Recency Candidate (new packet)

## Blockers / Notes

- Live Explorer needs Open/Refresh re-project to see new xMins.
- Opt-out: `trailing_start_k=0` on `build_features` / walkforward.
