# Near-miss candidate ideation

**Updated:** 2026-11-10
**Status:** Paper intake; no new empirical results
**Source:** Defender-role specialist, defence specialist, independent cross-cutting reviewer
**Scope:** Saved development diagnostics and source inspection; no archive outcome exploration, confirmation reads, sealed-window reads, model execution, or adoption
**Artifacts:** [Queue](idea_queue.csv), [source proposals](near-miss-ideation-response.md), [current brief](candidate_model_ideation_prompt.md)

## Intake decisions

- EXT-35: Leave-player-and-club-out creative-role kernel prior. Fixed defender K=2400; lagged donor creativity predicts other defenders' subsequent xG. Primary variants exclude target player and target club. Four preregistered variants, including club-exclusion ablation. Paper eligibility cleared; implementation skeleton partial, unregistered.
- EXT-37: Baseline-preserving opponent hazard curvature residual. Retain inherited hard-fixture adjustment; replace exact shipped opponent addon rather than apply opponent evidence twice. Three substantive variants plus identity control. Blocked pending exact overlay reconstruction/applicability provenance and implementation review. Current formula increases hazard only; tough-side slope matches incumbent, easy-side first-order attenuation remains explicit.
- EXT-36/38/39/40: Reserved specialist IDs unused. No additional defensible mechanism; no filler queue entries or automatic combined stack.

Full formulas, input manifests, integration contracts, cold-start fallbacks, ablations, risks, and typed partial skeletons: linked queue dossiers. No performance improvement claimed.

## Failure interpretation

Promising OPEN parents: EXT-20/23/32/33/34. Evidence: `smoke_results.csv` columns `variant`, `combined_delta`, `boot_p_gt0`, `segs`, `reasons`, `evidence_kind`, `scientific_verdict`; parent ledger rows `tried_as`, `status`, `result`. These rows are legacy proxy diagnostics; they cannot establish authoritative promotion verdicts.

Confirmed source findings:

- `backtesting/walkforward.py::inject_oracle_minutes` inserts actual fixture minutes as `external_xmins`. `models/participation_state_hybrid.py::predict` converts them through `target_to_states`, changing state probabilities, conditional durations, and P(60). Actual categorical states are not injected.
- Event hook evaluates start/substitute exposure separately; `models/learned_start_challenger.py::_allocate_bonus` also uses P(60) and synthetic BPS. Oracle/native score reversal does not identify minutes error as its cause.
- EXT-23/33/34 override `_apply_hard_fixture_defence` with identity. Production `models/hold_chase_challenger.py` retains that adjustment. Baseline removal is a separate intervention from proposed opponent signal.
- `features/matchup_share.py::apply_matchup_share_overlay` already adds `0.40 * delta_def` to concession rate. Multiplying incoming rate by another opponent-xG function can duplicate evidence.
- Builder warm seed does not imply seed rows reach candidate `fit()`: inspect `run_walkforward_backtest` history routing before claiming seeded donor/context support.

These findings motivate hypotheses; they do not prove why saved candidates lost. Saved aggregate smoke rows omit successful Tier-2 detail when followed by Tier 3; duplicate/superseded attempts and stale numerical ledger summaries require provenance checks before future analysis.

## Eligibility decisions

Active Dead locks unchanged. OPEN parent status does not authorize rebuilding an overlapping Dead class.

EXT-35 lexical matcher flags Dead club-by-DEF prior stacked with K2400. Independent semantic review clears paper intake: kernel conditions on lagged creativity across donor clubs, excludes target player's xG responses, preserves own-observation denominator, and excludes target-club rows in primary variants. Club-exclusion ablation pools all clubs, never selects target-club mean. Require synthetic own-xG impulse invariance, target-club invariance for all-club ablation, historical club reconstruction, DEF-only donor panel, full same-GW lag exclusion, and finite-input identity fallback. Preserve flagged class and rationale in queue/dossier.

EXT-37 remaining distinction depends on exact subtraction/replacement of shipped addon. Global CS/GC scaling, raw FDR fallback, opponent-rate amplification without cancellation, changed concession likelihood, and altered P(60)/exposure remain excluded. Unknown overlay applicability must not silently become an activated experiment.

EXT-37 lexical matcher also flags incumbent-return displacement. Independent semantic review rejects that match: proposal changes no start probabilities or club participation mass. Flag retained in dossier; blocked status reflects genuine overlay-provenance prerequisite.

No model attempts conducted; Candidate Ledger outcomes and locks unchanged. Queue records ideation only.

## Preregistered diagnostic before stacking

After implementation admission, freeze one eligible event intervention and cross event-head on/off with native/oracle participation. Four cells: Champion/native, intervention/native, Champion/oracle, intervention/oracle. Development 2025-26 only, seed 2024-25; no calendar-dependent activation or post-result grid expansion.

Retain full player-fixture frames and hashes before aggregation. Within each regime, event-on/off state tensors must match. Export rates, state probabilities, conditional durations, P(60), component points, BPS, bonus, selected starters/bench/captain, and common outcomes. Compare fixed selections separately from reoptimized selections. Do not change oracle decoder while running this diagnostic.

- Decision-score delta: intervention minus Champion under same regime; higher better; ideal positive. Diagnostic score target named explicitly; authoritative promotion target remains native rolling net FPL points.
- Regime interaction: oracle delta minus native delta; absolute magnitude lower means less regime sensitivity; ideal zero for transport stability, not proof of correctness.
- Component MAE: mean absolute component error; lower better; ideal zero. Signed component error: mean forecast minus outcome; ideal zero; neither positive nor negative preferred.
- Formation XI regret: existing diagnostic selection loss under common £100m 15-player squad with bench auto-subs; lower better; ideal zero.
- Squad-churn delta: candidate minus Champion `top_15_squad_churn`; lower better; ideal no increase, guard at most +0.50 players/GW. Not actual transfer count.

No four-cell summary grants promotion. Require ADR 0068 implementation reviews, native development screens, frozen registered confirmation, substantive guards, and admitted ADR 0066 rolling replay evidence before adoption.
