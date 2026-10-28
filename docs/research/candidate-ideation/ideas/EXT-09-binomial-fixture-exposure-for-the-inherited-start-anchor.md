---
idea_id: EXT-09
name: Binomial Fixture Exposure for the Inherited Start Anchor
tier: P1
component: xp_minutes
status: untested
replaces: "Late-only branch around models.learned_start_challenger._panel, _covariates, _fit_logistic, and learned_start_probabilities reached from LearnedStartChallengerModel.predict. _panel adds fixture_count and start_count while retaining started=max and current lag columns. _fit_logistic accepts binomial exposures. target_start_probabilities, blend_states, bonus law, and main ML H1/H3 remain fixed. Candidate-level dispatch must use original inherited anchor for target GW1-19. This is a reachable inherited-anchor change, not a correction to build_causal_panel."
grid: "binomial_fixture_exposure=True"
inputs: "Existing history.player_id; history.fixture_id; history.gameweek_id; history.starts; history.minutes; history.was_home; history.opponent_club_id; features.position_id; features.club_id; features.gameweek_id; features.fixture_id. Proposed derived columns: player-GW fixture_count and start_count, assembled from distinct pre-target fixture rows; immutable seed-row-count metadata. No new external source. Unknown/missing fixture opportunity causes exclusion/fallback, never a manufactured zero."
nearest_ledger_row: CSV data row 52; inherited-anchor observation-unit correction, not position/head/regularization variation
spec_path: ideas/EXT-09-binomial-fixture-exposure-for-the-inherited-start-anchor.md
---

# EXT-09: Binomial Fixture Exposure for the Inherited Start Anchor

## 1. Concept & Football Hypothesis

Starting at least once during a double gameweek and starting an individual fixture are different events. Hypothesis: the inherited anchor's player-GW binary label obscures rotation among budget starters with multiple fixtures. New mechanism changes observation likelihood to account for known fixture opportunities. It retains the shipped estimator, predictors, regularization, activation, and mass handling.

## 2. Mathematical Formulation

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

## 3. Decoupled Architecture Placement

M_mins, inherited p_start anchor and downstream xp_minutes. Event opportunities change through the existing inherited state scorer. Main causal panel targets remain untouched.

## 4. Replaces / Integration Hook

Late-only branch around models.learned_start_challenger._panel, _covariates, _fit_logistic, and learned_start_probabilities reached from LearnedStartChallengerModel.predict. _panel adds fixture_count and start_count while retaining started=max and current lag columns. _fit_logistic accepts binomial exposures. target_start_probabilities, blend_states, bonus law, and main ML H1/H3 remain fixed. Candidate-level dispatch must use original inherited anchor for target GW1-19. This is a reachable inherited-anchor change, not a correction to build_causal_panel.

## 5. Parameter Sweep Grid

binomial_fixture_exposure=True

## 6. Small-Sample & Cold-Start Strategy

Keep lambda=10 and current minimum training support. Warm seed continues through existing builder priors; do not concatenate prior-season integer player IDs into current history. New a_g attenuation requires genuine immutable seed-row-count metadata. No DGWs in training implies F=1 and the binomial fit equals the current binary fit; report an inert proposal rather than adding another adjustment.

## 7. Budget-Constrained Optimizer Interaction

Hypothesis: improves relative start probability among otherwise similarly priced players with irregular fixture opportunities. No uniform nailedness lift or per-club 11-player total. Global mass preservation can partly absorb changes, and main fixture-level H1 may already correct most ranking error. Likely narrow effect; do not infer promotion-sized alpha from label semantics.

## 8. Point-in-Time Feature Requirements

Existing history.player_id; history.fixture_id; history.gameweek_id; history.starts; history.minutes; history.was_home; history.opponent_club_id; features.position_id; features.club_id; features.gameweek_id; features.fixture_id. Proposed derived columns: player-GW fixture_count and start_count, assembled from distinct pre-target fixture rows; immutable seed-row-count metadata. No new external source. Unknown/missing fixture opportunity causes exclusion/fallback, never a manufactured zero.

## 9. Python Code Skeleton (Auto-Scaffolded)

```python
from __future__ import annotations

from models.adaptive_causal_challenger import AdaptiveCausalChallengerModel


class BinomialFixtureExposureForTheInheritedStartAnchorChallengerModel(AdaptiveCausalChallengerModel):
    """Auto-scaffolded skeleton for Binomial Fixture Exposure for the Inherited Start Anchor."""

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        pass

    def _start_challenger(self, *args: object, **kwargs: object) -> object:
        # Hook target: Late-only branch around models.learned_start_challenger._panel, _covariates, _fit_logistic, and learned_start_probabilities reached from LearnedStartChallengerModel.predict. _panel adds fixture_count and start_count while retaining started=max and current lag columns. _fit_logistic accepts binomial exposures. target_start_probabilities, blend_states, bonus law, and main ML H1/H3 remain fixed. Candidate-level dispatch must use original inherited anchor for target GW1-19. This is a reachable inherited-anchor change, not a correction to build_causal_panel.
        parent_method = getattr(super(), '_start_challenger', None)
        if callable(parent_method):
            return parent_method(*args, **kwargs)
        raise NotImplementedError('_start_challenger mechanism not yet implemented')
```


## Intake Provenance & Mechanism Audit

Source: [sol-max-minutes-response.md](../sol-max-minutes-response.md); GPT-6.1 Sol, Max reasoning, 2026-10-28.

Nearest ledger mechanisms: CSV data row 52; inherited-anchor observation-unit correction, not position/head/regularization variation.

Mechanism decision: Group-binomial starts out of known fixture opportunities replaces any-start label only in reachable inherited anchor. Active causal panel already fixture-level. Preserve existing predictors, ridge, mass handling, and GW1-19 behavior. Unknown opportunities cause fallback, never invented DNP rows.

Specification only: any autogenerated Python scaffold is incomplete wiring, not an implemented or evaluated model. Source references to shared Candidate 1 mean EXT-07. Dependency completion never authorizes stacking a lever that subsequently receives a dead verdict.

Lexical-screen flag: Learned participation variants other than shipped learned_start_challenger: ridge-logistic p_start (per-position; +learned p_sub_in / xmins-if-start / club rotation; no / per-club / club×position mass), alone or with soft P(60) bonus eligibility. Token overlap is not empirical or mechanism equivalence; distinctions above govern paper intake.

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
