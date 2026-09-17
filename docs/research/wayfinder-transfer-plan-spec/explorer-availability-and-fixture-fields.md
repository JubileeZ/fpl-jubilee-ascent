# Explorer availability and fixture fields already shipped

**Updated**: 2026-09-17T17:35:00+07:00  
**Data stamp**: `main` `d7a6c82cf987708e31f97c8f77bd185a11af1afb` (detached worktree start; isolated branch `research/explorer-availability-and-fixture-fields`)  
**Season**: Code inventory. Not a Season Archive metric. Live season on this SHA is 2026-27.  
**Status**: Active. Research only. No Feature Contract, dashboard JSON, or UI change.  
**Purpose**: Answer GitHub issue [#93](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/93): which availability, news, chance-of-playing, xMins, opponent, home/away, and difficulty fields already exist on the Feature Contract or Ownership Explorer dashboard data contract, and which of those are missing from the Ownership Explorer UI.  
**Scope**: Included: Feature Contract runtime required keys; `build_features` emitted columns; Operational `players.parquet` / `fixtures.parquet` fields that feed those contracts; `build_dashboard_dataset` player JSON; Ownership Explorer HTML/JS (`dashboard/index.html`, `explorer.js`, `squad.js`). Excluded: Transfer Plan CLI UI; FDR report CLI; Expected Role table; Availability Snapshot package internals beyond Feature Contract attach; implementation proposals.  
**Related**: [#93](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/93) (this note). Parent [#88](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/88) not edited. ADRs [0006](../../adr/0006-fixture-first-projection-contract.md), [0010](../../adr/0010-participation-state-snapshots-and-evaluation.md), [0011](../../adr/0011-multi-model-dashboard-comparison.md), [0019](../../adr/0019-modified-fdr-production.md), [0021](../../adr/0021-ownership-explorer-dashboard-planning-horizon.md). Glossary: `CONTEXT.md` Feature Contract, Ownership Explorer, Modified FDR, Appearance Probability.  
**Artifact**: none — field inventory; no companion CSV

> `Updated` is last note revision time. `Data stamp` is freshness of data or source evidence. Do not add duplicate `Last update` fields.

## Sources

- **Primary**: `features/contracts.py` — Feature Contract runtime required set `player_id`, `fixture_id`, `gameweek_id`; accessed 2026-09-17; role: runtime contract
- **Primary**: `features/builder.py` `build_features`, `_fixture_maps` — emitted availability and fixture columns; accessed 2026-09-17; role: Feature Contract producer
- **Primary**: `features/processor.py` player/fixture keep lists — Operational Dataset fields retained from Official FPL; accessed 2026-09-17; role: ingest schema
- **Primary**: `docs/data_dictionary.md` §4–5, §13 — players/fixtures retained fields and runtime contract summary; accessed 2026-09-17; role: documented Operational + runtime contracts
- **Primary**: `commands/export_dashboard.py` `build_dashboard_dataset` — Ownership Explorer dashboard JSON player object; accessed 2026-09-17; role: dashboard data contract producer
- **Primary**: `dashboard/index.html`, `dashboard/explorer.js`, `dashboard/squad.js` — Ownership Explorer UI columns and field reads; accessed 2026-09-17; role: UI consumer
- **Primary**: `projections/explorer_slice.py` — `avg_minutes` from Projection `projected_minutes`; accessed 2026-09-17; role: Explorer slice metrics
- **Primary**: `models/participation_state_hybrid.py` — Champion next-GW 0% chance hard DNP; accessed 2026-09-17; role: how Feature Contract chance is used
- **Secondary**: `CONTEXT.md` glossary (Feature Contract, Ownership Explorer, Modified FDR, Appearance Probability); ADRs 0006, 0010, 0011, 0019, 0021, 0022 — project interpretation of production meaning; accessed 2026-09-17
- **Repository data**: Git `HEAD` at Data stamp. No live `dashboard_data.json` inspect (gitignored / not required). Tests `tests/test_dashboard.py`, `tests/test_ownership_explorer_view.py`, `tests/test_fixture_contract.py` confirm keys/UI markers.

**Source boundary**: Claims are source-code and first-party docs on this SHA. Source claims not independently validated against a live exported JSON file.

## Agent Prompt

```text
Full redo docs/research/wayfinder-transfer-plan-spec/explorer-availability-and-fixture-fields.md

1. Re-read Feature Contract producer (features/builder.py, features/contracts.py).
2. Re-read dashboard data contract producer (commands/export_dashboard.py build_dashboard_dataset).
3. Re-read Ownership Explorer UI (dashboard/index.html, explorer.js, squad.js).
4. Re-check processor keep lists and data_dictionary players/fixtures sections.
5. Preserve Source synthesis vs Project interpretation.
6. Do not implement UI or contract changes.
7. Update Updated, Data stamp, Findings, Decision.
8. No companion CSV unless a later ticket asks for a machine table.
9. Scratch under .tmp/agent/ only; delete before finish.
```

## Method

**Method type**: Source synthesis (code + first-party docs inventory)

**Inputs**:
- Feature Contract: `features/contracts.py`, `features/builder.py`
- Operational fields: `features/processor.py`, `docs/data_dictionary.md`
- Dashboard JSON: `commands/export_dashboard.py`
- UI: `dashboard/index.html`, `dashboard/explorer.js`, `dashboard/squad.js`
- Champion use of chance: `models/participation_state_hybrid.py`
- Issue question: GitHub #93 body

**Procedure**:
1. List runtime-required Feature Contract columns vs builder-emitted columns for the asked concepts.
2. List dashboard JSON keys written for the same concepts.
3. Search Explorer HTML/JS for those JSON keys and for opponent / home / away / difficulty / news / chance / status.
4. Classify each field: Feature Contract / dashboard JSON / UI-visible.
5. Separate glossary interpretation (what production *means*) from what the files *contain*.

**Definitions and assumptions**:
- **Feature Contract** = DataFrame returned by `build_features` after `assert_feature_contract`. Runtime required keys are a subset of emitted columns.
- **Dashboard data contract** = JSON object from `build_dashboard_dataset` (`meta` + `players[]`), consumed as Ownership Explorer payload.
- **UI-visible** = rendered text, table header, filter control, or tooltip that reads the field. Presence on JSON without a JS/HTML read is **on contract, missing from UI**.
- **xMins (product)** = Projection `projected_minutes` / Explorer `avg_minutes` / per-GW `projections.gwN.xmins`, not Feature Contract `xmins_if_start` / `xmins_if_sub_in`.
- Horizon gameweek cells in Explorer show `total_xp`, not opponent or FDR.

### Metric Definitions & Direction

| Metric | Symbol | Definition / Formula | Direction | Ideal / Benchmark | Description |
|---|---|---|---|---|---|
| Field on Feature Contract | `on_fc` | Column present on `build_features` output (required or emitted) | Present / absent | Match intended product field | Schema presence, not UI |
| Field on dashboard JSON | `on_dash` | Key written in `build_dashboard_dataset` player or per-GW projection object | Present / absent | Match Explorer need | Contract presence, not UI |
| Field in Explorer UI | `on_ui` | HTML/JS renders or filters on that key | Present / absent | User can see it | Missing = shipped in data, not drawn |

**Validation boundary**: Validated by opening the cited files on this SHA. Unvalidated: live `data/dashboard_data.json` contents; whether a future UI path reads `player.status` via dynamic key (static source has no such read).

## Source synthesis

### Main claims

- Runtime Feature Contract requires only `player_id`, `fixture_id`, `gameweek_id`. Extra availability and fixture columns are builder output, not that frozenset.
- `build_features` merges full `players.parquet` (so Operational availability columns travel) and attaches `_fixture_maps` (`opponent_id`, `is_home`, `difficulty` = Modified FDR, strength multipliers). It also writes derived `chance_of_playing`, `is_immediate_next_gw`, snapshot flags, `xmins_if_start` / `xmins_if_sub_in`, `xmins_cap` (NaN).
- Operational `players.parquet` retains `status`, `chance_of_playing_next_round`, `chance_of_playing_this_round`, `news`, `news_added`. Fixtures retain Official FDR ticks `team_h_difficulty` / `team_a_difficulty`, not Modified FDR.
- Dashboard JSON copies `status`, `chance` (from `chance_of_playing_next_round` only), `news`, and per-GW `xmins` from `projected_minutes`. It does not write opponent, `is_home`, difficulty, `news_added`, or `chance_of_playing_this_round`.
- Ownership Explorer table headers: rank, Player, Club, Pos, Price, Own%, Total, per-GW xP, /90, xMins. Toolbar: Assume 90, avg minutes floor. Player components include an xMins row. No news, chance, status, opponent, H/A, or FDR column.

### Source rationale

- Issue #93 asks inventory only. Dashboard JSON builder and Explorer UI are the cite targets. Implementation is out of scope.

## Project interpretation

### Decision rules

- Treat **runtime required** vs **emitted** Feature Contract columns as different layers. A field can be on the live Feature Contract DataFrame without being in `FEATURE_CONTRACT_REQUIRED`.
- Treat Explorer **xMins** as Projection minutes on the dashboard contract, not as Feature Contract conditional-minute columns.
- Treat Feature Contract `difficulty` as **Modified FDR** (ADR 0019), not Official ticks.
- Treat Champion use of `chance_of_playing`: next-GW 0% hard DNP only when `is_immediate_next_gw` and `has_availability_snapshot` (`participation_state_hybrid.py`). Dashboard `chance` is a separate terminal API copy and is unused in Explorer JS.
- Appearance Probability (`1 - p_dnp`) is Feature Contract / Projection, not an Explorer column.

### Practical implications

- Wayfinder / Transfer Plan spec can assume opponent, home/away, and Modified FDR already exist on Feature Contract rows; they are not on the Explorer JSON or UI.
- News and chance-of-playing-next-round already exist on Operational players and dashboard JSON; Explorer does not show them.
- Showing fixtures in Explorer would need new dashboard JSON keys (or a new join), not only a Feature Contract change.

## Findings

### Evidence

**A. Feature Contract — runtime required**

| Field | On FC required set? | Source |
|---|---|---|
| `player_id`, `fixture_id`, `gameweek_id` | Yes | `features/contracts.py` `FEATURE_CONTRACT_REQUIRED`; `docs/data_dictionary.md` §13 |
| Availability, news, chance, xMins, opponent, H/A, difficulty | No | same files — not in the frozenset |

Empty frames skip the check (`assert_feature_contract`).

**B. Feature Contract — builder-emitted (asked concepts)**

Grain: one row per `player_id` × `fixture_id` (blank GW: `fixture_id == -1`). ADR 0006.

| Concept | Column(s) on `build_features` output | How produced | Source |
|---|---|---|---|
| Availability (API status) | `status` (if present on players parquet) | `df_players` load/rename `id`→`player_id`, merge into `df_feat` | `builder.py` `_load_players` / snapshot players; `processor.py` keep `status` |
| Availability (engine flags) | `draft_availability`, `availability_override`, `has_availability_snapshot`, `availability_snapshot_id` | Seed defaults `"eligible"` / `""`; snapshot flags after chance block | `builder.py` seed row + fillna + lines after chance |
| Availability (override cap) | `xmins_cap` | Set to NaN; production does not apply caps | `builder.py`; `CONTEXT.md` Availability Override; `models/base.py` `cap_projected_minutes` |
| News | `news`, `news_added` | Same player merge; Operational keep list | `processor.py`; `data_dictionary.md` §4 |
| Chance-of-playing (API raw) | `chance_of_playing_next_round`, `chance_of_playing_this_round` | Player merge | `processor.py`; `data_dictionary.md` §4 |
| Chance-of-playing (engine) | `chance_of_playing` | From `chance_of_playing_next_round` when snapshot/live path allows; else 100.0 if `as_of_gw` and no PIT snapshot (anti-leakage); fallback `appearance_probability * 100`; statuses `u`/`n` → 0 when snapshot present | `builder.py` chance block; `tests/test_fixture_contract.py` |
| Immediate-GW flag | `is_immediate_next_gw` | `gameweek_id == target_gw` | `builder.py` |
| xMins (conditional) | `xmins_if_start`, `xmins_if_sub_in`, `minutes_if_appearance`, `p_start`, `p_sub_in`, `p_dnp`, `appearance_probability` | Participation State posterior | `builder.py` seed merge; `CONTEXT.md` Participation State / Appearance Probability |
| Opponent | `opponent_id` | `_fixture_maps`; blank/NA → 0 | `builder.py` `_fixture_maps`; ADR 0006 |
| Home/away | `is_home` | `_fixture_maps`; NA → False | same |
| Difficulty (production) | `difficulty` | Modified FDR from Official ticks; NA/blank → 3.0 | `_fixture_maps` + `features/fdr.py`; ADR 0019; `tests/test_modified_fdr.py` |
| Opponent/team strength (related) | `opponent_attack_strength`, `opponent_defence_strength`, `attack_multiplier`, `defence_multiplier`, … | `_fixture_maps` | `builder.py`; `CONTEXT.md` Club Strength Vector |

Official FDR ticks `team_h_difficulty` / `team_a_difficulty` live on Operational `fixtures.parquet`, not as Feature Contract column names. Feature Contract `difficulty` is Modified FDR.

Champion (`participation_state_hybrid.py`): `chance_of_playing <= 0` forces DNP only when `is_immediate_next_gw` and `has_availability_snapshot`. That is next-GW 0% hard DNP, not horizon-wide API chance (ADR 0010 / `CONTEXT.md` Appearance Probability).

**C. Ownership Explorer dashboard data contract**

Producer: `commands/export_dashboard.py` `build_dashboard_dataset`. Players come from Operational `players.parquet`, not from Feature Contract column names. Per-GW xMins come from Projection `projected_minutes`.

| Concept | JSON key | Written? | Source |
|---|---|---|---|
| Availability status | `players[].status` | Yes (`str(p.get("status", "a"))`) | `export_dashboard.py` player_dict |
| News | `players[].news` | Yes | same |
| News timestamp | `news_added` | No | player_dict has no key |
| Chance next round | `players[].chance` | Yes; `int(chance_of_playing_next_round)` or `null` | same |
| Chance this round | — | No | only next-round mapped |
| Engine `chance_of_playing` | — | No | not copied from Feature Contract |
| Snapshot / draft availability | — | No | not in player_dict |
| xMins per GW | `players[].projections.gw{N}.xmins` and `models[name].projections.gw{N}.xmins` | Yes; `round(projected_minutes, 1)` | same loop |
| xMins horizon total | `total_xmins_horizon` | Yes | same |
| Slice avg minutes | `explorer.planning_horizon.avg_minutes` (via `planning_horizon_slice`) | Yes | `projections/explorer_slice.py` |
| Opponent | — | No | no fixture join in `build_dashboard_dataset` |
| Home/away | — | No | same |
| Difficulty / FDR | — | No | same |
| Feature `xmins_if_start` / `xmins_if_sub_in` | — | No | dashboard uses Projection minutes only |

Multi-model grouping under `player.models[model_name]` is ADR 0011. Fixture fields were not added in that contract.

**D. Ownership Explorer UI**

| Surface | What is shown | Source |
|---|---|---|
| Table headers | `#`, Player, Club, Pos, Price, Own%, Total, `GW{n}` (xP), `/90`, xMins | `explorer.js` `renderHead`; `index.html` thead |
| Per-GW cells | `slice.perGw[gw]` = `total_xp` only | `explorer.js` `sliceOf` / `renderTable` |
| xMins column | `slice.avg_minutes` | `explorer.js`; `explorer_slice.py` minutes / n_gameweeks |
| Avg minutes floor | filter on `avg_minutes` | `index.html` `#explorer-xmins-floor`; `explorer.js` `hideReason` `"xmins"` |
| Assume 90 | rescales `xmins` and xP in view | `index.html` `#explorer-assume-90`; `explorer.js` `assumeNinetyRow`; ADR 0021 |
| Player components | xMins row plus Event Component xP | `explorer.js` `PLAYER_COMPONENT_ROWS` |
| Squad components | xMins row among PROFILE_KEYS | `squad.js` `PROFILE_KEYS`; `index.html` “Squad components (xMins \| Assume 90)” |
| News | not referenced | grep of `dashboard/*.js` / `index.html`: no `player.news` |
| `chance` / chance-of-playing | not referenced | no `player.chance` |
| `status` (player) | not referenced | `app.js` `status` is job/API state only |
| Opponent / H/A / difficulty | not referenced | no those identifiers in explorer/squad/index for player fixtures |

Tests: `test_explorer_reports_xmins_not_role` asserts xMins header and no Role; `test_ownership_explorer_view` asserts xMins floor and squad xMins label.

**E. Inventory vs issue question**

| Field family | Feature Contract | Dashboard JSON | Explorer UI |
|---|---|---|---|
| Availability `status` | Emitted via player merge | `status` | Missing |
| Snapshot / draft / override flags | Emitted (`draft_availability`, snapshot flags, unused `xmins_cap`) | Missing | Missing |
| `news` | Emitted via player merge | `news` | Missing |
| `news_added` | Emitted via player merge | Missing | Missing |
| `chance_of_playing_next_round` | Emitted via player merge | `chance` | Missing |
| `chance_of_playing_this_round` | Emitted via player merge | Missing | Missing |
| Engine `chance_of_playing` | Derived column | Missing | Missing |
| Product xMins (clock) | Inputs: `xmins_if_*`, state probs; output is Projection `projected_minutes` | `xmins`, `avg_minutes`, `total_xmins_horizon` | Present (table, floor, components, Assume 90) |
| Conditional `xmins_if_start` / `xmins_if_sub_in` | Emitted | Missing | Missing |
| Opponent | `opponent_id` | Missing | Missing |
| Home/away | `is_home` | Missing | Missing |
| Difficulty | `difficulty` (Modified FDR) | Missing | Missing |
| Official FDR ticks | Operational fixtures only | Missing | Missing |

### Alternatives

- Infer fixtures in the UI from club + gameweek without JSON keys: not present; UI has no fixture map.
- Treat Club column as “opponent”: it is the player’s club (`p.team`), not the fixture opponent.

## Decision

**Verdict**: Availability `status`, `news`, and next-round chance are already on Operational players, travel on the Feature Contract DataFrame, and `status` / `news` / `chance` are already on the dashboard JSON — none of those three are drawn in Ownership Explorer. Product xMins is already on the dashboard contract and UI. Opponent, home/away, and Modified FDR `difficulty` are already on the Feature Contract and are absent from both dashboard JSON and UI.

**Recommended action**:
- Use this inventory for wayfinder / #88 spec work. This ticket is research-complete. No implementation in this note.

**Trigger / kill switch**:
- Re-open if `export_dashboard.py` player_dict or `explorer.js` `renderHead` / `PLAYER_COMPONENT_ROWS` add fixture or availability keys after this SHA.

## Risks and unknowns

- Live exported JSON not opened; contract taken from builder source and tests.
- `status` letter codes (`a`/`i`/`d`/`u`/`n`) documented in `data_dictionary.md` §4; UI never maps them.
- Feature Contract `opponent_id` is a club id, not a short name; Explorer would need a club join even if the id were exported.
- `chance` on JSON is terminal next-round API chance, not Champion snapshot-gated `chance_of_playing`.

## Refresh checklist

- [x] `Updated` uses ISO 8601 timestamp with timezone.
- [x] `Data stamp` identifies current evidence cutoff.
- [x] `Season` and scope remain accurate.
- [x] Source paths checked on this SHA.
- [x] Source synthesis and Project interpretation remain separate.
- [x] Unvalidated claims labeled.
- [x] Agent Prompt remains runnable and points to stable slug.
- [x] Scratch files removed from `.tmp/agent/`.
