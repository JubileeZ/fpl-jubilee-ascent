# Hold vs chase: last-season evidence for the barbell strategy

**Updated**: 2026-09-24T15:55:00+07:00
**Data stamp**: 2025-26 archive player/gameweek panel (29,747 fixture rows, 841 players); companion written 2026-09-24T15:55:00+07:00
**Season**: 2025/26
**Status**: Active
**Purpose**: Settle whether weekly points are holdable (buy good, HODL) or chaseable (fixture/form trading) — and where fixtures actually pay
**Scope**: Descriptive panel only (correlations, hit rates, persistence). No transfer-policy simulation; no blending (raw Realized grain). Not a model evaluation.
**Related**: [ADR 0033](../../adr/0033-transfer-plan-hits-until-champion-bias.md) · [Cross-GW dispersion](../xp-cross-gw-dispersion/xp-cross-gw-dispersion.md) · [INDEX](../INDEX.md)
**Artifact**: [hold_chase_summary.csv](hold_chase_summary.csv) `value`

> `Updated` is last note revision time. `Data stamp` is freshness of data or source evidence. Do not add duplicate `Last update` fields.

## Sources

- **Repository data**: `data/archive/2025-26/processed` — performances, fixtures (focal difficulty = `team_h/a_difficulty` by venue), players (position map)

**Source boundary**: One season, exploratory grain (player/GW sums, DGW summed). Difficulty = Official FDR, not xG-profile.

## Agent Prompt

```text
Full redo docs/research/hold-vs-chase-2025-26/hold-vs-chase-2025-26.md

1. Require data/archive/2025-26/processed.
2. Run: uv run python docs/research/hold-vs-chase-2025-26/runner.py
   (fast; rewrites hold_chase_summary.csv in this folder)
3. Refresh Findings from hold_chase_summary.csv value / n.
   Headline cells: autocorr_points, haul_top3_median, hitrate_pts_ge6,
   cs_rate, p_start_given_started, count_nailed_30.
4. Do not snapshot numeric totals in this prompt.
5. Scratch under .tmp/agent/ only; delete before finish.
```

## Method

**Method type**: Descriptive empirical analysis

**Procedure**:
1. Aggregate fixture rows to player/GW (points, minutes, CS, mean difficulty).
2. Difficulty correlation, week-to-week autocorrelation (minutes>0 both weeks), haul concentration (top-3 GW share, 25+ apps), hit/CS rates by difficulty bucket, start persistence + nailed counts.

### Metric Definitions & Direction

| Metric | Symbol | Definition / Formula | Direction | Ideal / Benchmark | Description |
|---|---|---|---|---|---|
| Difficulty correlation | `corr_difficulty_points` | Pearson r, focal difficulty vs points | Context (negative) | `hold_chase_summary.csv` `value` | Fixture signal strength in levels |
| Points autocorrelation | `autocorr_points` | Pearson r, points vs prior GW (min>0 both) | Context (low) | `hold_chase_summary.csv` `value` | Week-to-week predictability |
| Haul concentration | `haul_top3_median` | Median top-3 GW share of season points | Context | `hold_chase_summary.csv` `value` | Must-own-haulers evidence |
| Hit rate | `hitrate_pts_ge6` | P(points ≥ 6) by difficulty bucket | Higher $\uparrow$ easy | `hold_chase_summary.csv` `value` | Fixture payoff in frequency |
| CS rate | `cs_rate` | P(CS) by difficulty bucket, 60+ | Higher $\uparrow$ easy | `hold_chase_summary.csv` `value` | The actionable fixture edge |
| Start persistence | `p_start_given_started` | P(start \\| started prior GW) | Higher $\uparrow$ | `hold_chase_summary.csv` `value` | Nailed-state measurability |

**Validation boundary**: Single season. FDR ruler, not xG-profile. No causal transfer claims.

## Source synthesis

- Not applicable (no external sources; repository data only).

## Project interpretation

### Decision rules

- If autocorr ≈ 0.1 while start persistence ≈ 0.8: hold minutes, not points — barbell (nailed core HODL, fringe fixture rotation).
- If haul concentration ≈ 0.3: premiums must be owned + captained, never traded into.
- If CS easy/hard ≈ 3× while attacker hit-rate ≈ 2×: fixture rotation belongs to DEF/GKP, captaincy to attackers, transfers to minutes.

### Practical implications

- Transfer on minutes/availability; select XI and captain on fixtures; Hits for fixtures almost never repay (edge ~1.25 vs cost 4).

## Findings

### Evidence

- Fixture signal in levels is weak for attackers (`corr_difficulty_points` MID −0.0501, FWD −0.0559) but pays in frequency: `hitrate_pts_ge6` 0.2936 easy vs 0.1619 hard; `mean_points` 4.6964 vs 3.4465. Source: [hold_chase_summary.csv](hold_chase_summary.csv) `value`.
- Week-to-week points nearly unpredictable (`autocorr_points` 0.0899; DEF 0.036). Hauls drive seasons (`haul_top3_median` 0.2781, n=245). Source: [hold_chase_summary.csv](hold_chase_summary.csv) `value`.
- The fixture game is clean sheets: `cs_rate` 0.4376 easy vs 0.1456 hard (3×). Source: [hold_chase_summary.csv](hold_chase_summary.csv) `value`.
- Nailed is measurable: `p_start_given_started` 0.7862 vs 0.0758; 82 nailed (30+), 231 rotators, 528 fringe; core absence 0.1075. Source: [hold_chase_summary.csv](hold_chase_summary.csv) `value`.

### Alternatives

- Transfer-policy simulation (hold vs chase portfolios) — not run; would need transaction costs and squad constraints (Transfer Plan Walk-Forward territory).
- xG-profile difficulty ruler — deferred; FDR suffices for bucket direction.

## Decision

**Verdict**: Barbell confirmed — HODL nailed core season-long, rotate fringe (esp. DEF/GKP) on 1–3 GW fixture windows, captain best owned fixture weekly, transfers on minutes.

**Recommended action**:
- Feed the nailed-core finding into the next Model Candidate (start-persistence-aware participation); keep fixture spend in free decisions.

**Trigger / kill switch**:
- A second season overturning any headline cell reopens the strategy.

## Risks and unknowns

- Single-season evidence; 2025-26 may not repeat.
- Buckets hide within-bucket opponent variance.
- No chip/price/ownership layer in this panel.

## Refresh checklist

- [x] `Updated` uses ISO 8601 timestamp with timezone.
- [x] `Data stamp` identifies current evidence cutoff.
- [x] `Season` and scope remain accurate.
- [x] Source synthesis and Project interpretation remain separate.
- [x] Unvalidated claims labeled.
- [x] Agent Prompt remains runnable and points to stable slug.
- [x] Scratch files removed from `.tmp/agent/`.
