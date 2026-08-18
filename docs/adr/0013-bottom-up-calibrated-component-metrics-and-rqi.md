# 0013: Bottom-Up Calibrated Component Metrics, Dual-Vector Strength, and RQI

**Status:** Accepted. Clause 4 (Points-Heavy RQI) superseded by [ADR 0015](0015-defensive-composite-score.md). Clauses 1–3 unchanged.

## Context

Evaluating players, team strength, and complementary rotation pairs requires aligning metric architecture with FPL's discrete event scoring rules. Relying solely on static official FDR ratings or top-down composite power ratings obscures underlying event rates (xG, xA, defcon, saves) and prevents precise backtesting.

## Decision

We establish the foundational metric and ability modeling architecture for projections, feature engineering, and research notes:

1. **Bottom-Up Calibrated Component Architecture**: Projections derive expected points ($xP$) directly from underlying per-90 skill rates (`per90_xg`, `per90_xa`, `per90_defcon`, `per90_saves`) multiplied by venue-adjusted team/opponent strength factors and projected minutes.
2. **Rolling xG/xGA Dual-Vector Strength**: Team attack and opponent defense strength multipliers are calculated from 10-match rolling non-penalty xG (Team Attack) and xGA (Team Defense) scaled against league averages, falling back to official FDR only when data is sparse.
3. **Recency-Weighted Prior Shrinkage**: Player underlying rates blend a multi-season prior with exponential recency decay over recent matches, applying Bayesian shrinkage for sample-constrained / low-minute players.
4. **Points-Heavy Rotation Quality Index (RQI)**: Goalkeeper and Defender rotation pairs are evaluated for research reports using a canonical 0–100 score:
   $$\text{RQI} = 0.40 \cdot S_{\text{tot\_xp}} + 0.20 \cdot S_{\text{fdr}} + 0.20 \cdot S_{\text{corr}} + 0.10 \cdot S_{\text{easy}} + 0.10 \cdot S_{\text{cost}}$$
   where $S_{\text{tot\_xp}}$ measures Total Rotated Expected Points ($\text{tot\_rot\_xp}$) on a normalized scale, prioritizing absolute expected points output over relative gain ($\Delta xP$) to prevent artificial score inflation from volatile lower-tier/promoted keepers.


## Consequences

- $xP$ projections remain fully auditable, event-decomposed, and backtestable against official FPL scoring rules.
- Match-level strength adjustments react dynamically to team form and venue splits rather than relying on static integer FDR ratings.
- Research reporting historically used RQI for complementary pairings. Live ranking is DCS (ADR 0015).
