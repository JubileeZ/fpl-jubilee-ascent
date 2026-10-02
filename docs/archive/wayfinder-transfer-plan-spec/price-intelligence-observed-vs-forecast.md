# Price intelligence: observed vs forecast

**Updated**: 2026-09-17T17:37:46+07:00  
**Data stamp**: Official FPL live `bootstrap-static`, accessed 2026-09-17T10:37:46Z; repository evidence at `d7a6c82cf987708e31f97c8f77bd185a11af1afb`  
**Season**: 2026/27  
**Status**: Active  
**Purpose**: Separate price history already reported by project from next-price-deadline prediction.  
**Scope**: Repository commands, archived Parquet/raw API fields, live Official FPL API, Official FPL guidance. No feature implementation or third-party predictor comparison.  
**Related**: [Price intelligence observed vs forecast](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/91); [Transfer Plan dashboard spec](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/88)  
**Artifact**: None; source-synthesis note only.

## Sources

- **Primary**: [2026/27 Game Updates — Official Fantasy Premier League](https://fantasy.premierleague.com/en/help/new) — accessed 2026-09-17; role: Official predictor announcement.
- **Primary**: [FPL basics explained: How to make transfers — Premier League](https://www.premierleague.com/en/news/2174907/fpl-basics-explained-how-to-make-transfers) — published 2026-07-20; accessed 2026-09-17; role: current progress, predicted progress, refresh cadence, threshold, deadline, selling-price rules.
- **Primary**: [FPL player price changes: how, why and when does it happen? — Premier League](https://www.premierleague.com/en/news/2858775) — published 2025-10-03; accessed 2026-09-17; role: observed price-change mechanics.
- **Primary**: [FPL player price changes, Gameweek 5 — Premier League](https://www.premierleague.com/en/news/2884829) — published 2026-09-17; accessed 2026-09-17; role: dated overnight outcomes and Official predictor link.
- **Primary API**: [Official FPL `bootstrap-static`](https://fantasy.premierleague.com/api/bootstrap-static/) — accessed 2026-09-17T10:37:46Z; role: current player price, transfer-pressure, and predictor payload.
- **Repository source**: [`commands.price_report`](../../../commands/price_report.py) and [tests](../../../tests/test_price_report.py) — commit `d7a6c82`; role: snapshot/report behavior.
- **Repository source**: [`commands.refresh_data`](../../../commands/refresh_data.py), [`features.processor`](../../../features/processor.py), and [data dictionary](../../../docs/data_dictionary.md) — commit `d7a6c82`; role: ingestion and retained-field boundary.
- **Repository source**: [`commands.capture_availability_snapshot`](../../../commands/capture_availability_snapshot.py) and [nested-field test](../../../tests/test_availability_snapshots.py) — commit `d7a6c82`; role: full bootstrap-frame capture path.
- **Repository data**: [`2026-27/raw/bootstrap_static.json`](../../../data/archive/2026-27/raw/bootstrap_static.json), [`price_history.parquet`](../../../data/archive/2026-27/processed/price_history.parquet), and [`player_performances.parquet`](../../../data/archive/2026-27/processed/player_performances.parquet) — repository capture through 2026-09-14T13:58:24Z.

**Source boundary**: Official articles define product semantics but do not publish API field schema, likelihood-code mapping, or price-change formula. Field meanings below combine Official UI descriptions with observed first-party API names; undocumented mappings remain labeled.

## Agent Prompt

```text
Full redo docs/research/wayfinder-transfer-plan-spec/price-intelligence-observed-vs-forecast.md

1. Re-read Official FPL 2026/27 game updates, transfer guide, and latest price-change page.
2. Fetch live Official FPL bootstrap-static without writing credentials or user data.
3. Re-profile elements price/transfer/predictor fields and checked-in price_history.parquet.
4. Re-open commands.price_report, commands.refresh_data, features.processor, and availability capture.
5. Preserve observed outcomes, transfer pressure, Official prediction, and project-derived prediction as separate concepts.
6. Update Updated, Data stamp, evidence counts, Findings, Decision, and Risks.
7. Keep this path stable; create no companion unless analysis requires one.
8. Store scratch under .tmp/agent/ only; delete scratch before finishing.
```

## Method

**Method type**: Primary-source synthesis plus point-in-time dataset inspection.

**Inputs**:
- Official FPL guidance and live `bootstrap-static`.
- Repository command source and tests at `d7a6c82`.
- Checked-in 2026/27 raw bootstrap, price history, and player-performance Parquet.

**Procedure**:
1. Classify each signal by time direction: already happened, current pressure, or next-deadline projection.
2. Trace each API field through raw capture, processing, history append, and report output.
3. Profile raw rows and Parquet snapshots for row count, keys, nulls, duplicate keys, invalid costs, capture range, and roster-size variation.
4. Compare Official predictor semantics with project report semantics.

**Definitions and assumptions**:
- **Observed**: price value or delta known at capture time; no claim about next deadline.
- **Transfer pressure**: current/cumulative transfer activity; directional evidence, not a guaranteed price outcome.
- **Tonight forecast**: Official indication for next 00:00 UK price-change deadline. Official guidance says indication is not a guarantee.
- **Previous refresh**: prior distinct `captured_at`, not prior midnight and not necessarily prior day.

### Metric definitions and direction

- **Refresh delta**: `latest_price - previous_refresh_price`; descriptive, zero benchmark; sign records observed movement.
- **Season delta**: `latest_price - first_captured_price`; descriptive, zero benchmark; sign records movement since repository baseline, not necessarily Official season-opening price.
- **Current progress**: Official predictor percentage toward change; absolute movement toward or beyond 100% indicates stronger next-deadline signal under Official guidance.
- **Predicted progress**: Official projected percentage; absolute value beyond 100% means expected threshold crossing, while Official guidance explicitly withholds any guarantee.

**Validation boundary**: Dataset inspection used all rows, preserved negative signed change/progress values, and treated double-gameweek player-performance duplicates as fixture rows rather than errors. No project predictor was trained or backtested.

## Source synthesis

### Official price behavior

- Official FPL says heavy buying can produce a £0.1m daily rise and heavy selling can produce a £0.1m daily fall; changes happen overnight UK time. [Source](https://www.premierleague.com/en/news/2858775)
- Current 2026/27 guidance fixes the change deadline at 00:00 UK time and describes a page updated every 15 minutes with current progress, predicted progress after calibration, and “Likely” / “Very Likely” statuses. [Source](https://www.premierleague.com/en/news/2174907/fpl-basics-explained-how-to-make-transfers)
- Official guidance says progress above 100% indicates expected threshold crossing at the next deadline, but predictor output remains guidance rather than a guarantee. [Source](https://www.premierleague.com/en/news/2174907/fpl-basics-explained-how-to-make-transfers)
- Official FPL publishes dated post-change risers/fallers separately from the predictor; 17 September’s page reports completed overnight changes and links users to the 00:00 BST predictor. [Source](https://www.premierleague.com/en/news/2884829)
- Purchase price, current purchase cost, and manager-specific selling price are distinct: only £0.1m profit is retained per £0.2m rise, while falls reduce selling price £0.1m-for-£0.1m. [Source](https://www.premierleague.com/en/news/2174907/fpl-basics-explained-how-to-make-transfers)

### Official API field groups

- Live `bootstrap-static` exposes observed/current fields `now_cost`, `cost_change_event`, `cost_change_event_fall`, `cost_change_start`, `cost_change_start_fall`, `selected_by_percent`, `transfers_in`, `transfers_out`, `transfers_in_event`, and `transfers_out_event`. These fields were present for all 659 live player rows with no duplicate player IDs at access time. [API](https://fantasy.premierleague.com/api/bootstrap-static/)
- Live `bootstrap-static` also exposes predictor fields `price_change_calibrating`, `price_change_hourly_rate`, `price_change_locked_until`, `price_change_percent`, and nested `price_change_projections`. All 659 player rows contained these keys; every projection list contained three entries with `offset`, `projected_percent`, and `likelihood`. [API](https://fantasy.premierleague.com/api/bootstrap-static/)
- Official prose supports interpreting `price_change_percent` as current progress and `price_change_projections[*].projected_percent` as forecast progress. Offset units, numeric `likelihood` codes, `hourly_rate` units, and `locked_until` semantics are not published in reviewed Official guidance; project code must not invent those mappings. [Official guidance](https://www.premierleague.com/en/news/2174907/fpl-basics-explained-how-to-make-transfers) · [API](https://fantasy.premierleague.com/api/bootstrap-static/)

## Project interpretation

### What already exists as observed history

- `refresh_data` fetches Official `bootstrap-static`, processes `players.parquet`, then calls `append_price_snapshot`; each successful refresh therefore records observed `now_cost` after processing. [`commands.refresh_data`](../../../commands/refresh_data.py#L55-L59) · [`commands.refresh_data`](../../../commands/refresh_data.py#L123-L132)
- `append_price_snapshot` records `player_id`, `now_cost`, optional name/club, current-or-next Gameweek, and UTC `captured_at`, then rewrites prior history plus the new snapshot. [`commands.price_report`](../../../commands/price_report.py#L42-L69)
- `build_price_change_report` chooses latest, previous distinct timestamp, and first timestamp; it computes `change_since_refresh` and `change_since_season_start` after converting £0.1m integer costs to £m. [`commands.price_report`](../../../commands/price_report.py#L72-L134)
- CLI “Top risers” and “Top fallers” sort `change_since_refresh`; they are observed changes between refresh captures, not candidates predicted to move at tonight’s deadline. [`commands.price_report`](../../../commands/price_report.py#L153-L178)
- Checked-in 2026/27 history contains 21,141 rows across 34 captures from 2026-07-27T16:13:55Z through 2026-09-14T13:58:24Z, with no null core fields, duplicate `(player_id, captured_at)` keys, or negative costs. Capture sizes range from 563 to 658 players, so first/latest joins reflect changing player population. [`price_history.parquet`](../../../data/archive/2026-27/processed/price_history.parquet)
- At latest checked-in capture, report reconstruction returns 658 players; 18 moved by ±£0.1m versus previous refresh and 226 differed from first capture. These are retrospective snapshot deltas only. [`price_history.parquet`](../../../data/archive/2026-27/processed/price_history.parquet) · [`commands.price_report`](../../../commands/price_report.py#L72-L134)
- `player_performances.parquet` retains fixture-time `price`, `selected`, `transfers_balance`, `transfers_in`, and `transfers_out`; those historical fixture rows support retrospective analysis, not a live next-midnight forecast. [`features.processor`](../../../features/processor.py#L109-L141) · [`player_performances.parquet`](../../../data/archive/2026-27/processed/player_performances.parquet)

### What exists as current pressure or forecast input

- Archived 2026/27 raw bootstrap already contains observed change fields, transfer counts, `price_change_percent`, and complete `price_change_projections`; raw availability exists before any new feature work. [`bootstrap_static.json`](../../../data/archive/2026-27/raw/bootstrap_static.json)
- Standard `players.parquet` deliberately keeps `now_cost` and `selected_by_percent` but drops observed change fields, transfer counts, and all predictor fields because they are absent from `keep_player_cols`. [`features.processor`](../../../features/processor.py#L60-L81) · [data dictionary](../../../docs/data_dictionary.md#L42-L58)
- `price_history.parquet` stores only observed `now_cost` snapshots and cannot reconstruct contemporaneous progress, projected progress, likelihood, or transfer pressure after raw files advance. [`commands.price_report`](../../../commands/price_report.py#L42-L69)
- Availability capture converts the complete bootstrap `elements` list to a frame without field filtering, so an enabled in-window capture can preserve predictor columns; nested predictor lists are explicitly covered by hashing tests. No `data/availability-snapshots` package exists in checked-in `d7a6c82`, so this is a capture capability, not current durable evidence. [`commands.capture_availability_snapshot`](../../../commands/capture_availability_snapshot.py#L22-L25) · [`tests.test_availability_snapshots`](../../../tests/test_availability_snapshots.py#L74-L103)

### What would count as tonight’s forecast

- **Official forecast**: timestamped `price_change_percent`, next-deadline projected progress, and Official likelihood/status from current Official payload/UI. This is the authoritative available forecast, but project currently neither normalizes nor reports it. [Official guidance](https://www.premierleague.com/en/news/2174907/fpl-basics-explained-how-to-make-transfers) · [API](https://fantasy.premierleague.com/api/bootstrap-static/) · [`features.processor`](../../../features/processor.py#L60-L81)
- **Pressure indicator**: signed event transfer flow or Official current progress. This can explain direction but must not be relabeled as predicted outcome because Official says price changes depend on variable market factors and predictor indications are not guarantees. [Official guidance](https://www.premierleague.com/en/news/2174907/fpl-basics-explained-how-to-make-transfers)
- **Project-derived forecast**: a separately calibrated model trained on pre-deadline snapshots and subsequent Official outcomes. No such model, threshold calibration, probability, or evaluation exists in `commands.price_report`; snapshot deltas alone do not provide it. [`commands.price_report`](../../../commands/price_report.py)

### Transfer Plan display rules

- Label snapshot output **Observed price change**, with exact capture timestamp and comparison baseline (“since previous refresh” / “since first capture”). [`commands.price_report`](../../../commands/price_report.py#L72-L134)
- Label Official predictor output **Official next-deadline indication**, with fetched-at timestamp, current versus predicted progress separated, and non-guarantee copy. [Official guidance](https://www.premierleague.com/en/news/2174907/fpl-basics-explained-how-to-make-transfers)
- Label transfer counts **Transfer pressure**, never “will rise/fall.” [Official price mechanics](https://www.premierleague.com/en/news/2858775)
- Keep squad economics separate: Transfer Plan affordability must use current purchase cost plus manager-specific purchase/selling prices, not season or refresh price deltas. [Official selling-price rules](https://www.premierleague.com/en/news/2174907/fpl-basics-explained-how-to-make-transfers) · [user-picks schema](../../../docs/data_dictionary.md#L102-L113)

## Findings

### Evidence

- Project already has sound observed-history plumbing: current price capture, refresh-to-refresh delta, first-capture delta, and historical fixture price/transfer fields. [`commands.price_report`](../../../commands/price_report.py) · [`features.processor`](../../../features/processor.py#L109-L141)
- Project does not currently have a price-forecast report, despite Official predictor fields already arriving in raw bootstrap. [`bootstrap_static.json`](../../../data/archive/2026-27/raw/bootstrap_static.json) · [`features.processor`](../../../features/processor.py#L60-L81)
- 2026/27 changes the build-versus-buy question: Official FPL now supplies current and predicted progress, making direct, clearly attributed Official indication the smallest future product surface. [Official 2026/27 guidance](https://fantasy.premierleague.com/en/help/new)

### Alternatives

- Derive a custom transfer-count threshold from snapshots. Trade-off: requires denser timestamped inputs, known overnight outcomes, calibration by player ownership/status, and leakage-safe evaluation; Official formula and likelihood mapping remain undisclosed. [Official guidance](https://www.premierleague.com/en/news/2174907/fpl-basics-explained-how-to-make-transfers)
- Show only observed deltas. Trade-off: fully auditable but answers “what changed,” not “what may change tonight.” [`commands.price_report`](../../../commands/price_report.py)

## Decision

**Verdict**: Treat `commands.price_report`, price-history snapshots, and historical API change/transfer fields as observed intelligence; treat Official `price_change_percent` / projections as a distinct, timestamped next-deadline forecast; do not infer tonight’s result from refresh deltas.

**Recommended action**:
- Transfer Plan spec should reserve separate observed, pressure, and Official forecast labels.
- Any later implementation should retain Official predictor payload with fetch timestamp and freshness state before considering a custom predictor.
- Keep Official forecast optional and degradable; observed prices remain usable when forecast fields are absent or calibrating.

**Trigger / kill switch**:
- If Official removes or materially changes predictor fields/status semantics, hide forecast surface until field contract and UI mapping are revalidated.
- If future backtesting shows Official indication insufficient for decision support, open a separate calibrated-predictor research ticket rather than extending `price_report` semantics.

## Risks and unknowns

- Official API has no reviewed public field schema; numeric likelihood and offset semantics remain undocumented. [API](https://fantasy.premierleague.com/api/bootstrap-static/) · [Official guidance](https://www.premierleague.com/en/news/2174907/fpl-basics-explained-how-to-make-transfers)
- Price-history refresh cadence is user-driven, not fixed to 00:00 UK; missing refreshes can aggregate multiple Official changes into one observed delta. [`commands.refresh_data`](../../../commands/refresh_data.py#L123-L132) · [`commands.price_report`](../../../commands/price_report.py#L82-L91)
- First capture is a repository baseline, not guaranteed Official season-opening price for players added later; changing capture population confirms this limitation. [`price_history.parquet`](../../../data/archive/2026-27/processed/price_history.parquet)
- Archived raw bootstrap is latest-file state, not append-only predictor history; it cannot backtest past Official forecasts by itself. [`clients.fpl_api`](../../../clients/fpl_api.py#L47-L55)
- Official predictor can be stale relative to its 15-minute update cycle unless fetched near display time and marked with timestamp. [Official guidance](https://www.premierleague.com/en/news/2174907/fpl-basics-explained-how-to-make-transfers)
