---
name: progress-updates
description: Record agent progress across sessions via task.md / ROADMAP / current-state, and compact or archive tracking docs. Use when finishing work, updating checklists, advancing a phase, trimming bloated ROADMAP/current-state/CONTEXT, or deciding what goes in docs/archive/.
---

# Progress updates

Do not use chat history as source of truth. Read and follow `docs/agents/progress.md`.

## When to use

- Closing a task / checking ROADMAP boxes
- Updating `current-state` after existence changes
- Phase advance → Active-Phase Compaction
- Live tracking docs bloated → compaction / archive

## Do

1. Update the right layer (task → ROADMAP → current-state) per the progress.md table.
2. Apply in-place compaction rules in progress.md (ROADMAP, current-state, CONTEXT).
3. Archive only per when-to-archive; leave a pointer in the live file.
4. Never archive live `CONTEXT.md` / `CONTEXT-MAP.md`; never relocate ADRs from `docs/adr/`.

## Don't

- Always-load `progress.md` / archive at session start (lean ritual in `AGENTS.md`)
- Bury progress in `CONTEXT.md` or `AGENTS.md`
