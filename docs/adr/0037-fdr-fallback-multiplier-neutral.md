# FDR fallback multipliers neutral when Club Strength is zero

Live 2026/27 Club Strength attack/defence fields are 0, so `_fixture_maps` fell back to Modified FDR as `attack_multiplier` / `defence_multiplier`. Research on 2025-26 with that fallback forced: easy MID/FWD (`difficulty ≤ 2`, xMins ≥ 60) `signed_bias` ≈ +0.75 vs Club Strength ≈ −0.14; then-Champion ≈ participation. Decision: when strength ratios unavailable, shrink FDR raw multipliers toward 1.0 with `FDR_FALLBACK_MULTIPLIER_SHRINK = 0.0` (neutral ×1.0). Keep Modified FDR as Feature Contract **difficulty** (ADR 0019). Companion: `docs/research/dual-vector-fdr-regime-2025-26/fdr_fallback_shrink_sweep.csv`. Champion identity: [ADR 0039](0039-champion-participation-penalty-hybrid.md).

Rejected: keep raw FDR fallback; high attack cap only; calibrate live xP to Solio.
