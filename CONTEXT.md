# FPL-Jubilee-Ascent

FPL analytics and optimization engine for a single user. Ingests live FPL API data, engineers predictive features, generates per-player per-gameweek expected points (xP) projections, and solves for the optimal squad and transfer plan.

## Language

**User Squad**:
The user's specific 15-player Fantasy Premier League squad. Keyed by `entry_id`.
_Avoid_: Manager team, FPL team, team, manager_id

**Club**:
A real-world Premier League club (e.g. Arsenal, Liverpool). Keyed by `team_id` or `club_id`. Maps to `team` in the FPL API.
_Avoid_: Team (in domain model context)

**Position**:
A player's general pitch role (Goalkeeper, Defender, Midfielder, Forward). Maps to `element_type` in the FPL API.
_Avoid_: position (used as lineup index)

**Lineup Index**:
The squad slot/lineup position within the User Squad (integer 1 to 15, e.g. starting GK is 1, bench GK is 12). Maps to `position` in the FPL `/my-team/` endpoint picks.
_Avoid_: position_id, player position

**Player**:
A Premier League footballer available for selection. Maps to `element` in the FPL API.
_Avoid_: Element, asset

**Raw Cache**:
Raw JSON responses from the FPL API stored in `data/raw/`. Used as a rate-limit shield.
_Avoid_: Cache, historical data

**Projection**:
A per-player per-gameweek expected points (xP) and expected minutes (xMins) estimate produced by a model. Solver projections aggregate all Fixture Projections in the gameweek.
_Avoid_: xP output, prediction, score

**Fixture Projection**:
A per-player per-fixture expected points and minutes estimate. Canonical model output grain; retains fixture identity for double gameweeks.
_Avoid_: fixture score

**Gameweek Projection**:
A per-player per-gameweek aggregation of one or more Fixture Projections used by the solver and headline evaluation.
_Avoid_: weekly fixture

**Feature Contract**:
The strictly defined schema of engineered inputs passed to any projection model.
_Avoid_: Raw features, model inputs

**Model Adapter**:
A standardized interface that wraps any projection model, accepting a Feature Contract and outputting projections.
_Avoid_: Core model, custom model logic

**Planning Horizon**:
The configurable lookahead window (3-8 gameweeks) used by the MILP solver to optimize transfer strategy and team selection.
_Avoid_: Optimization length, gameweek plan

**Event Component**:
A decomposed scoring input (minutes, goals, assists, clean sheets, goals_conceded, saves, bonus, cards, penalty events) used by a component model to reconstruct a Projection via the FPL scoring matrix, rather than predicting total points directly.
_Avoid_: Feature, sub-stat

**Event Rate**:
A per-90-minutes estimate of how often a Player produces a given Event Component, seeded from prior-season per-fixture history and blended into current-season data as the season progresses.
_Avoid_: Per-90 average, rate (ambiguous)

**Appearance Probability**:
The likelihood a Player features in a fixture, taken from the FPL API `chance_of_playing_next_round` when present, else from prior-season appearance rate.
_Avoid_: Injury chance, playing chance

**Minutes if Appearance**:
The expected minutes for a Player conditional on making an appearance, distinct from their Appearance Probability.
_Avoid_: Average minutes, expected minutes

**Availability Override**:
An explicit, source-attributed and time-limited adjustment to a Player's expected availability or minutes when the FPL API has not yet reflected confirmed information.
_Avoid_: Expert guess, manual prediction

**Cold-Start**:
The state at the start of a new season where current-season Player performances are empty and Event Rates must be seeded entirely from prior-season history or fallback priors.
_Avoid_: Preseason (ambiguous), blank season

**Prior-Season Seed**:
Per-Player Event Rates and minutes carried over from the most recent archived season (`data/archive/<prev-season>/processed/`) to seed Projections during Cold-Start.
_Avoid_: Carryover, history seed

**Position-Price Fallback Prior**:
Position- and price-band aggregate Event Rates used when a Player has no usable Prior-Season Seed.
_Avoid_: Prior-Season Seed, default rate

**Position-Price Prior**:
A league-wide aggregate of Event Rates grouped by Position and price band, used as the fallback for Players with no Prior-Season Seed (new signings, promoted-Club Players, rookies).
_Avoid_: Default rate, baseline prior

**Player Code Mapping**:
The cross-season identity resolution technique that links transient annual FPL element `id` values across seasons using the immutable FPL `code` field (with name/position fallback).
_Avoid_: ID matching, element_id join

**Defensive Contribution (Defcon)**:
The FPL metric tracking defensive actions (clearances, blocks, interceptions, tackles, recoveries) used to evaluate position-specific defensive contribution thresholds for bonus/points.
_Avoid_: Tackles, defensive stat, work rate

**BPS Bonus Model**:
A statistical or regression model mapping projected Bonus Points System (BPS) totals from event components into expected bonus points (0, 1, 2, or 3).
_Avoid_: Bonus guess, bonus score

**Two-Stage Empirical Bayes GLM**:
An event-level regression fitting a league-wide baseline GLM with a log-minutes offset in Stage 1, and applying Empirical Bayes shrinkage to player-level residuals based on fixture sample size in Stage 2.
_Avoid_: Per-player regression, unregularized OLS

**Defcon Pearson Dispersion**:
A runtime diagnostic measuring the Pearson chi-square statistic on defensive action residuals to dynamically select between Poisson, Negative Binomial, and quasi-Poisson distributions.
_Avoid_: Fixed distribution, arbitrary variance scaling

**Team Defensive Event**:
A model abstraction treating goals conceded and clean sheets as team-level properties of the opponent's expected attack, scaled to individual players via minutes exposure.
_Avoid_: Per-player goal conceded rate, individual clean sheet rate


