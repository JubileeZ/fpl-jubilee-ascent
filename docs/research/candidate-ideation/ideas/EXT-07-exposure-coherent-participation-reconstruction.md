---
idea_id: EXT-07
name: Exposure-Coherent Participation Reconstruction
tier: P1
component: all
status: untested
replaces: "Replace out_df = champ_proj.copy() as event decoder input in MLComponentChallengerModel.predict, after hard DNP/oracle processing and before Group A. Reuse ParticipationStateHybridModel.predict's two calls to _project_event_components and LearnedStartChallengerModel._allocate_bonus. Preserve effective rows produced through DefXgShrinkChallengerModel.predict and MultiFeatureAssistChallengerModel.predict. A direct scorer call on original rows would miss inherited rate adjustments. Requires extracting/capturing prepared rows or controlled state override; constructor-only subclass is insufficient."
grid: "replay_final_states=True"
inputs: "Existing features.player_id; features.fixture_id; features.gameweek_id; features.position_id; features.per90_; features.attack_multiplier; features.defence_multiplier; features.xmins_cap when present; current operational availability/blank/external-minutes fields; existing final state arrays and fitted Group A/B outputs. Proposed derived object: effective prepared event rows and coherent final state record, neither currently an exported feature column. No new football source or terminal metadata."
nearest_ledger_row: CSV data rows 24/28/52/64/66; deterministic state/exposure propagation, not new rate fit, CS scale, P(60) estimator, or bench routing
spec_path: ideas/EXT-07-exposure-coherent-participation-reconstruction.md
---

# EXT-07: Exposure-Coherent Participation Reconstruction

## 1. Concept & Football Hypothesis

A revised probability of starting or playing duration should change all scoring opportunities generated from that participation state. Hypothesis: budget starters are misranked when displayed minutes and scoring exposure diverge. Source shows this mismatch can occur in the late-season path. This proposal introduces a coherent joint distribution and replays existing mathematics; it estimates no new football coefficient. Shared proposal with defense specialist, count once.

## 2. Mathematical Formulation

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

## 3. Decoupled Architecture Placement

Deterministic interface between M_mins and M_events. Touches xp_minutes and event exposure for xp_goals, xp_assists, xp_clean_sheet, xp_conceded, xp_saves, xp_defcon, rare components, and xp_bonus. No new event-rate head.

## 4. Replaces / Integration Hook

Replace out_df = champ_proj.copy() as event decoder input in MLComponentChallengerModel.predict, after hard DNP/oracle processing and before Group A. Reuse ParticipationStateHybridModel.predict's two calls to _project_event_components and LearnedStartChallengerModel._allocate_bonus. Preserve effective rows produced through DefXgShrinkChallengerModel.predict and MultiFeatureAssistChallengerModel.predict. A direct scorer call on original rows would miss inherited rate adjustments. Requires extracting/capturing prepared rows or controlled state override; constructor-only subclass is insufficient.

## 5. Parameter Sweep Grid

replay_final_states=True

## 6. Small-Sample & Cold-Start Strategy

No likelihood, prior, fitted scale, or N_eff retuning. Existing warm-seeded priors and active heads remain frozen. Hard GW1-19 return unchanged. Do not sweep partial reconstruction weights; use one consistent decoder specification.

## 7. Budget-Constrained Optimizer Interaction

Hypothesis: aligns the xMins floor and projected points used to select marginal £4.5m-£5.5m starters. Does not add a price uplift, uncertainty haircut, or custom selection objective. Could reduce some attractive budget projections or increase them; direction is not prescribed. Churn and all gate guardrails still decide.

## 8. Point-in-Time Feature Requirements

Existing features.player_id; features.fixture_id; features.gameweek_id; features.position_id; features.per90_*; features.attack_multiplier; features.defence_multiplier; features.xmins_cap when present; current operational availability/blank/external-minutes fields; existing final state arrays and fitted Group A/B outputs. Proposed derived object: effective prepared event rows and coherent final state record, neither currently an exported feature column. No new football source or terminal metadata.

## 9. Python Code Skeleton (Auto-Scaffolded)

```python
from __future__ import annotations

from models.adaptive_causal_challenger import AdaptiveCausalChallengerModel


class ExposureCoherentParticipationReconstructionChallengerModel(AdaptiveCausalChallengerModel):
    """Auto-scaffolded skeleton for Exposure-Coherent Participation Reconstruction."""

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        pass

    def _df(self, *args: object, **kwargs: object) -> object:
        # Hook target: Replace out_df = champ_proj.copy() as event decoder input in MLComponentChallengerModel.predict, after hard DNP/oracle processing and before Group A. Reuse ParticipationStateHybridModel.predict's two calls to _project_event_components and LearnedStartChallengerModel._allocate_bonus. Preserve effective rows produced through DefXgShrinkChallengerModel.predict and MultiFeatureAssistChallengerModel.predict. A direct scorer call on original rows would miss inherited rate adjustments. Requires extracting/capturing prepared rows or controlled state override; constructor-only subclass is insufficient.
        parent_method = getattr(super(), '_df', None)
        if callable(parent_method):
            return parent_method(*args, **kwargs)
        raise NotImplementedError('_df mechanism not yet implemented')
```


## Intake Provenance & Mechanism Audit

Source: [sol-max-minutes-response.md](../sol-max-minutes-response.md); GPT-6.1 Sol, Max reasoning, 2026-10-28.

Nearest ledger mechanisms: CSV data rows 24/28/52/64/66; deterministic state/exposure propagation, not new rate fit, CS scale, P(60) estimator, or bench routing.

Mechanism decision: Replays existing scorer at coherent final states; retains current rate/link/dispersion parameters and GW1-19 fallback. Simplex/cap checks are deterministic prerequisites. Preserve shipped displacement policy; no new routing parameter. Merge defense specialist proposal into this one lever.

Specification only: any autogenerated Python scaffold is incomplete wiring, not an implemented or evaluated model. Source references to shared Candidate 1 mean EXT-07. Dependency completion never authorizes stacking a lever that subsequently receives a dead verdict.

Lexical-screen flag: CS exposure over 60+ starts (GK and DEF clean-sheet exposure uses as-of player mean start minutes given >=60 minutes; shrunk to 85.0 min with K=4 starts). Token overlap is not empirical or mechanism equivalence; distinctions above govern paper intake.

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
