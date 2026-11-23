---
idea_id: EXT-39
name: Lagged BPS and ICT signal check
tier: P2
component: all
status: "blocked (signal not established)"
replaces: "Development-only diagnostic against frozen Champion forecasts, with no model or scoring hook."
grid: ""
inputs: features.position_id; history.player_id; history.gameweek_id; history.fixture_id; history.minutes; history.bps; history.ict_index; history.bonus; history.goals_scored; history.assists
nearest_ledger_row: "component_score_head; evt_bonus_bps_ridge; residual BPS bonus allocation"
spec_path: ideas/EXT-39-lagged-bps-and-ict-signal-check.md
---

# EXT-39: Lagged BPS and ICT signal check

## 1. Hypothesis

Historical Bonus Points System (BPS) and Influence, Creativity and Threat (ICT) can each contain information beyond the Champion forecast. Test separately whether higher prior BPS anticipates underestimated bonus or higher prior ICT anticipates underestimated goals plus assists. Same-fixture correlations do not answer the forward question.

## 2. Signal and comparison

Freeze the Champion forecast at each 2025–26 development deadline. Reuse the training-input rate calculation from [#205](../component-score-head.md) for each signal independently. Use current-season positive-minute rows from earlier Gameweeks already settled by the issue deadline. Convert valid values to numeric and shrink the observed BPS or ICT rate toward the official-position average with 360 pseudo-minutes. Keep the rate per 90 for matching. Use genuine recorded zero values. Exclude missing or nonfinite values from rate estimation and report coverage. Require some observed positive-minute history for the individual signal comparison.

Predeclare two comparisons.

- **Historical BPS → bonus points.** Outcome equals settled bonus minus issued Champion bonus.
- **Historical ICT → goal plus assist points.** Outcome equals settled native goal and assist points minus the sum of the corresponding issued Champion components.

Use lead 0 as primary. Compare rows within the same issue, official position, 15-minute projected-minutes band, 1-point total projected-points band, and 0.25-point band of the tested Champion component or component sum. Anchor bands at zero. Within each cell with at least four eligible rows, form equal-sized top and bottom signal quartiles using floor(cell size / 4). Drop cells with ties across a quartile boundary. Report matching coverage and differences in the baseline forecast variables within the matched groups.

For each cell, compute mean outcome in the high group minus mean outcome in the low group, in FPL points per fixture. Average cell differences within each issue weighted by matched group size, then average the issue differences with equal issue weight. Report coverage, block-specific spreads, and an overall estimate. Positive values indicate higher-signal players beat their forecasts by more than comparable lower-signal players.

## 3. Scope

Diagnostic evaluation of the unchanged Champion. Fit no points adjustment and run no candidate transfer replay. Derive realized goal and assist points using the native scoring rule and official position. Keep recorded DNPs where the issued forecast had positive minutes. Leave missing settlement labels unmatched and report exclusions. Assess longer leads separately if needed. Repeated forecasts of the same fixture are dependent.

## 4. Integration

Reuse the Champion forecast and pre-deadline staging paths. Build a diagnostic sidecar keyed by issue Gameweek, target Gameweek, player, and fixture. Retain each double-gameweek fixture separately and use the same issue cutoff for both legs. Join settled outcomes after producing the predictors. Verify that mutating target and later realized points, events, BPS, and ICT leaves the issued keys, predictors, and forecast values identical. Delaying a fixture's settlement must delay its inclusion in the historical rate.

## 5. Fixed comparisons

Two signal/component comparisons from section 2. Both use the same prior strength, matching scheme, and reporting protocol. No candidate grid.

## 6. Admission and sample support

Use the [staged historical inputs](../historical_replay_inputs.py). Archive schemas contain both signals. S-1 ICT can arrive as numeric strings. Retain GW1–7 receipt provenance separately from reconstructed GW8–38. An observed ICT and Creativity revision is documented in the [input audit](../pre-slate-search-2026-11-21.md#historical-schedule-gap-and-recovery). Label thin or materially imbalanced matches inconclusive.

## 7. Advancement

Advance to fresh candidate ideation only if at least one predeclared contrast is positive in both reconstructed S-1 blocks (GW8–19 and GW20–38), with a one-sided multiplicity-adjusted lower bound above zero for their combined estimate. Use a 5-Gameweek non-wrapping moving block bootstrap on chronological issue-level contrasts and a 97.5% one-sided bound for each of the two comparisons. Preserve the Gameweek calendar and missing comparability when forming blocks. Assess whether the signal reaches players relevant to lineup or transfer decisions. Keep this diagnostic separate from promotion evidence.

A positive diagnostic requires identifying a distinct mechanism and checking it against the ledger before queueing an executable candidate. A mixed or unsupported result leaves candidate execution blocked. Use S-1 only. Keep S-2 and live validation outside this diagnostic.

## 8. Point-in-time inputs

`features.position_id; history.player_id; history.gameweek_id; history.fixture_id; history.minutes; history.bps; history.ict_index; history.bonus; history.goals_scored; history.assists`

Read projected points, projected minutes, and scoring components from issued Champion output. Take the position used for scoring and matching from its issue-time Feature Contract. Access target outcome fields exclusively through the settlement join in the evaluator.

## 9. Python skeleton

```python
from __future__ import annotations

import pandas as pd


def check_issued_signals(
    issued_forecasts: pd.DataFrame, settled_components: pd.DataFrame
) -> pd.DataFrame:
    """Evaluate the predeclared signal contrasts by issue."""
    raise NotImplementedError("Match the issued signals and compare settled residuals")
```

## Prior work

- [#205](../component-score-head.md) used both signals alongside a learned total and could not isolate either signal. Its direct ridge specification remains locked.
- [Earlier BPS experiment](../../../archive/ml-component-champion-blueprint/ml-component-champion-blueprint.md) tested a learned bonus input combining lagged BPS and ICT Influence. Existing bonus allocation and residual BPS locks remain in the [Candidate Ledger](../../candidate-ledger/candidate_ledger.csv).
- Source — FPL model ideation and independent review, 2026-11-23.

## 10. Development results

Neither comparison passed the predeclared advancement criteria. BPS spread was +0.0313 bonus points/fixture for GW8–19 and −0.0072 for GW20–38. ICT spread was −0.0102 goal-plus-assist points/fixture for GW8–19 and +0.1540 for GW20–38. Combined spreads +0.0077 and +0.0904. Simultaneous one-sided lower bounds −0.0604 and −0.0068. Matched 2,569 BPS pairs and 2,262 ICT pairs across 37 Gameweeks. Candidate status remains blocked.

Fit inputs use immutable receipts published before each deadline. Coverage gap leaves GW24 fitted through GW9 and GW38 fitted through GW29. Interpretation applies to the histories available in these receipts. Settlement labels join after forecasting. Target-and-later input mutation left strict staged history identical at all 38 issues.

[Summary](../ext39-deadline-summary.csv) · [Per-issue counts, balance, and spreads](../ext39-deadline-by-issue.csv) · [Issue provenance](../deadline-research-issue-provenance.csv) · [Reproduction runner](../run_deadline_research.py).
