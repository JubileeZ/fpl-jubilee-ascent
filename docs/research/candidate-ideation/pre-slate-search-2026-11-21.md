# Pre-slate Candidate Search — 2026-11-21

**Disposition:** Under `#206` (Map `#205`, ADR 0071), `EXT-01_1` through `EXT-05_1` all completed evaluation with **`0` Win-Both qualifiers**: `EXT-01_1` (`S-1 +82`, `S-2 -67`), `EXT-02_1` (`S-1 -64` both variants), `EXT-03_1` (`S-1 +2`, `S-2 0` tie `2,299` vs `2,299`), `EXT-04_1` (`S-1 a080 +5`, `S-2 -21` `2,278` vs `2,299`), and conditional `EXT-05_1` (`S-1 0` tie `2,167` vs `2,167` both variants). All five lanes are dead-locked until `2027-11-22`; `Confirmed Champion` `def_xg_shrink_challenger` remains uncontested (`provisional_active=null`, `podium_sealed=false`).

## Evaluation contract

- Confirmed Champion: `def_xg_shrink_challenger` from [model selection](../../../config/model_selection.json).
- Development: 2025–26 (`S-1`), seed 2024–25. Untuned Historical Filter: 2024–25 (`S-2`), seed 2023–24. Exclude Assistant Managers. One `S-2` look after source and parameter pin. 2026–27 outcomes sealed.
- For `EXT-01_1`: [ADR 0069](../../adr/0069-annual-rolling-validation-and-dual-tier-promotion.md) full GW1–38 point-in-time archive replays plus admitted empirical prefix parity (`180s` `target_gap=0.0`, legacy regret segment floors, `0.5 * (delta_S1 + delta_S2)`). For `EXT-02_1`+: [ADR 0071](../../adr/0071-certified-solver-budget-and-milp-qualification-calibration.md) (PR `#210`/`#212`, `be0905a4`) governs: `600s` certified `target_gap=0.0` cap/default, `z = -1.50 SE` rolling-MILP segment floors (`-8.9 / -4.7 / -4.2` pts/GW), Win-Both gating (`S-1 > 0` & `S-2 > 0`), exact `Decimal` `0.3*S1 + 0.7*S2` ranking (`-delta_s2`, candidate name tie-break), batch-before-freeze, and `M = 1` default slate discipline (`M <= 2` max). Paired non-wrapping moving block bootstrap (`L=5`) describes historical evidence; later active-season confirmation retains `FWER <= 0.05`.
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

Both reserved arms matched admitted GW1 solver inputs and settled outcomes exactly. Common neutral opening anchor `opening-anchor-e253552e72848433`, protocol `f9da5685a3d64f66696956354aa239fb43d1e8a2d7f735d737f98b9e71fa058a`. [GW1 parity](prototypes/ext_01_1/s2_prefix_parity.csv) · [Attempt](prototypes/ext_01_1/s2_attempt.json) · [Protocol](prototypes/ext_01_1/s2_protocol.json) · [Replay status](prototypes/ext_01_1/s2_execution_status.csv)

On the original PR `#204` host, Champion completed GW1–38 with `2,299` net FPL points; candidate `ext_01_1_a10` certified GW1–23 before GW24 hit the 180-second `TIME_LIMIT` (relative gap `0.0009130622341009918`). Whole-process CPU affinity retry stopped at GW9 exact forecast equality check; solver-only affinity reproduced the GW24 timeout.

**2026-11-22 Apple M2 (`arm64`) certified completion (`#208`):** Uncontended sequential execution completed **all 38 Gameweeks** for both arms under unchanged source, inputs, and frozen 180-second `target_gap=0.0` solver policy (candidate GW24 solved exact `OPTIMAL`, `relative_gap=0.0` in `147.530253s`; Apple M2 GW1 forecast hash `de57412cb7628d8a...` matched identically across both arms and `audit_historical_prefix.py`, `0.0` component diff).

| Model | Verified Net (`S-2`) | Net Delta | Segments (`cold_start` / `early_mid` / `late`) | Projection Guards | Segment Floors | Paired L=5 MBB 95% CI (pts/GW) |
|---|---:|---:|---|---|---|---|
| `def_xg_shrink_challenger` | `2,299` | — | — | — | — | — |
| `ext_01_1_a10` | `2,232` | **`-67`** | `-18 / -62 / +13` (`-4.50` / `-4.13` / `+0.68` per GW) | `14/14 PASS` (`defcon` inapplicable) | **`1/3 PASS`** (`cold_start` FAIL, `early_mid` FAIL, `late` PASS) | `-5.61` to `+1.00` (est `-1.76`, `p_sup=0.8975`) |

`ext_01_1_a10` fails the S-2 Historical Filter (`delta_net <= 0`, `1/3` segments) and does not qualify for slate freeze. [S-2 summary](prototypes/ext_01_1/s2/summary.json) · [S-2 weekly paired scores](prototypes/ext_01_1/s2/paired_weekly_scores.csv) · [S-2 projection guards](prototypes/ext_01_1/s2/projection_guards.csv) · [Candidate Ledger](../candidate-ledger/candidate_ledger.csv)

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

Require positive full-season net delta, all applicable projection guards, all three segment floors and exact GW1 parity before presenting finalists for slate-freeze approval. For subsequent lanes (`EXT-02_1+`), [ADR 0071](../../adr/0071-certified-solver-budget-and-milp-qualification-calibration.md) raises the certified solver cap/default to `600s` (rotating `core_closure_hash()` cleanly), calibrates rolling-MILP segment floors to `z = -1.50 SE` (`-8.9 / -4.7 / -4.2` pts/GW) with strict key validation, ranks finalists by `0.3*S1 + 0.7*S2`, and mandates bounded batch evaluation (`EXT-02_1` -> `EXT-03_1` -> `EXT-04_1`; `EXT-05_1` only if `0` qualify) before `M = 1` default slate freeze. Do not change solver budgets inside an active reservation. Keep `EXT-01_1` dead-locked until `2027-11-22`.

### Best feasible at 180 seconds diagnostic

Run from repository root with both original reserved arms and their inputs available:

```bash
PYTHONPATH=. uv run python -u docs/research/candidate-ideation/run_s2_incumbent_diagnostic.py \
  --pin docs/research/candidate-ideation/prototypes/ext_01_1/development_selection.json
```

Both arms start at GW1 from the same neutral ownership anchor and independently replay the six-GW Strategic plan through GW38. Each solve targets zero relative gap with a 180-second budget. A feasible `TIME_LIMIT` decision advances only after the same legality checks and keeps the original solver certificate. No incumbent stops execution. Diagnose on one host with the same solver binary across both arms and resume with the same command.

The paired `diagnostic_report.json` under `.tmp/agent/explore-candidate/pre-slate/s2_incumbent_diagnostic/ext_01_1/` requires both complete trajectories and admitted GW1 parity. It records net points, solver status, runtime, objective bounds, gaps and action agreement where an original certified checkpoint has the exact same state and forecast. The diagnostic protocol and checkpoints are separate from the qualification reservation. Do not use diagnostic results for slate freeze or adoption.

2026-11-22 solve-only probe used retained candidate GW23 state and GW24 issue market and forecasts. Native `TIME_LIMIT` incumbent passed independent decision legality checks after `179.450659` seconds of solver time, relative gap `0.0008749054732374218`. No GW24 settlement or paired season score produced by this probe.

## Bounded queue

Initial eligible set empty (`untested` or `in-progress-b<N>`). EXT-10 and EXT-13 already closed. Bounded `#206` batch completed `EXT-02_1` -> `EXT-03_1` -> `EXT-04_1` and conditional last-place `EXT-05_1` under [ADR 0071](../../adr/0071-certified-solver-budget-and-milp-qualification-calibration.md) (`600s` certified `target_gap=0.0`, `core_closure_hash()` `f5773369817b2d99dfa4f7e8d75be1be3a24f2e6654606d5da200a88d74941b1`, Win-Both gating). Excluded active-season outcomes. All five `#206`/`#208` lanes dead-locked until `2027-11-22`. [Queue and dossiers](idea_queue.csv)

| Idea | Disposition | Mechanism |
|---|---|---|
| EXT-01_1 | S-1 passed (`+82`). S-2 failed (`-67`, dead until `2027-11-22`). | Within-player xGC-minus-GC rate adjustment. Distinct from fitted multifeature concessions GLM. |
| EXT-02_1 | S-1 failed (`-64` both variants, no S-2, dead until `2027-11-22`). | Player exposure weights incumbent assist branches. Distinct from start/sub attack intensity split. |
| EXT-03_1 | S-1 passed (`+2`). Pinned `a05` S-2 failed (`0.0` tie `2,299 vs 2,299`, dead until `2027-11-22`). | Club peer contrast on conditional cameo duration. Distinct from fitted start or appearance models. |
| EXT-04_1 | S-1 passed (`a080 +5`, `a050 -18`). Pinned `a080` S-2 failed (`-21`, `2,278 vs 2,299`, dead until `2027-11-22`). | Dismissal-dependent reliability weight on historical xG. Distinct from predicting red-card rates or opponent-strength adjustment. |
| EXT-05_1 | Conditional last (`#206`); S-1 failed (`0.0` tie `2,167 vs 2,167` both variants, no S-2, dead until `2027-11-22`). | Standalone Negative Binomial on unchanged Champion `μ` (distinct from bundled Club SoT rate pooling). |

EXT-01_1 implemented fixed variants `ext_01_1_a05` and `ext_01_1_a10`. One repair applied 0.05 minimum rate before fixture treatment on both supported and cold-start GK/DEF rows. Spec & Math and Standards & Pipeline independently approved prototype SHA-256 `90d0558febc907bbceb29ea4f337de1351134482c7b6080350a6735b1ae0c25b`. First smoke attempt invalidated when concurrent research code changed its bound source inventory. Both reviewers approved the separate S-2 pin, replay and evidence checks after two repair rounds. No slate freeze. [Candidate Ledger](../candidate-ledger/candidate_ledger.csv)

## #206 Bounded Batch Evaluation (ADR 0071, 2026-11-22)

Under `core_closure_hash()` `f5773369817b2d99dfa4f7e8d75be1be3a24f2e6654606d5da200a88d74941b1` (`600s` `target_gap=0.0`, shared S-1 `def_xg_shrink_challenger` baseline `2,167` net pts at `opening-anchor-809d4afb3e40c205`, protocol `c7463c2d88ee11989f882da486f51e591b4375c88fd9b6bf16184b6da3c69f2e`; S-2 baseline `2,299` net pts at `opening-anchor-e253552e72848433`):

| Lane & Variant | Reviewed Prototype SHA-256 | S-1 Net / Delta | S-1 Segments (`cold` / `early_mid` / `late`) | S-1 Guards & `GW1–7` Parity | S-2 Net / Delta (`2024-25`) | S-2 Segments, Guards & `GW1` Parity | Paired `L=5` MBB 95% CI (pts/GW) & Verdict |
|---|---|---|---|---|---|---|---|
| `EXT-02_1` `ext_02_1_k180` | `53c2879e` ([source](prototypes/ext_02_1/prototypes.py)) | `2,103` (`-64`) | `0 / -21 / -43` (`3/3` floors) | `15/15 PASS`; `21/21` `0.0` | Not run (`S-1` fail) | — | `-1.68` `[-4.16, +0.34]`; **Dead (`2027-11-22`)** ([S-1](prototypes/ext_02_1/s1/summary.json)) |
| `EXT-02_1` `ext_02_1_k450` | `53c2879e` ([source](prototypes/ext_02_1/prototypes.py)) | `2,103` (`-64`) | `0 / -21 / -43` (`3/3` floors) | `15/15 PASS`; `21/21` `0.0` | Not run (`S-1` fail) | — | `-1.68` `[-4.16, +0.34]`; **Dead (`2027-11-22`)** ([S-1](prototypes/ext_02_1/s1/summary.json)) |
| `EXT-03_1` `ext_03_1_a05` (pinned) | `d56bdec0` ([source](prototypes/ext_03_1/prototypes.py)) | `2,169` (`+2`) | `0 / 0 / +2` (`3/3` floors) | `15/15 PASS`; `21/21` `0.0` | `2,299` (`0.0`) | `0 / 0 / 0` (`3/3`); `14/14 PASS`; `GW1` `0.0` | `S-1 +0.05` `[-1.34, +0.66]`; `S-2 0.0` `[0.0, 0.0]`; **Dead (`2027-11-22`)** ([S-2](prototypes/ext_03_1/s2/summary.json)) |
| `EXT-03_1` `ext_03_1_a10` | `d56bdec0` ([source](prototypes/ext_03_1/prototypes.py)) | `2,169` (`+2`) | `0 / 0 / +2` (`3/3` floors) | `15/15 PASS`; `21/21` `0.0` | Tie-break unselected | — | Superseded by `ext_03_1_a05` pin ([pin](prototypes/ext_03_1/development_selection.json)) |
| `EXT-04_1` `ext_04_1_a050` | `f206b28f` ([source](prototypes/ext_04_1/prototypes.py)) | `2,149` (`-18`) | Fails `delta > 0` | `15/15 PASS`; `21/21` `0.0` | Not pinned | — | Sub-grid fail ([S-1](prototypes/ext_04_1/s1/summary.json)) |
| `EXT-04_1` `ext_04_1_a080` (pinned) | `f206b28f` ([source](prototypes/ext_04_1/prototypes.py)) | `2,172` (`+5`) | `0 / +11 / -6` (`3/3` floors) | `15/15 PASS`; `21/21` `0.0` | `2,278` (`-21`) | `+1 / -1 / -21` (`3/3`); `14/14 PASS`; `GW1` `0.0` | `S-1 +0.13` `[-1.32, +1.21]`; `S-2 -0.55` `[-3.34, +2.11]`; **Dead (`2027-11-22`)** ([S-2](prototypes/ext_04_1/s2/summary.json)) |
| `EXT-05_1` `ext_05_1_r3` | `b7f9238e` ([source](prototypes/ext_05_1/prototypes.py)) | `2,167` (`0.0`) | `0 / 0 / 0` (`3/3` floors) | `15/15 PASS`; `21/21` `0.0` | Not run (`S-1` tie) | — | `0.0` `[0.0, 0.0]`; **Dead (`2027-11-22`)** ([S-1](prototypes/ext_05_1/s1/summary.json)) |
| `EXT-05_1` `ext_05_1_r8` | `b7f9238e` ([source](prototypes/ext_05_1/prototypes.py)) | `2,167` (`0.0`) | `0 / 0 / 0` (`3/3` floors) | `15/15 PASS`; `21/21` `0.0` | Not run (`S-1` tie) | — | `0.0` `[0.0, 0.0]`; **Dead (`2027-11-22`)** ([S-1](prototypes/ext_05_1/s1/summary.json)) |

**Outcome:** `0` Win-Both qualifiers (`delta_s1 > 0` & `delta_s2 > 0`); no slate frozen; `Confirmed Champion` `def_xg_shrink_challenger` remains uncontested. [Candidate Ledger](../candidate-ledger/candidate_ledger.csv)
