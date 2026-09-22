# Calibrated Matchup Share (Shrunk Delta, Positional Priors, Decoupled Peripherals)

**Status:** Accepted. Supersedes the uncalibrated Matchup Share section of [ADR 0037](0037-fdr-fallback-multiplier-neutral.md).

Production Feature Contract fixture scaling priority:

1. **Calibrated Matchup Share** — when this-season finished Club Fixture Official xG history exists before the history cutoff (`features/matchup_share.py`):
   - **Shrunk Additive Delta**: Attack rates (`per90_xg`, `per90_xa`) and goals conceded (`per90_goals_conceded`) scale by calibrated factor $s_{\text{att}} = s_{\text{def}} = 0.40 \times \Delta_{\text{opp}}$. Tames the easy-fixture overprediction ceiling (+0.450 process bias on `easy_mid_fwd` reduced toward neutral) and controls clean sheet inflation from Jensen's inequality.
   - **Bayesian Positional Priors**: Player shares shrink toward position-level baseline priors ($\beta_{\text{pos}} = 4.0$; FWD ~0.26, MID ~0.14, DEF ~0.03). Solves the returning-star 0-share blindspot and dampens small-sample substitute spikes.
   - **Decoupled Peripherals**: `per90_saves` and `per90_defensive_contribution` remain neutral (×1.0), removing the shot quality vs volume distortion that penalized goalkeepers in easy fixtures.
   - **Model-Only Penalty Isolation**: `matchup_share.py` does not touch penalties. Penalty threat isolation (~0.15 xG/90 held out) is handled strictly by `ParticipationPenaltyHybridModel` at prediction time, fixing the ~0.045 xG open-play depression defect caused by Threat dilution.
   - **Sample-Weighted Venue Blending**: Venue weighting in `_blended_rate` scales smoothly via $w_{\text{venue}} = \min(0.5, n_{\text{venue}}/6)$, avoiding 1-match sample distortions.
   - **Multipliers**: Clamped to ×1.0 to prevent double-scaling with Club Strength.
2. **Club Strength** — when Matchup Share does not apply (new season / no Official xG games yet) and attack/defence strengths are non-zero: ratios in `_fixture_maps` (clamp 0.4–1.8).
3. **Neutral ×1.0** — when Matchup Share does not apply and strengths are 0/missing: `FDR_FALLBACK_MULTIPLIER_SHRINK = 0.0`. Modified FDR stays **difficulty** only ([ADR 0019](0019-modified-fdr-for-linear-baseline.md)).

Model Champion: [ADR 0039](0039-champion-participation-penalty-hybrid.md).
Target evaluation: [ADR 0038](0038-process-points-eval-target.md).
Companion research: `docs/research/matchup-share-addon-2025-26/matchup_share_summary.csv`.
