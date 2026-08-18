# Current Implementation State

Read if no prior context. `ROADMAP.md` shows target; this file shows what exists today. Current truth only — historical dumps → `docs/archive/` (see `docs/agents/progress.md`).

**Current phase:** New-season readiness complete — see `ROADMAP.md` Phase 5. All tracked implementation issues are closed (`JubileeZ/FPL-Jubilee-Ascent`).

## Next work — start here

Maintenance, real-data validation, and future model improvements.

Design decisions: `docs/adr/0003`–`0006`, `0010`, `0013` (clauses 1–3), `0014`, `0015` (DCS). Vocabulary in `CONTEXT.md`. Dated research diary: [`docs/archive/current-state-research-log.md`](../archive/current-state-research-log.md).

## Research truth (18 Aug)

- Live chip path = Canonical Preseason Chip Path S1 **364.21 xP** (`gw1-6_wc4_summary.csv` one row).
- Ranking metric = **DCS** (ADR 0015). RQI historical.
- Stage 1/2/ownership: **575** rows, **234** Draft-eligible. API **590** players. Trafford LEE, Rushworth COV.
- GKP DCS GW1–19 #1: Rushworth+Donnarumma **127.13 xP / DCS 89.33**. Club FDR-min #1: `AVL-CHE-LIV-MCI-NFO` **2.4386**.
- Stage 3 keepers Raya+Donnarumma = MILP 15-man pick, not the DCS pair.
- Live defensive note: `docs/research/defensive-fixture-rotation/`. Archived notes: `docs/archive/gkp-fixture-rotation/`, `docs/archive/def-fixture-rotation/`. Historical CSVs: `data/archive/gkp-fixture-rotation/`, `data/archive/def-fixture-rotation/`.
- FFS Playwright recheck 2026-08-18: guide modified 2026-08-18T02:21:39Z; 15 child `modified_time` unchanged.

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
| Features & Projections | `features/`, `projections/` | Data compilers and solver projection exporters |
| Backtesting Engine | `commands/backtest.py`, `backtesting/` | Walk-forward evaluation and decision-aware metrics |
| Vendored Solver | `solver/` | Port of open-fpl-solver modules |
| Research | `docs/research/`, `data/research/` | GW1–5 roles/stats, Canonical Chip Path, DCS rotation, ownership explorer. Legacy GKP/DEF CSVs in `data/archive/` |

---

## What does NOT exist yet (do not assume)

- Historical Availability Snapshot collection has not run yet; archive-backed promotion remains provisional until two Live Validation Windows complete.
- Committed Comparison Slate lives in `config/model_selection.json`; `commands.compare_models` and `commands.evaluate_model_promotion` implement automatic historical promotion with Promotion Evidence Records.
- Snapshot-backed nonzero-chance calibration is not implemented; the opt-in model only applies the immediate `0%` hard DNP rule.
- Transfer-plan regret remains intentionally out of scope until one-Gameweek Decision Regret passes the holdout gate.

---

## Safe commands today

```bash
uv run pytest                                          # Run pytest
uv run ruff check .                                    # Lint code
uv run python -m commands.refresh_data                 # Ingest current gameweek data
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
