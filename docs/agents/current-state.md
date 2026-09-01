# Current Implementation State

Read if no prior context. `ROADMAP.md` shows target; this file shows what exists today. Current truth only — historical dumps → `docs/archive/` (see `docs/agents/progress.md`).

**Current phase:** New-season readiness complete — see `ROADMAP.md` Phase 5. All tracked implementation issues are closed (`JubileeZ/FPL-Jubilee-Ascent`).

## Next work — start here

Season 2026/27 underway. Active research under `docs/research/` (`set-piece-taker-vs-defcon`, `tp-walkforward-gw1-19-2025-26`, `def-fdr-rotation-gw1-19`, `gkp-fdr-rotation-gw1-19`, `fpl-first-half-chip-strategy`). Dashboard = live product view. Production `_fixture_maps` Modified FDR fallback when API attack/defence = 0.

ADR 0022 Feature Contract: Recency-Weighted Prior Shrinkage on current-club Club Fixtures for Participation State and Event Rates (decay 0.95, strength 4, Prior-Season Seed else Position-Price). Missing rows not DNP. Expected Role Table optional Role label; does not gate Project. No Watch/Exclude, no `xmins_cap`. `refresh_data --rebuild-roles` / `--keep-roles` still Role registry ingest. Dual-Source extract on rebuild (`lineup-signals.json`).

Design decisions: `docs/adr/0003`–`0006`, `0010`, `0013` (clauses 1–3), `0014`, `0015` (DCS), `0016` superseded for Feature Contract minutes by `0022`, `0018` Mix vs Mix (two-tab / 1–5 / `is_next` superseded by 0021), `0019` (Modified FDR production score), `0020` (Transfer Plan Walk-Forward First-Half), `0021` (Ownership Explorer dashboard; Planning Horizon Start–End max 6), `0022` (Club Fixture minutes and Event Rates). Vocabulary in `CONTEXT.md`.

## Research truth (23 Aug)

- Active research: `docs/research/` (`set-piece-taker-vs-defcon`, `tp-walkforward-gw1-19-2025-26`, `def-fdr-rotation-gw1-19`, `gkp-fdr-rotation-gw1-19`, `fpl-first-half-chip-strategy`). Live index: `docs/research/INDEX.md`. Set-piece vs Defcon SoT = `docs/research/set-piece-taker-vs-defcon/def_breakeven.csv` `net_sp_vs_high_defcon`. DEF Club Occupancy SoT = `docs/research/def-fdr-rotation-gw1-19/def_rotation_club_occupancy.csv` `rank_mod_fdr`. Walk-forward ranking: `docs/research/tp-walkforward-gw1-19-2025-26/tp_walkforward_summary.csv` `realized_points` (vaastav 2024-25 seed).
- Production Expected Role Table = optional Explorer Role label (`features/expected_roles.csv`). Feature Contract minutes/rates = Club Fixture shrinkage (ADR 0022).
- **Official Fixture Difficulty** = opponent Club Strength Vector overall at focal venue. Production xP / FDR report = **Modified FDR** (official −0.25 home / +0.25 away; ADR 0019). Live API attack/defence = 0. Dual-Vector Strength (rolling npxG) not in production Python.
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
| Features & Projections | `features/`, `projections/` | Feature Contract (Club Fixture Recency-Weighted Prior Shrinkage for minutes and Event Rates; ADR 0022). Solver exporters, Ownership Explorer slice. Expected Role Rebuild optional Role registry. |
| Dashboard | `dashboard/`, `commands/dashboard.py` | Ownership Explorer only. Planning Horizon Start–End, length 1–6, Start any unfinished GW (live week allowed). Dashboard Refresh ingest+project in page; process start does not ingest/project. View-only Mix. Assume 90 toolbar toggle (all Players). ADR 0021. Open: README §8 (`uv run python -m commands.dashboard` → `http://127.0.0.1:8000`). IPv4-only bind; `localhost` may hit `::1`. |
| README preview | `README.md` | CLI fences not nested in unordered-list items (§3 / Development). Preview must show §3 after availability-overrides paragraph. |
| Backtesting Engine | `backtesting/` | Walk-forward model eval, Decision Regret, Transfer Plan Walk-Forward policy (ADR 0020) |
| Vendored Solver | `solver/` | Port of open-fpl-solver modules |
| Research | `docs/research/`, `docs/archive/` | Live: INDEX + template. 2026/27 preseason archived with colocated CSVs. Production Expected Role Prior from `features/expected_roles.csv`. Research HTML is not the dashboard product view. `data/archive/` = season snapshots only |

---

## What does NOT exist yet (do not assume)

- Historical Availability Snapshot collection not on `origin` (`availability-snapshots` branch missing). Writer now JSON-canonicalizes nested FPL list columns (`price_change_projections`, `scout_risks`, fixture `stats`); hourly Capture Action was failing inside 48h window. Keep `.github/workflows/capture_availability_snapshot.yml` + `evaluate_model_promotion.yml`. Archive-backed promotion remains provisional until two Live Validation Windows complete.
- Committed Comparison Slate lives in `config/model_selection.json`; `commands.compare_models` and `commands.evaluate_model_promotion` implement automatic historical promotion with Promotion Evidence Records.
- Snapshot-backed nonzero-chance calibration is not implemented; the opt-in model only applies the immediate `0%` hard DNP rule.
- Transfer-plan regret remains intentionally out of scope until one-Gameweek Decision Regret passes the holdout gate. First-Half Transfer Plan Walk-Forward ranking (ADR 0020) filled: `docs/research/tp-walkforward-gw1-19-2025-26/tp_walkforward_summary.csv` `realized_points`.
- Dual-Source Lineup Signals extract is pinned at `features/lineup-signals.json` and updated via `commands.refresh_data --rebuild-roles`.

---

## Safe commands today

```bash
uv run pytest                                          # Run pytest
uv run ruff check .                                    # Lint code
uv run python -m commands.refresh_data                 # Ingest current gameweek data
uv run python -m commands.refresh_data --rebuild-roles # Ingest + Expected Role Rebuild
uv run python -m commands.run_model linear_baseline    # Generate projections
uv run python -m commands.run_model dual_vector_state_hybrid # Operational default
uv run python -m commands.run_model participation_state_hybrid # Comparison slate
uv run python -m commands.run_model metrics_component_hybrid    # Comparison baseline
uv run python -m commands.capture_availability_snapshot --season 2026-27
uv run python -m commands.compare_models --gw_range 1-38 --data_dir data/archive/2025-26/processed
uv run python -m commands.evaluate_model_promotion --apply --gw_range 1-38 --data_dir data/archive/2025-26/processed
uv run python -m commands.decision_regret --entry_id <public-entry-id>
uv run python -m commands.solve --preseason --xmin_lb 0 # Optimize preseason transfers
uv run python -m commands.report                       # Print report
uv run python -m commands.price_report                # Print price changes
uv run python -m commands.dashboard                   # Ownership Explorer; Refresh in page
uv run python -m commands.snapshot_season --season 2024-25 --from-vaastav-dir data/archive/2024-25/vaastav
uv run python -m commands.snapshot_season --season 2024-25 --from-raw-dir <raw>
uv run python -m commands.transfer_plan_walkforward  # Ranking when 2024-25 seed exists; else blocked summary
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
