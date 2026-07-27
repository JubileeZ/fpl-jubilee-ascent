# 0010: Participation State, Snapshots, and Evaluation

## Status
Accepted

## Decision
Model each Fixture Projection through mutually exclusive Participation States: Did Not Play, Start, and Sub-in. Estimate state probabilities from recency-weighted Club Fixtures, shrink toward Prior-Season or Position-Price priors, and estimate conditional minutes separately for starts and sub-ins. Event Component projections remain conditional on each state; `xP = P(Start) × xP|Start + P(Sub-in) × xP|Sub-in`. Official FPL chance is calibrated next-gameweek evidence only; official club information may create reviewed, source-attributed, expiring Availability Overrides.

Capture all prediction-critical mutable inputs as change-only, immutable snapshot packages during the 48 hours before a deadline. Store `players.parquet`, `clubs.parquet`, `fixtures.parquet`, and metadata under season, target Gameweek, and capture timestamp on a dedicated versioned data branch. Verified packages must match their recorded deadline and content hash.

Snapshot-backed evaluation supports validated promotion. Archive-only evaluation may support Provisional Historical Promotion: its evidence must identify missing snapshot coverage, retain the former Model Champion in the Comparison Slate, and receive two Live Validation Windows before validation. Missing packages still fail strict snapshot-backed evaluation rather than falling back to terminal metadata.

Automatically evaluate registered Candidates when their code changes. Promote a Candidate when it wins the combined prior-season evaluation and two of Cold-Start, early/mid-season, and late-season windows on Decision-First Evaluation while matching Champion guardrails. Commit the resulting model-selection configuration and Promotion Evidence Record. Live reassessment is report-only; it never switches the Champion automatically. Evaluate advice through three-way, full-FPL-rules one-Gameweek Decision Regret for the public User Squad; defer transfer-plan regret until this passes.

## Consequences
Do not reuse FPL next-round availability across the Planning Horizon or treat unobserved injuries/suspensions as excluded historical fixtures. Component attribution must form an exact official scoring ledger; Defcon comes from its recorded event count, never a points residual. No third-party xP/xMins feed is ingested.
