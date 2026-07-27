# 0010: Participation State, Snapshots, and Evaluation

## Status
Accepted

## Decision
Model each Fixture Projection through mutually exclusive Participation States: Did Not Play, Start, and Sub-in. Estimate state probabilities from recency-weighted Club Fixtures, shrink toward Prior-Season or Position-Price priors, and estimate conditional minutes separately for starts and sub-ins. Event Component projections remain conditional on each state; `xP = P(Start) × xP|Start + P(Sub-in) × xP|Sub-in`. Official FPL chance is calibrated next-gameweek evidence only; official club information may create reviewed, source-attributed, expiring Availability Overrides.

Capture all prediction-critical mutable inputs as change-only, immutable snapshot packages during the 48 hours before a deadline. Store `players.parquet`, `clubs.parquet`, `fixtures.parquet`, and metadata under season, target Gameweek, and capture timestamp on a dedicated versioned data branch. Promotion backtests require a verified package for every Gameweek, matching its recorded deadline and content hash; missing packages fail evaluation rather than falling back to terminal metadata. Validate changes on an untouched holdout: lower no-appearance overprediction and xMins MAE without worsening xP MAE or bias. Evaluate advice through three-way, full-FPL-rules one-Gameweek Decision Regret for the public User Squad; defer transfer-plan regret until this passes.

## Consequences
Do not reuse FPL next-round availability across the Planning Horizon or treat unobserved injuries/suspensions as excluded historical fixtures. Component attribution must form an exact official scoring ledger; Defcon comes from its recorded event count, never a points residual. No third-party xP/xMins feed is ingested.
