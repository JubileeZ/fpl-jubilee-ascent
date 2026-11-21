# Pre-slate Candidate Search — 2026-11-21

**Disposition:** Evidence blocker before candidate execution. Five proposals ingested. Four blocked on replay input. One held for Dead Lever ruling. No finalist or scientific verdict.

## Evaluation contract

- Confirmed Champion: `def_xg_shrink_challenger` from [model selection](../../../config/model_selection.json).
- Development: 2025–26 (`S-1`), seed 2024–25. Untuned Historical Filter: 2024–25 (`S-2`), seed 2023–24. Exclude Assistant Managers. One `S-2` look after source and parameter pin. 2026–27 outcomes sealed.
- [ADR 0069](../../adr/0069-annual-rolling-validation-and-dual-tier-promotion.md): full GW1–38 point-in-time archive replays plus admitted empirical prefix parity. Independent six-GW Strategic solves from common neutral GW1 ownership anchor. Net FPL points = gross points minus transfer-hit deductions, cumulative; higher better; Champion delta strictly positive in each season, with all applicable projection and segment guards passing. Rank by mean of season deltas, then `S-2` delta, then model name. Paired non-wrapping moving block bootstrap (`L=5`) describes historical evidence. Later confirmation retains `M<=2` and `FWER<=0.05`.
- Re-ran `load_empirical_manifest_bundle(..., require_admitted=True)` on [S-1 GW1–7](../../../config/dev_mirror_2025_26_manifest.json) and [S-2 GW1](../../../config/dev_mirror_2024_25_manifest.json). Both admitted. Candidate-specific parity and full replay unexecuted.

## Blocking input

**S-1 six-GW forecast schedule as of each origin.** [Archive testing guide](../../testing/archive-testing.md) discloses residual terminal FDR and player-universe limitations. Separate issue here: terminal fixture Gameweek assignment transfers future rescheduling decisions into earlier optimizer horizons. [Feature builder](../../../features/builder.py) selects forecast fixtures using supplied Gameweek IDs; dropping terminal player columns and strict fit cutoff do not remove schedule hindsight.

| 2025–26 origin | Measured discrepancy | Consequence |
|---|---|---|
| GW24, 2026-01-31 13:30 UTC | Wolves–Arsenal (310) in GW31 in pinned mirror and GW26 in terminal archive. League announced GW26 on 2026-02-03. | Terminal schedule puts fixture inside GW24–29 horizon before public announcement. |
| GW30, 2026-03-14 13:30 UTC | Brighton–Chelsea (333) in GW34 with away FDR 3 in 2026-03-13 mirror. Terminal GW33, away FDR 4. | Terminal schedule assigns upcoming double and blank before April announcement. |
| GW32, 2026-04-10 17:30 UTC | Latest pinned fixture table still dated 2026-03-13. Fixtures 332–334 assigned GW34 despite confirmed GW33 assignments on 2026-04-05. Kickoffs confirmed 2026-04-07. | Mirror understates announced GW33 and overstates GW34. Official notices recover these three assignments and kickoffs, but lack a complete issue-time fixture table with FDR. |

Evidence: [fixture audit CSV](pre_slate_fixture_audit_2026-11-21.csv) contains paired fixture rows, UTC deadlines and pinned digests. Reproduced by joining named fixture IDs in manifest-selected `data/reports/empirical_mirrors/2025-26/fixtures/*.csv` to `data/archive/2025-26/processed/fixtures.parquet`; verified mirror SHA256 before comparing. Match timing from [February FPL notice](https://www.premierleague.com/en/news/4579676), [April FPL notice](https://www.premierleague.com/en/news/4624106) and [April kickoff confirmation](https://www.premierleague.com/en/news/4624588).

Historical bootstrap feed contains deadline timestamps and club/player metadata, with no fixtures table. Checked pre-GW32 alternate public snapshots. FPL-Elo-Insights retains football schedule rows with third-party IDs and no official FPL FDR table. Other checked API snapshot repositories lacked contemporaneous GW32 records. [Pinned alternate snapshot](https://github.com/olbauday/FPL-Elo-Insights/blob/acd8b36b24038426773dfdca00154a7949779e0c/data/2025-2026/By%20Gameweek/GW33/fixtures.csv)

Resume prerequisite: pinned pre-deadline schedules or source-audited reconstructions covering fixture identity, GW assignment, kickoff and difficulty across affected historical six-GW origins. Verify reconstruction against admitted prefix inputs before candidate evaluation. GW32 example establishes a blocking gap independently of GW8/GW2 full empirical admission cutoffs. Full empirical admission outside the required prefixes was not imposed.

## Bounded queue

Initial eligible set empty (`untested` or `in-progress-b<N>`); EXT-10 and EXT-13 already closed. One ideation batch used freshly generated brief with lock mechanisms and Dev context. Excluded historical-filter results and active-season outcomes. Preserved fixed grids and input manifests in [queue and dossiers](idea_queue.csv).

| Idea | Disposition | Mechanism |
|---|---|---|
| EXT-01_1 | Blocked on replay evidence | Within-player xGC-minus-GC rate adjustment. Distinct from fitted multifeature concessions GLM. |
| EXT-02_1 | Blocked on replay evidence | Player exposure weights incumbent assist branches. Distinct from start/sub attack intensity split. |
| EXT-03_1 | Blocked on replay evidence | Club peer contrast on conditional cameo duration. Distinct from fitted start or appearance models. |
| EXT-04_1 | Blocked on replay evidence | Dismissal-dependent reliability weight on historical xG. Distinct from predicting red-card rates or opponent-strength adjustment. |
| EXT-05_1 | Held for lineage ruling | Negative-binomial save threshold may overlap locked DEF-08 arm. |

Input preflight logged in [Candidate Ledger](../candidate-ledger/candidate_ledger.csv). No prototype execution, tuning, or S-2 candidate look; no candidate deltas, segment/guard estimates, bootstrap, or review gate run. No Dead Lever retired, reopened or added. Slate selection and confirmation registration pending.
