---
idea_id: EXT-08
name: Joint xGI Intensity and Allocation
tier: P1
component: xp_goals
status: untested
replaces: Add coupling correction after inherited MultiFeatureAssistChallengerModel._project_event_components count calculation and before inherited bonus allocation. Cache one factor pair per player/fixture. Preserve active MLComponentChallengerModel.predict Group A/B and all existing finishing parameters. Shared helper must use one causal implementation for training contexts and current prediction contexts; no new implicit archive reads.
grid: "k_mix=2.0; k_mix=4.0; k_mix=8.0; k_mix=16.0"
inputs: "Existing: features.player_id; features.position_id; features.fixture_id; features.gameweek_id; history.player_id; history.gameweek_id; history.minutes; history.expected_goals; history.expected_assists; history.price. Existing helper: positional_price_tier_prior. Derived to implement: derived.weighted_xg; derived.weighted_xa; derived.exposure90; derived.joint_rate_g; derived.joint_rate_a; derived.independent_reference_g; derived.independent_reference_a. Unavailable/not used: event recipient links, shot tags, terminal set-piece orders, future price. Derived names are proposed internal fields, absent from current FeatureContract."
nearest_ledger_row: CSV data rows 10/25/44/85/93; new own-xG/xA joint process intensity-allocation likelihood
spec_path: ideas/EXT-08-joint-xgi-intensity-and-allocation.md
---

# EXT-08: Joint xGI Intensity and Allocation

## 1. Concept & Football Hypothesis

Hypothesis: sustained involvement in scoring opportunities contains information even when small samples leave uncertain whether player primarily shoots or creates. Champion estimates xG and xA through separate shrinkage paths; own xA does not enter its active goals feature list. Joint latent total involvement and goal/assist allocation allow cross-signal learning. No finishing skill inferred from assists or realized goals. Cheap MID/FWD with similar independent xG estimates can differ in sustained total involvement.

   Ledger screen: mechanism-eligible on paper. Nearest shipped mechanism: position-specific scalar xG shrinkage. Nearest locked mechanisms: assist finishing offsets, position FPL-assist conversion, natural rate calibration, multi-feature goals GLM, price-stratified Huber panel. Proposed coupling uses own process xG/xA, separate intensity/allocation likelihood, no realized A/xA conversion, no price residual centering, no early ML.

## 2. Mathematical Formulation

For strictly prior played fixtures, define `e_t = minutes_t/90`, `w_t = 0.95^(cutoff-1-gw_t)`, `G = sum(w_t*xG_t)`, `A = sum(w_t*xA_t)`, `E = sum(w_t*e_t)`. Obtain existing point-in-time positional price-tier process priors `mu_G,mu_A`; set `mu = mu_G+mu_A` and `p0=mu_G/mu`. Use identity correction if `mu=0`.

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

## 3. Decoupled Architecture Placement

`M_events`: `xp_goals`, `xp_assists`. Existing minutes distribution unchanged. Subsequent bonus movement follows inherited scoring/BPS relation.

## 4. Replaces / Integration Hook

Add coupling correction after inherited `MultiFeatureAssistChallengerModel._project_event_components` count calculation and before inherited bonus allocation. Cache one factor pair per player/fixture. Preserve active `MLComponentChallengerModel.predict` Group A/B and all existing finishing parameters. Shared helper must use one causal implementation for training contexts and current prediction contexts; no new implicit archive reads.

## 5. Parameter Sweep Grid

`k_mix=2.0`; `k_mix=4.0`; `k_mix=8.0`; `k_mix=16.0`. All variants: `k_R=12`, correction fraction `0.25`, log-ratio bound `log(1.10)`, cutoff GW20, fixed N_eff thresholds. `k_mix` concentration unit: accumulated process xGI, not minutes.

## 6. Small-Sample & Cold-Start Strategy

Exact inherited fallback before GW20. Missing process records produce identity correction. Warm historical seed remains inside Champion anchor; new pseudo-likelihood uses current-season process history. Prior means use price known at first current-season observation, never terminal `now_cost`. No individual intercept regression or lagged dependent-variable fixed-effects panel, so no proposed within-transformation Nickell-bias correction. Generalized-likelihood calibration remains empirical risk.

## 7. Budget-Constrained Optimizer Interaction

Hypothesis: improve relative ranking of similarly priced attackers by distinguishing sustained involvement from uncertain goal/assist mix. Price supplies existing prior context, never automatic cheap-player boost or point-per-pound score. Bounded new factor limits perturbation but does not guarantee churn or captaincy guardrails. Must evaluate constrained blended XI regret at GBP83.5m, max three/club, plus full/active-window guards and excess churn ceiling 0.50.

## 8. Point-in-Time Feature Requirements

Existing: `features.player_id`; `features.position_id`; `features.fixture_id`; `features.gameweek_id`; `history.player_id`; `history.gameweek_id`; `history.minutes`; `history.expected_goals`; `history.expected_assists`; `history.price`. Existing helper: `positional_price_tier_prior`. Derived to implement: `derived.weighted_xg`; `derived.weighted_xa`; `derived.exposure90`; `derived.joint_rate_g`; `derived.joint_rate_a`; `derived.independent_reference_g`; `derived.independent_reference_a`. Unavailable/not used: event recipient links, shot tags, terminal set-piece orders, future price. Derived names are proposed internal fields, absent from current FeatureContract.

## 9. Python Code Skeleton (Optional)

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

## Intake Provenance & Mechanism Audit

Source: [sol-max-attack-response.md](../sol-max-attack-response.md); GPT-6.1 Sol, Max reasoning, 2026-10-28.

Nearest ledger mechanisms: CSV data rows 10/25/44/85/93; new own-xG/xA joint process intensity-allocation likelihood.

Mechanism decision: Cross-signal derivative must be nonzero; reject parameterization collapsing to independent shrinkage. No realized assist conversion, finishing-offset refit, DEF K relaxation, price residual centering, or early activation. Preserve existing exposure path for isolated event-rate comparison.

Specification only: any autogenerated Python scaffold is incomplete wiring, not an implemented or evaluated model. Source references to shared Candidate 1 mean EXT-07. Dependency completion never authorizes stacking a lever that subsequently receives a dead verdict.

Lexical-screen flag: Assist finishing offsets (goals+assists pooled). Token overlap is not empirical or mechanism equivalence; distinctions above govern paper intake.

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
