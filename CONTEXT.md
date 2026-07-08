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
A per-player per-gameweek expected points (xP) and expected minutes (xMins) estimate produced by a model.
_Avoid_: xP output, prediction, score

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

**Cold-Start**:
The state at the start of a new season where current-season Player performances are empty and Event Rates must be seeded entirely from prior-season history or fallback priors.
_Avoid_: Preseason (ambiguous), blank season

**Prior-Season Seed**:
Per-Player Event Rates and minutes carried over from the most recent archived season (`data/archive/<prev-season>/processed/`) to seed Projections during Cold-Start.
_Avoid_: Carryover, history seed

**Position-Price Prior**:
A league-wide aggregate of Event Rates grouped by Position and price band, used as the fallback for Players with no Prior-Season Seed (new signings, promoted-Club Players, rookies).
_Avoid_: Default rate, baseline prior
