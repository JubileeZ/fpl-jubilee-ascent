# Task: azg harness SubagentStart strip

**Objective:** Apply alpha-zero-g spawn-budget fix (drop SubagentStart double-count) + lean hook refresh.

**Acceptance:**
- [x] `.agents/hooks.json` has no `SubagentStart`
- [x] PreToolUse / SubagentStop / SessionStart lifecycle present

## Work Packet (SFDBN)

- **Status:** Done — Checkpoint now
- **Files:** `.agents/hooks.json` · spawn-budget · checkpoint/commit-gate · Cursor stop/commit-verify · AGENTS managed · `checkpoint-scan.sh`
- **Decisions:** Full `azg apply` from local alpha-zero-g (not hand-edit only)
- **Blocked:** None
- **Next:** Push needs AUTH; prior GKP optional RQI follow-up still optional

## Todo
- [x] azg apply
- [x] Confirm SubagentStart gone
- [x] Checkpoint commit
