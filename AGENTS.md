# FPL-Jubilee-Ascent
# Read by all AI agents working in this repo.
---

## Project Identity

FPL score projection and optimization engine. Ingests FPL API data, evaluates models using backtesting, and generates transfer plans via MILP. Consumed via CLI commands.

**Stack:** Python 3.14 · uv · pandas · pyarrow · sasoptpy · highspy · pytest · playwright

**Monorepo:** no

---

## Repo Structure

```
clients/      # FPL API and auth clients
models/       # Custom scoring models (convention-based auto-discovery)
features/     # FeatureContract builder (raw to feature dataframe)
projections/  # ProjectionContract exporter (features to solver CSV)
solver/       # Vendored open-fpl-solver source
backtesting/  # Backtest evaluation engine and metrics
commands/     # CLI command entry points
data/         # Transient raw API cache, season archives, solver reports
docs/         # Context vocabulary and data dictionary
```

---

## Key Commands

| Command | What it does |
|---------|-------------|
| `uv run ruff check .` | Lint codebase |
| `uv run pytest` | Run test suite |
| `bash tests/verify.sh` | Run delivery gate check |
| `uv run python -m commands.fetch_solio` | Ingest and cross-check Solio market projections |

**Pre-commit gate:** run `bash tests/verify.sh` before proposing commits.

---

## Off-Limits: Never Touch Without Explicit Instruction

- `.env` and files with secrets or credentials
- Database migrations — flag, never auto-apply or auto-run
- Production configuration files
- Files marked `# DO NOT EDIT` or `# GENERATED`
- `data/archive/` (modify historical files via snapshot script only)

---

## Project-Specific Safety Rules

- Test commands must never make real external HTTP requests; use HTTPX mocks/fixtures.
- Playwright auth flow invoked only when direct HTTP login and token paste fail.
- Never delete archive Parquet files outside destructive operations.

---

## Code Conventions

- All CLI commands runnable as modules (e.g., `uv run python -m commands.refresh_data`).
- Models adhere to `BaseModel` abstract class contract.
- Use explicit type annotations for all new Python code.

---

## Agent Behavior Overrides

- Doc edits telegraphic: no articles, no filler, concise fragments.
- ponytail: Python 3.14 and uv pre-approved stack requirements.
- ponytail: Prefer single line expressions when possible; avoid unnecessary abstractions.

---

<!-- AZG:MANAGED:START -->
## Session start

1. Read `docs/agents/current-state.md` (if unfamiliar with repo state).
2. Read `ROADMAP.md` (first unchecked item in active phase).
3. Read `task.md` Work Packet / open issues (if present).
4. Run `git log -5 --oneline` + `git status` (to sync history).
5. Do not rely on chat history.

Before Checkpoint (git commit of in-progress work): update Work Packet SFDBN fields in `task.md`.

---

## Universal Safety Rules

- No secrets/tokens/credentials in any file.
- Destructive ops (delete/overwrite/truncate/drop): inline `# DESTRUCTIVE: <reason>`.
- No new top-level dependencies without flagging in response.
- Agent harness device changes: implement scalably for current/future devices and new repos.
- Prefer reversible actions. If irreversible, state clearly before executing.
- Tool blocked by safety hook? Explain block, suggest exact command/content to write manually.
- Windows: run CLI/hooks only inside Git Bash.

---

## Domain Vocabulary

- Ambiguous terminology? Read `docs/agents/domain.md`.
- New terms? Create `CONTEXT.md` at root from `docs/agents/CONTEXT.md.tmpl` to register glossary.

---

## Progress & Issues

- Progress workflow: read `docs/agents/progress.md`.
- Issue tracker setup: read `docs/agents/issue-tracker.md`.
- Compaction: collapse completed phase checklists in `ROADMAP.md` to a single header/summary line (Active-Phase Compaction).
- Cleanup: delete transient session files (`task.md`, `implementation_plan.md`, `walkthrough.md`) once milestone/task is complete.
<!-- AZG:MANAGED:END -->
