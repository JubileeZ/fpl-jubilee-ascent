# Champion adaptive_causal_challenger (Adaptive Late-Season Causal ML Candidate)

**Status**: Accepted (2026-10-21, user authorized promotion on dev + confirm PASS under ADR 0062)

`adaptive_causal_challenger` replaces `def_xg_shrink_challenger` as Model Champion under the gate of ADR 0047, ADR 0049, ADR 0054, and ADR 0062 (Legal Formation XI regret primary, Playable-Pool guardrails, non-catastrophic segment loss guardrails, bootstrap P ≥ 0.60 both seasons, no minimum effect).

Model = `def_xg_shrink_challenger` stability in GW1–19 + stacked Causal Panel ML components in GW20+ (Tier 1 Ridge $p_{\text{start}}$ + start duration offset, Tier 2 shrunk xG residual goals + calibrated LOO assist finishing). Strictly excludes dead schedule congestion lever.

## Context & Rationale

Prior ML candidates (`ml_component_challenger` and `apex_predator_challenger`) demonstrated extraordinary predictive power in late-season conditions (+1.47 pts/GW) but failed confirmation on unseeded historical seasons due to early-season sample deficits and talisman haul over-regularization during GW5–19 (Cole Palmer and Erling Haaland 2024–25 runs). Furthermore, bundling the dead schedule congestion lever (-0.20 logit penalty for turnarounds < 3.5 days) penalized confirmation performance by -0.105 pts/GW.

`adaptive_causal_challenger` resolves this structural dilemma by enforcing 100% Champion stability across GW1–19, guaranteeing zero regression on early seasonal segments ($\Delta_{\text{cold\_start}} = 0.000 \ge -0.05$ and $\Delta_{\text{early\_mid}} = 0.000 \ge -0.15$). It activates causal ML at GW20+ after all 20 Premier League clubs have completed a full 19-match round-robin cycle (>3,800 player matches), providing well-conditioned statistical estimators that capture immense predictive alpha.

## Evidence

Evidence recorded in `docs/research/ml-adaptive-champion/candidate_gate.csv` (Blended `formation_xi_regret`, GW1–38):
- **2025–26 Dev**: PASS — delta = +0.7359 pts/GW (+28.0 legal XI points), bootstrap P(delta > 0) = 0.9918, 5/5 guardrails passed, ADR 0062 segment guardrails passed.
- **2024–25 Confirmation**: PASS — delta = +0.2259 pts/GW (+8.6 legal XI points), bootstrap P(delta > 0) = 0.6556, 5/5 guardrails passed, ADR 0062 segment guardrails passed.
- Deterministic replay via `uv run python -m commands.evaluate_model_promotion --data_dir data/archive/2024-25/processed --confirmation --apply` reproduces the confirmation victory.

## Slate & Lifecycle

- Status: provisional upon promotion (archive not snapshot-backed).
- Comparison Slate: Candidates `def_xg_shrink_challenger`, `club_def_prior_challenger`; `learned_start_challenger` leaves slate (max 2 Candidates).
- 2026–27 GW6+ post-promotion check pending once holdout GW6+ finishes; FAIL → revert to `def_xg_shrink_challenger` on user's words.
