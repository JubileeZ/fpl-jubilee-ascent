# Current Implementation State

Read if no prior context. `ROADMAP.md` shows target; this file shows what exists today. Current truth only — historical dumps → `docs/archive/` (see `docs/agents/progress.md`).

**Current phase:** New-season readiness complete — see `ROADMAP.md` Phase 5. All tracked implementation issues are closed (`JubileeZ/FPL-Jubilee-Ascent`).

## Next work — start here

Season 2026/27 underway. ADR 0023–0025 in code: Official FPL Operational Dataset; This-Season Evidence shrinkage; Expected Role retired; Explorer xMins. `refresh_data` pins `data/archive/<season>/`. `--from-vaastav-dir` is 2024-25 reconstruct only. Dashboard = live product view. Production `_fixture_maps` Modified FDR fallback when API attack/defence = 0.

Design decisions: `docs/adr/0003`–`0006`, `0010`, `0013` (clauses 1–3), `0014`, `0015` (DCS), `0016` superseded (0022 minutes, 0025 Role), `0018` Mix vs Mix (two-tab / 1–5 / `is_next` superseded by 0021), `0019` (Modified FDR), `0020` (walk-forward; seed clock reopened by 0024), `0021` (Ownership Explorer; Dual-Source clause superseded by 0025), `0022` (Club Fixture minutes; in-season seed superseded by 0024), `0023`–`0025`. Vocabulary in `CONTEXT.md`.

## Research truth (4 Sep)

- Active research: `docs/research/` (`epl-arrival-xg-xa-adjustment`, `set-piece-taker-vs-defcon`, `tp-walkforward-gw1-19-2025-26`, `def-fdr-rotation-gw1-19`, `gkp-fdr-rotation-gw1-19`, `fpl-first-half-chip-strategy`). Live index: `docs/research/INDEX.md`. Arrival xG/xA SoT = `docs/research/epl-arrival-xg-xa-adjustment/arrival_xg_xa_summary.csv` `npxg_median_ratio` / `xag_median_ratio`. Set-piece vs Defcon SoT = `docs/research/set-piece-taker-vs-defcon/def_breakeven.csv` `net_sp_vs_high_defcon`. DEF Club Occupancy SoT = `docs/research/def-fdr-rotation-gw1-19/def_rotation_club_occupancy.csv` `rank_mod_fdr`. GKP rotation SoT = `docs/research/gkp-fdr-rotation-gw1-19/raya_rotation_partners.csv` `total_mod_fdr` / `gkp_rotation_pairs_summary.csv` `pct_gw_mod_le_2_25` (CHE starter Martínez; FDR ticks unchanged vs 22 Aug parquet). Walk-forward ranking: `docs/research/tp-walkforward-gw1-19-2025-26/tp_walkforward_summary.csv` `realized_points` (vaastav 2024-25 seed).
- Production Feature Contract minutes/rates = Club Fixture shrinkage; Cold-Start Prior-Season Seed; after This-Season Evidence this-season Position-Price (ADR 0024). Expected Role retired (ADR 0025).
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
| Features & Projections | `features/`, `projections/` | Feature Contract (Club Fixture Recency-Weighted Prior Shrinkage; ADR 0024 This-Season Evidence). Solver exporters, Ownership Explorer slice. Expected Role retired. |
| Dashboard | `dashboard/`, `commands/dashboard.py` | Ownership Explorer only. Planning Horizon Start–End, length 1–6, Start any unfinished GW (live week allowed). Dashboard Refresh ingest+project in page; process start does not ingest/project. View-only Mix. Assume 90. xMins column. No Role. ADR 0021 / 0025. Open: README §8 (`uv run python -m commands.dashboard` → `http://127.0.0.1:8000`). IPv4-only bind; `localhost` may hit `::1`. |
| README preview | `README.md` | CLI fences not nested in unordered-list items (§3 / Development). Preview must show §3 after availability-overrides paragraph. |
| Backtesting Engine | `backtesting/` | Walk-forward model eval, Decision Regret, Transfer Plan Walk-Forward policy (ADR 0020) |
| Vendored Solver | `solver/` | Port of open-fpl-solver modules |
| Research | `docs/research/`, `docs/archive/` | Live: INDEX + template. 2026/27 preseason archived with colocated CSVs. Research HTML is not the dashboard product view. `data/archive/` = Season Archive pins |

---

## What does NOT exist yet (do not assume)

- Historical Availability Snapshot collection not on `origin` (`availability-snapshots` branch missing). Writer now JSON-canonicalizes nested FPL list columns (`price_change_projections`, `scout_risks`, fixture `stats`); hourly Capture Action was failing inside 48h window. Keep `.github/workflows/capture_availability_snapshot.yml` + `evaluate_model_promotion.yml`. Archive-backed promotion remains provisional until two Live Validation Windows complete.
- Committed Comparison Slate lives in `config/model_selection.json`; `commands.compare_models` and `commands.evaluate_model_promotion` implement automatic historical promotion with Promotion Evidence Records.
- Snapshot-backed nonzero-chance calibration is not implemented; the opt-in model only applies the immediate `0%` hard DNP rule.
- Transfer-plan regret remains intentionally out of scope until one-Gameweek Decision Regret passes the holdout gate. First-Half Transfer Plan Walk-Forward ranking (ADR 0020) filled: `docs/research/tp-walkforward-gw1-19-2025-26/tp_walkforward_summary.csv` `realized_points`. Existing walk-forward companions used ADR 0022 in-season seed, not ADR 0024.

---

## Safe commands today

```bash
uv run pytest                                          # Run pytest
uv run ruff check .                                    # Lint code
uv run python -m commands.refresh_data                 # Ingest current gameweek data; pin Season Archive
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
