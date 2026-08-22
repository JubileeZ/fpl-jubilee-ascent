# Current Implementation State

Read if no prior context. `ROADMAP.md` shows target; this file shows what exists today. Current truth only — historical dumps → `docs/archive/` (see `docs/agents/progress.md`).

**Current phase:** New-season readiness complete — see `ROADMAP.md` Phase 5. All tracked implementation issues are closed (`JubileeZ/FPL-Jubilee-Ascent`).

## Next work — start here

Season 2026/27 underway. Active research under `docs/research/` (`gkp-fdr-rotation-gw1-19`, `fpl-first-half-chip-strategy`). Production Expected Role Prior = `features/expected-role-gw1-5.csv`. Dashboard = live product view. Production `_fixture_maps` FDR fallback when API attack/defence = 0.

ADR 0016 ingest live: Cold-Start minutes/state = Expected Role Prior from committed table; Event Rates stay Prior-Season Seed; Appearance Blend 1→5. `refresh_data --rebuild-roles` / `--keep-roles`. Snapshot season is not table identity. Dual-Source extract written on rebuild (`lineup-signals.json`).

Design decisions: `docs/adr/0003`–`0006`, `0010`, `0013` (clauses 1–3), `0014`, `0015` (DCS), `0016` (Expected Role Prior Cold-Start minutes), `0018` (two-tab Transfer Plan + Ownership Explorer; 0008/0017 superseded). Vocabulary in `CONTEXT.md`.

## Research truth (22 Aug)

- Active research: `docs/research/` (`gkp-fdr-rotation-gw1-19`, `fpl-first-half-chip-strategy`). Live index: `docs/research/INDEX.md`.
- Production Expected Role Prior ingest: `features/expected-role-gw1-5.csv`.
- **Official Fixture Difficulty** = opponent Club Strength Vector overall at focal venue. Live API attack/defence = 0. Dual-Vector Strength (rolling npxG) not in production Python.
- Ranking metric = **DCS** (ADR 0015). RQI historical. Stage 3 keepers = MILP 15-man pick, not the DCS pair.




---

## What exists

| Area | Path | Notes |
|------|------|-------|
| Project Scaffold | `AGENTS.md`, `ROADMAP.md`, `CONTEXT.md` | Configuration, roadmap, vocabulary |
| Dependencies | `pyproject.toml`, `.venv/` | Package configuration via uv |
| API Clients | `clients/fpl_api.py`, `clients/fpl_auth.py` | Inbound request handlers and JWT Playwright/tiered login (`.env` credentials → `data/session_token.json` → `user_picks.parquet`) |
| Data Dictionary | `docs/data_dictionary.md` | Mapping from raw API fields to flat files |
| CLI Commands | `commands/` | Scripts for refreshing, snapshotting, modeling, backtesting, FDR reporting, solving |
| Custom Models | `models/` | Linear, component, hybrid, and participation-state models |
| Features & Projections | `features/`, `projections/` | Feature Contract (Expected Role Prior Cold-Start minutes + Prior-Season Seed rates), solver exporters, Ownership Explorer slice |
| Dashboard | `dashboard/`, `commands/dashboard.py` | Transfer Plan + Ownership Explorer. Transfer Plan opens first; 15 is User Squad else preseason draft. Planning Horizon 1–5 (default 5) from `is_next`. Force Keep/Ban, Booked/Enabled Chips per Chip Set, view-only Mix. Champion MILP + Official Fixture Difficulty. Full-Season Window export writes solver CSVs. Open: README §8 (`uv run python -m commands.dashboard` → `http://127.0.0.1:8000`). IPv4-only bind; `localhost` may hit `::1`. |
| README preview | `README.md` | CLI fences not nested in unordered-list items (§3 / Development). Preview must show §3 after availability-overrides paragraph. |
| Backtesting Engine | `commands/backtest.py`, `backtesting/` | Walk-forward evaluation and decision-aware metrics |
| Vendored Solver | `solver/` | Port of open-fpl-solver modules |
| Research | `docs/research/`, `docs/archive/` | Live: INDEX + template. 2026/27 preseason archived with colocated CSVs. Production Expected Role Prior from archived Stage 1 CSV. Research HTML is not the dashboard product view. `data/archive/` = season snapshots only |

---

## What does NOT exist yet (do not assume)

- Historical Availability Snapshot collection not on `origin` (`availability-snapshots` branch missing). Writer now JSON-canonicalizes nested FPL list columns (`price_change_projections`, `scout_risks`, fixture `stats`); hourly Capture Action was failing inside 48h window. Keep `.github/workflows/capture_availability_snapshot.yml` + `evaluate_model_promotion.yml`. Archive-backed promotion remains provisional until two Live Validation Windows complete.
- Committed Comparison Slate lives in `config/model_selection.json`; `commands.compare_models` and `commands.evaluate_model_promotion` implement automatic historical promotion with Promotion Evidence Records.
- Snapshot-backed nonzero-chance calibration is not implemented; the opt-in model only applies the immediate `0%` hard DNP rule.
- Transfer-plan regret remains intentionally out of scope until one-Gameweek Decision Regret passes the holdout gate.
- Dual-Source Lineup Signals JSON is written on Expected Role Rebuild; no committed `lineup-signals.json` until next `--rebuild-roles`.

---

## Safe commands today

```bash
uv run pytest                                          # Run pytest
uv run ruff check .                                    # Lint code
uv run python -m commands.refresh_data                 # Ingest current gameweek data
uv run python -m commands.refresh_data --rebuild-roles # Ingest + Expected Role Rebuild
uv run python -m commands.run_model linear_baseline    # Generate projections
uv run python -m commands.run_model component_baseline # Generate component projections
uv run python -m commands.run_model participation_state_hybrid # Operational default
uv run python -m commands.run_model metrics_component_hybrid    # Comparison baseline
uv run python -m commands.capture_availability_snapshot --season 2026-27
uv run python -m commands.compare_models --gw_range 1-38 --data_dir data/archive/2025-26/processed
uv run python -m commands.evaluate_model_promotion --apply --gw_range 1-38 --data_dir data/archive/2025-26/processed
uv run python -m commands.decision_regret --entry_id <public-entry-id>
uv run python -m commands.solve --preseason --xmin_lb 0 # Optimize preseason transfers
uv run python -m commands.report                       # Print report
uv run python -m commands.price_report                # Print price changes
uv run python -m commands.dashboard                   # Transfer Plan + Ownership Explorer
```

---

## Agent pitfalls

- Playwright Chromium binary must be installed (`uv run playwright install chromium`) to run `refresh_data`/`snapshot_season` when `FPL_TOKEN` is unset.
- Windows console is cp1252 by default; `commands.*` reconfigure stdio to UTF-8 via `clients.env_loader.configure_utf8_stdio()`. New commands that `print` non-ASCII (player names) must call it too.
- Tests rely on `tool.pytest.ini_options.pythonpath = ["."]`; don't remove it or collection breaks with `ModuleNotFoundError: No module named 'clients'`.
- Don't hardcode `.venv/bin/python` in tests — use `sys.executable` (cross-platform).

---

## Doc map

| Question | Read |
|----------|------|
| Documentation map | `docs/README.md` |
| Glossary | `CONTEXT.md` |
| Phases & checklist | `ROADMAP.md` |
| Agent rules | `AGENTS.md` |
| How to update progress | `docs/agents/progress.md` |
