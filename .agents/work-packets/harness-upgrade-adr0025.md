# Active Task: harness-upgrade-adr0025

- **Status:** In Progress
- **Objective:** Upgrade to Alpha-Zero-G ADR 0025 packet lifecycle gates
- **Acceptance:** verify.sh passes with updated commit-scan, commit-gate, and verify gate
- **Issue/Ticket:** None

## Work Packet (SFDBN)

- **Status:** In Progress
- **Files:** .agents/hooks/commit-gate.sh, .agents/hooks/commit-scan.sh, .cursor/hooks/commit-verify.sh, tests/verify.sh
- **Decisions:** Adopt ADR 0025 upstream lifecycle fixes
- **Blocked:** None
- **Next:** Complete and clean up packet

## Todo
- [x] Run azg apply
- [x] Verify harness tests pass
