# 0005: Hybrid Metrics Component Projection Model (Regression Attack + Poisson Defence + Softmax Bonus)

## Context

`component_baseline` provided a solid Cold-Start foundation but used a single monolithic fixture multiplier, inverted goal scoring points in the matrix (Forward=6, Defender=4), lacked underlying metrics regression (xG/Threat/xA/Creativity), ignored defensive contributions (Defcon), and lacked discrete Poisson modeling for clean sheets, goal concessions, and bonus points.

## Decision

We introduce `metrics_component_hybrid` (`models/metrics_component_hybrid.py`) which implements:

1. **Scoring Matrix Alignment**: Correct goal points (F=4, M=5, D=6, GK=6) and red cards (-3) in `models/scoring_matrix.py`.
2. **Dual Fixture Multipliers**: Separate Attack Multiplier (opponent defence) and Defence Multiplier (opponent attack).
3. **Regression Attack Model**: Goal rates predicted from `xG` + `Threat`; assist rates predicted from `xA` + `Creativity`.
4. **Poisson Defence & Defcon Model**:
   - Clean Sheet: $P(\text{Clean Sheet}) = e^{-\lambda}$ for players with $xMins \ge 60$.
   - Goals Conceded Deduction: Discrete Poisson expectation sum over $k \ge 2$ conceded.
   - Defcon: Poisson/Negative-Binomial threshold probability for DEF (threshold 10) and MID/FWD (threshold 12).
5. **Softmax BPS Bonus Model**: Reconstruct expected BPS from event outputs and map to expected bonus points via multinomial logistic regression.

## Consequences

- Direct alignment with official FPL scoring rules.
- Predicts expected points with higher precision by separating finishing variance from underlying chance creation and defensive work.
- Projections remain fully explainable and deterministic per event component.
