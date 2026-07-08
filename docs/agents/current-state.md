# Current Implementation State

Read if no prior context. `ROADMAP.md` shows target; this file shows what exists today.

**Active phase:** New-season readiness — see `ROADMAP.md` Phase 5. Tracked as GitHub issues (`JubileeZ/FPL-Jubilee-Ascent`).

## Next work — start here

Critical path (unblocks the new-season model, the reason this phase exists):

1. ~~#77 — FPL scoring matrix module~~ ✅ Done. `models/scoring_matrix.py` covers all 12 Event Components; 19 tests in `tests/test_scoring_matrix.py`.
2. ~~#84 — Component model with Prior-Season Seed~~ ✅ Done. `models/component_baseline.py` reconstructs xP via the scoring matrix; per-90 rates + `has_prior_seed` in `features/builder.py`. Backtest GW10-30 beats linear_baseline (MAE 0.99 vs 1.03, RMSE 2.04 vs 2.20, Spearman 0.698 vs 0.693).
3. ~~#85 — Cold-Start fallback + current-season blend~~ ✅ Done. Prior-season seed + Position-Price Prior fallback + appearance-based blend in `features/builder.py`; cold-start guard disables player-specific prior at GW1-4.

Next on path:
- **#83 — Long-format Feature Contract for Planning Horizon** ← start here. Fixes the GW39-42-inherit-GW38-fixture bug.

Unblocked quick wins (independent, grab anytime):
- #79 captain/vice report · #80 chip booking validation · #81 price-change tracking · #82 tuning surface

Blocked, wait for deps:
- #86 per-component fixture difficulty (#83) · #87 FDR report (#83)

Design decisions for the model are recorded in `docs/adr/0003-reconstruct-points-from-event-components.md`; vocabulary in `CONTEXT.md`.

---

## What exists

| Area | Path | Notes |
|------|------|-------|
| Project Scaffold | `AGENTS.md`, `ROADMAP.md`, `CONTEXT.md` | Configuration, roadmap, vocabulary |
| Dependencies | `pyproject.toml`, `.venv/` | Package configuration via uv |
| API Clients | `clients/fpl_api.py`, `clients/fpl_auth.py` | Inbound request handlers and JWT Playwright/tiered login |
| Data Dictionary | `docs/data_dictionary.md` | Mapping from raw API fields to flat files |
| CLI Commands | `commands/` | Scripts for refreshing, snapshotting, modeling, backtesting, solving |
| Custom Models | `models/` | Baseline linear rolling model conforming to contract |
| Features & Projections | `features/`, `projections/` | Data compilers and solver projection exporters |
| Backtesting Engine | `commands/backtest.py` | Engine for historical performance simulation |
| Vendored Solver | `solver/` | Port of open-fpl-solver modules |

---

## What does NOT exist yet (do not assume)

Phase 5 pending work remains:
- #83 long-format Feature Contract (per-GW horizon fixtures)
- #86 per-component fixture difficulty
- #87 fixture difficulty (FDR) report
- #79/#80/#81/#82 quick-win CLI/features

---

## Safe commands today

```bash
uv run pytest                                          # Run pytest
uv run ruff check .                                    # Lint code
uv run python -m commands.refresh_data                 # Ingest current gameweek data
uv run python -m commands.run_model linear_baseline    # Generate projections
uv run python -m commands.run_model component_baseline # Generate component projections
uv run python -m commands.solve --preseason --xmin_lb 0 # Optimize preseason transfers
uv run python -m commands.report                       # Print report
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
| Glossary | `CONTEXT.md` |
| Phases & checklist | `ROADMAP.md` |
| Agent rules | `AGENTS.md` |
| How to update progress | `docs/agents/progress.md` |
