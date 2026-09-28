# Current Implementation State

Read if no prior context. `ROADMAP.md` = target. This file = what exists today. Historical dumps → `docs/archive/` (`docs/agents/progress.md`).

**Current phase:** Phases 1–5 complete. Season 2026/27 operations + research. Tracked implementation issues closed (`JubileeZ/FPL-Jubilee-Ascent`).

## Next work — start here

**No active map.** 2026-09-28 multi-feature event-rate search → `multi_feature_assist_challenger` promoted (ADR 0048): dev PASS; 2024-25 P 0.896 passes lowered 0.60 confirmation bar. Note `docs/research/multi-feature-event-rate/multi-feature-event-rate.md`.

**Slate:** Champion `multi_feature_assist_challenger` (provisional); Candidates `face_value_challenger`, `hold_chase_challenger` (former Champions). `defence_link_challenger`, `bonus_arm_challenger` → Catalog.

**Eval hardening 2026-09-28 (ADR 0046):** backtest features point-in-time (price/club pre-target, terminal player cols dropped); gate adds min effect 1%, block-bootstrap P ≥ 0.95, guardrail tolerances; 2026-27 GW6+ sealed holdout. Point-in-time re-gate: `face_value_challenger` vs `hold_chase_challenger` = regret tie (FAIL), accuracy win → Champion kept by user decision.

**Promotion protocol (ADR 0047, 0048):** gate PASS 2025-26 (boot P ≥ 0.95) + 2024-25 (no seed, one run, boot P ≥ 0.60) → promote on user's words; 2026-27 GW6+ = post-promotion check (FAIL → revert to `face_value_challenger`).

**Live data fix 2026-09-28:** `features/processor.py` ingests only `element_summary_<id>.json` for ids in current bootstrap. Raw cache held 174 stale 2025-26 summaries (ids 668–841) → 4401 prior-season rows in 2026-27 pin `player_performances` (fixture-id collisions; crashed new Champion). Pin rebuilt locally (`snapshot_season --season 2026-27 --from-raw-dir`), 3216 rows GW1–5. Source cleanup: `prune_stale_element_summaries` (`features/season_archive.py`) runs in `refresh_data` on `data/raw` and in `pin_season_archive` on pin raw; 174 stale files removed from both, pin hash refreshed.

**Next leads:** Learned hurdle correction on Champion (needs per-GW feature memory in live path); 2026-27 GW6+ = post-promotion check (ADR 0047). Deferred eval work: constrained valid-XI regret, White/SPA across variants.

Eval canon: `docs/research/INDEX.md`. Prior residual work: `docs/research/champion-component-gap/`.

## Research truth

Live index: `docs/research/INDEX.md` — **Eval canon** block = promotion metrics vs component-gap metrics (read first for Candidate/Champion work). Companions live in topic folders. Production minutes/rates = Club Fixture shrinkage + Trailing Start Window (ADR 0035). Production difficulty = **Modified FDR** (difficulty only). Fixture xP scale = **Calibrated Matchup Share** when this-season Official club xG exists (ADR 0040); else Club Strength; else neutral ×1.0 (ADR 0037). Champion = `face_value_challenger` (Historical Promotion Gate, ADR 0044/0045; former Champion `hold_chase_challenger` stays on the slate). Component-gap crown = `xp_goals` structural (`docs/research/champion-component-gap/component_gap_summary.csv` `mse_share`). Research ranking = **DCS**. Dual-Vector Strength not in production Python.

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
| Solver | `solver/` | open-fpl-solver `2ff829f` highspy; live Transfer Plan gap 1% (ADR 0043); Dream Team and Walk-Forward stay gap 0 |
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
uv run python -m commands.run_model multi_feature_assist_challenger
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
