# FPL ownership and rank data sources (Official Operational Dataset)

**Updated**: 2026-09-17T17:40:00+07:00  
**Data stamp**: Live Season Pin `data/archive/2026-27/raw/bootstrap_static.json` + `element_summary_1.json` (pin HEAD `d7a6c82`); live Official GET `event/4/live/`, `leagues-classic/314/standings/`, `entry/{id}/`, `entry/{id}/event/4/picks/` accessed 2026-09-17  
**Season**: 2026/27 (GW4 current on pin)  
**Status**: Active  
**Purpose**: Map which ownership, transfer-momentum, rank-tier, captain-adjusted effective ownership (EO), and mini-league fields this project can use without leaving Official FPL as Operational Dataset.  
**Scope**: Official FPL HTTP JSON only. Excludes FBref, Understat, FPLReview/LiveFPL EO dumps, editorial 10k sheets. Does not treat overall `selected_by_percent` as EO. No product implementation.  
**Related**: GitHub [#90](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/90) · map [#88](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/88) · [CONTEXT.md](../../../CONTEXT.md) Operational Dataset · [ADR 0023](../../adr/0023-official-fpl-operational-dataset.md) · [ADR 0032](../../adr/0032-live-season-pin-official-only.md) · [data dictionary](../../data_dictionary.md) · [INDEX](../INDEX.md)

> `Updated` is last note revision time. `Data stamp` is freshness of data or source evidence.

## Sources

- **Primary**: Official FPL `GET https://fantasy.premierleague.com/api/bootstrap-static/` — Fantasy Premier League; live game state; accessed 2026-09-17 via Live Season Pin copy; role: player ownership, event-window transfers, event-level most-captained ids, `total_players`
- **Primary**: Official FPL `GET https://fantasy.premierleague.com/api/element-summary/{player_id}/` — Fantasy Premier League; accessed 2026-09-17 via pin `element_summary_1.json`; role: finished-GW `selected` counts and `transfers_in` / `transfers_out`
- **Primary**: Official FPL `GET https://fantasy.premierleague.com/api/event/{gw}/live/` — Fantasy Premier League; accessed 2026-09-17 (GW4); role: confirm live stats have no ownership / captain %
- **Primary**: Official FPL `GET https://fantasy.premierleague.com/api/leagues-classic/{league_id}/standings/` — Fantasy Premier League; accessed 2026-09-17 (`league_id=314`); role: Overall classic standings pages
- **Primary**: Official FPL `GET https://fantasy.premierleague.com/api/entry/{entry_id}/` and `.../event/{gw}/picks/` — Fantasy Premier League; accessed 2026-09-17; role: league membership, rank, per-entry captain flags
- **Primary**: Repo `CONTEXT.md` Operational Dataset vs Research-Only Evidence; ADR 0023; ADR 0032 pin allowlist; `clients/fpl_api.py`; `features/processor.py`; `features/contracts.py`; `features/season_archive.py`; `commands/refresh_data.py`; `commands/export_dashboard.py`; `docs/data_dictionary.md`
- **Repository data**: `data/archive/2026-27/raw/` Official pin — cutoff 2026-09-17 (workspace pin at research start)

**Source boundary**: Premier League does not publish a separate OpenAPI spec. Claims are from JSON bodies of first-party `fantasy.premierleague.com/api` responses plus this repo's ingest/contracts. Community EO formulas are not Official fields. Source claims not independently validated beyond the fetched JSON and opened repo files.

## Agent Prompt

```text
Full redo docs/research/wayfinder-transfer-plan-spec/fpl-ownership-and-rank-data-sources.md

1. Re-open CONTEXT.md Operational Dataset, ADR 0023, ADR 0032, data_dictionary.md, clients/fpl_api.py, features/processor.py, features/contracts.py, features/season_archive.py, commands/export_dashboard.py.
2. Re-inspect pin bootstrap-static elements/events keys and one element-summary history row.
3. Re-GET Official event/{current}/live/, leagues-classic/314/standings/, one entry/ and event picks/.
4. Keep Source synthesis vs Project interpretation separate. Do not call selected_by_percent EO.
5. Update Updated, Data stamp, Findings, Decision, Risks. No product code.
6. Scratch under .tmp/agent/ only; delete before finish.
```

## Method

**Method type**: Source synthesis (API JSON + repo ingest/contracts)

**Inputs**:
- Pin `data/archive/2026-27/raw/bootstrap_static.json`, `element_summary_1.json`
- Live Official GETs listed under Sources
- Opened repo files listed under Sources

**Procedure**:
1. List Official fields that describe ownership, transfers, captains, leagues, ranks.
2. Mark which fields this repo already copies into Operational parquet / Dashboard JSON vs discards vs never fetches.
3. Mark which derived metrics (EO, top-10k ownership) require extra Official endpoints vs third-party files.
4. Apply ADR 0023/0032: Official responses may enter Operational Dataset; User Squad identity stays out of the Live Season Pin.

**Definitions and assumptions**:
- **Overall ownership** = `elements[].selected_by_percent` (share of all managers). Not EO.
- **Effective ownership (EO)** = ownership adjusted for extra scoring from captain (and triple captain) among a defined manager set. Official API has no `effective_ownership` field.
- **Rank-tier / top-10k** = subset of Overall classic league (`id` 314, `name` "Overall" on 2026-09-17) by `rank`, not a published per-player ownership series.
- **Mini-league** = classic (or H2H) league other than Overall, typically from `entry/{id}.leagues`.

### Metric Definitions & Direction

| Metric | Symbol | Definition / Formula | Direction | Ideal / Benchmark | Description |
|---|---|---|---|---|---|
| Overall ownership | `selected_by_percent` | Official % of all FPL managers owning the Player | Context | Not EO | Live bootstrap field; Explorer `ownership_pct` |
| Selection count | `selected` | Integer manager count on an `element-summary` history row | Context | Pair with `total_players` | Per finished GW; not a percent |
| Event transfer in/out | `transfers_in_event` / `transfers_out_event` | Bootstrap season-window counts for the current event | Context | Momentum, not ownership | Present on bootstrap; dropped from `players.parquet` |
| History transfer in/out | `history.transfers_in` / `transfers_out` | Per finished GW net transfers on element-summary | Context | Momentum | Kept on `player_performances` |
| Captain-adjusted EO | EO | Among a defined entry set: share selected + extra for `is_captain` (`multiplier` 2) and TC (`multiplier` 3) | Context | Cannot equal `selected_by_percent` | Constructed from picks, not a bootstrap column |
| Overall rank | `rank` | Classic Overall standings row rank | Lower $\downarrow$ for a manager | Top-10k = `rank` ≤ 10000 | League 314 pages of 50 |

**Validation boundary**: Live GETs are point-in-time 2026-09-17. Pin JSON may lag live. No Availability Snapshot used. League 314 id confirmed on live JSON this session, not assumed from folklore alone.

## Source synthesis

### Main claims

- `bootstrap-static` top-level keys on the 2026-27 pin include `elements`, `events`, `total_players` (pin value `10771928`). No `effective_ownership` key.
- Each `elements[]` object includes `selected_by_percent`, `selected_rank`, `selected_rank_type`, `transfers_in`, `transfers_out`, `transfers_in_event`, `transfers_out_event`. No captain-percentage field on the player object.
- Each `events[]` object includes `most_selected`, `most_transferred_in`, `most_captained`, `most_vice_captained` (single player ids), `transfers_made`, `ranked_count`, `chip_plays`. Data dictionary lists these as discarded from `gameweeks.parquet`.
- `element-summary` `history[]` rows include `selected`, `transfers_in`, `transfers_out`, `transfers_balance`. No captain flags.
- `event/{gw}/live/` JSON (GW4, 2026-09-17) top key is `elements` only. Each element has `id`, `stats`, `explain`, `modified`. `stats` keys are match stats (`minutes`, `total_points`, ICT, xG, …). No `selected`, transfers, or captain %.
- `leagues-classic/314/standings/` (2026-09-17): `league.id` 314, `league.name` "Overall", `league_type` "s", `scoring` "c". `standings.results` length 50 with `entry`, `rank`, `last_rank`, `event_total`, `total`. `standings.has_next` true. `last_updated_data` present.
- `entry/{id}/` includes `summary_overall_rank`, `leagues.classic[]` (system leagues plus others) with `id`, `name`, `entry_rank`, `rank_count`, `league_type`. Overall appears as `id` 314, `short_name` "overall".
- `entry/{id}/event/{gw}/picks/` includes `picks[].element`, `multiplier`, `is_captain`, `is_vice_captain`, plus `entry_history.overall_rank`.
- ADR 0023: production ingest, Feature Contract, Model Champion, Transfer Plan, and Ownership Explorer use only Official FPL API responses and Season Archives of those responses. Research-Only Evidence must not write Raw Cache, Season Archive ingest, Feature Contract, or Champion inputs.
- CONTEXT Operational Dataset: Official FPL API plus Season Archives of those responses. User Squad is Official (`/me/`, `/my-team/`) but is not a Season Archive / Live Season Pin object (ADR 0032).
- `clients/fpl_api.py` implements bootstrap, live, fixtures, element-summary, me, my-team, entry, entry history, entry transfers, event picks. No `leagues-classic` or `leagues-h2h` client.
- `commands/refresh_data.py` fetches bootstrap, fixtures, all element-summaries, and authenticated me + my-team. It does not fetch `event/{gw}/live/` or any league standings.
- `features/processor.py` keeps `selected_by_percent` on players; keeps `selected` + history transfers on performances; does not keep `transfers_in_event` / `transfers_out_event` / `selected_rank` / event `most_captained`.
- `features/contracts.py` `OPERATIONAL_REQUIRED.players` does not require `selected_by_percent`. Feature Contract required columns are only `player_id`, `fixture_id`, `gameweek_id`. `features/builder.py` has no `selected_by` / ownership / transfer-momentum columns.
- `commands/export_dashboard.py` sets Explorer `ownership_pct` from `selected_by_percent`. ADR 0021/0027: that field is overall ownership on the Explorer chart, not EO. Official Captain on the Squad Board is the User Squad armband, not market C%.
- `features/season_archive.py` Official raw allowlist: `bootstrap_static.json`, `fixtures_all.json`, `element_summary_*.json`, `event_*_live.json`, `fixtures_gw_*.json`. League JSON, `me.json`, `my_team_*` are not Official pin files.

### Source rationale

- Overall ownership and GW transfer counts exist as first-party bootstrap/summary fields, so they can stay inside Operational Dataset without a third-party scrape.
- Per-player captain % and EO are not first-party columns; they are only reconstructable by aggregating Official picks for a chosen entry set.
- Top-10k / rank-tier ownership is not a bootstrap series. Official path is Overall standings pages plus per-entry picks.
- Mini-league tables are Official `leagues-classic/{id}/standings/` once `league_id` is known (from `entry/{id}` or a public code).

## Project interpretation

### Decision rules

- If the product needs **overall ownership**, use pin/live `selected_by_percent` (already Explorer). Label it overall ownership, never EO.
- If the product needs **transfer momentum**, prefer Official `transfers_in_event` / `transfers_out_event` (live bootstrap; not currently parquet) and/or history `transfers_in` / `transfers_out` (already `player_performances`). Do not import third-party “net transfers” charts.
- If the product needs **top-10k or rank-tier ownership / EO**, stay Official by paging `leagues-classic/314/standings/` then `entry/{id}/event/{gw}/picks/`. Treat that as new Official ingest (gitignored live cache; pin only if ADR 0032 allowlist is extended). Do not use FPLReview/LiveFPL CSVs as Operational Dataset.
- If the product needs **captain-adjusted EO**, compute it from Official picks (`is_captain`, `multiplier`) over a defined entry set. Do not substitute `selected_by_percent`. Event `most_captained` is a single id, not C%.
- If the product needs **the user’s mini-league**, use Official `entry/{entry_id}/` `leagues` plus `leagues-classic/{id}/standings/`. Keep identity files out of the Live Season Pin (same rule as User Squad).
- Feature Contract / Champion stay free of ownership unless a later ADR adds Official columns. Dashboard may show Official ownership without feeding Champion.

### Practical implications

- Gap vs community “EO / 10k ownership” dashboards is ingest volume and labeling, not a requirement to leave Official FPL.
- `event/live/` does not close the EO gap.
- Expanding `players.parquet` with discarded bootstrap transfer fields is Official-eligible and pin-safe (bootstrap already pinned).

## Findings

### Evidence

**Already usable on Operational Dataset (ingested today)**

1. **Overall ownership %** — bootstrap `selected_by_percent` → `players.parquet` → dashboard `ownership_pct`. Not EO.
2. **Finished-GW selection count and transfers** — element-summary `history.selected`, `transfers_in`, `transfers_out`, `transfers_balance` → `player_performances.parquet`. `selected / total_players` is an Official-derived overall share at that history row, still not EO.
3. **User Squad captain flags** — authenticated `/my-team/` and `/entry/{id}/event/{gw}/picks/` (`is_captain`, `multiplier`). Official; gitignored; not pin. One manager’s armband, not market EO.
4. **User overall rank** — available on Official `entry/{id}/` (`summary_overall_rank`) and picks `entry_history.overall_rank`. Client exists (`fetch_entry_summary`); refresh does not call it.

**Official and Operational-eligible, present in pin JSON, dropped by processor**

5. **Current-event transfer momentum** — `transfers_in_event`, `transfers_out_event`, season `transfers_in` / `transfers_out` on bootstrap elements. Pin retains them in `bootstrap_static.json`; `processor.py` `keep_player_cols` omits them.
6. **Ownership rank among players** — `selected_rank`, `selected_rank_type`.
7. **Event headline ids** — `events[].most_captained` / `most_vice_captained` / `most_selected` / `most_transferred_in` / `transfers_made` / `chip_plays`. Single-id / aggregate, not per-player C% or EO.

**Official FPL, not fetched by refresh, eligible if added as Official ingest**

8. **Overall / rank-tier standings** — `GET /leagues-classic/314/standings/?page_standings=N` (50 rows/page; `has_next`). Top-10k ≈ first 200 pages. No per-player ownership in the standings payload.
9. **Per-entry squads for a tier** — `GET /entry/{entry_id}/event/{gw}/picks/` for those entries. From this, **tier ownership** = share with `element` in picks; **tier EO** = that share plus extra for `multiplier` 2 (C) or 3 (TC). Vice-captain (`is_vice_captain`) is not extra points unless you model autosub, which live picks do not pre-resolve.
10. **Mini-leagues** — `entry/{id}.leagues.classic[]` then `leagues-classic/{league_id}/standings/`. Same pattern as Overall. H2H would be a different Official family (`leagues.h2h` on the sampled entry was `[]` on 2026-09-17).
11. **`event/{gw}/live/`** — already in the pin allowlist and `snapshot_season`; **no** ownership, transfers, or captain %. Does not help EO.

**Must not enter Operational Dataset**

12. Third-party EO / 10k ownership files, scraped non-FPL sites, and treating `selected_by_percent` as EO (ticket constraint + INDEX “Ownership Popularity” definition).

### Alternatives

- **Keep Explorer on overall % only** — zero new ingest; honest label.
- **Promote bootstrap transfer fields into parquet** — small Official change; still not EO.
- **Sample Official Overall picks (e.g. 10k or stratified ranks)** — Official EO/10k; rate-limit and cache policy required; do not git-pin 10k pick dumps without an ADR 0032 change.
- **One mini-league table for the authenticated entry** — Official; identity-sensitive; gitignore like User Squad.

## Decision

**Verdict**: Without leaving Official FPL, the project already has overall ownership and finished-GW transfer counts; it can add event-window momentum from pinned bootstrap fields; it cannot get captain-adjusted EO or top-10k ownership from `selected_by_percent` or `event/live/`; those metrics require Official league standings + entry picks aggregations, which are Operational-eligible but not ingested.

**Recommended action**:
- Product copy: `ownership_pct` = overall `selected_by_percent`, not EO.
- Transfer-momentum: recover `transfers_in_event` / `transfers_out_event` from bootstrap if needed.
- EO / 10k / mini-league: new Official clients + gitignored cache; extend pin allowlist only with an ADR.
- Do not feed third-party 10k/EO into Feature Contract or Champion.

**Trigger / kill switch**:
- If FPL adds a first-party per-player captain % or EO field on bootstrap/live, re-open this note and prefer that field over picks aggregation.
- If league 314 is not Overall on a future GET, stop using 314 from memory; read `entry.leagues` `short_name=overall`.

## Risks and unknowns

- Paging ~200 Overall pages plus thousands of picks calls is Official but fragile (rate limits, pagination changes). Unvalidated operational cost.
- History `selected` vs bootstrap `selected_by_percent` timing can disagree within a GW; both are Official, neither is EO.
- VC conversion and autosubs are not in bootstrap; EO that includes expected VC is a model, not an Official field.
- Private mini-league visibility may require the same auth as User Squad; do not commit those JSON files to the pin.
- `total_players` vs `events[].ranked_count` differ on the pin (unranked / inactive entries); percent bases are not identical.

## Refresh checklist

- [x] `Updated` uses ISO 8601 timestamp with timezone.
- [x] `Data stamp` identifies current evidence cutoff.
- [x] `Season` and scope remain accurate.
- [x] Source URLs, publication dates, and access dates checked.
- [x] Source synthesis and Project interpretation remain separate.
- [x] Unvalidated claims labeled.
- [x] Agent Prompt remains runnable and points to stable slug.
- [x] Scratch files removed from `.tmp/agent/`.
