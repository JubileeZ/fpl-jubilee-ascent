---
idea_id: EXT-13
name: Habit-Adjusted Cumulative Playing Dose
tier: P3
component: xp_minutes
status: blocked (historical schedule provenance)
replaces: "Add a pure, pre-deadline workload builder alongside models.ml_panel_features._build_gw_panel; apply the incremental learned offset inside MLComponentChallengerModel.predict H1 before its existing preserve_mass loop. Keep current H1 covariates and weights fixed. The new offset consumes causal Champion prediction caches for earlier training rows; those offsets are proposed derived inputs, not present in train_panel today. This requires a controlled H1 hook or an extracted helper, not enable_congestion=True."
grid: "recovery_days=2,hazard_ridge=100; recovery_days=4,hazard_ridge=100; recovery_days=2,hazard_ridge=400; recovery_days=4,hazard_ridge=400"
inputs: "Existing history.player_id; history.fixture_id; history.gameweek_id; history.minutes; history.starts; history.kickoff_time; features.kickoff_time; features.position_id; current fixture schedule known at deadline. Proposed derived features: actual-playing-dose kernel; shrunk habitual-dose quantile; frozen Champion prequential p_start and horizon expected-minutes cache; genuine seed-row count. No existing features.fatigue, external recovery data, cup minutes, international minutes, injury news, or physiological measurements assumed. Historical schedule provenance prerequisite: final archive fixture dates alone do not establish dates known at each historical deadline. Without deadline-valid schedule evidence, defer this version or specify a separate deadline-only dose formulation before experimentation. No future realized minutes or rescheduled kickoff information may enter historical predictors."
nearest_ledger_row: CSV data rows 52/82/89; proposed actual played-dose/habit signal; historical schedule provenance unresolved
spec_path: ideas/EXT-13-habit-adjusted-cumulative-playing-dose.md
---

# EXT-13: Habit-Adjusted Cumulative Playing Dose

## Checkpoint status (2026-10-28)

Blocked, no empirical verdict: (historical schedule provenance). Current status: `idea_queue.csv` + Candidate Ledger. Proposal body below records original intake, not a current gate verdict.

## 1. Concept & Football Hypothesis

Rotation decisions may respond to accumulated played minutes relative to a player's usual workload, rather than elapsed time since the last listed fixture. Hypothesis: two players on the same turnaround differ when one played several recent full matches and the other had little actual playing time. Current panel's rest_days uses the last recorded row, including rows with zero minutes; short_turnaround is binary. New signal is cumulative played-minute dose relative to a player's own prior exposure distribution.

## 2. Mathematical Formulation

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

## 3. Decoupled Architecture Placement

M_mins, a new played-load covariate and anchored participation correction. xp_minutes and event exposure flow through the existing scorer. No goal/assist/defcon changes.

## 4. Replaces / Integration Hook

Add a pure, pre-deadline workload builder alongside models.ml_panel_features._build_gw_panel; apply the incremental learned offset inside MLComponentChallengerModel.predict H1 before its existing preserve_mass loop. Keep current H1 covariates and weights fixed. The new offset consumes causal Champion prediction caches for earlier training rows; those offsets are proposed derived inputs, not present in train_panel today. This requires a controlled H1 hook or an extracted helper, not enable_congestion=True.

## 5. Parameter Sweep Grid

recovery_days=2,hazard_ridge=100; recovery_days=4,hazard_ridge=100; recovery_days=2,hazard_ridge=400; recovery_days=4,hazard_ridge=400

## 6. Small-Sample & Cold-Start Strategy

Hard GW1-19 fallback; a_g shrinkage afterwards. Habit quantile shrinks with K=12; slope prior centers at zero; no player fixed effects and no personal slope estimated from a short season. Warm seed may initialize position-level habit summaries after explicit immutable summary plumbing. Current-season history drives incremental exposure. Missing/invalid timestamps cause original-Champion fallback, not a synthetic short-rest flag.

## 7. Budget-Constrained Optimizer Interaction

Hypothesis: avoids overvaluing a cheap player whose recent starts reflect exceptional temporary load while leaving players near their own normal exposure close to anchor. No automatic reward for playing infrequently. Smooth dose and bounded regularized slope should be tested for churn, never assumed to satisfy it. Important risk: unobserved cup/international workload makes this only a Premier League load proxy; it may add no information beyond current history features.

## 8. Point-in-Time Feature Requirements

Existing history.player_id; history.fixture_id; history.gameweek_id; history.minutes; history.starts; history.kickoff_time; features.kickoff_time; features.position_id; current fixture schedule known at deadline. Proposed derived features: actual-playing-dose kernel; shrunk habitual-dose quantile; frozen Champion prequential p_start and horizon expected-minutes cache; genuine seed-row count. No existing features.fatigue, external recovery data, cup minutes, international minutes, injury news, or physiological measurements assumed.

   Historical schedule provenance prerequisite: final archive fixture dates alone do not establish dates known at each historical deadline. Without deadline-valid schedule evidence, defer this version or specify a separate deadline-only dose formulation before experimentation. No future realized minutes or rescheduled kickoff information may enter historical predictors.

## 9. Python Code Skeleton (Auto-Scaffolded)

```python
from __future__ import annotations

from models.adaptive_causal_challenger import AdaptiveCausalChallengerModel


class HabitAdjustedCumulativePlayingDoseChallengerModel(AdaptiveCausalChallengerModel):
    """Auto-scaffolded skeleton for Habit-Adjusted Cumulative Playing Dose."""

    def __init__(self, recovery_days: float = 2.0, hazard_ridge: float = 100.0, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.recovery_days = float(recovery_days)
        self.hazard_ridge = float(hazard_ridge)

    def _panel_features(self, *args: object, **kwargs: object) -> object:
        # Hook target: Add a pure, pre-deadline workload builder alongside models.ml_panel_features._build_gw_panel; apply the incremental learned offset inside MLComponentChallengerModel.predict H1 before its existing preserve_mass loop. Keep current H1 covariates and weights fixed. The new offset consumes causal Champion prediction caches for earlier training rows; those offsets are proposed derived inputs, not present in train_panel today. This requires a controlled H1 hook or an extracted helper, not enable_congestion=True.
        parent_method = getattr(super(), '_panel_features', None)
        if callable(parent_method):
            return parent_method(*args, **kwargs)
        raise NotImplementedError('_panel_features mechanism not yet implemented')
```


## Intake Provenance & Mechanism Audit

Source: [minutes-ideation-response.md](../minutes-ideation-response.md); frontier language-model review, 2026-10-28.

Nearest ledger mechanisms: CSV data rows 52/82/89; proposed actual played-dose/habit signal; historical schedule provenance unresolved.

Mechanism decision: Blocked: final archive kickoff dates do not establish schedule known at each historical deadline. Require deadline-valid schedule provenance or separately specified deadline-only formulation before eligibility. Dose from actual played minutes and habitual excess must remain essential; rest-day curve or changed congestion threshold alone is locked lever. No automatic activation or retest authorized.

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
- [Shared reconstruction audit](C:/Users/phjenphithak/fpl-jubilee-ascent/docs/research/candidate-ideation/defense-ideation-response.md).

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
