# Solve command Transfer Plan payload

**Updated**: 2026-09-17T17:30:00+07:00  
**Data stamp**: Repo `main` `d7a6c82cf987708e31f97c8f77bd185a11af1afb` (`commands/solve.py`, `solver/transfer_plan.py`, `solver/solver.py`, `commands/export_dashboard.py`, `commands/dashboard.py`, `dashboard/`)  
**Season**: Code contract; not season-ingest  
**Status**: Active. Source synthesis of CLI emit vs dashboard load.  
**Purpose**: Inventory what `commands.solve` already writes for a Transfer Plan (buys/sells, XI, bench, captain, Hits, chips, ITB, Free Transfer Bank, per-GW 15, Solver Objective). Cite flags, paths, fields. Note what dashboard does not load.  
**Scope**: Included: `python -m commands.solve` JSON + stdout. Excluded: implementing dashboard UI; changing serializer; issue 88.  
**Related**: [GitHub #92](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/92) · [ADR 0021](../../adr/0021-ownership-explorer-dashboard-planning-horizon.md) · [INDEX](../INDEX.md)

> Code-derived claims from opened files on this SHA. No live MILP run this session.

## Sources

- **Primary**: `commands/solve.py` — CLI flags, `execute_transfer_plan`, write path `data/solution.json`
- **Primary**: `solver/transfer_plan.py` — `serialize_transfer_plan` JSON schema
- **Primary**: `solver/solver.py` — MILP `picks` / `statistics` / `summary` / `score` (vendored open-fpl-solver extract)
- **Primary**: `commands/export_dashboard.py` — `build_dashboard_dataset` discards `solution_path`; loaders unused by CLI export
- **Primary**: `commands/dashboard.py` — HTTP APIs: `/api/refresh`, `/api/dream-team` only
- **Primary**: `dashboard/index.html`, `dashboard/app.js`, `dashboard/squad.js` — fetch `dashboard_data.json`; Squad Board ITB/FT from User Squad meta
- **Primary**: `tests/test_transfer_plan.py`, `tests/test_dashboard.py`, `tests/test_ownership_explorer_view.py`
- **Primary**: `README.md` § Generate Transfer Plan; `docs/adr/0021-ownership-explorer-dashboard-planning-horizon.md`
- **Not Transfer Plan emit**: `commands/report.py` → `data/reports/top_picks_<model>.csv`; `commands/dream_team.py` in-memory Dream Team overlay

**Source boundary**: Repository source + tests. Unvalidated: live `data/solution.json` contents after a real solve (file may be absent or stale).

## Agent Prompt

```text
Full redo docs/research/wayfinder-transfer-plan-spec/solve-command-transfer-plan-payload.md

1. Re-read commands/solve.py, solver/transfer_plan.py, solver/solver.py (picks/statistics/summary), commands/export_dashboard.py loaders + build_dashboard_dataset, commands/dashboard.py APIs, dashboard/index.html app.js squad.js.
2. Re-check tests/test_transfer_plan.py and tests/test_dashboard.py test_build_dashboard_dataset_omits_transfer_plan.
3. Preserve CLI emit vs dashboard non-load as Source synthesis vs Project interpretation.
4. Do not implement UI or change serializer unless a later ticket asks.
5. Update Updated, Data stamp (HEAD SHA of opened files), Findings, Decision.
6. Keep filename stable.
```

## Method

**Method type**: Source synthesis (repository primary sources)

**Inputs**:
- CLI module `commands/solve.py`
- Serializer `solver/transfer_plan.py`
- Vendor extract writer `solver/solver.py` (~picks DataFrame and `statistics`)
- Dashboard export/load path `commands/export_dashboard.py`, `commands/dashboard.py`, `dashboard/`
- Tests named above

**Procedure**:
1. Trace `main()` flags into `execute_transfer_plan`.
2. Map serializer fields to user vocabulary (buys/sells, XI, bench, captain, Hits, chips, ITB, Free Transfer Bank, per-GW 15, Solver Objective).
3. Confirm no Transfer Plan CSV under `data/reports/` from this command.
4. Confirm dashboard JSON/API/HTML do not consume `data/solution.json`.

**Definitions and assumptions**:
- Transfer Plan document = JSON with top-level `meta` + `weeks` (`load_transfer_plan_document`).
- Legacy dump = `picks`/`model_name` without `weeks`/`meta`; loaders return plan `None`.
- Per-GW 15 = `weeks[].squad_ids` (`squad == 1` rows), not `lineup_ids` (XI).

### Metric Definitions & Direction

| Metric | Symbol | Definition / Formula | Direction | Ideal / Benchmark | Description |
|---|---|---|---|---|---|
| Solver Objective | `meta.solver_objective` | `solution["score"]` = `val(objective_expr)` after MILP | Higher $\uparrow$ (solver max) | Feasible solve | Decayed/constrained objective, not raw xP |
| Total xP | `meta.total_xp` | `val(sum((lineup+captain)*points))` over players × GWs | Higher $\uparrow$ | Context | Undecayed lineup+captain xP sum |
| Per-GW Hits | `weeks[].hits` | `statistics[gw]["pt"]` = `penalized_transfers` | Lower $\downarrow$ for spend | 0 when FT cover | Missing on first `all_gw` stats dict; serializer defaults `pt` to 0 |
| Per-GW Free Transfer Bank | `weeks[].ft` | `statistics[gw]["ft"]` else picks `ft` | Context | Rules cap 5 | Banked FTs entering/at that GW |
| Per-GW ITB | `weeks[].itb` | `statistics[gw]["itb"]` = `in_the_bank` | Context | ≥ 0 | Solver bank units (summary prints 1 decimal) |
| Per-GW objective | `weeks[].objective` | `statistics[gw]["obj"]` | Higher $\uparrow$ | Context | Absent first GW in vendor `statistics` |

**Validation boundary**: Schema asserted in `test_serialize_transfer_plan_is_json_safe_and_lists_weekly_moves` and `test_execute_transfer_plan_writes_json_safe_plan`. First-GW `statistics` thinning is vendor behavior (`solver.py`), not covered by those tests’ first week (`pt`/`obj` present in the mock).

## Source synthesis

### CLI flags (`commands.solve`)

Documented / argparse (`commands/solve.py` `main`):

| Flag | Effect |
|---|---|
| `--horizon N` | Planning length; clamped via `clamp_planning_horizon` (max 10). Default `DEFAULT_PLANNING_HORIZON` (6). |
| `--model NAME` | Projection CSV datasource; else Champion `get_default_model_name()`. |
| `--decay_base F` | Decay multiplier stored on options and copied into `meta.decay_base`. |
| `--hit_cost F` | Points cost per paid transfer (solver option, not a JSON field name). |
| `--preseason` | Blank squad; synthetic `my_data` bank 1000 tenths; skip parquet squad. |
| `--target_gw N` | Start GW; else preseason → 1; else `resolve_default_target_gw(processed_dir)`. |

Dynamic overrides: unknown `--key` parsed by `_apply_dynamic_overrides` against `SUPPORTED_DYNAMIC_OVERRIDES`. Chip keys `use_wc` / `use_bb` / `use_fh` / `use_tc` take comma lists of GWs. Boolean flags include `hide_transfers` (blanks next-GW buy/sell **strings** on the raw solution dict; JSON `weeks[].buy`/`sell` still come from picks flags). `export_debug` is an allowed option key; this worktree’s `solver/` has no `export_debug` writer hits.

README recipes: `uv run python -m commands.solve --preseason --xmin_lb 0` and `uv run python -m commands.solve --horizon 10`. `--xmin_lb` is a dynamic override, not argparse.

### Files emitted

| Artifact | Path / channel | Writer |
|---|---|---|
| Transfer Plan JSON | `PROJECT_ROOT / "data" / "solution.json"` | `execute_transfer_plan` `json.dump(plan, …, indent=2)` |
| Stdout plan text | Console after `"RECOMMENDED SQUAD & TRANSFER PLAN"` | `print(plan["summary"])` if nonempty |
| Logs | logger | `"Saved Transfer Plan to {solution_path}"` |

No CSV, no `data/reports/*` from `commands.solve`. Ranking CSV is a **different** command: `commands.report` → `data/reports/top_picks_<model_name>.csv` (README § Print Report).

Input (not emit): `pad_solver_csv_horizon(DATA_DIR / f"{datasource}.csv", …)` reads/pads `data/<model>.csv`.

### JSON document (`serialize_transfer_plan`)

Top-level keys: `meta`, `weeks`, `summary`. Tests assert `"model"` not in dump.

**`meta`**

| Field | Source |
|---|---|
| `champion` | `options["datasource"]` |
| `horizon` | clamped horizon |
| `next_gw` | `target_gw` |
| `decay_base` | options, JSON-rounded |
| `solver_objective` | `solution["score"]` |
| `total_xp` | `solution["total_xp"]` |
| `booked_chips` | CLI options `use_wc`/`use_bb`/`use_fh`/`use_tc` as int lists (booked, not necessarily solved chips) |

**`weeks[]` (one object per picks `week`)**

| User concept | Field | Derivation |
|---|---|---|
| Gameweek | `gw` | `groupby("week")` |
| Chips (solved) | `chip` | `statistics.chip` else first picks `chip` (`WC`/`FH`/`BB`/`TC` or `None`) |
| Free Transfer Bank | `ft` | `statistics.ft` else picks `ft` |
| Hits | `hits` | `statistics.pt` default 0 |
| Transfer count | `transfer_count` | `statistics.nt` else picks `transfer_count` |
| ITB | `itb` | `statistics.itb` (may be missing → JSON `null`) |
| Week xP | `xp` | `statistics.xP` else sum `lineup.xp_cont` |
| Week Solver Objective | `objective` | `statistics.obj` |
| Buys | `buy` | `{id, name}` where `transfer_in == 1` |
| Sells | `sell` | `{id, name}` where `transfer_out == 1` |
| Per-GW 15 | `squad_ids` | ids with `squad == 1` |
| XI | `lineup_ids` | `lineup == 1` |
| Bench | `bench_ids` | `bench >= 0` |
| Captain | `captain_id` | first `captain == 1` or `null` |
| Vice | `vice_id` | first `vicecaptain == 1` or `null` |

**`summary`**: vendor `summary_of_actions` string. Vendor skips **first** `all_gw` in that text (`continue` after storing only `itb`/`ft`). Later GWs include CHIP, `ITB=…->…`, `FT=`, `PT=`, `NT=`, Buy/Sell lines, Lineup/Bench names, Lineup xPts.

### Vendor `statistics` gap

For `w == all_gw[0]`, `statistics[w] = {itb, ft}` only. Serializer then: `hits` 0 unless `pt` present; `chip` may still come from picks `chip` column; `objective`/`itb` follow `stats.get`.

Picks rows include transfer-out players even when `squad == 0`; they are omitted from `squad_ids`.

### Dashboard loaders vs dashboard product

`load_transfer_plan_document` / `load_transfer_plan` in `commands/export_dashboard.py` accept `data/solution.json` when both `weeks` and `meta` exist. Callers: **tests only** (`tests/test_transfer_plan.py`). `export_dashboard.main` and `commands.dashboard.run_dashboard_export` do not pass `solution_path`. `build_dashboard_dataset` binds `_ = solution_path` and omits `transfer_plan`. Test `test_build_dashboard_dataset_omits_transfer_plan` asserts no `transfer_plan`, no `solution_model_name`, no `prefilled_squad_ids`.

HTTP (`handle_dashboard_api`): `/api/refresh`, `/api/dream-team`. No `/api/transfer-plan`. ADR 0021: `dashboard/plan.js` and `/api/transfer-plan` are not product UI. HTML test: `'id="tab-plan"' not in html`, `"plan.js" not in html`, `"Transfer Plan" not in html`.

Browser fetch: `dashboard_data.json` (`app.js`). Squad Board ITB / Free Transfer Bank / hit warning use `meta.itb` and `meta.free_transfers` from `user_state.parquet` (`load_user_state`) plus What-If vs `owned_squad_ids` (`squad.js`). Not `weeks[].itb` / `weeks[].ft` / `weeks[].hits`.

Dream Team Solve (`commands/dream_team.py`) returns in-memory `player_ids` / budget / leftover; does not write Transfer Plan JSON; overlay is not a Transfer Plan tab.

## Project interpretation

### Decision rules

- Spec / UI work should treat `data/solution.json` as the Transfer Plan contract (`meta` + `weeks` + `summary`).
- Do not assume dashboard JSON already embeds that contract.
- Do not treat `commands.report` CSV as Transfer Plan output.
- Map Hits → `hits` (`pt`); Free Transfer Bank → `ft`; Solver Objective → `meta.solver_objective` (and optionally per-GW `objective`).
- Per-GW 15 → `squad_ids`, not XI `lineup_ids`.

### Practical implications

A viewer that only loads `dashboard_data.json` cannot show MILP buys/sells, planned XI/bench/captain, planned Hits/chips, planned ITB/FT, or Solver Objective. Those exist on disk after `commands.solve` (JSON + stdout) until something reads `solution.json`.

## Findings

### Evidence

- Solve writes one JSON file: `data/solution.json` (`commands/solve.py` `solution_path=PROJECT_ROOT / "data" / "solution.json"`).
- Schema covers buys/sells (`buy`/`sell`), XI (`lineup_ids`), bench (`bench_ids`), captain (`captain_id`), Hits (`hits`), chips (`chip` + `meta.booked_chips`), ITB (`itb`), Free Transfer Bank (`ft`), per-GW 15 (`squad_ids`), Solver Objective (`meta.solver_objective`).
- Dashboard dataset and live UI do not load that file. Loaders exist unused. Squad Board ITB/FT are User Squad state. Dream Team is a separate 15 overlay.

### Alternatives

- Embed `transfer_plan` into `dashboard_data.json` (explicitly omitted today).
- Serve `/api/transfer-plan` (absent; ADR 0021 rejects as product UI).
- Persist a CSV report under `data/reports/` (solve does not).

## Decision

**Verdict**: Transfer Plan payload is JSON `data/solution.json` plus stdout `summary`; no solve CSV. Dashboard does not load it.

**Recommended action**:
- Issue 92: document this contract (this note). Implementation of a dashboard consumer is out of scope here.

**Trigger / kill switch**:
- If `execute_transfer_plan` changes `solution_path` or serializer keys, redo this note.
- If `build_dashboard_dataset` starts calling `load_transfer_plan_document`, the “dashboard does not load” finding is false.

## Risks and unknowns

- First-GW vendor `statistics` thinner than later GWs; UI must not assume `hits`/`objective`/`chip` always from `statistics`.
- `meta.booked_chips` is CLI booking, not necessarily solved `weeks[].chip`.
- `hide_transfers` does not strip JSON buy/sell lists.
- No this-session open of a produced `data/solution.json` after a live solve.

## Refresh checklist

- [x] `Updated` ISO 8601 + timezone
- [x] `Data stamp` SHA of opened sources
- [x] Season/scope: code contract
- [x] Sources are repo paths
- [x] Source synthesis vs Project interpretation separate
- [x] Unvalidated live-file contents labeled
- [x] Agent Prompt points at this slug
- [x] No `.tmp/agent/` scratch
