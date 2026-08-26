# 0005: Hybrid Metrics Component Projection Model (Calibrated Components)

## Context

`component_baseline` provides the explainable Cold-Start foundation. The hybrid model
adds metric-informed attack rates, fixture-specific attack/defence effects, and
count-distribution expectations for thresholded FPL events.

## Decision

We introduce `metrics_component_hybrid` (`models/metrics_component_hybrid.py`) which implements:

1. **Scoring Matrix Alignment**: Official goal points (GK=10, D=6, M=5, F=4), red cards (-3), and outfield defensive-contribution points live in `models/scoring_matrix.py`. Source and capture date are recorded in `docs/fpl_scoring_rules_2025-26.md`.
2. **Fixture-Level Inputs**: Feature rows retain `fixture_id` and derive separate attack and defence multipliers from opponent/team strength vectors when available; FDR remains the documented fallback.
3. **Calibrated Attack Mapping**: Goal rates use `xG` + `Threat`, and assist rates use `xA` + `Creativity`. `fit(history_df)` estimates non-negative weights from pre-cutoff history and shrinks sparse estimates toward the default prior.
4. **Poisson Defence & Defcon Model**:
   - Clean Sheet: $P(\text{Clean Sheet}) = e^{-\lambda}$ multiplied by a calibrated probability of reaching 60 minutes.
   - Goals Conceded Deduction and Saves: expected values over Poisson count distributions, not `floor(expected count)`. Saves $\lambda$ scales by `defence_multiplier` (opponent attack / own defence).
   - Defcon: negative-binomial threshold probability for DEF (threshold 10) and MID/FWD (threshold 12), mapped to two expected FPL points. Defcon $\lambda$ scales by the same `defence_multiplier`.
   - Strength missing or zero: Modified FDR fallback already in `_fixture_maps` (`difficulty / 3` for defence, `(6 - difficulty) / 3` for attack, clipped 0.4–1.8; ADR 0019). Model uses the same FDR ratios when multiplier columns are absent.
5. **Competitor-Aware Bonus Proxy**: fixture competitors receive a softmax allocation of three expected bonus points. This is an auditable proxy for the official match-level BPS tie system, not a fitted multinomial BPS model.

## Consequences

- Point-in-time backtests can fit attack mappings without using target-gameweek outcomes.
- Fixture projections aggregate safely for double gameweeks before solver export.
- Bonus remains an approximation until richer match-level BPS features and tie handling are available.
