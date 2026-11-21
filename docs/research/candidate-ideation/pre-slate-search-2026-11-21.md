# Pre-slate Candidate Search — 2026-11-21

**Disposition:** S-1 fixture blocker resolved. First reviewed lane in certified S-1 replay. S-2 input preflight and candidate selection pending. No finalist or scientific verdict.

## Evaluation contract

- Confirmed Champion: `def_xg_shrink_challenger` from [model selection](../../../config/model_selection.json).
- Development: 2025–26 (`S-1`), seed 2024–25. Untuned Historical Filter: 2024–25 (`S-2`), seed 2023–24. Exclude Assistant Managers. One `S-2` look after source and parameter pin. 2026–27 outcomes sealed.
- [ADR 0069](../../adr/0069-annual-rolling-validation-and-dual-tier-promotion.md): full GW1–38 point-in-time archive replays plus admitted empirical prefix parity. Independent six-GW Strategic solves from common neutral GW1 ownership anchor. Net FPL points = gross points minus transfer-hit deductions, cumulative; higher better; Champion delta strictly positive in each season, with all applicable projection and segment guards passing. Rank by mean of season deltas, then `S-2` delta, then model name. Paired non-wrapping moving block bootstrap (`L=5`) describes historical evidence. Later confirmation retains `M<=2` and `FWER<=0.05`.
- Re-ran `load_empirical_manifest_bundle(..., require_admitted=True)` on [S-1 GW1–7](../../../config/dev_mirror_2025_26_manifest.json) and [S-2 GW1](../../../config/dev_mirror_2024_25_manifest.json). Both admitted. Candidate-specific parity and full replay unexecuted.

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

[S-1 replay runner](run_s1_replay.py) verifies joint fixture/market snapshot identity, full forecast fixture coverage including blanks, and projection component reconciliation before passing the table to the native zero-gap solver. Retains immutable run-scoped forecasts, model and protocol hashes, and audited scores. GW1 Champion pilot verified from neutral anchor `opening-anchor-809d4afb3e40c205`. Full certified S-1 replay and model-specific prefix parity pending.

S-2 schedule preflight verified 38 pinned pre-deadline fixture tables and 19 dated kickoff amendments across GW23, GW33 and GW35 origins. Overlay amends kickoffs with known announcement dates and preserves recorded FPL Gameweek assignments and latest observed FDR. Unresolved conditional Villa–Spurs kickoff at GW33 retains the contemporaneous API time. GW1 admitted inputs preserved. No model was run on S-2. [Dated amendments](s2_historical_fixture_amendments.csv) · [April 17 circular](https://resources.premierleague.pulselive.com/premierleague/document/2025/04/17/cb7dbd1f-35cc-4a63-96ef-8a7febb8159c/Fixture-Amendments-23-Season-2024-25.pdf)

## Bounded queue

Initial eligible set empty (`untested` or `in-progress-b<N>`); EXT-10 and EXT-13 already closed. One ideation batch used freshly generated brief with lock mechanisms and Dev context. Excluded historical-filter results and active-season outcomes. Preserved fixed grids and input manifests in [queue and dossiers](idea_queue.csv).

| Idea | Disposition | Mechanism |
|---|---|---|
| EXT-01_1 | Active S-1 replay | Within-player xGC-minus-GC rate adjustment. Distinct from fitted multifeature concessions GLM. |
| EXT-02_1 | Queued after active lane | Player exposure weights incumbent assist branches. Distinct from start/sub attack intensity split. |
| EXT-03_1 | Queued after active lane | Club peer contrast on conditional cameo duration. Distinct from fitted start or appearance models. |
| EXT-04_1 | Queued after active lane | Dismissal-dependent reliability weight on historical xG. Distinct from predicting red-card rates or opponent-strength adjustment. |
| EXT-05_1 | Held for lineage ruling | Negative-binomial save threshold may overlap locked DEF-08 arm. |

EXT-01_1 implemented fixed variants `ext_01_1_a05` and `ext_01_1_a10`. One repair applied 0.05 minimum rate before fixture treatment on both supported and cold-start GK/DEF rows. Spec & Math and Standards & Pipeline independently approved prototype SHA-256 `90d0558febc907bbceb29ea4f337de1351134482c7b6080350a6735b1ae0c25b`. First smoke attempt invalidated when concurrent research code changed its bound source inventory. No scientific verdict, candidate S-2 look or slate freeze. [Candidate Ledger](../candidate-ledger/candidate_ledger.csv)
