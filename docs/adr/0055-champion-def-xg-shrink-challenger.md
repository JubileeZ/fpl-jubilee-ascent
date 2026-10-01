# Champion def_xg_shrink_challenger (Position-specific DEF xG rate shrinkage K=2400)

**Status**: Accepted (2026-10-01, user authorized promotion on dev + confirm PASS under ADR 0054)

`def_xg_shrink_challenger` replaces `club_def_prior_challenger` as Model Champion under the gate of ADR 0054 (Legal Formation XI regret primary, Playable-Pool guardrails, bootstrap P ≥ 0.60 both seasons, no minimum effect). Model = `learned_start_challenger` + position-specific xG rate shrinkage (idea ATK-04, `docs/research/component-model-ideas`): DEF xG/90 shrinks toward the as-of DEF position mean with 2400 pseudo-minutes instead of 360 (split-half reliability of DEF xG/90 is low: r ≈ 0.30 vs MID/FWD). Applied as ratio `rate_K / rate_360` on `features.per90_xg` so builder prior, matchup addon, and penalty isolation survive.

## Context & Rationale
Under historical unconstrained `top_11_regret`, outfield lineups were heavily dominated by attacking midfielders and forwards (often 0–1 DEF). Consequently, defender xG noise barely affected 2024-25 unconstrained selection regret, causing `def_xg_shrink_challenger` to fail confirmation previously (-0.076 pts/GW, ADR 0047). Under ADR 0054, every legal lineup strictly enforces 1 GKP, 3–5 DEF, 2–5 MID, 1–3 FWD. In this formation-constrained environment, noisy defender xG misled the lineup optimizer into selecting fluke defenders who scored early. Dampening defender xG with K=2400 pseudo-minutes completely eliminates these traps and delivers decisive improvements across both seasons.

## Evidence
Evidence recorded in `docs/research/formation-eval-retest/candidate_gate.csv` (Blended `formation_xi_regret`, GW1–38):
- **2025-26 Dev**: PASS — delta = +0.7929 pts/GW, 3/3 seasonal segment wins, bootstrap P(delta > 0) = 0.944, all guardrails passed.
- **2024-25 Confirmation**: PASS — delta = +0.5941 pts/GW, 2/3 seasonal segment wins, bootstrap P(delta > 0) = 0.863, all guardrails passed.
- Deterministic replay via `commands.evaluate_model_promotion --data_dir data/archive/2024-25/processed --confirmation --apply` matches confirmation verdict.

## Slate & Lifecycle
- Status: provisional (archive not snapshot-backed).
- Comparison Slate: Candidates `club_def_prior_challenger`, `learned_start_challenger`; `multi_feature_assist_challenger` leaves slate (max 2 Candidates).
- 2026-27 GW6+ post-promotion check pending once holdout GW6+ finishes; FAIL → revert to `club_def_prior_challenger` on user's words.
