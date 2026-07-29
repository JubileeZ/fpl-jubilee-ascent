# Current Implementation State

Read if no prior context. `ROADMAP.md` shows target; this file shows what exists today.

**Current phase:** New-season readiness complete — see `ROADMAP.md` Phase 5. All tracked implementation issues are closed (`JubileeZ/FPL-Jubilee-Ascent`).

## Next work — start here

Critical path (unblocks the new-season model, the reason this phase exists):

1. ~~#77 — FPL scoring matrix module~~ ✅ Done. `models/scoring_matrix.py` covers all 13 Event Components, including 2025/26 defensive contributions; tests in `tests/test_scoring_matrix.py`.
2. ~~#84 — Component model with Prior-Season Seed~~ ✅ Done. `models/component_baseline.py` reconstructs xP via the scoring matrix; `has_prior_seed`, `has_fallback_prior`, and `has_seed` distinguish seed sources in `features/builder.py`.
3. ~~#85 — Cold-Start fallback + current-season blend~~ ✅ Done. Prior-season seed + Position-Price Prior fallback + appearance-based blend in `features/builder.py`; cold-start guard disables player-specific prior at GW1-4.

Next on path:
- Maintenance, real-data validation, and future model improvements.

Unblocked quick wins (independent, grab anytime):
- None; #79/#80/#81/#82 complete locally.

Blocked, wait for deps:
- None.

Design decisions recorded in `docs/adr/0003-reconstruct-points-from-event-components.md`, `docs/adr/0004-cross-season-player-code-mapping.md`, `docs/adr/0005-hybrid-metrics-component-projection-model.md`, `docs/adr/0006-fixture-first-projection-contract.md`, and `docs/adr/0010-participation-state-snapshots-and-evaluation.md`; vocabulary in `CONTEXT.md`.

Recent Session Updates:
- **RoleScore transfer overlay (29 Jul eve):** `docs/research/20260729-pl-starter-rolescore.md` — Welbeck→CHE medical → Georginio (Rutter) preferred BHA #9 (Ext R lean, RS 75.2); Welbeck CHE = B starts; Trafford terms agreed.
- **Scoring Matrix Realignment**: Corrected `_GOAL_POINTS` per position (GK=10, Defender=6, Midfielder=5, Forward=4), added defensive-contribution points, and retained official negative-event penalties in `models/scoring_matrix.py`.
- **Fixture-First Contract**: `features/builder.py` emits one row per player/fixture across the planning horizon; `projections/exporter.py` aggregates double-gameweeks for solver CSVs.
- **Hybrid Metrics Component Model (`metrics_component_hybrid`)**: Uses separate fixture attack/defence effects, rolling pre-cutoff attack-weight calibration, Poisson count expectations, direct Defcon expected points, and competitor-aware bonus allocation.
- **Backtesting Metrics**: `backtesting/metrics.py` reports forecast error, signed bias, rank validity, position strata, and shortlist overlap/regret.
- **Component Attribution Harness**: Updated `backtesting/metrics.py`, `models/metrics_component_hybrid.py`, `models/component_baseline.py`, and `commands/backtest.py` with per-component prediction export (`xp_minutes`, `xp_goals`, `xp_assists`, `xp_clean_sheet`, `xp_conceded`, `xp_defcon`, `xp_bonus`), component metrics evaluation, and `--component_breakdown` CLI reporting.
- **Backtest Archive Fallback**: `commands/backtest.py` selects the newest processed season archive when active performance history is unavailable.
- **Fixture Difficulty Report**: `commands/fdr_report.py` reads processed fixtures, preserves double gameweeks, and prints/exports a sortable club-by-horizon FDR matrix.
- **Captain/Vice Report**: `commands.report` prints next-gameweek recommendations and exports role columns.
- **Chip Validation**: `commands.solve` rejects duplicate, conflicting, and out-of-horizon booked chips before solver preparation.
- **Price History**: `commands.refresh_data` appends UTC price snapshots; `commands.price_report` reports refresh and season changes.
- **Tuning Surface**: `commands.run_model` exposes blend thresholds; `commands.solve` exposes horizon, decay, hit-cost, and validated overrides.
- **ADR 0005 Recorded**: Updated [`docs/adr/0005-hybrid-metrics-component-projection-model.md`](../../docs/adr/0005-hybrid-metrics-component-projection-model.md) to match shipped behavior.
- **Solio Pipeline Deprecated & Removed (ADR 0009)**: Audited and removed Solio market ingestion pipeline (`commands/fetch_solio.py`), feature merge in `features/builder.py`, and GitHub Action workflow (`.github/workflows/fetch_solio.yml`) due to top-N payload truncation and mathematical xMins inversion saturation. Retained local 2-State Empirical Bayes Mixture Model for minute estimations.
- **Participation State Model**: `participation_state_hybrid` is provisionally operational default; `metrics_component_hybrid` remains its Candidate. Archive-only results may support provisional promotion; verified snapshots support validated promotion. `commands.capture_availability_snapshot` writes immutable pre-deadline packages; `--require_snapshots` rejects missing or tampered packages for strict evaluation. Provisional status requires two four-Gameweek Live Validation Windows.
- **Image Generation Removal**: Removed PNG squad timeline visualization logic (`solver/visualization.py`, `commands/solve.py`) and deleted `data/images/` directory. Retained `matplotlib` in `pyproject.toml`.



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

---

## What does NOT exist yet (do not assume)

- Historical Availability Snapshot collection has not run yet; archive-backed promotion remains provisional until two Live Validation Windows complete.
- Committed Comparison Slate lives in `config/model_selection.json`; `commands/compare_models` and `commands.evaluate_model_promotion` implement automatic historical promotion with Promotion Evidence Records.
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
