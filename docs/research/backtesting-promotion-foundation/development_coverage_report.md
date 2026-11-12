# Development source coverage and training lineage inventory

**Updated:** 2026-11-12T20:30:15+00:00
**Data stamp:** Local inspection of `data/reports/readiness-source-pilot/v1/` and unsealed `data/archive/{2023-24,2024-25,2025-26}/`. Zero network calls; sealed `2026-27 GW6+` strictly untouched.
**Season:** 2025-26 (Dev, GW1–38); 2024-25 & 2023-24 (Seed archives).
**Status:** Local audit and code-lineage verification; empirical gate closed; no promotion authority.
**Purpose:** Establish per-deadline 2025-26 development coverage and verify source-authorized training lineage under approved `#175` Q1–Q10 rules to inform empirical route selection (`#178`).
**Scope:** Local file inspection, official arithmetic ledger check, and model/builder code trace only. No network retrieval, archive mutation, solver runs, model execution, or Candidate evaluation.
**Related:** [Candidate Evaluation and Promotion Readiness](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/174) · [Input evidence and freshness rules (#175)](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/175) · [Development coverage ticket (#176)](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/176) · [Empirical admission route (#178)](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/178) · [input-evidence-contract.md](input-evidence-contract.md) · [readiness-source-pilot.md](readiness-source-pilot.md)
**Artifact:** [development_coverage_inventory.csv](development_coverage_inventory.csv) · [development_coverage_sources.csv](development_coverage_sources.csv) · [development_coverage_assessment.json](development_coverage_assessment.json) · [development_coverage_inventory.py](development_coverage_inventory.py)

## Sources

- **Quarantined 2025-26 GW1–2 pilot**: `data/reports/readiness-source-pilot/v1/` (`07`–`17`, `attempts.jsonl`, `summary.json`). SHA-256 verified against `summary.json`.
- **Unsealed archives**: `data/archive/2023-24/{processed,vaastav}/`, `data/archive/2024-25/{processed,vaastav}/`, `data/archive/2025-26/{processed,raw}/`.
- **Code modules**: `features/builder.py`, `backtesting/walkforward.py`, `backtesting/walkforward_solve.py`, `backtesting/forecast_adapter.py`, `backtesting/input_pilot.py`, `models/def_xg_shrink_challenger.py`, `models/adaptive_causal_challenger.py`, `models/club_def_prior_challenger.py`.
- **Source boundary**: Pre-`#175` diagnostics in `backtesting/input_pilot.py` / [input_evidence_fields.csv](input_evidence_fields.csv) mark all 9 groups `unresolved` (`timing_basis="unknown"`) because bounded-reconstruction rules from `#175` are not yet codified into `input_pilot.py` or `data_admission.py`.

## Decision

1. **Quarantined pilot satisfies `#175` Q1–Q10 bounds for GW1 anchor and GW2 inputs only, pending code activation (`#178`)**:
   - **GW1 (`07-opening_bootstrap.raw`)**: `685` players (`0` `element_type==5` managers), `637` selectable (`min_15_cost = 640/1000`), `is_next=True`, commit `4h 37m 12s` and bounded `capture_lower` `5h 07m 12s` pre-deadline (`<= 8h` target).
   - **GW2 (`09-origin_bootstrap_pilot.raw`, `11-fixture_pilot.raw`)**: `698` players (`0` managers), `641` selectable, `541` unflagged null-chance (`is_next=True`, commit `4h 38m 45s`, `capture_lower` `4h 59m 53s` pre-deadline `<= 8h`); `60` horizon fixtures GW2–7 (`10/GW`, commit `2d 09h 30m 57s` pre-deadline; parent commit absent locally so fallback `capture_lower = 7d 00h 00m 00s <= 7d`).
2. **Continuous 38-GW 2025-26 replay cannot run without bounded acquisition (`#178`)**:
   - GW1 6-GW schedule and GW3–38 pre-deadline `bootstrap-static` / `fixtures.csv` snapshots are absent locally (`183` of `342` GW×field evaluations absent).
   - `data/archive/2025-26/raw/bootstrap_static.json` is a terminal May 2026 snapshot (`38/38` finished events) and cannot supply point-in-time inputs.
3. **Training lineage invariant holds across all model paths**:
   - `model.fit()` receives strictly current-season pre-target rows (`gameweek_id < gw`); zero prior-season raw rows enter `fit()`. Prior-season `2024-25` seed reaches `features/builder.py` only when passed explicitly (`use_archive_seed=False` in `walkforward.py`, which does not auto-default seed for `2025-26`).

## Method

**Method type**: Offline byte/hash verification, schema and freshness check under `#175` Q1–Q10 bounds, official component-to-points ledger arithmetic audit, and codebase lineage trace.

**Procedure**:
1. Verify all `summary.json` SHA-256 digests in `data/reports/readiness-source-pilot/v1/` and extract collector, commit, deadline, `max(news_added)`, `element_type`, and `can_select` telemetry.
2. Hash and inspect all non-sealed archives (`2023-24`, `2024-25`, `2025-26`) including `processed/`, `vaastav/`, and `2025-26/raw/`; exclude `2026-27` via explicit path guard.
3. Execute full `2025-26` component-to-`total_points` reconciliation (including Defensive Contributions thresholds `>=10` DEF, `>=12` MID/FWD) across all `29,747` rows in `player_performances.parquet`.
4. Evaluate exact `features/builder.py` seed resolution (`MIN_PRIOR_APPEARANCES=8`, `MIN_PRIOR_MINUTES=450`) against GW1 (`07`) and GW2 (`09`) elements and inspect active Champion/Challenger `fit()` code paths.
5. Export companion CSV/JSON files and regenerate this markdown note directly from computed outputs.

### Metric Definitions & Direction

| Metric | Symbol | Definition / Formula | Direction | Ideal / Benchmark | Description |
|---|---|---|---|---|---|
| **Field Coverage Status** | `status` | Per-`(gw, field_group)` disposition (`evidenced_bounded`, `carried_from_gw1`, `evidenced_empty`, `partial`, `absent`) | Context (`evidenced_*` $\uparrow$) | Required groups `evidenced_*` before replay | Classifies retained local bytes vs Q1–Q10 rules; separate from promotion verdict. |
| **Snapshot Bounded Age** | `deadline - capture_lower` | Pre-deadline distance using `max(commit - 1800s, max(news_added))` for bootstraps or fallback `prev_gw_deadline` for fixtures | Lower $\downarrow$ within target | Bootstraps `<= 8h` (`24h` ceil); schedule `<= 7d` | Earliest plausible pre-deadline capture age under `#175` Q1b/Q7. |
| **Seed Direct-Prior Count** | `player_prior_eligible` | GW players matching 2024-25 seed (`code` then `name`) with `apps >= 8` & `mins >= 450` | Context | Full verified seed coverage | Counts players receiving individual 2024-25 prior rates vs `position_price_prior` fallback. |
| **Ledger Arithmetic Mismatches** | `mismatches` | Count of `player_performances.parquet` rows where `total_points != sum(native components)` | Lower $\downarrow$ | `0` | Tests internal scoring consistency; does not replace independent `+24h` settlement receipts. |
| **Digest Integrity** | `sha256` | Exact SHA-256 byte equality vs `summary.json` / disk files | Exact match | 100% matched | Guards against byte corruption; hash alone does not attest capture time. |

## Findings

### Retained Source & Archive Inventory (`development_coverage_sources.csv`)

| Storage Location | Artifact Name | Bytes | Rows | SHA-256 | Temporal Basis | Status |
|---|---|---:|---:|---|---|---|
| `data/reports/readiness-source-pilot/v1/` | `07-opening_bootstrap.raw` | 106,252 | 685 | `eee31c9ece48...` | GW1 pre-deadline (2025-08-15T12:52:48+00:00) | **evidenced_bounded** |
| `data/reports/readiness-source-pilot/v1/` | `09-origin_bootstrap_pilot.raw` | 104,780 | 698 | `4fc61f6f89d9...` | GW2 pre-deadline (2025-08-22T12:51:15+00:00) | **evidenced_bounded** |
| `data/reports/readiness-source-pilot/v1/` | `11-fixture_pilot.raw` | 56,644 | 60 | `8c4f54bbb1d7...` | GW2-7 schedule (2025-08-20T07:59:03+00:00) | **evidenced_bounded** |
| `data/archive/2023-24/processed/` | `players.parquet` | 111,489 | 865 | `4f767f37274e...` | prior-season seed processed archive | **partial** |
| `data/archive/2023-24/processed/` | `player_performances.parquet` | 875,411 | 29725 | `5af4eedd7d91...` | prior-season seed processed archive | **partial** |
| `data/archive/2023-24/processed/` | `fixtures.parquet` | 12,255 | 380 | `2d64f8b86485...` | prior-season seed processed archive | **partial** |
| `data/archive/2023-24/vaastav/` | `fixtures.csv` | 712,532 | 380 | `d8521bdbb80e...` | post-season vaastav mirror archive (unpinned commit manifest) | **partial** |
| `data/archive/2023-24/vaastav/` | `gws/merged_gw.csv` | 4,997,188 | 29725 | `e9c09c8856f1...` | post-season vaastav mirror archive (unpinned commit manifest) | **partial** |
| `data/archive/2024-25/processed/` | `players.parquet` | 105,384 | 804 | `76ff58f701b8...` | prior-season seed processed archive | **partial** |
| `data/archive/2024-25/processed/` | `player_performances.parquet` | 861,891 | 27605 | `ceed6b878a19...` | prior-season seed processed archive | **partial** |
| `data/archive/2024-25/processed/` | `fixtures.parquet` | 12,232 | 380 | `2341493d57b8...` | prior-season seed processed archive | **partial** |
| `data/archive/2024-25/vaastav/` | `fixtures.csv` | 751,413 | 380 | `ce696e187569...` | post-season vaastav mirror archive (unpinned commit manifest) | **partial** |
| `data/archive/2024-25/vaastav/` | `gws/merged_gw.csv` | 5,125,595 | 27605 | `5bbbcba6353b...` | post-season vaastav mirror archive (unpinned commit manifest) | **partial** |
| `data/archive/2025-26/processed/` | `players.parquet` | 108,626 | 841 | `6f4e1cd553f8...` | post-season processed archive | **partial** |
| `data/archive/2025-26/processed/` | `player_performances.parquet` | 713,470 | 29747 | `64db5dc13408...` | post-season processed archive | **partial** |
| `data/archive/2025-26/processed/` | `fixtures.parquet` | 215,444 | 380 | `9821829c8ea4...` | post-season processed archive | **partial** |
| `data/archive/2025-26/raw/` | `bootstrap_static.json` | 2,743,417 | 841 | `f108d27b4fb1...` | terminal May 2026 raw snapshot (38/38 finished) | **unusable_as_point_in_time** |
| `data/archive/2025-26/raw/` | `fixtures_all.json` | 2,551,440 | 380 | `59b917fddd3f...` | terminal full-season fixtures JSON (unusable as point-in-time schedule) | **unusable_as_point_in_time** |

- `2025-26/raw/` additionally holds `38` `event_*_live.json` and `841` `element_summary_*.json` files (`881` total files), ingested post-season without independent `>= max(kickoff)+24h` or `data_checked` receipts.
- `2024-25/processed/players.parquet` contains `804` rows: `784` players (`position_id` 1–4) plus `20` Assistant Managers (`position_id == 5`, `322` performance rows). Both `2024-25` and `2025-26` have `0` duplicate permanent player `code`s.
- All `29,747` rows in `2025-26/processed/player_performances.parquet` (`GW 1..38`, `38` GWs) pass exact 2025-26 official component arithmetic reconciliation (`0` mismatches).

### Per-Deadline Coverage Summary (`development_coverage_inventory.csv`, 342 evaluations)

- **`evidenced_bounded` (8)**: GW1 `opening_anchor`; GW1–2 `eligible_universe`, `price_club_position`, `availability`; GW2 `fixture_schedule` (`11-fixture_pilot.raw`, `gw2_7_rows=60`, `commit=2d 09h 30m 57s` pre-GW2). Note: `collector_uses_naive_today=True`; pre-`#175` `input_pilot.py` still marks these `unresolved` until `#178` codifies Q1–Q10 rules.
- **`carried_from_gw1` (37)**: GW2..38 `opening_anchor` continuity via `ReplayState`.
- **`evidenced_empty` (1)**: GW1 `historical_performance` (0 prior current-season matches by definition).
- **`partial` (113)**: GW2..38 `historical_performance` (`37`); GW1..38 `prior_season_training` (`38`); GW1..38 `settled_outcomes` (`38`). Bytes exist in `processed/`, `vaastav/`, and post-season `raw/`, but lack `#175`-compliant pre-deadline/post-settlement capture receipts and pinned upstream commit manifests.
- **`absent` (183)**: GW1 and GW3..38 `fixture_schedule` (`37`); GW3..38 `eligible_universe` / `price_club_position` / `availability` (`108`); GW1..38 `shared_chip_calendar` (`38`).

### Seed Resolution & Model Training Lineage

- **GW1 Bootstrap (`685` players vs `2024-25/processed`)**: `511` matched by `code`, `0` matched only by `name_to_seed_id`, and `174` unmatched newcomers. Because `features/builder.py` requires `apps >= 8` and `mins >= 450`, only **`302`** receive individual 2024-25 priors (`has_prior_seed=True`), while `209` below-threshold matched players plus `174` newcomers (`383` total) take `position_price_prior` fallbacks. (GW2 bootstrap `698` players: `304` individual priors, `210` matched fallbacks, `184` unmatched.)
- **Feature Builder vs Walkforward Seed Wiring**: `backtesting/walkforward.py`, `backtesting/walkforward_solve.py`, and `backtesting/forecast_adapter.py` pass `use_archive_seed=False` to `build_features()`. `_default_seed_season_for_data_dir()` auto-selects `2023-24` only when evaluating `2024-25`, returning `None` for `2025-26` unless `seed_season="2024-25"` or `seed_processed_dir` is explicitly provided. Cold-start seed priors deactivate globally in `build_features()` once current-season match rows exist.
- **Zero Prior-Season Rows in `model.fit()`**: `walkforward.py` feeds `history_before_target(df_perf, gw)` (`gameweek_id < gw`) exclusively to `model.fit()` across all selection models (`DefXgShrinkChallengerModel`, `AdaptiveCausalChallengerModel`, `ClubDefPriorChallengerModel`, inheriting `LearnedStartChallengerModel`).

## Risks and unknowns

1. `08-opening_bootstrap-commit.raw` and `10-origin_bootstrap_pilot-commit.raw` are unsigned GitHub bot commits; `12-fixture_pilot-commit.raw` is GPG-signed but its parent commit `46277afda009...` is not retained locally, forcing `capture_lower` to fall back to `GW1` deadline (`7d`).
2. Existing `backtesting/input_pilot.py` and `backtesting/data_admission.py` still enforce pre-`#175` checks (`timing_basis="unknown"`, all pilot groups `unresolved`); empirical admission stays closed until `#178` decides the route and `#182` gates implementation.
3. Terminal `2025-26/processed/players.parquet` contains `841` season-cumulative players (`156` more than GW1), illustrating look-ahead leakage if terminal tables replace GW-by-GW `fplcache` snapshots.
4. `2024-25/processed/players.parquet` retains `20` `position_id == 5` managers (`322` perf rows); any `#178` seed ingestion adapter must continue isolating or filtering `element_type == 5`.

## Agent Prompt

```text
Reproduce offline from repo root:
uv run python docs/research/backtesting-promotion-foundation/development_coverage_inventory.py

Inputs (read-only; never inspect data/archive/2026-27/):
- data/reports/readiness-source-pilot/v1/
- data/archive/2023-24/, data/archive/2024-25/, data/archive/2025-26/
- features/builder.py, backtesting/walkforward.py, backtesting/walkforward_solve.py, backtesting/forecast_adapter.py, models/

Outputs regenerated beside this note:
- docs/research/backtesting-promotion-foundation/development_coverage_inventory.csv (status breakdown, source_sha256, coverage_count)
- docs/research/backtesting-promotion-foundation/development_coverage_sources.csv (sha256, size_bytes, row_count, admission_status)
- docs/research/backtesting-promotion-foundation/development_coverage_assessment.json (freshness bounds, gw1_seed_resolution, ledger_reconciliation, code_sha256)
- docs/research/backtesting-promotion-foundation/development_coverage_report.md (cache of companion cells)

Keep scratch only in .tmp/agent/ and delete scratch before finishing. Validate with:
uv run pytest tests/test_development_coverage_inventory.py
```
