# FPL-Jubilee-Ascent
---

## Project Identity

FPL score projection and optimization engine. Ingests FPL API data, evaluates models using backtesting, and generates transfer plans via MILP. Weekly product = local dashboard (Explorer + Transfer Plan Surface). CLI for ingest, models, research, and advanced solve flags.

**Stack:** Python 3.14 · uv · pandas · pyarrow · highspy · pytest · playwright

**Monorepo:** no

---

## Repo Structure

```
clients/       # FPL API and auth clients
models/        # Custom scoring models (convention-based auto-discovery)
features/      # FeatureContract builder + Season Archive helpers
projections/   # ProjectionContract exporter + Explorer slice + Expected GW Score
solver/        # Vendored open-fpl-solver + planning/scenarios
backtesting/   # Backtest evaluation engine and metrics
commands/      # CLI + dashboard/scenarios entry points
dashboard/     # Explorer + Transfer Plan Surface (commands.dashboard)
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
| `uv run python -m commands.streamlit_planner` | Alternate launcher for complete Streamlit dashboard @ `http://127.0.0.1:8501`; same app as `commands.dashboard`. Deployment preparation: `docs/product/streamlit-planner-deployment.md`; single manager/process; no deployment performed |
| `uv run pytest` | Run test suite |
| `bash tests/verify.sh` | Run delivery gate check |
| `uv run python -m commands.refresh_data` | Ingest live FPL; pin Official-only Live Season Pin; print hash changed/unchanged; never git commit |
| `uv run python -m commands.dashboard` | Streamlit dashboard @ `http://127.0.0.1:8000`: Explorer (Watchlist & Dream Team), Research, Model Methodology. Public deployment ready without credentials. Shared heavy-job queue. Apple utility design (ADR 0060). |
| `uv run python -m commands.solve` | CLI Transfer Plan MILP → `data/solution.json`. Default single-arm no-hit (weekly_hit_limit=0) gap 0.0 with deterministic digest caching; `--scenarios` for 3 arms; `--allow-hits` to permit hits; `--force` to re-solve |
| `uv run python -m commands.snapshot_season --season 2024-25 --from-vaastav-dir <csv-dir>` | Frozen reconstruct of 2024-25 Season Archive only |
| `uv run python -m commands.snapshot_season --season 2024-25 --from-raw-dir <raw>` | Process local FPL raw JSON into `data/archive/<season>/processed` |
| `uv run python -m commands.transfer_plan_walkforward` | First-Half Transfer Plan Walk-Forward; blocked summary without 2024-25 seed; MILP ranking when seed exists |
| `uv run python -m commands.measure_champion_bias` | Champion signed bias vs Realized Points; writes `docs/research/champion-signed-bias-2025-26/champion_bias_summary.csv` |

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

- CLI projection model names: [docs/model_name.md](docs/model_name.md). Champion = `config/model_selection.json`.
- **MUST** read [docs/testing/archive-testing.md](docs/testing/archive-testing.md) before performing backtesting or historical data exploration.
- **MUST** read [docs/research/INDEX.md](docs/research/INDEX.md) for active research index, **Eval canon**, and layout conventions.
- **MUST** read [Candidate Ledger](docs/research/candidate-ledger/candidate-ledger.md) before new Candidate lever. Hard rule: Dead lever never retried before `revisit_after` (evidence + 1 year), no exceptions without user's explicit words. Log every attempt in `candidate_ledger.csv`.
- Candidate / Champion search: `explore-candidate` skill (`.agents/skills/explore-candidate/`; AFK `/goal`, Human Queue, harness `smoke.py`).
- Live research topic = `docs/research/<topic-slug>/` (note, runners, and companion CSV/HTML in that folder).
- Archive a topic by moving the whole folder to `docs/archive/<topic-slug>/`. Companions travel with it.
- `data/archive/` = season ingest (`YYYY-YY`) only. `data/reports/` = solver/tool outputs. Session scratch = `.tmp/agent/` (delete before finish; exception: `.tmp/agent/explore-candidate/` = resume state, kept until explore-candidate Exit (a)/(b)).
- Research boundary: Research topics (`docs/research/`) strictly bounded to scoring models, projection math, statistical evaluation, and optimization/strategy. UI, UX, and frontend dashboard architecture are product/engineering specs, never research topics in `docs/research/`.
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
- Authenticated squad ingestion: Never ask user for manager ID or manual squad list in chat. Read `.env` credentials (`FPL_EMAIL` and `FPL_PASSWORD`) via `uv run python -m commands.refresh_data` to execute Playwright login via password Enter key, cache `data/session_token.json`, and populate `data/processed/user_picks.parquet`. If auth fails, report missing `.env` credentials. User Squad is not written to Season Archive / Live Season Pin.

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

- Safety-hook deny: explain block; give exact manual command/content; leave hook unchanged (do not execute blocked action). Never emit multi-line heredocs (`cat << 'EOF'`); use single-line commands or write payload to temporary scratch files.
- Work Packets only in `.agents/`: `.agents/work-packets/` contains only `*.md` Work Packets; code files, scripts, or executables in `work-packets/` strictly forbidden. Project skills under `.agents/skills/` may contain skill assets and scripts.

---

## Domain Vocabulary

- Ambiguous domain terms: follow `docs/agents/domain.md` (read `CONTEXT.md` / `CONTEXT-MAP.md` + relevant ADRs; use glossary/ADR terms only).
- Glossary/ADR writes: `/grill-with-docs` (uses `/domain-modeling`) after a term is resolved — domain concepts only; glossary-only; lazy create/update per that skill.

---

## Work State & Checkpoints

- Tracker: `docs/agents/issue-tracker.md`. Updates/compaction/archive/cleanup: `docs/agents/progress.md`.
- Autonomous progress & push: user prompt asking to update progress and commit/push authorizes full cycle: update packet/docs, run `bash tests/verify.sh`, commit, and `git push`.
- Code commits: stage a Work Packet under `.agents/work-packets/` with code — `commit-gate` enforces. Finished packet: delete the file in the same Checkpoint. Trivial: minimal packet OK.
- Handoff / device switch / leave-for-other-agent: write Packet ID to `.agents/handoff-pointer` and commit the packet. Other device: pull, then Bind that Packet ID.
- Cleanup when task complete: delete `implementation_plan.md` / `walkthrough.md`; **delete** the packet file (do not empty). Next task: new packet from `.agents/work-packet.md.tmpl`. Durable state stays in ROADMAP / current-state / git.
<!-- AZG:MANAGED:END -->

<!-- antislop:start -->
## antislop
For UI, copy, people, mobile layout, or code comments work, read these installed skill files directly (use these paths even if a same-named global skill exists):
- Core filter, always on: `antislop`: `.agents/skills/antislop/SKILL.md`
- UI / visual: `antislop-ui`: `.agents/skills/antislop-ui/SKILL.md`
- Copy & text: `antislop-copywriting`: `.agents/skills/antislop-copywriting/SKILL.md`
- People: `antislop-human`: `.agents/skills/antislop-human/SKILL.md`
- Code comments: `antislop-code`: `.agents/skills/antislop-code/SKILL.md`
Before starting, follow the core's "Two Usage Modes" section in strict order: explicit session instruction first, then global preference, then ask. A session instruction always wins. For a resolved mode, say `antislop active: <mode> (session override).` or `antislop active: <mode> (global preference).` once before presenting findings or making edits, using the actual mode and source. Acknowledging the user's request without naming the source does not replace this notice.
Only an explicit choice of antislop during or after selects a session mode. A request to review, audit, or avoid file edits does not select a mode; read the global preference in that case. Another skill's mode does not select antislop's mode.
If the mode is unresolved, ask during/after and end the response; wait for the answer before any UI review, planning, or concept. For read-only tasks, put the active-mode notice only at the start of the final answer, never in progress messages. For editing tasks, announce before the first edit and omit it from the final answer.
To update antislop later: `npx antislop-ai --update`, or run `npx antislop-ai` and pick Overwrite them.
<!-- antislop:end -->
