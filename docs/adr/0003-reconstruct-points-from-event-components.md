# Reconstruct projections from event components via the FPL scoring matrix

## Context

`linear_baseline` predicts a Player's total points directly from a rolling average. At Cold-Start (new season, no current-season history) every Player projects to 0 and the solver produces a meaningless squad. We are introducing a component model seeded from a Prior-Season Seed to fix this.

## Decision

The new model will **not** learn total points as a target. Instead it predicts per-90 Event Rates (minutes/appearance, goals, assists, clean sheets, goals_conceded, saves, bonus, cards, penalty events) and reconstructs projected points by mapping those events through the official FPL scoring matrix (deterministic per Position: a Goal is worth 6/5/4/4 for F/M/D/GK, an Assist 3, a Clean Sheet 4/4/1/0, etc.).

Event Rates are seeded from the Prior-Season Seed and blended into current-season data after a threshold of current-season appearances. Clean sheets and goals-conceded are modeled per Player from prior history (Player-level), not per Club. Newcomers with no prior seed fall back to the Position-Price Prior.

## Consequences

- Projections become explainable (a Player's xP is the sum of its event contributions).
- The model can produce sensible projections at Cold-Start instead of 0.
- Adding the matrix is cheap and reversible per-event, but switching the whole model back to direct-points prediction would be a rewrite — hence recording the decision.
- Reconstructing ignores any residual points not explained by tracked events (e.g. rare scoring-rule edge cases); accepted as noise.
