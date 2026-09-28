# Two-season promotion gate; sealed holdout becomes post-promotion check

Amends ADR 0046 promotion order. **Amended by ADR 0048**: 2024-25 bootstrap bar 0.60. Frozen Candidate promotes when it passes Historical Promotion Gate (ADR 0046 rules unchanged: Blended `top_11_regret`, delta ≥ 1% Champion regret, 3-GW block-bootstrap P ≥ 0.95, ≥2/3 segments, guardrail tolerances) on **both** seasons:

1. 2025-26 GW1–38, seed 2024-25 (development season; selection + tuning here only).
2. 2024-25 GW1–38, no seed (confirmation season; never tuned on; one run per frozen Candidate).

Pass both → `commands.evaluate_model_promotion --data_dir data/archive/2024-25/processed --apply` on user's words, new promotion ADR. Fail 2024-25 → Champion stays; Candidate Ledger row Dead (evidence + 1 year).

2026-27 GW6+ stays sealed (no tuning/smoke/ablation). Role changes: one post-promotion check per promoted Champion once finished GWs available; FAIL → revert to prior Champion (user's words) and log in Ledger.

2024-25 scoring differs (no defensive contribution points, stricter assist rule — 41 fewer season assists under 2025/26 definition — different BPS weights) and has no 2023-24 seed (cold start = position/price priors for every model). Accepted: gate is relative, both models scored on same season; defcon absent in data → zero for both; bonus logic shared. 2024-25 Assistant Manager elements (`position_id` 5, team-result points outside player ledger) excluded from walk-forward evaluation (`PLAYER_POSITIONS`, `backtesting/walkforward.py`); no-op for 2025-26+ (fixed before first verdict). Candidates whose lever is defcon/BPS-specific: 2024-25 result not informative → keep ADR 0046 holdout-first order for those.

Rationale: 2026-27 GW6+ unavailable until 2026-10-12 and small for weeks; 2024-25 = full independent season never used as target. Recorded before first 2024-25 gate run (`multi_feature_assist_challenger`, 2026-09-28).

**Considered Options**: holdout-first only (ADR 0046) — rejected as sole path (weeks of delay, ≤5 GWs cannot reach P 0.95); 2026-27 GW1–5 as confirmation — rejected (GW-lagged Candidates inactive GW1–3, looked at in prior searches); pooled 2024-25 + 2025-26 single gate — rejected (dev season dominates; want independent pass).
