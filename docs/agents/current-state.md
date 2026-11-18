# Current Implementation State

Read if no prior context. `ROADMAP.md` = target. This file = what exists today. Historical dumps → `docs/archive/` (`docs/agents/progress.md`).

**Current phase:** [Weekly Transfer Planner Selection and Champion Adoption](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/190) charted. `explore-candidate` / `ideate-candidate` active under `ADR 0069` (`2025-26` Dev `S-1`, `2024-25` Filter `S-2`, `2026-27` quarantined; `96` active `candidate_ledger.csv` dead locks preserved). Champion `def_xg_shrink_challenger` unchanged; `provisional_active=null`, `podium_sealed=false`; `2026-27 GW1–10` Champion baseline `604`.

## Active Frontier & Completed Map #184 (`ADR 0069`)

[ADR 0070](../adr/0070-weekly-planner-selection-and-champion-adoption.md) accepted design. Ready tickets: [Inventory admissible active-season evidence for the first checkpoint](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/191) and [Define weekly Transfer Planner selection and finalist eligibility](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/192). Implementation and calibration pending.

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
| CLI | `commands/` | Refresh, snapshot, model, backtest, FDR, solve, dashboard, bias, `evaluate_model_promotion`, `ingest_fplcache`, `acquire_empirical_mirrors`, `run_stage_a_and_b` |
| Models | `models/`, `docs/model_name.md` | Catalog `name`. Champion + Dual-Tier selection in `config/model_selection.json` |
| Features / projections | `features/`, `projections/` | Typed contracts; Explorer slice; Role retired; Trailing Start Window default (ADR 0035); Calibrated Matchup Share overlay (`features/matchup_share.py`, ADR 0040); Three-Tier Minutes Cascade & Broad Pool Shield (`features/injury_triage.py`); Official processed heals from Live Season Pin on resolve (ADR 0036) |
| Dashboard | `dashboard/`, `commands/dashboard.py`, `DESIGN.md` | One native Streamlit product: Transfer Planner (Dual-Tier toggle), Explorer, Research, Model Methodology (ADR 0060); `http://127.0.0.1:8000`, IPv4 bind. Persistent editable draft/results/jobs; shared exclusive heavy-job queue; Explorer What-If separate. Content-width reflow, focused Player dialogs, initially collapsed sidebar, contained tables/math; spec `docs/product/dashboard-responsive-layout.md`. Legacy branching backups downloadable. |
| README | `README.md` | How to use + CLI |
| Backtesting | `backtesting/`, `config/` | Walk-forward, Decision Regret, Transfer Plan Walk-Forward, `SeasonLifecycle` (`season_lifecycle.json`), `Randdalf/fplcache` (`fplcache_2026_27_manifest.json`), `mode="empirical"` mirrors/admission (`dev_mirror_*_manifest.json`, `seed_manifest_2024_25.json`), Kendall-PW/HAC + Early-Harm evaluator (`evidence_statistics.py`, `promotion_evidence.py`, `confirmation_registry.py`), Stage A->B profiler/replay, post-GW1 IRL `>3` club-overage hold legality |
| Solver | `solver/` | open-fpl-solver `2ff829f` highspy; live Transfer Plan default gap 0% with deterministic digest caching (ADR 0057); Strategic variance optimization & 3 arms `strategic`, `unconstrained`, `no_hit` (ADR 0061); Dream Team and Walk-Forward stay gap 0 |
| Research | `docs/research/`, `docs/archive/` | Live INDEX + topics. `data/archive/` = Season Archive pins |

## What does NOT exist yet (do not assume)

- Qualified `Provisional Active` finalist not yet frozen (`0` existing catalog qualifiers on `S-1`/`S-2`); `M <= 2` slate awaits new Candidate Search winners.
- Official `2027-28` native `SeasonRules` alignment and `protocol_hash` lock pending next summer's official FPL rules release.
- `GW38` summer-rollover carryover policy when an active `Provisional Active` finalist holds a practical lead without yet clearing `<= 5%` FWER confirmation.
- Snapshot-backed nonzero-chance calibration not implemented; opt-in model applies next-GW `0%` hard DNP only.
- `availability-snapshots` branch missing on `origin`.

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
