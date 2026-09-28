# Active Task: Multi-feature assist Candidate + two-season promotion gate

- **Status:** In Progress
- **Objective:** Ship `multi_feature_assist_challenger` Candidate; adopt ADR 0047 two-season gate; run 2024-25 confirmation; promote only on PASS.
- **Acceptance:** ruff + pytest + verify green; 2024-25 gate verdict logged in Candidate Ledger; PASS → Champion + promotion ADR; FAIL → Champion unchanged, ledger Dead.
- **Issue/Ticket:** explore-candidate 2026-09-28 (user idea: multi-feature event rates)

## Work Packet (SFDBN)

- **Status:** Candidate built + dev gate PASS; ADR 0047 written pre-run; 2024-25 gate pending.
- **Files:** `models/multi_feature_assist_challenger.py`, `tests/test_multi_feature_assist_challenger.py`, `docs/research/multi-feature-event-rate/`, `docs/adr/0047-two-season-promotion-gate.md`, ledger, INDEX, `config/model_selection.json`
- **Decisions:** assists-only GLM (xA target, λ 10); slate replaces `defence_link_challenger` (user); ADR 0047 protocol (user).
- **Blocked:** none
- **Next:** run 2024-25 dry gate (scratch config) → PASS: reorder slate, `--apply` on 2024-25.

## Todo
- [x] Candidate + tests + catalog
- [x] ADR 0047
- [ ] 2024-25 gate
- [ ] Promote or log fail

## Blockers / Notes
- None
