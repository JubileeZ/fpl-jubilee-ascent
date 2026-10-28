# Candidate ideation response: participation, minutes, budget starters

Updated: 2026-10-28 (+07:00)
Data stamp: local source audit; no historical performance outputs inspected.
Status: four untested hypotheses; shared reconstruction proposal counted once across specialist reports.
Requested perspective: independent quantitative modeler, participation/minutes and budget-starter ranking.
Purpose: supply mechanism-screened dossiers for parent consolidation.
Scope: this report only. No model, queue, ledger, packet, tracking, or data changes.

## Sources and method

Read AGENTS.md; docs/agents/current-state.md; active ROADMAP slice; git status and last five commits; ideate-candidate skill; antislop core and copy guidance; Eval canon; archive-testing guide; Candidate Ledger note and complete candidate_ledger.csv; current ideation prompt. Inspected executable model paths and feature construction. Source arguments below establish code behavior and feasibility; football explanations remain hypotheses.

Primary local sources:

- [Eval canon](C:/Users/phjenphithak/fpl-jubilee-ascent/docs/research/INDEX.md:9).
- [Archive-testing rules](C:/Users/phjenphithak/fpl-jubilee-ascent/docs/testing/archive-testing.md:9).
- [Authoritative ledger](C:/Users/phjenphithak/fpl-jubilee-ascent/docs/research/candidate-ledger/candidate_ledger.csv).
- [Current ideation prompt](C:/Users/phjenphithak/fpl-jubilee-ascent/docs/research/candidate-ideation/candidate_model_ideation_prompt.md).
- [Adaptive activation](C:/Users/phjenphithak/fpl-jubilee-ascent/models/adaptive_causal_challenger.py:29).
- [Late-season estimator and decoder](C:/Users/phjenphithak/fpl-jubilee-ascent/models/ml_component_challenger.py:191).
- [Inherited learned-start anchor](C:/Users/phjenphithak/fpl-jubilee-ascent/models/learned_start_challenger.py:55).
- [Causal panel and actual targets](C:/Users/phjenphithak/fpl-jubilee-ascent/models/ml_panel_features.py:734).
- [Existing scoring function](C:/Users/phjenphithak/fpl-jubilee-ascent/models/calibrated_matchup_hybrid.py:33).
- [Shared reconstruction audit](C:/Users/phjenphithak/fpl-jubilee-ascent/docs/research/candidate-ideation/sol-max-defense-response.md).

### Source findings relevant to feasibility

1. Active causal panel already uses player-fixture targets. build_causal_panel attaches raw fixture minutes and starts to corresponding rows. A proposed correction from GW-summed ML targets to fixture targets would duplicate existing behavior.
2. Inherited learned-start anchor uses a different observation unit. Its _panel groups player-GW rows, takes max(started), sums minutes, then learned_start_probabilities fits that binary response. target_start_probabilities maps one player probability back onto fixture rows and preserves total start mass against FaceValue probabilities. Reachable late-season path: Adaptive.predict -> MLComponent.predict -> DefXgShrink.predict -> LearnedStart.predict -> learned_start_probabilities. ML H1 subsequently preserves mass against that anchor. Candidate 2 concerns this inherited anchor only.
3. MLComponent.predict copies champ_proj, updates participation metadata and xp_minutes, then multiplies pre-existing event components. H1/H3 do not replay the event scorer at final exposure. H1 also changes final_p_start without reconciling final_p_dnp when H2 is disabled. Current ProjectionContract checks column presence, not probability normalization. These are source-audit findings, without claims about empirical effect or prevalence.
4. Actual event column is xp_clean_sheet, singular. Prompt vocabulary xp_clean_sheets refers to the same component. Actual inherited hook is CalibratedMatchupHybridModel._project_event_components.
5. Current default activation uses inherited w_ML = clip((GW-3)/5, 0, 1), already full at GW20. Active constructor leaves use_neff_alpha=False. Parent corrected and regenerated prompt during this review. No proposal depends on the former five-GW late-ramp description.
6. Walk-forward passes seed_processed_dir to build_features. model.fit receives deadline-filtered current-season performances. Prior-season rows are not automatically concatenated into ML fit history. Any new seed-duration summary or genuine seed-row count needs explicit feature plumbing; do not invent an available seed training panel.

### Common experimental boundary

Keep predictions byte-for-byte equal to existing Champion for target GW1-19. Keep existing matchups, DEF K=2400 adjustment, finishing, assists, bonus allocation law, hard DNP, blanks, and external-minutes bypass unless a specified deterministic reconstruction requires their existing decoder to run again.

Develop only on 2025-26 with 2024-25 seed. Freeze selected final Candidate before one 2024-25 confirmation with 2023-24 seed. Never tune on confirmation. 2026-27 GW6+ remains sealed; no outputs from that window used here.

For new estimated corrections, define an additional shrinkage weight:

\[
a_g=\mathbf1(g\ge20)\operatorname{clip}
\left(\frac{N_{\mathrm{in},<g}+0.5N_{\mathrm{seed}}-3500}{7500-3500},0,1\right).
\]

Count genuine rows once. Existing model.fit history supplies current-season rows; proposed immutable seed-summary metadata supplies N_seed. This extra weight attenuates only a new correction after GW20. It does not enable the existing ML stack earlier, alter its current activation, or substitute the hard-coded default seed count for evidence.

Promotion primary remains blended constrained formation XI regret: Champion regret minus Candidate regret, higher is better, ideal positive with required bootstrap bars. Existing churn is 15 minus successive selected-squad overlap, lower is better, allowed mean at most Champion +0.50 players/GW. No component diagnostic replaces the full dual-window gate.

## Findings: structured proposals

### Candidate 1: Exposure-Coherent Participation Reconstruction

1. **Concept & Football Hypothesis**: A revised probability of starting or playing duration should change all scoring opportunities generated from that participation state. Hypothesis: budget starters are misranked when displayed minutes and scoring exposure diverge. Source shows this mismatch can occur in the late-season path. This proposal introduces a coherent joint distribution and replays existing mathematics; it estimates no new football coefficient. Shared proposal with defense specialist, count once.

2. **Mathematical Formulation**:

   Let \(\pi_S^*,\mu_S^*,q_S^*\) denote existing late-head outputs and \(\pi_B^0,\mu_B^0,q_B^0\) existing bench-state outputs. Reconcile state probabilities using the already-shipped displacement convention:

   \[
   \pi_B^*=\min(\pi_B^0,1-\pi_S^*),\qquad
   \pi_D^*=1-\pi_S^*-\pi_B^*.
   \]

   Reduced starting mass goes to DNP, not to a new bench-routing mechanism. Reuse blend_states for this convention. Preserve already-produced global per-GW start mass; introduce no club target or vacancy rule.

   If availability cap C binds, scale conditional durations once by
   \(r=\min(1,C/(\pi_S^*\mu_S^*+\pi_B^*\mu_B^0))\).
   Pass exactly the existing decoder's cap and threshold semantics through one shared state preparation path. Do not claim a cap-derived P(60) is an independently estimated distribution.

   With R_c the unchanged existing state event scorer, define:

   \[
   \widehat{XP}_c=\pi_S^*R_c(r\mu_S^*,q_S^*)+
   \pi_B^*R_c(r\mu_B^0,q_B^0),\quad
   \widehat{XP}_{\min}=\pi_S^*(1+q_S^*)+\pi_B^*(1+q_B^0).
   \]

   Apply current Group A goals and Group B assists multipliers once after reconstruction. Regenerate synthetic BPS and use current P(60)-weighted Plackett-Luce allocation once. Keep all existing rate, dispersion, and temperature constants. Hard DNP and blank imply all state mass on DNP and zero event values; external minutes continue through existing target_to_states.

   Acceptance invariants: finite nonnegative probabilities summing to one; printed minutes equal state expectation after cap; unchanged exposure reproduces existing decoder; points equal component sum; no duplicate bonus allocation or defender xG adjustment.

3. **Decoupled Architecture Placement**: Deterministic interface between M_mins and M_events. Touches xp_minutes and event exposure for xp_goals, xp_assists, xp_clean_sheet, xp_conceded, xp_saves, xp_defcon, rare components, and xp_bonus. No new event-rate head.

4. **Replaces / Integration Hook**: Replace out_df = champ_proj.copy() as event decoder input in MLComponentChallengerModel.predict, after hard DNP/oracle processing and before Group A. Reuse ParticipationStateHybridModel.predict's two calls to _project_event_components and LearnedStartChallengerModel._allocate_bonus. Preserve effective rows produced through DefXgShrinkChallengerModel.predict and MultiFeatureAssistChallengerModel.predict. A direct scorer call on original rows would miss inherited rate adjustments. Requires extracting/capturing prepared rows or controlled state override; constructor-only subclass is insufficient.

5. **Parameter Sweep Grid**: replay_final_states=True

6. **Small-Sample & Cold-Start Strategy**: No likelihood, prior, fitted scale, or N_eff retuning. Existing warm-seeded priors and active heads remain frozen. Hard GW1-19 return unchanged. Do not sweep partial reconstruction weights; use one consistent decoder specification.

7. **Budget-Constrained Optimizer Interaction**: Hypothesis: aligns the xMins floor and projected points used to select marginal £4.5m-£5.5m starters. Does not add a price uplift, uncertainty haircut, or custom selection objective. Could reduce some attractive budget projections or increase them; direction is not prescribed. Churn and all gate guardrails still decide.

8. **Point-in-Time Feature Requirements**: Existing features.player_id; features.fixture_id; features.gameweek_id; features.position_id; features.per90_*; features.attack_multiplier; features.defence_multiplier; features.xmins_cap when present; current operational availability/blank/external-minutes fields; existing final state arrays and fitted Group A/B outputs. Proposed derived object: effective prepared event rows and coherent final state record, neither currently an exported feature column. No new football source or terminal metadata.

9. **Python Code Skeleton (Optional)**: Omitted. Exact monolithic insertion point, inherited scorer hooks, state algebra, and singleton grid specified. Implementation must change decoder behavior; an initializer stub would provide no evidence of correct reconstruction.

### Candidate 2: Binomial Fixture Exposure for the Inherited Start Anchor

1. **Concept & Football Hypothesis**: Starting at least once during a double gameweek and starting an individual fixture are different events. Hypothesis: the inherited anchor's player-GW binary label obscures rotation among budget starters with multiple fixtures. New mechanism changes observation likelihood to account for known fixture opportunities. It retains the shipped estimator, predictors, regularization, activation, and mass handling.

2. **Mathematical Formulation**:

   For player i and completed historical GW r, let \(F_{ir}\) be count of distinct observed player-fixture opportunities and \(K_{ir}\) actual starts, with \(0\le K_{ir}\le F_{ir}\). Preserve current pre-r predictor vector x_ir, including current any-start lag definitions, and fit:

   \[
   K_{ir}\sim\operatorname{Binomial}(F_{ir},p_{ir}),\qquad
   \operatorname{logit}(p_{ir})=\beta_0+x_{ir}^{\top}\beta.
   \]

   \[
   \widehat\beta=\arg\min_\beta
   -\sum_{ir}[K_{ir}\log p_{ir}+(F_{ir}-K_{ir})\log(1-p_{ir})]
   +\frac{10}{2}\|\beta_{\mathrm{nonintercept}}\|_2^2.
   \]

   Equivalent implementation: response K/F and IRLS observation weight F. A grouped-binomial working likelihood does not assert conditional independence of a player's two starts; retain GW-block uncertainty assessment. Preserve current binary any-start fields for lags; do not replace them silently with K/F.

   Use per-fixture p, then existing target_start_probabilities and preserve_mass against the existing FaceValue start total. After GW20 only, attenuate the difference between old and corrected raw anchor probabilities by a_g before existing normalization. Both training outcomes and opportunity counts come from pre-target completed fixture rows. Never infer a missing row is DNP.

   For a toy player with per-fixture p=0.5 and two independent opportunities, P(any start)=0.75 whereas E(starts)=1. This arithmetic illustrates distinct labels; existing global mass preservation means it is not an empirical estimate of net squad inflation.

3. **Decoupled Architecture Placement**: M_mins, inherited p_start anchor and downstream xp_minutes. Event opportunities change through the existing inherited state scorer. Main causal panel targets remain untouched.

4. **Replaces / Integration Hook**: Late-only branch around models.learned_start_challenger._panel, _covariates, _fit_logistic, and learned_start_probabilities reached from LearnedStartChallengerModel.predict. _panel adds fixture_count and start_count while retaining started=max and current lag columns. _fit_logistic accepts binomial exposures. target_start_probabilities, blend_states, bonus law, and main ML H1/H3 remain fixed. Candidate-level dispatch must use original inherited anchor for target GW1-19. This is a reachable inherited-anchor change, not a correction to build_causal_panel.

5. **Parameter Sweep Grid**: binomial_fixture_exposure=True

6. **Small-Sample & Cold-Start Strategy**: Keep lambda=10 and current minimum training support. Warm seed continues through existing builder priors; do not concatenate prior-season integer player IDs into current history. New a_g attenuation requires genuine immutable seed-row-count metadata. No DGWs in training implies F=1 and the binomial fit equals the current binary fit; report an inert proposal rather than adding another adjustment.

7. **Budget-Constrained Optimizer Interaction**: Hypothesis: improves relative start probability among otherwise similarly priced players with irregular fixture opportunities. No uniform nailedness lift or per-club 11-player total. Global mass preservation can partly absorb changes, and main fixture-level H1 may already correct most ranking error. Likely narrow effect; do not infer promotion-sized alpha from label semantics.

8. **Point-in-Time Feature Requirements**: Existing history.player_id; history.fixture_id; history.gameweek_id; history.starts; history.minutes; history.was_home; history.opponent_club_id; features.position_id; features.club_id; features.gameweek_id; features.fixture_id. Proposed derived columns: player-GW fixture_count and start_count, assembled from distinct pre-target fixture rows; immutable seed-row-count metadata. No new external source. Unknown/missing fixture opportunity causes exclusion/fallback, never a manufactured zero.

9. **Python Code Skeleton (Optional)**: Omitted. Requires a late-only anchor implementation or dependency injection into inherited prediction. A subclass that changes the active causal panel alone would target the wrong code path.

### Candidate 3: Full-Duration Survival Likelihood for Starting Players

1. **Concept & Football Hypothesis**: Two starters can share mean playing time while having different probabilities of reaching 60 minutes. Hypothesis: full recorded exit-time information distinguishes reliable budget starters from frequent early exits more efficiently than a clipped linear duration offset. This estimates a complete starting-duration distribution. It does not fit direct Beta-binomial P(60) counts, hidden roles, starter-tenure decay, or state-dependent attack intensity.

2. **Mathematical Formulation**:

   Let T be recorded minutes for a started fixture, on support 1 through 90. Treat recorded 90 as administrative survival to match end. All earlier exits count as exits regardless of unobserved reason; do not invent injury/substitution labels.

   Piecewise constant per-minute exit hazard h_i,k over fixed intervals 1-30, 31-44, 45-59, 60-74, 75-84, and 85-89:

   \[
   \operatorname{logit}(h_{i,k})
   =a^0_{\mathrm{pos}(i),k}+u_k+z_i^\top\beta.
   \]

   Here z contains pre-deadline shrunk mean-start minutes and early-hook features, standardized on training history only. No player fixed effects or new lagged dependent variable in a within-player estimator.

   For an exit at T<90:

   \[
   \ell_i=\log h_{i,k(T)}
   +\sum_{t=1}^{T-1}\log(1-h_{i,k(t)}).
   \]

   For T=90, use only survival terms through minute 89. Anchor a0 to prior-season pooled position exit exposures, with smoothing
   \(h^0_{p,k}=(D^{\rm seed}_{p,k}+1/2)/(R^{\rm seed}_{p,k}+1)\).
   D is exit count; R is at-risk minute exposure, both known before current season. Apply zero-mean Gaussian priors to beta and deviations u. Minimize summed negative log likelihood plus
   \(\lambda\|\beta\|^2/2+\kappa\|u\|^2/2\).

   \[
   S_i(t)=P(T\ge t)=\prod_{v=1}^{t-1}(1-h_{i,k(v)}),\quad
   \mu_{S,i}=\sum_{t=1}^{90}S_i(t),\quad q_{S,i}=S_i(60).
   \]

   Apply a_g and existing horizon decay to the difference from current H3 mean and P(60). State probabilities and sub-in distribution remain unchanged. Rebuild scorer inputs with these two moments using the shared reconstruction interface; do not introduce new defcon mixtures or conditional CS-exposure estimators.

3. **Decoupled Architecture Placement**: M_mins, replacement for H3 conditional starting duration and its mechanically derived p_60_if_start. Indirect event exposure uses the existing decoder. New targets are whole duration histories, not direct fantasy points.

4. **Replaces / Integration Hook**: MLComponentChallengerModel.predict H3 block currently fits target_minutes minus shrunk_mins_if_start, clips start minutes to [60,90], and maps mean to P(60) with a line. Replace that H3 likelihood and moment mapping. build_causal_panel already supplies fixture-level target_minutes and target_starts. New immutable pooled seed hazard summaries belong in build_features seed preparation, explicitly passed as optional numeric features. Shared Candidate 1 replay utility is a prerequisite for assessing full scoring consequences.

5. **Parameter Sweep Grid**: hazard_ridge=50,seed_strength=12; hazard_ridge=200,seed_strength=12; hazard_ridge=50,seed_strength=24; hazard_ridge=200,seed_strength=24

6. **Small-Sample & Cold-Start Strategy**: Fixed bins and few pooled coefficients; shrink to one prior season's position hazard. Retain original Champion when required prior summaries or valid starts are absent. Apply a_g only after GW20. Seed summaries use prior-season position metadata known at that time; no cross-season ID join needed for pooled hazards. Starts with invalid or missing durations are excluded, with coverage reported. Survival likelihood addresses censoring at 90; it cannot identify tactical exits versus injuries from current data.

7. **Budget-Constrained Optimizer Interaction**: Hypothesis: ranks cheap starters by threshold reliability while resisting the selection of a player whose mean is inflated by occasional full matches. Full-history proper likelihood and strong pooled priors limit individual small-sample overreaction. Could still overfit rare early exits; no fixed price uplift or claim that lower minutes MAE guarantees better constrained XI regret.

8. **Point-in-Time Feature Requirements**: Existing history.minutes; history.starts; history.player_id; history.fixture_id; history.gameweek_id; existing causal-panel shrunk_mins_if_start and early_hook_rate; features.position_id. Proposed derived features: fixed-bin exit counts and at-risk exposures, prior-season position hazard summaries, genuine seed-row count. These are not existing FeatureContract columns. Injury exit reasons, exact substitute identity, player tracking load, and live lineup news are unavailable and unused.

9. **Python Code Skeleton (Optional)**: Omitted. Requires an explicit duration-likelihood implementation and seed-summary feature plumbing. Develop decoder-only and decoder-plus-survival arms separately; only attribute incremental improvement over the common decoder baseline to this mechanism.

### Candidate 4: Habit-Adjusted Cumulative Playing Dose

1. **Concept & Football Hypothesis**: Rotation decisions may respond to accumulated played minutes relative to a player's usual workload, rather than elapsed time since the last listed fixture. Hypothesis: two players on the same turnaround differ when one played several recent full matches and the other had little actual playing time. Current panel's rest_days uses the last recorded row, including rows with zero minutes; short_turnaround is binary. New signal is cumulative played-minute dose relative to a player's own prior exposure distribution.

2. **Mathematical Formulation**:

   At deadline d_g and scheduled kickoff t, use only observed performances in H_<g:

   \[
   L_i(t;\tau)=\sum_{r\in H_{<g}}\frac{m_{ir}}{90}
   \exp\left(-\frac{t-t_{ir}}{\tau}\right).
   \]

   Zero-minute rows add zero. Build the player's habitual dose Q_i as the 75th percentile of historical pre-deadline doses evaluated at earlier scheduled kickoffs, each recomputed using only information available at that earlier deadline. Shrink Q_i toward a position-pooled quantile with 12 prior observations. Fix

   \[
   D_i(t)=\min(1,\max(0,L_i(t;\tau)-Q_i)).
   \]

   For later known fixtures in the forecast horizon, add expected dose from intervening scheduled fixtures using frozen Champion expected minutes, never future realized minutes. Apply the identical pre-deadline forecast construction to historical training rows.

   Let p0_ir be an expanding, frozen Champion prequential start probability. Fit a bounded nonnegative positional slope through

   \[
   Y_{ir}\sim\operatorname{Bernoulli}
   \left(\sigma(\operatorname{logit}(p^0_{ir})-\beta_{p(i)}D_i(t_{ir}))\right),
   \quad 0\le\beta_p\le0.25,
   \]

   with zero-centered Gaussian shrinkage \(\lambda\sum_p\beta_p^2/2\), zero additional intercept, and proper Bernoulli log likelihood. At inference multiply only the incremental offset by a_g and existing horizon decay. Reuse shipped global mass normalization and blend_states. No club sum target, DNP return ramp, or per-player fitted stamina parameter.

3. **Decoupled Architecture Placement**: M_mins, a new played-load covariate and anchored participation correction. xp_minutes and event exposure flow through the existing scorer. No goal/assist/defcon changes.

4. **Replaces / Integration Hook**: Add a pure, pre-deadline workload builder alongside models.ml_panel_features._build_gw_panel; apply the incremental learned offset inside MLComponentChallengerModel.predict H1 before its existing preserve_mass loop. Keep current H1 covariates and weights fixed. The new offset consumes causal Champion prediction caches for earlier training rows; those offsets are proposed derived inputs, not present in train_panel today. This requires a controlled H1 hook or an extracted helper, not enable_congestion=True.

5. **Parameter Sweep Grid**: recovery_days=2,hazard_ridge=100; recovery_days=4,hazard_ridge=100; recovery_days=2,hazard_ridge=400; recovery_days=4,hazard_ridge=400

6. **Small-Sample & Cold-Start Strategy**: Hard GW1-19 fallback; a_g shrinkage afterwards. Habit quantile shrinks with K=12; slope prior centers at zero; no player fixed effects and no personal slope estimated from a short season. Warm seed may initialize position-level habit summaries after explicit immutable summary plumbing. Current-season history drives incremental exposure. Missing/invalid timestamps cause original-Champion fallback, not a synthetic short-rest flag.

7. **Budget-Constrained Optimizer Interaction**: Hypothesis: avoids overvaluing a cheap player whose recent starts reflect exceptional temporary load while leaving players near their own normal exposure close to anchor. No automatic reward for playing infrequently. Smooth dose and bounded regularized slope should be tested for churn, never assumed to satisfy it. Important risk: unobserved cup/international workload makes this only a Premier League load proxy; it may add no information beyond current history features.

8. **Point-in-Time Feature Requirements**: Existing history.player_id; history.fixture_id; history.gameweek_id; history.minutes; history.starts; history.kickoff_time; features.kickoff_time; features.position_id; current fixture schedule known at deadline. Proposed derived features: actual-playing-dose kernel; shrunk habitual-dose quantile; frozen Champion prequential p_start and horizon expected-minutes cache; genuine seed-row count. No existing features.fatigue, external recovery data, cup minutes, international minutes, injury news, or physiological measurements assumed.

   Historical schedule provenance prerequisite: final archive fixture dates alone do not establish dates known at each historical deadline. Without deadline-valid schedule evidence, defer this version or specify a separate deadline-only dose formulation before experimentation. No future realized minutes or rescheduled kickoff information may enter historical predictors.

9. **Python Code Skeleton (Optional)**: Omitted. Estimator requires the stated prequential offset cache and timestamp audit. A rest_days transform alone is insufficient and would fail the ledger screen as a renamed schedule-congestion lever.

## Decision and ledger audit

Priority: Candidate 1 first, Candidate 2 second, Candidate 3 third, Candidate 4 fourth. Candidate 1 overlaps defense specialist's sole admitted proposal. Candidate 2 is narrow and may be nearly inert after inherited mass normalization and active H1. Candidate 3 offers the clearest genuinely new duration likelihood but has more implementation and sample-risk cost. Candidate 4 has the weakest observable football signal because non-PL workload is absent.

Screened complete ledger by mechanism, including all shipped and active dead rows. No reuse of shipped face-value weights, goal-finishing K, learned-start mass preservation, positional xG shrink, assist GLM, calibrated matchups, or Adaptive late activation as purported new alpha. They remain fixed foundations.

Nearest locked mechanisms and separation conditions:

- Candidate 1 versus direct residual correction, goals reshaping, post-link CS/GC tuning, bonus calibration, and defcon mixtures: decoder replay changes exposure inputs with identical fitted rates and laws. It contains no learned outcome residual, new dispersion, CS-only scale, or bonus parameter. If implementation adds such a term, reject it.
- Candidate 1 versus displaced-start-to-bench: reduced start mass continues to DNP under shipped blend_states; no new routing fraction. Simplex reconciliation is a shared distribution invariant, not another candidate.
- Candidate 2 versus learned participation variants: response is fixture-opportunity Binomial rather than any-start Bernoulli. No new position fit, sub-in head, duration regression, club normalization, or bonus eligibility variant. If implementation only changes regularization or predictor weights, reject it.
- Candidate 3 versus direct Beta-binomial P(60), old learned xmins, HMM, CS exposure, and defcon duration mixtures: full observed duration likelihood with end-of-match censoring; P(60) and mean derived jointly from survival. No direct binary 60+ fit, latent role state, duration compression target, CS-only conditional exposure, or defcon mixture parameter.
- Candidate 4 versus fixed congestion shift: cumulative actual minute dose and habit-relative excess are indispensable new signals. No last-fixture threshold rule, fixed negative shift, or personal short-season stamina regression. If reduced to a rest-days curve or altered threshold/shift, reject it.
- Candidates 2-4 versus Price-Stratified Huber Continuous-N_eff panel, Bounded/Apex/early-Mins-LOO variants: no price centering, Huber duration, early activation, early goals clamp, or schedule-shift stack. First half remains exactly Champion. The latest continuous early-activation family remains locked through 2027-10-26.
- Other screened event, keeper, rare-event, and structural levers remain untouched: no finishing-pool retune, G/A refit, state attack intensity, assist conversion/share/finishing refit, venue/schedule rate adjustment, raw opponent multiplier, goalie slot/SoT model, rare-event/card pooling, BPS fitting/saturation/temperature, or candidate ensemble.

Rejected mechanisms:

- Fixture-level target correction for the active causal ML panel: already implemented.
- Price-stratified Huber loss plus continuous early ML activation: dead through 2027-10-26.
- New per-position Ridge participation fits, learned sub-in, return/DNP ramps, nailed-starter lift, and incumbent-return transfer of start mass: active dead matches.
- Rest-days spline or shifted short-turnaround threshold alone: same congestion lever; not Candidate 4.
- Budget price-bin uplift, direct points residual haircut, or price re-centering: insufficient novel signal; potential overlap with dead residual and Huber mechanisms.
- Direct 60+ Beta-binomial recalibration: active dead match; not Candidate 3.
- Inferred substitute-pair networks from aggregate minutes: true replacement events unavailable; insufficiently identified.
- Posterior-risk deductions presented as expected points: changes utility semantics without a validated expected-score mechanism.
- Possession, bookmaker margins, tracking fatigue, exact injury-exit labels: unavailable in inspected point-in-time contract; no invented columns.
- More than four slate entries: would duplicate mechanisms or lower the novelty bar.

## Risks and unknowns

All football mechanisms untested. No candidate has passed smoke, Tier 1, Tier 2, development, confirmation, or promotion. Source audit does not establish effect size or occurrence frequency.

Shared reconstruction changes several components deterministically; separate that correction from estimated duration/load hypotheses. Use matched development arms to identify incremental effect. Freeze final composition before the single confirmation run.

No external HTTP calls, empirical backtests, holdout reads, queue/ledger writes, or commits. Only this authorized report file created.

## Agent prompt

Consolidate shared reconstruction once. Recheck admission boundaries against authoritative ledger before implementation. If proceeding, reproduce state/exposure audit using synthetic fixtures; preserve operational hard DNP, oracle, caps, blanks, inherited prepared rates, and exact GW1-19 parity. Log empirical attempts only when experimentation begins. Use existing Eval canon and unmodified promotion gate.

## Delivery checks

PASS: all four dossiers use exact nine-section format; each grid has one or four variants.
PASS: existing, proposed-derived, and unavailable feature inputs distinguished.
PASS: every football gain remains a labeled hypothesis; no fabricated experiment result.
PASS: source pointers name executable hooks; wrong active-panel target correction explicitly rejected.
PASS: ledger locks, confirmation freeze, and sealed holdout retained.
PASS: prose contains no em dash; no UI or interactive artifact introduced.
