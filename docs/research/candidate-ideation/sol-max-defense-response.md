# Sol Max defensive candidate ideation

Updated: 2026-10-28 (Asia/Bangkok)

Scope: goalkeeper events, defensive scoring, bonus, cross-component consistency under constrained lineup selection. Local source inspection only. All proposals untested. No empirical backtest, smoke, gate, HTTP ingestion, or queue write performed.

Decision: admit one distinct hypothesis. Other plausible goalkeeper and bonus mechanisms overlap active ledger locks or require unavailable observations. Parent session may merge this hypothesis with its attack/minutes reconstruction proposal; count as one mechanism across components.

## Ranked shortlist

1. Late-state-consistent defensive scoring. Recalculate existing defensive links at participation states already selected by Champion's late ML heads. Preserve event rates, probability links, dispersion, matchup scaling, and GW1-19 fallback. Priority follows concrete code path, not measured accuracy.

No second candidate admitted. Shortlist reflects ledger screening rather than expected effect size.

### Candidate 1: Late-State-Consistent Defensive Scoring

1. **Concept & Football Hypothesis**: Defensive scoring exposure follows minutes spent on pitch. When existing late-season participation heads change start probability or conditional duration, clean-sheet eligibility, goals-conceded deductions, save thresholds, and defensive-contribution thresholds should use those same states. Current `MLComponentChallengerModel.predict` obtains `champ_proj`, changes participation and `projected_minutes`, and recalculates `xp_minutes`; default-disabled defense and bonus heads leave underlying defensive components at original exposure. Hypothesis: propagating existing participation estimates through existing defensive scoring links changes relative values of otherwise similar defenders and goalkeepers. No claim that this improves realized accuracy or promotion metrics.

2. **Mathematical Formulation**: For player-fixture row \(i\), let \(a\in\{\mathrm{start},\mathrm{sub}\}\). Existing pre-ML state tuple \(S_i^0\) contains \((p_{ia}^0,m_{ia}^0,q_{ia}^0)\); existing final late-ML state tuple \(S_i^1\) contains \((p_{ia}^1,m_{ia}^1,q_{ia}^1)\). Here \(q=P(60+\mid a)\). DNP contributes zero. Preserve rates \(r_{Gi}\), \(r_{Si}\), \(r_{Di}\) for goals conceded, saves, and defensive contribution; preserve existing defense multiplier \(d_i\).

   Use exactly current link parameters:

   \[
   \lambda_{Gi}=\max(0.05,r_{Gi}d_i),\qquad
   \lambda_{Gia}^k=\lambda_{Gi}m_{ia}^k/90,
   \]

   \[
   \lambda_{Sia}^k=\mathbf1_{\mathrm{GK}}r_{Si}d_i m_{ia}^k/90,\qquad
   \lambda_{Dia}^k=\max(0,r_{Di}d_i m_{ia}^k/90).
   \]

   For NB mean \(\lambda\), shape \(r\), retain
   \(P(N=n)=\Gamma(n+r)[\Gamma(r)n!]^{-1}(r/(r+\lambda))^r(\lambda/(r+\lambda))^n\).
   For each defensive component, define same state-weighted scoring function already used before ML:

   \[
   F_{\mathrm{CS}}(S_i^k)
   =c_i\sum_a p_{ia}^kq_{ia}^k\exp(-\lambda_{Gia}^k),
   \quad c_i\in\{4,4,1,0\}\text{ for GK, DEF, MID, FWD},
   \]

   \[
   F_{\mathrm{GC}}(S_i^k)
   =-\mathbf1_{\mathrm{GK,DEF}}\sum_a p_{ia}^k
   \sum_{n=0}^{\infty}\lfloor n/2\rfloor
   P_{\mathrm{NB}}(n;\lambda_{Gia}^k,r=3),
   \]

   \[
   F_{\mathrm{saves}}(S_i^k)
   =\mathbf1_{\mathrm{GK}}\sum_a p_{ia}^k
   \sum_{n=0}^{\infty}\lfloor n/3\rfloor
   e^{-\lambda_{Sia}^k}(\lambda_{Sia}^k)^n/n!,
   \]

   \[
   F_{\mathrm{defcon}}(S_i^k)
   =2\mathbf1_{\mathrm{outfield}}\sum_a p_{ia}^k
   P_{\mathrm{NB}}(N\ge T_i;\lambda_{Dia}^k,r_i),
   \]

   with existing \((T_i,r_i)=(10,8.5)\) for DEF and \((12,7.0)\) for MID/FWD. Reuse repository expectation helpers, including their existing truncation behavior, rather than changing numerical tails during this experiment.

   Reconstruction:

   \[
   \widehat y_{ic}^{\mathrm{candidate}}
   =\widehat y_{ic}^{\mathrm{Champion}}
   +\mathbf1_{g_{\mathrm{asof}}\ge20}
   [F_c(S_i^1)-F_c(S_i^0)],
   \quad c\in\{\mathrm{CS,GC,saves,defcon}\}.
   \]

   When baseline defensive output equals \(F_c(S_i^0)\), result equals \(F_c(S_i^1)\). Difference form makes identity behavior explicit and avoids multiplying probabilities after scoring. `xp_clean_sheet` is actual singular column name. `xp_minutes`, `xp_goals`, `xp_assists`, and `xp_bonus` remain inherited in this defensive isolation. Recompute `projected_points` as sum of all `xp_*` columns.

   No new likelihood fit, event prior, shrinkage coefficient, or mixture distribution. Existing finishing, K=2400 DEF xG shrinkage, matchup model, and late ML heads remain inherited.

3. **Decoupled Architecture Placement**: Deterministic edge from \(M_{\mathrm{mins}}\) to \(M_{\mathrm{events}}\). Components: `xp_clean_sheet`, `xp_conceded`, `xp_saves`, `xp_defcon`. Participation estimator unchanged. This proposal concerns propagation of its outputs; fitting defense or bonus heads is outside mechanism.

4. **Replaces / Integration Hook**: Modify assembly in `MLComponentChallengerModel.predict`, after final participation/external-override handling and before final `xp_*` sum. Real implementation seam starts at `out_df = champ_proj.copy()` in `models/ml_component_challenger.py:366`. Reuse `CalibratedMatchupHybridModel._project_event_components` (`models/calibrated_matchup_hybrid.py:33`) for existing links, plus same state mixture as `ParticipationStateHybridModel.predict` (`models/participation_state_hybrid.py:76`). Keep `enable_defense=False` and `enable_bonus=False`; these flags enable different fitted/multiplier mechanisms and must stay disabled.

   `HoldChaseChallengerModel.predict` applies hard-fixture GC adjustment before event projection. Reconstruction must receive that same effective rate frame, including `_apply_hard_fixture_defence`, exactly once. Original `features_df` alone does not contain that inherited adjustment. Do not repeat whole inherited feature transformation on an already transformed frame. Do not apply K=2400 xG adjustment twice when parent consolidates attack reconstruction.

   Preserve row alignment by `(player_id, gameweek_id, fixture_id)`, validate one row per key, and process each double-GW fixture independently before any GW aggregation. Blank fixture sentinel remains zero. Capture original effective state and rate frame during projection; reconstructing it from terminal archive metadata is unnecessary.

5. **Parameter Sweep Grid**: `components=clean_sheet+conceded+saves+defcon,activation=champion_gw20,coefficient=1.0`

   One structural variant. No sweep of shapes, temperatures, exposure priors, matchup strengths, or early-activation dates. Component attribution may later diagnose this single variant on development season; such attributions do not establish separate candidates.

6. **Small-Sample & Cold-Start Strategy**: Return inherited Champion output exactly for all as-of GW1-19 invocations, including multi-GW horizons that cross GW20. Respect inherited insufficient-panel fallback at GW20+; when final states equal original states, correction equals zero. Inherit existing warm Feature Contract seeding and existing causal panel/sample shrinkage. No earlier activation justified by \(N_{\mathrm{eff}}\). If sampling weight documented as \(\alpha_g=\operatorname{clip}((0.5N_{\mathrm{seed}}+N_{<g}-3500)/4000,0,1)\), preserve actual parent's handling rather than creating another ramp. No estimated player fixed effect, so this mechanism introduces no new short-panel Nickell estimation problem.

   Important code boundary: `backtesting/walkforward.py` passes current-season pre-target performance rows to `model.fit`; historical warm seed enters `build_features` separately. Do not claim model-fit history automatically includes 2023-24/2024-25 rows. This mechanism needs only resulting existing rates and states, so no extra seed-history plumbing is necessary.

7. **Budget-Constrained Optimizer Interaction**: Two same-price defenders can currently receive different late participation estimates while retaining defensive points calculated at earlier estimates. Reconstruction would make their defensive comparison depend on final exposure through existing nonlinear links. Same applies to goalkeeper save thresholds and conceded deductions. No price discount or premium penalty is introduced. Correction is zero when states agree, and follows same inherited participation/horizon trajectory when they differ. Those properties limit gratuitous new noise sources; they do not guarantee lower churn or resist every instance of Optimizer's Curse. Require ADR 0064 budget/club constraints and churn guardrail to decide usefulness.

   Covariance-only diversification would not change expected additive scoring under accurate marginal means. Existing Strategic defensive-stack penalty already addresses a separate selection preference. Do not turn this proposal into a variance penalty disguised as projected expected points.

8. **Point-in-Time Feature Requirements**: Existing `features.player_id`; existing `features.gameweek_id`; existing `features.fixture_id`; existing `features.position_id`; existing `features.difficulty`; existing `features.defence_multiplier`; existing `features.per90_goals_conceded`; existing `features.per90_saves`; existing `features.per90_defensive_contribution`; existing `features.xmins_cap`; existing `features.external_xmins` when present; existing `features.is_immediate_next_gw`; existing `features.has_availability_snapshot`; existing operational availability fields under current snapshot policy; existing original/final projection `p_start,p_sub_in,p_dnp,xmins_if_start,xmins_if_sub_in,p_60_if_start,p_60_if_sub_in`; derived addition `original_effective_defensive_state` captured in memory; derived addition `final_effective_defensive_state` captured in memory; derived addition `effective_defence_rate_frame` captured after inherited transformations.

   Existing historical sources, already consumed upstream: pre-deadline `history.player_id`, `history.fixture_id`, `history.gameweek_id`, `history.kickoff_time`, `history.minutes`, `history.starts`, `history.goals_conceded`, `history.saves`, `history.defensive_contribution`. No new persisted feature column or unavailable dataset required. Feature-schema presence does not prove every historical archive contains meaningful defcon observations; retain existing builder behavior and inspect coverage before any future implementation.

9. **Python Code Skeleton (Optional)**: Omitted. Equations and single grid specify mechanism. A stub calling an invented reconstruction helper would conceal unresolved state invariants. Implement only after integration audit below determines whether final states are valid inputs; do not treat constructor-only scaffold as evaluated model.

## Code audit and integration prerequisites

Observed through source reading; no empirical accuracy finding.

- `models/ml_component_challenger.py:224` creates baseline `champ_proj`; lines 245-252 copy original states/durations. Lines 366-378 write changed state columns and `xp_minutes`, while defensive scoring columns stay copied. Optional Group C at line 417 applies save/defcon multipliers rather than rebuilding exposure; Champion disables it. Optional Group D at line 426 fits BPS and reallocates bonus; Champion disables it.
- With Champion's `enable_mins_h2=False`, H1 updates `final_p_start` at line 285, while DNP residual reconciliation appears inside H2 at lines 307-308. Final `(p_dnp,p_start,p_sub_in)` therefore need not sum to one solely from inspected algebra. Before using states as mixture probabilities, check simplex invariants. This report does not introduce a new participation model or choose a new redistribution policy.
- `final_xmins` applies `cap_projected_minutes` at line 346 without rescaling final conditional durations there. Earlier `ParticipationStateHybridModel.predict` rescales durations when cap binds. Use one explicit effective-duration representation so reconstruction agrees with reported minutes. External-xMins and operational hard DNP bypasses must preserve current semantics.
- `features/contracts.py:48` checks required projection columns only. Passing that function does not establish simplex validity, exposure consistency, or expected-point correctness.
- `xp_bonus` remains inherited in defensive isolation. Bonus will therefore still use original expected event utility. This is a stated limit. If parent tests a full graph reconstruction, use unchanged existing synthetic BPS formula, T=6 allocation, and existing eligibility, and screen it as part of same consistency mechanism. Do not enable fitted bonus head or change allocation form.

Proposed deterministic verification before any future smoke:

1. GW1-19 output exactly equals inherited Champion, including horizon crossing GW20.
2. No change in final state yields exact identity on all components.
3. Pure DNP and blank fixture yield zero reconstructed defensive points.
4. One-state 90-minute examples reproduce existing scoring helpers exactly.
5. Final state simplex, nonnegative probabilities, and `projected_minutes = sum(p_state * effective_state_minutes)` agree, including caps and external overrides.
6. Fixture-key permutation preserves per-fixture outputs; double-GW outputs equal sum of separately projected fixtures.
7. `projected_points` equals sum of component columns.

These checks were specified, not executed. Upstream simplex/cap problems should be isolated in a deterministic prerequisite patch and reviewed before interpreting candidate results. Parent should avoid silently combining fresh probability-policy changes with this event-exposure experiment.

## Ledger audit

Read all 93 CSV rows: 83 dead, 10 shipped; no open lever. CSV authoritative; older narrative tables contain superseded gate thresholds. Numbering below refers to data rows, excluding CSV header.

Nearest locks screened:

- Row 64, CS exposure over 60+ starts, locked until 2027-09-29. That changes exposure estimator to historical conditional 60+ mean shrunk toward 85 minutes. Proposed mechanism uses already-selected final minutes with current link; no new CS estimator or exposure prior.
- Rows 24 and 28, post-link CS inflation/CS-GC rescaling, locked until 2027-09-27. Proposed mechanism recomputes unchanged link at changed existing input. No fixed scale, fitted residual uplift, or probability correction.
- Row 62, conceded-count shape, locked until 2027-09-30. Existing NB r=3 retained; no Poisson/NB-shape comparison.
- Rows 71, 79-81, saves volume and defcon dispersion/pressure/hit-rate mechanisms, locked until 2027-09-29 or 2027-09-30. Existing per90 inputs, d multiplier, count distributions, and thresholds retained.
- Rows 52 and 66, learned participation variants/displaced start mass routing, locked until 2027-09-28 and 2027-09-29. Proposal introduces no new participation head, fit, or routing parameter. Simplex invariant issue is prerequisite engineering work; altering substantive mass policy would require separate ledger review.
- Rows 13, 26-27, 38, 54, 59, 65, 77, 84, bonus alternatives, locked through respective 2027 revisit dates. No standalone bonus candidate admitted; original bonus left intact in defensive isolation.
- Rows 88-90, 92-93, ML stacks and early/continuous activation failures. Preserve Champion GW1-19 fallback and existing late schedule. No restart of early activation with different damping.
- Shipped rows 4-5, 7, 58, 91 retained as existing mechanisms. Inheritance does not make them new candidates.
- Row 34, terminal archive inputs, permanently locked. No terminal player totals, availability, ownership, or penalty orders added.

Assessment: provisional new-mechanism screen pass for deterministic propagation of existing states. Ledger contains no explicit stale-exposure reconstruction entry. Parent should consolidate attack/defense propagation under one lever. No evidence-based exception requested, no dead lever reopened, no ledger attempt logged because no experiment performed.

## Rejected ideas

1. Shot-volume times keeper save skill: same mechanism as row 71, including NB variant. Renaming shot volume as pressure or expected shots does not make it new.
2. Opponent possession/block depth adjustment for defcon: current Official contract lacks possession and event locations; pressure proxies from opponent attack/team defense reduce to row 80.
3. Shot-distance or post-shot-xG keeper adjustment: unavailable processed data. `expected_goals_conceded` is not post-shot xG; neither `saves + goals_conceded` nor team xG identifies shot placement, distance, or ball velocity.
4. Learned NB shape, beta-binomial defcon hit rate, 60+ versus early-exit mixtures: rows 79 and 81. Changed K or dispersion grid remains same locked lever.
5. Better CS exposure priors or shared team clean-sheet rates: rows 18, 20, 45, 62, 64 cover GC shrink/pooling/GLM/shape and 60+ exposure. No fallback argument reopens them.
6. Bonus ties from a simulated discrete match/BPS distribution: overlaps correlated Monte-Carlo rank/allocation row 65 and broad row 38 allocation mechanisms. Local notes also lack fully inventoried official BPS coefficients. Do not present synthetic integer utilities as identified official BPS.
7. Bonus quality regression or price-tier residual offsets: fitted BPS utility row 77, residual/expanded BPS row 38, or generic residual correction row 35. Temperature, eligibility, and caps already locked/shipped.
8. Continuous latent defensive-role filter using only existing event counts: no additional identified tactical signal; closely resembles adaptive recency/shrinkage. Insufficient distinction to admit under current brief. Any future proposal needs explicit new observation or state identification beyond a renamed rate smoother.
9. Covariance penalty or posterior-LCB price frontier as xP: changes decision utility rather than expected scoring, duplicates Strategic variance-management purpose, and has no automatic advantage under additive expected-score gate. Requires separately scoped optimizer research if requested.

## Evaluation boundary and risks

Any future implementation develops on 2025-26 with 2024-25 Feature Contract seed. Freeze complete candidate before single 2024-25 confirmation with 2023-24 seed; never tune there. 2026-27 GW6+ remains sealed and supplies no ideation evidence. No such observations read for this report.

Primary future decision metric: Blended Constrained Legal Formation XI Regret, cap GBP83.5m and max three per club. Delta definition: mean Champion regret minus mean Candidate regret; higher preferred, benchmark positive with full gate pass. Bootstrap requirements: development P>=0.75, confirmation P>=0.65, pooled stratified P>=0.85 using non-wrapping L=5 blocks. Keep scaled segment floors and dual full/active-window accuracy, bias, captaincy, minutes, Spearman, and churn guardrails. Churn definition: 15 minus consecutive budget-feasible squad intersection; lower preferred, candidate benchmark no more than Champion+0.50 players/GW. Formula-consistency error definition: absolute reported minutes minus sum of state-weighted effective minutes; lower preferred, ideal zero. Simplex error definition: absolute `(p_dnp+p_start+p_sub_in)-1`; lower preferred, ideal zero. Identity error definition: maximum absolute candidate-versus-Champion component difference when states agree; lower preferred, ideal zero.

Main unknowns: final state invariants; size/direction of new ranking effects; whether inherited baseline errors compensate for stale exposure; bonus still uses original utility; coverage of historical defensive-contribution observations. Structural coherence alone is not evidence of forecasting advantage.

## Sources and reproducibility

Read: `AGENTS.md`; `.agents/skills/antislop/SKILL.md`; `.agents/skills/antislop-copywriting/SKILL.md`; `.agents/skills/ideate-candidate/SKILL.md`; `docs/agents/current-state.md`; active `ROADMAP.md`; status and last five commits; `docs/testing/archive-testing.md`; `docs/research/INDEX.md`; `docs/research/candidate-ledger/candidate-ledger.md`; entire `candidate_ledger.csv`; refreshed `candidate_model_ideation_prompt.md`.

Code evidence: `models/adaptive_causal_challenger.py`; `models/ml_component_challenger.py`; `models/ml_panel_features.py`; `models/def_xg_shrink_challenger.py`; `models/learned_start_challenger.py`; `models/multi_feature_assist_challenger.py`; `models/face_value_challenger.py`; `models/hold_chase_challenger.py`; `models/calibrated_matchup_hybrid.py`; `models/participation_state_hybrid.py`; `models/base.py`; `features/builder.py`; `features/processor.py`; `features/contracts.py`; `backtesting/walkforward.py`; `tests/test_adaptive_causal_challenger.py`; `docs/data_dictionary.md`; historical `bonus-bps-inventory-125.md` as code inventory only.

Agent refresh: reread named code sections and all ledger rows; update source-line references and mechanism screen; preserve untested label until authorized empirical run; write only this companion. Parent owns queue ingestion and durable tracking.

Copy gate PASS: parser-required labels retained; specific code claims point to inspected local sources; no fabricated performance claims; proposal and future verification labeled untested. UI/design checks inapplicable to this text companion.
