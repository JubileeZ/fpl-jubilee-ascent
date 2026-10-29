# Highest-owned feasible squad: data feasibility and evaluation meaning

**Updated**: 2026-10-29T13:42:04+07:00\
**Data stamp**: Local unsealed 2023-24/2024-25/2025-26 ownership-price metadata and three public GW1-date bootstrap samples inspected 2026-10-29. No points/outcome analysis or sealed 2026-27 access.\
**Season**: Historical unsealed seasons only.\
**Status**: Q28 opening-anchor continuous benchmark agreed; source admission and implementation pending.\
**Purpose**: Assess user's simpler highest-owned legal squad anchor, including refreshed anchors at each planning origin.\
**Related**: [Foundation](backtesting-promotion-foundation.md), [independent review](independent-review.md), [preflight](preflight-plan.md).\
**Artifacts**: [Local coverage](ownership_local_coverage.csv), [downloaded-sample metadata](ownership_snapshot_samples.csv), [mirror provenance registry](ownership_snapshot_provenance.csv), [audit runner](audit_ownership_sources.py).

## Findings

User's anchor is valid initial benchmark concept. No need to insist on personal squad or multiple hand-designed archetypes before testing it. Constructing numerical anchor appears feasible from available fields; no anchor optimization performed, so feasible optimum not yet computed or certified.

Local archives contain useful ownership counts/prices, but precise deadline semantics remain unresolved. Parent fetched/decompressed three unsealed GW1-date bootstrap samples and verified fields/ranges/IDs. Follow-up checked historical collector/workflow, recorded UTC commits before each payload deadline, and matching immutable content hashes. Narrow mirror-provenance check passes; freshness/eligibility admission and complete replay inputs still required.

Main methodological distinction: starting once and preserving each model's evolving team measures sustained transfer management. Replacing team with new ownership template each deadline measures local intervention from standardized external states. Both useful; neither can silently stand for other.

## Sources

Primary sources accessed 2026-10-29:

- [Official squad rules](https://www.premierleague.com/en/news/2174419/fpl-basics-how-to-pick-a-squad): full fifteen, initial budget, positional quotas, club cap.
- [Official ownership description](https://www.premierleague.com/en/news/4680259/whats-new-in-202627-fantasy-more-ways-to-view-your-squad/): ownership fraction per player.
- [Randdalf/fplcache](https://github.com/Randdalf/fplcache): official bootstrap mirror; four scheduled collections daily according to README.
- [Collector](https://raw.githubusercontent.com/Randdalf/fplcache/main/cache.py) and [workflow](https://raw.githubusercontent.com/Randdalf/fplcache/main/.github/workflows/cache.yml): capture/file generation and scheduling.
- Sample pages: [2023-08-11](https://github.com/Randdalf/fplcache/blob/main/cache/2023/8/11/1231.json.xz), [2024-08-16](https://github.com/Randdalf/fplcache/blob/main/cache/2024/8/16/1238.json.xz), [2025-08-15](https://github.com/Randdalf/fplcache/blob/main/cache/2025/8/15/1252.json.xz).
- [Vaastav dictionary](https://github.com/vaastav/Fantasy-Premier-League/blob/master/DATA_DICTIONARY.md), [timing caveat](https://github.com/vaastav/Fantasy-Premier-League/blob/master/README.md), [2023 preseason commit](https://github.com/vaastav/Fantasy-Premier-League/commit/a5fe899bd3104fd0f197a2e5f9cef7121a792a21), [2025 preseason commit](https://github.com/vaastav/Fantasy-Premier-League/commit/46277afda009b340e738336dabc4b0822dd80c57): fallback semantics/source recovery, not blanket timing certification.
- O'Brien et al., [Identification of skill in an online game](https://arxiv.org/abs/2009.01206), 2020: empirical template-team patterns, not validation of this exact benchmark.
- Agarwal et al., [RL theory book](https://rltheorybook.github.io/rltheorybook_AJKS_V3.pdf), initial-state/value definitions: different restart distributions define different policy-value questions.

**Source boundary:** Three subagents independently checked local data, external acquisition, and methodology. Parent reproduced coverage and fetched sample contents afterward. No model/solver/backtest result or achieved inferential error guarantee follows from metadata availability. Unknown timing is unresolved, not automatically demonstrated leakage.

## Method and reproducibility

Local population: performance IDs whose season metadata position is 1-4, excluding Assistant Manager. Audit uses terminal metadata only to define coverage population; does not certify those fields as valid historical anchor inputs. Grain player × fixture × GW. Window unsealed season GWs, with GW1 subset. Read schemas/raw samples before quality aggregation; no points/minutes/outcome columns used by saved runner.

Quality checks: duplicate keys, numeric parse failures, negative price/owner count, represented GWs, multiple-fixture consistency, snapshot/deadline-column presence. Source table hashes retained. Findings in `ownership_local_coverage.csv` columns `represented_gws`, `gw1_unique_players`, `duplicate_keys`, `invalid_numeric_cells`, `negative_price_or_ownership_cells`, and `player_gws_with_disagreeing_price_or_ownership`.

External population: all `elements` in each explicitly listed unsealed bootstrap sample. Fetch/decompress in memory; inspect raw field samples; audit IDs, required metadata, price positivity, ownership range, and position codes. Raw payloads not persisted. `ownership_snapshot_samples.csv` records immutable URL/full commit, compressed SHA256, row counts, quality checks, and payload's GW1 deadline.

Run local audit: `uv run python docs/research/backtesting-promotion-foundation/audit_ownership_sources.py`.

Run local plus explicit public sample fetch: same command with `--fetch-samples`. Requires network; not a test command. Existing local interpreter usable if uv cache unavailable. Coverage/sample CSVs regenerated by runner. Separate provenance registry records public GitHub API/history and immutable-byte review, not fabricated capture times.

## Local data: present and missing

For each unsealed season, `data/archive/<season>/processed/player_performances.parquet` retains `player_id`, `fixture_id`, `gameweek_id`, `selected`, and `price`. `selected` is count, price in tenths of million. These are fixture-grain stock observations, not additive events.

Coverage spans requested gameweek labels, required numeric ownership/price cells populated/nonnegative, and repeated-fixture price/count values consistent in audited groups; see companion cells for exact counts. Collapse to one admissible player/GW observation; summing double-gameweek ownership or prices wrong.

Missing from audited archives: processed historical player snapshots/price history. Reconstructed earlier seasons lack processed deadline column; later season has it. No capture timestamp on historical ownership-price rows. Complete eligible universe still needed for blank GWs; fixture rows alone insufficient. Terminal `players.selected_by_percent`/`now_cost` not historical opening observations.

Presence of GW1 field does not establish deadline time. Post-match collection also does not prove a field invalid if that field intrinsically locked earlier. Prefer snapshot provenance until semantics independently established.

## External data: obtainable and content-checked

Public fplcache files for all three listed GW1 dates were retrieved/decompressed successfully. Parent's content checks found required fields present, unique IDs, positive prices, and reported ownership within valid range; exact source/sample/quality cells in `ownership_snapshot_samples.csv`.

This is still a three-sample check, not complete per-deadline season coverage. Collector uses timezone-naive `datetime.today()`; filename alone insufficient. Follow-up provenance record corroborates source chronology using recorded UTC commits and matching pinned content. Several-hours-old ownership valid as recorded signal but stale, not exact final-deadline census. Freshness/eligibility policy not yet adopted.

### Completed narrow publication-provenance check

[Provenance registry](ownership_snapshot_provenance.csv) records full Git commits, UTC author/committer times, file-added status, Git blob IDs, payload deadlines, compressed hashes, and match flags. Each selected path returned one history commit; author and committer UTC times match explicit UTC commit message and precede corresponding GW1 deadline.

Verified immutable commits: [2023](https://github.com/Randdalf/fplcache/commit/1e066f7405a23e0f00917706b297ec35c4218062), [2024](https://github.com/Randdalf/fplcache/commit/2ae22a16ee2280311de07b8b5ee3b8393377a178), [2025](https://github.com/Randdalf/fplcache/commit/4aaec38e6b5f5ade8b63162a3678ce67148adb67). Inspect path history through public GitHub commits API with `path` parameter; inspect commit file-added metadata; fetch raw file at full commit and compare SHA256 against sample companion.

Historical collector/workflow at each commit, not just current main, corroborates fetch then datetime filename/LZMA write, Ubuntu runner, scheduled collections, and UTC commit message. Pinned raw bytes matched prior moving-branch sample hashes, then parent reran content audit against immutable URLs.

Boundary: Git timestamps can be assigned and mirror is third-party record, not independently attested official server receipt. Commit follows request; exact fetch seconds not stored. Metadata supports practical pre-deadline source chronology; it does not certify exact ownership at lock or every future sample. First opening samples approximately five hours before deadline, not final census. No narrow source-fetch blocker remains for anchor-construction feasibility; actual constraint solve/eligibility admission still pending.

Acquisition proposal: enumerate files before each target origin; select latest admissible source under predefined freshness policy; pin commit and content hash; validate schema/eligibility/time; store provenance separately from model inputs. No historical archive files edited by audit.

Vaastav historical commits are fallback for dated preseason ownership/price/universe. Early preseason snapshot not automatically final-GW1 population. Algebraic opening-price reconstruction cannot recover opening ownership, missing removed players, or whether later arrival existed at opening deadline.

## Anchor definition and rationale

For origin g, use aligned reported ownership p_i,g and binary membership x_i. Maximize sum(p_i,g × x_i), subject to full fifteen, native position quotas, club cap, origin eligibility, and declared total capital. Opening case uses initial budget; price is affordability constraint, not ownership/price ratio.

For true ownership marginals, E[|S intersect M|] = sum over i in S of P(i in M). Linearity of expectation needs no independence assumption. Thus objective maximizes expected overlap with random manager's squad, conditional on feasible set. Rounded reported percentages approximate true marginals. Does not identify most probable complete squad or prove universal transfer superiority.

Use constrained optimization, not greedy picking that can miss best feasible combination. Predefine deterministic secondary tie-breaks independent of evaluated forecasts/outcomes; document near ties for later sensitivity. Counts and percentages equivalent only with same population/time denominator; summing fixture counts cannot recover manager denominator.

### Metric definitions

- **Ownership overlap objective:** Sum of ownership fractions for selected players. Higher ↑. Ideal benchmark = maximum over declared feasible fifteen; theoretical maximum fifteen. Optimum not computed by this audit.
- **Net policy advantage:** Candidate actual points after transfer penalties minus Champion equivalent, conditional on common initial state/policy. Higher ↑; neutral benchmark zero. No policy scores computed here.
- **Missing/duplicate/invalid cells:** Counts under explicitly declared population/keys/ranges. Lower ↓; ideal zero. Quality compliance alone does not prove deadline causality.
- **Snapshot age:** Origin time minus verified capture time. Lower ↓ for freshness, admissible only nonnegative; maximum acceptable age not selected yet. No timestamp certification performed.

## Reset choices and their claims

### A. One opening anchor, independently evolving season paths

Recommended primary sustained-management benchmark. Lock common fifteen at GW1 deadline; choose starters/bench/captain, then begin transfers GW2 under native rules. Otherwise unlimited preseason transfers erase anchor immediately. Existing archive adapter starts with empty picks/redraft; cannot use it unchanged.

Preserve separate evolving ownership, acquisition/sale prices, bank, FT balance, chip state, and decisions. Forecast six weeks ahead each deadline; execute immediate decision; replan next week. Later market ownership does not give free squad reset.

One reference per season is sufficient to define initial reproducible benchmark; no mandatory archetype expansion. Scope claim to market-informed starting condition, and expand sensitivity if anchor choice materially affects conclusions. Personal squad optional.

### B. Fresh market-template anchor every deadline

Valid local intervention diagnostic: which model recommends better immediate action from common standardized state at origin? Build anchor using origin-known data, solve horizon, score immediate action, discard branch.

Summed origin scores not realizable continuous-season management score. Free changes between external anchors erase prior transfer investments, saved FTs, and retained value. This may miss mechanism that buys for later reward. Refreshed origins can parallelize but need roughly one policy solve/model/origin, plus reusable anchor construction; not automatic optimizer savings.

Declare midseason reference finances: total capital minus squad cost equals bank, not full budget plus free owned team. Acquisition values and FT/chip balances need explicit standardized assumptions. These do not recover average real-manager state.

### C. Each anchor starts multiweek branch

Replan/evolve through branch if modeling actual product behavior. Committing all originally planned future actions tests open-loop plan instead. Overlapping branches reuse match outcomes and cost additional planning calls; not independent seasons. Terminal horizon truncates long-term transfer value. Sparse predeclared origins useful sensitivity option.

## Decision

1. **GW1 Opening Anchor Benchmark**: Adopt one highest-owned feasible GW1 squad per season as the standardized initial benchmark condition (Q28), locked at first deadline.
2. **Continuous Path Evolution**: Lineup and captain evaluated in GW1; transfers commence at GW2 with native FT state, preserving independent finances, ownership, and chips.
3. **Local Reset Diagnostic Separation**: Periodic refreshed anchors remain optional local-intervention diagnostics, never substituted for continuous season score.

## Risks and unknowns

- **Pre-deadline Timing Latency**: Pre-deadline public mirror snapshots are captured hours before lock; subtle late price or ownership movements may remain unobserved.
- **Lexicographic Tie-breaking**: Multiple feasible squads can achieve equal total ownership under £100m budget; secondary objective tie-breaks must remain model-neutral and deterministic.
- **Population Representativeness**: The highest-owned template represents aggregate market selection, not individual manager cohort distributions.

## Agent Prompt

```text
Refresh ownership-anchor-feasibility.md and its companions.
Read archive-testing and INDEX. Restrict data to explicitly unsealed sources.
Recompute metadata via audit_ownership_sources.py; --fetch-samples explicitly accesses public URLs.
Preserve local grain/population and source hashes. No outcome analysis in metadata audit.
Do not promote coverage or filename timestamps into proof of causal timing.
Snapshot samples are three explicit files, not certified full-season coverage.
Separate anchor optimization from transfer-model evaluation and reset diagnostics from sustained paths.
Preserve Q28 opening-anchor continuous choice; no Champion/ledger/holdout changes while refreshing evidence.
```
