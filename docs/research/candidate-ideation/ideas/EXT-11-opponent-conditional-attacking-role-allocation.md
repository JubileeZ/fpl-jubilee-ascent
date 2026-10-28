---
idea_id: EXT-11
name: Opponent Conditional Attacking Role Allocation
tier: P2
component: xp_goals
status: untested
replaces: Add derived opponent-role contrasts alongside causal panel context. Existing _reconstruct_club_id and _club_fixture_table provide in-memory club-side pattern; require exactly two identifiable fixture sides. Precompute forecast normalizers by (fixture_id,club_id) before event projection. Apply factors in _project_event_components using inherited expected goal counts; update scoring points/BPS. For final-MID/FWD total-preservation property, incorporate existing Group A goal multiplier into precomputed counts or apply normalization after Group A and rerun inherited bonus calculation once. Specify one ordering before implementation; do not silently claim pre-Group-A normalization preserves final totals.
grid: "lambda_role=25.0; lambda_role=50.0; lambda_role=100.0"
inputs: "Existing: features.player_id; features.position_id; features.club_id; features.opponent_id; features.fixture_id; features.gameweek_id; history.player_id; history.fixture_id; history.gameweek_id; history.opponent_club_id; history.minutes; history.expected_goals; history.expected_assists; history.was_home; history.price. Derived to implement: derived.predeadline_profile; derived.predeadline_xg_offset; derived.opponent_role_contrast; derived.club_attacker_normalizer. Historical positions must come from known season position mapping; no cross-season current-position backfill. Unavailable/not used: shot location, actual wide/central role, marking assignments, possession, bookmaker spread. Do not label shooting/creating bins as observed tactical roles."
nearest_ledger_row: CSV data rows 12/32/40/50/73; new conditional opponent-role contrasts, not scalar club strength or absent-player mass transfer
spec_path: ideas/EXT-11-opponent-conditional-attacking-role-allocation.md
---

# EXT-11: Opponent Conditional Attacking Role Allocation

## Checkpoint status (2026-10-28)

Implementation/checks prepared under `prototypes/ext_11/`; audit and synthetic checks pending. No smoke or empirical verdict. Current status: `idea_queue.csv` + Candidate Ledger. Proposal body below records original intake, not a current gate verdict.

## 1. Concept & Football Hypothesis

Hypothesis: opponents differ in which attacking profiles generate chances against them, beyond total chances conceded. Aggregate opponent xG cannot distinguish concessions to shooting midfielders, creating midfielders, and forwards. FPL positions provide coarse profiles only; no inference about real winger/striker locations. New signal is relative attacking-role concession pattern, conditional on opponents already faced.

   Ledger screen: mechanism-eligible on paper, higher near-match risk than Candidate 1. Nearest locked mechanisms: scalar opponent-relative team Poisson multiplier, true scoreline Poisson, flat MID/FWD goal scales, schedule-adjusted past player xG/xA. New opponent-by-role interaction leaves total attacking expectation fixed, varies across opponents, and adjusts for attacking profiles actually faced. Any implementation reducing to scalar opponent rate or historical xGC deflation is rejected.

## 2. Mathematical Formulation

At every historical deadline, assign MID to shooting/creating profile from pre-deadline shrunk `xG/(xG+xA)`, threshold 0.5; FWD gets third profile. Profile assignment uses prior history only. Let `I_f` be MID/FWD players on attacking side of completed historical fixture. Set `b_if=(minutes_if/90)*r_xG,i,<gw(f)` using causal prior rate; historical target minutes serve exposure, not forecast feature. Fit conditional allocation:

   $$p_{if}(\theta)=\frac{b_{if}\exp(\theta_{o(f),r(i,f)})}{\sum_{j\in I_f}b_{jf}\exp(\theta_{o(f),r(j,f)})}.$$

   Generalized multinomial log-likelihood for fractional process marks:

   $$\widehat\theta=\arg\max_\theta\left\{\sum_{f<g}\sum_{i\in I_f}xG_{if}\log p_{if}(\theta)-\frac{\lambda}{2}\sum_{o,r}\theta_{or}^2\right\},\quad\sum_r\pi_r\theta_{or}=0.$$

   Prior `theta_or ~ Normal(0,1/lambda)` on centered contrast space; `pi_r` equals causal league profile exposure shares. Skip zero-total fixtures and ineligible/missing-offset records. Pre-deadline offsets account for opponent schedule composition; fitting simple raw conceded role shares would confound defensive preference with attackers faced.

   For forecast fixture, let `C_i` be inherited expected goal count and `u_i=exp(alpha_g*theta_opponent,role)`. Apply identity for defenders and goalkeepers. Within attacking club's MID/FWD subset:

   $$C_i'=C_i\frac{u_i}{\sum_jC_ju_j/\sum_jC_j}.$$

   Zero total uses identity. Limit fitted contrasts to `[-log(1.10),log(1.10)]` before forecast normalization; bounds fixed across grid. Thus `sum_i C_i'=sum_i C_i` over MID/FWD. Common scalar `theta_or=a_o` cancels exactly, proving scalar opponent-strength multiplier cannot generate proposal's effect. No `sum p_start=11` constraint; no redistribution of absent player's xG.

## 3. Decoupled Architecture Placement

`M_events`: `xp_goals`. No new assists, minutes, clean-sheet, or bonus head. Existing effects of changed goal counts on BPS follow inherited mechanism.

## 4. Replaces / Integration Hook

Add derived opponent-role contrasts alongside causal panel context. Existing `_reconstruct_club_id` and `_club_fixture_table` provide in-memory club-side pattern; require exactly two identifiable fixture sides. Precompute forecast normalizers by `(fixture_id,club_id)` before event projection. Apply factors in `_project_event_components` using inherited expected goal counts; update scoring points/BPS. For final-MID/FWD total-preservation property, incorporate existing Group A goal multiplier into precomputed counts or apply normalization after Group A and rerun inherited bonus calculation once. Specify one ordering before implementation; do not silently claim pre-Group-A normalization preserves final totals.

## 5. Parameter Sweep Grid

`lambda_role=25.0`; `lambda_role=50.0`; `lambda_role=100.0`. Profile threshold `0.5`, contrast bound `log(1.10)`, cutoff GW20, fixed N_eff thresholds. No matchup shrink or position goal-weight sweep.

## 6. Small-Sample & Cold-Start Strategy

Before GW20, exact inherited predictions. Unseen opponent or missing profile evidence gives zero contrast. New heads use current-season history; warm seed remains in Champion baseline rates. Ridge prior shrinks profile contrasts, not DEF xG rate. Promoted clubs remain near neutral until observed concessions differentiate roles. No player fixed effects; causal rate offsets generated with strictly earlier history. Double-GW matches remain fixture-level observations with one pre-deadline information boundary.

## 7. Budget-Constrained Optimizer Interaction

Hypothesis: within same fixture, low-cost shooting MID can rank differently from expensive FWD where opponent's relative profile pattern differs. Fixed total prevents extra club attacking mass from new feature; no price-driven multiplier. Profile assignment and opponent contrast can still cause switches, so churn remains empirical guardrail. Captaincy risk: reallocating MID/FWD mass can suppress premium forwards; evaluate active-window captaincy regret explicitly. This mechanism is weaker if coarse FPL positions contain little stable matchup information.

## 8. Point-in-Time Feature Requirements

Existing: `features.player_id`; `features.position_id`; `features.club_id`; `features.opponent_id`; `features.fixture_id`; `features.gameweek_id`; `history.player_id`; `history.fixture_id`; `history.gameweek_id`; `history.opponent_club_id`; `history.minutes`; `history.expected_goals`; `history.expected_assists`; `history.was_home`; `history.price`. Derived to implement: `derived.predeadline_profile`; `derived.predeadline_xg_offset`; `derived.opponent_role_contrast`; `derived.club_attacker_normalizer`. Historical positions must come from known season position mapping; no cross-season current-position backfill. Unavailable/not used: shot location, actual wide/central role, marking assignments, possession, bookmaker spread. Do not label shooting/creating bins as observed tactical roles.

## 9. Python Code Skeleton (Optional)

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

## Intake Provenance & Mechanism Audit

Source: [attack-ideation-response.md](../attack-ideation-response.md); frontier language-model review, 2026-10-28.

Nearest ledger mechanisms: CSV data rows 12/32/40/50/73; new conditional opponent-role contrasts, not scalar club strength or absent-player mass transfer.

Mechanism decision: Common scalar opponent contrast cancels under final normalization. Preserve club attacking expectation after existing Group A multiplier; do not normalize before Group A and claim final totals remain fixed. No raw opponent-strength scale, past xGC deflation, or teammate-absence redistribution.

Specification only: any autogenerated Python scaffold is incomplete wiring, not an implemented or evaluated model. Source references to shared Candidate 1 mean EXT-07. Dependency completion never authorizes stacking a lever that subsequently receives a dead verdict.

Lexical-screen flag: none. Token overlap is not empirical or mechanism equivalence; distinctions above govern paper intake.

No empirical attempt; no candidate-ledger verdict. Recheck authoritative ledger before implementation. Preserve confirmation freeze and sealed holdout.

## Shared Source Context

# Attacking-rate ideation

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
