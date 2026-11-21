# Pre-slate Candidate Search — 2026-11-21

**Disposition:** `ext_01_1_a10` passed S-1. Its single reserved S-2 filter is blocked at GW24 by a missing zero-gap solver certificate. No finalist yet.

## Evaluation contract

- Confirmed Champion: `def_xg_shrink_challenger` from [model selection](../../../config/model_selection.json).
- Development: 2025–26 (`S-1`), seed 2024–25. Untuned Historical Filter: 2024–25 (`S-2`), seed 2023–24. Exclude Assistant Managers. One `S-2` look after source and parameter pin. 2026–27 outcomes sealed.
- [ADR 0069](../../adr/0069-annual-rolling-validation-and-dual-tier-promotion.md): full GW1–38 point-in-time archive replays plus admitted empirical prefix parity. Independent six-GW Strategic solves from common neutral GW1 ownership anchor. Net FPL points = gross points minus transfer-hit deductions, cumulative; higher better; Champion delta strictly positive in each season, with all applicable projection and segment guards passing. Rank by mean of season deltas, then `S-2` delta, then model name. Paired non-wrapping moving block bootstrap (`L=5`) describes historical evidence. Later confirmation retains `M<=2` and `FWER<=0.05`.
- Re-ran `load_empirical_manifest_bundle(..., require_admitted=True)` on [S-1 GW1–7](../../../config/dev_mirror_2025_26_manifest.json) and [S-2 GW1](../../../config/dev_mirror_2024_25_manifest.json). Both admitted. Candidate-specific parity results below.

## Historical schedule gap and recovery

**S-1 six-GW forecast schedule as of each origin.** [Archive testing guide](../../testing/archive-testing.md) discloses residual terminal FDR and player-universe limitations. Separate issue here: terminal fixture Gameweek assignment transfers future rescheduling decisions into earlier optimizer horizons. [Feature builder](../../../features/builder.py) selects forecast fixtures using supplied Gameweek IDs; dropping terminal player columns and strict fit cutoff do not remove schedule hindsight.

| 2025–26 origin | Measured discrepancy | Consequence |
|---|---|---|
| GW24, 2026-01-31 13:30 UTC | Wolves–Arsenal (310) in GW31 in pinned mirror and GW26 in terminal archive. League announced GW26 on 2026-02-03. | Terminal schedule puts fixture inside GW24–29 horizon before public announcement. |
| GW30, 2026-03-14 13:30 UTC | Brighton–Chelsea (333) in GW34 with away FDR 3 in 2026-03-13 mirror. Terminal GW33, away FDR 4. | Terminal schedule assigns upcoming double and blank before April announcement. |
| GW32, 2026-04-10 17:30 UTC | Latest pinned fixture table still dated 2026-03-13. Fixtures 332–334 assigned GW34 despite confirmed GW33 assignments on 2026-04-05. Kickoffs confirmed 2026-04-07. | Mirror understates announced GW33 and overstates GW34. Official notices recover these three assignments and kickoffs, but lack a complete issue-time fixture table with FDR. |

Evidence: [fixture audit CSV](pre_slate_fixture_audit_2026-11-21.csv) contains paired fixture rows, UTC deadlines and pinned digests. Reproduced by joining named fixture IDs in manifest-selected `data/reports/empirical_mirrors/2025-26/fixtures/*.csv` to `data/archive/2025-26/processed/fixtures.parquet`; verified mirror SHA256 before comparing. Match timing from [February FPL notice](https://www.premierleague.com/en/news/4579676), [April FPL notice](https://www.premierleague.com/en/news/4624106) and [April kickoff confirmation](https://www.premierleague.com/en/news/4624588).

Historical bootstrap feed contains deadline timestamps and club/player metadata, with no fixtures table. Checked pre-GW32 alternate public snapshots. FPL-Elo-Insights retains football schedule rows with third-party IDs and no official FPL FDR table. Other checked API snapshot repositories lacked contemporaneous GW32 records. [Pinned alternate snapshot](https://github.com/olbauday/FPL-Elo-Insights/blob/acd8b36b24038426773dfdca00154a7949779e0c/data/2025-2026/By%20Gameweek/GW33/fixtures.csv)

Recovered S-1 GW8–38 schedules from an hourly mirror of the official FPL all-fixtures endpoint. Verified 380 unique fixture IDs, legal club/difficulty fields, pre-deadline capture bounds and SHA-256 for every used snapshot. Kept admitted fixture bytes for GW1–7. GW32 captures all three GW33 reassignments and their kickoffs/difficulties. [Pinned S-1 source manifest](s1_historical_fixture_sources.csv) · [GW32 capture](https://github.com/arshadfaizan360/fpl-data-mirror/blob/665a7b1d9203abbd14e1e23ee2aac9aa1272224f/fixtures.json)

S-1 prefix history parity preflight found a GW7 archive revision in creativity/ICT for player 12, fixture 59. The Champion forecast varied by up to 0.001805 xP per player-fixture. Stage admitted prior settlement bytes for GW1–7. Use complete pre-issue archive performance rows for GW8–38, bounded by GW, kickoff and the issue fixture's completed flag. Later revisions remain an unmeasured limitation outside the admitted prefix. Full empirical admission beyond the required prefixes does not apply to historical qualification.

[S-1 replay runner](run_s1_replay.py) verifies joint fixture/market snapshot identity, full forecast fixture coverage including blanks, and projection component reconciliation before passing the table to the native zero-gap solver. All three S-1 arms completed GW1–38 under runner commit `fa52dc50` and protocol `1775d3f56a224bb1ad2118d720219fd38f072ef550fca78bdf2e5bcd5fda0135`. Shared neutral opening anchor `opening-anchor-809d4afb3e40c205`. Independently rebuilt admitted GW1–7 forecasts and outcomes. 21/21 model-origin checks matched solver hashes and settled scores exactly, with zero fixture-projection component difference. [Admitted prefix parity](prototypes/ext_01_1/s1_prefix_parity.csv)

S-2 schedule preflight verified 38 pinned pre-deadline fixture tables and 19 dated kickoff amendments across GW23, GW33 and GW35 origins. Overlay amends kickoffs with known announcement dates and preserves recorded FPL Gameweek assignments and latest observed FDR. Unresolved conditional Villa–Spurs kickoff at GW33 retains the contemporaneous API time. GW1 admitted inputs preserved. [Dated amendments](s2_historical_fixture_amendments.csv) · [April 17 circular](https://resources.premierleague.pulselive.com/premierleague/document/2025/04/17/cb7dbd1f-35cc-4a63-96ef-8a7febb8159c/Fixture-Amendments-23-Season-2024-25.pdf)

## S-1 development selection

| Candidate | Candidate net | Champion net | Net delta | Segment deltas GW1–4 / GW5–19 / GW20–38 | Projection guards | Paired L=5 MBB 95% interval (points/GW) |
|---|---:|---:|---:|---:|---|---:|
| `ext_01_1_a05` | 2,240 | 2,167 | +73 | +5 / +36 / +32 | 15/15 PASS | −0.42 to +3.95 |
| `ext_01_1_a10` | 2,249 | 2,167 | +82 | +7 / +19 / +56 | 15/15 PASS | −2.03 to +5.74 |

Both variants meet positive Dev net delta and segment floors. Highest eligible S-1 delta selects `ext_01_1_a10`, `a=1.0`. Pin binds both model closures, reviewed source SHA-256, complete S-1 grid report, admitted prefix parity and derived guard margins. S-2 launcher reserves one immutable look for this lane and permits identical retries. Bootstrap intervals describe historical uncertainty. Confirmation multiplicity budget remains reserved for later. [Development pin](prototypes/ext_01_1/development_selection.json) · [Weekly paired scores](prototypes/ext_01_1/s1/paired_weekly_scores.csv) · [Projection guards](prototypes/ext_01_1/s1/projection_guards.csv) · [Run identities and MBB](prototypes/ext_01_1/s1/summary.json)

## S-2 Historical Filter

Both reserved arms matched admitted GW1 solver inputs and settled outcomes exactly. Common neutral opening anchor `opening-anchor-e253552e72848433`. Champion completed GW1–38 with 2,299 net FPL points. [GW1 parity](prototypes/ext_01_1/s2_prefix_parity.csv) · [Attempt](prototypes/ext_01_1/s2_attempt.json) · [Protocol](prototypes/ext_01_1/s2_protocol.json) · [Replay status](prototypes/ext_01_1/s2_execution_status.csv)

First candidate execution certified GW1–23. GW24 hit 180-second native solve limit with `TIME_LIMIT`, relative gap `0.0009130622341009918`. Identical solo retry exited with no additional certificate. Terminal diagnostics unavailable for that retry. Whole-process CPU affinity retry stopped at GW9 exact forecast equality check due to floating-point differences in projected points. Final retry preserved normal forecasting environment, verified GW1–23 from checkpoints, and applied preferred CPU affinity to main thread after GW24 forecast. Same `TIME_LIMIT` and exact same relative gap at GW24. Shared attempt and protocol remained bound. Full paired S-2 evidence unavailable. No model performance verdict.

### Resume before slate freeze

Revalidated frozen Dev selection, S-2 reservation, both archive/seed inventories, 76 mirror source hashes and admitted GW1 inputs. Champion `scores.csv` present with 38 certified checkpoints. Candidate retained GW1–23 checkpoints with no full-season `scores.csv`. Same reservation reusable on a host with faster single-thread performance and compatible numerical output. Use the branch checkout and `uv sync --locked`. Bring these inputs to the corresponding paths:

- `data/archive/2024-25/processed/` and `data/archive/2023-24/processed/`.
- `data/reports/empirical_mirrors/` files referenced by `config/dev_mirror_2024_25_manifest.json`, including all 38 fixture/bootstrap snapshots and admitted GW1 settlement.
- `.tmp/agent/explore-candidate/pre-slate/s2_filter/ext_01_1/`, including both replay arms and both reservation manifests.

Resume fails closed on forecast, outcome or evaluation identity mismatch. Keep original forecasting environment where possible. Forcing the whole process onto one CPU previously changed floating-point results and tripped exact resume checks.

From repository root, resume candidate and compare completed replays:

```bash
topic=docs/research/candidate-ideation
lane="$topic/prototypes/ext_01_1"
reserved=.tmp/agent/explore-candidate/pre-slate/s2_filter/ext_01_1
PYTHONPATH=. uv run python -u "$topic/run_s2_filter.py" \
  --pin "$lane/development_selection.json" --arm candidate
```

Run only after candidate completes GW38 under the reserved protocol:

```bash
PYTHONPATH=. uv run python "$topic/compare_historical_replays.py" \
  --season 2024-25 --pin "$lane/development_selection.json" \
  --prefix-parity "$lane/s2_prefix_parity.csv" \
  --champion "$reserved"/champion/replays/def_xg_shrink_challenger-gw01-38-22178f8e-f9da5685 \
  --candidate "$reserved"/candidate/replays/ext_01_1_a10-gw01-38-a989919c-f9da5685 \
  --out "$lane/s2"
```

Require positive full-season net delta, all applicable projection guards, all three segment floors and exact GW1 parity before presenting EXT-01_1 for slate-freeze approval. Changing the 180-second time budget changes the replay identity. Any longer-budget historical replay needs an explicitly reviewed replacement protocol before it can inform lock-in. Keep the other ideas queued with their existing dispositions.

## Bounded queue

Initial eligible set empty (`untested` or `in-progress-b<N>`). EXT-10 and EXT-13 already closed. One ideation batch used freshly generated brief with lock mechanisms and Dev context. Excluded historical-filter results and active-season outcomes. User narrowed evaluation to EXT-01_1 only. EXT-02_1 implementation stopped before review or replay. [Queue and dossiers](idea_queue.csv)

| Idea | Disposition | Mechanism |
|---|---|---|
| EXT-01_1 | S-1 passed. S-2 blocked at GW24. | Within-player xGC-minus-GC rate adjustment. Distinct from fitted multifeature concessions GLM. |
| EXT-02_1 | Deferred, no replay | Player exposure weights incumbent assist branches. Distinct from start/sub attack intensity split. |
| EXT-03_1 | Deferred, no replay | Club peer contrast on conditional cameo duration. Distinct from fitted start or appearance models. |
| EXT-04_1 | Deferred, no replay | Dismissal-dependent reliability weight on historical xG. Distinct from predicting red-card rates or opponent-strength adjustment. |
| EXT-05_1 | Held for lineage ruling | Negative-binomial save threshold may overlap locked DEF-08 arm. |

EXT-01_1 implemented fixed variants `ext_01_1_a05` and `ext_01_1_a10`. One repair applied 0.05 minimum rate before fixture treatment on both supported and cold-start GK/DEF rows. Spec & Math and Standards & Pipeline independently approved prototype SHA-256 `90d0558febc907bbceb29ea4f337de1351134482c7b6080350a6735b1ae0c25b`. First smoke attempt invalidated when concurrent research code changed its bound source inventory. Both reviewers approved the separate S-2 pin, replay and evidence checks after two repair rounds. No slate freeze. [Candidate Ledger](../candidate-ledger/candidate_ledger.csv)
