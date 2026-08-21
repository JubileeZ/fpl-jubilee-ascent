# Agent Progress Updates

How agents record progress so next agent/device continues without chat history.

---

## Three layers

| Layer | File | Update when | Purpose |
|-------|------|-------------|---------|
| **1 — Task** | GitHub Issue / `.agents/work-packets/<packet-id>.md` | Start / finish focused chunk | Scope, blockers, commit links |
| **2 — Phase checklist** | `ROADMAP.md` | Roadmapped bullet **done** | `- [ ]` → `- [x]` on matching line |
| **3 — Reality snapshot** | `docs/agents/current-state.md` | Moved planned → exists | Shows what exists on disk |

Do not use chat history as source of truth. Commit doc updates in same commit as the code.

---

## Workflow per work session

```mermaid
flowchart LR
    Start["Read current-state.md"] --> Issue["Pick / create task or issue"]
    Issue --> Work["Implement + test + lint"]
    Work --> Roadmap["Check ROADMAP box if bullet done"]
    Roadmap --> State["Update current-state.md if exists-table changed"]
    State --> Close["Close task or issue with summary"]
```

### 1. Start
Follow Session start in `AGENTS.md` (once per session). Then pick or create task/issue.

### 2. During work
- Comment on task/issue if blocked or scope changes.
- Do not check ROADMAP boxes for partial work.

### 2b. Device Handoff (user-triggered)
- Handoff write: only when user asks (handoff / device switch / leave-for-other-agent).
- Canonical: bound Work Packet + `.agents/handoff-pointer` (Packet ID only). Commit with work.
- Day-to-day same device: bound packet + `current-state.md`.
- Do not write `.agents/session-handoff.md` (retired duplicate SFDBN).

### 3. Before finishing (pre-commit gate)
- Run `uv run ruff check .`, `uv run pytest`, and `bash tests/verify.sh`.
- Move no session artifacts into project documentation. Delete `.tmp/agent/` contents and `implementation_plan.md` / `walkthrough.md` when done. Finished Work Packet: **delete** the file (do not empty).

### 4. On completion — update docs
| If you… | Then update… |
|---------|----------------|
| Finished a `ROADMAP.md` bullet | `- [x]` that bullet only |
| Added file/dir listed in "does NOT exist" | Move row to **What exists**; remove from "does NOT exist" |
| Changed architecture (hard to reverse) | New ADR in `docs/adr/` |
| Resolved new domain term | `CONTEXT.md` glossary entry |
| Advanced to next phase | `current-state.md` **Active phase** + `ROADMAP.md` status line; collapse completed phase checklist in `ROADMAP.md` to single summary line (Active-Phase Compaction). |

---

## What NOT to update on every small change
| File | When to touch |
|------|----------------|
| `CONTEXT.md` | New/clarified domain terms only |
| `docs/deployment.md` | Production deployment guides only |
| `AGENTS.md` | New commands, safety rules, structure changes |

---

## Compaction (in place)

Keep live tracking docs small. Prefer rewrite in place.

1. **ROADMAP — Active-Phase Compaction.** Phase done → collapse checklist to one header/summary line. Only active phase expanded.
2. **current-state = current truth only.** What exists / gaps **today**. Drop stale narrative; move historical dumps to archive (leave one-line pointer).
3. **CONTEXT = glossary only.** Terms + definitions. No implementation progress, phase history, or design dumps.

ADRs stay in `docs/adr/`. Supersede via status — do not move into archive.

---

## Archive (`docs/archive/`)

Historical detail off the live path, still in git.

**Layout**

- Multi-file: `docs/archive/<kebab-slug>/` (optional `index.md`)
- Single file: `docs/archive/<kebab-slug>.md`
- Optional date: `docs/archive/<YYYY-MM-DD>-<kebab-slug>.md` or dated folder

Create `docs/archive/` lazily on first dump. After moving detail, leave pointer in live file.

**When to archive**

- Completed phase checklist too long for one-line ROADMAP summary, detail still useful
- Superseded design / research dumps no longer current truth
- Long narrative removed from `current-state` so file stays a snapshot

**Never archive**

- Live `CONTEXT.md` / `CONTEXT-MAP.md` — trim in place at root
- ADRs — keep under `docs/adr/`; mark superseded / accepted

Archive is not always-on. Open only when task needs historical detail.

---

## Multi-device sync
- **Syncs via Git:** Code, docs (`ROADMAP.md`, `current-state.md`, ADRs), issues.
- **Does not sync:** `.tmp/agent/` session plans, handoffs, scratch artifacts, local build caches, local `.env`.

Pull before starting. Read `current-state.md` after pull — not previous chat.

---

## Checklist for agents (copy mentally)
- [ ] Lean always-on ritual followed (`AGENTS.md`)
- [ ] Task/issue created or referenced
- [ ] Tests + lint pass
- [ ] `ROADMAP.md` checkbox(es) updated
- [ ] `current-state.md` updated if existence table changed
- [ ] Compaction / archive applied if phase advanced or live docs bloated
- [ ] Task closed with summary
