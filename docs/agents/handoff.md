# Handoff: Statistical Overhaul of `metrics_component_hybrid` Model

## Goal of Next Session
Execute the 5-step statistical overhaul of `metrics_component_hybrid` in [`models/metrics_component_hybrid.py`](file:///Users/jubilee/fpl-jubilee-ascent/models/metrics_component_hybrid.py) and [`features/builder.py`](file:///Users/jubilee/fpl-jubilee-ascent/features/builder.py), and verify performance improvement using the backtesting harness in [`commands/backtest.py`](file:///Users/jubilee/fpl-jubilee-ascent/commands/backtest.py).

---

## Baseline Backtest Benchmark (GW1–38)
Before making changes, we ran the full 38-gameweek backtest on `metrics_component_hybrid`:

- **Sample Count**: 21,204 player-gameweeks
- **Points RMSE**: `3.2230`
- **Points MAE**: `2.7545`
- **Signed Bias**: `+1.8220` (Model severely overpredicts points)
- **Spearman Rank Correlation**: `-0.0023` (Zero rank correlation with actual points)
- **Top-11 Overlap**: `12.92%`
- **Top-15 Overlap**: `13.33%`

---

## Agreed 5-Step Action Plan

1. **Team Attack & Defence Multipliers (Item #4)**:
   - File: [`features/builder.py`](file:///Users/jubilee/fpl-jubilee-ascent/features/builder.py)
   - Action: Compute rolling team attack and defence ratings (Dixon-Coles / xG for & against) to attach `attack_multiplier` and `defence_multiplier` columns directly to player feature rows instead of falling back to crude symmetric FDR `(6 - diff) / 3`.

2. **WLS & Ridge Calibration (Items #1 & #2)**:
   - File: [`models/metrics_component_hybrid.py`](file:///Users/jubilee/fpl-jubilee-ascent/models/metrics_component_hybrid.py#L60-L87)
   - Action: Update `_fit_metric_weights` to use **Weighted Least Squares (WLS)** weighted by $\sqrt{\text{minutes}}$ and **Ridge regression** shrinking towards default weights `[0.75, 0.25]`. Remove ad-hoc clipping `clip(0, 2)` and `n / (n + 100)`.

3. **Negative Binomial Conceded Distribution (Item #5)**:
   - File: [`models/metrics_component_hybrid.py`](file:///Users/jubilee/fpl-jubilee-ascent/models/metrics_component_hybrid.py#L166-L170)
   - Action: Replace pure Poisson assumption for goals conceded with a Negative Binomial distribution (adding a dispersion parameter $r$) to correctly model clean sheet tails $P(\text{CS})$ and reduce the positive point prediction bias.

4. **Bonus Point Allocation Calibration (Item #7)**:
   - File: [`models/metrics_component_hybrid.py`](file:///Users/jubilee/fpl-jubilee-ascent/models/metrics_component_hybrid.py#L203-L232)
   - Action: Calibrate Softmax temperature $T$ using historical BPS distributions, and update expected bonus calculation to account for the full +3 (1st), +2 (2nd), and +1 (3rd) tier structure across eligible players ($\ge 45$ mins).

5. **Start/Sub Minutes Mixture Model (Item #9)**:
   - File: [`models/metrics_component_hybrid.py`](file:///Users/jubilee/fpl-jubilee-ascent/models/metrics_component_hybrid.py#L131-L133)
   - Action: Replace continuous 60-minute sigmoid curve with a 2-state mixture model ($P(\text{start}) \cdot E[\text{mins} \mid \text{start}] + P(\text{sub}) \cdot E[\text{mins} \mid \text{sub}]$) to accurately reflect rotation risk and clean sheet eligibility ($P(\ge 60\text{m})$).

---

## Key Files & References

- Model Implementation: [`models/metrics_component_hybrid.py`](file:///Users/jubilee/fpl-jubilee-ascent/models/metrics_component_hybrid.py)
- Feature Builder: [`features/builder.py`](file:///Users/jubilee/fpl-jubilee-ascent/features/builder.py)
- Backtest CLI Command: `uv run python -m commands.backtest metrics_component_hybrid --gw_range 1-38`
- Backtest Engine & Metrics: [`backtesting/metrics.py`](file:///Users/jubilee/fpl-jubilee-ascent/backtesting/metrics.py)
- Raw Data Exports:
  - [`data/bootstrap_players.csv`](file:///Users/jubilee/fpl-jubilee-ascent/data/bootstrap_players.csv)
  - [`data/bootstrap_teams.csv`](file:///Users/jubilee/fpl-jubilee-ascent/data/bootstrap_teams.csv)
  - [`data/bootstrap_events.csv`](file:///Users/jubilee/fpl-jubilee-ascent/data/bootstrap_events.csv)

---

## Suggested Skills for Next Agent
- **`tdd`**: Use test-driven development to implement each step incrementally and verify against unit tests.
- **`code-review`**: Perform a code review after implementing the changes to compare new backtesting metrics against the baseline benchmark.
