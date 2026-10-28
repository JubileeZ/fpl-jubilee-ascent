# Sol Max attacking-rate ideation

Date: 2026-10-28. Scope: local code and ledger review; goals, assists, budget-enabler ranking. Status: untested hypotheses. No empirical gains claimed. No model implementation, ingestion, smoke test, backtest, gate run, or queue change.

Three proposals retained. Fewer than requested five to seven: remaining approaches either overlap locked mechanisms or require unavailable inputs. Ranking reflects implementation feasibility and clarity of mechanism, not expected gate performance.

1. Joint xGI intensity and allocation: conjugate calculation; existing history sufficient; clearest algebraic distinction from independent rate shrinkage.
2. Opponent conditional attacking-role allocation: new relative concession signal; coarse FPL positions limit resolution; requires careful schedule-composition control.
3. Sequential attacking-opportunity change detection: new temporal likelihood; existing history sufficient; highest computational and identification risk.

## Verified implementation and evaluation boundary

- Authoritative screen: full `candidate_ledger.csv`, including latest price-stratified Huber/continuous-N_eff failure. No locked lever reopened. Ledger note explicitly permits different mechanism with new form or signal; verdicts below remain paper screens, not empirical admission.
- Development: 2025-26, seed 2024-25. Freeze before single 2024-25 confirmation, seed 2023-24. No ideas or parameters derived from sealed 2026-27 GW6+ outcomes.
- Common fallback: candidate returns exact inherited Champion prediction whenever information cutoff precedes GW20. Gate on information cutoff, not future fixture gameweek inside a multi-GW horizon. All future fixtures use same frozen pre-cutoff history.
- Active Champion code: `AdaptiveCausalChallengerModel.predict` bypasses ML before GW20. Its inherited default weight is already 1 at GW20: `clip((target_gw - 3) / 5, 0, 1)`. No GW20-24 ramp exists in active path. `use_neff_alpha=False` by default; Adaptive does not enable it. Existing activation, heads, and weights remain frozen in these proposals.
- Distinct prior strengths: builder event shrinkage and DEF ratio use 360-minute reference; active ML panel uses 1080 minutes for MID/FWD and 2400 for DEF. These are different code paths. No proposal changes DEF shrinkage or reintroduces club x DEF prior.
- Verified event hook: `MultiFeatureAssistChallengerModel._project_event_components(row, position, expected_minutes, *, clean_sheet_minutes, p_sixty_mins)`. Called separately for start/sub states. Existing `_allocate_bonus` consumes `xbps` after state weighting. `_project_event_components` exists; `_predict_goal_rate` or a ready-made role/pace helper does not.
- Proposed integration: cache correction factors by `(player_id, fixture_id)` in candidate `predict`, then override inherited `_project_event_components`. For event count multipliers `f_G,f_A`, set new expected goals/assists from inherited counts, add corresponding scoring-matrix point differences, and update `xbps` by `24 * delta_goals + 12 * delta_assists` before existing bonus allocation. Existing GW20+ Group A goals and Group B LOO multipliers then run unchanged. This preserves component reconciliation and avoids editing final `projected_points` alone. Implementation must verify this ordering against actual call chain.
- Every correction applies only to MID/FWD. GKP/DEF predictions unchanged except shared fixture bonus allocation resulting from changed attacking counts. No new bonus model, cap, temperature, or eligibility rule.
- Common reliability: new head can use fixed `alpha_g = clip((N_eff - 3500)/4000, 0, 1)` multiplied by `1[cutoff >= 20]`. This attenuates only genuinely new mechanism; no sweep of activation schedule. New heads below fit current-season history only, so set their `N_seed=0`; builder retains warm-seeded Champion anchor. Do not infer raw seed fit rows from `features.has_seed`. Explicit raw seed integration would require additional identity/provenance plumbing and separate leakage audit.
- Novelty checks described below are proposed implementation checks. None executed here.

Sources: [Adaptive](C:/Users/phjenphithak/fpl-jubilee-ascent/models/adaptive_causal_challenger.py:59), [ML weight](C:/Users/phjenphithak/fpl-jubilee-ascent/models/ml_component_challenger.py:200), [goals and assists heads](C:/Users/phjenphithak/fpl-jubilee-ascent/models/ml_component_challenger.py:382), [panel prior constants](C:/Users/phjenphithak/fpl-jubilee-ascent/models/ml_panel_features.py:24), [assist event hook](C:/Users/phjenphithak/fpl-jubilee-ascent/models/multi_feature_assist_challenger.py:203), [bonus allocation](C:/Users/phjenphithak/fpl-jubilee-ascent/models/learned_start_challenger.py:228), [full ledger](C:/Users/phjenphithak/fpl-jubilee-ascent/docs/research/candidate-ledger/candidate_ledger.csv), [Eval canon](C:/Users/phjenphithak/fpl-jubilee-ascent/docs/research/INDEX.md:7).

### Candidate 1: Joint xGI Intensity and Allocation

1. **Concept & Football Hypothesis**: Hypothesis: sustained involvement in scoring opportunities contains information even when small samples leave uncertain whether player primarily shoots or creates. Champion estimates xG and xA through separate shrinkage paths; own xA does not enter its active goals feature list. Joint latent total involvement and goal/assist allocation allow cross-signal learning. No finishing skill inferred from assists or realized goals. Cheap MID/FWD with similar independent xG estimates can differ in sustained total involvement.

   Ledger screen: mechanism-eligible on paper. Nearest shipped mechanism: position-specific scalar xG shrinkage. Nearest locked mechanisms: assist finishing offsets, position FPL-assist conversion, natural rate calibration, multi-feature goals GLM, price-stratified Huber panel. Proposed coupling uses own process xG/xA, separate intensity/allocation likelihood, no realized A/xA conversion, no price residual centering, no early ML.

2. **Mathematical Formulation**: For strictly prior played fixtures, define `e_t = minutes_t/90`, `w_t = 0.95^(cutoff-1-gw_t)`, `G = sum(w_t*xG_t)`, `A = sum(w_t*xA_t)`, `E = sum(w_t*e_t)`. Obtain existing point-in-time positional price-tier process priors `mu_G,mu_A`; set `mu = mu_G+mu_A` and `p0=mu_G/mu`. Use identity correction if `mu=0`.

   Latent total opportunity rate `R` and shooter share `p`:

   $$R\sim\operatorname{Gamma}(k_R\mu,k_R),\qquad p\sim\operatorname{Beta}(k_p p_0,k_p(1-p_0)).$$

   Gamma uses shape/rate parameterization. Fractional process totals enter generalized likelihood

   $$L(R,p)\propto e^{-ER}R^{G+A}p^G(1-p)^A.$$

   This is explicit pseudo-likelihood for continuous xG/xA, not claim that xG values are integer Poisson counts. Posterior means:

   $$q_G=\frac{k_R\mu+G+A}{k_R+E}\frac{k_p p_0+G}{k_p+G+A},\qquad q_A=\frac{k_R\mu+G+A}{k_R+E}\frac{k_p(1-p_0)+A}{k_p+G+A}.$$

   Isolate coupling from ordinary independent shrinkage with

   $$q_G^0=\frac{k_R\mu_G+G}{k_R+E},\qquad q_A^0=\frac{k_R\mu_A+A}{k_R+E}.$$

   Apply `f_e = exp(alpha_g * 0.25 * clip(log(q_e/q_e^0), -log(1.10), log(1.10)))`; zero-denominator or missing-history cases use 1. Fixed `k_R=12` full-match exposures, matching current MID/FWD panel prior scale. Safety constants fixed before dev.

   Algebraic novelty check:

   $$\frac{\partial q_G}{\partial A}=\frac{k_p p_0+G}{k_R+E}\frac{k_p-k_R\mu}{(k_p+G+A)^2}.$$

   Cross-partial vanishes when `k_p=k_R*mu`; entire model then collapses to independent Gamma shrinkage. Do not offer that identity as new lever. Nonzero cross-partial distinguishes retained mechanism from changing scalar K or flattening xG slope.

3. **Decoupled Architecture Placement**: `M_events`: `xp_goals`, `xp_assists`. Existing minutes distribution unchanged. Subsequent bonus movement follows inherited scoring/BPS relation.

4. **Replaces / Integration Hook**: Add coupling correction after inherited `MultiFeatureAssistChallengerModel._project_event_components` count calculation and before inherited bonus allocation. Cache one factor pair per player/fixture. Preserve active `MLComponentChallengerModel.predict` Group A/B and all existing finishing parameters. Shared helper must use one causal implementation for training contexts and current prediction contexts; no new implicit archive reads.

5. **Parameter Sweep Grid**: `k_mix=2.0`; `k_mix=4.0`; `k_mix=8.0`; `k_mix=16.0`. All variants: `k_R=12`, correction fraction `0.25`, log-ratio bound `log(1.10)`, cutoff GW20, fixed N_eff thresholds. `k_mix` concentration unit: accumulated process xGI, not minutes.

6. **Small-Sample & Cold-Start Strategy**: Exact inherited fallback before GW20. Missing process records produce identity correction. Warm historical seed remains inside Champion anchor; new pseudo-likelihood uses current-season process history. Prior means use price known at first current-season observation, never terminal `now_cost`. No individual intercept regression or lagged dependent-variable fixed-effects panel, so no proposed within-transformation Nickell-bias correction. Generalized-likelihood calibration remains empirical risk.

7. **Budget-Constrained Optimizer Interaction**: Hypothesis: improve relative ranking of similarly priced attackers by distinguishing sustained involvement from uncertain goal/assist mix. Price supplies existing prior context, never automatic cheap-player boost or point-per-pound score. Bounded new factor limits perturbation but does not guarantee churn or captaincy guardrails. Must evaluate constrained blended XI regret at GBP83.5m, max three/club, plus full/active-window guards and excess churn ceiling 0.50.

8. **Point-in-Time Feature Requirements**: Existing: `features.player_id`; `features.position_id`; `features.fixture_id`; `features.gameweek_id`; `history.player_id`; `history.gameweek_id`; `history.minutes`; `history.expected_goals`; `history.expected_assists`; `history.price`. Existing helper: `positional_price_tier_prior`. Derived to implement: `derived.weighted_xg`; `derived.weighted_xa`; `derived.exposure90`; `derived.joint_rate_g`; `derived.joint_rate_a`; `derived.independent_reference_g`; `derived.independent_reference_a`. Unavailable/not used: event recipient links, shot tags, terminal set-piece orders, future price. Derived names are proposed internal fields, absent from current FeatureContract.

9. **Python Code Skeleton (Optional)**:

   Specification stub only; inherited prediction unchanged until new causal helper and event hook implemented.

   ```python
   from models.adaptive_causal_challenger import AdaptiveCausalChallengerModel

   class JointXgiAllocationChallengerModel(AdaptiveCausalChallengerModel):
       def __init__(self, k_mix: float = 4.0) -> None:
           super().__init__()
           self.k_mix = float(k_mix)

       @property
       def name(self) -> str:
           return "joint_xgi_allocation_challenger"
   ```

### Candidate 2: Opponent Conditional Attacking Role Allocation

1. **Concept & Football Hypothesis**: Hypothesis: opponents differ in which attacking profiles generate chances against them, beyond total chances conceded. Aggregate opponent xG cannot distinguish concessions to shooting midfielders, creating midfielders, and forwards. FPL positions provide coarse profiles only; no inference about real winger/striker locations. New signal is relative attacking-role concession pattern, conditional on opponents already faced.

   Ledger screen: mechanism-eligible on paper, higher near-match risk than Candidate 1. Nearest locked mechanisms: scalar opponent-relative team Poisson multiplier, true scoreline Poisson, flat MID/FWD goal scales, schedule-adjusted past player xG/xA. New opponent-by-role interaction leaves total attacking expectation fixed, varies across opponents, and adjusts for attacking profiles actually faced. Any implementation reducing to scalar opponent rate or historical xGC deflation is rejected.

2. **Mathematical Formulation**: At every historical deadline, assign MID to shooting/creating profile from pre-deadline shrunk `xG/(xG+xA)`, threshold 0.5; FWD gets third profile. Profile assignment uses prior history only. Let `I_f` be MID/FWD players on attacking side of completed historical fixture. Set `b_if=(minutes_if/90)*r_xG,i,<gw(f)` using causal prior rate; historical target minutes serve exposure, not forecast feature. Fit conditional allocation:

   $$p_{if}(\theta)=\frac{b_{if}\exp(\theta_{o(f),r(i,f)})}{\sum_{j\in I_f}b_{jf}\exp(\theta_{o(f),r(j,f)})}.$$

   Generalized multinomial log-likelihood for fractional process marks:

   $$\widehat\theta=\arg\max_\theta\left\{\sum_{f<g}\sum_{i\in I_f}xG_{if}\log p_{if}(\theta)-\frac{\lambda}{2}\sum_{o,r}\theta_{or}^2\right\},\quad\sum_r\pi_r\theta_{or}=0.$$

   Prior `theta_or ~ Normal(0,1/lambda)` on centered contrast space; `pi_r` equals causal league profile exposure shares. Skip zero-total fixtures and ineligible/missing-offset records. Pre-deadline offsets account for opponent schedule composition; fitting simple raw conceded role shares would confound defensive preference with attackers faced.

   For forecast fixture, let `C_i` be inherited expected goal count and `u_i=exp(alpha_g*theta_opponent,role)`. Apply identity for defenders and goalkeepers. Within attacking club's MID/FWD subset:

   $$C_i'=C_i\frac{u_i}{\sum_jC_ju_j/\sum_jC_j}.$$

   Zero total uses identity. Limit fitted contrasts to `[-log(1.10),log(1.10)]` before forecast normalization; bounds fixed across grid. Thus `sum_i C_i'=sum_i C_i` over MID/FWD. Common scalar `theta_or=a_o` cancels exactly, proving scalar opponent-strength multiplier cannot generate proposal's effect. No `sum p_start=11` constraint; no redistribution of absent player's xG.

3. **Decoupled Architecture Placement**: `M_events`: `xp_goals`. No new assists, minutes, clean-sheet, or bonus head. Existing effects of changed goal counts on BPS follow inherited mechanism.

4. **Replaces / Integration Hook**: Add derived opponent-role contrasts alongside causal panel context. Existing `_reconstruct_club_id` and `_club_fixture_table` provide in-memory club-side pattern; require exactly two identifiable fixture sides. Precompute forecast normalizers by `(fixture_id,club_id)` before event projection. Apply factors in `_project_event_components` using inherited expected goal counts; update scoring points/BPS. For final-MID/FWD total-preservation property, incorporate existing Group A goal multiplier into precomputed counts or apply normalization after Group A and rerun inherited bonus calculation once. Specify one ordering before implementation; do not silently claim pre-Group-A normalization preserves final totals.

5. **Parameter Sweep Grid**: `lambda_role=25.0`; `lambda_role=50.0`; `lambda_role=100.0`. Profile threshold `0.5`, contrast bound `log(1.10)`, cutoff GW20, fixed N_eff thresholds. No matchup shrink or position goal-weight sweep.

6. **Small-Sample & Cold-Start Strategy**: Before GW20, exact inherited predictions. Unseen opponent or missing profile evidence gives zero contrast. New heads use current-season history; warm seed remains in Champion baseline rates. Ridge prior shrinks profile contrasts, not DEF xG rate. Promoted clubs remain near neutral until observed concessions differentiate roles. No player fixed effects; causal rate offsets generated with strictly earlier history. Double-GW matches remain fixture-level observations with one pre-deadline information boundary.

7. **Budget-Constrained Optimizer Interaction**: Hypothesis: within same fixture, low-cost shooting MID can rank differently from expensive FWD where opponent's relative profile pattern differs. Fixed total prevents extra club attacking mass from new feature; no price-driven multiplier. Profile assignment and opponent contrast can still cause switches, so churn remains empirical guardrail. Captaincy risk: reallocating MID/FWD mass can suppress premium forwards; evaluate active-window captaincy regret explicitly. This mechanism is weaker if coarse FPL positions contain little stable matchup information.

8. **Point-in-Time Feature Requirements**: Existing: `features.player_id`; `features.position_id`; `features.club_id`; `features.opponent_id`; `features.fixture_id`; `features.gameweek_id`; `history.player_id`; `history.fixture_id`; `history.gameweek_id`; `history.opponent_club_id`; `history.minutes`; `history.expected_goals`; `history.expected_assists`; `history.was_home`; `history.price`. Derived to implement: `derived.predeadline_profile`; `derived.predeadline_xg_offset`; `derived.opponent_role_contrast`; `derived.club_attacker_normalizer`. Historical positions must come from known season position mapping; no cross-season current-position backfill. Unavailable/not used: shot location, actual wide/central role, marking assignments, possession, bookmaker spread. Do not label shooting/creating bins as observed tactical roles.

9. **Python Code Skeleton (Optional)**:

   ```python
   from models.adaptive_causal_challenger import AdaptiveCausalChallengerModel

   class OpponentRoleAllocationChallengerModel(AdaptiveCausalChallengerModel):
       def __init__(self, lambda_role: float = 50.0) -> None:
           super().__init__()
           self.lambda_role = float(lambda_role)

       @property
       def name(self) -> str:
           return "opponent_role_allocation_challenger"
   ```

### Candidate 3: Sequential Attacking Opportunity Change Detection

1. **Concept & Football Hypothesis**: Hypothesis: persistent attacking-opportunity changes can occur during season, so fixed 0.95 decay sometimes mixes distinct opportunity regimes. Repeated process innovations should support changing memory; isolated realized goals should not. Candidate learns continuous xG/xA intensity change points, never hidden participation roles. Unobserved cause might be tactical responsibility or team context; model cannot identify cause from FPL data.

   Ledger screen: mechanism-eligible on paper, computationally least attractive. Nearest locked mechanisms: latent-role HMM participation, starter-tenure rate decay, goals-path reshaping, natural rate calibration. Difference: continuous event-rate likelihood and data-dependent run-length posterior; no participation transitions, K reduction, global goal scale, xG slope change, or early ML activation. Implementing merely another fixed decay factor would lose novelty and should be rejected.

2. **Mathematical Formulation**: For `e in {xG,xA}`, played fixture exposure `v_t=minutes_t/90`, and `y_t` observed process value, use compound Poisson-Gamma Tweedie likelihood with fixed power `p=1.5`:

   $$y_t\mid\theta_t\sim\operatorname{Tw}_{1.5}\left(v_t e^{\theta_t},\phi v_t^{-0.5}\right).$$

   Mean `v_t*exp(theta_t)`, variance `phi*v_t*exp(1.5*theta_t)`. Supports exact zero and continuous positive process totals. DNP fixtures carry no event-rate observation. Latent continuous log-rate transition:

   $$\theta_t\mid\theta_{t-1}\sim(1-h)\delta_{\theta_{t-1}}+h\operatorname{Normal}\left(\log\mu_{i,t}-\frac{\sigma_0^2}{2},\sigma_0^2\right),\quad\sigma_0^2=0.25.$$

   `mu_i,t` is process prior known before that historical fixture, from existing positional price-tier helper. Constant hazard means prior change probability per played fixture, not preselected change dates. Bayesian filtering updates run-length and rate density using each prior observed `y_t`; deterministic quadrature or bounded run-length recursion required. Use same likelihood with `h=0` as stationary reference, not Champion refit.

   $$q_{e,g}^{CP}=\mathbb E[e^{\theta_g}\mid\mathcal H_{<g}],\qquad q_{e,g}^{0}=\mathbb E[e^{\theta}\mid\mathcal H_{<g},h=0].$$

   Candidate factor `f_e=exp(alpha_g*s_i*0.25*clip(log(q_e^CP/q_e^0),-log(1.10),log(1.10)))`, with fixed `s_i=E_i/(E_i+12)`, `E_i=sum prior played minutes/90`. Zero reference or failed numerical fit gives identity correction. Forecast farther fixtures by integrating reset transition, without inventing future observations; if reset mean remains `mu`, `E[rate at k]=(1-h)^k*q_CP + (1-(1-h)^k)*mu`. Both CP and stationary forecasts use same known inputs.

3. **Decoupled Architecture Placement**: `M_events`: `xp_goals`, `xp_assists`. Fit process-rate filters only. No changes to `p_start`, `p_sub_in`, duration, P(60), or DEF shrinkage.

4. **Replaces / Integration Hook**: New deterministic causal filter helper, fed raw process history from candidate `fit`. Cache ratio to stationary reference in candidate `predict`, then apply common `_project_event_components` correction. Existing `features.builder._weighted_event_totals` identifies fixed-decay baseline, but proposal does not edit that global builder. No existing Tweedie/change-point helper verified; implementation required. Avoid process-global cross-GW mutable memory: reconstruct filter from supplied fit history so independent predictions reproduce identical output.

5. **Parameter Sweep Grid**: `change_hazard=0.0208333333,dispersion=0.5`; `change_hazard=0.0208333333,dispersion=1.0`; `change_hazard=0.0416666667,dispersion=0.5`; `change_hazard=0.0416666667,dispersion=1.0`. Fixed Tweedie power `1.5`, prior log variance `0.25`, attenuation `0.25`, evidence strength `12` exposures, log-ratio bound `log(1.10)`. Both process heads use same grid pair.

6. **Small-Sample & Cold-Start Strategy**: Exact Champion fallback before GW20, including horizon rows crossing GW20. New process likelihood uses only current-season prior fixtures; warm seed remains Champion anchor. At low personal exposure, `s_i` suppresses correction continuously. No resetting prior around current target's future evidence. Price prior at each historical fixture uses preceding recorded price; unavailable initial history starts at existing safe positional prior. No per-player fixed-effect autoregression; posterior uncertainty remains explicit. Tweedie likelihood assumptions and few fixtures per player can still produce false change detections.

7. **Budget-Constrained Optimizer Interaction**: Hypothesis: persistent process-role improvement can distinguish new budget starters from one-fixture hauls without assuming cheap price implies value. No realized-goal spike enters detector. Bounded evidence-weighted factor aims to constrain ranking turnover, but role-break detection can cause sudden switches; churn might be decisive failure. Must compare active-window XI regret, captaincy, MAE, bias, and churn; better process likelihood alone cannot admit mechanism.

8. **Point-in-Time Feature Requirements**: Existing: `features.player_id`; `features.position_id`; `features.fixture_id`; `features.gameweek_id`; `history.player_id`; `history.gameweek_id`; `history.fixture_id`; `history.kickoff_time`; `history.minutes`; `history.expected_goals`; `history.expected_assists`; `history.price`. Derived to implement: `derived.causal_process_prior`; `derived.rate_runlength_posterior`; `derived.stationary_process_reference`; `derived.future_reset_expectation`. Unavailable/not used: tactical role-change labels, training reports, touch maps, shot-type tags, same-target fixture outcomes. No terminal prior reconstruction.

9. **Python Code Skeleton (Optional)**:

   ```python
   from models.adaptive_causal_challenger import AdaptiveCausalChallengerModel

   class AttackChangeDetectionChallengerModel(AdaptiveCausalChallengerModel):
       def __init__(self, change_hazard: float = 1.0 / 48.0, dispersion: float = 1.0) -> None:
           super().__init__()
           self.change_hazard = float(change_hazard)
           self.dispersion = float(dispersion)

       @property
       def name(self) -> str:
           return "attack_change_detection_challenger"
   ```

## Near-matches and unavailable-data ideas excluded

- **Creator co-start / forecast creator-support elasticity**: possible new signal from lagged teammate xA and forecast participation, but generic `Champion rate * exp(beta * support)` remains close to locked learned Poisson/direct residual corrections and personnel/absence multipliers. Actual co-start history indicates shared starting lineup, never actual overlap minutes. Current-target starts unavailable before deadline; cannot use realized lineup as historical deadline feature. A fully specified joint lineup/event likelihood or new pre-deadline support signal could distinguish mechanism; omitted from retained slate pending clearer design.
- **Cost-neutral pairwise event ranking / decision-focused residual learning**: new objective alone does not establish new football mechanism. If output remains price-tier centering or learned correction on same base, overlaps Huber price-stratified panel and direct residual locks. No automatic cheap-player boost proposed. Better constrained evaluation does not reopen failed form.
- **Recipient-specific finishing**: individual pass-to-shot recipient links unavailable. Pooling teammate G-minus-xG reproduces shipped LOO assist finishing; own/position A-to-xA correction matches locked assist offsets/conversion. Excluded.
- **Game pace, possession, transition threat, score-state elasticity**: processed history lacks possession, event timestamps, shot transitions, and bookmaker pre-match spreads. Final scores cannot reconstruct time spent leading/trailing. xG-derived scalar expected margin/tempo would largely repeat opponent-strength/matchup mechanisms. Prompt exemplar names unavailable fields; no fabricated proxies retained.
- **Open-play/set-piece or penalty decomposition**: no verified shot-type/penalty-goal event labels. Terminal set-piece order prohibited. Per-90-only penalty inference already locked; synthetic 0.76 penalty subtraction lacks event evidence. Excluded.
- **Start/sub attack intensity**: explicitly locked position-state rate split. Extra nonlinear shape or new ratio grid would remain retry. Excluded.
- **Higher defender priors from club, creativity boost, lower DEF K**: shipped/locked or direct moratorium breach. Excluded.
- **Early continuous activation, Huber, different clamps**: all retain locked mathematical mechanism despite changed labels. No reopening through new Champion, warm confirmation, or reformed constrained gate.

## Local feature and leakage audit

Existing raw performance fields verified in processor: fixture/GW/player IDs, opponent ID, minutes, starts, price, xG, xA, creativity, threat, and full-time score fields. Existing causal panel reconstructs club ID in memory and builds training row `g` from rows `<g`. Derived fields in candidate manifests do not exist yet. No proposal relies on reading terminal `players.parquet` scoring totals, status, ownership, price momentum, or set-piece orders.

Warm seeding currently belongs to builder; `load_fit_history` returns filtered current-season performance history. Code using boolean `has_seed` as actual count or pretending model has raw seed rows would misstate available evidence. Final historical metadata has residual limitations documented by archive guide; proposals do not use new terminal club strength/FDR inputs.

Sources: [processor fields](C:/Users/phjenphithak/fpl-jubilee-ascent/features/processor.py:140), [terminal-column guard](C:/Users/phjenphithak/fpl-jubilee-ascent/features/builder.py:152), [fit history](C:/Users/phjenphithak/fpl-jubilee-ascent/features/builder.py:222), [event accumulation](C:/Users/phjenphithak/fpl-jubilee-ascent/features/builder.py:532), [causal panel](C:/Users/phjenphithak/fpl-jubilee-ascent/models/ml_panel_features.py:734), [assist features](C:/Users/phjenphithak/fpl-jubilee-ascent/models/multi_feature_assist_challenger.py:111), [goals-path implementation](C:/Users/phjenphithak/fpl-jubilee-ascent/models/goals_path_challenger.py:1), [archive guide](C:/Users/phjenphithak/fpl-jubilee-ascent/docs/testing/archive-testing.md:1).

## Proposed evaluation sequence

Only after parent ledger screen and authorized exploration: frozen mechanisms, at most listed grid variants, causal/leakage checks, Tier 2 Oracle Event Gate, then integrated development gate under same constrained XI/active-window conditions. Existing minutes unchanged, so Oracle improvement must come from new attacking mechanism. No candidate stacking before individual evidence. Freeze surviving candidate before single warm confirmation; retain pooled stratified and all safety bars. No sealed-window inspection for selection or tuning.

Copy QA: PASS, every football mechanism labeled hypothesis; numerical parameters explicitly proposed; hooks/fields sourced from local code; unavailable inputs listed; no empirical gain promised; report-only edit. UI-specific craft checks inapplicable to Markdown specification.
