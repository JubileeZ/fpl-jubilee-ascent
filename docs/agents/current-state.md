# Current Implementation State

Read if no prior context. `ROADMAP.md` = target. This file = what exists today. Historical dumps → `docs/archive/` (`docs/agents/progress.md`).

**Current phase:** Phases 1–5 complete. Season 2026/27 operations + research. Tracked implementation issues closed (`JubileeZ/FPL-Jubilee-Ascent`).

## Next work — start here

Wayfinder map [Transfer Plan dashboard spec](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/88). **Must+Should Transfer Plan Surface implemented** (ADR 0034). Differentials Ranking + Top-10k EO product shipped (Refresh → EO crawl → Explorer panel; Δ£ observed column). Fog / unticketed Later remain. Bind `.agents/work-packets/transfer-plan-dashboard-spec.md`. Research: `docs/research/wayfinder-transfer-plan-spec/`. Glossary: Differentials Ranking, Effective Ownership.

## Research truth

Live index: `docs/research/INDEX.md`. Companions live in topic folders. Production minutes/rates = Club Fixture shrinkage + Trailing Start Window (ADR 0035). Production difficulty = **Modified FDR** (difficulty only). Fixture xP scale = **Calibrated Matchup Share** when this-season Official club xG exists (ADR 0040); else Club Strength; else neutral ×1.0 (ADR 0037). Champion = `calibrated_matchup_hybrid` (ADR 0041). Research ranking = **DCS**. Dual-Vector Strength not in production Python.

## What exists

| Area | Path | Notes |
|------|------|-------|
| Scaffold | `AGENTS.md`, `ROADMAP.md`, `CONTEXT.md` | Config, phases, glossary |
| Deps | `pyproject.toml`, `.venv/` | uv |
| Clients | `clients/` | FPL API + Playwright/JWT auth |
| Data dictionary | `docs/data_dictionary.md` | API → parquet |
| CLI | `commands/` | Refresh, snapshot, model, backtest, FDR, solve, dashboard, bias |
| Models | `models/`, `docs/model_name.md` | Catalog `name`. Champion in `config/model_selection.json` |
| Features / projections | `features/`, `projections/` | Typed contracts; Explorer slice; Role retired; Trailing Start Window default (ADR 0035); Calibrated Matchup Share overlay (`features/matchup_share.py`, ADR 0040); Official processed heals from Live Season Pin on resolve (ADR 0036) |
| Dashboard | `dashboard/`, `commands/dashboard.py` | Explorer + Transfer Plan Surface peer tabs. `http://127.0.0.1:8000`. IPv4 bind. Refresh / Dream Team / Solve scenarios exclusive |
| README | `README.md` | How to use + CLI |
| Backtesting | `backtesting/` | Walk-forward, Decision Regret, Transfer Plan Walk-Forward |
| Solver | `solver/` | open-fpl-solver `2ff829f` highspy; `planning.py` + `transfer_plan.py` + `scenarios.py` ours |
| Research | `docs/research/`, `docs/archive/` | Live INDEX + topics. `data/archive/` = Season Archive pins |

## What does NOT exist yet (do not assume)

- `availability-snapshots` branch missing on `origin`. Capture workflow kept. Promotion provisional until two Live Validation Windows.
- Snapshot-backed nonzero-chance calibration not implemented; opt-in model applies next-GW `0%` hard DNP only.
- Transfer-plan regret deferred until one-Gameweek Decision Regret passes holdout. First-Half Walk-Forward ranking exists as research companion.

## Safe commands today

```bash
uv run pytest
uv run ruff check .
uv run python -m commands.refresh_data
uv run python -m commands.run_model calibrated_matchup_hybrid
uv run python -m commands.dashboard
uv run python -m commands.solve --preseason --xmin_lb 0
uv run python -m commands.measure_champion_bias
uv run python -m commands.transfer_plan_walkforward
```

Catalog names and more recipes: `README.md` (weekly dashboard path first), `docs/model_name.md`.

## Agent pitfalls

- Playwright Chromium required for `refresh_data` / `snapshot_season` when `FPL_TOKEN` unset.
- Windows console cp1252; commands call `configure_utf8_stdio()` before non-ASCII prints.
- pytest `pythonpath = ["."]`; do not drop it.
- Tests use `sys.executable`, not `.venv/bin/python`.
- Transfer Plan Scenarios need User Squad; plan JSON is `data/transfer_plan_scenarios.json`, not `dashboard_data.json`.

## Doc map

Index: `docs/README.md`. Weekly path / Key Commands: `README.md`, `AGENTS.md`.
