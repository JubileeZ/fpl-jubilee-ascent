---
description:
alwaysApply: true
---

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
data/         # Raw API cache, season archives, solver reports, research artifacts
data/research/ # Machine-readable companions to durable research notes
docs/         # Durable project documentation and decision records
```

---

## Historical Archive Testing

- `data/archive/<season>/processed/` contains historical season data for exploratory backtests, regression testing, and model comparison.
- Example: `uv run python -m commands.backtest participation_state_hybrid --gw_range 1-38 --data_dir data/archive/2025-26/processed`.
- Archive backtests are exploratory only: terminal player, club, fixture, and availability metadata may not represent the pre-deadline information set.
- Treat `data/archive/` Parquet files as immutable. Regenerate historical data through archive/snapshot tooling; never edit or delete archive files directly.

---

## Docs & Research

- Keep durable, project-relevant documentation in `docs/`: architecture decisions in `docs/adr/`, agent operating guides in `docs/agents/`, human-readable research notes in `docs/research/<topic-slug>.md`, and topic documentation in named `docs/<topic>/` directories.
- Keep research filenames stable topic slugs; no date prefixes. Start notes by copying `docs/research/template/research-note.md`.
- Required research-note core sections: `Updated`, `Data stamp`, `Season`, `Purpose`, `Sources`, `Agent Prompt`, `Method`, `Findings`, `Decision`, and `Risks and unknowns`.
- Store machine-readable research companions under `data/research/<topic-slug>.*`; research-note header must link companion with `Artifact`. Note remains human-readable interpretation; companion remains row-level/data authority.
- `Updated` = last note revision timestamp, ISO 8601 with timezone. `Data stamp` = source or dataset freshness cutoff. Do not add duplicate `Last update` fields.
- Keep `Source synthesis` separate from `Project interpretation`; label source claims not independently validated.
- Keep `Agent Prompt` reproducible: identify inputs, refresh/recheck steps, stable output path, and scratch cleanup.
- **Active research index** — discovery only; findings stay in linked note/companion:
  - [Expected Role GW1–5](docs/research/expected-role-gw1-5.md) · [CSV companion](data/research/expected-role-gw1-5.csv)
  - [FPL 2026/27 pre-season source directory](docs/research/fpl-preseason-guide.md) · [budget GKP](docs/research/fpl-budget-goalkeepers.md) · [£5.0m DEF](docs/research/fpl-5-0m-defenders.md) · [£4.5m DEF](docs/research/fpl-4-5m-defenders.md) · [£4.0m DEF](docs/research/fpl-4-0m-defenders.md) · [£4.5m MID](docs/research/fpl-4-5m-midfielders.md) · [summer transfers](docs/research/fpl-summer-transfers.md)
  - [FPL first-half chip strategy](docs/research/fpl-first-half-chip-strategy.md)
- Keep active-index scope ≤5 topics; remove or replace superseded paths.
- Reserve `data/reports/` exclusively for automated tool/solver execution outputs (e.g. `data/reports/promotion_evidence/`).
- Keep source, commands, tests, and data in existing domain directories; do not create root-level project artifacts unless canonical repository files (`README.md`, `AGENTS.md`, `CONTEXT.md`, or `ROADMAP.md`).
- Store session-only plans, handoffs, investigations, and scratch artifacts in `.tmp/agent/`. This directory is ignored and must not contain source-of-truth project information.
- At task completion, delete all session-only artifacts, including `.tmp/agent/` contents and legacy root-level `task.md`, `implementation_plan.md`, and `walkthrough.md`.
- If work remains unfinished, record only the durable status, decision, and blocker in the issue tracker or appropriate project documentation; do not retain a handoff document as the sole record.

---

## Key Commands

| Command | What it does |
|---------|-------------|
| `uv run ruff check .` | Lint codebase |
| `uv run pytest` | Run test suite |
| `bash tests/verify.sh` | Run delivery gate check |

**Pre-commit gate:** run `uv run ruff check .`, `uv run pytest`, and
`bash tests/verify.sh` before proposing commits.

---

## Off-Limits: Never Touch Without Explicit Instruction

- `.env` and files with secrets or credentials
- Database migrations — flag, never auto-apply or auto-run
- Production configuration files
- Files marked `# DO NOT EDIT` or `# GENERATED`

---

## Project-Specific Safety Rules

- Test commands must never make real external HTTP requests; use HTTPX mocks/fixtures.
- Playwright auth flow invoked only when direct HTTP login and token paste fail. Submits sign-in form via `#password` Enter key to bypass `account.premierleague.com` tab/cookie overlay selector ambiguity.

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
- Authenticated squad ingestion: Never ask user for manager ID or manual squad list in chat. Read `.env` credentials (`FPL_EMAIL` and `FPL_PASSWORD`) via `uv run python -m commands.refresh_data` to execute Playwright login via password Enter key, cache `data/session_token.json`, and populate `data/processed/user_picks.parquet`. If auth fails, report missing `.env` credentials.

---

<!-- AZG:MANAGED:START -->
## Session start

Lean always-on only:

1. Read `task.md` Work Packet if present.
2. Read `ROADMAP.md` active phase / first unchecked item only (not archived or collapsed phases).
3. Read `docs/agents/current-state.md` Active phase + What exists / gaps when unfamiliar, or when existence may have changed.
4. Run `git log -5 --oneline` + `git status`.
5. Treat `AGENTS.md` / rules as pointer index — open linked docs only when the task needs them.
6. Do not rely on chat history.

Not always-on: full `CONTEXT.md`, `docs/agents/progress.md`, `docs/agents/issue-tracker.md`, archived ROADMAP, research notes.

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

- Ambiguous terminology? Use `domain-vocabulary` skill / rule, or read `docs/agents/domain.md`.
- New terms? Create `CONTEXT.md` at root from `docs/agents/CONTEXT.md.tmpl` to register glossary (or `/grill-with-docs`).

---

## Progress & Issues

- Progress workflow: use `progress-updates` skill / rule, or read `docs/agents/progress.md`.
- Issue tracker setup: read `docs/agents/issue-tracker.md`.
- Compaction / archive: see `docs/agents/progress.md` (Active-Phase Compaction; current-state = current truth; CONTEXT glossary-only; `docs/archive/` when-to-archive). Never archive live `CONTEXT.md` / `CONTEXT-MAP.md`; never relocate ADRs from `docs/adr/`.
- Cleanup: delete transient session files (`task.md`, `implementation_plan.md`, `walkthrough.md`) once milestone/task is complete.
<!-- AZG:MANAGED:END -->
