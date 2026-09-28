# Active Task: explore-candidate skill

- **Status:** In Progress (closing)
- **Objective:** Project skill `explore-candidate`: AFK /goal orchestrator hunting Candidate to replace Champion via gate wins.
- **Acceptance:** Skill + `smoke.py` audit/leakage/confirm-protocol refusals verified; dev + confirm season runs end-to-end; ruff + pytest + verify.sh green.
- **Issue/Ticket:** none (user request 2026-09-28)

## Work Packet (SFDBN)

- **Status:** Skill shipped; packet deleted in follow-up Checkpoint.
- **Files:** `.agents/skills/explore-candidate/SKILL.md`, `.agents/skills/explore-candidate/smoke.py`, `AGENTS.md` pointer.
- **Decisions:** AFK default + Human Queue (config edit, `--apply`, Dead override, commit/push = human). Season roles from `data/archive` (dev = latest complete, confirm = second-latest, holdout = live). Prototypes season-agnostic (audit refuses literals).
- **Blocked:** none.
- **Next:** delete this packet.

## Todo
- [x] Skill + harness
- [x] AFK / goal run contract
- [x] Season roles resolved from archive
- [ ] Delete packet after skill commit
