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

**Starting Shape**:
DEF–MID–FWD counts in one Gameweek's starting XI (always 1 GKP). Legal bounds: 3–5 DEF, 2–5 MID, 1–3 FWD. A per-Gameweek lineup property. Distinct from the 15, which is always 2 GKP / 5 DEF / 5 MID / 3 FWD.
_Avoid_: formation (season-long), squad structure, 15 shape

**Locked Starting Shape**:
Research constraint: every Gameweek in a Season Window must use one Starting Shape. Ablation against unconstrained legal XI in Transfer Plan Walk-Forward.
_Avoid_: formation, squad shape

**Player**:
A Premier League footballer available for selection. Maps to `element` in the FPL API.
_Avoid_: Element, asset

**Price**:
A Player's current FPL purchase value in £m.
_Avoid_: cost, now_cost, value

**Raw Cache**:
Raw JSON responses from the FPL API stored in `data/raw/`. Live working copy; not git-tracked.
_Avoid_: Cache, historical data, Season Archive

**Season Archive**:
Git-tracked Official FPL capture for one season-year under `data/archive/<YYYY-YY>/` (raw JSON plus processed parquet). Deadline or on-demand pin. Durable backup and historical replay material. Not live Raw Cache. Not Research Note companions.
_Avoid_: gitignoring archive, committing live Raw Cache on every refresh, treating vaastav live pull as the archive method

**Operational Dataset**:
Production Player, Club, Fixture, and performance tables. Official FPL API responses plus Season Archives of those responses only.
_Avoid_: Dual-Source websites, FBref, Understat, live vaastav pull, editorial XI as Feature Contract input

**Research-Only Evidence**:
Third-party or editorial numbers allowed in a Research Note. May justify a frozen constant. Must not feed Feature Contract, Raw Cache, Season Archive ingest, or Model Champion inputs.
_Avoid_: FBref client in production, Understat parquet as Event Rates, Dual-Source scrape as xMins

**Projection**:
A per-player per-gameweek expected points (xP) and expected minutes (xMins) estimate produced by a model. Solver projections aggregate all Fixture Projections in the gameweek.
_Avoid_: xP output, prediction, score

**Fixture Projection**:
A per-player per-fixture expected points and minutes estimate. Canonical model output grain; retains fixture identity for double gameweeks.
_Avoid_: fixture score

**Club Fixture**:
A finished Fixture while a Player is registered with the participating Club. Training denominator for Participation State and Event Rates. Excludes fixtures before a transfer-in or after a transfer-out. Missing history and Incomplete History Rows are not Club Fixtures and are not Did Not Play.
_Avoid_: Eligible game, season fixture, padded DNP, this-season fixture at a previous Club, live or future 0-minute history as DNP

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
Inclusive Gameweek window [Horizon Start, Horizon End] for Ownership Explorer ranking and Mix scores. Length 1–6 (default 6 when enough unfinished weeks remain: End = min(Start+5, 38)). Horizon Start is any unfinished Gameweek (`finished=false`) from the earliest unfinished through GW38; live deadline-passed week allowed; finished weeks cannot be Start. Default Start = earliest unfinished. A live unfinished Gameweek uses the full Gameweek Projection (no in-play trim). Clipped at GW38. Not First-Half Horizon, Full-Season Window, or Score Mode. CLI `commands.solve --target_gw` is Horizon Start; `--horizon` is length; clamp 1–6. Start/End in the dashboard re-slices the Full-Season export; it does not re-project.
_Avoid_: Optimization length, 1–5 from is_next, default 5, excluding the live unfinished GW after deadline, Season Window ranking, Realized Points / All Projection in product Explorer, in-play remaining-fixtures grain

**Horizon Start**:
First Gameweek of the Planning Horizon. Any unfinished Gameweek from the earliest unfinished through 38. Finished weeks are not selectable. Default = earliest unfinished.
_Avoid_: is_next as the product start, target_gw as the UI name, picking a finished GW, locking Start to only the earliest unfinished, Horizon Begins as a second clock

**Horizon End**:
Last Gameweek of the Planning Horizon, inclusive. Must satisfy Start ≤ End ≤ min(Start+5, 38). Default = min(Start+5, 38).
_Avoid_: length-only dropdown as the product control, End=38 as Full-Season, End=19 as First-Half, Horizon To as a second clock

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
Planning Horizon xP divided by (Σ expected minutes / 90). Cameo minutes do not reduce this number. Equals xP per Gameweek when every horizon Gameweek is 90 minutes (Assume 90; no Double Gameweek, no blank). Ownership Explorer Y-axis option.
_Avoid_: xP per game, Event Rate, Per-90 average, Season Window rate

**xP per Gameweek**:
Planning Horizon xP divided by gameweek count in that horizon. Equals Projected Rate when minutes are 90 every Gameweek. Ownership Explorer Y-axis option.
_Avoid_: xP per game, per-match xP, average points, Season Window average

**Event Component**:
A decomposed scoring input (minutes, goals, assists, clean sheets, goals_conceded, saves, bonus, cards, penalty events) used by a component model to reconstruct a Projection via the FPL scoring matrix, rather than predicting total points directly.
_Avoid_: Feature, sub-stat

**Event Rate**:
A per-90-minutes estimate of how often a Player produces a given Event Component. Feature Contract uses Recency-Weighted Prior Shrinkage on current-club Club Fixtures. After This-Season Evidence, observations and Position-Price shrink target are this season only.
_Avoid_: Per-90 average, rate (ambiguous), Appearance Blend, in-season Prior-Season Seed rates

**Appearance Probability**:
$1 - p_{\text{dnp}}$ from the Participation State posterior. Distinct from official `chance_of_playing` (next-GW 0% hard DNP only).
_Avoid_: Injury chance, playing chance, API chance as horizon appearance

**Participation State**:
One mutually exclusive finished Club Fixture outcome for a Player: Did Not Play, Start, or Sub-in. Estimated from actual Club Fixture playing time. State probabilities sum to one and determine conditional minutes and Event Component projections. Product reports xMins from this posterior, not an Expected Role label.
_Avoid_: Appearance Probability (only whether a Player features), lineup status, Expected Role, Role column as minutes, Incomplete History Row as a state

**Incomplete History Row**:
An `element_summary` history row for a Fixture that is not finished. Not a Club Fixture. Not Did Not Play.
_Avoid_: Recorded DNP, Sunday not-yet-played as DNP, future 0-minute pad

**Recorded DNP**:
A finished Club Fixture with zero minutes. Did Not Play in Participation State.
_Avoid_: Incomplete History Row, missing history, padded DNP

**This-Season Evidence**:
At least one this-season finished `player_performances` history row in the Operational Dataset (`element_summary` history on a finished Fixture: minutes, starts, or Recorded DNP). Global: one finished row anywhere ends Cold-Start for every Player.
_Avoid_: GW1 deadline as the clock, per-player first appearance, fixture listed with no history row, Incomplete History Row as evidence, Expected Role, bootstrap season totals alone

**Expected Role**:
Retired product label. Not shown. Not a Feature Contract input. Dual-Source scrapes are gone. Surfaces report xMins from Participation State.
_Avoid_: Nailed Starter as xMins, Role column, Draft-eligible from Role, `--rebuild-roles` as required ingest

**Nailed Starter**:
Retired Expected Role value.
_Avoid_: live xMins, Feature Contract prior

**Regular Starter**:
Retired Expected Role value.
_Avoid_: live xMins, Feature Contract prior

**Rotation**:
Retired Expected Role value.
_Avoid_: live xMins, Feature Contract prior

**Cameo**:
Retired Expected Role value.
_Avoid_: live xMins, Feature Contract prior

**Out of Contention**:
Retired Expected Role value.
_Avoid_: live xMins, Feature Contract prior

**Expected Role Prior**:
Retired. Not Feature Contract minutes or Event Rates.
_Avoid_: Cold-Start minutes seed, xMins prior

**XI Contention Set**:
Retired with Expected Role. Not a product list.
_Avoid_: Draft shortlist as live minutes

**Draft Shortlist**:
Retired with Expected Role. Preseason 15 is MILP on Feature Contract xMins.
_Avoid_: Role-gated draft, Nailed-only pool

**Draft Availability**:
Retired Expected Role Table field. Feature Contract never applied Watch/Exclude.
_Avoid_: Watch as live $p_{\text{start}}$ cut, Exclude as live DNP

**Role Evidence**:
Retired with Expected Role.
_Avoid_: Explorer Role audit column

**Dual-Source Lineup Signals**:
Retired production ingest. Editorial XI may appear only as Research-Only Evidence. No FFS/Meerkat adapter on refresh.
_Avoid_: FFS scrape, Meerkat URL, `--rebuild-roles`

**Expected Role Table**:
Retired registry. Not required for Project. Not an Explorer column.
_Avoid_: table-gated Project, minutes prior from this table

**Expected Role Rebuild**:
Retired engine. `refresh_data` does not scrape lineups.
_Avoid_: `--rebuild-roles` as required ingest, Meerkat scrape on Refresh

**Minutes if Appearance**:
Expected minutes conditional on an appearance, distinct from Appearance Probability. From the Participation State posterior (Start vs Sub-in). Cold-Start empty tenure: Prior-Season Seed else last-season Position-Price. After This-Season Evidence: this-season Position-Price.
_Avoid_: Average minutes, Expected Role Prior minutes, in-season last-year player minutes

**Availability Override**:
An explicit, source-attributed and time-limited `xmins_cap` when the FPL API has not yet reflected confirmed club information. Production Feature Contract does not apply these caps.
_Avoid_: Expert guess, manual prediction, live `xmins_cap` as default data-only path

**Availability Snapshot**:
A time-stamped record of Player availability captured before a Gameweek deadline. Used to evaluate Availability and xMins without future-information leakage.
_Avoid_: Current status, injury history

**Cold-Start**:
This-Season Evidence absent. Feature Contract uses Prior-Season Seed else last-season Position-Price. Ends globally when This-Season Evidence appears.
_Avoid_: Preseason as a second clock, Expected Role Prior as minutes seed, hardcoded Position defaults while a Season Archive seed exists, per-player first appearance as the switch

**Appearance Blend**:
Retired production mix. Was a linear appearance-count mix (weight 0 through 1 appearance, 100% current-season at 5) of Cold-Start prior and current-season observation.
_Avoid_: GW5 flip, live Feature Contract mix, dashboard-only minutes, blend_start 3 / blend_full 8

**Prior-Season Seed**:
Per-Player Event Rates and Participation State from the latest completed Season Archive. Used only during Cold-Start. Not the in-season shrink target. Never the live season pin. Summer club change does not discard a usable Cold-Start seed.
_Avoid_: Carryover, in-season last-year player minutes, three-season FPL blend, Expected Role Prior, live Season Archive as seed

**Career Individual Rate**:
Per-90 xG, xA, Defcon, and GK saves from a Player's last completed senior league season. Used only when no usable Prior-Season Seed exists (foreign arrivals, promoted-Club Players, rookies).
_Avoid_: Position-Price Prior, three-season foreign blend, treating any summer transfer as a newcomer

**Destination Team Concede Rate**:
Destination Club's prior-season Premier League goals conceded per game. Supplies the Team Defensive Event λ for Players with no Prior-Season Seed. Clubs with no PL archive use that season's PL league-average concede rate.
_Avoid_: Player-level GC for newcomers, Championship GC as PL λ, opponent xG as the seed

**Position-Price Prior**:
Position × FPL price-band aggregate of Event Rates and Participation State. Cold-Start: from the seed Season Archive. After This-Season Evidence: from this-season Club Fixtures. Shrink target for thin this-season samples.
_Avoid_: Default rate, Career Individual Rate, Expected Role Prior, per-player last season in-season

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
Same object as Position-Price Prior when a Player has no usable Prior-Season Seed during Cold-Start.
_Avoid_: Distinct second prior, Research Position Baseline, Career Individual Rate

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
Exported player metadata, historical rates, and per-gameweek Event Component projections for Ownership Explorer. Export grain is the Full-Season Window; the product ranking band is the Planning Horizon slice. Not Transfer Plan JSON.
_Avoid_: UI state, solver export, Full-Season Window as the product slice, Transfer Plan embed

**Dashboard Refresh**:
In-page FPL ingest plus Champion and Comparison Slate projection rewrite of the Dashboard Data Contract. Charts reload without restarting the server. `commands.dashboard` starts HTTP immediately and paints last JSON or empty; it does not ingest or project on process start. Does not scrape lineups. Does not require `commands.run_model` or a prior `refresh_data` before opening the dashboard.
_Avoid_: Re-solve, export-only restart as the update path, `--rebuild-roles`, blocking process start on ingest or Project, table-gated Project

**Interactive Squad Builder**:
Retired product surface. Not a dashboard tab. A sandbox 15 is not a product object.
_Avoid_: Roster picker, drag list, live tab name, treating Explorer as a draft sandbox

**Transfer Plan**:
CLI MILP 15-player result over a Planning Horizon: per-gameweek User Squad, lineup, transfers in and out, free transfers, hits, Force Keep, Force Ban, Booked Chips, and Enabled Chips. Always scored with the Model Champion on Modified FDR. Starting 15 is the live User Squad when it exists, otherwise a preseason draft. Not a dashboard view. Not Ownership Explorer, not Canonical Preseason Chip Path, not a sandbox 15.
_Avoid_: team plan, dashboard tab, Re-solve as product UI, Load MILP Squad, research chip path, Dual-Vector xP, Squad Builder, Official Fixture Difficulty as Transfer Plan score, sole live product surface

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
The decayed quantity the MILP maximises over the Planning Horizon. Distinct from undiscounted Gameweek Projection xP in the solver report.
_Avoid_: xP, score, total_xp, research total_6gw_xp, Explorer Total column

**Hit**:
A paid transfer beyond the Free Transfer Bank. Official cost is 4 points per paid transfer (solver `hit_cost` default). Distinct from spending banked Free Transfers.
_Avoid_: minus, treating any transfer as a Hit, one transfer per week

**Free Transfer Bank**:
Unused Free Transfers held, cap 5. One new Free Transfer accrues each Gameweek. Spending the bank is not a Hit. Official rules preserve the bank through Wildcard and Free Hit.
_Avoid_: Hit, unlimited transfers, requiring the weekly Free Transfer to be spent

**Transfer Target Policy**:
Research constraint on which Positions a Free Transfer may change in Transfer Plan Walk-Forward. Distinct from Starting Shape and from Expected Role Rotation.
_Avoid_: rotation, fix DEF (ambiguous), lock

**Attack-Targeted FTs**:
Transfer Target Policy: Free Transfers may not change DEF or GKP unless the owned Player meets the Did-Not-Play Exception for that deadline Gameweek.
_Avoid_: rotate MID/FWD, fix defence

**Defence-Targeted FTs**:
Transfer Target Policy: Free Transfers may not change MID or FWD unless the owned Player meets the Did-Not-Play Exception for that deadline Gameweek.
_Avoid_: rotate DEF, spend transfers on DEF

**Did-Not-Play Exception**:
Transfer Target Policy override: an owned Player may be transferred even if that Position is targeted-fixed when Model Champion `p_dnp ≥ 0.5` on the deadline Gameweek only. Not a later week in the Planning Horizon. Not terminal `chance_of_playing`.
_Avoid_: horizon-wide injury flag, archive chance_of_playing, requiring p_dnp = 1

**Defcon-Floor Tilt**:
Research solver score for DEF and MID: Gameweek Projection xP plus `xp_defcon` (Defcon counted twice). GKP and FWD stay on vanilla xP. Frozen before Realized Points are inspected.
_Avoid_: Defcon-only ranking, consistency, hard pool filter

**Attack-Ceiling Tilt**:
Research solver score for DEF and MID: Gameweek Projection xP minus `xp_defcon` (Defcon stripped). Goals, assists, and clean sheets unchanged. GKP and FWD stay on vanilla xP. Frozen before Realized Points are inspected.
_Avoid_: high ceiling, ignoring clean sheets, FWD Defcon strip

**Mix**:
Unordered set of 1–5 Players scored as one bundle: sum Price, each Gameweek Projection in the Planning Horizon, and horizon total. Mix vs Mix requires the same size (1 vs 1, 2 vs 2, 3 vs 3). Same position is not required. A Player occupies at most one Mix. View-only: a Mix does not Force Keep or Force Ban. Not a Transfer Plan, not a legal 15.
_Avoid_: combo, package, alternative 15, differential, solver squad, Plan this Mix, same Player in both Mixes, Mix order, Re-solve from Mix

**Mix Member**:
A Player occupying Mix A or Mix B, never both. Distinct from highlighting a Player in Ownership Explorer.
_Avoid_: selected player, overlapping Mix occupancy

**Assume 90**:
Ownership Explorer view-only toolbar toggle next to Projected Rate / xP per Gameweek. When on, every Player is treated as a full 90-minute match on each Gameweek that already has projected minutes (180 on a Double Gameweek). Event Component xP scales by target/xMins; minutes points become 2 per match. Blank Gameweeks stay 0. Does not write Feature Contract or Availability Override.
_Avoid_: xmins_cap, Availability Override, Project-time minutes, per-player pin, linear total xP scale including minutes points

**Ownership Explorer**:
Live product dashboard view. Ranks Feature Contract Players on the Planning Horizon, with Mix vs Mix, Assume 90, xMins, per-GW xP columns, and linked ownership and price charts. Same Feature Contract, Primary Projection Model (default Model Champion), and Modified FDR. No Role column. Not Transfer Plan. Not a Season Window ranking.
_Avoid_: Ownership Value Explorer (research HTML), 3D scatter, First-Half Horizon as the product band, Dual-Vector explorer xP, Official Fixture Difficulty as Explorer score, Transfer Plan tab, Expected Role as a rank field

**Decision Regret**:
Actual-point gap between a decision made from Projections and the best legal hindsight alternative under identical constraints. Initial scope: one-Gameweek starting XI, bench order, captain, and vice-captain.
_Avoid_: Squad Gap (ambiguous), optimizer gap

**Transfer Plan Walk-Forward**:
Research evaluation of a Transfer Plan policy. At each historical Gameweek deadline in a Season Window, solve from Projections built only on history before that deadline, then score that Gameweek's scoring 15 on Realized Points. Same This-Season Evidence clock as production (ADR 0024). Distinct from model MAE backtest and from one-Gameweek Decision Regret. Exploratory on archive data without Availability Snapshots. Not a product Transfer Plan.
_Avoid_: backtest (ambiguous with model MAE), hindsight oracle, Transfer-plan regret (deferred product metric), in-season Prior-Season Seed after This-Season Evidence

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
A Candidate may replace the Model Champion only after winning the combined prior-season evaluation and at least two of its Cold-Start, early/mid-season, and late-season segments while matching or improving every Champion guardrail. Evaluation replays This-Season Evidence (ADR 0024); the GW1–4 segment is true Cold-Start only while that season's history is empty.
_Avoid_: One-off backtest win, aggregate-only promotion, evaluating ADR 0022 in-season last-year blend while shipping 0024

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
Bottom-up expected points ($xP$) modeling derived from explicit underlying per-90 player skill rates (`per90_xg`, `per90_xa`, `per90_defcon`, `per90_saves`) multiplied by venue-adjusted team/opponent strength vectors and projected minutes. Goals/assists use `attack_multiplier`. Clean sheets, conceded, saves, and defcon use `defence_multiplier`. Missing or zero Club Strength Vector attack/defence → Modified FDR fallback in `_fixture_maps`.
_Avoid_: Top-down power rating, single composite score xP prediction

**Official Fixture Difficulty**:
Per-club-fixture integer 1–5 on `team_h_difficulty` / `team_a_difficulty`. Focal-team difficulty. 2026/27: home FDR = opponent `strength_overall_home`; away FDR = opponent `strength_overall_away`. Those `_home`/`_away` fields are your venue, not the opponent's own ground. Not attack/defence blend. Not production xP input.
_Avoid_: Dual-Vector Strength, Club Strength Vector, treating API strength as finer FDR, ARS `strength_overall_away` as Arsenal stronger on the road, Modified FDR

**Modified FDR**:
Official Fixture Difficulty − 0.25 if focal home, + 0.25 if focal away. Production difficulty for Feature Contract, Champion xP, Transfer Plan, Ownership Explorer, FDR report.
_Avoid_: Official Fixture Difficulty, Dual-Vector Strength, DCS effective FDR (`defence_multiplier × 3`)

**Club Strength Vector**:
Official API club fields `strength`, `strength_overall_home/away`, `strength_attack_home/away`, `strength_defence_home/away`. Live 2026/27: `strength` null, attack/defence 0, overall = Official Fixture Difficulty ticks at focal venue.
_Avoid_: Dual-Vector Strength, FDR, Elo-style 1000-scale ratings (prior-season archive only), opponent's own home/away form

**Dual-Vector Strength**:
Match-level team attack and opponent defense strength multipliers derived from 10-match rolling non-penalty xG (Team Attack) and xGA (Team Defense) scaled against league averages, falling back to Official Fixture Difficulty only when data is sparse. Not implemented in production Python; not the API Club Strength Vector.
_Avoid_: Static FDR multiplier, single team rating, API `strength_*`, Prior-Season Dual-Vector Seed

**Prior-Season Dual-Vector Seed**:
Cold-Start Dual-Vector Strength from the latest archive season: club attack = sum of player `expected_goals` per club-fixture; club defence = that fixture’s `expected_goals_conceded` (one team value, not summed across players); home/away split; scaled to league average. Promoted Clubs use league average. FPL-xG proxy, not npxG. Live research xP for Canonical Preseason Chip Path (Stage 3) and First-Half Chip Path. Also research DCS effective FDR (`defence_multiplier × 3`).
_Avoid_: Dual-Vector Strength (live rolling npxG), Club Strength Vector, Official Fixture Difficulty, FDR-xP Canonical

**Recency-Weighted Prior Shrinkage**:
Feature Contract estimator for Participation State and Event Rates. Recency-weighted current-club Club Fixture observations. Cold-Start: shrink toward Prior-Season Seed else last-season Position-Price. After This-Season Evidence: this-season observations only, shrink toward this-season Position-Price; empty tenure is that pool, not last year's player. Per-90 Event Rates use minutes played; Recorded DNP updates state probabilities only. Data-only: finished FPL history, Season Archive seed during Cold-Start, next-GW 0% chance.
_Avoid_: Simple unweighted current-season average, static role rates, Expected Role Prior, Appearance Blend, in-season per-player last season, Watch/Exclude as minutes, padded DNP, Incomplete History Row as DNP

**Defensive Composite Score (DCS)**:
A 0–100 ranking of a Defensive Rotation Set: 60% opportunity-cost-adjusted rotated expected points plus 40% fixture-risk (zero-difficult weeks, rotated FDR, schedule correlation). Live research ranking uses Prior-Season Dual-Vector Seed effective FDR (`defence_multiplier × 3`).
_Avoid_: RQI, OC-RQI, Rotation Quality Index

**Defensive Rotation Set**:
A goalkeeper pair, five-defender set, or seven-asset backline ranked by DCS. Distinct from the Canonical Preseason Chip Path 15-man squad (including its keepers).
_Avoid_: GKP pick (ambiguous vs squad keepers), the defensive squad, RQI pair

**Club Occupancy**:
Five Club slots filling a five-defender Defensive Rotation Set. A multiset: one Club may occupy 1–3 slots, so distinct Club count is 2–5. Fixture difficulty of the occupancy is a Club-fixture property; swapping Players of the same Club does not change it.
_Avoid_: team combination, team combo, club set (distinct Clubs only), player 5-tuple

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




