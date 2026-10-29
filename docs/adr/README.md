# Architecture Decision Records (ADRs)

Authoritative architectural and design decisions governing FPL-Jubilee-Ascent.

## Lifecycle Statuses

- **Accepted**: Active architectural baseline currently enforced in production and tests.
- **Amended**: Baseline modified or scoped by a subsequent decision while preserving core tenets.
- **Superseded**: Historical record replaced by a newer decision (indicated with link).
- **Proposed**: Under evaluation or awaiting formal adoption gate.

---

## Decisions by Subsystem

### 1. Modeling & Score Projections

| ADR | Title | Status | Summary |
|-----|-------|--------|---------|
| [0001](0001-add-scipy-dependency.md) | Add SciPy Dependency for Projection Models | Accepted | Introduces SciPy for statistical distribution and regression math. |
| [0003](0003-reconstruct-points-from-event-components.md) | Reconstruct projections from event components via FPL scoring matrix | Accepted | Projections built bottom-up from decoupled event components mapped through the official scoring matrix. |
| [0005](0005-hybrid-metrics-component-projection-model.md) | Hybrid Metrics Component Projection Model | Accepted | Calibrated components combining underlying metrics (xG, xA, xGC) with official rates. |
| [0006](0006-fixture-first-projection-contract.md) | Fixture-first projection contract | Accepted | Standardizes projection outputs indexed by `(player_id, gameweek_id, fixture_id)`. |
| [0007](0007-event-level-empirical-bayes-projection-engine.md) | Event-Level Empirical Bayes Projection Engine | Accepted | Replaces heuristic shrinkage with Empirical Bayes estimates across event components. |
| [0009](0009-market-projection-ingestion-and-solio-minutes-blend.md) | Market Projection Ingestion & Solio Minutes (DEPRECATED) | Superseded | Deprecated experimental external market blend. |
| [0010](0010-participation-state-snapshots-and-evaluation.md) | Participation State, Snapshots, and Evaluation | Accepted | Explicit modeling of starter vs substitute vs DNP probabilities. |
| [0013](0013-bottom-up-calibrated-component-metrics-and-rqi.md) | Bottom-Up Calibrated Components, Dual-Vector Strength, and RQI | Accepted | Calibrates component metrics and team strength vectors. |
| [0014](0014-preseason-career-rate-and-destination-concede.md) | Preseason newcomer rates | Accepted | Cold-start rates combining historical career priors with destination team rates. |
| [0015](0015-defensive-composite-score.md) | Defensive Composite Score replaces RQI | Accepted | Replaces RQI with defensive composite metric for rotation and clean sheet projections. |
| [0016](0016-expected-role-prior-cold-start-minutes.md) | Expected Role Prior Cold-Start Minutes | Superseded | Retired by ADR 0022 and ADR 0025. |
| [0022](0022-club-fixture-minutes-and-rate-shrinkage.md) | Minutes & Rates from Club Fixture Shrinkage | Accepted | Feature Contract minutes and event rates derived from club fixture shrinkage. |
| [0024](0024-this-season-evidence-shrinkage.md) | This-Season Evidence ends Cold-Start | Accepted | In-season rates transition exclusively to current-season evidence once observed. |
| [0025](0025-retire-expected-role.md) | Expected Role is Retired | Accepted | Full retirement of Expected Role; xMins reported directly from Club Fixtures. |
| [0026](0026-completed-club-fixtures-state-shrink.md) | Completed Club Fixtures & State Shrinkage | Accepted | Clarifies Completed Club Fixtures definition; prior-season seed decoupled from live pin. |
| [0035](0035-trailing-start-window.md) | Trailing Start Window for Participation State xMins | Accepted | Rolling match window for estimating active starter persistence. |
| [0037](0037-fdr-fallback-multiplier-neutral.md) | Matchup Share Primary & Neutral Fallback | Accepted | Matchup Share as primary difficulty multiplier; falls back to Club Strength, then 1.0 neutral. |
| [0039](0039-champion-participation-penalty-hybrid.md) | Champion rename: participation_penalty_hybrid | Accepted | Aligns model nomenclature. |
| [0040](0040-calibrated-matchup-share-shrinkage.md) | Calibrated Matchup Share | Accepted | Shrunk delta, positional priors, and decoupled peripherals for fixture difficulty. |
| [0041](0041-champion-calibrated-matchup-hybrid.md) | Champion rename: calibrated_matchup_hybrid | Accepted | Champion designation for calibrated matchup model. |
| [0045](0045-champion-face-value-challenger.md) | Champion face_value_challenger | Accepted | Face-value xG/xA attack, pooled finishing offset (1800 min), start shrinkage. |
| [0048](0048-champion-multi-feature-assist-challenger.md) | Champion multi_feature_assist_challenger | Accepted | Ridge Poisson GLM assist rate; confirmation-season bootstrap bar 0.60. |
| [0050](0050-champion-learned-start-challenger.md) | Champion learned_start_challenger | Accepted | Ridge-logistic learned starter probability with P(60)-weighted bonus pool. |
| [0051](0051-champion-club-def-prior-challenger.md) | Champion club_def_prior_challenger | Accepted | Shrinks DEF xG/90 toward club × DEF pooled rate prior. |
| [0055](0055-champion-def-xg-shrink-challenger.md) | Champion def_xg_shrink_challenger | Accepted | Position-specific DEF xG rate shrinkage with $K=2400$ pseudo-minutes. Active Champion. |
| [0056](0056-operational-zero-availability-hard-dnp.md) | Operational Zero-Availability Hard DNP | Accepted | Zero-chance or red-flagged assets forced to 0.0 xMins across operational horizons. |
| [0063](0063-champion-adaptive-causal-challenger.md) | Champion adaptive_causal_challenger | Accepted | Causal panel ML components with GW1–19 stability and GW20+ late-season activation. |

---

### 2. Optimization, Transfer Planning & Solver

| ADR | Title | Status | Summary |
|-----|-------|--------|---------|
| [0020](0020-transfer-plan-walk-forward-first-half.md) | Transfer Plan Walk-Forward First-Half Strategy | Accepted | Simulates multi-period transfer decisions under expanding-horizon evidence. |
| [0029](0029-planning-horizon-cap-10.md) | Planning Horizon Cap is 10 | Accepted | Caps transfer planning horizon at 10 gameweeks for solver stability and memory bounds. |
| [0030](0030-vendor-open-fpl-solver-highspy.md) | Vendor open-fpl-solver with HiGHS | Accepted | Vendors the open-fpl-solver MILP core using highspy; keeps custom planning logic in our layer. |
| [0031](0031-transfer-plan-start-open-deadline.md) | Transfer Plan Start Binds to Open Deadline | Accepted | Solver planning always roots from the next unexpired deadline. |
| [0033](0033-transfer-plan-hits-until-champion-bias.md) | Transfer Plan Hits Until Champion Bias Measured | Accepted | Retains paid transfers in plan until empirical Champion signed bias is verified. |
| [0042](0042-must-arms-optimal-vs-no-hit.md) | Must Scenarios: Optimal vs No Hit | Accepted | Establishes canonical scenario arm comparison between unconstrained hits and no-hit baselines. |
| [0043](0043-transfer-plan-solver-gap.md) | Solver Gap 1% Stopping Limit | Superseded | Superseded by ADR 0057 (0.0% exact gap). |
| [0053](0053-conservative-scenario-and-horizon-recovery.md) | Conservative Transfer Plan Scenario & Horizon Recovery | Accepted | Introduces variance-reduced scenario heuristics and horizon recovery. |
| [0057](0057-zero-gap-digest-caching-3-arm-transfer-plan.md) | Zero-Gap Default and Deterministic Digest Caching | Accepted | Enforces exact 0.0% MILP optimality gap with SHA-256 digest solve caching. Supersedes ADR 0043. |
| [0061](0061-strategic-variance-scenario-and-unconstrained-rename.md) | Strategic Variance Scenario Arm & Unconstrained Rename | Accepted | Replaces conservative heuristics with 5 mathematical MILP slack constraints; renames optimal to unconstrained. |
| [0065](0065-strategic-arm-horizon-penalty-scaling-and-ft-schedule.md) | Strategic Horizon Penalty Scaling & FT Schedule | Accepted | Discounted horizon scaling for hit/GK friction and diminishing emergency free transfer buffer. |

---

### 3. Dashboard, UI & Product Experience

| ADR | Title | Status | Summary |
|-----|-------|--------|---------|
| [0008](0008-interactive-dashboard-and-squad-builder.md) | Interactive Dashboard and Squad Builder | Superseded | Superseded by ADR 0018. |
| [0011](0011-multi-model-dashboard-comparison.md) | Multi-Model Dashboard Comparison and Selection | Accepted | Provides multi-model selection and side-by-side metric comparison. |
| [0017](0017-transfer-plan-dashboard.md) | Transfer Plan Dashboard View | Superseded | Superseded by ADR 0018. |
| [0018](0018-two-tab-transfer-plan-explorer.md) | Two-Tab Dashboard: Transfer Plan & Ownership Explorer | Accepted | Establishes primary two-tab product architecture. |
| [0021](0021-ownership-explorer-dashboard-planning-horizon.md) | Ownership Explorer Live Dashboard | Accepted | Standardizes Start–End planning horizons on the Explorer surface. |
| [0027](0027-squad-board-on-ownership-explorer.md) | Squad Board on Ownership Explorer | Accepted | Adds interactive 15-player squad board overlay to Explorer. |
| [0028](0028-dream-team-explorer-overlay.md) | Dream Team Explorer Overlay | Accepted | Integrates top projected XI Dream Team overlay directly into Explorer. |
| [0034](0034-transfer-plan-surface-peer-tab.md) | Transfer Plan Surface Peer Tab | Accepted | Promotes Transfer Plan from CLI-only to interactive dashboard peer tab. |
| [0052](0052-projection-parity-cli-dashboard.md) | Projection Parity Invariant (CLI & Dashboard) | Accepted | Mandates bit-for-bit numerical parity between CLI exports and interactive dashboard tables. |
| [0058](0058-straight-line-horizon-decision-tree.md) | Horizon-Locked Decision Tree Planner | Superseded | Superseded by ADR 0059 and ADR 0060. |
| [0059](0059-streamlit-transfer-planner.md) | Single Editable Transfer Plan in Streamlit | Superseded | Migrated planner to native Streamlit; superseded by consolidated dashboard in ADR 0060. |
| [0060](0060-one-streamlit-dashboard.md) | One Native Streamlit Dashboard | Accepted | Unifies Explorer, Transfer Plan Surface, Performance, and Methodology into a single Streamlit app. |

---

### 4. Data Ingestion & Operational Pipeline

| ADR | Title | Status | Summary |
|-----|-------|--------|---------|
| [0002](0002-custom-env-parser.md) | Custom .env Parser | Accepted | Zero-dependency `.env` parsing supporting variable expansion and comments. |
| [0004](0004-cross-season-player-code-mapping.md) | Cross-Season Player Identity via Permanent Code | Accepted | Maps player histories across seasons using immutable FPL `code` rather than transient season `id`. |
| [0012](0012-updated-playwright-fpl-oauth-flow.md) | Playwright FPL OAuth Flow & OneTrust Handling | Accepted | Robust automated authentication handling cookie consent banners and CSRF tokens. |
| [0019](0019-modified-fdr-production.md) | Production Scoring Uses Modified FDR | Accepted | Scales official FDR into continuous defense and attack multipliers. |
| [0023](0023-official-fpl-operational-dataset.md) | Official FPL Operational Dataset Boundary | Accepted | Strict isolation between official runtime data and historical research archives. |
| [0032](0032-live-season-pin-official-only.md) | Live Season Pin Official-Only | Accepted | Pins live season API snapshot with hash verification; never auto-committed to git. |
| [0036](0036-operational-pin-heal.md) | Operational Tables Heal from Live Season Pin | Accepted | Auto-recovers missing or corrupted operational tables from the verified Live Season Pin. |

---

### 5. Evaluation, Statistical Rigor & Promotion Gates

| ADR | Title | Status | Summary |
|-----|-------|--------|---------|
| [0038](0038-process-points-eval-target.md) | Process Points Evaluation Target | Accepted | Evaluates underlying expected points removing match-level variance noise. |
| [0044](0044-blended-eval-target-promotion-primary.md) | Blended Eval Target as Promotion Primary | Superseded | Replaced as primary promotion metric by rolling replay net points in ADR 0066; retained as diagnostic. |
| [0046](0046-point-in-time-backtest-and-statistical-gate.md) | Point-in-Time Backtest & Statistical Gate | Amended | Zero-leakage features retained; amended by ADR 0066 for rolling replay estimand and attempt registry. |
| [0047](0047-two-season-promotion-gate.md) | Two-Season Promotion Gate | Amended | Dev and Confirmation seasons retained; amended by ADR 0066 requiring fresh registered confirmation and manual adoption. |
| [0049](0049-gate-bootstrap-060-no-min-effect.md) | Bootstrap Bar 0.60 Without Arbitrary Minimum Effect | Superseded | Superseded by ADR 0066 search-wide family-wise error control (FWER ≤ 0.05 via Bonferroni/Holm). |
| [0054](0054-formation-constrained-xi-regret-and-playable-pool-guardrails.md) | Constrained Legal XI Regret & Playable Pool Guardrails | Amended | Constrained XI regret and squad churn retained as fast screens; amended by ADR 0066 rolling net-score primary. |
| [0062](0062-non-catastrophic-segment-loss-promotion-guardrail.md) | Non-Catastrophic Segment Loss Guardrail | Amended | Continuous segment loss floors integrated into ADR 0066 multi-season protocol and substantive guards. |
| [0064](0064-promotion-gate-and-evaluation-rigor-overhaul.md) | Promotion Gate & Evaluation Rigor Overhaul | Amended | Warm-seeded confirmation and non-wrapping MBB (L=5) retained; amended by ADR 0066 for 4-way verdicts and manual adoption. |
| [0066](0066-backtesting-and-promotion-foundation.md) | Backtesting and Promotion Foundation | Accepted | Primary rolling replay net FPL points, neutral GW1 anchor, substantive projection guards, 4-verdict taxonomy, immutable attempt registry, and manual adoption. |

---

## Chronological Index (0001–0066)

| Number | Identifier | Status | Subsystem |
|--------|------------|--------|-----------|
| 0001 | [add-scipy-dependency](0001-add-scipy-dependency.md) | Accepted | Modeling |
| 0002 | [custom-env-parser](0002-custom-env-parser.md) | Accepted | Pipeline |
| 0003 | [reconstruct-points-from-event-components](0003-reconstruct-points-from-event-components.md) | Accepted | Modeling |
| 0004 | [cross-season-player-code-mapping](0004-cross-season-player-code-mapping.md) | Accepted | Pipeline |
| 0005 | [hybrid-metrics-component-projection-model](0005-hybrid-metrics-component-projection-model.md) | Accepted | Modeling |
| 0006 | [fixture-first-projection-contract](0006-fixture-first-projection-contract.md) | Accepted | Modeling |
| 0007 | [event-level-empirical-bayes-projection-engine](0007-event-level-empirical-bayes-projection-engine.md) | Accepted | Modeling |
| 0008 | [interactive-dashboard-and-squad-builder](0008-interactive-dashboard-and-squad-builder.md) | Superseded | Dashboard |
| 0009 | [market-projection-ingestion-and-solio-minutes-blend](0009-market-projection-ingestion-and-solio-minutes-blend.md) | Superseded | Modeling |
| 0010 | [participation-state-snapshots-and-evaluation](0010-participation-state-snapshots-and-evaluation.md) | Accepted | Modeling |
| 0011 | [multi-model-dashboard-comparison](0011-multi-model-dashboard-comparison.md) | Accepted | Dashboard |
| 0012 | [updated-playwright-fpl-oauth-flow](0012-updated-playwright-fpl-oauth-flow.md) | Accepted | Pipeline |
| 0013 | [bottom-up-calibrated-component-metrics-and-rqi](0013-bottom-up-calibrated-component-metrics-and-rqi.md) | Accepted | Modeling |
| 0014 | [preseason-career-rate-and-destination-concede](0014-preseason-career-rate-and-destination-concede.md) | Accepted | Modeling |
| 0015 | [defensive-composite-score](0015-defensive-composite-score.md) | Accepted | Modeling |
| 0016 | [expected-role-prior-cold-start-minutes](0016-expected-role-prior-cold-start-minutes.md) | Superseded | Modeling |
| 0017 | [transfer-plan-dashboard](0017-transfer-plan-dashboard.md) | Superseded | Dashboard |
| 0018 | [two-tab-transfer-plan-explorer](0018-two-tab-transfer-plan-explorer.md) | Accepted | Dashboard |
| 0019 | [modified-fdr-production](0019-modified-fdr-production.md) | Accepted | Pipeline |
| 0020 | [transfer-plan-walk-forward-first-half](0020-transfer-plan-walk-forward-first-half.md) | Accepted | Solver |
| 0021 | [ownership-explorer-dashboard-planning-horizon](0021-ownership-explorer-dashboard-planning-horizon.md) | Accepted | Dashboard |
| 0022 | [club-fixture-minutes-and-rate-shrinkage](0022-club-fixture-minutes-and-rate-shrinkage.md) | Accepted | Modeling |
| 0023 | [official-fpl-operational-dataset](0023-official-fpl-operational-dataset.md) | Accepted | Pipeline |
| 0024 | [this-season-evidence-shrinkage](0024-this-season-evidence-shrinkage.md) | Accepted | Modeling |
| 0025 | [retire-expected-role](0025-retire-expected-role.md) | Accepted | Modeling |
| 0026 | [completed-club-fixtures-state-shrink](0026-completed-club-fixtures-state-shrink.md) | Accepted | Modeling |
| 0027 | [squad-board-on-ownership-explorer](0027-squad-board-on-ownership-explorer.md) | Accepted | Dashboard |
| 0028 | [dream-team-explorer-overlay](0028-dream-team-explorer-overlay.md) | Accepted | Dashboard |
| 0029 | [planning-horizon-cap-10](0029-planning-horizon-cap-10.md) | Accepted | Solver |
| 0030 | [vendor-open-fpl-solver-highspy](0030-vendor-open-fpl-solver-highspy.md) | Accepted | Solver |
| 0031 | [transfer-plan-start-open-deadline](0031-transfer-plan-start-open-deadline.md) | Accepted | Solver |
| 0032 | [live-season-pin-official-only](0032-live-season-pin-official-only.md) | Accepted | Pipeline |
| 0033 | [transfer-plan-hits-until-champion-bias](0033-transfer-plan-hits-until-champion-bias.md) | Accepted | Solver |
| 0034 | [transfer-plan-surface-peer-tab](0034-transfer-plan-surface-peer-tab.md) | Accepted | Dashboard |
| 0035 | [trailing-start-window](0035-trailing-start-window.md) | Accepted | Modeling |
| 0036 | [operational-pin-heal](0036-operational-pin-heal.md) | Accepted | Pipeline |
| 0037 | [fdr-fallback-multiplier-neutral](0037-fdr-fallback-multiplier-neutral.md) | Accepted | Modeling |
| 0038 | [process-points-eval-target](0038-process-points-eval-target.md) | Accepted | Evaluation |
| 0039 | [champion-participation-penalty-hybrid](0039-champion-participation-penalty-hybrid.md) | Accepted | Modeling |
| 0040 | [calibrated-matchup-share-shrinkage](0040-calibrated-matchup-share-shrinkage.md) | Accepted | Modeling |
| 0041 | [champion-calibrated-matchup-hybrid](0041-champion-calibrated-matchup-hybrid.md) | Accepted | Modeling |
| 0042 | [must-arms-optimal-vs-no-hit](0042-must-arms-optimal-vs-no-hit.md) | Accepted | Solver |
| 0043 | [transfer-plan-solver-gap](0043-transfer-plan-solver-gap.md) | Superseded | Solver |
| 0044 | [blended-eval-target-promotion-primary](0044-blended-eval-target-promotion-primary.md) | Superseded | Evaluation |
| 0045 | [champion-face-value-challenger](0045-champion-face-value-challenger.md) | Accepted | Modeling |
| 0046 | [point-in-time-backtest-and-statistical-gate](0046-point-in-time-backtest-and-statistical-gate.md) | Amended | Evaluation |
| 0047 | [two-season-promotion-gate](0047-two-season-promotion-gate.md) | Amended | Evaluation |
| 0048 | [champion-multi-feature-assist-challenger](0048-champion-multi-feature-assist-challenger.md) | Accepted | Modeling |
| 0049 | [gate-bootstrap-060-no-min-effect](0049-gate-bootstrap-060-no-min-effect.md) | Superseded | Evaluation |
| 0050 | [champion-learned-start-challenger](0050-champion-learned-start-challenger.md) | Accepted | Modeling |
| 0051 | [champion-club-def-prior-challenger](0051-champion-club-def-prior-challenger.md) | Accepted | Modeling |
| 0052 | [projection-parity-cli-dashboard](0052-projection-parity-cli-dashboard.md) | Accepted | Dashboard |
| 0053 | [conservative-scenario-and-horizon-recovery](0053-conservative-scenario-and-horizon-recovery.md) | Accepted | Solver |
| 0054 | [formation-constrained-xi-regret-and-playable-pool-guardrails](0054-formation-constrained-xi-regret-and-playable-pool-guardrails.md) | Amended | Evaluation |
| 0055 | [champion-def-xg-shrink-challenger](0055-champion-def-xg-shrink-challenger.md) | Accepted | Modeling |
| 0056 | [operational-zero-availability-hard-dnp](0056-operational-zero-availability-hard-dnp.md) | Accepted | Modeling |
| 0057 | [zero-gap-digest-caching-3-arm-transfer-plan](0057-zero-gap-digest-caching-3-arm-transfer-plan.md) | Accepted | Solver |
| 0058 | [straight-line-horizon-decision-tree](0058-straight-line-horizon-decision-tree.md) | Superseded | Dashboard |
| 0059 | [streamlit-transfer-planner](0059-streamlit-transfer-planner.md) | Superseded | Dashboard |
| 0060 | [one-streamlit-dashboard](0060-one-streamlit-dashboard.md) | Accepted | Dashboard |
| 0061 | [strategic-variance-scenario-and-unconstrained-rename](0061-strategic-variance-scenario-and-unconstrained-rename.md) | Accepted | Solver |
| 0062 | [non-catastrophic-segment-loss-promotion-guardrail](0062-non-catastrophic-segment-loss-promotion-guardrail.md) | Amended | Evaluation |
| 0063 | [champion-adaptive-causal-challenger](0063-champion-adaptive-causal-challenger.md) | Accepted | Modeling |
| 0064 | [promotion-gate-and-evaluation-rigor-overhaul](0064-promotion-gate-and-evaluation-rigor-overhaul.md) | Amended | Evaluation |
| 0065 | [strategic-arm-horizon-penalty-scaling-and-ft-schedule](0065-strategic-arm-horizon-penalty-scaling-and-ft-schedule.md) | Accepted | Solver |
| 0066 | [backtesting-and-promotion-foundation](0066-backtesting-and-promotion-foundation.md) | Accepted | Evaluation |
