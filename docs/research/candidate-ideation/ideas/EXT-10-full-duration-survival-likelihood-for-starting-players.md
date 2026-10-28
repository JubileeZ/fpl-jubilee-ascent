---
idea_id: EXT-10
name: Full-Duration Survival Likelihood for Starting Players
tier: P2
component: xp_minutes
status: untested
replaces: "MLComponentChallengerModel.predict H3 block currently fits target_minutes minus shrunk_mins_if_start, clips start minutes to [60,90], and maps mean to P(60) with a line. Replace that H3 likelihood and moment mapping. build_causal_panel already supplies fixture-level target_minutes and target_starts. New immutable pooled seed hazard summaries belong in build_features seed preparation, explicitly passed as optional numeric features. Shared Candidate 1 replay utility is a prerequisite for assessing full scoring consequences."
grid: "hazard_ridge=50,seed_strength=12; hazard_ridge=200,seed_strength=12; hazard_ridge=50,seed_strength=24; hazard_ridge=200,seed_strength=24"
inputs: "Existing history.minutes; history.starts; history.player_id; history.fixture_id; history.gameweek_id; existing causal-panel shrunk_mins_if_start and early_hook_rate; features.position_id. Proposed derived features: fixed-bin exit counts and at-risk exposures, prior-season position hazard summaries, genuine seed-row count. These are not existing FeatureContract columns. Injury exit reasons, exact substitute identity, player tracking load, and live lineup news are unavailable and unused."
nearest_ledger_row: CSV data rows 19/52/60/64/79/81; full starting-duration censored likelihood, not direct 60+ binary calibration or component mixture
spec_path: ideas/EXT-10-full-duration-survival-likelihood-for-starting-players.md
---

# EXT-10: Full-Duration Survival Likelihood for Starting Players

## 1. Concept & Football Hypothesis

Two starters can share mean playing time while having different probabilities of reaching 60 minutes. Hypothesis: full recorded exit-time information distinguishes reliable budget starters from frequent early exits more efficiently than a clipped linear duration offset. This estimates a complete starting-duration distribution. It does not fit direct Beta-binomial P(60) counts, hidden roles, starter-tenure decay, or state-dependent attack intensity.

## 2. Mathematical Formulation

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

## 3. Decoupled Architecture Placement

M_mins, replacement for H3 conditional starting duration and its mechanically derived p_60_if_start. Indirect event exposure uses the existing decoder. New targets are whole duration histories, not direct fantasy points.

## 4. Replaces / Integration Hook

MLComponentChallengerModel.predict H3 block currently fits target_minutes minus shrunk_mins_if_start, clips start minutes to [60,90], and maps mean to P(60) with a line. Replace that H3 likelihood and moment mapping. build_causal_panel already supplies fixture-level target_minutes and target_starts. New immutable pooled seed hazard summaries belong in build_features seed preparation, explicitly passed as optional numeric features. Shared Candidate 1 replay utility is a prerequisite for assessing full scoring consequences.

## 5. Parameter Sweep Grid

hazard_ridge=50,seed_strength=12; hazard_ridge=200,seed_strength=12; hazard_ridge=50,seed_strength=24; hazard_ridge=200,seed_strength=24

## 6. Small-Sample & Cold-Start Strategy

Fixed bins and few pooled coefficients; shrink to one prior season's position hazard. Retain original Champion when required prior summaries or valid starts are absent. Apply a_g only after GW20. Seed summaries use prior-season position metadata known at that time; no cross-season ID join needed for pooled hazards. Starts with invalid or missing durations are excluded, with coverage reported. Survival likelihood addresses censoring at 90; it cannot identify tactical exits versus injuries from current data.

## 7. Budget-Constrained Optimizer Interaction

Hypothesis: ranks cheap starters by threshold reliability while resisting the selection of a player whose mean is inflated by occasional full matches. Full-history proper likelihood and strong pooled priors limit individual small-sample overreaction. Could still overfit rare early exits; no fixed price uplift or claim that lower minutes MAE guarantees better constrained XI regret.

## 8. Point-in-Time Feature Requirements

Existing history.minutes; history.starts; history.player_id; history.fixture_id; history.gameweek_id; existing causal-panel shrunk_mins_if_start and early_hook_rate; features.position_id. Proposed derived features: fixed-bin exit counts and at-risk exposures, prior-season position hazard summaries, genuine seed-row count. These are not existing FeatureContract columns. Injury exit reasons, exact substitute identity, player tracking load, and live lineup news are unavailable and unused.

## 9. Python Code Skeleton (Auto-Scaffolded)

```python
from __future__ import annotations

from models.adaptive_causal_challenger import AdaptiveCausalChallengerModel


class FullDurationSurvivalLikelihoodForStartingPlayersChallengerModel(AdaptiveCausalChallengerModel):
    """Auto-scaffolded skeleton for Full-Duration Survival Likelihood for Starting Players."""

    def __init__(self, hazard_ridge: float = 50.0, seed_strength: float = 12.0, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.hazard_ridge = float(hazard_ridge)
        self.seed_strength = float(seed_strength)

    def _minutes(self, *args: object, **kwargs: object) -> object:
        # Hook target: MLComponentChallengerModel.predict H3 block currently fits target_minutes minus shrunk_mins_if_start, clips start minutes to [60,90], and maps mean to P(60) with a line. Replace that H3 likelihood and moment mapping. build_causal_panel already supplies fixture-level target_minutes and target_starts. New immutable pooled seed hazard summaries belong in build_features seed preparation, explicitly passed as optional numeric features. Shared Candidate 1 replay utility is a prerequisite for assessing full scoring consequences.
        parent_method = getattr(super(), '_minutes', None)
        if callable(parent_method):
            return parent_method(*args, **kwargs)
        raise NotImplementedError('_minutes mechanism not yet implemented')
```


## Intake Provenance & Mechanism Audit

Source: [sol-max-minutes-response.md](../sol-max-minutes-response.md); GPT-6.1 Sol, Max reasoning, 2026-10-28.

Nearest ledger mechanisms: CSV data rows 19/52/60/64/79/81; full starting-duration censored likelihood, not direct 60+ binary calibration or component mixture.

Mechanism decision: Mean duration and P(60) derived jointly from full survival likelihood. Keep existing event distributions and GW1-19 parity; no Beta-binomial threshold fit or duration compression. Requires EXT-07 decoder prerequisite and explicit immutable seed-hazard summaries. Report incremental evidence against matched decoder-only development arm.

Specification only: any autogenerated Python scaffold is incomplete wiring, not an implemented or evaluated model. Source references to shared Candidate 1 mean EXT-07. Dependency completion never authorizes stacking a lever that subsequently receives a dead verdict.

Lexical-screen flag: Teammate-absence share redistribution (Fraction w of absent players expected club xG share to present teammates; same-pos / outfield; goals / g+a). Token overlap is not empirical or mechanism equivalence; distinctions above govern paper intake.

No empirical attempt; no candidate-ledger verdict. Recheck authoritative ledger before implementation. Preserve confirmation freeze and sealed holdout.

## Shared Source Context

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
