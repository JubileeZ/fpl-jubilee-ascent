# FPL-Jubilee-Ascent
---

## Project Identity

FPL score projection and optimization engine. Ingests FPL API data, evaluates models using backtesting, and generates transfer plans via MILP. Consumed via CLI commands.

**Stack:** Python 3.14 · uv · pandas · pyarrow · sasoptpy · highspy · pytest · playwright

**Monorepo:** no

---

## Repo Structure

```
clients/       # FPL API and auth clients
models/        # Custom scoring models (convention-based auto-discovery)
features/      # FeatureContract builder + Expected Role Prior ingest
projections/   # ProjectionContract exporter + Ownership Explorer slice metrics
solver/        # Vendored open-fpl-solver source
backtesting/   # Backtest evaluation engine and metrics
commands/      # CLI command entry points
dashboard/     # Ownership Explorer (served by commands.dashboard)
config/        # Model Champion selection
tests/         # pytest suite
data/          # Raw API cache, season snapshots, solver reports
data/archive/  # Season ingest only (`YYYY-YY`)
docs/research/ # Live research: INDEX, template, topic folders (notes + companions)
docs/archive/  # Archived research topics (notes + companions colocated)
docs/          # Durable project documentation and decision records
.agents/       # Session handoff and agent skills
```

---

## Key Commands

| Command | What it does |
|---------|-------------|
| `uv run ruff check .` | Lint codebase |
| `uv run pytest` | Run test suite |
| `bash tests/verify.sh` | Run delivery gate check |
| `uv run python -m commands.dashboard` | Serve Ownership Explorer; Refresh in page ingest+project |
| `uv run python -m commands.snapshot_season --season 2024-25 --from-vaastav-dir <csv-dir>` | Map vaastav FPL CSVs into `data/archive/2024-25/processed` |
| `uv run python -m commands.snapshot_season --season 2024-25 --from-raw-dir <raw>` | Process local FPL raw JSON into `data/archive/<season>/processed` |
| `uv run python -m commands.transfer_plan_walkforward` | First-Half Transfer Plan Walk-Forward; blocked summary without 2024-25 seed; MILP ranking when seed exists |

**Commit readiness:** run `uv run ruff check .`, `uv run pytest`, and `bash tests/verify.sh` before proposing commits.

---

## Safety Rules

- Never commit, print, or paste secret values (from `.env`, credentials, tokens, or chat). App code may read env vars; do not exfiltrate their values.
- Database migrations — flag, never auto-apply or auto-run.
- Production configuration files — do not edit without explicit authorization.
- Test commands must never make real external HTTP requests; use HTTPX mocks/fixtures.
- Playwright auth flow invoked only when direct HTTP login and token paste fail. Submits sign-in form via `#password` Enter key to bypass `account.premierleague.com` tab/cookie overlay selector ambiguity.

---

## Docs & Research

- **MUST** read [docs/testing/archive-testing.md](docs/testing/archive-testing.md) before performing backtesting or historical data exploration.
- **MUST** read [docs/research/INDEX.md](docs/research/INDEX.md) for active research index and layout conventions.
- Live research topic = `docs/research/<topic-slug>/` (note, runners, and companion CSV/HTML in that folder).
- Archive a topic by moving the whole folder to `docs/archive/<topic-slug>/`. Companions travel with it.
- `data/archive/` = season ingest (`YYYY-YY`) only. `data/reports/` = solver/tool outputs. Session scratch = `.tmp/agent/` (delete before finish).
- Metric documentation: every custom or domain metric in the note with Definition/Formula, Direction (Higher $\uparrow$ / Lower $\downarrow$), Ideal Benchmark.
- Research figures are caches of named companion CSV cells. Topic runner writes the companion in the topic folder, then regenerates note caches. Agent Prompts name artifact path + column (e.g. `gw1-6_wc4_summary.csv` `total_6gw_xp`), not a numeric snapshot.

---

## Code Conventions

- All CLI commands runnable as modules (e.g., `uv run python -m commands.refresh_data`).
- Models adhere to `BaseModel` abstract class contract.
- Use explicit type annotations for all new Python code.
- Doc edits telegraphic: no articles, no filler, concise fragments.
- ponytail: Python 3.14 and uv pre-approved stack requirements.
- ponytail: Prefer single line expressions when possible; avoid unnecessary abstractions.
- Authenticated squad ingestion: Never ask user for manager ID or manual squad list in chat. Read `.env` credentials (`FPL_EMAIL` and `FPL_PASSWORD`) via `uv run python -m commands.refresh_data` to execute Playwright login via password Enter key, cache `data/session_token.json`, and populate `data/processed/user_picks.parquet`. If auth fails, report missing `.env` credentials.

---

<!-- AZG:MANAGED:START -->
## Placeholder fill

`<!-- AGENT: ... -->` in agent/tracking docs (e.g. `AGENTS.md`, `ROADMAP.md`, `docs/agents/*`):
1. Ask fill or skip; skip → leave comment exact.
2. One section at a time; ≤3 options, recommended first.
3. Done → drop resolved comments + inapplicable sections; telegraphic prose.

---

## Session start

Once per session (not every turn). Continuity from listed files (chat ≠ continuity):

1. `current-state.md` (reality).
2. `ROADMAP.md` active phase / first unchecked only.
3. `git status` + `git log -5 --oneline` before edit.
4. Other docs JIT via pointers.

Do not read Work Packet bodies at start. **Independent Request** (no change asked): no packet I/O.

**Bind** only when the user says continue / handoff / a Packet ID, or asks to continue and `.agents/handoff-pointer` names one. Change asked with no bind: attended — ask new vs which open slug (≤3); unattended — create `.agents/work-packets/<slug>.md` from `.agents/work-packet.md.tmpl`. Never auto-bind the last leftover packet.

Session start done when: `current-state` + ROADMAP slice + git status/log. Bound packet read only after Bind.

Missing required continuity doc: restore from git if history exists; else ask user.

During work / before Checkpoint: update tracking docs when state changes
(see `docs/agents/progress.md`). Before Checkpoint: refresh bound packet SFDBN, or delete the packet if finished.

JIT (read when task needs): full `CONTEXT.md`, `progress.md`, `issue-tracker.md`, archived ROADMAP, research notes.

---

## Harness Safety

- Safety-hook deny: explain the block; give exact manual command/content; leave hook unchanged (do not execute the blocked action).

---

## Domain Vocabulary

- Ambiguous domain terms: follow `docs/agents/domain.md` (read `CONTEXT.md` / `CONTEXT-MAP.md` + relevant ADRs; use glossary/ADR terms only).
- Glossary/ADR writes: `/grill-with-docs` (uses `/domain-modeling`) after a term is resolved — domain concepts only; glossary-only; lazy create/update per that skill.

---

## Work State & Checkpoints

- Tracker: `docs/agents/issue-tracker.md`. Updates/compaction/archive/cleanup: `docs/agents/progress.md`.
- Code commits: stage a Work Packet under `.agents/work-packets/` with code — `commit-gate` enforces. Finished packet: delete the file in the same Checkpoint. Trivial: minimal packet OK.
- Handoff / device switch / leave-for-other-agent: write Packet ID to `.agents/handoff-pointer` and commit the packet. Other device: pull, then Bind that Packet ID.
- Cleanup when task complete: delete `implementation_plan.md` / `walkthrough.md`; **delete** the packet file (do not empty). Next task: new packet from `.agents/work-packet.md.tmpl`. Durable state stays in ROADMAP / current-state / git.
<!-- AZG:MANAGED:END -->
