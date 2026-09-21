# Trailing Start Window for Participation State xMins

Thin current-club tenure plus Position-Price shrink left recent starters (Konsa-class) with low xMins despite trailing Starts. Feature Contract now applies **Trailing Start Window**: when last \(K=3\) current-club Club Fixtures are Starts (any Sub-in or Recorded DNP resets), blend window posterior with full-tenure posterior at \(w=0.90\) toward the window. State only; Event Rates unchanged. Data-only; Expected Role stays retired (ADR 0025). Globals (`STATE_PRIOR_STRENGTH`, recency decay) unchanged.

**Status:** Accepted. Amends ADR 0022 / 0024 / 0026 Participation State path only.

**Considered:** Global prior/recency retune; replace window (no blend); Role/lineup prior; Candidate-only flag until promotion. Rejected: globals hurt White-like tenures and barely lift nails; replace is cliffier; Role reopens judgment; dual minutes brains fight ADR 0022 one-brain rule. Eval: 2025-26 walk-forward minutes MAE −0.31, 60+ underprediction improves; overall minutes bias and xP MAE tick up slightly — accepted for starter under-trust fix. Live scenarios: Konsa ≥70, Gabriel ≥85, Mosquera ≤45.

**Consequences:** Default `trailing_start_k=3`, `trailing_start_weight=0.90` in `build_features`. Opt-out: `trailing_start_k=0`. Rate Recency Candidate deferred (separate grill). Re-project / Refresh for live Explorer.
