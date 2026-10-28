---
idea_id: EXT-12
name: Sequential Attacking Opportunity Change Detection
tier: P2
component: xp_goals
status: untested
replaces: "New deterministic causal filter helper, fed raw process history from candidate fit. Cache ratio to stationary reference in candidate predict, then apply common _project_event_components correction. Existing features.builder._weighted_event_totals identifies fixed-decay baseline, but proposal does not edit that global builder. No existing Tweedie/change-point helper verified; implementation required. Avoid process-global cross-GW mutable memory: reconstruct filter from supplied fit history so independent predictions reproduce identical output."
grid: "change_hazard=0.0208333333,dispersion=0.5; change_hazard=0.0208333333,dispersion=1.0; change_hazard=0.0416666667,dispersion=0.5; change_hazard=0.0416666667,dispersion=1.0"
inputs: "Existing: features.player_id; features.position_id; features.fixture_id; features.gameweek_id; history.player_id; history.gameweek_id; history.fixture_id; history.kickoff_time; history.minutes; history.expected_goals; history.expected_assists; history.price. Derived to implement: derived.causal_process_prior; derived.rate_runlength_posterior; derived.stationary_process_reference; derived.future_reset_expectation. Unavailable/not used: tactical role-change labels, training reports, touch maps, shot-type tags, same-target fixture outcomes. No terminal prior reconstruction."
nearest_ledger_row: CSV data rows 25/78/85/86; continuous process-rate change likelihood, not participation HMM or fixed recency retune
spec_path: ideas/EXT-12-sequential-attacking-opportunity-change-detection.md
---

# EXT-12: Sequential Attacking Opportunity Change Detection

## 1. Concept & Football Hypothesis

Hypothesis: persistent attacking-opportunity changes can occur during season, so fixed 0.95 decay sometimes mixes distinct opportunity regimes. Repeated process innovations should support changing memory; isolated realized goals should not. Candidate learns continuous xG/xA intensity change points, never hidden participation roles. Unobserved cause might be tactical responsibility or team context; model cannot identify cause from FPL data.

   Ledger screen: mechanism-eligible on paper, computationally least attractive. Nearest locked mechanisms: latent-role HMM participation, starter-tenure rate decay, goals-path reshaping, natural rate calibration. Difference: continuous event-rate likelihood and data-dependent run-length posterior; no participation transitions, K reduction, global goal scale, xG slope change, or early ML activation. Implementing merely another fixed decay factor would lose novelty and should be rejected.

## 2. Mathematical Formulation

For `e in {xG,xA}`, played fixture exposure `v_t=minutes_t/90`, and `y_t` observed process value, use compound Poisson-Gamma Tweedie likelihood with fixed power `p=1.5`:

   $$y_t\mid\theta_t\sim\operatorname{Tw}_{1.5}\left(v_t e^{\theta_t},\phi v_t^{-0.5}\right).$$

   Mean `v_t*exp(theta_t)`, variance `phi*v_t*exp(1.5*theta_t)`. Supports exact zero and continuous positive process totals. DNP fixtures carry no event-rate observation. Latent continuous log-rate transition:

   $$\theta_t\mid\theta_{t-1}\sim(1-h)\delta_{\theta_{t-1}}+h\operatorname{Normal}\left(\log\mu_{i,t}-\frac{\sigma_0^2}{2},\sigma_0^2\right),\quad\sigma_0^2=0.25.$$

   `mu_i,t` is process prior known before that historical fixture, from existing positional price-tier helper. Constant hazard means prior change probability per played fixture, not preselected change dates. Bayesian filtering updates run-length and rate density using each prior observed `y_t`; deterministic quadrature or bounded run-length recursion required. Use same likelihood with `h=0` as stationary reference, not Champion refit.

   $$q_{e,g}^{CP}=\mathbb E[e^{\theta_g}\mid\mathcal H_{<g}],\qquad q_{e,g}^{0}=\mathbb E[e^{\theta}\mid\mathcal H_{<g},h=0].$$

   Candidate factor `f_e=exp(alpha_g*s_i*0.25*clip(log(q_e^CP/q_e^0),-log(1.10),log(1.10)))`, with fixed `s_i=E_i/(E_i+12)`, `E_i=sum prior played minutes/90`. Zero reference or failed numerical fit gives identity correction. Forecast farther fixtures by integrating reset transition, without inventing future observations; if reset mean remains `mu`, `E[rate at k]=(1-h)^k*q_CP + (1-(1-h)^k)*mu`. Both CP and stationary forecasts use same known inputs.

## 3. Decoupled Architecture Placement

`M_events`: `xp_goals`, `xp_assists`. Fit process-rate filters only. No changes to `p_start`, `p_sub_in`, duration, P(60), or DEF shrinkage.

## 4. Replaces / Integration Hook

New deterministic causal filter helper, fed raw process history from candidate `fit`. Cache ratio to stationary reference in candidate `predict`, then apply common `_project_event_components` correction. Existing `features.builder._weighted_event_totals` identifies fixed-decay baseline, but proposal does not edit that global builder. No existing Tweedie/change-point helper verified; implementation required. Avoid process-global cross-GW mutable memory: reconstruct filter from supplied fit history so independent predictions reproduce identical output.

## 5. Parameter Sweep Grid

`change_hazard=0.0208333333,dispersion=0.5`; `change_hazard=0.0208333333,dispersion=1.0`; `change_hazard=0.0416666667,dispersion=0.5`; `change_hazard=0.0416666667,dispersion=1.0`. Fixed Tweedie power `1.5`, prior log variance `0.25`, attenuation `0.25`, evidence strength `12` exposures, log-ratio bound `log(1.10)`. Both process heads use same grid pair.

## 6. Small-Sample & Cold-Start Strategy

Exact Champion fallback before GW20, including horizon rows crossing GW20. New process likelihood uses only current-season prior fixtures; warm seed remains Champion anchor. At low personal exposure, `s_i` suppresses correction continuously. No resetting prior around current target's future evidence. Price prior at each historical fixture uses preceding recorded price; unavailable initial history starts at existing safe positional prior. No per-player fixed-effect autoregression; posterior uncertainty remains explicit. Tweedie likelihood assumptions and few fixtures per player can still produce false change detections.

## 7. Budget-Constrained Optimizer Interaction

Hypothesis: persistent process-role improvement can distinguish new budget starters from one-fixture hauls without assuming cheap price implies value. No realized-goal spike enters detector. Bounded evidence-weighted factor aims to constrain ranking turnover, but role-break detection can cause sudden switches; churn might be decisive failure. Must compare active-window XI regret, captaincy, MAE, bias, and churn; better process likelihood alone cannot admit mechanism.

## 8. Point-in-Time Feature Requirements

Existing: `features.player_id`; `features.position_id`; `features.fixture_id`; `features.gameweek_id`; `history.player_id`; `history.gameweek_id`; `history.fixture_id`; `history.kickoff_time`; `history.minutes`; `history.expected_goals`; `history.expected_assists`; `history.price`. Derived to implement: `derived.causal_process_prior`; `derived.rate_runlength_posterior`; `derived.stationary_process_reference`; `derived.future_reset_expectation`. Unavailable/not used: tactical role-change labels, training reports, touch maps, shot-type tags, same-target fixture outcomes. No terminal prior reconstruction.

## 9. Python Code Skeleton (Optional)

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

## Intake Provenance & Mechanism Audit

Source: [sol-max-attack-response.md](../sol-max-attack-response.md); GPT-6.1 Sol, Max reasoning, 2026-10-28.

Nearest ledger mechanisms: CSV data rows 25/78/85/86; continuous process-rate change likelihood, not participation HMM or fixed recency retune.

Mechanism decision: Maintain data-dependent run-length posterior for xG/xA with stated likelihood and stationary reference. A different fixed decay or K is not this mechanism. No participation role HMM, starter-tenure shrinkage reset, slope flattening, or early ML activation. Numerical failures fall back to identity.

Specification only: any autogenerated Python scaffold is incomplete wiring, not an implemented or evaluated model. Source references to shared Candidate 1 mean EXT-07. Dependency completion never authorizes stacking a lever that subsequently receives a dead verdict.

Lexical-screen flag: Latent-role HMM participation modeling (3-4 hidden roles with EM transitions; replace or 50-50 blend with logistic model). Token overlap is not empirical or mechanism equivalence; distinctions above govern paper intake.

No empirical attempt; no candidate-ledger verdict. Recheck authoritative ledger before implementation. Preserve confirmation freeze and sealed holdout.

## Shared Source Context

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
