# README Markdown preview truncation

**Objective:** Cursor/VS Code Markdown preview of `README.md` renders past availability-overrides paragraph (full CLI flow through Development).

**Acceptance:** Preview after "the projection run." shows `### 3. Generate Transfer Plan (Solve MILP)`. No list-item-nested fenced code blocks in §3 / §8 Open steps / Development.

## Work Packet (SFDBN)

- **Status:** Preview-safe README rewrite done. Uncommitted. Working tree = `README.md` + this packet + continuity. `main` matches `origin/main` except this docs tree.
- **Files:** `README.md`; `task.md`; `docs/agents/current-state.md`; `.agents/session-handoff.md`
- **Decisions:** Truncation cause = unordered-list items with indented ` ``` ` fences (VS Code/Cursor preview treats rest of file as inside fence). Fix = bold labels + standalone fences. Angle-bracket CLI placeholders in fences → `MODEL_NAME` / `GWS` / `PUBLIC_ENTRY_ID` / `START-END` / `PROCESSED_DATA_DIR`. §8 numbered Open steps: blank line before nested fence. Installation numbered fences left (preview already passed them).
- **Blocked:** none
- **Next:**
  - [x] Un-nest §3 / Development fences; blank-line §8 Open fences; escape CLI placeholders in fences.
  - [ ] User: Markdown Refresh Preview / reopen `Ctrl+Shift+V`. Confirm §3 visible.
  - [ ] Commit if User asks.
