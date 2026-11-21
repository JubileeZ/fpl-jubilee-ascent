# Current Implementation State

Read if no prior context. `ROADMAP.md` = target. This file = what exists today. Historical dumps → `docs/archive/` (`docs/agents/progress.md`).

**Current phase:** [Weekly Transfer Planner Selection and Champion Adoption](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/190) implemented & `/code-review`-remediated on canonical branch `feat/champion-adoption-v1` @ `06b96f0a` (`#201`/`#198`/`#200` complete; `1217` pytest, `29/29` `verify.sh`, `0` ruff/scoped pyright errors; `#199` live private GitHub pilot & `>=15`-GW historical fixture open; operator-vs-agent runbook in [pilot & preflight report](../testing/champion-adoption-pilot-report.md#5-next-step-runbook-operator-manual-vs-agent-automatable); live rollout disabled). `explore-candidate` / `ideate-candidate` active under `ADR 0069` (`2025-26` Dev `S-1`, `2024-25` Filter `S-2`, `2026-27` quarantined; `96` active `candidate_ledger.csv` dead locks preserved). Champion `def_xg_shrink_challenger` unchanged; `provisional_active=null`, `podium_sealed=false`; `2026-27 GW1–10` Champion baseline `604`.

## Weekly Transfer Planner

- 2026-27 GW11 pre-deadline official refresh pinned. Local Strategic GW11–20 solve verified at 0% gap, GW14 Free Hit, availability audit passed. Manager-specific plan and minutes overrides stored locally at `data/solution.json` and `data/planner/xmins_override.csv`.

## Active Frontier & Completed Map #184 (`ADR 0069`)

[ADR 0070](../adr/0070-weekly-planner-selection-and-champion-adoption.md) accepted design. Canonical review branches pushed (`feat/sparse-confirmation-certification`, `feat/portable-checkpoint-evidence`, `feat/protected-champion-adoption`, `feat/champion-adoption-v1`); live rollout disabled (`CHAMPION_ADOPTION_LIVE_ENABLED=false`).

- [Certify sparse Champion confirmation and statistical Early-Harm](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/201) implemented on `feat/sparse-confirmation-certification` & `feat/champion-adoption-v1`. `backtesting/sparse_certification.py` + `commands.certify_sparse_confirmation` verified scalar-vs-vectorized parity (`525` prefixes + `56` edge cases, max diff `1.23e-11`, `100%` binary match). Tuned on `seed=20101` (`gw1_4_material_loss_limit=25.0`, `M=1` `3.461e-05`/`0.00173025`/`0.02733795`, `M=2` `6.04e-06`/`0.00060375`/`0.00953925`). Primary enforced `seed=20102` breached statistical Early-Harm false exclusion (`0.2313 > 0.05`); predeclared `advisory` fallback certified on untouched `seed=20103` (`certified=True`, `worst_false_full_pass_upper_95=0.0441 <= 0.05`, `primary_gw38_power_lower_95=0.3665 >= 1/3`, `worst_terminal_false_exclusion_upper_95=0.0214 <= 0.05`, `certification_digest=9e7234b17fc73543eb8330817f3d5ec519735de4f3264485f2592c7f46d53c56`). Versioned `v2.0` protocol decoupled from `provisional_active` and `trail_at_gw15`.
- [Build portable checkpoint evidence and verify the pilot fixture](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/198) implemented on `feat/portable-checkpoint-evidence` & `feat/champion-adoption-v1`. [Non-live fixture inventory](../testing/pilot-fixture-inventory.md) (`commands.inventory_pilot_fixture`, `2026-27` untouched) confirmed `has_admissible_historical_gw15_passing_fixture=False` (`2025-26` stops `GW1..7`, `2024-25` `GW1..1`, `2023-24` `0`; retained GW15 fixture reconstructs `inconclusive`, `bundle_hash=9f99c4b8...`). Delivered `backtesting/portable_evidence.py` (`BlobStore`, relative POSIX validation, `compute_serving_model_closure`, `ExclusionLedger`, `AdoptionLedger`, `VerificationScorecard`, `pack_checkpoint_snapshot`, `verify_checkpoint_snapshot_archive`), DGW/BGW `(player_id, fixture_id)` outcomes, first-party `.xz` `timing_basis="receipt"`, `"finished": True` & float casts on `history_fixtures`, Matchup-Share `expected_goals_conceded` preservation, portable `forecast_id` & `solver_identity`, `180s` certified `QualityPolicy`, prefix-reusable `replay_evaluation_identity`, prefix-aware `verify_checkpoint_attempt`, `2027-28` `S-1` transition baseline, `commands.produce_validation_evidence` (`collect`/`freeze`/`replay`/`scorecard`/`bootstrap-s1-baseline`), and unified hourly `.github/workflows/validation-collector.yml`.
- [Implement protected Champion adoption and planner freshness](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/200) implemented on `feat/protected-champion-adoption` & `feat/champion-adoption-v1`. Fixed `adopt_champion()` atomic selection + `.adoption.json` replacement after race check. Delivered `backtesting/adoption_transaction.py` (`AdoptionRequestManager` w/ 30d default expiry & full archive/bundle verification, `NotificationDispatcher`, `SharedReservationCoordinator`), `commands.manage_champion_adoption` (`HttpWebhookMailProvider`, `record-approval`, `sync-evidence-worktree`, App-token PR API merge & live checks), `.github/workflows/champion-adoption-{request,pr-checks,merge}.yml`, and `models/planner_selection.py` (`check_remote_main_freshness`, `StaleCheckoutError`, `"unverified"` offline Champion-only fallback enforced in live `make_solve_request`, `sync_validation_evidence_readonly` root+season sync, `resolve_weekly_planner_model`, injury-audit `--rerun` model pinning).
- [Run the isolated GitHub Champion adoption pilot](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/199): local automated pilot acceptance harness (`tests/test_pilot_acceptance_harness.py`) passed `5/5` tests covering `#197` scenarios. Read-only [production preflight report](../testing/production-preflight-report.json) (`commands.manage_champion_adoption production-preflight`) attested `3/10` gates passing (`certified_protocol`, `live_rollout_disabled`, `shared_reservation_wiring`) and `7/10` open/blocked (`admissible_historical_passing_fixture`, `branch_protection_main`, `protected_environment`, `github_app_and_no_bypass`, `immutable_evidence_and_releases`, `mail_delivery_and_reconciliation`, `sealed_slate_and_operator_signoff`). See [pilot & preflight report](../testing/champion-adoption-pilot-report.md) on tested commit `06b96f0a` (`feat/champion-adoption-v1`, `1217` pytest, `29/29` `verify.sh`) & section 5 next-step runbook. Live isolated private GitHub pilot awaiting operator pilot repo, separate GitHub App installation, test inbox, and protected approval.
- [Formal cadence and preregistration](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/196#issuecomment-7043351900) and [pilot acceptance](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/197#issuecomment-7043511729) closed. [Implementation spec](../product/champion-adoption-implementation.md) delivered in code on `feat/champion-adoption-v1`.
- [GitHub approval and adoption transaction](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/194#issuecomment-7034197070) closed. [ADR 0070 amendments](../adr/0070-weekly-planner-selection-and-champion-adoption.md#closed-ticket-review-amendments-2026-11-20) govern controlled merge, request priority, planner freshness, and conditional S-1 baseline fallback. Production activation pending.

- [Inventory admissible active-season evidence for the first checkpoint](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/191#issuecomment-6984434844) closed. `2026-27 GW1–10` pinned bootstrap verified, ingest settlement recorded. `origin/availability-snapshots` holds pre-deadline fixture captures for `GW1–10`, with package hashes reproduced for `GW1–6`. `adr0069-checkpoint-v2` prefix empty from `GW1`. Fixture, history, seed and independent settlement receipts plus certified opening anchor missing. `2026-27 GW15` conditional on authentic receipt recovery, full prefix and frozen slate. Without early receipts, earliest prospective opportunity `2027-28 GW15` with capture from `GW1`.
- [Choose the checkpoint evidence producer and portable registry contract](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/193#issuecomment-7014840996) closed. Offline verifier/adopter preserved; `commands.produce_validation_evidence` (`collect`/`freeze`/`replay`) and unified `validation-collector.yml` write to `validation-evidence` (GitHub Releases only for passing checkpoints). Relative POSIX paths, `blobs/<sha256>`, transitive `serving_model_closure_hash` (modeling deps only), prefix-reusable replays (no `scored_end_gw`), canonical `registry.jsonl` + `exclusions.jsonl` + `adoption_ledger.jsonl`, DGW/BGW + `history_fixtures` + CI HiGHS cap fixes, fail-closed transient/permanent gaps, and `2027-28` `S-1` Season Archive transition.
- [Define weekly Transfer Planner selection and finalist eligibility](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/192#issuecomment-6986056342) closed. Verified common-prefix leader serves weekly. Ordinary deficit preserves eligibility. Registered harm or demonstrated mandatory guard failure excludes. Injury-audit rerun pins reviewed model. Scorecard and exclusions separate from Champion config. Implemented on `feat/champion-adoption-v1` (#200).

Completed ADR 0069 routes:
- **Preserved `#175`–`#179` Foundations (CLOSED under superseded Map #174):** Freshness/input bounds (`#175`), `< gw` lineage/coverage audit (`#176`), primary-source inference review on `research/promotion-inference-177` (`#177`), unified `mode="empirical"` design (`#178`), Strategic 6-GW replay/Stage A->B controls & 15 `MANDATORY_GUARDS` (`#179`).
- **#185 ([Implement ADR 0069 SeasonLifecycle config, 2026-27 SeasonRules verification, and Randdalf/fplcache GW1-38 ingestion](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/185), CLOSED):** Delivered `config/season_lifecycle.json` + `SeasonLifecycle` policy across 9 callers/tests, verified `native-2026-27-v1` (`docs/rules/scoring-rules-2026-27.md`, `two_chip_sets=True`, `afcon_gw15_topup=False`) + `< gw` `model.fit()` isolation, and built `backtesting/fplcache_ingest.py` + `commands/ingest_fplcache.py` (`config/fplcache_2026_27_manifest.json`).
- **#186 ([Approve calibrated <= 5% FWER inference, Dual-Tier early-harm fallback, and max-2 podium rules](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/186), CLOSED):** Approved zero-hardcode policy: consistent one-sided Kendall-PW + Bartlett HAC Student-$t$ superiority (`one_sided_lower > 0` iff `p <= alpha_spent`), O'Brien-Fleming spend (`0.0005`/`0.010`/`0.0395` at `GW15`/`GW30`/`GW38`, halved for `M=2`), statistical Early-Harm Fallback (`min_gw=6`, `p_harm <= 0.025` or guard `FAIL`), data-derived `S-1` Champion guards (`max(0.05 * S-1 mean, 1 * S-1 GW_SE)`), `0.5 * (delta_S1 + delta_S2)` podium ranking, sealed `M<=2` slate, and symmetric `alpha/M` simultaneous tracking + `#1->#2` rotation.
- **#189 ([Implement unified mode="empirical" replay, Strategic 6-GW parity, and Stage A->B verification](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/189), CLOSED):** Pinned `2025-26` dev (`GW1..7`, first blocked `GW8`, `Partial Prefix`), `2024-25` filter (`GW1..1`, first blocked `GW2`, `Partial Prefix`) & `2024-25` seed manifests (`config/{dev_mirror_2025_26_manifest,dev_mirror_2024_25_manifest,seed_manifest_2024_25}.json`); delivered `backtesting/{empirical_mirrors,empirical_admission}.py`, `commands/{acquire_empirical_mirrors,run_stage_a_and_b}.py`, `ADR 0065` Strategic parity + `QualityPolicy(target_gap=0.0)` + LP dual kernel MIP start (`backtesting/native_transfer_solver.py`); Stage A `0/8` censored (`226.2945s`, `929.66 MB` RSS) & Stage B B1–B4 pass; ruff + `1111` pytest + `verify.sh` + two-axis reviews clean (`0` findings).
- **#187 ([Wire Dual-Tier weekly serving, GW15/GW30/GW38 confirmation evaluator, and end-to-end verification](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/187), CLOSED):** Dual-Tier side-by-side predictions (`Confirmed Champion` Explorer default, `Provisional Active` Transfer Plan default with `Confirmed Champion` one switch away, manual `adopt_champion`) + `#186` Kendall-PW/HAC OBF `GW15`/`GW30`/`GW38` evaluator + `min_gw=6` Early-Harm + `S-1` margins + `M<=2` podium/rotation + `S->S-1->S-2` summer rollover (`6e064d8c`).
- **#188 ([Freeze initial finalists on 2025-26 + 2024-25, launch GW1-15 Dual-Tier validation, and resume Candidate Search](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/188), CLOSED 2026-11-18):** `0` qualifiers (`adaptive_causal_challenger` / `club_def_prior_challenger` failed `S-1`+`S-2`); `provisional_active=null`, `podium_sealed=false`; synced `2026-27 GW1–10` `Randdalf/fplcache` `settled_verified`, fixed post-GW1 IRL `>3` club-overage hold (`replay_state.py`, `rolling_replay.py`, `native_transfer_solver.py`), verified `2026-27 GW1–10` Champion baseline `604`, codified two-part `S-1`/`S-2` vs `S` boundary (`CONTEXT.md`, `ADR 0069`), unlocked `explore-candidate` / `ideate-candidate`. Closes [Map #184](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/184).

Historical Oct–Nov 2026 session logs archived to [2026-11-18 Session History](../archive/2026-11-18-session-history.md).
Eval canon: `docs/research/INDEX.md`. Prior residual work: `docs/research/champion-component-gap/`.

### ADR 0069 review follow-up

- GW15 provisional queue keeps ahead/even, unharmed #1. Rotate only to unharmed, non-trailing #2 after #1 drops. Fallback preserves season seal.
- `validation_fplcache` admits complete GW15/GW30/GW38 prefixes separately from full-season eligibility. `adr0069-checkpoint-v2` reconstructs native replay scores and S-1-calibrated guards, verifies frozen registry bindings and finalizes passing bundles for explicit manual adoption. V1 diagnostic only. [Operator workflow](../testing/operator-workflow.md#stage-7-manual-champion-adoption)
- Retained GW15 fixture verified through bundle reconstruction. Fixture verdict inconclusive. Manual adoption verified separately at passing-verdict boundary. Live winning checkpoint pending first qualified slate; evidence collection and checkpoint execution operator-run.
- Explorer and Transfer Plan default to Provisional Active when available, else Confirmed Champion. Refresh retains both serving tiers. Strategy Champion selection routes explicitly. Forecast defaults resolve configured Confirmed Champion. Stored forecasts retain recorded model identity.

## Research truth

Live index: `docs/research/INDEX.md` — **Eval canon** block = promotion metrics vs component-gap metrics (read first for Candidate/Champion work). Companions live in topic folders. Production minutes/rates = Club Fixture shrinkage + Trailing Start Window (ADR 0035). Production difficulty = **Modified FDR** (difficulty only). Fixture xP scale = **Calibrated Matchup Share** when this-season Official club xG exists (ADR 0040); else Club Strength; else neutral ×1.0 (ADR 0037). `Confirmed Champion` = `def_xg_shrink_challenger` (`ADR 0055`); `Provisional Active` = `null`; `podium_sealed` = `false` (`M <= 2` slate and `<= 5%` FWER budget open under `ADR 0069`). Component-gap crown = `xp_goals` structural (`docs/research/champion-component-gap/component_gap_summary.csv` `mse_share`). Research ranking = **DCS**. Dual-Vector Strength not in production Python.

## What exists

| Area | Path | Notes |
|------|------|-------|
| Scaffold | `AGENTS.md`, `ROADMAP.md`, `CONTEXT.md` | Config, phases, glossary |
| Deps | `pyproject.toml`, `.venv/` | uv |
| Clients | `clients/` | FPL API + Playwright/JWT auth |
| Data dictionary | `docs/data_dictionary.md` | API → parquet |
| CLI | `commands/` | Refresh, snapshot, model, backtest, FDR, solve, dashboard, bias, `evaluate_model_promotion`, `ingest_fplcache`, `acquire_empirical_mirrors`, `run_stage_a_and_b`, `certify_sparse_confirmation`, `inventory_pilot_fixture`, `produce_validation_evidence`, `manage_champion_adoption` |
| Models | `models/`, `docs/model_name.md` | Catalog `name`. Champion + Dual-Tier selection in `config/model_selection.json`. Weekly planner selection & remote freshness (`models/planner_selection.py`). |
| Features / projections | `features/`, `projections/` | Typed contracts; Explorer slice; Role retired; Trailing Start Window default (ADR 0035); Calibrated Matchup Share overlay (`features/matchup_share.py`, ADR 0040); Three-Tier Minutes Cascade & Broad Pool Shield (`features/injury_triage.py`); Official processed heals from Live Season Pin on resolve (ADR 0036) |
| Dashboard | `dashboard/`, `commands/dashboard.py`, `DESIGN.md` | One native Streamlit product: Transfer Planner (Dual-Tier toggle), Explorer, Research, Model Methodology (ADR 0060); `http://127.0.0.1:8000`, IPv4 bind. Persistent editable draft/results/jobs; shared exclusive heavy-job queue; Explorer What-If separate. Content-width reflow, focused Player dialogs, initially collapsed sidebar, contained tables/math; spec `docs/product/dashboard-responsive-layout.md`. Legacy branching backups downloadable. |
| README | `README.md` | How to use + CLI |
| Backtesting | `backtesting/`, `config/` | Walk-forward, Decision Regret, Transfer Plan Walk-Forward, `SeasonLifecycle` (`season_lifecycle.json`), `Randdalf/fplcache` (`fplcache_2026_27_manifest.json`), `mode="empirical"` mirrors/admission (`dev_mirror_*_manifest.json`, `seed_manifest_2024_25.json`), Kendall-PW/HAC + Early-Harm evaluator (`evidence_statistics.py`, `promotion_evidence.py`, `confirmation_registry.py`), Stage A->B profiler/replay, post-GW1 IRL `>3` club-overage hold legality, sparse certification (`sparse_certification.py`), portable evidence store & snapshot verifier (`portable_evidence.py`), protected adoption transaction & shared reservation (`adoption_transaction.py`) |
| Solver | `solver/` | open-fpl-solver `2ff829f` highspy; live Transfer Plan default gap 0% with deterministic digest caching (ADR 0057); Strategic variance optimization & 3 arms `strategic`, `unconstrained`, `no_hit` (ADR 0061); Dream Team and Walk-Forward stay gap 0 |
| Workflows | `.github/workflows/` | `validation-collector.yml`, `champion-adoption-{request,pr-checks,merge}.yml` (live rollout gated off by default) |
| Research | `docs/research/`, `docs/archive/` | Live INDEX + topics. `data/archive/` = Season Archive pins |

## What does NOT exist yet (do not assume)

- Qualified `Provisional Active` finalist not yet frozen (`0` existing catalog qualifiers on `S-1`/`S-2`); `M <= 2` slate awaits new Candidate Search winners.
- Official `2027-28` native `SeasonRules` alignment and `protocol_hash` lock pending next summer's official FPL rules release.
- `GW38` summer-rollover carryover policy when an active `Provisional Active` finalist holds a practical lead without yet clearing `<= 5%` FWER confirmation.
- Snapshot-backed nonzero-chance calibration not implemented; opt-in model applies next-GW `0%` hard DNP only.

## Safe commands today

```bash
uv run pytest
uv run ruff check .
uv run python -m commands.refresh_data
uv run python -m commands.run_model club_def_prior_challenger
uv run python -m commands.dashboard
uv run python -m commands.solve --preseason --xmin_lb 0
uv run python -m commands.measure_champion_bias
uv run python -m commands.transfer_plan_walkforward
```

Catalog names and more recipes: `README.md` (weekly dashboard path first), `docs/model_name.md`.

## Agent pitfalls

- Playwright Chromium required for `refresh_data` / `snapshot_season` when `FPL_TOKEN` unset.
- Windows console cp1252; commands call `configure_utf8_stdio()` before non-ASCII prints.
- pytest `pythonpath = ["."]`; do not drop it.
- Tests use `sys.executable`, not `.venv/bin/python`.
- Transfer Plan Scenarios need User Squad; plan JSON is `data/transfer_plan_scenarios.json`, not `dashboard_data.json`.

## Doc map

Index: `docs/README.md`. Weekly path / Key Commands: `README.md`, `AGENTS.md`.
