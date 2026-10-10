# Active Task: harness-hooks-upgrade

- **Status:** In Progress
- **Objective:** Apply azg safety hook update to allow project skills and rules (ADR 0024)
- **Acceptance:** `bash tests/verify.sh` passes; block-destructive-ops allows .agents/skills/ and .cursor/rules/
- **Issue/Ticket:** ADR 0024 / alpha-zero-g apply

## Work Packet (SFDBN)

- **Status:** In Progress
- **Files:** .agents/hooks/block-destructive-ops.sh, AGENTS.md, .cursor/hooks/block-destructive-ops.sh
- **Decisions:** azg apply from alpha-zero-g
- **Blocked:** None
- **Next:** Run tests/verify.sh and commit

## Todo
- [x] azg apply ADR 0024 (allow project skills and rules in safety hook)
- [ ] Verify harness integrity via tests/verify.sh

## Blockers / Notes
- None
