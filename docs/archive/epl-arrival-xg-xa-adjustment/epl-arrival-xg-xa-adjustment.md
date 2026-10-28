# Premier League arrival xG / xA translation

**Updated**: 2026-09-02T00:20:00+07:00  
**Data stamp**: worldfootballR FBref Big 5 standard dump `2025-09-18T17:39:48Z`; pannadata Understat roster/shots `2026-04-18T08:01:47Z`; literature URLs fetched 2026-09-01  
**Season**: Multi-season. FBref arrivals with Premier League season-end 2019–2025 (2018-19 through 2024-25). Incomplete 2025-26 dump excluded.  
**Status**: Active. Research only. No Career Individual Rate or Feature Contract change.  
**Purpose**: Quantify how **xG** and **xA** Event Rates change when a Player moves from another senior league into the Premier League, for typical vs elite attackers, to inform a later Career Individual Rate haircut if one is ever wanted.  
**Scope**: In: summer arrivals from La Liga, Bundesliga, Serie A, Ligue 1 with ≥900 minutes in both the source-league season and the first Premier League season. Talent = within-source-league quartile of prior npxG+xAG/90. Out: production CIR; Championship / Eredivisie / Primeira Liga player-level npxG (dump has no rows); minutes / Defcon.  
**Related**: [literature-sources.md](literature-sources.md) · [ADR 0014](../../adr/0014-preseason-career-rate-and-destination-concede.md) · [ADR 0003](../../adr/0003-reconstruct-points-from-event-components.md)  
**Artifact**: [arrival_xg_xa_summary.csv](arrival_xg_xa_summary.csv) `npxg_median_ratio` / `xag_median_ratio` · [arrival_xg_xa_before_after.csv](arrival_xg_xa_before_after.csv) `ratio_npxg` · [arrival_xg_xa_understat_summary.csv](arrival_xg_xa_understat_summary.csv) `npxg_median_ratio` · [talent_league_cuts.csv](talent_league_cuts.csv) `p75_npxg_xag_p90` · [literature_numeric_claims.csv](literature_numeric_claims.csv) `value`

> `Updated` is last note revision. `Data stamp` is evidence cutoff.

## Sources

- **Primary**: [worldfootballR FBref Big 5 player standard RDS](https://github.com/JaseZiv/worldfootballR_data/releases/download/fb_big5_advanced_season_stats/big5_player_standard.rds) — JaseZiv/worldfootballR_data (archived 2025-09-18); dump updated 2025-09-18T17:39:48Z; accessed 2026-09-02; role: Opta npxG / xAG / minutes by competition. Recomputed in this folder.
- **Primary**: [pannadata Understat roster parquet](https://github.com/peteowen1/pannadata/releases/download/understat-latest/understat_roster.parquet) and [shots parquet](https://github.com/peteowen1/pannadata/releases/download/understat-latest/understat_shots.parquet) — peteowen1/pannadata; dump updated 2026-04-18T08:01:47Z; accessed 2026-09-02; role: independent npxG (non-penalty shots) and xA. Recomputed in this folder.
- **Primary**: [literature-sources.md](literature-sources.md) — URLs opened 2026-09-01; role: league-strength systems and published transfer studies. Not re-estimated here.
- **Secondary (not recomputed)**: [The Athletic Championship scorers](https://www.nytimes.com/athletic/3422947/2022/07/28/mitrovic-solanke-johnson-premier-league/) — 2022-07-28; [ESPN year-1 H1/H2](https://www.espn.co.uk/football/story/_/id/48014821/premier-league-summer-transfers-bunch-busts-patience-needed) — 2026-02-24; [Transfer Portal](https://arxiv.org/abs/2201.11533) — 2022-01-27. Rows in [literature_numeric_claims.csv](literature_numeric_claims.csv).

**Source boundary**: Headline ratios are FBref Opta npxG/90 and xAG/90, recomputed from the RDS. Understat is a second provider, not mixed into the same ratio. Championship / Eredivisie / Primeira Liga player-level npxG was in v1 league scope but **absent from the dump**; FBref HTML 403 this session. Athletic Championship figure is **goals**, selected scorers, `Source claims not independently recomputed`.

## Agent Prompt

```text
Full redo docs/research/epl-arrival-xg-xa-adjustment/epl-arrival-xg-xa-adjustment.md

1. Re-read literature-sources.md and re-fetch any URL whose date moved.
2. Run: uv run --with pyreadr python docs/research/epl-arrival-xg-xa-adjustment/runner.py
3. Refresh Findings from companions in this folder. Do not snapshot totals in this prompt.
   - arrival_xg_xa_summary.csv slice pooled_summer_900 / talent_top_summer_900 / talent_average_summer_900 columns npxg_median_ratio xag_median_ratio n
   - arrival_xg_xa_summary.csv league_*_summer_900 npxg_median_ratio
   - arrival_xg_xa_understat_summary.csv slice pooled_summer_900 npxg_median_ratio xa_median_ratio
   - talent_league_cuts.csv p75_npxg_xag_p90
   - data_quality.csv
4. Keep Source synthesis separate from Project interpretation. No CIR / Feature Contract edit unless a later grilling round says so.
5. Scratch under .tmp/agent/epl-arrival only; delete before finishing.
```

## Method

**Method type**: Empirical player-season before/after + source synthesis.

**Inputs**:
- FBref Big 5 standard RDS (Opta `npxG_Expected`, `xAG_Expected`, `Min_Playing`, `Comp`, `Url`)
- Understat roster `x_g` / `x_a` / `time` plus shots with `situation != Penalty` for npxG
- Literature claims CSV transcribed from fetched pages

**Procedure**:
1. Quality pass on the RDS: row count, competitions, duplicate Url+season+squad (0), Url+season+comp (mid-season club change → sum), null minutes/npxG/xAG, incomplete 2026 season, GK count. See [data_quality.csv](data_quality.csv).
2. Aggregate to player × season-end year × competition. Drop `Pos==GK` and any row with ≥50% minutes as GK.
3. **Summer transition**: source-league season year Y, Premier League season Y+1, prior-year Premier League minutes < 90, source league in {La Liga, Bundesliga, Serie A, Ligue 1}.
4. Primary floor: ≥900 minutes both sides (`meets_900`). Sensitivity: ≥450 (`meets_450`, Prior-Season Seed floor).
5. `ratio_npxg` = PL npxG/90 ÷ prior npxG/90; `ratio_xag` = PL xAG/90 ÷ prior xAG/90. Null if prior rate ≤ 0.
6. Talent on the primary cohort only: within each `prior_league`, top = prior npxG+xAG/90 ≥ league p75; average = [p25, p75); bottom = < p25. Cuts in [talent_league_cuts.csv](talent_league_cuts.csv).
7. Independent Understat summer transitions, same minutes floors; do not join providers in one ratio.
8. Headline statistic = **median** ratio. Mean is reported and is skewed by near-zero priors.

**Definitions and assumptions**:
- First Premier League season ≈ <90 Premier League minutes in the prior season-year (stricter than the 450-minute seed floor).
- January same-season non-PL + PL is a sensitivity slice only.
- Dest “Big 6” = Arsenal, Chelsea, Liverpool, Manchester City, Manchester Utd, Tottenham (name match on FBref squad).
- xAG (FBref/Opta) is not Opta xA and not Understat xA; compare medians across files, not row-wise.

### Metric Definitions & Direction

| Metric | Symbol | Definition / Formula | Direction | Ideal / Benchmark | Description |
|---|---|---|---|---|---|
| npxG retain ratio | `ratio_npxg` | $(\text{npxG}_{PL}/90) / (\text{npxG}_{src}/90)$ | Context (1 = unchanged) | Median of `pooled_summer_900` | Non-penalty xG translation. Mean inflates when prior npxG/90 ≈ 0. |
| xAG retain ratio | `ratio_xag` | $(\text{xAG}_{PL}/90) / (\text{xAG}_{src}/90)$ | Context (1 = unchanged) | Median of `pooled_summer_900` | Chance-creation translation. Estimated separately from npxG. |
| Understat xa retain | `ratio_xa` | $(\text{xA}_{PL}/90) / (\text{xA}_{src}/90)$ | Context | Median of Understat `pooled_summer_900` | Second-provider check. Not mixed with xAG in one cell. |
| npxG rate difference | `diff_npxg` | PL npxG/90 − source npxG/90 | Context | Near 0 if no league/role shock | Absolute per-90 change. |
| Talent split | `talent_split` | top / average / bottom from source-league quartile of prior npxG+xAG/90 | Context | Defined only when `in_primary=1` | Not FPL Price, not named stars. |
| In primary | `in_primary` | summer and `meets_900` after GK drop | Context | 1 = headline row | Filter for the 194-player cohort. |

**Validation boundary**: Selection on ≥900 PL minutes drops arrivals who lost the job. Teammate quality, age, and minutes collapse are confounders, not controlled in the headline median. Championship / Eredivisie / Primeira Liga **not independently recomputed**. 2025-26 incomplete in the RDS.

## Source synthesis

Literature inventory is [literature-sources.md](literature-sources.md). Load-bearing published claims used here:

- No two independent papers publish a ready-made origin→Premier League xG/90 and xA/90 retain table by talent. Transfer Portal (2022) is the strongest xG/xA *model* and refuses a single league scalar; high-xG players are underpredicted (stickier than the model).
- Championship **goals** for a selected scorer sample: mean 20 → ~13 (−36%, retain ~0.65). Not npxG. Survivorship.
- ESPN n=80: inside year 1, xG +11.9% and xA −5.9% from first 19 to last 19 games. Adaptation slope, not origin translation. Shows xG and xA can move differently.
- ClubElo / Opta Power Rankings / UEFA rank the Premier League above other domestic leagues. Those are not xG multipliers. Do not average them into retain-%.

## Project interpretation

### Decision rules

- This round is **research files only**. Do not write Career Individual Rate, Position-Price Prior, or Feature Contract.
- If a later round wants a CIR haircut, use **median** `ratio_npxg` and `ratio_xag`, not the mean, and prefer **source-league × talent** slices over one pooled scalar.
- Championship / Eredivisie / Primeira Liga stay unlabeled in the empirical table until a player-level dump exists. Do not fill them with Athletic goals or UEFA coefficients.

### Practical implications

- Unadjusted last-season xG/xA (today’s CIR) overstates typical Big 5 arrivals who actually play 900+ Premier League minutes.
- A single “EPL is harder → multiply by 0.7” rule is worse than league-specific medians: La Liga arrivals in this sample barely drop; Bundesliga arrivals drop more.
- Destination club and age move the ratio as much as league label (Big 6 vs not; ≤23 vs ≥28).

## Findings

### Evidence

Recomputed 2026-09-02 from [arrival_xg_xa_summary.csv](arrival_xg_xa_summary.csv) and [arrival_xg_xa_understat_summary.csv](arrival_xg_xa_understat_summary.csv). Primary cohort: `slice=pooled_summer_900`, n=194, `in_primary=1`.

**Pooled (use median, not mean)**

| Slice | n | `npxg_median_ratio` | `npxg_mean_ratio` | `xag_median_ratio` | `xag_mean_ratio` |
|---|---|---|---|---|---|
| `pooled_summer_900` | 194 | 0.781 | 1.060 | 0.774 | 1.121 |
| `pooled_summer_450` | 261 | 0.777 | 1.045 | 0.813 | 1.135 |
| Understat `pooled_summer_900` | 194 | 0.784 | 1.188 | 0.763 (`xa_median_ratio`) | 1.266 |

Share with `ratio_npxg` < 1 on the FBref primary slice: 0.651. Two players have prior npxG/90 = 0 so `npxg_n_ratio` = 192.

Understat pooled median npxG retain agrees with FBref to two hundredths. That is the two-source hinge for the pooled haircut.

**Top vs average (within source league, not pooled fame)**

| Slice | n | `npxg_median_ratio` | `xag_median_ratio` |
|---|---|---|---|
| `talent_top_summer_900` | 51 | 0.821 | 0.760 |
| `talent_average_summer_900` | 94 | 0.758 | 0.666 |
| `talent_bottom_summer_900` | 49 | 0.754 | 0.989 |

Top attackers retain more npxG and more xAG than the interquartile group. The npxG gap is modest (0.82 vs 0.76). The xAG gap is larger (0.76 vs 0.67). Bottom-slice **mean** ratios > 1.5 are small-denominator noise; ignore means there. Bottom xAG **median** near 1.0 is not a “they improve” finding.

Same direction as Transfer Portal calibration (high-xG stickier). Not a published retain-% table in that paper.

**Source league (still median)**

| Slice | n | `npxg_median_ratio` | `xag_median_ratio` |
|---|---|---|---|
| `league_La Liga_summer_900` | 46 | 0.927 | 0.978 |
| `league_Ligue 1_summer_900` | 69 | 0.790 | 0.823 |
| `league_Serie A_summer_900` | 41 | 0.754 | 0.597 |
| `league_Bundesliga_summer_900` | 38 | 0.703 | 0.694 |

La Liga → Premier League is a small npxG/xAG step in this sample. Bundesliga is the largest npxG step. Serie A xAG median 0.60 is the largest creation drop; n=41, treat as a league hint not a law.

Understat league medians move the same way (La Liga highest, Bundesliga/Serie A lower). Exact cells in the Understat summary; Serie A n=40 there.

**Confounders (not the headline)**

- Dest Big 6 `npxg_median_ratio` 0.944 (n=66) vs non-Big 6 0.752 (n=128). Teammate/level effect, as StatsBomb 2019 argued.
- Age ≤23: 0.908 npxG median (n=71). Age ≥28: 0.588 (n=33).
- Minutes collapse <0.5: xAG median 0.583 (n=22) — role shock, not a pure league tax.
- January ≥900: n=16, too small.

**Championship / Eredivisie / Primeira Liga**

No player-level npxG/xAG rows in the RDS (`data_quality.csv` comps = Big 5 only). FBref Championship stats page Cloudflare-blocked on curl this session. Substitute: Athletic selected scorers, goals retain ~0.65 (`literature_numeric_claims.csv` `athletic_2022_championship_goals_mean_pl`). Do not treat that as CIR npxG.

Raw RDS: 46258 rows, 38 columns, 0 duplicate Url+season+squad. Header/sample inspected before aggregates. Primary arrivals 2018-19 through 2024-25.

### Alternatives

- One pooled 0.78 on both Event Rates: simple, hides La Liga vs Bundesliga and xG vs xA.
- Mean ratio (~1.06): statistically available, **wrong object** (right-skew).
- UEFA / ClubElo / SPI scaled to retain-%: different object; literature note forbids averaging systems.
- Carry last-season rates unchanged (current CIR): Transfer Portal says this is a bad forecast (xG MSE −54% vs their model). This sample’s median < 1 agrees on direction.

## Decision

**Verdict**: Research-only. For Big 5 summer arrivals who then play ≥900 Premier League minutes, median retain is about **0.78 npxG** and **0.77 xAG** (`pooled_summer_900`). Typical (within-league interquartile) is **0.76 npxG** and **0.67 xAG**. Top (within-league ≥p75) is **0.82 npxG** and **0.76 xAG**. Do not ship CIR.

**Recommended action**:
- Keep [arrival_xg_xa_summary.csv](arrival_xg_xa_summary.csv) as the SoT for any later CIR debate.
- If CIR is opened later: start from league × talent medians, separate `ratio_npxg` and `ratio_xag`, never the mean.
- Leave Championship / Eredivisie / Primeira as a labeled hole.

**Trigger / kill switch**:
- Player-level Championship / Eredivisie / Primeira npxG dump appears → re-run and replace the Athletic goals placeholder.
- A dest-club + role model (Transfer Portal class) beats league × talent medians on the same rows → retire the scalar.
- User asks to apply CIR → new grilling round, not this note.

## Risks and unknowns

- ≥900 PL minutes is survivorship. Quiet flops never enter the median.
- FBref 2025-26 incomplete; 2026-27 arrivals not in the dump.
- xAG ≠ xA ≠ Understat xA. Pooled medians agreed; do not row-match providers.
- Dest Big 6 is a name list, not club xG strength.
- January n=16.
- Eredivisie / Primeira / Championship player npxG not observed.
- Literature Transfer Portal examples are predictions, not this sample’s outcomes.

## Refresh checklist

- [x] `Updated` ISO 8601 +07:00
- [x] `Data stamp` is evidence cutoff
- [x] Source synthesis separate from Project interpretation; no CIR edit
- [x] Unvalidated / missing-league claims labeled
- [x] Agent Prompt names companion path + column
- [x] Scratch under `.tmp/agent/epl-arrival` to delete after run
