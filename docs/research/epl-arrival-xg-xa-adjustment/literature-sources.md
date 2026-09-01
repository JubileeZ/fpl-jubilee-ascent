# Premier League arrival xG / xA — literature sources

**Updated**: 2026-09-01T23:59:00+07:00  
**Data stamp**: Sources fetched 2026-09-01. ClubElo About HTML generated 2026-09-01 08:07:31. UEFA five-year association coefficients: live 2025/26 window (England 119.519) plus UEFA.com year-end snapshot 2025-12-28 (England 103.658). FiveThirtyEight SPI live CSV unreachable; methodology archive 2023-05-29; league-average SPI table archive 2022-05-25.  
**Season**: Multi-season literature. Not a repository empirical run.  
**Status**: Active companion to [epl-arrival-xg-xa-adjustment.md](epl-arrival-xg-xa-adjustment.md). Source synthesis only.  
**Purpose**: Inventory published, high-trust evidence on how attacking Event Components **xG** and **xA** (or npxG / xAG) change when a player moves from another senior league into the **Premier League** (the query phrase “EPL” is this user request only). Split typical vs elite arrivals where sources allow. Inform later work on **Career Individual Rate** (last completed senior-league per-90 xG/xA used only when no **Prior-Season Seed** exists). This note is source synthesis. It is not a production Decision and does not set a haircut.  
**Scope**: League-strength coefficients; empirical attacking-output change into the Premier League; elite vs average; xG vs xA translation; adaptation window; confounders. Excluded: code, ADR, CONTEXT, INDEX update, repository backtest.  
**Related**: ADR 0014 Career Individual Rate; ADR 0003 Event Rates; ADR 0022 Prior-Season Seed ≥450 minutes.  
**Artifact**: None. Literature only.

> `Updated` is last note revision. `Data stamp` is evidence cutoff. Training memory is not a citation.

---

## Sources

Each URL was opened this task. Dates are publication or effective dates from the page, then access 2026-09-01.

### League strength / translation systems

1. **Primary — FiveThirtyEight SPI methodology**: [How Our Club Soccer Predictions Work](https://web.archive.org/web/20230529093930/https://fivethirtyeight.com/methodology/how-our-club-soccer-predictions-work/) — Jay Boice / FiveThirtyEight; model v1.0 2017-01-19, last listed tweak v1.3 2018-08-10; Wayback capture 2023-05-29; accessed 2026-09-01. Role: first-party SPI definition; league-strength as inter-league goal bonus. Live `fivethirtyeight.com` methodology URL redirected to ABC News (2026-09-01). Live `spi_global_rankings.csv` also redirected to ABC News.
2. **Primary — FiveThirtyEight SPI data README**: [soccer-spi README](https://raw.githubusercontent.com/fivethirtyeight/data/master/soccer-spi/README.md) — FiveThirtyEight data repo; accessed 2026-09-01. Role: field dictionary; points to dead methodology URL.
3. **Secondary — SPI league averages (derived, not first-party table)**: [Football League Rankings](https://web.archive.org/web/20220525122752/https://www.globalfootballrankings.com/) — thepearapps; Wayback 2022-05-25; accessed 2026-09-01. Role: mean club SPI by league from FiveThirtyEight global rankings. Not FiveThirtyEight-authored.
4. **Primary — ClubElo**: [clubelo.com About HTML](http://clubelo.com/About) (fetched via API URL that served About); page created 2026-09-01 08:07:31; accessed 2026-09-01. Role: live mean club Elo by association level. `/System` and `/Ranking` returned “site overloaded” on WebFetch.
5. **Primary — ClubElo case**: [The Case](http://www.clubelo.com/TheCase) — ClubElo; accessed 2026-09-01 (search extract + prior Ranking extract). Role: Elo as results-only strength; expected win from rating gap; national cups excluded.
6. **Primary — UEFA association coefficients (method)**: [How men's association club coefficients are calculated](https://www.uefa.com/nationalassociations/uefarankings/country/) — UEFA; accessed 2026-09-01. Role: official method (five-season mean of club UEFA results). Not a domestic-league xG translator.
7. **Primary — UEFA rankings explainer**: [About the rankings](https://www.uefa.com/nationalassociations/uefarankings/) — UEFA; accessed 2026-09-01.
8. **Primary — UEFA year-end association snapshot**: [UEFA rankings 2025: Which teams and nations are on top?](https://www.uefa.com/uefachampionsleague/news/02a0-1f8b9164ba92-1dd42564c706-1000--uefa-rankings-2025-which-teams-and-nations-are-on-top/) — UEFA.com; published 2025-12-28; coefficients “up to date as of 24 December 2025”; accessed 2026-09-01. Role: five-year association table at end-2025 (England 103.658).
9. **Secondary — UEFA 2026 five-year table (calculator matching UEFA top five)**: [UEFA Country Ranking 2026](https://kassiesa.net/uefa/data/method5/crank2026.html) — Bert Kassies; accessed 2026-09-01. Role: full association list summing 2021/22–2025/26. Top five match UEFA.com homepage snippets this task (England 119.519). Not UEFA-hosted.
10. **Primary — Stats Perform Power Rankings + Transfer Portal (editorial)**: [What Is the Transfer Portal?](https://theanalyst.com/articles/what-is-the-transfer-portal) — Opta Analyst / Stats Perform; examples dated January 2021 window; accessed 2026-09-01. Role: Power Rankings 0–100; first 1,000 minutes post-transfer as prediction target; Bruno Guimarães league ratings.
11. **Primary — Transfer Portal paper**: [Transfer Portal: Accurately Forecasting the Impact of a Player Transfer in Soccer](https://arxiv.org/abs/2201.11533) — Daniel Dinsdale, Joe Gallagher (Stats Perform); submitted 2022-01-27; [PDF](https://arxiv.org/pdf/2201.11533); accessed 2026-09-01. Role: 13 Opta per-90 metrics including xG and xA; 26,000 samples; 2,659 historic transfers.
12. **Primary — Opta Power Rankings league averages (2026)**: [FPL New Signings 2026-27](https://theanalyst.com/articles/fpl-summer-signings-stats-projections-tips-premier-league-2026-27) — Opta Analyst (Solio FPL model hosted on page); accessed 2026-09-01; page is 2026-27 season preview. Role: current Opta Power Rankings league means. Solio per-player projections are a separate, non-Opta-empirical layer.
13. **Primary — Opta xG**: [What Is Expected Goals (xG)?](https://theanalyst.com/articles/what-is-expected-goals-xg) — Opta Analyst; accessed 2026-09-01. Role: Opta xG definition; penalty constant 0.79; 40 competitions 2018-19–2021-22 train set.
14. **Primary — Opta xA**: [What Are Expected Assists (xA)?](https://theanalyst.com/articles/what-are-expected-assists-xa) — Opta Analyst; accessed 2026-09-01. Role: xA ≠ FBref xAG; every completed pass, shot not required.
15. **Primary — Stats Perform glossary**: [Sports data glossary](https://developers.statsperform.com/sports-data-glossary) — Stats Perform; accessed 2026-09-01. Role: xG / xA product definitions.
16. **Primary — Smarterscout method (no published coefficients)**: [Why we do what we do at smarterscout.com](https://www.linkedin.com/pulse/why-we-do-what-smarterscoutcom-dan-altman) — Dan Altman; accessed 2026-09-01. Role: per-metric league adjustment from transfer network. Coefficients not on page.
17. **Secondary — Gemini league coefficients (Plus-Minus, not xG/xA)**: [How Do We Compare Performance Across Leagues?](https://brunofreire.xyz/posts/how-do-we-compare-performance-across-leagues) — Bruno Freire / Gemini Sports; accessed 2026-09-01. Exact post date not on page. Role: transfer-bridge Ridge coefficients in Seasonal EPM (xG differential / season), not player xG/90.

### Empirical transfer / arrival studies

18. **Primary — Hierarchical Bayesian PL-destination translation**: [Hierarchical Bayesian Modeling of Cross-League Performance Translation in Elite Football](https://sportrxiv.org/index.php/server/preprint/view/953) — Mohammad Arshan Shaikh; SportRxiv; [PDF](https://sportrxiv.org/index.php/server/preprint/download/953/2045/1940); accessed 2026-09-01. Submitted to *Journal of Sports Analytics*. Role: 174 ATT+MID + 106 DEF training transfers into Premier League, 2017/18–2022/23; held-out 2022/23→2024/25. **Does not model xG or xA.**
19. **Primary — ML Big Five pair translation**: [A Machine Learning Framework for Cross-League Per-90 Statistic Translation](https://sportrxiv.org/index.php/server/preprint/view/959) — Shaikh; SportRxiv; posted 2026-07-09; accessed 2026-09-01. Role: 25 directional Big Five pairs; log-ratio per-90; MAE 0.3325 log-ratio. Abstract does not publish xG/xA haircuts. PDF download 404 this task.
20. **Primary — ESPN within-season adaptation**: [Premier League summer transfers: A bunch of busts, or is patience needed?](https://www.espn.co.uk/football/story/_/id/48014821/premier-league-summer-transfers-bunch-busts-patience-needed) — Ryan O'Hanlon / ESPN; published 2026-02-24 (syndicated date); accessed 2026-09-01. Role: 80 summer attackers from outside England, ≥€15m, ≥300 minutes both halves of first Premier League season, 2015-16 onward. **Compares first 19 vs last 19 Premier League matches, not origin-league vs Premier League.**
21. **Primary — Championship goal drop (goals, not xG)**: [How Aleksandar Mitrovic, Dominic Solanke and Brennan Johnson can make step up to Premier League](https://www.nytimes.com/athletic/3422947/2022/07/28/mitrovic-solanke-johnson-premier-league/) — Liam Tharme, Mark Carey, Ahmed Shooble, Michael Bailey / The Athletic; published 2022-07-28, updated 2022-08-02; accessed 2026-09-01. Role: 52 occasions of 10+ Premier League goals for a promoted side over 10 seasons; mean 20 Championship goals → just under 13 Premier League goals (−36%).
22. **Primary — StatsBomb teammate/level effects**: [New Team, Same Numbers](https://blogarchive.statsbomb.com/articles/soccer/new-team-same-numbers-how-transfers-do-and-dont-change-player-output/) — StatsBomb; originally 2019-03-05; archive accessed 2026-09-01. Role: 22 summer-2018 movers; output tracks teammate quality and opposition level more than a league scalar.
23. **Primary — StatsBomb league distributions (2013-14)**: [Goal Scoring and Assist Distributions Across Leagues](https://blogarchive.statsbomb.com/articles/soccer/goal-scoring-and-assist-distributions-across-leagues/) — StatsBomb archive; 2013-14 season data; accessed 2026-09-01. Role: within-league SD of goals/assists; **author states UEFA coefficients are flawed for this job and that La Liga ≈ Premier League skill was an assumption, not a measured translation.**
24. **Lead — Machine Football league weightings (images not transcribed)**: [From Lisbon to London](https://machinefootball.substack.com/p/from-lisbon-to-london-analysing-viktor) — Machine Football; 2026-02-23; accessed 2026-09-01. Role: claims Primeira Liga→Premier League drop-off mirrors Championship; table is a figure.
25. **Lead — Machine Football Belgium finishing**: [Who Could Replace Mohamed Salah?](https://machinefootball.substack.com/p/who-could-replace-mohamed-salah) — Machine Football; 2025-12-10; accessed 2026-09-01. Role: “almost 30%” finishing drop-off Belgian Pro League→Premier League since 2016-17.
26. **Lead — Machine Football Championship attributes**: [The Premier League Trap](https://machinefootball.substack.com/p/the-premier-league-trap) — Lucas Le Saux / Machine Football; 2025-07-10; accessed 2026-09-01. Role: promoted-side Creativity / Dribbling / Finishing typically −20% to −30%.
27. **Lead — expectinggoals “Bundesliga tax”**: [The "Bundesliga Tax"](https://www.expectinggoals.com/p/the-bundesliga-tax-why-transfers) — expectinggoals / Double Pivot; accessed 2026-09-01 (search extract; full page timed out). Role: non-penalty **goals** translation into Premier League reversed from 2010s premium to 2020s haircut. Numeric table not recovered this task.

**Source boundary**: Source claims below are what those pages say. Not independently re-estimated on FBref/Opta microdata in this repo. Where only one study reports a figure, it is labeled single-source. A recommendation-grade Career Individual Rate haircut would need two independent player-level xG/xA arrival studies; that pair was **not** found.

---

## Agent Prompt

```text
Full redo docs/research/epl-arrival-xg-xa-adjustment/literature-sources.md

1. Re-fetch every URL under Sources. Do not cite training memory.
2. Prefer first-party pages (UEFA, ClubElo, Stats Perform/Opta Analyst, StatsBomb, FiveThirtyEight archive, arXiv, SportRxiv, Athletic, ESPN).
3. Keep Source synthesis separate from interpretation. Do not write a production Decision or a Career Individual Rate coefficient.
4. Recompute any arithmetic from fetched numbers. When sources disagree, name which is trusted and why. Do not average.
5. Refresh Updated, Data stamp, tables, Could-not-verify.
6. Do not edit docs/research/INDEX.md, CONTEXT.md, or ADRs.
7. Scratch only under .tmp/agent/; delete before finish.
```

---

## Method

**Method type**: Source synthesis. No repository dataset.

**Procedure**:
1. Fetch first-party league-rating systems and xG/xA definitions.
2. Fetch player-transfer studies that report xG, xA, npxG, xAG, goals, or stated translation factors into the Premier League.
3. Split typical vs elite only when the source itself splits (fee, xG level, calibration).
4. Record confounders the sources name.
5. List figures that could not be verified from a fetched page.

### Metric Definitions & Direction

| Metric | Symbol | Definition / Formula | Direction | Ideal / Benchmark | Description |
|---|---|---|---|---|---|
| Expected goals | xG | Shot-level P(goal) from a named model (Opta vs StatsBomb differ) | Context | Not a league-invariant rate | Attacking Event Component. Model- and league-style dependent. |
| Non-penalty expected goals | npxG | xG excluding penalties | Context | Prefer to raw xG for taker-mix | Penalty share is a named confounder. Opta penalty xG = 0.79 constant. |
| Expected assists (Opta) | xA | P(completed pass becomes an assist); shot not required | Context | Not interchangeable with xAG | Opta Analyst: pass type, pattern, start/end location, distance. |
| Expected assisted goals (FBref-style) | xAG | xG of the shot following a key pass | Context | Not interchangeable with Opta xA | ESPN distinguishes xA from “expected goals assisted”. |
| Career Individual Rate | — | Last completed senior-league per-90 xG/xA | Context | Used only if no Prior-Season Seed | ADR 0014 newcomer path. This note does not set its haircut. |
| Prior-Season Seed | — | Archived Premier League season, ≥450 minutes | Context | Preferred over Career Individual Rate | Returning Premier League players. Not this literature question. |
| League mean SPI | — | Mean club SPI in a league | Higher = stronger league ↑ | Not an xG multiplier | FiveThirtyEight; last derived table fetched is 2022-05-25. |
| ClubElo league mean | ⌀ Elo | Mean club Elo in a level | Higher = stronger league ↑ | Not an xG multiplier | Results-only; cups excluded. |
| UEFA association coefficient | — | Five-season mean of club UEFA results | Higher = more European success ↑ | Not domestic xG | Access-list / seeding tool. |
| Opta Power Rankings league mean | — | Mean of 0–100 team ratings | Higher = stronger league ↑ | Not an xG multiplier | Hierarchical Elo family; rescaled. |
| Log-ratio translation | $y=\log\frac{r_{\text{dest}}+0.05}{r_{\text{src}}+0.05}$ | Shaikh (2026) response | $y>0$ = rate rose in Premier League | Not xG | Shaikh ATT+MID metrics are KP, PrgP, PrgC, SCA. |

**Validation boundary**: No figure in this note was re-fit on event data. Unvalidated for production.

---

## Source synthesis

### 1. League-strength systems (not xG haircuts)

**FiveThirtyEight SPI (source 1).** Offensive rating = expected goals vs an average team on a neutral field; defensive rating = expected goals conceded; overall SPI = expected share of available points. Match update uses adjusted goals, shot-based xG, and non-shot xG (Opta play-by-play since 2010). Inter-league matches plus Transfermarkt league market values produce a **league strength rating expressed as a goal bonus** for clubs in UEFA matches. The methodology page **does not publish the numeric league-bonus table**. Live SPI files were dead on 2026-09-01.

**Derived SPI league means, May 2022 (source 3).** Mean club SPI: Premier League 72.97; La Liga 69.97; Bundesliga 69.27; Serie A 63.43; Ligue 1 60.54; Primeira Liga 52.05; Eredivisie 51.56; Brasileirão 49.30; Liga MX 47.40; Championship 44.10; Belgian Pro League 42.73; MLS 39.47. Secondary site. Stale vs 2026 Opta/ClubElo.

**ClubElo, About HTML 2026-09-01 (source 4).** Results-only Elo. Mean Level 1 Elo this fetch: England 1832 (17 clubs listed — not a full 20); Spain 1745 (20); Germany 1733 (18); Italy 1721 (20); France 1697 (18); Brazil 1696 (20); Belgium 1590 (19); Mexico 1586 (18); Portugal 1574 (18); United States 1559 (30); Netherlands 1536 (18). England Level 2 1601 (26 clubs). Same-session search of `/Ranking` showed England Level 1 (20 teams) ⌀1833 — close to 1832, fuller roster. Elo gap is an expected **match-result** score, not an xG/90 factor. ClubElo does not publish an xG translation coefficient.

**UEFA association coefficients (sources 6–9).** Mean points from UEFA club competitions, last five seasons. **Not** domestic shot quality. Two official-adjacent snapshots disagree because the window moved:

- UEFA.com 2025-12-28 (as of 2025-12-24): England 103.658, Italy 92.124, Spain 85.953, Germany 82.902, France 75.534, Netherlands 65.762, Portugal 63.266, Belgium 57.750.
- Kassies 2026 table (21/22–25/26), matching UEFA.com live top five this task: England 119.519, Italy 99.946, Spain 97.046, Germany 92.902, France 83.498, Portugal 73.166, Netherlands 67.929, Belgium 62.250.

Trust **UEFA.com** for the method and the 2025-12-28 snapshot. Trust Kassies only as a full-list calculator that matches UEFA’s published top five for the later window. Do not treat either as an xG haircut. StatsBomb (source 23) already called UEFA coefficients “extremely flawed” for player comparison (2013-14 era).

**Stats Perform Power Rankings (sources 10–12).** Hierarchical Elo, 0–100 daily rescaling (best team 100). Transfer Portal (2021 editorial): average Premier League team 85.5 vs Ligue 1 78.0. Opta Analyst 2026-27 preview: Premier League mean 92.8; Bundesliga 86.9 (gap 5.9); Championship 81.2. Gap Premier League vs Championship ≈ gap Bundesliga vs Championship. Eleven Premier League clubs in world top 20. Absolute 0–100 levels are **not** comparable across 2021 vs 2026 because of daily 0–100 scaling. Rank order (Premier League above other domestic leagues) is stable across ClubElo, SPI-2022, UEFA, and Opta 2026.

**Smarterscout (source 16).** Adjusts **each metric separately** from a decade of transfers (example: tackling in Brazil vs Premier League). **No coefficients published** on the fetched page. Method claim only: xG and dribbling need not share a factor.

**Gemini EPM (source 17).** League coefficients from origin/destination Ridge on Seasonal EPM (xG *differential per season*), by position. Validation: league translation raised Spearman correlation with Transfermarkt value from 0.323 to 0.581. **Does not publish the coefficient vector.** Not a player xG/90 table.

### 2. Empirical attacking-output change into the Premier League

**No fetched first-party paper publishes a complete league-by-league xG/90 and xA/90 haircut table for Premier League arrivals.** Closest high-trust objects:

**Dinsdale & Gallagher 2022 Transfer Portal (source 11) — strongest modeling paper that actually targets xG and xA.**

- Opta event data; 32 domestic leagues; targets = first **1,000 minutes** at new club (or next 1,000 if no transfer).
- Baseline = carry forward last rolling per-90. Transfer-only test: **49% mean MSE reduction** across 13 metrics; **54% MSE reduction for xG/90**.
- Calibration (xG, transfers): **slight overprediction at low xG; slight underprediction at high xG**.
- Grouped models: xG with shots; xA with passing-style metrics. Implicit: xG and xA are not one factor.
- Worked examples are **not** a Premier League-arrival mean:
  - Kamaldeen Sulemana, Danish Superliga → Ligue 1: “over 20% reduction in xG”.
  - Rhys Healey, Ligue 2 → Brighton: shooting metrics “expected to fall by around 30%” to average Premier League striker.
  - Kylian Mbappé, Ligue 1 → Real Madrid: **8–15% decrease** in predicted outputs; still 94th percentile in La Liga.
  - Frenkie de Jong → Manchester United: up to **50%** cut, attributed to **team style more than league**.
  - Jérémy Doku, Ligue 1 → Liverpool: **xG predicted to rise**; **xA predicted to drop slightly**. Same player, opposite signs for xG vs xA.
- Team-feature appendix: newly promoted team xG/90 example 1.5 → 0.9 (**−40%**) as a *prior* for the new league, not a measured player mean.

**Shaikh 2026 HBFLT (source 18) — strongest Premier League-destination bridge; wrong metrics for this question.**

- Destination: Premier League only. Feeders: La Liga, Bundesliga, Serie A, Ligue 1, plus within-Premier League baseline.
- Inclusion: ≥5×90 in both seasons. ATT+MID n=174 train / 45 test; DEF 106 / 35.
- Metrics: **KP, PrgP, PrgC, SCA** (attack) — **not xG, not xA**.
- Only credibly non-zero ATT league association named in text: La Liga SCA posterior mean **+0.306** (90% HDI [+0.015, +0.578]) — i.e. **higher** SCA/90 in the Premier League than at source vs domestic movers. exp(0.306) ≈ **1.36**. Author: may be tempo/style or **selection**, not a causal league tax.
- Explicit: effects are **conditional associations**; Year-1 only; loans not distinguished; FBref-derived Kaggle stats.

**Shaikh 2026 conformal ML (source 19).** All 25 Big Five directional pairs; MAE **0.3325 log-ratio** (~28% typical absolute geometric error vs a perfect translator). Improves naive/pair-mean by 6.1% / 7.6%. **No xG/xA haircut table in the abstract.** PDF not fetched.

**ESPN O'Hanlon 2026-02-24 (source 20) — adaptation inside the Premier League, not origin vs destination.**

- 80 summer attackers from **outside England**, ≥€15m, ≥300 minutes in **both** halves of first Premier League season, 2015-16 onward.
- First 19 vs last 19 Premier League games, per 90: Goals **+5.7%**; **xG +11.9%**; Assists +0.6%; **xA −5.9%**; chances created +1.6%; shots +4%; box touches +6.3%; passes into box +5.1%; successful dribbles −3.5%.
- Author: xA decline is hard to square with more box passes; inclined to treat passing impact as “no real change”.
- Six 2025 summer arrivals ≥€60m (Wirtz, Ekitike, Šeško, Gyökeres, Simons, Woltemade), smaller second-half sample: Goals +52%; **xG +19.2%**; Assists +12.1%; **xA +66%**.

**The Athletic 2022-07-28 (source 21) — Championship → Premier League goals, selected scorers.**

- 52 occasions of **10+ Premier League goals** for a promoted side (10 seasons). Mean **20 Championship goals → just under 13 Premier League goals** = **−36% goals**.
- Only 13 of 52 then scored 10+ again the **following** Premier League season.
- Championship season is 46 games vs 38. Minutes/role change named.
- Style (Opta/The Analyst): Premier League more expansive than Championship; higher shot quality / closer shots; more cutbacks; higher press; fewer long passes.
- Mitrovic: overperformed xG in Championship, underperformed vs Premier League defences (player example, not a sample mean).

**StatsBomb 2019 (source 22).** n=22, mixed leagues, summer 2018. Same-level clubs: radar **shape and volume mostly hold**, including some cross-league moves. Up a level (better teammates): attacking volume **up** (Mahrez, Fabián Ruiz, Shaqiri). Down a level / worse teammates: volume **down**. Relegation to Championship: **same shape, larger volume**. Inverse stated for promoted players. **No numeric xG haircut.** Teammate quality and relative dominance dominate a league label.

**Machine Football (sources 24–26) — proprietary attributes; figures not OCR’d.**

- Portugal → Premier League “mirrors Championship” (2026-02-23). Numeric cells not in HTML.
- Belgian Pro League attackers: finishing drop-off **almost 30%** (sample: transfers since 2016-17) (2025-12-10).
- Promoted teams: Creativity, Dribbling, Finishing typically **−20% to −30%** (2025-07-10). Southampton 2024/25 example is a club, not a player mean.

**Solio on Opta Analyst 2026-27 (source 12) — projections, not realized haircuts.**

- Tzolis (Belgian Pro League): goals/90 **0.50 → 0.28** (retain 56%); FPL assists/90 **0.70 → 0.27** (retain 39%). Includes set-piece competition at Arsenal.
- Touré: Bundesliga 3.2 goals/game vs Premier League 2.8; assist rate 0.54 → 0.26 projected.
- These are a vendor FPL model, not an Opta Transfer Portal replay.

**expectinggoals (source 27).** Non-penalty **goals**; mix of xG+goals “didn’t change relative league effects meaningfully”. 2010s: outside-Premier League arrivals often **beat** within-league movers; 2020s: **reversed**. Full numeric series not recovered (page timeout).

### 3. Elite / top vs typical / average

| Source | What it actually split | Claim |
|---|---|---|
| Transfer Portal xG calibration | High vs low pre-transfer xG | Model **underpredicts** highest xG players and **overpredicts** lowest. Elite retain **more** xG than the transfer model; low-xG retain **less**. Not a published retain-% table. |
| ESPN 2026 | €15m+ (n=80) vs €60m+ 2025 (n=6) | Fee-elite improved **more** from first half to second half of year 1 (xG +19.2% vs +11.9%; xA +66% vs −5.9%). **Within Premier League**, not origin-league haircut. n=6 and shorter H2 sample. |
| Opta Analyst 2026-27 | Haaland vs Gyökeres anecdote | Similar origin scoring rates (62/67 Dortmund vs 68/66 Sporting); Haaland 36 Premier League goals; Gyökeres 14. **n=2.** Destination club and role differ. |
| Athletic 2022 | Players who already scored 10+ in the Premier League | −36% vs Championship is **conditional on Premier League success**. Survivorship. |
| Shaikh 2026 | No elite split | Shrinkage toward league/team means by design. |
| StatsBomb 2019 | Qualitative | Superstar-on-bad-team vs squad-player-on-good-team: teammate quality can dominate. |

Two independent sources that **both** say stars retain more **origin-league xG** than squad attackers were **not** found. The Transfer Portal calibration is the only first-party xG split by output level. ESPN’s fee split is a different question (in-season slope).

### 4. Whether xG and xA need different factors

**Sources that treat them as different objects:**

- Opta: xG is shot-conditional (20+ features, GK position, pressure). xA is **every completed pass**. FBref-style xAG is shot-conditional key-pass xG. ESPN used Opta-like xA and found it can **move opposite** xG.
- Transfer Portal: separate model heads; Doku Liverpool example **xG up, xA down**. Sulemana: shooting down, some passing **up** despite harder league because Rennes wingers create more xA.
- Smarterscout: “dribbling might be different” — per-metric adjustment.
- ESPN n=80: **xG +11.9%** vs **xA −5.9%** in the same window.

**Sources that did not separate them:** Athletic Championship study (goals only). Machine Football “finishing” vs “creativity” are proprietary, not xG/xA. Shaikh ATT+MID is SCA/KP/carries, not xG/xA.

**Synthesis (source claims, not a Decision):** High-trust methods that predict both metrics **do not use one scalar**. ESPN’s only large-n xG vs xA result is **within-season**, not origin→Premier League.

### 5. Adaptation window

| Window | Source | Finding |
|---|---|---|
| First ~1,000 minutes (~11×90) | Transfer Portal | Explicit prediction horizon; can be lengthened. Ismaïla Sarr xA prior mis-estimated in Premier League, then used for Championship. |
| First 19 vs last 19 of year 1 | ESPN n=80 | xG +11.9%; goals +5.7%; xA −5.9%. Minutes filter drops players who lost the job. |
| First 8–9 vs 19 (2025 fee-elite) | ESPN n=6 | Larger xG/xA bounce; author warns small H2 sample. |
| Full first season vs origin | Shaikh | Year-1 log-ratio only. Limitation: adaptation lag absorbed in residual. |
| Second Premier League season | Athletic | Of 52 “10+ goals in year 1 after promotion”, only 13 scored 10+ again in year 2. |
| Later seasons | — | **Not fetched** as an xG/xA panel. |

No fetched study isolates **first 10–15 Premier League matches** as a separate xG/xA cell. Closest: 1,000-minute Transfer Portal horizon.

### 6. Confounders sources name

- **Minutes / selection**: ESPN 300-minute both-halves; Shaikh 5×90 both seasons; Athletic 10+ Premier League goals; Transfer Portal 1,000-minute target. All drop arrivals who barely play.
- **Role / position / style**: Transfer Portal position-stamped events; de Jong 50% style shock; Doku inverted vs traditional wing; Athletic lone 9 vs pair; Shaikh ATT+MID bucket hides CF vs winger.
- **Teammate / destination quality**: StatsBomb 2019 central result; Transfer Portal Power Rankings **and** relative standing in league (Guimarães: harder league **and** weaker club vs Lyon).
- **Age**: Shaikh quadratic age on log-ratio; Transfer Portal youth priors.
- **Set-piece / penalty share**: Opta penalty xG 0.79; Athletic headers/set-piece for Mitrovic; Solio Tzolis corner assists cut by Rice competition. npxG not used as the Athletic sample metric.
- **xG provider**: Opta (FBref current explained page / Transfer Portal) vs StatsBomb freeze-frames vs FBref-era mix. Shaikh used FBref-derived Kaggle. Cross-provider league comparison is not identified with a player-arrival haircut in fetched pages.
- **Loan vs permanent**: Shaikh cannot distinguish.
- **Season length**: Championship 46 vs 38 (Athletic).
- **League goal climate**: Solio Bundesliga 3.2 vs Premier League 2.8 goals/game (2025-26 cited on that page).
- **Non-stationarity**: expectinggoals 2010s vs 2020s reversal; Shaikh Int train/test variance shift; Opta vs 2021 Power Ranking levels.
- **Causal vs association**: Shaikh §7.2 selection into Premier League.

---

## Tables (fetched numbers only)

### A. League mean ratings (not xG translation factors)

| League | Figure | Unit | Effective date | Source |
|---|---|---|---|---|
| Premier League | 1832 (17 clubs listed) | Mean ClubElo | 2026-09-01 08:07:31 | ClubElo About HTML |
| Premier League | 1833 (20 clubs) | Mean ClubElo | same-session `/Ranking` search | ClubElo Ranking snippet |
| Championship (ENG L2) | 1601 (26 clubs) | Mean ClubElo | 2026-09-01 | ClubElo About HTML |
| La Liga | 1745 (20) | Mean ClubElo | 2026-09-01 | ClubElo About HTML |
| Bundesliga | 1733 (18) | Mean ClubElo | 2026-09-01 | ClubElo About HTML |
| Serie A | 1721 (20) | Mean ClubElo | 2026-09-01 | ClubElo About HTML |
| Ligue 1 | 1697 (18) | Mean ClubElo | 2026-09-01 | ClubElo About HTML |
| Belgian Pro League | 1590 (19) | Mean ClubElo | 2026-09-01 | ClubElo About HTML |
| Liga MX | 1586 (18) | Mean ClubElo | 2026-09-01 | ClubElo About HTML |
| Primeira Liga | 1574 (18) | Mean ClubElo | 2026-09-01 | ClubElo About HTML |
| MLS | 1559 (30) | Mean ClubElo | 2026-09-01 | ClubElo About HTML |
| Eredivisie | 1536 (18) | Mean ClubElo | 2026-09-01 | ClubElo About HTML |
| Premier League | 92.8 | Opta Power Rankings league mean | 2026-27 preview | Opta Analyst / Solio article |
| Bundesliga | 86.9 | Opta Power Rankings league mean | 2026-27 preview | Opta Analyst |
| Championship | 81.2 | Opta Power Rankings league mean | 2026-27 preview | Opta Analyst |
| Premier League | 85.5 | Power Rankings league mean | Jan 2021 example | Opta Analyst Transfer Portal |
| Ligue 1 | 78.0 | Power Rankings league mean | Jan 2021 example | Opta Analyst Transfer Portal |
| Premier League | 72.97 | Mean SPI | Wayback 2022-05-25 | globalfootballrankings.com |
| La Liga | 69.97 | Mean SPI | 2022-05-25 | globalfootballrankings.com |
| Bundesliga | 69.27 | Mean SPI | 2022-05-25 | globalfootballrankings.com |
| Serie A | 63.43 | Mean SPI | 2022-05-25 | globalfootballrankings.com |
| Ligue 1 | 60.54 | Mean SPI | 2022-05-25 | globalfootballrankings.com |
| Primeira Liga | 52.05 | Mean SPI | 2022-05-25 | globalfootballrankings.com |
| Eredivisie | 51.56 | Mean SPI | 2022-05-25 | globalfootballrankings.com |
| Liga MX | 47.40 | Mean SPI | 2022-05-25 | globalfootballrankings.com |
| Championship | 44.10 | Mean SPI | 2022-05-25 | globalfootballrankings.com |
| Belgian Pro League | 42.73 | Mean SPI | 2022-05-25 | globalfootballrankings.com |
| MLS | 39.47 | Mean SPI | 2022-05-25 | globalfootballrankings.com |
| England | 119.519 | UEFA 5y association | 21/22–25/26 | Kassies; matches UEFA.com top five |
| Italy | 99.946 | UEFA 5y association | 21/22–25/26 | Kassies / UEFA.com |
| Spain | 97.046 | UEFA 5y association | 21/22–25/26 | Kassies / UEFA.com |
| Germany | 92.902 | UEFA 5y association | 21/22–25/26 | Kassies / UEFA.com |
| France | 83.498 | UEFA 5y association | 21/22–25/26 | Kassies / UEFA.com |
| Portugal | 73.166 | UEFA 5y association | 21/22–25/26 | Kassies |
| Netherlands | 67.929 | UEFA 5y association | 21/22–25/26 | Kassies |
| Belgium | 62.250 | UEFA 5y association | 21/22–25/26 | Kassies |
| England | 103.658 | UEFA 5y association | as of 2025-12-24 | UEFA.com 2025-12-28 |

Do **not** convert these rows to xG retain-% by averaging systems. They measure different objects (results Elo, SPI points share, UEFA Europe, 0–100 Power Rankings).

### B. Player / team attacking translation numbers actually on the page

| Claim | Sample | Window | Source |
|---|---|---|---|
| xG/90 MSE −54% vs carry-forward | 2,659 transfers, 32 leagues | First 1,000 min | Dinsdale & Gallagher 2022 |
| 13-metric MSE −49% vs carry-forward | Same | First 1,000 min | Dinsdale & Gallagher 2022 |
| xG calibration: overpredict low, underpredict high | Same xG plot | First 1,000 min | Dinsdale & Gallagher 2022 |
| xG −20%+ (example) | Sulemana Superliga → Ligue 1 | Next 1,000 min *predicted* | Dinsdale & Gallagher 2022 |
| Shooting −~30% (example) | Healey Ligue 2 → Premier League | Predicted | Dinsdale & Gallagher 2022 |
| Outputs −8 to −15% (example) | Mbappé Ligue 1 → La Liga | Predicted | Dinsdale & Gallagher 2022 |
| xG up / xA slightly down (example) | Doku → Liverpool | Predicted | Dinsdale & Gallagher 2022 |
| Team xG prior 1.5 → 0.9 (−40%) | Promoted-team toy | New-league prior | Dinsdale & Gallagher app. |
| SCA log-ratio +0.306 (HDI > 0) | La Liga → Premier League attackers | Year 1 vs source | Shaikh 2026 HBFLT |
| MAE 0.3325 log-ratio | Big Five pairs | Season-to-season | Shaikh 2026 ML abstract |
| xG +11.9%; xA −5.9% | 80 PL year-1 attackers, €15m+ | H1 vs H2 *inside* PL | ESPN 2026-02-24 |
| xG +19.2%; xA +66% | 6 arrivals €60m+ (2025) | H1 vs shorter H2 *inside* PL | ESPN 2026-02-24 |
| Goals 20 → ~13 (−36%) | 52 promoted 10+ PL-goal seasons | Championship season vs year-1 PL | Athletic 2022-07-28 |
| Finishing −~30% | Belgian Pro League attackers since 2016-17 | Unspecified | Machine Football 2025-12-10 |
| Creativity/Dribbling/Finishing −20 to −30% | Promoted *teams* | Championship → PL season | Machine Football 2025-07-10 |
| Goals/90 0.50 → 0.28; assists/90 0.70 → 0.27 | Tzolis projection | Next PL season | Solio on Opta Analyst 2026 |

---

## Conflicts (do not average)

1. **UEFA 103.658 vs 119.519 (England).** Different five-year windows. Trust the dated UEFA.com snapshot for end-2025; trust 119.519 as the later window that includes 2025/26 (Kassies + UEFA homepage top five). Neither is xG.
2. **ClubElo England 17 vs 20 clubs.** About HTML incomplete roster; Ranking snippet 20 teams ⌀1833. Trust 1833 as the fuller Level-1 mean if using ClubElo; 1832 is what the About parse actually contained.
3. **SPI 2022 Championship 44.1 vs ClubElo 2026 ENG L2 1601 vs Opta 2026 Championship 81.2.** Different years and scales. Rank vs Premier League is consistent (weaker). Magnitude is not interchangeable.
4. **La Liga SCA *increase* (Shaikh) vs “Premier League tax” narrative (Machine Football, expectinggoals, Solio).** Different metrics and selection. Shaikh SCA is not xG. Trust Shaikh for SCA/KP/Prg* **associations** with stated caveats; do not invert it into an xG haircut.
5. **Transfer Portal: xG can rise at a better club in a harder league (Doku).** StatsBomb 2019: better teammates raise volume. League-only haircuts omit this.
6. **Athletic −36% goals (retain ~65%) vs a blog that said promoted scorers keep 36% of Championship goals.** The Athletic page is 20 → 13. Trust Athletic. The “keep 36%” wording is a misread of “36 per cent drop-off”.
7. **ESPN xA down while xG up** vs Transfer Portal examples where both fall. Different questions (in-season slope vs origin translation). Both can be true.
8. **2010s vs 2020s (expectinggoals).** If that series is real, a pooled multi-year haircut is wrong. Page not fully fetched; treat as unverified magnitude.

**What to trust for this repo’s question (interpretation boundary, not a Decision):**  
For **league rank**, current Opta Power Rankings (2026) and ClubElo (2026-09-01) agree the Premier League sits above other senior domestic leagues; UEFA agrees for European results. For **player xG/xA after arrival**, the only first-party model that outputs those two Event Components is Transfer Portal (2022), and it **refuses a single league scalar**. The only large-n **measured** xG/xA deltas fetched are ESPN’s **within-Premier-League** H1/H2 slopes. Championship **goals** −36% (Athletic) is not npxG/xAG.

---

## Could-not-verify

- Live FiveThirtyEight SPI league-strength **goal-bonus table** and live `spi_global_rankings.csv` (redirect to ABC News, 2026-09-01).
- ClubElo `/System` and `/Ranking` full pages (site overloaded on WebFetch). About HTML used instead.
- Transfer Portal **Table 2 per-metric MSE%** for xA (PDF extract named 37–61% range and 54% for xG; xA cell not captured).
- Shaikh 959 full PDF (download 404); GitHub `football-league-translation` “public upon acceptance”.
- Smarterscout / Gemini **numeric league coefficient vectors**.
- expectinggoals full “Bundesliga tax” time-series chart (timeout).
- Machine Football league-weighting **figure cells** (Portugal, Championship, Bundesliga creativity vs Championship).
- FBref `expected-goals-model-explained` full page (timeout this task). Search snippet: FBref uses **Opta** xG; npxG recommended to drop PKs. Treat as unverified until re-fetched.
- Hudl StatsBomb xG glossary (HTTP 500).
- StatsBomb “Brazil vs Big 5” PDF at the 2023 URL: later fetch served marketing HTML, not the 2021-22 xG table.
- Promotion-effect Substack (−33.49% **team** xG Championship→Premier League): search snippet only; page timed out. Not used as a load-bearing figure.
- Peer-reviewed McHale & Szczepański 2014 mixed-effects **transfer-value** coefficients (cited by Shaikh; paper not opened).
- MLS / Liga MX **player-level** xG/xA arrival studies (ASA pages fetched do not publish an MLS→Premier League xG factor).
- Eredivisie / Primeira Liga **player-level xG/xA** retain-% other than Machine Football’s un-OCR’d figure and Solio/anecdotes.
- First **10–15 match** xG/xA cell distinct from 1,000 minutes or 19-game halves.
- npxG and xAG translation factors as named series.
- Production Decision / Career Individual Rate multiplier — **out of scope**.

---

## Interpretation boundary

This note does not choose a Career Individual Rate haircut, does not average league ratings into retain-%, and does not implement code. If a later Decision needs a number, the literature gap is: **no two independent, current, player-level studies report origin-league → Premier League xG/90 and xA/90 retain rates for typical vs elite arrivals.** Available substitutes are (i) Transfer Portal-style team+league+role models, (ii) Championship **goal** drop for a selected scorer sample, (iii) in-season xG slope of those who keep minutes.

## Refresh checklist

- [x] `Updated` ISO 8601 +07:00
- [x] `Data stamp` is evidence cutoff
- [x] Source URLs opened this task
- [x] Source synthesis separate from interpretation; no production Decision
- [x] Unvalidated / single-source labeled
- [x] Could-not-verify listed
- [x] Scratch under `.tmp/agent/` removed
