# Research Index & Guidelines

**Updated**: 2026-10-29 (+07:00)
**Status**: Live index. Active research topics tracked below.

---

## Eval canon (session-durable)

Agents starting any model / Candidate / Champion work **read this block first**. Topic notes hold evidence; this block holds which metric is primary for which job.

**Leakage / holdout (ADR 0046, 0047, 0064, 0066):** 2025-26 = development season. Promotion = scientific verdict PASS on multi-season normalized evaluation: 2025-26 (seed 2024-25) **and** 2024-25 (seed 2023-24; un-tuned confirmation registered in immutable attempt registry). Non-wrapping MBB ($L=5$) paired stored-score bootstrap with family-wise error rate control ($\text{FWER} \le 0.05$ via Bonferroni/Holm, ADR 0066). 2026-27 GW6+ sealed: no tuning/smoke/ablation; one post-promotion check per Champion. All runs logged in Candidate Ledger and confirmation registry. Backtest features without snapshot are point-in-time (price/club from pre-target rows; season-end player columns dropped) — never read `players.parquet` season totals, status, ownership, or set-piece orders in backtest code.

**Before proposing a Candidate lever:** read [Candidate Ledger](candidate-ledger/candidate-ledger.md). Dead lever = no retry until `Revisit after` (evidence date + 1 year); new Champion does not reopen early. Record every attempt there.

### Promotion & model selection (production gate)

| Job | Primary | Guardrails & Diagnostics | Authority |
|-----|---------|--------------------------|-----------|
| Historical Promotion Gate / Candidate vs Champion | **Actual Native-Season Net FPL Points** (gross points minus official hit deductions) under independent 6-GW rolling Strategic transfer plan replay from neutral GW1 ownership anchor; paired non-wrapping MBB ($L=5$) with search-wide $\text{FWER} \le 0.05$ (Bonferroni/Holm); multi-season normalized weighting (ADR 0066); non-catastrophic segment loss floors (ADR 0062, 0066) | Substantive Projection Non-Inferiority Guards (total points, minutes, G/A/CS/saves/bonus via `backtesting/projection_guards.py`); Invariant Common Population Masks; Ledger Reconciliation; Supporting Diagnostics: Constrained Formation XI Regret (£83.5m, max 3/club), Squad Churn (≤ +0.50), Blended Eval Target, Process Points | [ADR 0066](../adr/0066-backtesting-and-promotion-foundation.md) · [ADR 0064](../adr/0064-promotion-gate-and-evaluation-rigor-overhaul.md) · [ADR 0062](../adr/0062-non-catastrophic-segment-loss-promotion-guardrail.md) · [ADR 0061](../adr/0061-strategic-variance-scenario-and-unconstrained-rename.md) · [ADR 0057](../adr/0057-zero-gap-digest-caching-3-arm-transfer-plan.md) · [ADR 0047](../adr/0047-two-season-promotion-gate.md) · [ADR 0046](../adr/0046-point-in-time-backtest-and-statistical-gate.md) |
| Champion Signed Bias gate (Hits / no mean calibrate) | Realized `signed_bias` | `mae`, `minutes_bias` | [ADR 0033](../adr/0033-transfer-plan-hits-until-champion-bias.md) · [champion-signed-bias](champion-signed-bias-2025-26/champion_bias_summary.csv) `signed_bias` |
| Supporting totals diagnostics in research companions | Triple-report `realized` \| `process` \| `blend` | Formation XI Regret, Squad Churn | ADR 0044 · ADR 0054 · ADR 0066 |

**Four-way scientific verdicts (ADR 0066):**
- **`pass`**: Statistically significant positive net score delta meeting bootstrap bar, material-loss floors, and substantive guards.
- **`fail`**: Statistically demonstrated regression or material harm.
- **`inconclusive`**: Uncertainty spans zero or fresh confirmation evidence pending; routes to registered confirmation, NOT 1-year Dead Lever lock.
- **`invalid`**: Contract breach, execution defect, or inert prototype; does NOT trigger 1-year Dead Lever lock.

**Manual Adoption Authority (ADR 0066):** Evaluation CLI and CI read-only. Legacy smoke/blended-XI comparisons diagnostic only; their `pass` fields cannot authorize promotion or new Dead Lever locks. Shared evaluator reconstructs candidate-bound replay evidence with complete guards and registered confirmation. Production adoption requires empirical admission, finalized registry, explicit approval reference, exact approved bundle hash and expected current Champion; [operator workflow](../testing/operator-workflow.md). Current empirical admission/calibration remains pending; synthetic verification cannot authorize adoption. Bonferroni budget supported; chronological Holm rejected; FWER target requires valid calibrated inference.

**Rejected as promotion primary:** Process-only; Blended without Realized/Process guardrails; single-gameweek unconstrained regret; component MAE; FPL `ep_*`.

### Event Component gap diagnosis (which ledger row to improve)

| Job | Primary | Diagnostics | Authority |
|-----|---------|-------------|-----------|
| Rank gap Event Component | **Realized** `mse_share` = $\mathrm{mean}(e_c\cdot e)/\mathrm{mean}(e^2)$ | Process G/A twins; Poisson-xGC CS/GC twins; `demotion_label` ∈ {`structural`,`variance`,`link-bias`,`no_twin`} | [champion-component-gap](champion-component-gap/champion-component-gap.md) · `component_gap_summary.csv` `mse_share` |
| Demotion thresholds | θ twin shrink ≥ **0.50**; τ \|signed_bias\| ≤ **0.05** | CS/GC shrink + large Realized bias → `link-bias` | Same note Method |
| Pools | `all` primary crown; `mins_60` rate check | Position `ALL` + GKP/DEF/MID/FWD secondary | Grill 2026-09-25 |

**Rejected for component ranking:** component MAE; raw \|bias\| alone; relative bias; Blended/Process as component ledger primary; Extended Process Points (deferred).

**Last crown (2025-26 gate, former Champion `hold_chase_challenger`; not recomputed for `face_value_challenger`, `pool=all` `position=ALL`):** `xp_goals` `structural` — inherited across Comparison Slate. CS/assists often `variance` on `all`; CS `link-bias` on `mins_60`.

### Glossary pointers

`CONTEXT.md`: Rolling Replay Net Score · Neutral GW1 Ownership Anchor · Realized Points · Process Points · Blended Eval Target · Poisson-xGC Twin · Extended Process Points · Four-Way Scientific Verdicts · Immutable Attempt Registry · Model Champion / Candidate / Comparison Slate.

---

## Active Research Index

- **Backtesting and promotion foundation (2026-10-29)**: [ADR 0066](../adr/0066-backtesting-and-promotion-foundation.md) · [Q1-Q28 agreements](backtesting-promotion-foundation/backtesting-promotion-foundation.md) · [Independent review](backtesting-promotion-foundation/independent-review.md) · [Ownership-anchor evidence](backtesting-promotion-foundation/ownership-anchor-feasibility.md) · [Legacy verdicts audit report](backtesting-promotion-foundation/legacy_verdicts_audit.md) · [Audit CSV](backtesting-promotion-foundation/legacy_verdicts_audit.csv) · [Preflight plan](backtesting-promotion-foundation/preflight-plan.md) (rolling transfer plan replay net score primary; neutral GW1 ownership anchor; substantive projection guards; stored-score block bootstrap with FWER control; 4-way scientific verdicts; immutable attempt registry; prospective capture; manual adoption).

- **Candidate Ideation & External Model Collaboration (2026-10-28)**: [Note](candidate-ideation/candidate-ideation.md) · [Prompt Brief](candidate-ideation/candidate_model_ideation_prompt.md) · [Minutes report](candidate-ideation/minutes-ideation-response.md) · [Attack report](candidate-ideation/attack-ideation-response.md) · [Defense report](candidate-ideation/defense-ideation-response.md) · [Idea Queue](candidate-ideation/idea_queue.csv) · [Smoke](candidate-ideation/smoke_results.csv) · [Prototype sources/checks](candidate-ideation/prototypes/README.md) (EXT-07/09 full-dev FAIL recorded in ledger; EXT-08 partial grid checkpointed (k2/k4 FAIL, k8/k16 unfinished); continue remaining grid then EXT-11/12; EXT-10 blocked by Dead decoder prerequisite/seed summaries, EXT-13 by schedule provenance. Model-neutral LLM guidance and report names; prompt regenerated from current ledger. Champion unchanged; no confirmation or holdout run.)
- **Promotion Gate & Evaluation Rigor Overhaul (2026-10-24)**: [Note](backtest-gate-reform/backtest-gate-reform.md) · [Summary](backtest-gate-reform/historical_candidate_re_evaluation_summary.csv) · [Tickets](backtest-gate-reform/wayfinder-tickets.json) · [Wayfinder Map #166](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/166) (Wayfinder Map #166 charted with 7 decision tickets #167–#173; resolving unseeded confirmation regime mismatch, short-panel Nickell bias, unconstrained LegalXI churn blindness, circular bootstrap boundary wrap, and endogenous playable pool masking under ADR 0064)
- **Adaptive Causal ML Challenger (2026-10-21)**: [Note](ml-adaptive-champion/ml-adaptive-champion.md) · [Gate](ml-adaptive-champion/candidate_gate.csv) `combined_delta` / `boot_p_gt0` · [Smoke](ml-adaptive-champion/smoke_results.csv) `combined_delta` / `segs` (Adaptive Causal ML Candidate stacking Ridge $p_{\text{start}}$, duration offset, shrunk xG goals residual, and LOO assist finishing with 100% Champion stability across GW1–19 and activation at GW20+; dev 2025-26 PASS +0.736 P 0.992; confirm 2024-25 PASS +0.226 P 0.656 under ADR 0062; Human Gate adoption queued)
- **Decoupled projection architecture & Decomposed Event Challenger (2026-10-14)**: [Proposal](decoupled-projection-architecture/decoupled_minutes_event_proposal.md) · [Champion context](decoupled-projection-architecture/champion_model_context.md) · [Gate context](decoupled-projection-architecture/backtesting_and_promotion_gate_context.md) · [Prompts](decoupled-projection-architecture/agent_prompts_for_ideation.md) · [Tickets](decoupled-projection-architecture/wayfinder-tickets.json) · [Oracle Gate Prototype](decoupled-projection-architecture/prototype_oracle_gate.py) · [Oracle Gate Demo](decoupled-projection-architecture/oracle_gate_demo.html) · [Minutes Gate Prototype](decoupled-projection-architecture/prototype_minutes_gate.py) · [Minutes Gate Demo](decoupled-projection-architecture/minutes_gate_demo.html) (Wayfinder Map #159; tickets #160, #161, & #162 closed; 3-tier gating: Standalone Minutes Gate, Oracle Minutes Event Gate, Integrated Composite Gate)
- **Candidate Ledger (tried / untried levers)**: [Ledger](candidate-ledger/candidate-ledger.md) (Shipped / Dead with `Revisit after` / Open next-lever pool)
- **Champion component gap**: [Note](champion-component-gap/champion-component-gap.md) · [Summary](champion-component-gap/component_gap_summary.csv) `mse_share` · [Totals](champion-component-gap/component_gap_totals.csv) `realized_mae` (Realized `mse_share` primary; Process G/A + Poisson-xGC CS/GC twins; demotion / `link-bias`) · [Segment loss #123](champion-component-gap/segment-loss-121.md) · [segment summary](champion-component-gap/segment_loss_121_summary.csv) `blend_regret_delta_champ_minus_cand` · [AFK segment-fix experiments #124](champion-component-gap/segment_fix_experiments_124.md) · [CS/GC sweep](champion-component-gap/segment_fix_sweep_124.csv) · [bonus sweep](champion-component-gap/bonus_scale_sweep_124.csv) · [Bonus/BPS inventory #125](champion-component-gap/bonus-bps-inventory-125.md) · [Layer diagnosis #133](champion-component-gap/layer-diagnosis-133.md) · [gate](champion-component-gap/layer_diagnosis_133_gate.csv) `late_delta` · [late position](champion-component-gap/layer_diagnosis_133_late_position.csv) `regret_delta`
- **Champion signed bias (2025-26 GW1–38)**: [Note](champion-signed-bias-2025-26/champion-signed-bias-2025-26.md) · [Summary](champion-signed-bias-2025-26/champion_bias_summary.csv) `signed_bias`
- **First-Half 5-DEF Rotation Strategy (GW1–19)**: [Note](def-fdr-rotation-gw1-19/def-fdr-rotation-gw1-19.md) · [Club Occupancy](def-fdr-rotation-gw1-19/def_rotation_club_occupancy.csv) `rank_mod_fdr` / `total_mod_fdr` · [Summary](def-fdr-rotation-gw1-19/def_rotation_5sets_summary.csv) `total_mod_fdr` · [Starting DEFs](def-fdr-rotation-gw1-19/starting_defs_gw1_19.csv) · [Schedule Picks](def-fdr-rotation-gw1-19/gw1_19_def_rotation_schedule_picks.csv)
- **Transfer Plan Walk-Forward (2025-26 GW1–19)**: [Note](tp-walkforward-gw1-19-2025-26/tp-walkforward-gw1-19-2025-26.md) · [Summary](tp-walkforward-gw1-19-2025-26/tp_walkforward_summary.csv) `realized_points` (ranked; attack FT / 3-4-3 / Defcon-Floor) · [Club Occupancy](tp-walkforward-gw1-19-2025-26/def_rotation_club_occupancy.csv) `rank_mod_fdr`

## Closed

- **Early Gameweek ML Activation & Sample Maturity (2026-10-23)**: [Note](../archive/early-gw-ml-exploration/early-gw-ml-exploration.md) · [Gate](../archive/early-gw-ml-exploration/candidate_gate.csv) `combined_delta` / `boot_p_gt0` · [Smoke](../archive/early-gw-ml-exploration/smoke_results.csv) `combined_delta` / `segs` (`bounded_causal_challenger` dev PASS +0.156, confirm 2024-25 unseeded FAIL -2.280; confirms GW1-19 fallback necessary; dead until 2027-10-23)
- **Apex Predator Challenger (2026-10-21)**: [Note](../archive/apex-predator-challenger/apex-predator-challenger.md) · [Gate](../archive/apex-predator-challenger/candidate_gate.csv) `combined_delta` / `boot_p_gt0` · [Smoke](../archive/apex-predator-challenger/smoke.csv) `combined_delta` / `segs` (dev PASS +0.840; confirm unseeded FAIL -0.153; dead until 2027-10-21)
- **ML Component Champion Blueprint (2026-10-21)**: [Blueprint](../archive/ml-component-champion-blueprint/ml-component-champion-blueprint.md) · [Gate](../archive/ml-component-champion-blueprint/candidate_gate.csv) · [Tier 1 Minutes](../archive/ml-component-champion-blueprint/tier1_minutes_ablation.csv) · [Tier 2 Oracle](../archive/ml-component-champion-blueprint/tier2_oracle_event_ablation.csv) (causal panel feature engine and component ablations; dev FAIL segment consistency; dead until 2027-10-21)
- **MILP solver strategic constraints & variance control (2026-10-19)**: [Note](../archive/milp-variance-constraints/milp-variance-constraints.md) (Quantitative justification for adding strategic variance-control constraints to MILP squad optimizers; codified into ADR 0061)
- **Multi-component progression ladder (2026-10-13)**: [Note](../archive/multi-component-ladder/multi-component-ladder.md) · [Smoke](../archive/multi-component-ladder/smoke_results.csv) (dev FAIL across unseeded tenure decay, creative defender assists, and stacked club priors; dead until 2027-10-13)
- **DDP and autosub probability formulation (2026-10-02)**: [Note](../archive/ddp-autosub-formulation/ddp-autosub-formulation.md) (Mathematical formulation of Dynamic Disruption Probability, bench weight horizon scaling, Poisson-Binomial autosub; Wayfinder ticket #136)
- **Player projection calibration & tier de-biasing (2026-10-01)**: [Note](../archive/player-projection-calibration/player-projection-calibration.md) · [Gate](../archive/player-projection-calibration/candidate_gate.csv) · [Smoke](../archive/player-projection-calibration/smoke_results.csv) (Lane 1 bonus saturation dev FAIL; Lane 2 calibrated rate confirm FAIL -0.449; dead until 2027-10-01)
- **Formation eval retest (2026-10-01)**: [Note](../archive/formation-eval-retest/formation-eval-retest.md) · [Gate](../archive/formation-eval-retest/candidate_gate.csv) · [Smoke](../archive/formation-eval-retest/smoke_results.csv) (Past dev winners re-screened under ADR 0054 legal formation XI eval; `def_xg_shrink_challenger` promoted to Champion ADR 0055)
- **Club starting mass redistribution (2026-10-01)**: [Note](../archive/club-starting-mass-redistribution/club-starting-mass-redistribution.md) · [Smoke](../archive/club-starting-mass-redistribution/smoke_results.csv) (11.0 starting mass conservation failed dev gate -3.14 to -4.13; dead until 2027-10-01)
- **Component model ideas (2026-09-28)**: [Note](../archive/component-model-ideas/component-model-ideas.md) · [Component list](../archive/component-model-ideas/component_list.csv) · [Idea queue](../archive/component-model-ideas/idea_queue.csv) · [Smoke](../archive/component-model-ideas/smoke_results.csv) · [Gate](../archive/component-model-ideas/candidate_gate.csv) (All 29 ideas evaluated: ATK-05 promoted Champion ADR 0051; 3 confirm-fail; 25 dead/failed; queue 100% complete)
- **Asymmetric finishing challenger & Dual-lane search round 2 (2026-09-28)**: [Note](../archive/asymmetric-finishing-challenger/asymmetric-finishing-challenger.md) · [Gate](../archive/asymmetric-finishing-challenger/candidate_gate.csv) · [Smoke](../archive/asymmetric-finishing-challenger/smoke_results.csv) (dev PASS +0.261; confirm 2024-25 FAIL -0.231; dead until 2027-09-28)
- **Dual-lane Candidate search (2026-09-28)**: [Note](../archive/dual-lane-candidate-search/dual-lane-candidate-search.md) · [Smoke](../archive/dual-lane-candidate-search/smoke_results.csv) · [Gate](../archive/dual-lane-candidate-search/candidate_gate.csv) (88 variants; `learned_start_challenger` promoted Champion ADR 0050; 11 levers dead)
- **Multi-feature event rate (2026-09-28)**: [Note](../archive/multi-feature-event-rate/multi-feature-event-rate.md) · [Gate](../archive/multi-feature-event-rate/candidate_gate_summary.csv) · [Smoke](../archive/multi-feature-event-rate/smoke_results.csv) · [Confirmation](../archive/multi-feature-event-rate/confirmation_gate_summary.csv) (GLM assist rate promoted Champion ADR 0048; goals/GC/stack levers dead)
- **Face-value Challenger (2026-09-28)**: [Note](../archive/face-value-challenger/face-value-challenger.md) · [Gate](../archive/face-value-challenger/face_value_gate_summary.csv) · [Smoke lanes](../archive/face-value-challenger/smoke_lane_results.csv) · [Point-in-time re-gate](../archive/face-value-challenger/point_in_time_regate.csv) (ADR 0045 Champion; point-in-time re-gate ADR 0046 regret tie)
- **Cross-GW dispersion (2025-26)**: [Note](../archive/xp-cross-gw-dispersion/xp-cross-gw-dispersion.md) · [Summary](../archive/xp-cross-gw-dispersion/dispersion_summary.csv) · [Components](../archive/xp-cross-gw-dispersion/fixture_component_swing.csv)
- **Downside attack scale**: [Note](../archive/fixture-downside-scale/fixture-downside-scale.md) · [Summary](../archive/fixture-downside-scale/downside_swing_summary.csv) `blend_mae`
- **Hold vs chase (2025-26)**: [Note](../archive/hold-vs-chase-2025-26/hold-vs-chase-2025-26.md) · [Summary](../archive/hold-vs-chase-2025-26/hold_chase_summary.csv) `value`
- **Matchup share add-on (2025-26)**: [Note](../archive/matchup-share-addon-2025-26/matchup-share-addon-2025-26.md) · [Summary](../archive/matchup-share-addon-2025-26/matchup_share_summary.csv) `signed_bias` (shipped Matchup → Strength → neutral, ADR 0037/0040)
- **Premier League arrival xG/xA translation**: [Note](../archive/epl-arrival-xg-xa-adjustment/epl-arrival-xg-xa-adjustment.md) · [Summary](../archive/epl-arrival-xg-xa-adjustment/arrival_xg_xa_summary.csv) · [Before/after](../archive/epl-arrival-xg-xa-adjustment/arrival_xg_xa_before_after.csv) · [Literature](../archive/epl-arrival-xg-xa-adjustment/literature-sources.md)
- **Set-piece taker vs Defcon**: [Note](../archive/set-piece-taker-vs-defcon/set-piece-taker-vs-defcon.md) · [DEF break-even](../archive/set-piece-taker-vs-defcon/def_breakeven.csv) · [MID break-even](../archive/set-piece-taker-vs-defcon/mid_breakeven.csv)
- **First-Half GKP Rotation Pairs (GW1–19)**: [Note](../archive/gkp-fdr-rotation-gw1-19/gkp-fdr-rotation-gw1-19.md) · [Summary](../archive/gkp-fdr-rotation-gw1-19/gkp_rotation_pairs_summary.csv) · [Raya partners](../archive/gkp-fdr-rotation-gw1-19/raya_rotation_partners.csv) · [Starting GKPs](../archive/gkp-fdr-rotation-gw1-19/starting_gkps_gw1_19.csv) · [Schedule Picks](../archive/gkp-fdr-rotation-gw1-19/gw1_19_rotation_schedule_picks.csv)
- **First-Half Chip Strategy (source synthesis)**: [Note](../archive/fpl-first-half-chip-strategy/fpl-first-half-chip-strategy.md)
- **Wayfinder Transfer Plan dashboard spec**: archived to [../archive/wayfinder-transfer-plan-spec/](../archive/wayfinder-transfer-plan-spec/). Product UI/UX spec retired from active research root per research boundary rule.
- **Fixture-swing candidates** (2026-09-24): both arms dead — multiplicative breached easy cap (+0.681) and lost blend MAE; additive tied MAE with worse easy bias. Champion stands. Note: [fixture-swing-candidates](../archive/fixture-swing-candidates/fixture-swing-candidates.md) · [Summary](../archive/fixture-swing-candidates/candidate_swing_summary.csv) `blend_mae`.
- **Fixture xP scale without Club Strength** (2026-09-22): production [ADR 0037](../adr/0037-fdr-fallback-multiplier-neutral.md) = Matchup Share → Club Strength → neutral. Prior rejected scales: [FDR regime](../archive/dual-vector-fdr-regime-2025-26/dual-vector-fdr-regime-2025-26.md) · [Official xG Dual-Vector](../archive/dual-vector-official-xg-2025-26/dual-vector-official-xg-2025-26.md) · [Team Poisson λ](../archive/team-poisson-lambda-2025-26/team-poisson-lambda-2025-26.md). Gate evidence also [matchup-share](../archive/matchup-share-addon-2025-26/matchup_share_summary.csv) `signed_bias`.

---

## Research Lifecycle & Archiving Protocol

Research topics transition through three distinct lifecycle states to keep `docs/research/` compact, focused, and navigable:

1. **Active (`docs/research/<slug>/`)**:
   - In-flight candidate ideation and exploration queues (`candidate-ideation`).
   - Active Promotion Gate standards and backtesting framework reform (`backtest-gate-reform`).
   - Active Champion documentation and provisional candidate blue-sky notes (`ml-adaptive-champion`).
   - Active benchmark evaluation targets and component gap diagnosis canon (`champion-component-gap`, `champion-signed-bias-2025-26`).
   - Structural prototypes and verified rotation baselines referenced by active regression test fixtures (`decoupled-projection-architecture`, `def-fdr-rotation-gw1-19`, `tp-walkforward-gw1-19-2025-26`).
   - Reusable template (`template/`).

2. **Authoritative / Protected Registries (Never Archive from `docs/research/`)**:
   - `candidate-ledger/` ([`candidate-ledger.md`](candidate-ledger/candidate-ledger.md) and [`candidate_ledger.csv`](candidate-ledger/candidate_ledger.csv)) is the permanent source of truth for evaluated levers, baseline deltas, and 1-year retest moratoriums. It is never moved to `docs/archive/`.
   - Topics actively written to by CLI commands (such as [`champion-signed-bias-2025-26`](champion-signed-bias-2025-26/champion_bias_summary.csv) written by `uv run python -m commands.measure_champion_bias`) remain live in `docs/research/`.

3. **Archived (`docs/archive/<slug>/`)**:
   - Completed candidate queue sweeps and exhausted exploration batches.
   - Evaluated candidate variants that failed dev or confirmation gates and are recorded dead in `candidate_ledger.csv`.
   - Superseded architecture proposals, historical seasonal heuristics, and closed strategy whitepapers.
   - **Procedure**: Move the entire directory `docs/research/<slug>/` to `docs/archive/<slug>/` (carrying all markdown notes, runners, and companion CSV/HTML artifacts). Update pointers in `INDEX.md` `## Closed` and references in `candidate_ledger.csv`.

---

## Research Conventions & Standards

- **Colocate**: note, runners, and companion CSV/HTML live in `docs/research/<topic-slug>/`. No `data/research/`. No research companions under `data/archive/`.
- **Live root**: `docs/research/` holds `INDEX.md`, `template/`, and active topic folders only. No loose notes beside INDEX.
- **Archive**: move the whole topic folder to `docs/archive/<topic-slug>/`. Companions travel with it. Leave a pointer here.
- **Season ingest**: `data/archive/YYYY-YY/` only (raw/processed FPL snapshots). Not research CSVs.
- **Reports**: `data/reports/` for solver/tool execution outputs.
- **Filename**: stable topic slugs; no date prefixes. Start from `docs/research/template/research-note.md`.
- **Required sections**: `Updated`, `Data stamp`, `Season`, `Purpose`, `Sources`, `Agent Prompt`, `Method`, `Findings`, `Decision`, `Risks and unknowns`.
- **Timestamps**: `Updated` = note revision (ISO 8601 + timezone). `Data stamp` = evidence cutoff. No duplicate `Last update`.
- **Artifact**: link companions in the note header; same-folder relative path.
- **Evidence**: keep `Source synthesis` separate from `Project interpretation`. Label unvalidated claims.
- **Metrics**: every quantitative note includes `### Metric Definitions & Direction` (Definition/Formula, Direction, Ideal Benchmark, Description). Promotion vs component-gap primary metrics live in **Eval canon** at top of this INDEX — do not invent a competing primary in a topic note.
- **Agent Prompt**: inputs, refresh steps, stable output path in the topic folder, scratch cleanup.
- **Figures**: caches of named companion CSV cells. Prompt names path + column (e.g. `gkp_rotation_pairs_summary.csv` `total_mod_fdr`), not a numeric snapshot.

---

## Master Metric Definitions & Interpretation Reference

| Domain / Area | Metric | Symbol | Definition / Formula | Direction | Ideal / Benchmark | Description |
|---|---|---|---|---|---|---|
| **Rotation** | **Total Modified FDR** | `total_mod_fdr` | $\sum_{g=1}^{19} \min(\text{Mod FDR}_A(g), \text{Mod FDR}_B(g))$ | Lower is better $\downarrow$ | **$\le 44.00$** | Cumulative rotated fixture difficulty across GW1–19 with home/away weighting. |
| **Rotation** | **Average Modified FDR** | `avg_mod_fdr` | $\frac{\text{total\_mod\_fdr}}{19}$ | Lower is better $\downarrow$ | **$\le 2.30$ / GW** | Mean difficulty of the started goalkeeper each gameweek. Unrotated baseline is $\approx 3.00$. |
| **Rotation** | **Total Base FDR** | `total_base_fdr` | $\sum_{g=1}^{19} \min(\text{Base FDR}_A(g), \text{Base FDR}_B(g))$ | Lower is better $\downarrow$ | **$\le 46.00$** | Unmodified official FPL FDR sum under weekly best-fixture rotation. |
| **Rotation** | **Defensive Composite Score** | `DCS` | $0.60 \times S_{\text{Score}} + 0.40 \times S_{\text{Risk}}$ | Higher is better $\uparrow$ | **$\ge 80.0$ / 100** | Live ranking metric for a Defensive Rotation Set. |
| **Rotation** | **Fixture Overlap Index** | `FOI` | $\frac{1}{T}\sum (1 - p_{\text{cs1}})(1 - p_{\text{cs2}})$ | Lower is better $\downarrow$ | **$< 0.50$** (Min $\approx 0.40$) | Probability of joint clean-sheet failure across paired goalkeepers. |
| **Rotation** | **FDR Schedule Correlation** | $r$ / `avg_corr` | Pearson correlation between club FDR sequences across gameweeks | Lower is better $\downarrow$ (Negative) | **$r \le -0.10$** | Measures fixture alignment. Negative correlation ensures one team has an easy fixture when the other faces a top-6 opponent. |
| **Rotation** | **Zero-Difficult Gameweeks** | `Zero-Diff %` | % of GWs where all started assets face FDR $\le 3$ | Higher is better $\uparrow$ | **$100.0\%$** | Completely avoids fielding starters against FDR $\ge 4$ elite attacks. |
| **Rotation** | **Easy-week coverage** | `pct_gw_mod_le_2_25` | $100 \times n(\min(\text{Mod FDR}_A,\text{Mod FDR}_B) \le 2.25) / 19$ | Higher is better $\uparrow$ | **$100\%$ (19/19)** | Share of GW1–19 where started GKP faces only official FDR 1–2 (away FDR 2 = 2.25 still counts; FDR 3 home = 2.75 fails). |
| **Rotation** | **Rotated / Effective FDR** | `Rot FDR` | Average weekly fixture difficulty rating across started slots | Lower is better $\downarrow$ | **$\le 2.40$** | Benchmark baseline for unrotated schedule is $3.00$; rotation targets $\le 2.40$. |
| **Rotation** | **Rotated Expected Points** | `Rotated xP` | $\sum_{t=1}^N \max_{i \in \text{squad}} xP_{i,t}$ | Higher is better $\uparrow$ | Maximized | Sum of weekly projected points under optimal starting selection. |
| **Walk-Forward** | **Champion signed bias** | `signed_bias` | $\mathrm{mean}(\text{projected\_points} - \text{actual\_points})$ | Near zero (context) | Gate in `champion_bias_summary.csv` `signed_bias` | Model Champion vs Realized Points. Positive = overprediction. Not FPL `ep_*`. |
| **Walk-Forward** | **Component MSE share** | `mse_share` | $\mathrm{mean}(e_c\cdot e)/\mathrm{mean}(e^2)$ on Realized ledger | Context (rank by $\|\,\|$) | `component_gap_summary.csv` `mse_share` | Which Event Component drives Official squared error. Not component MAE. Not promotion primary. |
| **Walk-Forward** | **Twin shrink** | `twin_shrink` | $1 - \|mse\_share\_twin\|/\|mse\_share\|$ | Higher → more finish/link noise | ≥ 0.50 with τ → demotion check | Process G/A or Poisson-xGC twin vs Realized share |
| **Walk-Forward** | **Demotion label** | `demotion_label` | `structural` / `variance` / `link-bias` / `no_twin` | Context | structural = Candidate lever | Gap diagnosis decision label |
| **Walk-Forward** | **First-Half Realized Points** | `realized_points` | Scoring-15 Realized Points GW1–19 after autosubs; Hits forbidden | Higher is better $\uparrow$ | Unconstrained baseline | Transfer Plan Walk-Forward ranking object (ADR 0020). |
| **Chip Strategy** | **Scenario Expected Points** | `Total xP` | Cumulative projected points across target window under Chip Path | Higher is better $\uparrow$ | Maximized | MILP-optimized points under chip constraints. |
| **Chip Strategy** | **Value Over Chip Baseline** | `VoC` | $xP(\text{Scenario } k) - xP(\text{No Chip Baseline})$ | Higher is better $\uparrow$ | **$\ge +12.0\text{ xP}$** | Net points gained by deploying specific chip combinations early vs holding. |
| **Ownership** | **Projected Rate** | `xP/90` | Expected points per 90 minutes normalized by role and fixture | Higher is better $\uparrow$ | **$\ge 5.0$** (Enabler) / **$\ge 7.0$** (Premium) | Normalized per-minute scoring potential. |
| **Ownership** | **Ownership Popularity** | `Ownership %` | Game-wide `selected_by_percent` from FPL API | Context-dependent | **$< 5.0\%$** (Diff) / **$> 30.0\%$** (Template) | Raw ownership proportion across all fantasy managers. |
| **Set-Piece** | **Team Set-Piece Net Swing** | `Net Swing` | $\Delta \text{xG}_{\text{set-piece}} - \Delta \text{xGA}_{\text{set-piece}}$ | Higher is better $\uparrow$ | **$> +0.20\text{ xG/game}$** | Net goal expectancy added via set-piece offense minus set-piece defense conceded. |
| **Set-Piece** | **Attack xP per start** | `xp_attack_per_start` | $(\text{goals} \times \text{goal pts} + \text{assists} \times 3) / n_{\ge60}$ | Higher $\uparrow$ | DEF $\ge 1.0$ / MID $\ge 1.5$ | Reconstructed attacking FPL points per 60+ minute appearance. |
| **Set-Piece** | **Defcon hit rate** | `defcon_hit_rate` | Starts reaching CBIT/CBIRT threshold / starts | Higher $\uparrow$ | DEF $\ge 0.45$ | Share of starts that bank the 2 Defcon pts. |
| **Set-Piece** | **Break-even hit-rate gap** | `breakeven_hit_rate_gap` | $\Delta$ attack xP per start / 2 | Context | DEF $\approx 0.34$ (2025-26) | Extra Defcon hits needed to offset a taker's extra attack xP. |
| **Arrival translation** | **npxG retain ratio** | `ratio_npxg` | PL npxG/90 ÷ source-league npxG/90 | Context (1 = unchanged) | `arrival_xg_xa_summary.csv` `pooled_summer_900` `npxg_median_ratio` | First Premier League season vs prior Big 5 season. Use median; mean is skewed. |
| **Arrival translation** | **xAG retain ratio** | `ratio_xag` | PL xAG/90 ÷ source-league xAG/90 | Context (1 = unchanged) | `arrival_xg_xa_summary.csv` `pooled_summer_900` `xag_median_ratio` | Separate from npxG. Not Opta xA; Understat check is `ratio_xa`. |
