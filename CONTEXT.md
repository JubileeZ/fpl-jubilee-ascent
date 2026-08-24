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

**Price**:
A Player's current FPL purchase value in £m.
_Avoid_: cost, now_cost, value

**Raw Cache**:
Raw JSON responses from the FPL API stored in `data/raw/`. Used as a rate-limit shield.
_Avoid_: Cache, historical data

**Projection**:
A per-player per-gameweek expected points (xP) and expected minutes (xMins) estimate produced by a model. Solver projections aggregate all Fixture Projections in the gameweek.
_Avoid_: xP output, prediction, score

**Fixture Projection**:
A per-player per-fixture expected points and minutes estimate. Canonical model output grain; retains fixture identity for double gameweeks.
_Avoid_: fixture score

**Club Fixture**:
A Fixture occurring while a Player is registered with the participating Club. Used as the Participation State training denominator; excludes fixtures before a transfer-in or after a transfer-out.
_Avoid_: Eligible game, season fixture

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
Lookahead of 1–5 gameweeks (default 5) for Transfer Plan and Ownership Explorer, starting at the next gameweek whose deadline has not passed, clipped at GW38. A deadline-passed gameweek is excluded even if unfinished.
_Avoid_: Optimization length, gameweek plan, First-Half Horizon, default 6, 3–8 window, locked gameweek, including the live unfinished GW after deadline

**First-Half Horizon**:
Research window GW1–19 covering Set 1 chips. Not a Planning Horizon. Not the product Ownership Explorer ranking band.
_Avoid_: Planning Horizon, full-season, GW1–6 Canonical window

**Second-Half Horizon**:
Research window GW20–38 covering Set 2 chips. Not a Planning Horizon. Not the product Ownership Explorer ranking band.
_Avoid_: Planning Horizon, rest of season, second half (unbounded)

**Full-Season Window**:
Research window GW1–38. First-Half Horizon plus Second-Half Horizon. Not a Planning Horizon. Not the product Ownership Explorer ranking band.
_Avoid_: Planning Horizon, season horizon

**Season Window**:
Research ranking band: First-Half Horizon, Second-Half Horizon, or Full-Season Window. Not the product Ownership Explorer ranking band.
_Avoid_: Planning Horizon, Horizon (ambiguous)

**Score Mode**:
Research slice: All Projection, Realized Points, or Remaining Projection. Not a product Ownership Explorer control.
_Avoid_: xP mode, results toggle, horizon mode, product Explorer toggle

**All Projection**:
Score Mode summing Gameweek Projection xP for every gameweek in the Season Window, including finished weeks. Not the product Explorer total.
_Avoid_: Remaining Projection, Realized Points, hybrid total, Planning Horizon total

**Realized Points**:
Score Mode summing official FPL total_points over finished gameweeks in the Season Window. Not xP. Not a product Explorer mode.
_Avoid_: Projection, Remaining Projection, xP

**Remaining Projection**:
Score Mode summing Gameweek Projection xP over unfinished gameweeks in the Season Window. Not the product Planning Horizon slice.
_Avoid_: All Projection, rest-of-season (unbounded), Realized Points

**Projected Rate**:
Planning Horizon xP divided by (Σ expected minutes / 90). Cameo minutes do not reduce this number. Ownership Explorer Y-axis option.
_Avoid_: xP per game, Event Rate, Per-90 average, Season Window rate

**xP per Gameweek**:
Planning Horizon xP divided by gameweek count in that horizon. Ownership Explorer Y-axis option.
_Avoid_: xP per game, per-match xP, average points, Season Window average

**Event Component**:
A decomposed scoring input (minutes, goals, assists, clean sheets, goals_conceded, saves, bonus, cards, penalty events) used by a component model to reconstruct a Projection via the FPL scoring matrix, rather than predicting total points directly.
_Avoid_: Feature, sub-stat

**Event Rate**:
A per-90-minutes estimate of how often a Player produces a given Event Component, seeded from prior-season per-fixture history and blended into current-season data as the season progresses.
_Avoid_: Per-90 average, rate (ambiguous)

**Appearance Probability**:
The likelihood a Player features in a fixture, taken from the FPL API `chance_of_playing_next_round` when present, else from prior-season appearance rate.
_Avoid_: Injury chance, playing chance

**Participation State**:
One mutually exclusive fixture outcome for a Player: Did Not Play, Start, or Sub-in. State probabilities sum to one and determine conditional minutes and Event Component projections.
_Avoid_: Appearance Probability (only whether a Player features), lineup status, Expected Role

**Expected Role**:
Club-relative preseason judgment of how a Player is expected to be used over the early-season band (GW1–5). Five values: Nailed Starter, Regular Starter, Rotation, Cameo, Out of Contention. Seeds Participation State priors and Draft eligibility; only Nailed Starter and Regular Starter are Draft-eligible. Dated Research Note snapshot. Method: Dual-Source Lineup Signals plus conflict rules and Expected Role Priors. Concrete websites are replaceable adapters (currently FFS Team News and FPL Meerkat).
_Avoid_: First team, nailed, importance, lineup status, Participation State, GW1-only XI, full-season average, treating a source URL as the method

**Nailed Starter**:
Expected Role for a Player who is near-certain to Start when fit.
_Avoid_: Locked starter, guaranteed starter

**Regular Starter**:
Expected Role for a Player who is the default starter most weeks when fit, with occasional benchings.
_Avoid_: Preferred starter, first choice (ambiguous with Nailed Starter)

**Rotation**:
Expected Role for a Player who contends for starts and shares minutes with others; not Draft-eligible.
_Avoid_: Squad player, fringe starter

**Cameo**:
Expected Role for a Player who mostly sits on the bench or enters as a late Sub-in; not Draft-eligible.
_Avoid_: Impact sub, bench option

**Out of Contention**:
Expected Role for a Player unlikely to feature meaningfully; not Draft-eligible.
_Avoid_: Not play, discarded, out of squad

**Expected Role Prior**:
Default Participation State probabilities and conditional minutes attached to an Expected Role. Feature Contract Cold-Start minutes prior. Applied to fit Players; per-Player overrides only when sources clearly diverge from the tier default.
_Avoid_: Hand-tuned minutes for every Player, Appearance Probability, Prior-Season Seed minutes

**XI Contention Set**:
Players with a realistic Start or Sub-in path in the Expected Role horizon (Nailed Starter, Regular Starter, Rotation, and notable Cameo challengers). Research grain for role assignment; Draft shortlist is the Nailed + Regular subset.
_Avoid_: Entire price list, first team (ambiguous), full squad dump

**Draft Shortlist**:
Per-Club list of fit-role Draft-eligible Players (Nailed Starter and Regular Starter only) derived from the XI Contention Set. Current availability is applied separately before selecting a Gameweek squad.
_Avoid_: First team, starter XI, projected lineup, current available list

**Draft Availability**:
Date-stamped overlay applied after Expected Role assignment: Eligible, Watch, Exclude GW1, or Exclude GW1–5. Does not change fit-role label. Feature Contract applies these overlays at Cold-Start. Availability Override wins when present; API chance still caps. Scoring: Watch multiplies $p_{\text{start}}$ by 0.70 for GW1–5 (cut mass → $p_{\text{dnp}}$); Exclude GW1 zeros GW1 only; Exclude GW1–5 zeros GW1–5 only (GW6 uses fit-role priors).
_Avoid_: Draft eligibility, Expected Role, injury status, treating Watch as annotation-only

**Role Evidence**:
Per-Player attribution for an Expected Role assignment: stated reason, source references, conflict rule applied, and confidence. Required on every XI Contention Set row so the User can audit logic.
_Avoid_: Bare Role label, unexplained override

**Dual-Source Lineup Signals**:
Two inputs to Expected Role conflict rules: a predicted XI per Club, and a nailed-starter marker set. Not a website, URL, or HTML layout. Adapters extract these signals; if a site moves or dies, replace the adapter, keep the signals and rules. Committed extract (club → XI names + nailed set) is the derivation pin; raw HTML is optional.
_Avoid_: FFS scrape, Meerkat URL, HTML snapshot as the method

**Expected Role Table**:
Machine-readable companion to the Expected Role Research Note. One row per XI Contention Set Player with Expected Role, Expected Role Prior fields (or overrides), confidence, Role Evidence, API availability fields, registration status, and Draft Availability. Carries the FPL season it belongs to. Feature Contract reads this table at Cold-Start; never scrapes. Refuses to build if the table is missing or its season is not the current season. Players absent from the table take the Out of Contention Expected Role Prior. Does not replace live Availability Override. Updates only via Expected Role Rebuild, then commit.
_Avoid_: Research Note prose alone, solver projection CSV, live scrape at projection time, implicit refresh inside data ingest, previous-season table as this season's prior

**Expected Role Rebuild**:
Explicit Stage 1 run that writes a new Expected Role Table and Dual-Source Lineup Signals extract from current adapters. Never runs at projection time. When data refresh runs and the table is missing or belongs to another season: ask rebuild vs defer. Rebuild writes this season's table. Defer still refreshes FPL API data; Feature Contract / Champion / solver / dashboard refuse until a this-season table exists. In-season refresh with a current-season table does not ask.
_Avoid_: Silent scrape on `refresh_data`, dashboard export scrape, reusing last season's table, nagging every Cold-Start refresh of the same season

**Minutes if Appearance**:
The expected minutes for a Player conditional on making an appearance, distinct from their Appearance Probability. Cold-Start value comes from Expected Role Prior; current-season value from realized minutes.
_Avoid_: Average minutes, expected minutes

**Availability Override**:
An explicit, source-attributed and time-limited adjustment to a Player's expected availability or minutes when the FPL API has not yet reflected confirmed information.
_Avoid_: Expert guess, manual prediction

**Availability Snapshot**:
A time-stamped record of Player availability captured before a Gameweek deadline. Used to evaluate Availability and xMins without future-information leakage.
_Avoid_: Current status, injury history

**Cold-Start**:
The state at the start of a new season where current-season Player performances are empty. Event Rates seed from Prior-Season Seed or fallback priors. Participation State and conditional minutes seed from Expected Role Prior.
_Avoid_: Preseason (ambiguous), blank season

**Appearance Blend**:
Linear mix of Cold-Start prior and current-season observation by that Player's current-season appearance count. Weight stays 0 through 1 appearance, then ramps to 100% current-season at 5 appearances. One clock for Event Rates and minutes. Not a calendar Gameweek switch.
_Avoid_: GW5 flip, dashboard-only minutes mix, two clocks, blend_start 3 / blend_full 8

**Prior-Season Seed**:
Per-Player Event Rates from the most recent archived season (`data/archive/<prev-season>/processed/`) to seed Projections during Cold-Start. A summer club change does not discard a usable seed. Not the Cold-Start minutes prior.
_Avoid_: Carryover, history seed, three-season FPL blend, Expected Role Prior

**Career Individual Rate**:
Per-90 xG, xA, Defcon, and GK saves from a Player's last completed senior league season. Used only when no usable Prior-Season Seed exists (foreign arrivals, promoted-Club Players, rookies).
_Avoid_: Position-Price Prior, three-season foreign blend, treating any summer transfer as a newcomer

**Destination Team Concede Rate**:
Destination Club's prior-season Premier League goals conceded per game. Supplies the Team Defensive Event λ for Players with no Prior-Season Seed. Clubs with no PL archive use that season's PL league-average concede rate.
_Avoid_: Player-level GC for newcomers, Championship GC as PL λ, opponent xG as the seed

**Position-Price Prior**:
A league-wide aggregate of Event Rates grouped by Position and price band, used as the production fallback for Players with no Prior-Season Seed (new signings, promoted-Club Players, rookies).
_Avoid_: Default rate, baseline prior, Career Individual Rate

**Player Code Mapping**:
The cross-season identity resolution technique that links transient annual FPL element `id` values across seasons using the immutable FPL `code` field (with name/position fallback).
_Avoid_: ID matching, element_id join

**Usable Season**:
A FPL season-year whose minutes meet the 450 floor (same as Prior-Season Seed). Research Stage 2 Cold-Start uses only the latest archive season; older FPL years are not blended. Thin or missing latest years are not a seed.
_Avoid_: Dual-floor 50/50 blend, any-minutes season, treating injury season as automatic latest prior

**Research Position Baseline**:
Position-only aggregate Event Rates used by preseason Stage 2 when a Player has no usable Prior-Season Seed and no Career Individual Rate package. Distinct from production Position-Price Prior (position × price band).
_Avoid_: Position-Price Prior, Prior-Season Seed, Career Individual Rate

**Position-Price Fallback Prior**:
Position- and price-band aggregate Event Rates used in production Cold-Start when a Player has no usable Prior-Season Seed.
_Avoid_: Prior-Season Seed, default rate, Research Position Baseline, Career Individual Rate

**Defensive Contribution (Defcon)**:
The FPL metric tracking defensive actions (clearances, blocks, interceptions, tackles, recoveries) used to evaluate position-specific defensive contribution thresholds for bonus/points. CBIT (clearances + blocks + interceptions + tackles) for DEF threshold 10; CBITR (+ recoveries) for MID/FWD threshold 12.
_Avoid_: Tackles, defensive stat, work rate, raw foreign defensive actions

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
A model abstraction treating goals conceded and clean sheets as team-level properties of the opponent's expected attack, scaled to individual players via minutes exposure. Cold-Start Players with no Prior-Season Seed take Destination Team Concede Rate as the club λ.
_Avoid_: Per-player goal conceded rate, individual clean sheet rate

**Dashboard Data Contract**:
Exported player metadata, historical rates, and per-gameweek Event Component projections for Transfer Plan and Ownership Explorer over the Planning Horizon. Not the Transfer Plan JSON.
_Avoid_: UI state, solver export, Full-Season Window as the product slice

**Interactive Squad Builder**:
Retired product surface. Not a dashboard tab. A sandbox 15 is not a product object. Pitch on Transfer Plan shows the User Squad and plan weeks only.
_Avoid_: Roster picker, drag list, live tab name, treating the pitch as a draft sandbox

**Transfer Plan**:
The sole 15-player product surface. MILP result over a Planning Horizon: per-gameweek User Squad, lineup, transfers in and out, free transfers, hits, Force Keep, Force Ban, Booked Chips, and Enabled Chips. Always scored with the Model Champion on Official Fixture Difficulty. Starting 15 is the live User Squad when it exists, otherwise a preseason draft. Not Ownership Explorer, not Canonical Preseason Chip Path, not a sandbox 15.
_Avoid_: team plan, MILP squad, Load MILP Squad, research chip path, Dual-Vector xP, Squad Builder

**Force Keep**:
User override. A Player who must be in that gameweek’s scoring 15 (Free Hit 15, Wildcard 15, or the owned 15). Specified per gameweek in the Planning Horizon. Owned or unowned (unowned is a forced buy). Hits are allowed; an infeasible Keep fails the solve. Not FPL deadline freeze of a passed gameweek. Not the rolled 15 under a Free Hit.
_Avoid_: lock, locked, deadline lock, preference pin, requiring Keep in the FH backing 15

**Force Ban**:
User override. A Player who must not be in that gameweek’s scoring 15. Owned: must leave that gameweek and may return later. Unowned: do not buy that gameweek. Hits are allowed; an infeasible Ban fails the solve.
_Avoid_: lock, exclude, availability flag as a projection edit

**Chip Set**:
One of two identical chip inventories per season. Set 1 is GW1–19 and expires unused at the GW19 deadline. Set 2 is GW20–38 and is a fresh inventory; spending a Set 1 chip does not consume the Set 2 copy.
_Avoid_: season chips, one BB per season, carrying unused Set 1 chips into GW20

**Available Chip**:
A chip still unspent in one Chip Set. Booked Chip and Enabled Chip are offered per Chip Set, not once per season. On a Planning Horizon that includes both GW19 and GW20, Set 1 and Set 2 copies of the same chip are two Available Chips if unspent. Preseason / no User Squad: all Set 1 chips are available.
_Avoid_: enabling a spent chip, treating Set 1 spend as blocking Set 2, one BB toggle across a GW19/GW20 straddle

**Booked Chip**:
A chip forced on one specific gameweek in the Planning Horizon, chosen from Available Chips. That gameweek must belong to the Chip Set of that Available Chip. At most one chip per gameweek. Distinct from Enabled Chip.
_Avoid_: Enabled Chip, Canonical chip path, playing two chips in one gameweek

**Enabled Chip**:
A chip the user intends to play once in this Planning Horizon without pinning the week, chosen from Available Chips. The solver must place it on a gameweek in that Chip Set that has no Booked Chip. Default is none enabled; the solver does not invent chips. Enabling Set 1 BB and Set 2 BB is two Enabled Chips.
_Avoid_: Booked Chip, optional chip, enabling all four by default, Canonical chip path, one BB for a straddle horizon

**Solver Objective**:
The decayed quantity the MILP maximises over the Planning Horizon. Distinct from undiscounted Gameweek Projection xP shown per week on the Transfer Plan.
_Avoid_: xP, score, total_xp, research total_6gw_xp

**Mix**:
Unordered set of 1–5 Players scored as one bundle: sum Price, each Gameweek Projection in the Planning Horizon, and horizon total. Mix vs Mix requires the same size (1 vs 1, 2 vs 2, 3 vs 3). Same position is not required. A Player occupies at most one Mix. View-only: a Mix does not Force Keep, Force Ban, or Re-solve. Not a Transfer Plan, not a legal 15.
_Avoid_: combo, package, alternative 15, differential, solver squad, Plan this Mix, same Player in both Mixes, Mix order

**Mix Member**:
A Player occupying Mix A or Mix B, never both. Distinct from highlighting a Player in Ownership Explorer.
_Avoid_: selected player, overlapping Mix occupancy

**Ownership Explorer**:
Dashboard view ranking Feature Contract Players on the Planning Horizon, with Mix vs Mix, per-GW xP columns, and linked ownership and price charts. Same Feature Contract, Model Champion, and Official Fixture Difficulty as the solver. Not Transfer Plan. Not a Season Window ranking.
_Avoid_: Ownership Value Explorer (research HTML), 3D scatter, First-Half Horizon as the product band, Dual-Vector explorer xP

**Decision Regret**:
Actual-point gap between a decision made from Projections and the best legal hindsight alternative under identical constraints. Initial scope: one-Gameweek starting XI, bench order, captain, and vice-captain.
_Avoid_: Squad Gap (ambiguous), optimizer gap

**Model Champion**:
The currently selected operational Projection Model, retained as the primary comparator for historical and live evaluation.
_Avoid_: Default model, production model

**Model Candidate**:
A Projection Model evaluated against the Model Champion. At most two Candidates may be tracked concurrently, making a three-model comparison including the Champion.
_Avoid_: Experimental model, challenger

**Primary Projection Model**:
The active model selected in the dashboard to drive Ownership Explorer ranking and Mix scores. Defaults to the Model Champion. Does not select the Transfer Plan datasource; that is always the Model Champion.
_Avoid_: Active UI model, pitch model, MILP model

**Secondary Comparison Model**:
Retired with Interactive Squad Builder. Overlay xP/Diff columns are not a product control. Ownership Explorer uses the Primary Projection Model only. Transfer Plan is always the Model Champion.
_Avoid_: Compare model, overlay model, Compare Models checkbox

**Decision-First Evaluation**:
Model comparison hierarchy that prioritizes Decision Regret, falls back to xP MAE when Decision Regret is unavailable, and treats xMins MAE, bias, and rank correlation as guardrails.
_Avoid_: Prediction-only evaluation, aggregate score

**Historical Promotion Gate**:
A Candidate may replace the Model Champion only after winning the combined prior-season evaluation and at least two of its Cold-Start, early/mid-season, and late-season segments while matching or improving every Champion guardrail.
_Avoid_: One-off backtest win, aggregate-only promotion

**Incremental Promotion**:
A Candidate that passes the Historical Promotion Gate becomes the Model Champion even for a small primary-metric improvement; the former Champion remains in the comparison slate for live validation and rollback.
_Avoid_: Margin threshold, discard previous model

**Provisional Historical Promotion**:
An Incremental Promotion supported only by archive data without verified pre-deadline snapshots. It remains provisional until two Live Validation Windows provide current-season evidence.
_Avoid_: Validated promotion, snapshot-backed promotion

**Live Validation Window**:
A rolling four-Gameweek comparison of the Model Champion and up to two Candidates using predictions captured from the same pre-deadline inputs.
_Avoid_: Single-Gameweek validation, live test

**Live Reassessment**:
A Live Validation Window confirms or challenges a Champion but cannot switch it automatically. A material loss triggers user review, a new Historical Promotion Gate evaluation, or a second live window.
_Avoid_: Automatic live promotion, weekly model switching

**Meaningful Live Lead**:
At least a 5% primary-metric advantage over a Live Validation Window while matching the Model Champion's guardrails. Smaller leads are unclear and leave the comparison slate unchanged.
_Avoid_: Single-week win, automatic promotion threshold

**Candidate Admission**:
When the three-model comparison slate is full, a new Model Candidate enters only by passing the Historical Promotion Gate against an existing Candidate, which it replaces. The Model Champion is retained.
_Avoid_: Unbounded experiment list, Champion replacement by admission

**Automatic Historical Promotion**:
An evaluation job triggered by Candidate code changes updates the committed Model Champion configuration and preserves its evidence report whenever a Candidate passes the Historical Promotion Gate. Routine model reports do not mutate selection state.
_Avoid_: Manual promotion, silent report-side effect

**Candidate Registration**:
An explicit committed addition of a Model Candidate to the comparison slate. Registration enables automatic evaluation and promotion but does not itself change the Model Champion.
_Avoid_: Model auto-discovery, implicit admission

**Comparison Slate**:
The Model Champion plus zero to two registered Model Candidates. It starts with `participation_state_hybrid` as Champion and `metrics_component_hybrid` as its sole Candidate.
_Avoid_: All models, model pool

**Promotion Evidence Record**:
Versioned JSON and Markdown artifacts that identify evaluated models and commits, evaluation windows and snapshot coverage, primary and guardrail metrics, promotion outcome, and resulting Comparison Slate.
_Avoid_: Backtest log, undocumented promotion

**Research Note**:
Durable human-readable analysis under `docs/research/<topic-slug>/` (note + companion CSV/HTML in that folder). Archive by moving the whole folder to `docs/archive/<topic-slug>/`.
_Avoid_: Scratch investigation, dated filename

**Updated**:
Last revision timestamp for a Research Note, formatted as ISO 8601 with timezone.
_Avoid_: Data stamp, duplicate Last update field

**Data Stamp**:
Freshness cutoff for source or dataset evidence used by a Research Note.
_Avoid_: Updated timestamp, publication date when evidence cutoff differs

**Source Synthesis**:
Direct summary of external source claims without upgrading them to independently validated facts.
_Avoid_: Project interpretation, verified finding

**Project Interpretation**:
Project-specific translation of findings into conditional decision rules, kept separate from Source Synthesis.
_Avoid_: Source claim, independent validation

**Research Source Directory**:
Research Note mapping related source pages to child notes, freshness, scope, and source gaps; not substitute for child evidence.
_Avoid_: Merged research report, complete source transcription

**Calibrated Component Architecture**:
Bottom-up expected points ($xP$) modeling derived from explicit underlying per-90 player skill rates (`per90_xg`, `per90_xa`, `per90_defcon`, `per90_saves`) multiplied by venue-adjusted team/opponent strength vectors and projected minutes. Goals/assists use `attack_multiplier`. Clean sheets, conceded, saves, and defcon use `defence_multiplier`. Missing or zero Club Strength Vector attack/defence → Official FDR fallback in `_fixture_maps`.
_Avoid_: Top-down power rating, single composite score xP prediction

**Official Fixture Difficulty**:
Per-club-fixture integer 1–5 on `team_h_difficulty` / `team_a_difficulty`. In 2026/27 it equals the opponent Club Strength Vector overall at the focal venue (home FDR = opponent `strength_overall_home`; away FDR = opponent `strength_overall_away`). Not a blend of attack and defence.
_Avoid_: Dual-Vector Strength, Club Strength Vector, treating API strength as a finer FDR

**Club Strength Vector**:
Official API club fields `strength`, `strength_overall_home/away`, `strength_attack_home/away`, `strength_defence_home/away`. Live 2026/27: `strength` null, attack/defence all 0, overall already the 2–5 Official Fixture Difficulty ticks.
_Avoid_: Dual-Vector Strength, FDR, Elo-style 1000-scale ratings (prior-season archive only)

**Dual-Vector Strength**:
Match-level team attack and opponent defense strength multipliers derived from 10-match rolling non-penalty xG (Team Attack) and xGA (Team Defense) scaled against league averages, falling back to Official Fixture Difficulty only when data is sparse. Not implemented in production Python; not the API Club Strength Vector.
_Avoid_: Static FDR multiplier, single team rating, API `strength_*`, Prior-Season Dual-Vector Seed

**Prior-Season Dual-Vector Seed**:
Cold-Start Dual-Vector Strength from the latest archive season: club attack = sum of player `expected_goals` per club-fixture; club defence = that fixture’s `expected_goals_conceded` (one team value, not summed across players); home/away split; scaled to league average. Promoted Clubs use league average. FPL-xG proxy, not npxG. Live research xP for Canonical Preseason Chip Path (Stage 3) and First-Half Chip Path. Also research DCS effective FDR (`defence_multiplier × 3`).
_Avoid_: Dual-Vector Strength (live rolling npxG), Club Strength Vector, Official Fixture Difficulty, FDR-xP Canonical

**Recency-Weighted Prior Shrinkage**:
Event Rate estimation method blending a multi-season prior with exponential recency decay over recent matches (e.g. 10 appearances) and applying Bayesian shrinkage for sample-constrained / low-minute players.
_Avoid_: Simple unweighted current-season average, static role rates

**Defensive Composite Score (DCS)**:
A 0–100 ranking of a Defensive Rotation Set: 60% opportunity-cost-adjusted rotated expected points plus 40% fixture-risk (zero-difficult weeks, rotated FDR, schedule correlation). Live research ranking uses Prior-Season Dual-Vector Seed effective FDR (`defence_multiplier × 3`).
_Avoid_: RQI, OC-RQI, Rotation Quality Index

**Defensive Rotation Set**:
A goalkeeper pair, five-defender set, or seven-asset backline ranked by DCS. Distinct from the Canonical Preseason Chip Path 15-man squad (including its keepers).
_Avoid_: GKP pick (ambiguous vs squad keepers), the defensive squad, RQI pair

**Opportunity-Cost Adjusted Score (OC-Score)**:
Weekly rotated expected points minus the outfield shadow price $\gamma$ times spend above the position floor (GKP £8.5m, DEF £20.0m, backline £28.5m). Points factor inside DCS, not a separate ranking metric.
_Avoid_: OC-RQI, net value, RQI points term

**Canonical Preseason Chip Path**:
Live GW1–6 research plan: Bench Boost GW1, locked transfers GW1–3, Wildcard GW4, roll GW5 free transfer, enter GW6 with four banked Free Transfers. Scored on Prior-Season Dual-Vector Seed. Stage 3 publishes this path only. 15-man keepers are a MILP squad pick, not a DCS pair. Path identity is `gw1-6_wc4_summary.csv` `total_6gw_xp`, not a numeric snapshot.
_Avoid_: S13, 16-scenario matrix, Chip Exploration Matrix, BB2 + TC3 + WC4 as current optimum, First-Half Chip Path, Operational First-Half Plan, FDR-xP Canonical, treating xP literals as path identity

**First-Half Chip Path**:
Sibling GW1–19 research plan under `docs/archive/gw1-19-first-half-chip-path/`. Bench Boost GW1; two published Wildcard calendars (GW3 and GW4); Free Hit and Triple Captain forced in any week except GW1 and the Wildcard week; pre-WC and Wildcard 15s skip the Free Hit week in their objective; post-WC greedy Free Transfers, zero hits; greenfield Draft 15. Same Prior-Season Dual-Vector Seed as Canonical. Headline metric = undiscounted Total xP. Does not replace Canonical chip calendar (no FH/TC in Stage 3; horizon stays GW1–6).
_Avoid_: Canonical Preseason Chip Path, Operational First-Half Plan, S13, spending Set 2 chips before GW20, writing Dual-Vector Strength into production builder

**Operational First-Half Plan**:
Locked user GW1–19 playbook under `docs/archive/gw1-19-operational-plan/`. Same pre-WC 15 as Canonical and First-Half WC4; First-Half Wildcard rebuild 15; chips BB1, WC4, FH12, TC17; bank-state Free Transfer hurdles; frozen XI (no greedy FT CSV). FH12 15 rebuild at deadline. Path identity is `operational_summary.csv` `frozen_19gw_xi_xp`, not First-Half `total_19gw_xp` or Canonical `total_6gw_xp`.
_Avoid_: Canonical Preseason Chip Path, First-Half Chip Path, treating `first_half_transfers.csv` as this playbook, DCS keepers as the owned pair

**Set-Piece Hierarchy**:
Ordered ranking of designated set-piece takers (corners left/right, direct free-kicks, indirect free-kicks, penalties) per Club.
_Avoid_: Set-piece list, dead-ball taker (ambiguous)

**Inswinging Corner Preference**:
Tactical distribution of left-footed vs right-footed corner delivery from respective flanks (2025/26 Premier League meta: 83% inswingers).
_Avoid_: Corner curve, foot preference

**Set-Play Target xG**:
Non-penalty expected goals generated from set-piece deliveries for box aerial targets and first contacts.
_Avoid_: Set-piece goal threat, header xG

**Set-Piece Net Swing**:
Club-level goal differential between non-penalty dead-ball goals scored and conceded, driven by specialized set-piece coaching staff.
_Avoid_: Set-piece differential, dead-ball swing




