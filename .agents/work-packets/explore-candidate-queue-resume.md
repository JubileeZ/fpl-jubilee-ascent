# Active Task: explore-candidate Queue mode resumability

- **Status:** In Progress
- **Objective:** `/explore-candidate docs/research/component-model-ideas/idea_queue.csv` survives quota/chat death: resume same packet, no lost smoke work, no second confirm look, no status without ledger row
- **Acceptance:** `tests/test_explore_candidate_smoke.py` green (skip-done variants, incremental rows, confirm guard scans all `candidate_gate.csv`); SKILL.md Queue slug/Bind/in-progress/ledger-timing/resume rules; ruff + pytest + verify.sh pass
- **Issue/Ticket:** audit 2026-09-29 (explore-candidate Queue mode)

## Work Packet (SFDBN)

- **Status:** Done; review fixes applied (Champion-leak exit 2 + cancel queued; main-loop tests; stale-Champion rows; evidence order; AGENTS.md scratch exception)
- **Files:** `.agents/skills/explore-candidate/smoke.py`, `.agents/skills/explore-candidate/SKILL.md`, `tests/test_explore_candidate_smoke.py`, `docs/research/component-model-ideas/idea_queue.csv`
- **Decisions:** smoke.py appends each row as variant finishes; skips variants already in `--out` for same season/champion/gw_range; confirm guard scans every `docs/{research,archive}/*/candidate_gate.csv`. Invoking skill with same args = Bind (AGENTS.md satisfied)
- **Blocked:** none
- **Next:** user deletes this packet manually (safety hook blocks agent `git rm` under `.agents`)

## Todo
- [x] smoke.py skip-done + incremental write (TDD)
- [x] smoke.py confirm guard global scan (TDD)
- [x] SKILL.md resume/Bind/slug/in-progress/ledger timing
- [x] Code review + checks
- [ ] Delete packet (follow-up Checkpoint, manual)
