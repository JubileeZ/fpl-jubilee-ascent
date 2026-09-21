# Matchup Share primary; Club Strength then neutral fallback

**Status:** Accepted. Supersedes prior ADR 0037 neutral-only when Club Strength is 0.

Production Feature Contract fixture scaling priority:

1. **Matchup Share** — when this-season finished Club Fixture Official xG history exists before the history cutoff (`features/matchup_share.py`). Bumps `per90_xg` / `per90_xa` by player club share × (opp xGC − league); `per90_goals_conceded` by (opp xG − league); scales saves/defcon by opp xG / league. Forces `attack_multiplier` / `defence_multiplier` ×1.0. Pen takers: add-on on open-play only (~0.15 xG/90 held out).
2. **Club Strength** — when Matchup Share does not apply (new season / no Official xG games yet) and attack/defence strengths are non-zero: ratios in `_fixture_maps` (clamp 0.4–1.8).
3. **Neutral ×1.0** — when Matchup Share does not apply and strengths are 0/missing: `FDR_FALLBACK_MULTIPLIER_SHRINK = 0.0`. Modified FDR stays **difficulty** only (ADR 0019).

Champion: [ADR 0039](0039-champion-participation-penalty-hybrid.md).

Research on 2025-26 all-pool: Matchup Share `signed_bias` slightly worse than neutral (Realized +0.200 vs +0.185; Process +0.213 vs +0.198). Shipped anyway per product choice with cold-start Strength → neutral fallback. Companion: `docs/research/matchup-share-addon-2025-26/matchup_share_summary.csv`.

Rejected as sole cold-start scale: raw Modified FDR as multiplier; Official xG Dual-Vector / Team Poisson λ without Share form; Solio calibration.
